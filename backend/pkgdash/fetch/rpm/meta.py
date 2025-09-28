import os
import queue
from typing import List, Iterable, Tuple, Sized
import asyncio

import aiohttp
from bs4 import BeautifulSoup

import logging

from tqdm.asyncio import tqdm as tqdm_async

from pkgdash.fetch.file import RemoteFile, download_file
from pkgdash.fetch.utils import url_filename_split, get_local_path

PKGSHIP_DOWNLOAD_PATH = './/cache//'


def _parse_xml_urls(body: str) -> List[str]:
    soup = BeautifulSoup(body, 'xml')
    return [loc['href'] for loc in soup.find_all('location')]


def _parse_html_urls(body: str) -> List[str]:
    soup = BeautifulSoup(body, 'html.parser')
    return [a['href'] for a in soup.find_all('a') if 'href' in a.attrs]


async def find_rpm_repodata_urls(base_url: str) -> List[str]:
    """
    Traverse on the webpage to get a list of 'repodata/' urls; stop recurse if found on current page
    :returns: list of repodata urls, e.g. ['https://repo.openeuler.org/X/Y/repodata/']

    >>> import asyncio
    >>> asyncio.run(find_rpm_repodata_urls('https://mirrors.tuna.tsinghua.edu.cn/openeuler/openEuler-22.03-LTS/'))[0]
    'https://mirrors.tuna.tsinghua.edu.cn/openeuler/openEuler-22.03-LTS/source/repodata/'
    """
    q = queue.Queue()
    q.put(base_url)
    repodata_urls = []
    async with aiohttp.ClientSession() as sess:
        while not q.empty():
            url = q.get()
            # perform a request
            async with sess.get(url) as resp:
                if resp.status == 200:
                    body = await resp.text()
                    _next_urls = _parse_html_urls(body)
                    _full_urls = []
                    for u in _next_urls:
                        _u = u
                        if '?' in _u:
                            _u = _u[:_u.index('?')]
                        if not _u.endswith('/') or _u.endswith('./') or _u.endswith('../'):
                            continue
                        if _u.startswith('/'):
                            _u = base_url + _u[1:]
                        elif not u.startswith('http'):
                            _u = url + _u
                        if not _u.startswith(base_url) or _u == url:
                            continue
                        if _u.endswith('repodata/'):
                            repodata_urls.append(_u)
                            logging.info(f'Found Repository {_u}')
                            break
                        _full_urls.append(_u)
                    else:
                        for u in _full_urls:
                            q.put(u)
    return repodata_urls


def _get_local_path_repodata(url: str) -> str:
    # libsolv need a /repodata/... path
    _u_parent, _u_filename = url.split('repodata/')  # else url is malformed
    _p = os.path.join(get_local_path(_u_parent), 'repodata', _u_filename)
    return _p


async def _create_download_tasks(repodata_url: str) -> List[asyncio.Future]:
    _base_url = repodata_url
    if 'repomd.xml' in repodata_url:
        _base_url, _ = url_filename_split(repodata_url)
    if 'repodata' in repodata_url:
        _base_url, _ = url_filename_split(repodata_url, split_dir=True)
    _repomd_url = _base_url + '/repodata/repomd.xml'
    _p = _get_local_path_repodata(_repomd_url)

    _hrefs = []
    async with RemoteFile(_repomd_url, path=_p) as f:
        urls = _parse_xml_urls(f)
        # just download everything
        for u in urls:
            if u.startswith('/'):
                u = _base_url + u
            _hrefs.append(u)

    # use an async pool to download
    tasks = []
    for u in _hrefs:
        u = _base_url + '/' + u
        _p = _get_local_path_repodata(u)
        # check dir
        if not os.path.exists(os.path.dirname(_p)):
            os.makedirs(os.path.dirname(_p))
        tasks.append(asyncio.create_task(download_file(u, _p)))
    return tasks


async def download_rpm_repo_meta(repodata_url: str) -> List[str]:
    """
    Downloads repomd.xml and all the files listed in it
    :returns: list of downloaded files

    >>> import asyncio
    >>> os.path.basename(asyncio.run(download_rpm_repo_meta('https://mirrors.tuna.tsinghua.edu.cn/openeuler/openEuler-22.03-LTS/source/repodata/'))[0])
    'f1aeacb4f48d8323f59bc292abc5ccd6aada35f681417eda42ac730466fe7acc-primary.xml.gz'
    """
    tasks = await _create_download_tasks(repodata_url)
    return await tqdm_async.gather(*tasks, total=len(tasks), desc='Downloading Metadata')


async def download_rpm_all_meta(base_url: str) -> List[str]:
    """
    Scan for repodatas and download all the files listed in them
    :returns: list of downloaded files

    >>> import asyncio
    >>> os.path.basename(asyncio.run(download_rpm_all_meta('https://mirrors.tuna.tsinghua.edu.cn/openeuler/openEuler-22.03-LTS/'))[0])
    'f1aeacb4f48d8323f59bc292abc5ccd6aada35f681417eda42ac730466fe7acc-primary.xml.gz'
    """
    repodata_urls = await find_rpm_repodata_urls(base_url)
    tasks = []
    for u in repodata_urls:
        tasks.extend(await _create_download_tasks(u))
    return await tqdm_async.gather(*tasks, total=len(tasks), desc='Downloading Metadata')


if __name__ == '__main__':
    async def runner():
        for url in (
            'https://mirrors.tuna.tsinghua.edu.cn/openeuler/openEuler-22.03-LTS-SP1/',
            'https://mirrors.tuna.tsinghua.edu.cn/opensuse/tumbleweed/repo/oss/',
            'https://mirrors.tuna.tsinghua.edu.cn/centos/8/',
            'https://mirrors.tuna.tsinghua.edu.cn/fedora/releases/38/',
        ):
            print(await download_rpm_all_meta(url))

    asyncio.run(runner())