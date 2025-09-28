import os
import asyncio
import json
import shutil

import requests
from packageurl import PackageURL

from pkgdash.models.connector.mongo import create_engine
from pymongo.errors import DuplicateKeyError
from pkgdash.analyze.utils import (
    _uncompress_if_gzip,
    _uncompress_if_tar,
    execute_command,
    _is_vcs_repo_url,
    _sanitize_vcs_url,
    check_license_validity,
)
from pkgdash.models.database.package import Package
from pkgdash.models.database.deplink import PackageDependency
from pkgdash.models.spdx_license import SPDXLicense
from github import Github
from github.Repository import Repository as GithubRepo
import re
import hashlib
import random

packages_dir = "/home/lzh/repo_url"
output_json_dir = "./pkgdash/analyze/github/output/"
download_dir = "./pkgdash/analyze/github/download/"


gh = Github(os.getenv("GITHUB_TOKEN"))

cnt = 0

GITHUB_PATTERN = re.compile(
    r"^(https?://)?(www\.)?github\.com/([a-zA-Z0-9_.-]+)/([a-zA-Z0-9_.-]+)/?$"
)


def extract_repo_path(github_url):
    match = re.search(r"github\.com/([^/]+/[^/]+)", github_url)
    if match:
        return match.group(1)
    return None


def compute_sha1(file_path):
    """计算文件的SHA1哈希"""
    sha1 = hashlib.sha1()
    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            sha1.update(chunk)
    return sha1.hexdigest()


def get_all_files(folder_path):
    """递归地从文件夹中随机选择k个文件"""
    all_files = []
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            all_files.append(os.path.join(root, file))
    return all_files


def get_files_from_repo(repo):
    """从GitHub仓库中获取一定数量的文件并计算SHA1哈希"""
    all_files = []
    for content in repo.get_contents(""):
        if content.type == "file":
            file_content = content.decoded_content
            sha1_hash = compute_sha1(file_content)
            all_files.append((content.path, sha1_hash))
    return all_files


def calculate_similarity(hashes1, hashes2):
    """计算两个文件哈希集合的相似度（使用Jaccard相似度）"""
    set1 = set(hashes1)
    set2 = set(hashes2)
    intersection = set1.intersection(set2)
    union = set1.union(set2)
    return len(intersection) / len(union) if union else 0


def get_npm_package_info(package_name: str, package_namespace: str | None = None) -> dict | None:
    # 构建npm registry API的URL
    if package_namespace is None:
        url = f"https://registry.npmjs.org/{package_name}"
    else:
        url = f"https://registry.npmjs.org/{package_namespace}/{package_name}"

    # 发送GET请求
    response = requests.get(url)

    # 检查请求是否成功
    if response.status_code == 200:
        # 解析JSON响应
        package_info = response.json()

        # 获取repository和homepage信息
        repository = package_info.get("repository", {})
        homepage = package_info.get("homepage", "")

        return {"pkg": package_name, "repo_url": repository, "homepage": homepage}
    else:
        print(f"Error: Unable to fetch package information. Status code: {response.status_code}")
        return None


async def analyze(packages_dir: str, save_to_db: bool = True) -> None:
    packages_path = packages_dir + ("/" if packages_dir[-1] != "/" else "")
    url_mp = {}

    async def process_package(p: str, save_to_db: bool) -> None:
        try:
            global cnt
            print(f"Processing {p} : {cnt}")
            cnt += 1
            files_to_be_removed = []
            filename = p.split("/")[-1].replace(".tar.gz", "").replace(".tar.bz2", "")
            tar_path = _uncompress_if_gzip(p)
            files_to_be_removed += [tar_path]
            package_path = _uncompress_if_tar(tar_path)
            files_to_be_removed += [package_path]
            entries = os.listdir(package_path)
            if len(entries) == 1 and os.path.isdir(os.path.join(package_path, entries[0])):
                package_path = os.path.join(package_path, entries[0])
            output_json_path = output_json_dir + f"{filename}.json"
            if not os.path.exists(output_json_path):
                execute_command(f"scancode -p --json-pp {output_json_path} {package_path}")
            output_json = json.load(open(output_json_path, "r", encoding="utf-8"))
            i = 0
            try:
                while (
                    output_json["packages"][i]["type"] != "npm"
                    and output_json["packages"][i]["type"] != "pypi"
                ):
                    i += 1
                package_info_json = output_json["packages"][i]
                pacakge_name = package_info_json["name"]
                vcs_url = _sanitize_vcs_url(package_info_json["vcs_url"])
                code_view_url = _sanitize_vcs_url(package_info_json["code_view_url"])
                homepage_url = _sanitize_vcs_url(package_info_json["homepage_url"])
                url = vcs_url or code_view_url or homepage_url
                if url and GITHUB_PATTERN.match(url):
                    gh_url = extract_repo_path(url)
                    repo: GithubRepo = gh.get_repo(gh_url)
                    url = repo.html_url
                elif url is None:
                    local_sha1_lst = []
                    selected_files = get_all_files(package_path)
                    for file in selected_files:
                        sha1_hash = compute_sha1(file)
                        local_sha1_lst += [sha1_hash]
                    repositories = gh.search_repositories(
                        query=pacakge_name, sort="stars", order="desc"
                    )
                    k = 5
                    top_k_repos = []
                    for idx, repo in enumerate(repositories):
                        if idx >= k:
                            break
                        top_k_repos.append(repo)
                    if top_k_repos:
                        res = []
                        download_repo_dir = download_dir + pacakge_name + "/"
                        if not os.path.exists(download_repo_dir):
                            os.mkdir(download_repo_dir)
                        for repo in top_k_repos:
                            repo_sha1 = []
                            execute_command(f"git clone {repo.html_url}.git", download_repo_dir)
                            selected_files2 = get_all_files(download_repo_dir + repo.name)
                            for file in selected_files2:
                                sha1_hash = compute_sha1(file)
                                repo_sha1 += [sha1_hash]
                            res += [
                                (repo.html_url, calculate_similarity(local_sha1_lst, repo_sha1))
                            ]
                        sorted_res = sorted(res, key=lambda x: x[1], reverse=True)
                        url = sorted_res[0][0]
                url_mp[package_path] = url
            except IndexError as e:
                return

        except Exception as e:
            print("Error: ", e)

    tasks = [
        process_package(packages_path + p, save_to_db)
        for p in os.listdir(packages_path)
        if p.endswith(".tar.gz") or p.endswith(".tar.bz2")
    ]
    await asyncio.gather(*tasks)

    with open("res.json", "w") as f:
        json.dump(url_mp, f, indent=4)


if __name__ == "__main__":

    async def main():
        await create_engine()
        await analyze(packages_dir, save_to_db=False)

    asyncio.run(main())
