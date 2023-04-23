import sys
if sys.version_info >= (3, 0):
    from urllib.error import URLError, HTTPError
    from urllib.parse import urljoin, urlparse, urlunparse, urlencode, ParseResult, quote, quote_plus, unquote_plus, parse_qs
    from urllib.request import pathname2url
    from urllib.request import urlopen
else:
    from urlparse import urljoin, urlparse, urlunparse, ParseResult, parse_qs
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

def compare_urls_ignore_domain(url1, url2):
    """
    Сравнивает два URL-адреса, игнорируя различия в доменных именах и IP-адресах.

    :param url1: первый URL-адрес
    :param url2: второй URL-адрес
    :return: True, если URL-адреса совпадают (игнорируя доменные имена и IP-адреса), в противном случае - False
    """
    parsed_url1 = urlparse(url1)
    parsed_url2 = urlparse(url2)

    return parsed_url1.scheme == parsed_url2.scheme and \
           parsed_url1.port == parsed_url2.port and \
           parsed_url1.path == parsed_url2.path and \
           parsed_url1.params == parsed_url2.params and \
           parsed_url1.query == parsed_url2.query and \
           parsed_url1.fragment == parsed_url2.fragment