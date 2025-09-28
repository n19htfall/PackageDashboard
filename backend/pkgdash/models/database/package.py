from typing import Optional, List, Union, Literal
from datetime import datetime, timezone

from pydantic import BaseModel
from beanie import Document, Indexed
import pymongo

from ..spdx_license import SPDXLicense
from pkgdash.common import DATE_RANGE


# defines a software package
class Package(Document, BaseModel):
    """
    Defines a software package (can be rpm/npm/maven/etc.)
    This is not the result of the package scan
    """

    """
    PURL=scheme:type/namespace/name@version?qualifiers#subpath
    Spec: https://github.com/package-url/purl-spec
    """
    purl: Indexed(str, unique=True)
    """The display name of the package"""
    name: str
    """Package Version"""
    version: Optional[str]
    """A shorter description (optional)"""
    summary: Optional[str]
    """Description"""
    description: Optional[str]
    """Package License (SPDX Format)"""
    license: Optional[str]
    """HomePage URL"""
    homepage_url: Optional[str]
    """Repo URL defined in package metadata"""
    repo_url: Optional[str]
    """Source package purl (if different from binary)"""
    source_purl: Optional[str]

    """OS Distro"""
    distro: Optional[str]
    distro_release: Optional[str]
    arch: Optional[str]
    """Source Package Identifier (e.g. RPM Source RPM)"""
    source_pid: Optional[str]

    """Metadata"""
    record_created_at: datetime = datetime.utcnow()
    record_updated_at: datetime = datetime.utcnow()


class PackageStats(Document, BaseModel):
    """The calculated statistics of a repository"""

    """
    PURL=scheme:type/namespace/name@version?qualifiers#subpath
    Spec: https://github.com/package-url/purl-spec
    """
    purl: Indexed(str, "hashed")
    """The date range of the statistics"""
    stats_from: datetime
    stats_interval: DATE_RANGE

    """Metadata"""
    record_created_at: datetime = datetime.utcnow()
    record_updated_at: datetime = datetime.utcnow()

    """The number of commits / comments / issues / prs / stars / tags in the date range"""
    n_commits: int
    n_comments: int
    n_issues: int
    n_prs: int
    n_stars: int
    n_tags: int

    """Compound Metrics"""
    pagerank: Optional[float]

    # create unique index on (url, stats_from, stats_interval)
    class Settings:
        indexes = [
            pymongo.IndexModel(
                [
                    ("purl", pymongo.ASCENDING),
                    ("stats_from", pymongo.ASCENDING),
                    ("stats_interval", pymongo.ASCENDING),
                ],
                unique=True,
            )
        ]


class PackageVulns(Document, BaseModel):
    purl: Indexed(str, "hashed")
    repo_url: Indexed(str, "hashed")
    name: str
    version: str
    commit_sha: Optional[str] = None
    vulns: List[str] = []
    n_contributors: Optional[int] = None
    is_archived: Optional[bool] = None
    license_compatibility: Optional[int] = None

    """Metadata"""
    record_created_at: datetime = datetime.now(timezone.utc)
    record_updated_at: datetime = datetime.now(timezone.utc)

    # create unique index on (purl, dep_purl)
    class Settings:
        indexes = [
            pymongo.IndexModel(
                [("purl", pymongo.ASCENDING), ("repo_url", pymongo.ASCENDING)],
                unique=True,
            )
        ]
