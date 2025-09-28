import os
import asyncio
import json
import shutil

import requests
from packageurl import PackageURL
from typing import Optional

from pkgdash.models.connector.mongo import create_engine
from pymongo.errors import DuplicateKeyError
from pkgdash.analyze.utils import (
    _uncompress_if_gzip,
    _uncompress_if_tar,
    execute_command,
    _is_vcs_repo_url,
    _sanitize_vcs_url,
    check_license_validity,
)
from pkgdash.models.database.package import Package
from pkgdash.models.database.deplink import PackageDependency
from pkgdash.models.spdx_license import SPDXLicense

packages_dir = "/home/lzh/maven"
output_json_dir = "./pkgdash/analyze/maven/output/"


def extract_summary(description: Optional[str]) -> Optional[str]:
    """从描述中提取摘要（提取第一句话作为摘要）"""
    if not description or not description.strip():
        return None
    sentence_endings = ["\n", "\r\n", "。", ".", "!", "?", "！", "？", ";", "；"]
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


async def save_package_to_db(package_url: PackageURL, package_json: dict) -> Package:
    """
    Save package document
    """
    purl_info = package_url.to_dict()
    description: str | None = package_json.get("description")

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
        summary=description,
        homepage_url=homepage_url,
        distro="maven",
        repo_url=repo_url,
        license=license_spdx,
    )

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


def parse_namespace(pkg: str) -> tuple[str, str | None]:
    if pkg and pkg[0] == "@":
        res = pkg.split("/")
        return res[1], res[0]
    else:
        return pkg, None


async def save_dependencies_to_db(package_json: dict, deps: list[dict]):
    pkg_purl = PackageURL(
        name=package_json.get("name"),
        namespace=package_json.get("namespace"),
        qualifiers=package_json.get("qualifiers"),
        subpath=package_json.get("subpath"),
        type="maven",
        version=package_json.get("version"),
    )
    for dep in deps:
        dep_purl = dep.get("purl")
        purl_str = pkg_purl.to_string()
        pd = PackageDependency(
            purl=purl_str,
            dep_purl=dep_purl,
            constraint="",
            type="maven",
        )
        try:
            await pd.save()
            print(f"Package {dep_purl} for {purl_str} saved to database")
        except DuplicateKeyError:
            await PackageDependency.find_one({"purl": purl_str, "dep_purl": dep_purl}).update(
                {"$set": pd.dict(exclude={"record_created_at"})}
            )
            print(f"Package {dep_purl} for {purl_str} updated in database")


cnt = 0


async def analyze(packages_dir: str, save_to_db: bool = True) -> None:
    packages_path = packages_dir + ("/" if packages_dir[-1] != "/" else "")

    async def process_package(p: str, save_to_db: bool) -> None:
        try:
            global cnt
            print(f"Processing {p} : {cnt}")
            cnt += 1
            # files_to_be_removed = []
            filename = p.split("/")[-1].replace(".tar.gz", "").replace(".tar.bz2", "")
            tar_path = _uncompress_if_gzip(p)
            # files_to_be_removed += [tar_path]
            package_path = _uncompress_if_tar(tar_path)
            # files_to_be_removed += [package_path]
            entries = os.listdir(package_path)
            if len(entries) == 1 and os.path.isdir(os.path.join(package_path, entries[0])):
                package_path = os.path.join(package_path, entries[0])
            output_json_path = output_json_dir + f"{filename}.json"
            if not os.path.exists(output_json_path):
                execute_command(f"scancode -p --json-pp {output_json_path} {package_path}")
            output_json = json.load(open(output_json_path, "r", encoding="utf-8"))
            i = 0
            try:
                while output_json["packages"][i]["type"] != "maven":
                    i += 1
                pacakge_name = output_json["packages"][i]["name"]
                pacakge_version = output_json["packages"][i]["version"]
                package_url = PackageURL(
                    name=pacakge_name,
                    namespace=output_json["packages"][i]["namespace"],
                    qualifiers=output_json["packages"][i]["qualifiers"],
                    subpath=output_json["packages"][i]["subpath"],
                    type=output_json["packages"][i]["type"],
                    version=pacakge_version,
                )
            except IndexError as e:
                return

            if package_url and save_to_db:
                await save_package_to_db(package_url, output_json["packages"][i])
                await save_dependencies_to_db(
                    output_json["packages"][i], output_json["dependencies"]
                )

            # for f in files_to_be_removed:
            #     if os.path.exists(f) and os.path.isfile(f):
            #         os.remove(f)
            #     elif os.path.exists(f) and os.path.isdir(f):
            #         shutil.rmtree(f)
        except Exception as e:
            print("Error: ", e)

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
