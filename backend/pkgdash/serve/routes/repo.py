from typing import List

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from pkgdash import settings, logger

from fastapi_pagination import Page, paginate, Params
from fastapi_pagination.ext.beanie import paginate as paginate_beanie

from pkgdash.models import Package, PackageStats, Repository, RepositoryStats, PackageDependency, PackageSource

api = APIRouter()

@api.get("/list", response_model=Page[Repository])
async def list_repositories(p: Params = Depends()):
    """List all prepositories"""
    return await paginate_beanie(Repository.find_all(), params=p)

@api.get("/search", response_model=Page[Repository])
async def search_repositories(q: str, p: Params = Depends()):
    """Search for repositories"""
    return await paginate_beanie(Repository.find_many({"name": {"$regex": q}}), params=p)

@api.get("/info", response_model=Repository)
async def get_repository_info(url: str):
    """Get repository info"""
    res = await Repository.find_one({"url": url})
    if not res:
        raise HTTPException(status_code=404, detail=f"No information for {url}")
    return res

@api.get("/stats", response_model=List[RepositoryStats])
async def get_repository_stats(url: str):
    """Get repository stats"""
    res = await RepositoryStats.find_many({"url": url}).sort("stats_from").to_list()
    if not res:
        raise HTTPException(status_code=404, detail=f"No statistics for {url}")
    return res

@api.get("/packages", response_model=List[PackageSource])
async def get_repository_packages(url: str):
    """Get repository packages"""
    res = await PackageSource.find_many({"repo_url": url}).to_list()
    # distinct on purl
    res = list({v.purl :v for v in res}.values())
    if not res:
        raise HTTPException(status_code=404, detail=f"No associated packages for {url}")
    return res

@api.get("/rec", response_model=List[Package])
async def get_similar_packages(url: str):
    repo = await Repository.find_one({"url": url})
    res:List[Package] = []
    for repo_url in repo.similar_repos:
        pkg = await Package.find_one({"repo_url": repo_url})
        if pkg:
            res += [pkg]
    return res