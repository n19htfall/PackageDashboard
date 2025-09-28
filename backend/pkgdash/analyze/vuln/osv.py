import asyncio
from github import Github, Auth
from github.Repository import Repository as GithubRepo
from github.Commit import Commit
import os
import logging
import json
from pkgdash.models.database.package import PackageStats, Package
from pkgdash.models.database.repository import Repository, RepositoryStats
from pkgdash.models.database.sourcelink import PackageSource
from pkgdash.models.database.package import PackageVulns
from datetime import datetime
from typing import AsyncGenerator, Tuple, Literal, List
from zoneinfo import ZoneInfo
from pkgdash.models.connector.mongo import create_engine
from packageurl import PackageURL
import argparse
import requests
import re

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


with open("./osv_ecosystem_map.json", "r") as file:
    osv_ecosystem_map: dict = json.load(file)


def extract_repo_path(github_url):
    match = re.search(r"github\.com/([^/]+/[^/]+)", github_url)
    if match:
        return match.group(1)
    return None


async def iterate_packages(distro_name: str = None) -> AsyncGenerator[Tuple[str, str], None]:
    if distro_name is None:
        async for package in Package.find_all():
            if package.repo_url:
                yield package.purl, package.repo_url
    else:
        async for package in Package.find(Package.distro == distro_name):
            if package.repo_url:
                yield package.purl, package.repo_url


def get_vulns_by_commit(commit_sha: str) -> List[dict]:
    data = {
        "commit": commit_sha,
    }
    response = requests.post("https://api.osv.dev/v1/query", json=data)
    response_json: dict = response.json()
    vulns = response_json.get("vulns", None)
    return vulns


def get_vulns_by_package(ecosystem: str, name: str, version: str) -> List[dict]:
    data = {"version": version, "package": {
        "name": name, "ecosystem": ecosystem}}
    response = requests.post("https://api.osv.dev/v1/query", json=data)
    response_json: dict = response.json()
    vulns = response_json.get("vulns", None)
    return vulns


def get_release_commit(repo: GithubRepo, version_to_find: str) -> Commit | None:
    releases = repo.get_releases()
    for release in releases:
        if release.title is None or release.tag_name is None:
            print("Error ", repo.full_name, " ", version_to_find)
            return None
        if version_to_find in release.title or version_to_find in release.tag_name:
            git_ref = repo.get_git_ref(f"tags/{release.tag_name}")
            if git_ref.object.type == "commit":
                commit_sha = git_ref.object.sha
            elif git_ref.object.type == "tag":
                tag_obj = repo.get_git_tag(git_ref.object.sha)
                commit_sha = tag_obj.object.sha
            commit = repo.get_commit(commit_sha)
            return commit
    tags = repo.get_tags()
    for tag in tags:
        if version_to_find in tag.name:
            git_ref = repo.get_git_ref(f"tags/{tag.name}")
            if git_ref.object.type == "commit":
                commit_sha = git_ref.object.sha
            elif git_ref.object.type == "tag":
                tag_obj = repo.get_git_tag(git_ref.object.sha)
                commit_sha = tag_obj.object.sha
            commit = repo.get_commit(commit_sha)
            return commit
    return None


async def save_to_db(doc: PackageVulns, primary_key: dict) -> None:
    if hasattr(doc, "url"):
        url_value = doc.url
    elif hasattr(doc, "purl"):
        url_value = doc.purl
    else:
        url_value = "unknown"
    try:
        find_doc = await type(doc).find_one(primary_key)
        if find_doc:
            await find_doc.update({"$set": doc.model_dump(exclude={"record_created_at"})})
            logger.info(
                f"Document {url_value} updated to {type(doc).__name__} database")
        else:
            await doc.save()
            logger.info(
                f"Document {url_value} saved to {type(doc).__name__} database")
    except Exception as e:
        logger.error(f"Saving document {url_value} error: {e}")


