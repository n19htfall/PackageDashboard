import os
import hashlib
import re
from typing import Tuple

PKGDASH_DOWNLOAD_PATH = './/.cache//'


def get_canonical_path(*p) -> str:
    return os.path.realpath(os.path.abspath(os.path.expanduser(os.path.join(*p))))


def md5(url: str):
    """Return a hash of the url"""
    return hashlib.md5(url.encode('utf-8')).hexdigest()


def get_local_path(url: str):
    """
    Generate a hashed and readable local path for an url
    >>> import os
    >>> p = get_local_path('https://google.com/a/AAA/A')
    >>> os.path.basename(os.path.dirname(p))
    'google_com_a_AAA_308453f'
    """
    dirname, filename = url_filename_split(url)
    dirname = re.sub(r'https?://', '', dirname)
    if '/' in dirname:  # trim domain
        dirname = '/'.join(dirname.split('/')[1:])
    _hash = md5(dirname)[-7:]
    dirname = re.sub(r'[^a-zA-Z0-9]', '_', dirname)
    if dirname.endswith('_'):
        _url = dirname[:-1]
    dirname += '_' + _hash
    return get_canonical_path(PKGDASH_DOWNLOAD_PATH, dirname, filename)


def url_filename_split(url: str, split_dir=False) -> Tuple[str, str]:
    """
    Split base url and filename from an url
    >>> url_filename_split('https://google.com/a/AAA/A')
    ('https://google.com/a/AAA', 'A')
    >>> url_filename_split('https://google.com/a/AAA/')
    ('https://google.com/a/AAA', '')
    >>> url_filename_split('https://google.com/a/AAA/', split_dir=True)
    ('https://google.com/a', 'AAA')
    """
    if '://' not in url:
        url = 'https://' + url
    if split_dir and url.endswith('/'):
        url = url[:-1]
    if not url.endswith('/') and url.count('/') > 2:  # not a file, e.g. https://A/B/
        return (
            '/'.join(url.split('/')[:-1]),
            url.split('/')[-1]
        )
    else:
        return (url[:-1], '')


if __name__ == '__main__':
    print(get_local_path(
        'https://mirrors.tuna.tsinghua.edu.cn/openeuler/openEuler-22.03-LTS/source/repodata/f1aeacb4f48d8323f59bc292abc5ccd6aada35f681417eda42ac730466fe7acc-primary.xml.gz'))
