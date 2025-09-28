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


def _uncompress_if_gzip(path: os.PathLike) -> str:
    """
    Uncompresses a file xxx.gz/.bz2 into xxx; return uncompressed file path
    """
    if path.endswith('.gz'):
        import gzip
        with gzip.open(path, 'rb') as f_in:
            with open(path[:-3], 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        return path[:-3]
    elif path.endswith('.bz2'):
        import bz2
        with bz2.open(path, 'rb') as f_in:
            with open(path[:-4], 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        return path[:-4]
    elif path.endswith('.xz'):
        import lzma
        with lzma.open(path, 'rb') as f_in:
            with open(path[:-3], 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        return path[:-3]
    else:
        return path


def _generate_purl_from_rpm(d) -> str:
    return (
        f"pkg:rpm/{quote_plus(d['distro'])}/{quote_plus(d['name'])}"
        f"@{quote_plus(d['version'])}-{quote_plus(d['release'])}?"
        f"arch={quote_plus(d['arch'])}&epoch={quote_plus(d['epoch'])}"
        f"&distro={quote_plus(d['distro'])}-{quote_plus(d['distro_release'])}"
    )

RPM_PATTERN = re.compile(r'^([a-zA-Z0-9_\-]+|[a-zA-Z0-9\.]+)-(v?[0-9\.].+)\.src\.rpm$')
def _generate_source_purl_from_rpm(d, source_rpm) -> str:
    """
    Generates a PURL for the source RPM (openstack-tempest-27.0.0-2.oe2203sp1.src.rpm -> pkg:rpm/openeuler/python3-tempest-tests@27.0.0-2.oe2203sp1?arch=noarch&epoch=0&distro=openeuler-22.04)
    """
    _captured = None
    try:
        _captured = re.match(RPM_PATTERN, source_rpm).groups()
        assert len(_captured) == 2
    except Exception as e:
        # give it another try
        version = d['version']
        if version in source_rpm:
            _captured = (source_rpm[:source_rpm.index(version) - 1], source_rpm[source_rpm.index(version):])
        else:
            logger.error(f"Invalid source RPM name: {source_rpm}")
            raise e
    name = _captured[0]
    version = _captured[1]
    return (
        f"pkg:rpm/{quote_plus(d['distro'])}/{quote_plus(name)}"
        f"@{quote_plus(version)}?"
        f"arch=src&epoch={quote_plus(d['epoch'])}"
        f"&distro={quote_plus(d['distro'])}-{quote_plus(d['distro_release'])}"
    )

VCS_PATTERN = re.compile(r'^(https?://)?(www\.)?(github|gitee|bitbucket|gitlab)\.com/([a-zA-Z0-9_.-]+)/([a-zA-Z0-9_.-]+)/?$')

def _is_vcs_repo_url(url: str or None) -> bool:
    """
    Checks if a URL is a GitHub/Gitee/Bitbucket/GitLab repo URL
    """
    return url and VCS_PATTERN.match(url) is not None

async def import_rpm_sqlite(path: os.PathLike, distro='openeuler', release='22.04') -> None:
    """
    Imports RPM data from a sqlite database
    """
    sqlite_path = _uncompress_if_gzip(path)
    con = sqlite3.connect(sqlite_path)
    con.row_factory = sqlite3.Row

    cur = con.cursor()
    cur.execute("SELECT * FROM packages")
    res = cur.fetchall()
    logger.info(f"Importing {len(res)} packages from {sqlite_path}")

    async with BulkWriter() as writer:
        for rpkg in res:
            rpkg = dict(**rpkg, distro=distro, distro_release=release)
            purl = _generate_purl_from_rpm(rpkg)
            
            pkg = await Package.find_one({'purl': purl}) or \
                Package(purl=purl, name=rpkg['name'], version=rpkg['version'])
            pkg.record_updated_at = datetime.now()

            pkg.version = rpkg['version']
            pkg.summary = rpkg['summary']
            pkg.description = rpkg['description'] if rpkg['description'] else rpkg['summary']
            pkg.license = rpkg['rpm_license']
            pkg.homepage_url = rpkg['url']

            if _is_vcs_repo_url(rpkg['url']):
                pkg.repo_url = rpkg['url']

            pkg.arch = rpkg['arch']
            if rpkg['rpm_sourcerpm']:
                pkg.source_pid = rpkg['rpm_sourcerpm']
                try:
                    pkg.source_purl = _generate_source_purl_from_rpm(rpkg, rpkg['rpm_sourcerpm'])
                except:
                    pass

            pkg.distro = rpkg['distro']
            pkg.distro_release = rpkg['distro_release']
            await pkg.save(bulk_writer=writer)

    con.close()


if __name__ == "__main__":
    import asyncio

    from pkgdash.fetch.rpm.meta import download_rpm_all_meta
    from pkgdash.models.connector.mongo import create_engine
    from pkgdash.models.database.osrepo import OSPackageRepository

    async def main():
        await create_engine()
        for d, url in dict(settings.os_repo).items():
            distro, release = d.split('-')
            files = await download_rpm_all_meta(url)
            logger.info(f"Downloaded {len(files)} files from {d}")
            for f in files:
                if 'primary.sqlite' in f:
                    await import_rpm_sqlite(f, distro=distro, release=release)

            repo = await OSPackageRepository.find_one({'name': d}) or \
                OSPackageRepository(name=d, url=url, distro=distro, distro_release=release)
            repo.record_updated_at = datetime.now()

            repo.files = files
            _archs = await Package.distinct('arch', {'distro': distro, 'distro_release': release})
            for ign in 'src', 'noarch', 'i686':
                if ign in _archs:
                    _archs.remove(ign)
            repo.archs = _archs
            await repo.save()

    asyncio.run(main())