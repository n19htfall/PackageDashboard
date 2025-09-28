import shutil
import tarfile
import subprocess
import re
import io
import json
import sys
import os
import requests
from requests.exceptions import RequestException
from pkgdash.models.spdx_license import SPDXLicense
from urllib.parse import urljoin, urlparse
from typing import List
from contextlib import redirect_stdout


def _uncompress_if_gzip(path: str) -> str:
    """
    Uncompresses a file xxx.gz/.bz2 into xxx; return uncompressed file path
    """
    if path.endswith(".gz"):
        import gzip

        with gzip.open(path, "rb") as f_in:
            with open(path[:-3], "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)
        return path[:-3]
    elif path.endswith(".bz2"):
        import bz2

        with bz2.open(path, "rb") as f_in:
            with open(path[:-4], "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)
        return path[:-4]
    elif path.endswith(".xz"):
        import lzma

        with lzma.open(path, "rb") as f_in:
            with open(path[:-3], "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)
        return path[:-3]
    else:
        return path


def _uncompress_if_tar(path: str) -> str:
    if path.endswith(".tar"):
        extract_path = path[:-4]
        with tarfile.open(path, "r") as tar:
            tar.extractall(path=extract_path)
            return extract_path
    else:
        return path


def execute_command(command: str):
    try:
        subprocess.run(command, capture_output=True, text=True, shell=True)
    except Exception as e:
        return f"Error: {e}"


VCS_PATTERN = re.compile(
    r"^(https?://)?(www\.)?(github|gitee|bitbucket|gitlab)\.com/([a-zA-Z0-9_.-]+)/([a-zA-Z0-9_.-]+)/?$"
)


def _is_vcs_repo_url(url: str | None) -> bool:
    """
    Checks if a URL is a GitHub/Gitee/Bitbucket/GitLab repo URL
    """
    return url and VCS_PATTERN.match(url) is not None


def check_license_validity(license_expression: str) -> bool:
    try:
        SPDXLicense(license_expression)
        return True
    except ValueError:
        return False


GITHUB_PATTERN = re.compile(
    r"^(https?://)?(www\.)?github\.com/([a-zA-Z0-9_.-]+)/([a-zA-Z0-9_.-]+)/?$"
)


def _sanitize_vcs_url(url: str | None) -> str | None:
    if url is None:
        return None
    if "www." in url:
        url = url.replace("www.", "")
    if url.endswith("/"):
        url = url[:-1]
    if url.startswith("http://"):
        url = url.replace("http://", "https://")
    if url.endswith(".git"):
        url = url[:-4]
    return url if VCS_PATTERN.match(url) else None


def extract_url_from_answer(answer: str | None) -> str | None:
    if not answer:
        return None
    url_pattern = (
        r'(?P<url>https?://[^\s<>"]+|www\.[^\s<>"]+|[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}[^\s<>"]*)'
    )
    match = re.search(url_pattern, answer, re.IGNORECASE)
    if match:
        extracted_url = match.group("url")
        if not extracted_url.startswith(("http://", "https://")):
            if extracted_url.startswith("www."):
                extracted_url = "https://" + extracted_url
            elif "." in extracted_url:
                extracted_url = "https://www." + extracted_url
        if extracted_url.startswith("http://"):
            extracted_url = extracted_url.replace(
                "http://", "https://", 1
            )
        return extracted_url
    else:
        return None


def get_redirected_repo_url(repo_url):
    """
    Detects the final redirected URL of a repository URL.

    Args:
        repo_url (str): The initial repository URL to check.

    Returns:
        str or None: The final redirected URL after following redirects,
                     or None if there's an error (e.g., invalid URL, network issue).
    """
    try:
        response = requests.get(
            repo_url, allow_redirects=True, timeout=10
        )  # allow_redirects=True is default, but explicit for clarity
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        return response.url  # The final URL after redirects
    except RequestException as e:
        print(f"Error checking repo_url '{repo_url}': {e}")
        return repo_url


def extract_repo_path(github_url):
    match = re.search(r"github\.com/([^/]+/[^/]+)", github_url)
    if match:
        return match.group(1)
    return None


def is_url_reachable(url, timeout=10):
    """
    Checks if a URL is reachable by making an HTTP GET request and verifying the status code.

    Args:
        url (str): The URL to check.
        timeout (int, optional): Timeout in seconds for the request. Defaults to 10 seconds.

    Returns:
        bool: True if the URL is reachable (returns a 2xx status code), False otherwise.
              Returns False if there's a request error (e.g., invalid URL, network issue, timeout).
    """
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        return True  # URL is reachable if no exception was raised and status code is 2xx
    except RequestException as e:
        print(f"URL '{url}' is not reachable. Error: {e}")
        return False
