import os
import asyncio
import json
import shutil
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, List
from dataclasses import dataclass
from contextlib import asynccontextmanager
import logging

import requests
from packageurl import PackageURL
from pymongo.errors import DuplicateKeyError

from pkgdash.models.connector.mongo import create_engine
from pkgdash.analyze.utils import (
    _uncompress_if_gzip,
    _uncompress_if_tar,
    execute_command,
    _is_vcs_repo_url,
    _sanitize_vcs_url,
    check_license_validity,
    VCS_PATTERN
)
from pkgdash.models.database.package import Package
from pkgdash.models.database.deplink import PackageDependency
from pkgdash.models.spdx_license import SPDXLicense
from pkgdash.analyze.github.fetch_github import fetch_repo, save_sourcelink
from pkgdash.analyze.vuln.osv import find_osv_vulns


@dataclass
class AnalyzerConfig:

    packages_dir: str = "./samples/npm/"
    output_json_dir: str = "./pkgdash/analyze/npm/output/"
    npm_registry_url: str = "https://registry.npmjs.org"
    max_concurrent_tasks: int = 10

    def __post_init__(self):
        # 确保目录路径以 / 结尾
        if not self.packages_dir.endswith("/"):
            self.packages_dir += "/"
        if not self.output_json_dir.endswith("/"):
            self.output_json_dir += "/"

        # 创建输出目录
        Path(self.output_json_dir).mkdir(parents=True, exist_ok=True)


