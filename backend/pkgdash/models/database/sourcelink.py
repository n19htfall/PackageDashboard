from typing import Optional, List, Union, Literal
from datetime import datetime

from pydantic import BaseModel
from beanie import Document, Indexed
import pymongo

# defines a software package
class PackageSource(Document, BaseModel):
    """
    Defines a software package (can be rpm/npm/maven/etc.)
    This is not the result of the package scan
    """

    """
    PURL=scheme:type/namespace/name@version?qualifiers#subpath
    Spec: https://github.com/package-url/purl-spec
    """
    purl: Indexed(str, "hashed")
    """
    PURL of the dependency
    """
    repo_url: Indexed(str, "hashed")
    """
    The type of the sourcing link
    """
    type: str
    """
    The detection time of the dependency
    """
    sourced_at: datetime = datetime.utcnow()
    """
    The detection confidence
    """
    confidence: float = 1.0

    # create unique index on (purl, dep_purl)
    class Settings:
        indexes = [
            pymongo.IndexModel(
                [("purl", pymongo.ASCENDING), ("repo_url", pymongo.ASCENDING)],
                unique=True,
            )
        ]