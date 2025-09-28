import json
import os
import shutil
import asyncio

from .utils import (
    _uncompress_if_gzip,
    _uncompress_if_tar,
    execute_command,
    check_license_validity,
    get_redirected_repo_url,
    extract_repo_path,
    _sanitize_vcs_url,
    VCS_PATTERN,
    GITHUB_PATTERN,
)

from packageurl import PackageURL
from pymongo.errors import DuplicateKeyError
from pkgdash.models.database.package import Package
from pkgdash.models.database.deplink import PackageDependency
from pkgdash.models.connector.mongo import create_engine
from pkgdash.models.spdx_license import SPDXLicense
from pkgdash.analyze.github.source import save_sourcelink
from pkgdash.analyze.github.fetch_github import fetch_repo
from pkgdash.analyze.vuln.osv import find_osv_vulns

from github import Github
from github import Auth
from github.Repository import Repository as GithubRepo


packages_dir = "./samples/"

gh = Github(auth=Auth.Token(os.environ["GITHUB_TOKEN"]))


async def save_package_to_db(
    package_url: PackageURL, package_json: dict, pip_report: dict
) -> Package:
    """
    Save package document
    """
    purl_info = package_url.to_dict()
    description: str | None = package_json.get("description")
    install: list[dict] = pip_report.get("install") or []
    if install:
        if (tmp := install[0].get("metadata")) is not None:
            summary = tmp.get("summary")
        else:
            summary = None

    vsc_url = package_json.get("vcs_url")
    code_view_url = package_json.get("code_view_url")
    homepage_url = package_json.get("homepage_url")

    repo_url = (
        _sanitize_vcs_url(vsc_url)
        or _sanitize_vcs_url(code_view_url)
        or _sanitize_vcs_url(homepage_url)
    )
    license_spdx = package_json.get("license_expression_spdx")
    if license_spdx is None:
        license = next(iter(package_json.get("license_detections", [])), None)
        license_spdx = license["license_expression_spdx"] if license else None

    package = Package(
        purl=package_url.to_string(),
        name=purl_info["name"],
        version=purl_info["version"],
        description=description,
        summary=summary,
        homepage_url=homepage_url,
        distro="pypi",
        repo_url=repo_url,
        license=(
            SPDXLicense(license_spdx).name
            if license_spdx and check_license_validity(license_spdx)
            else None
        ),
    )

    # redirect
    if package.repo_url:
        package.repo_url = get_redirected_repo_url(package.repo_url)
    if package.repo_url and GITHUB_PATTERN.match(package.repo_url):
        repo: GithubRepo = gh.get_repo(extract_repo_path(package.repo_url))
        package.repo_url = repo.html_url
        if (
            package.repo_url
            and (not homepage_url or not VCS_PATTERN.match(homepage_url))
            and repo.homepage
        ):
            package.homepage_url = repo.homepage

    try:
        await package.save()
        print(f"Package {package_url} saved to database")
    except DuplicateKeyError:
        await Package.find_one({"purl": package_url.to_string()}).update(
            {"$set": package.dict(exclude={"record_created_at"})}
        )
        print(f"Package {package_url} updated in database")
    finally:
        return package


async def save_dependencies_to_db(
    package: Package, dependencies_json: dict, pip_report: dict
) -> None:
    """
    Save PackageDependency document
    """
    try:

        installed_pkg = pip_report.get("install") or []

        pkgs_version = {}
        for i, pkg in enumerate(installed_pkg[1:], 1):
            try:
                metadata = pkg.get("metadata", {})
                if not metadata:
                    continue

                name = metadata.get("name")
                version = metadata.get("version")
                if name and version:
                    pkgs_version[name.lower()] = version

            except Exception as e:
                continue

        if not dependencies_json:
            return

        for i, dep_json in enumerate(dependencies_json):
            try:

                dep_purl = dep_json.get("purl")
                if not dep_purl:
                    continue

                try:
                    package_url_obj = PackageURL.from_string(dep_purl)
                    dep_name = package_url_obj.name.lower()
                except Exception as e:
                    continue

                if dep_name not in pkgs_version:
                    continue

                version = pkgs_version[dep_name]
                constraint = dep_json.get("extracted_requirement")
                dep_purl_with_version = f"{dep_purl}@{version}"

                print(
                    f"DEBUG: Creating PackageDependency for {dep_purl_with_version}")

                pd = PackageDependency(
                    purl=package.purl,
                    dep_purl=dep_purl_with_version,
                    type="pypi",
                    constraint=constraint,
                )

                try:
                    await pd.save()
                    print(
                        f"PackageDependency {dep_purl_with_version} for {package.purl} saved to database")
                except DuplicateKeyError:
                    try:
                        await PackageDependency.find_one({"purl": package.purl, "dep_purl": dep_purl_with_version}).update(
                            {"$set": pd.dict(exclude={"record_created_at"})}
                        )
                        print(
                            f"PackageDependency {dep_purl_with_version} for {package.purl} updated to database")
                    except Exception as update_error:
                        print(
                            f"DEBUG: Failed to update dependency {dep_purl_with_version}: {update_error}")
                except Exception as save_error:
                    continue

            except Exception as dep_error:
                continue

    except Exception as e:
        print(
            f"ERROR: Fatal error in save_dependencies_to_db for {package.purl}: {e}")
        import traceback
        traceback.print_exc()


