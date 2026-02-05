import os
import time
import httpx
from typing import List, Dict, Optional
from github import Github, Auth
from github.GithubException import RateLimitExceededException, GithubException
from dataclasses import dataclass
from tqdm import tqdm
from datetime import datetime

from pkgdash.models.connector.mongo import create_engine
from pkgdash.models.database.package import Package
from pkgdash.models.database.repository import Repository
from pkgdash.analyze.pypi.utils import extract_repo_path, GITHUB_PATTERN

@dataclass
class SimilarRepo:
    name: str
    url: str
    stars: int
    description: Optional[str]
    topics: List[str]
    source: str  # "github_topics", "oss_insight", etc.


class GitHubSimilarFinder:
    
    def __init__(self):
        self.gh = Github(auth=Auth.Token(""))
    
    def check_rate_limit(self):
        rate_limit = self.gh.get_rate_limit()
        core = rate_limit.core
        search = rate_limit.search
        
        if core.remaining < 10:
            reset_time = core.reset.timestamp()
            wait_seconds = max(0, reset_time - time.time()) + 60  # 多等60秒确保重置
            tqdm.write(f"\n⚠️  Core API rate limit reached! Remaining: {core.remaining}")
            tqdm.write(f"   Reset at: {core.reset.strftime('%Y-%m-%d %H:%M:%S')}")
            tqdm.write(f"   Waiting {wait_seconds/60:.1f} minutes...")
            time.sleep(wait_seconds)
            tqdm.write("   ✅ Resumed!\n")
        
        if search.remaining < 5:
            reset_time = search.reset.timestamp()
            wait_seconds = max(0, reset_time - time.time()) + 60
            tqdm.write(f"\n⚠️  Search API rate limit reached! Remaining: {search.remaining}")
            tqdm.write(f"   Reset at: {search.reset.strftime('%Y-%m-%d %H:%M:%S')}")
            tqdm.write(f"   Waiting {wait_seconds/60:.1f} minutes...")
            time.sleep(wait_seconds)
            tqdm.write("   ✅ Resumed!\n")
    
    def _retry_on_error(self, func, max_retries=3, delay=5):
        last_exception = None
        for attempt in range(max_retries):
            try:
                # 每次尝试前检查 rate limit
                self.check_rate_limit()
                return func()
            except RateLimitExceededException as e:
                tqdm.write(f"\n⚠️  Rate limit exceeded, waiting for reset...")
                self.check_rate_limit()
                # 重试
                continue
            except GithubException as e:
                if e.status == 403 and "rate limit" in str(e).lower():
                    tqdm.write(f"\n⚠️  Rate limit hit (403), waiting...")
                    self.check_rate_limit()
                    continue
                elif e.status == 404:
                    # 仓库不存在，不需要重试
                    return None
                elif e.status >= 500:
                    # 服务器错误，等待后重试
                    last_exception = e
                    tqdm.write(f"   Server error ({e.status}), retry {attempt + 1}/{max_retries}...")
                    time.sleep(delay * (attempt + 1))
                    continue
                else:
                    raise
            except (httpx.TimeoutException, httpx.ConnectError, ConnectionError) as e:
                last_exception = e
                tqdm.write(f"   Network error, retry {attempt + 1}/{max_retries}...")
                time.sleep(delay * (attempt + 1))
                continue
            except Exception as e:
                last_exception = e
                if attempt < max_retries - 1:
                    tqdm.write(f"   Error: {e}, retry {attempt + 1}/{max_retries}...")
                    time.sleep(delay)
                continue
        
        if last_exception:
            raise last_exception
        return None
    
    async def find_similar(
        self, 
        repo_url: str, 
        limit: int = 10
    ) -> List[SimilarRepo]:
        if not GITHUB_PATTERN.match(repo_url):
            return []
        
        repo_path = extract_repo_path(repo_url)
        if not repo_path:
            return []
        
        results: List[SimilarRepo] = []
        
        results.extend(await self._find_by_topics(repo_path, limit))
        
        results.extend(await self._find_by_oss_insight(repo_path, limit))
        
        seen: set[str] = set()
        unique_results: List[SimilarRepo] = []
        for r in results:
            if r.name not in seen and r.name != repo_path:
                seen.add(r.name)
                unique_results.append(r)
        
        unique_results.sort(key=lambda x: x.stars, reverse=True)
        return unique_results[:limit]
    
    GENERIC_TOPICS = {
        "python", "javascript", "typescript", "java", "go", "rust", "c", "cpp", 
        "ruby", "php", "swift", "kotlin", "scala", "shell", "bash",
        "http", "api", "web", "cli", "tool", "tools", "library", "framework",
        "client", "server", "app", "application", "project", "awesome",
        "tutorial", "examples", "demo", "sample", "template", "boilerplate",
        "learn", "learning", "education", "course", "book", "documentation",
        "humans", "forhumans", "simple", "easy", "fast", "lightweight",
        "linux", "windows", "macos", "docker", "kubernetes", "aws", "azure", "gcp",
    }

    async def _find_by_topics(
        self, 
        repo_path: str, 
        limit: int
    ) -> List[SimilarRepo]:
        try:
            repo = self._retry_on_error(lambda: self.gh.get_repo(repo_path))
            if repo is None:
                return []
            
            topics = self._retry_on_error(lambda: repo.get_topics())
            if not topics:
                return []
            
            specific_topics = [t for t in topics if t.lower() not in self.GENERIC_TOPICS]
            
            if not specific_topics:
                repo_name = repo_path.split("/")[-1].lower()
                specific_topics = [t for t in topics if repo_name in t.lower() or t.lower() in repo_name]
            
            if not specific_topics:
                return []
            
            language = repo.language
            seen = set()
            similar = []
            
            for topic in specific_topics[:3]:
                query = f"topic:{topic}"
                if language:
                    query += f" language:{language}"
                
                try:
                    results = self._retry_on_error(
                        lambda q=query: self.gh.search_repositories(q, sort="stars", order="desc")
                    )
                    if results is None:
                        continue
                    
                    for r in results[:limit]:
                        if r.full_name != repo_path and r.full_name not in seen:
                            seen.add(r.full_name)
                            similar.append(SimilarRepo(
                                name=r.full_name,
                                url=r.html_url,
                                stars=r.stargazers_count,
                                description=r.description,
                                topics=[],
                                source="github_topics"
                            ))
                            if len(similar) >= limit:
                                break
                except Exception as e:
                    continue
                
                if len(similar) >= limit:
                    break
            similar.sort(key=lambda x: x.stars, reverse=True)
            return similar[:limit]
        except Exception as e:
            return []
    
    async def _find_by_oss_insight(
        self, 
        repo_path: str, 
        limit: int
    ) -> List[SimilarRepo]:
        """使用 OSS Insight API"""
        for attempt in range(3):
            try:
                url = f"https://api.ossinsight.io/v1/repos/{repo_path}/similar"
                
                async with httpx.AsyncClient(timeout=15) as client:
                    resp = await client.get(url)
                    
                    if resp.status_code == 429:  # Too Many Requests
                        time.sleep(60)
                        continue
                    
                    if resp.status_code != 200:
                        return []
                    
                    data = resp.json().get("data", [])
                    return [
                        SimilarRepo(
                            name=item.get("repo_name", ""),
                            url=f"https://github.com/{item.get('repo_name', '')}",
                            stars=item.get("stars", 0),
                            description=item.get("description"),
                            topics=[],
                            source="oss_insight"
                        )
                        for item in data[:limit]
                    ]
            except (httpx.TimeoutException, httpx.ConnectError) as e:
                if attempt < 2:
                    time.sleep(5 * (attempt + 1))
                    continue
                return []
            except Exception as e:
                return []
        return []

