import sys
if sys.version_info >= (3, 0):
    from urllib.error import URLError, HTTPError
    from urllib.parse import urljoin, urlparse, urlunparse, urlencode, ParseResult, quote, quote_plus, unquote_plus
    from urllib.request import pathname2url
    from urllib.request import urlopen
else:
    from urlparse import urljoin, urlparse, urlunparse, ParseResult
    from urllib import pathname2url, quote, quote_plus, unquote_plus
    from urllib2 import urlopen, quote, URLError, HTTPError

    def urlencode(query, doseq=False, safe='', encoding=None, errors=None, quote_via=quote_plus):
        import urllib

        q = {}
        for k, v in query.items():
            if isinstance(v, unicode):
                v = v.encode(encoding if encoding else 'utf-8')
            q[k] = v
        return urllib.urlencode(q, doseq)

from .string import decode_string

def path2url(path):
    return urljoin('file:', pathname2url(path))

    