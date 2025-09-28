from typing import Optional, List, Union, Literal
from datetime import datetime

from pydantic import BaseModel
from beanie import Document, Indexed
import pymongo

# defines a software package
class PackageDependency(Document, BaseModel):
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
    Only for OS packages
    """
    pkgid: Optional[int]
    
    """
    PURL of the dependency
    """
    dep_purl: Indexed(str, "hashed")
    """
    Only for OS Packages
    """
    dep_pkgid: Optional[int]

    """
    The type of the dependency
    """
    type: str
    """
    The constriant of the dependency
    """
    constraint: Optional[str]
    """
    The detection time of the dependency
    """
    dep_at: datetime = datetime.utcnow()

    # create unique index on (purl, dep_purl)
    class Settings:
        indexes = [
            pymongo.IndexModel(
                [("purl", pymongo.ASCENDING), ("dep_purl", pymongo.ASCENDING)],
                unique=True,
            )
        ]