import asyncio
from github import Github
from github.Repository import Repository as GithubRepo
import os
import logging
import json
from pkgdash.models.database.package import PackageStats, Package
from pkgdash.models.database.repository import Repository, RepositoryStats
from pkgdash.models.database.sourcelink import PackageSource
from datetime import datetime
from typing import AsyncGenerator, Tuple
from zoneinfo import ZoneInfo
from pkgdash.models.connector.mongo import create_engine
from packageurl import PackageURL
import argparse

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# SPDX license map
# with open("license_map.json", "r") as file:
#     license_map: dict = json.load(file)


async def iterate_packages() -> AsyncGenerator[Tuple[str, str], None]:
    async for package in Package.find_all():
        if package.repo_url:
            yield package.purl, package.repo_url


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


if __name__ == "__main__":
    distro = "pypi"
    
    async def main():
        await create_engine()

        async for purl, url in iterate_packages():
            t = PackageURL.from_string(purl).type
            if t != distro:
                continue
            if url:
                await save_sourcelink(purl, url)

    asyncio.run(main())
