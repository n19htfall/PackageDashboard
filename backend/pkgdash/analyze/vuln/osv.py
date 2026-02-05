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

CVE_RE = re.compile(r"(CVE-\d{4}-\d{4,})", re.IGNORECASE)

def extract_cve_ids_from_vuln(vuln: dict) -> List[str]:
    ids = set()
    if not isinstance(vuln, dict):
        return []
    # check string fields
    for field in ("id", "details", "summary"):
        val = vuln.get(field)
        if isinstance(val, str):
            for m in CVE_RE.finditer(val):
                ids.add(m.group(1).upper())
    # check aliases list
    aliases = vuln.get("aliases") or []
    if isinstance(aliases, list):
        for a in aliases:
            if isinstance(a, str):
                for m in CVE_RE.finditer(a):
                    ids.add(m.group(1).upper())
                if a.upper().startswith("CVE-"):
                    ids.add(a.upper())
    # check references for urls/comments that may include CVE
    for ref in vuln.get("references", []) or []:
        if not isinstance(ref, dict):
            continue
        for key in ("url", "comment", "type"):
            v = ref.get(key) or ""
            if isinstance(v, str):
                for m in CVE_RE.finditer(v):
                    ids.add(m.group(1).upper())
    return list(ids)


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
    data = {"version": version, "package": {"name": name, "ecosystem": ecosystem}}
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
            await find_doc.update({"$set": doc.dict(exclude={"record_created_at"})})
            logger.info(f"Document {url_value} updated to {type(doc).__name__} database")
        else:
            await doc.save()
            logger.info(f"Document {url_value} saved to {type(doc).__name__} database")
    except Exception as e:
        logger.error(f"Saving document {url_value} error: {e}")


if __name__ == "__main__":
    async def main():
        await create_engine()
        purl = "pkg:rpm/openeuler/libyang@1.0.184-5.oe2203sp1?arch=aarch64&epoch=0&distro=openeuler-2203sp1"
        repo_url ="https://github.com/CESNET/libyang"
        try:
            vulns = None
            purl_obj = PackageURL.from_string(purl)
            if repo_url:
                auth = Auth.Token("")
                gh = Github(auth=auth)
                full_name = extract_repo_path(repo_url)
                repo = gh.get_repo(full_name)
                version_string = purl_obj.version or ""
                version = (
                    version_string.split("-")[0] if "-" in version_string else version_string
                )
                commit = get_release_commit(repo, version)
                if commit is not None:
                    vulns = get_vulns_by_commit(commit_sha=commit.sha)
                repo_is_archived = repo.archived
                repo_n_contributors = repo.get_contributors().totalCount
            ids = set()
            if vulns is not None:
                logger.debug("OSV returned %d vuln objects for purl=%s", len(vulns), purl)
                for vuln in vulns:
                    try:
                        extracted = extract_cve_ids_from_vuln(vuln)
                        if extracted:
                            ids.update(extracted)
                        else:
                            vuln_id = vuln.get("id")
                            if vuln_id:
                                ids.add(vuln_id)
                            else:
                                logger.debug(
                                    "No CVE ids extracted from vuln object for purl=%s — vuln preview: %s",
                                    purl,
                                    json.dumps(vuln, ensure_ascii=False)[:1000],
                                )
                    except Exception:
                        logger.exception("Error extracting CVE ids from vuln for purl=%s", purl)
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
            logger.warning("Error: %s, purl=%s, skip", e, purl)
        except Exception:
            logger.exception("Error processing purl=%s, skip", purl)

    asyncio.run(main())