async def find_osv_vulns(purl: str, repo_url: str) -> None:
    try:
        vulns = None
        purl_obj = PackageURL.from_string(purl)

        if repo_url:
            auth = Auth.Token(os.getenv("GITHUB_TOKEN"))
            gh = Github(auth=auth)
            full_name = extract_repo_path(repo_url)
            if full_name is None:
                return
            repo = gh.get_repo(full_name)
            version_string = purl_obj.version or ""
            version = (
                version_string.split(
                    "-")[0] if "-" in version_string else version_string
            )
            commit = get_release_commit(repo, version)
            if commit is not None:
                vulns = get_vulns_by_commit(commit_sha=commit.sha)
            repo_is_archived = repo.archived
            repo_n_contributors = repo.get_contributors().totalCount
        else:
            ecosys = osv_ecosystem_map.get(purl_obj.type)
            vulns = get_vulns_by_package(
                ecosystem=ecosys, name=purl_obj.name, version=purl_obj.version
            )
        ids = set()
        if vulns is not None:
            for vuln in vulns:
                vuln_id = vuln.get("id")
                if vuln_id and vuln_id.startswith("CVE"):
                    ids.add(vuln_id)
                else:
                    aliases = vuln.get("aliases", [])
                    cve_alias = next(
                        (alias for alias in aliases if alias.startswith("CVE")),
                        None,
                    )
                    if cve_alias:
                        ids.add(cve_alias)
                    elif vuln_id:
                        ids.add(vuln_id)
        ids_lst = list(ids)
        pv = PackageVulns(
            purl=purl,
            repo_url=repo_url,
            name=purl_obj.name,
            version=version,
            vulns=ids_lst,
            commit_sha=commit.sha if commit else None,
            is_archived=repo_is_archived,
            n_contributors=repo_n_contributors,
        )
        pv_key: dict = {"purl": pv.purl, "repo_url": pv.repo_url}
        await save_to_db(pv, pv_key)
    except AttributeError as e:
        return


if __name__ == "__main__":
    d = "pypi"

    async def main():
        await create_engine()

        async for purl, repo_url in iterate_packages(d):
            doc = await PackageVulns.find_one({"purl": purl, "repo_url": repo_url})
            if doc:
                continue
            try:
                vulns = None
                purl_obj = PackageURL.from_string(purl)
                if purl_obj.type != d:
                    continue
                if repo_url:
                    auth = Auth.Token(os.getenv("GITHUB_TOKEN"))
                    gh = Github(auth=auth)
                    full_name = extract_repo_path(repo_url)
                    if full_name is None:
                        continue
                    repo = gh.get_repo(full_name)
                    version_string = purl_obj.version or ""
                    version = (
                        version_string.split(
                            "-")[0] if "-" in version_string else version_string
                    )
                    commit = get_release_commit(repo, version)
                    if commit is not None:
                        vulns = get_vulns_by_commit(commit_sha=commit.sha)
                    repo_is_archived = repo.archived
                    repo_n_contributors = repo.get_contributors().totalCount
                else:
                    ecosys = osv_ecosystem_map.get(purl_obj.type)
                    vulns = get_vulns_by_package(
                        ecosystem=ecosys, name=purl_obj.name, version=purl_obj.version
                    )
                ids = set()
                if vulns is not None:
                    for vuln in vulns:
                        vuln_id = vuln.get("id")
                        if vuln_id and vuln_id.startswith("CVE"):
                            ids.add(vuln_id)
                        else:
                            aliases = vuln.get("aliases", [])
                            cve_alias = next(
                                (alias for alias in aliases if alias.startswith("CVE")),
                                None,
                            )
                            if cve_alias:
                                ids.add(cve_alias)
                            elif vuln_id:
                                ids.add(vuln_id)
                ids_lst = list(ids)
                pv = PackageVulns(
                    purl=purl,
                    repo_url=repo_url,
                    name=purl_obj.name,
                    version=version,
                    vulns=ids_lst,
                    commit_sha=commit.sha if commit else None,
                    is_archived=repo_is_archived,
                    n_contributors=repo_n_contributors,
                )
                pv_key: dict = {"purl": pv.purl, "repo_url": pv.repo_url}
                await save_to_db(pv, pv_key)
            except AttributeError as e:
                print(f"属性错误: {e}, purl={purl}, 跳过")
                continue
            except Exception as e:
                print(f"发生异常: {e}, purl={purl}, 跳过")
                continue

    asyncio.run(main())
