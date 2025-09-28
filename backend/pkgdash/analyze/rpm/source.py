import os
import shutil
import re
import sqlite3
from urllib.parse import quote_plus
from datetime import datetime

from beanie import BulkWriter
from beanie.odm.operators.update.general import Set

from pkgdash import settings, logger
from pkgdash.models.database.package import Package

GITHUB_PATTERN = re.compile(r'^(https?://)?(www\.)?github\.com/([a-zA-Z0-9_.-]+)/([a-zA-Z0-9_.-]+)/?$')
def _sanitize_github_url(url: str) -> str:
    if 'www.' in url:
        url = url.replace('www.', '')
    if url.endswith('/'):
        url = url[:-1]
    if url.startswith('http://'):
        url = url.replace('http://', 'https://')
    if url.endswith('.git'):
        url = url[:-4]
    return url

if __name__ == "__main__":
    import asyncio

    from pkgdash.fetch.rpm.meta import download_rpm_all_meta
    from pkgdash.models.connector.mongo import create_engine
    from pkgdash.models.database.sourcelink import PackageSource

    async def main():
        await create_engine()
        async with BulkWriter() as bulk_writer:
            async for pkg in Package.find_all():
                if pkg.repo_url and GITHUB_PATTERN.match(pkg.repo_url):
                    record = PackageSource(
                        purl=pkg.purl,
                        repo_url=_sanitize_github_url(pkg.repo_url),
                        type='rpm',
                    )
                    await record.save(bulk_writer=bulk_writer)
    asyncio.run(main())