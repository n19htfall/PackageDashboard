import bz2
import gzip
import os
from typing import Optional, BinaryIO, TextIO

import aiohttp

from pkgdash.fetch.utils import get_local_path


async def download_file(url: str, filename: str) -> str:
    """
    Download a file with aiohttp
    :return: filename
    """
    if os.path.exists(filename):  # cache
        return filename

    # create dir if not exists
    if not os.path.exists(os.path.dirname(filename)):
        os.makedirs(os.path.dirname(filename))

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            with open(filename, 'wb') as file:
                while True:
                    chunk = await response.content.read(1024)
                    if not chunk:
                        break
                    file.write(chunk)

    return filename


ARCHIVE_CLASS = {
    "gz": gzip.open,
    "bz2": bz2.open,
}


def open_may_be_archive(path: str, mode='rb', **kwargs) -> BinaryIO | TextIO:
    _file_ext = '' if path.count('.') == 0 else path.split('.')[-1]
    if _file_ext in ARCHIVE_CLASS:
        return ARCHIVE_CLASS[_file_ext](path, mode, **kwargs)
    else:
        return open(path, mode, **kwargs)


class RemoteFile(object):
    """
    Cache a remote file and open in rb mode, supports gzip & bz2
    >>> import asyncio
    >>> async def test():
    ...     async with RemoteFile('https://mirrors.tuna.tsinghua.edu.cn/centos/8.5.2111/configmanagement/x86_64/ansible-5/repodata/caf347f317f156ddd33776a55332924fd51ffa7e9d745f13dc05dac611a88931-primary.xml.gz') as f:
    ...         print(f.read().decode('utf-8').splitlines()[0].strip())
    >>> asyncio.run(test())
    <?xml version="1.0" encoding="UTF-8"?>
    >>> import asyncio
    >>> async def test2():
    ...     async with RemoteFile('https://mirrors.tuna.tsinghua.edu.cn/centos/8-stream/storage/ppc64le/gluster-9/repodata/repomd.xml') as f:
    ...         print(f.read().decode('utf-8').splitlines()[0].strip())
    >>> asyncio.run(test())
    <?xml version="1.0" encoding="UTF-8"?>
    """
    _local_path: str
    _remote_path: str
    _mode: str = 'rb'

    def __init__(self, url: str, path: Optional[str] = None, mode='rb'):
        self._local_path = get_local_path(url) if not path else path
        self._remote_path = url
        self._mode = mode

    async def __aenter__(self):
        await download_file(url=self._remote_path, filename=self._local_path)
        self._f = open_may_be_archive(self._local_path, self._mode)
        return self._f

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self._f.close()


if __name__ == '__main__':
    import asyncio


    async def open_remote():
        async with RemoteFile(
                url='https://mirrors.tuna.tsinghua.edu.cn/centos/8.5.2111/configmanagement/x86_64/ansible-5/repodata/caf347f317f156ddd33776a55332924fd51ffa7e9d745f13dc05dac611a88931-primary.xml.gz') as f:
            print(f.read().decode('utf-8'))


    asyncio.run(open_remote())