def analyze_report(package_name: str, package_version: str, output: str) -> None:
    execute_command(
        f"pip install --dry-run --no-cache {package_name}=={package_version} --report={output} --ignore-installed"
    )


async def analyze(packages_dir: str, save_to_db: bool = True) -> None:
    packages_path = packages_dir + ("/" if packages_dir[-1] != "/" else "")

    async def process_package(p: str, save_to_db: bool) -> None:
        try:
            print(f"Processing {p}: (1/4) Metadata extraction")
            files_to_be_removed = []

            filename = p.split("/")[-1].replace(".tar.gz",
                                                "").replace(".tar.bz2", "")
            os.makedirs(f"./pkgdash/analyze/pypi/output/", exist_ok=True)
            output_json_path = f"./pkgdash/analyze/pypi/output/{filename}.json"
            if not os.path.exists(output_json_path):
                tar_path = _uncompress_if_gzip(p)
                files_to_be_removed += [tar_path]
                package_path = _uncompress_if_tar(tar_path)
                files_to_be_removed += [package_path]

                entries = os.listdir(package_path)
                if len(entries) == 1 and os.path.isdir(entries[0]):
                    package_path = os.path.join(package_path, entries[0])

                execute_command(
                    f"scancode -p --json-pp {output_json_path} {package_path}")
            output_json = json.load(
                open(output_json_path, "r", encoding="utf-8"))

            try:
                pacakge_name = output_json["packages"][0]["name"]
                pacakge_version = output_json["packages"][0]["version"]
            except IndexError as e:
                return
            package_url = PackageURL(
                name=pacakge_name,
                namespace=output_json["packages"][0]["namespace"],
                qualifiers=output_json["packages"][0]["qualifiers"],
                subpath=output_json["packages"][0]["subpath"],
                type="pypi",
                version=pacakge_version,
            )

            pip_output_json_path = f"./pkgdash/analyze/pypi/output/{filename}-pip-report.json"
            if not os.path.exists(pip_output_json_path):
                analyze_report(pacakge_name, pacakge_version,
                               pip_output_json_path)
            pip_report = json.load(
                open(pip_output_json_path, "r", encoding="utf-8"))

            for f in files_to_be_removed:
                if os.path.exists(f) and os.path.isfile(f):
                    os.remove(f)
                elif os.path.exists(f) and os.path.isdir(f):
                    shutil.rmtree(f)

            if save_to_db:
                package = await save_package_to_db(
                    package_url, output_json["packages"][0], pip_report
                )
                purl = package.purl
                repo_url = package.repo_url
                await save_dependencies_to_db(package, output_json["dependencies"], pip_report)

                if repo_url and repo_url.startswith("http") and VCS_PATTERN.match(repo_url):
                    print(f"Processing {p}: (2/4) Fetching GitHub repo data")
                    await save_sourcelink(purl, repo_url)
                    await fetch_repo(purl, repo_url)
                    print(f"Processing {p}: (3/4) Find Vulnerabilities")
                    await find_osv_vulns(purl, repo_url)
                    print(f"Processing {p}: (4/4) Done!")

        except Exception as e:
            print(e)

    tasks = [
        process_package(packages_path + p, save_to_db)
        for p in os.listdir(packages_path)
        if p.endswith(".tar.gz") or p.endswith(".tar.bz2")
    ]
    await asyncio.gather(*tasks)


if __name__ == "__main__":

    async def main():
        await create_engine()
        await analyze(packages_dir, save_to_db=True)

    asyncio.run(main())
