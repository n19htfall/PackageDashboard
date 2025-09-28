from typing import Optional, List, Union, Literal
from datetime import datetime, timezone

from pydantic import BaseModel
from beanie import Document, Indexed
import pymongo

from pkgdash.common import DATE_RANGE


class Repository(Document, BaseModel):
    """
    Defines a software repository from code-hosting sites (e.g. github.com, gitee.com)
    Data from API goes here
    """

    """The url of the repository"""
    url: Indexed(str, unique=True)
    """The display name of the package"""
    name: str

    """Statistics"""
    n_stars: int
    created_at: datetime
    updated_at: datetime
    pushed_at: datetime
    archived_at: Optional[datetime]
    is_template: bool
    is_fork: bool
    primary_language: Optional[str]
    topics: List[str] = []
    description: Optional[str]

    """License Info from GitHub API, should be SPDX compatible"""
    license: Optional[str]

    """Metadata"""
    record_created_at: datetime = datetime.now(timezone.utc)
    record_updated_at: datetime = datetime.now(timezone.utc)


# Pydantic model for Repository
# class Repository(Document, BaseModel):
#     """
#     Defines a software repository from code-hosting sites (e.g. github.com, gitee.com)
#     Data from API goes here
#     """

#     """The url of the repository"""
#     url: Indexed(str, unique=True)
#     """The display name of the package"""
#     name: str

#     """Statistics"""
#     n_stars: int
#     n_commits: int
#     n_comments: int
#     n_issues: int
#     n_prs: int
#     n_tags: int
#     created_at: datetime
#     updated_at: datetime
#     pushed_at: datetime
#     is_archived: bool
#     archived_at: Optional[datetime] = None
#     is_template: bool
#     is_fork: bool
#     primary_language: Optional[str] = None
#     topics: List[str] = []
#     description: Optional[str] = None

#     """License Info from GitHub API, should be SPDX compatible"""
#     license: Optional[str] = None

#     """Metadata"""
#     record_created_at: datetime = datetime.now(timezone.utc)
#     record_updated_at: datetime = datetime.now(timezone.utc)


# still deciding whether to cache the stats or calculate from ch on-demand
class RepositoryStats(Document, BaseModel):
    """The calculated statistics of a repository"""

    """The go-style repository URL, e.g. github.com/pkgdeps/pkgdeps"""
    url: Indexed(str, "hashed")
    """The date range of the statistics"""
    stats_from: datetime
    stats_interval: DATE_RANGE

    """The number of commits / comments / issues / prs / stars / tags in the date range"""
    n_commits: int
    n_comments: int
    n_issues: int
    n_prs: int
    n_stars: int
    n_tags: int

    """Metadata"""
    record_created_at: datetime = datetime.now(timezone.utc)
    record_updated_at: datetime = datetime.now(timezone.utc)

    """Compound Metrics"""
    hits: Optional[float]
    hits_rank_pct: Optional[float]
    hits_zscore: Optional[float]

    # create unique index on (url, stats_from, stats_interval)
    class Settings:
        indexes = [
            pymongo.IndexModel(
                [
                    ("url", pymongo.ASCENDING),
                    ("stats_from", pymongo.ASCENDING),
                    ("stats_interval", pymongo.ASCENDING),
                ],
                unique=True,
            )
        ]