class NPMRegistryClient:

    def __init__(self, registry_url: str = "https://registry.npmjs.org"):
        self.registry_url = registry_url
        self.session = requests.Session()

    def get_package_info(
        self, package_name: str, package_namespace: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        try:
            url = self._build_registry_url(package_name, package_namespace)
            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            package_info = response.json()
            repository = package_info.get("repository", {})
            homepage = package_info.get("homepage", "")

            return {"pkg": package_name, "repo_url": repository, "homepage": homepage}
        except requests.RequestException as e:
            logging.warning(
                f"Failed to fetch package info for {package_name}: {e}")
            return None

    def _build_registry_url(self, package_name: str, package_namespace: Optional[str]) -> str:
        if package_namespace is None:
            return f"{self.registry_url}/{package_name}"
        else:
            return f"{self.registry_url}/{package_namespace}/{package_name}"


class PackageParser:
    @staticmethod
    def parse_namespace(pkg: str) -> Tuple[str, Optional[str]]:
        if pkg and pkg.startswith("@"):
            parts = pkg.split("/", 1)
            if len(parts) == 2:
                return parts[1], parts[0]
        return pkg, None

    @staticmethod
    def extract_summary(description: Optional[str]) -> Optional[str]:
        if not description or not description.strip():
            return None
        sentence_endings = ["\n", "\r\n", "。",
                            ".", "!", "?", "！", "？", ";", "；"]
        text = description.strip()
        min_pos = len(text)
        for ending in sentence_endings:
            pos = text.find(ending)
            if pos != -1 and pos < min_pos:
                min_pos = pos
        if min_pos == len(text):
            return text[:200] + "..." if len(text) > 200 else text
        summary = text[:min_pos].strip()
        if not summary or len(summary) < 3:
            return None
        return summary


class DatabaseManager:
    def __init__(self, npm_client: NPMRegistryClient):
        self.npm_client = npm_client

    async def save_package(self, package_url: PackageURL, package_json: Dict[str, Any]) -> Package:
        try:
            package = self._build_package_from_json(package_url, package_json)
            await self._upsert_package(package)
            logging.info(f"Package {package_url} processed successfully")
            return package
        except Exception as e:
            logging.error(f"Failed to save package {package_url}: {e}")
            raise

    async def save_dependencies(self, package_json_path: str, lock_json_path: str) -> None:
        try:
            package_json = self._load_json(package_json_path)
            lock_json = self._load_json(lock_json_path)

            pkg_purl = self._extract_package_purl(lock_json)
            dependencies = self._extract_dependencies(package_json, lock_json)

            await self._save_dependency_relationships(
                pkg_purl, dependencies, package_json.get("dependencies", {})
            )

        except Exception as e:
            logging.error(f"Failed to save dependencies: {e}")
            raise

    def _build_package_from_json(
        self, package_url: PackageURL, package_json: Dict[str, Any]
    ) -> Package:
        purl_info = package_url.to_dict()
        description = package_json.get("description")

        repo_url = self._extract_repo_url(package_url, package_json)
        homepage_url = package_json.get("homepage_url")

        license_spdx = self._extract_license(package_json)

        return Package(
            purl=package_url.to_string(),
            name=purl_info["name"],
            version=purl_info["version"],
            description=description,
            summary=PackageParser.extract_summary(description),
            homepage_url=homepage_url,
            distro="npm",
            repo_url=repo_url,
            license=(
                SPDXLicense(license_spdx).name
                if license_spdx and check_license_validity(license_spdx)
                else None
            ),
        )

    def _extract_repo_url(
        self, package_url: PackageURL, package_json: Dict[str, Any]
    ) -> Optional[str]:
        vcs_url = package_json.get("vcs_url")
        code_view_url = package_json.get("code_view_url")
        homepage_url = package_json.get("homepage_url")

        repo_url = (
            _sanitize_vcs_url(vcs_url)
            or _sanitize_vcs_url(code_view_url)
            or _sanitize_vcs_url(homepage_url)
        )

        if not _is_vcs_repo_url(repo_url) or not _is_vcs_repo_url(homepage_url):
            npm_info = self.npm_client.get_package_info(
                package_url.name, package_url.namespace)
            if npm_info:
                repo_info = npm_info["repo_url"]
                if isinstance(repo_info, str):
                    repo_url = _sanitize_vcs_url(repo_info)
                elif isinstance(repo_info, dict):
                    repo_url = _sanitize_vcs_url(repo_info.get("url"))

        return repo_url

    def _extract_license(self, package_json: Dict[str, Any]) -> Optional[str]:
        license_spdx = package_json.get("license_expression_spdx")
        if license_spdx is None:
            license_detections = package_json.get("license_detections", [])
            if license_detections:
                license_spdx = license_detections[0].get(
                    "license_expression_spdx")
        return license_spdx

    def _load_json(self, file_path: str) -> Dict[str, Any]:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _extract_package_purl(self, lock_json: Dict[str, Any]) -> PackageURL:
        pkg_name = lock_json.get("name")
        pkg_version = lock_json.get("version")
        pkg_name, pkg_namespace = PackageParser.parse_namespace(pkg_name)

        return PackageURL(
            name=pkg_name,
            namespace=pkg_namespace,
            qualifiers=None,
            subpath=None,
            type="npm",
            version=pkg_version,
        )

    def _extract_dependencies(
        self, package_json: Dict[str, Any], lock_json: Dict[str, Any]
    ) -> List[Tuple[str, str]]:
        dependencies = []
        required_deps = list(package_json.get("dependencies", {}).keys())
        lock_packages = lock_json.get("packages", {})
        lock_dependencies = lock_json.get("dependencies", {})

        for dep_name in required_deps:
            version = self._find_dependency_version(
                dep_name, lock_packages, lock_dependencies)
            if version:
                dependencies.append((dep_name, version))

        return dependencies

    def _find_dependency_version(
        self, dep_name: str, lock_packages: Dict[str, Any], lock_dependencies: Dict[str, Any]
    ) -> Optional[str]:
        possible_keys = [
            dep_name,
            f"node_modules/{dep_name}",
        ]

        for key in possible_keys:
            if key in lock_packages:
                return lock_packages[key].get("version")

        if dep_name in lock_dependencies:
            return lock_dependencies[dep_name].get("version")

        return None

    async def _save_dependency_relationships(
        self, pkg_purl: PackageURL, dependencies: List[Tuple[str, str]], constraints: Dict[str, str]
    ) -> None:
        purl_str = pkg_purl.to_string()

        for dep_name, version in dependencies:
            dep_name_parsed, dep_namespace = PackageParser.parse_namespace(
                dep_name)
            dep_purl = PackageURL(
                name=dep_name_parsed,
                namespace=dep_namespace,
                qualifiers=None,
                subpath=None,
                type="npm",
                version=version,
            )

            dependency = PackageDependency(
                purl=purl_str,
                dep_purl=dep_purl.to_string(),
                constraint=constraints.get(dep_name),
                type="npm",
            )

            await self._upsert_dependency(dependency)

    async def _upsert_package(self, package: Package) -> None:
        try:
            await package.save()
            logging.info(f"Package {package.purl} saved to database")
        except DuplicateKeyError:
            await Package.find_one({"purl": package.purl}).update(
                {"$set": package.dict(exclude={"record_created_at"})}
            )
            logging.info(f"Package {package.purl} updated in database")

    async def _upsert_dependency(self, dependency: PackageDependency) -> None:
        try:
            await dependency.save()
            logging.info(
                f"Dependency {dependency.dep_purl} for {dependency.purl} saved")
        except DuplicateKeyError:
            await PackageDependency.find_one(
                {"purl": dependency.purl, "dep_purl": dependency.dep_purl}
            ).update({"$set": dependency.dict(exclude={"record_created_at"})})
            logging.info(
                f"Dependency {dependency.dep_purl} for {dependency.purl} updated")


class PackageProcessor:

    def __init__(self, config: AnalyzerConfig, db_manager: DatabaseManager):
        self.config = config
        self.db_manager = db_manager

    async def process_package(self, package_file: str, save_to_db: bool = True) -> None:
        temp_files = []
        try:
            logging.info(
                f"Processing {package_file}: (1/4) Metadata extraction")
            package_path, temp_files = await self._prepare_package(package_file)
            output_json_path = await self._run_scancode_analysis(package_file, package_path)
            await self._ensure_package_lock(package_path)
            package_url, package_json = await self._parse_package_info(output_json_path)

            if package_url and save_to_db:
                package = await self.db_manager.save_package(package_url, package_json)
                await self._save_dependencies_if_exists(package_path)

                if package.repo_url and VCS_PATTERN.match(package.repo_url):
                    logging.info(
                        f"Package {package.purl} repository URL: {package.repo_url}")
                    print(
                        f"Processing {package_file}: (2/4) Fetching GitHub repo data")
                    await save_sourcelink(package_url, package.repo_url)
                    await fetch_repo(package_url, package.repo_url)
                    print(
                        f"Processing {package_file}: (3/4) Find Vulnerabilities")
                    await find_osv_vulns(package_url, package.repo_url)
                    print(f"Processing {package_file}: (4/4) Done!")

        except Exception as e:
            logging.error(f"Error processing package {package_file}: {e}")
        finally:
            await self._cleanup_temp_files(temp_files)

    async def _prepare_package(self, package_file: str) -> Tuple[str, List[str]]:
        temp_files = []

        tar_path = _uncompress_if_gzip(package_file)
        if tar_path != package_file:
            temp_files.append(tar_path)

        package_path = _uncompress_if_tar(tar_path)
        if package_path != tar_path:
            temp_files.append(package_path)

        entries = os.listdir(package_path)
        if len(entries) == 1 and os.path.isdir(os.path.join(package_path, entries[0])):
            package_path = os.path.join(package_path, entries[0])

        return package_path, temp_files

    async def _run_scancode_analysis(self, package_file: str, package_path: str) -> str:
        filename = Path(package_file).stem.replace(".tar", "")
        output_json_path = os.path.join(
            self.config.output_json_dir, f"{filename}.json")

        if not os.path.exists(output_json_path):
            execute_command(
                f"scancode -p --json-pp {output_json_path} {package_path}")

        return output_json_path

    async def _ensure_package_lock(self, package_path: str) -> None:
        lock_json_path = os.path.join(package_path, "package-lock.json")
        if not os.path.exists(lock_json_path):
            execute_command(f"npm install --package-lock-only", package_path)

    async def _parse_package_info(
        self, output_json_path: str
    ) -> Tuple[Optional[PackageURL], Optional[Dict[str, Any]]]:
        try:
            with open(output_json_path, "r", encoding="utf-8") as f:
                output_json = json.load(f)

            for package_info in output_json.get("packages", []):
                if package_info.get("type") == "npm":
                    package_url = PackageURL(
                        name=package_info["name"],
                        namespace=package_info.get("namespace"),
                        qualifiers=package_info.get("qualifiers"),
                        subpath=package_info.get("subpath"),
                        type=package_info["type"],
                        version=package_info["version"],
                    )
                    return package_url, package_info

            return None, None

        except (json.JSONDecodeError, KeyError) as e:
            logging.error(
                f"Failed to parse package info from {output_json_path}: {e}")
            return None, None

    async def _save_dependencies_if_exists(self, package_path: str) -> None:
        package_json_path = os.path.join(package_path, "package.json")
        lock_json_path = os.path.join(package_path, "package-lock.json")

        if os.path.exists(package_json_path) and os.path.exists(lock_json_path):
            await self.db_manager.save_dependencies(package_json_path, lock_json_path)

    async def _cleanup_temp_files(self, temp_files: List[str]) -> None:
        for file_path in temp_files:
            try:
                if os.path.exists(file_path):
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
            except OSError as e:
                logging.warning(
                    f"Failed to cleanup temp file {file_path}: {e}")


class NPMPackageAnalyzer:

    def __init__(self, config: AnalyzerConfig):
        self.config = config
        self.npm_client = NPMRegistryClient(config.npm_registry_url)
        self.db_manager = DatabaseManager(self.npm_client)
        self.processor = PackageProcessor(config, self.db_manager)
        self.processed_count = 0

    async def analyze_packages(self, save_to_db: bool = True) -> None:
        package_files = self._get_package_files()

        if not package_files:
            logging.info("No package files found to process")
            return

        logging.info(f"Found {len(package_files)} packages to process")

        semaphore = asyncio.Semaphore(self.config.max_concurrent_tasks)

        async def process_with_semaphore(package_file: str) -> None:
            async with semaphore:
                await self._process_package_with_counter(package_file, save_to_db)

        tasks = [process_with_semaphore(pf) for pf in package_files]
        await asyncio.gather(*tasks, return_exceptions=True)

        logging.info(f"Completed processing {self.processed_count} packages")

    def _get_package_files(self) -> List[str]:
        package_files = []
        packages_path = Path(self.config.packages_dir)

        if not packages_path.exists():
            logging.error(
                f"Packages directory does not exist: {packages_path}")
            return []

        for file_path in packages_path.iterdir():
            if file_path.suffix in [".gz", ".bz2"] and file_path.name.endswith(
                (".tar.gz", ".tar.bz2")
            ):
                package_files.append(str(file_path))

        return sorted(package_files)

    async def _process_package_with_counter(self, package_file: str, save_to_db: bool) -> None:
        self.processed_count += 1
        logging.info(
            f"Processing package {self.processed_count}: {Path(package_file).name}")
        await self.processor.process_package(package_file, save_to_db)


@asynccontextmanager
async def setup_analyzer(config: AnalyzerConfig):
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    await create_engine()

    analyzer = NPMPackageAnalyzer(config)

    try:
        yield analyzer
    finally:
        pass


async def main():
    config = AnalyzerConfig(
        packages_dir="./samples/npm/",
        output_json_dir="./pkgdash/analyze/npm/output/",
        max_concurrent_tasks=5,
    )

    async with setup_analyzer(config) as analyzer:
        await analyzer.analyze_packages(save_to_db=True)


if __name__ == "__main__":
    asyncio.run(main())
