import sys
if sys.version_info >= (3, 0):
    from urllib.error import URLError, HTTPError
    from urllib.parse import urljoin, urlparse, urlunparse, urlencode, ParseResult, quote, quote_plus
    from urllib.request import pathname2url
    from urllib.request import urlopen
else:
    from urlparse import urljoin, urlparse, urlunparse, ParseResult
    from urllib import pathname2url, urlencode, quote, quote_plus
    from urllib2 import urlopen, quote, quote_plus, URLError, HTTPError

from .string import decode_string

def path2url(path):
    return urljoin('file:', pathname2url(path))

    