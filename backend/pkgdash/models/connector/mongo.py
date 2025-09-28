from pydantic import BaseModel
import os
import asyncio
from beanie import Document, init_beanie
from motor.motor_asyncio import AsyncIOMotorClient

from pkgdash import settings
from ..database.package import Package, PackageStats, PackageVulns
from ..database.repository import Repository, RepositoryStats
from ..database.osrepo import OSPackageRepository
from ..database.deplink import PackageDependency
from ..database.sourcelink import PackageSource

_ORM_MODELS = [Package, Repository, PackageStats, RepositoryStats, OSPackageRepository, 
               PackageDependency, PackageSource, PackageVulns]

async def create_engine() -> AsyncIOMotorClient:
    """
    Creates a new motor engine
    """
    client = AsyncIOMotorClient(settings.mongodb.url)
    _db = client[settings.mongodb.db]

    # Beanie initialization. This will create indexes
    await init_beanie(_db, document_models=_ORM_MODELS)

    return client


if __name__ == '__main__':
    async def main():
        await create_engine()

    asyncio.run(main())