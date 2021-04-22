import sys
if sys.version_info >= (3, 0):
    from urllib.parse import urljoin, urlparse, urlencode
    from urllib.request import pathname2url
    from urllib.request import urlopen
else:
    from urlparse import urljoin, urlparse
    from urllib import pathname2url, urlencode
    from urllib2 import urlopen

from .string import decode_string

def path2url(path):
    return urljoin('file:', pathname2url(path))

    