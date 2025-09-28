import asyncio
from github import Github, Auth
from github.Repository import Repository as GithubRepo
import os
import logging
import json
from pkgdash.models.database.package import PackageStats, Package
from pkgdash.models.database.repository import Repository, RepositoryStats
from pkgdash.models.database.sourcelink import PackageSource
from datetime import datetime
from typing import AsyncGenerator, Tuple, Literal, Optional
from zoneinfo import ZoneInfo
from pkgdash.models.connector.mongo import create_engine
from packageurl import PackageURL
import argparse
import re

DATE_RANGE = Literal["Day", "Week", "Month", "Year"]

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# SPDX license map
with open("./license_map.json", "r") as file:
    license_map: dict = json.load(file)


async def iterate_packages(distro_name: str) -> AsyncGenerator[Tuple[str, str], None]:
    async for package in Package.find(Package.distro == distro_name):
        if package.repo_url:
            yield package.purl, package.repo_url


async def find_pkg_by_purl(purl: str) -> Package | None:
    return await Package.find_one(Package.purl == purl)


def extract_repo_path(github_url):
    match = re.search(r"github\.com/([^/]+/[^/]+)", github_url)
    if match:
        return match.group(1)
    return None


def get_repository(repo: GithubRepo) -> Repository:
    try:
        # Extract primary language
        primary_language = None
        if repo.language:
            primary_language = repo.language
        # Extract license information
        license_name = None
        if repo.license:
            if repo.license.spdx_id != "NOASSERTION":
                license_name = repo.license.spdx_id
            else:
                license_name = license_map.get(repo.license)

        # Extract contributors
        contributors = repo.get_contributors()
        contributors_html = [c.html_url for c in contributors]

        # Create Repository model
        repository = Repository(
            url=repo.html_url,
            name=repo.name,
            n_stars=repo.stargazers_count,
            created_at=repo.created_at,
            updated_at=repo.updated_at,
            pushed_at=repo.pushed_at,
            is_archived=repo.archived,
            is_template=repo.is_template,
            is_fork=repo.fork,
            primary_language=primary_language,
            topics=repo.get_topics(),
            description=repo.description,
            license=license_name,
            contributors=contributors_html,
        )
        return repository
    except Exception as e:
        logger.error(f"Error fetching repository {repo.name}: {e}")
        raise


def get_repostats(
    purl: str, repo: GithubRepo, interval: DATE_RANGE
) -> Tuple[RepositoryStats, PackageStats]:
    to_date = datetime.now(ZoneInfo("UTC")).replace(
        hour=0, minute=0, second=0, microsecond=0)
    # from_date = get_date_range(interval, to_date)
    from_date = to_date
    try:
        _prs = repo.get_pulls(state="all").totalCount
        n_commits = repo.get_commits().totalCount
        n_comments = repo.get_issues_comments().totalCount
        n_issues = repo.get_issues(state="all").totalCount
        n_tags = repo.get_tags().totalCount
        n_stars = repo.get_stargazers().totalCount

        stats = RepositoryStats(
            url=repo.html_url,
            stats_from=from_date,
            stats_interval=interval,
            n_commits=n_commits,
            n_comments=n_comments,
            n_issues=n_issues,
            n_prs=_prs,
            n_tags=n_tags,
            n_stars=n_stars,
        )
        pkg_stats = PackageStats(
            purl=purl,
            stats_from=from_date,
            stats_interval=interval,
            n_commits=n_commits,
            n_comments=n_comments,
            n_issues=n_issues,
            n_prs=_prs,
            n_tags=n_tags,
            n_stars=n_stars,
        )
        return stats, pkg_stats
    except Exception as e:
        logger.error(f"计算仓库{repo.name}的统计数据时出错: {e}")
        raise


async def save_sourcelink(purl: str, url: str) -> None:
    if url[-1] == "/":
        url = url[:-1]
    type = PackageURL.from_string(purl).type
    source = PackageSource(purl=purl, repo_url=url, type=type)
    d = dict(purl=purl, repo_url=url, type=type)
    try:
        find_doc = await PackageSource.find_one(d)
        if find_doc:
            await find_doc.update({"$set": source.dict(exclude={"sourced_at"})})
            logger.info(f"Document {purl} updated to PackageSource database")
        else:
            await source.save()
            logger.info(f"Document {purl} saved to PackageSource database")
    except Exception as e:
        logger.error(f"Saving document {purl} error: {e}")


async def save_to_db(doc: Repository | RepositoryStats | PackageStats, primary_key: dict) -> None:
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
            logger.info(
                f"Document {url_value} updated to {type(doc).__name__} database")
        else:
            await doc.save()
            logger.info(
                f"Document {url_value} saved to {type(doc).__name__} database")
    except Exception as e:
        logger.error(f"Saving document {url_value} error: {e}")


async def fetch_repo(purl, url, gh: Optional[Github] = None) -> None:
    if gh is None:
        gh = Github(auth=Auth.Token(os.environ["GITHUB_TOKEN"]))
    try:
        repo = gh.get_repo(extract_repo_path(url))
    except Exception as e:
        logger.error(e)
        return None
    INTERVAL: DATE_RANGE = "Day"
    r = get_repository(repo)
    r_key: dict = {"url": r.url}
    await save_to_db(r, r_key)
    r_stats, pkg_stats = get_repostats(purl, repo, INTERVAL)
    r_stats_key: dict = {
        "url": r_stats.url,
        "stats_from": r_stats.stats_from,
        "stats_interval": r_stats.stats_interval,
    }
    pkg_stats_key: dict = {
        "purl": pkg_stats.purl,
        "stats_from": pkg_stats.stats_from,
        "stats_interval": pkg_stats.stats_interval,
    }
    await save_to_db(r_stats, r_stats_key)
    await save_to_db(pkg_stats, pkg_stats_key)


if __name__ == "__main__":
    async def main():
        await create_engine()

        INTERVAL: DATE_RANGE = "Day"
        d = "pypi"

        async for purl, url in iterate_packages(d):
            gh = Github(auth=Auth.Token(os.environ["GITHUB_TOKEN"]))
            try:
                repo = gh.get_repo(extract_repo_path(url))
                # print(repo)
            except Exception as e:
                logger.error(e)
                continue
            r = get_repository(repo)
            r_key: dict = {"url": r.url}
            await save_to_db(r, r_key)
            r_stats, pkg_stats = get_repostats(purl, repo, INTERVAL)
            r_stats_key: dict = {
                "url": r_stats.url,
                "stats_from": r_stats.stats_from,
                "stats_interval": r_stats.stats_interval,
            }
            pkg_stats_key: dict = {
                "purl": pkg_stats.purl,
                "stats_from": pkg_stats.stats_from,
                "stats_interval": pkg_stats.stats_interval,
            }
            await save_to_db(r_stats, r_stats_key)
            await save_to_db(pkg_stats, pkg_stats_key)

    asyncio.run(main())