async def find_similar_repos(repo_url: str, limit: int = 10) -> List[SimilarRepo]:
    """查找相似仓库的便捷函数"""
    finder = GitHubSimilarFinder()
    return await finder.find_similar(repo_url, limit)

async def recommend_similar_packages(purl: str):
    """根据包的 repo_url 推荐相似包"""
    package = await Package.find_one({"purl": purl})
    print(f"Finding similar packages for: {package}")
    if not package or not package.repo_url:
        return []
    
    similar_repos = await find_similar_repos(package.repo_url, limit=5)
    
    recommendations = []
    for repo in similar_repos:
        print(f"Looking for package with repo URL: {repo.url}")
        pkg = await Package.find_one({"repo_url": repo.url})
        if pkg:
            recommendations.append({
                "purl": pkg.purl,
                "name": pkg.name,
                "repo": repo.url,
                "stars": repo.stars,
                "description": repo.description
            })
    
    return recommendations


async def update_all_repos_similar(skip_existing: bool = True):
    finder = GitHubSimilarFinder()
    
    rate_limit = finder.gh.get_rate_limit()
    print(f"GitHub API Rate Limit Status:")
    print(f"  Core: {rate_limit.core.remaining}/{rate_limit.core.limit} (reset at {rate_limit.core.reset})")
    print(f"  Search: {rate_limit.search.remaining}/{rate_limit.search.limit} (reset at {rate_limit.search.reset})")
    print()
    
    if skip_existing:
        repos = await Repository.find(
            {"$or": [
                {"similar_repos": {"$exists": False}},
                {"similar_repos": None}
            ]}
        ).to_list()
        total_all = await Repository.count()
        print(f"Found {len(repos)} repositories to process (skipping {total_all - len(repos)} already processed)")
    else:
        repos = await Repository.find_all().to_list()
        print(f"Found {len(repos)} repositories to process")
    
    if not repos:
        print("No repositories to process!")
        return
    
    success_count = 0
    skip_count = 0
    error_count = 0
    start_time = datetime.now()
    
    pbar = tqdm(repos, desc="Processing repos", unit="repo")
    for repo in pbar:
        pbar.set_postfix({
            "success": success_count,
            "skip": skip_count, 
            "error": error_count
        })
        
        if not repo.topics:
            repo.similar_repos = []
            await repo.save()
            skip_count += 1
            continue
        
        try:
            similar = await finder.find_similar(repo.url, limit=3)
            
            similar_urls = [s.url for s in similar]
            
            repo.similar_repos = similar_urls
            await repo.save()
            success_count += 1
            
        except RateLimitExceededException:
            tqdm.write(f"⚠️  Rate limit exception for {repo.url}, will retry after reset")
            finder.check_rate_limit()
            try:
                similar = await finder.find_similar(repo.url, limit=3)
                similar_urls = [s.url for s in similar]
                repo.similar_repos = similar_urls
                await repo.save()
                success_count += 1
            except Exception as e:
                tqdm.write(f"❌ Failed after retry: {repo.url}: {e}")
                repo.similar_repos = []
                await repo.save()
                error_count += 1
                
        except Exception as e:
            tqdm.write(f"❌ Error processing {repo.url}: {type(e).__name__}: {e}")
            repo.similar_repos = []
            await repo.save()
            error_count += 1
    
    elapsed = datetime.now() - start_time
    print(f"\n{'='*50}")
    print(f"✅ Completed!")
    print(f"   Time elapsed: {elapsed}")
    print(f"   Success: {success_count}")
    print(f"   Skipped (no topics): {skip_count}")
    print(f"   Errors: {error_count}")
    print(f"{'='*50}")


if __name__ == "__main__":
    import asyncio

    async def main():
        await create_engine()
        await update_all_repos_similar()
        
        # similar = await recommend_similar_packages(purl="pkg:pypi/requests@2.32.4")
        # for repo in similar:
        #     print(f"{repo['name']} - {repo['stars']} stars - {repo['repo']}")

    asyncio.run(main())
