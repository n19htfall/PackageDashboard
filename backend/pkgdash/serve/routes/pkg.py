import re

from pkgdash import settings, logger
from collections import deque
from typing import List, Set

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from fastapi_pagination import Page, paginate, Params
from fastapi_pagination.ext.beanie import paginate as paginate_beanie
from pymongo.errors import OperationFailure
from packageurl import PackageURL
from queue import Queue

from pkgdash.models import (
    Package,
    PackageStats,
    Repository,
    RepositoryStats,
    PackageDependency,
    PackageSource,
    PackageVulns,
)


api = APIRouter()


@api.get("/list", response_model=Page[Package])
async def list_packages(p: Params = Depends()):
    """List all packages"""
    return await paginate_beanie(Package.find_all(), params=p)


@api.get("/search", response_model=Page[Package])
async def search_packages(q: str, p: Params = Depends(), distros: List[str] = Query(None)):
    """Search for packages"""
    try:
        if not distros:
            return await paginate_beanie(Package.find_many({"purl": {"$regex": q}}), params=p)
        else:
            return await paginate_beanie(
                Package.find_many({"purl": {"$regex": q}, "distro": {"$in": distros}}),
                params=p,
            )
    except OperationFailure as e:
        # invalid regex
        raise HTTPException(status_code=400, detail=str(e))


@api.get("/info", response_model=Package)
async def get_package_info(purl: str):
    """Get package info"""
    purl = purl.replace("%40", "@")
    purl_obj = PackageURL.from_string(purl)
    purl = purl_obj.to_string()
    res = await Package.find_one({"purl": {"$regex": f"^{re.escape(purl)}"}})
    if not res:
        raise HTTPException(status_code=404, detail=f"No information for {purl}")
    return res


@api.get("/stats", response_model=List[PackageStats])
async def get_package_stats(purl: str):
    """Get package stats"""
    purl = purl.replace("%40", "@")
    purl_obj = PackageURL.from_string(purl)
    purl = purl_obj.to_string()
    res = (
        await PackageStats.find_many({"purl": {"$regex": f"^{re.escape(purl)}"}})
        .sort("stats_from")
        .to_list()
    )
    if not res:
        raise HTTPException(status_code=404, detail=f"No statistics for {purl}")
    return res


@api.get("/deps", response_model=List[PackageDependency])
async def get_package_deps(purl: str):
    """Get package dependencies"""
    purl = purl.replace("%40", "@")
    purl_obj = PackageURL.from_string(purl)
    purl = purl_obj.to_string()
    res = await PackageDependency.find_many({"purl": {"$regex": f"^{re.escape(purl)}"}}).to_list()
    if not res:
        raise HTTPException(status_code=404, detail=f"No dependencies for {purl}")
    return res


@api.get("/tdeps", response_model=List[PackageDependency])
async def get_package_tdeps(purl: str):
    """Get package dependencies"""
    purl = purl.replace("%40", "@")
    purl_obj = PackageURL.from_string(purl)
    canonical_purl = purl_obj.to_string()
    all_dependencies: dict[tuple[str, str], Set[PackageDependency]] = {}
    processed_purls: Set[str] = set()  # 记录已处理过的 PURL，防止无限循环
    dep_queue: deque[PackageDependency] = deque()  # 使用 deque
    try:
        initial_deps = await get_package_deps(canonical_purl)
        processed_purls.add(canonical_purl)
        for dep in initial_deps:
            dep_queue.append(dep)
            rel_key = (dep.purl, dep.dep_purl)
            if rel_key not in all_dependencies:
                all_dependencies[rel_key] = dep
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch initial dependencies for {canonical_purl}"
        )
    print(dep_queue)
    while dep_queue:  # 使用 deque 的布尔值判断是否为空
        current_dep: PackageDependency = dep_queue.popleft()  # 从左侧取出 (FIFO)
        try:
            # 获取当前依赖的直接依赖
            if current_dep.dep_purl in processed_purls:
                continue
            deps_of_current = await get_package_deps(current_dep.dep_purl)
            processed_purls.add(current_dep.dep_purl)
            for next_dep in deps_of_current:
                rel_key = (next_dep.purl, next_dep.dep_purl)
                if rel_key not in all_dependencies:
                    all_dependencies[rel_key] = next_dep
                dep_queue.append(next_dep)  # 加入队列等待处理
        except Exception as e:
            continue
    result_list = list(all_dependencies.values())
    return result_list


@api.get("/rdeps", response_model=List[PackageDependency])
async def get_package_rdeps(purl: str):
    """Get package dependents"""
    purl = purl.replace("%40", "@")
    purl_obj = PackageURL.from_string(purl)
    purl = purl_obj.to_string()
    res = await PackageDependency.find_many(
        {"dep_purl": {"$regex": f"^{re.escape(purl)}"}}
    ).to_list()
    if not res:
        raise HTTPException(status_code=404, detail=f"No dependents {purl}")
    return res


@api.get("/sources", response_model=List[PackageSource])
async def get_package_sources(purl: str):
    """Get package repository"""
    purl = purl.replace("%40", "@")
    purl_obj = PackageURL.from_string(purl)
    purl = purl_obj.to_string()
    res = await PackageSource.find_many({"purl": {"$regex": f"^{re.escape(purl)}"}}).to_list()
    # distinct on repo_url
    res = list({v.repo_url: v for v in res}.values())
    if not res:
        raise HTTPException(status_code=404, detail=f"No associated repositories for {purl}")
    return res


@api.get("/distros", response_model=List[str])
async def get_package_distros():
    """Get package distros"""
    return [d for d in await Package.distinct("distro") if d is not None]


@api.get("/alerts", response_model=PackageVulns)
async def get_package_alert(purl: str):
    """Get package alerts"""
    purl = purl.replace("%40", "@")
    purl_obj = PackageURL.from_string(purl)
    purl = purl_obj.to_string()
    print(purl)
    res = await PackageVulns.find_one({"purl": {"$regex": f"^{re.escape(purl)}"}})
    if not res:
        raise HTTPException(status_code=404, detail=f"No associated alerts for {purl}")
    return res
