import shutil
import tarfile
import subprocess
import re

from pkgdash.models.spdx_license import SPDXLicense


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


def execute_command(command: str, cwd: str | None = None):
    try:
        subprocess.run(command, capture_output=True, text=True, shell=True, cwd=cwd)
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


def _sanitize_vcs_url(url: str | None) -> str | None:
    if url is None:
        return None
    if "git+" in url:
        url = url.replace("git+", "")
    if "www." in url:
        url = url.replace("www.", "")
    if url.endswith("/"):
        url = url[:-1]
    if url.startswith("http://"):
        url = url.replace("http://", "https://")
    if url.startswith("git://"):
        url = url.replace("git://", "https://")
    if url.endswith(".git"):
        url = url[:-4]
    return url if VCS_PATTERN.match(url) else None


def check_license_validity(license_expression: str) -> bool:
    try:
        SPDXLicense(license_expression)
        return True
    except ValueError:
        return False
