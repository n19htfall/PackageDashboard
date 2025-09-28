from typing import Optional, List, Union, Literal
from datetime import datetime

from pydantic import BaseModel
from beanie import Document, Indexed

class OSPackageRepository(Document, BaseModel):
    """
    Defines a software package (can be rpm/npm/maven/etc.)
    This is not the result of the package scan
    """

    name: Indexed(str, unique=True)
    """The base url of the package"""
    url: str

    """OS Distro"""
    distro: Optional[str]
    distro_release: Optional[str]
    archs: List[str] = []
    files: List[str] = []

    """Metadata"""
    record_created_at: datetime = datetime.utcnow()
    record_updated_at: datetime = datetime.utcnow()