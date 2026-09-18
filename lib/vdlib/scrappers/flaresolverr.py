# coding: utf-8

from __future__ import absolute_import

import os
import json
import threading as _thr

try:
    import xbmc
    import xbmcvfs
    _KODI = True
except ImportError:
    _KODI = False

try:
    from urllib.request import Request, urlopen
    from urllib.parse import urlencode
except ImportError:
    from urllib2 import Request, urlopen
    from urllib import urlencode


FS_CACHE_TTL = 300
FS_HEDGE_MIN = 3
FS_HEDGE_MAX = 25


def _log(msg, level=None):
    if _KODI:
        xbmc.log('[FlareSolverr] ' + str(msg), level or xbmc.LOGDEBUG)


def _state_dir():
    try:
        d = xbmcvfs.translatePath('special://profile/addon_data/script.module.vd-common')
    except Exception:
        import tempfile
        d = os.path.join(tempfile.gettempdir(), 'vd_flaresolverr')
    if not os.path.exists(d):
        try:
            os.makedirs(d)
        except Exception:
            pass
    return d


def _safe_name(s):
    return ''.join(c if c.isalnum() or c in ('-', '_') else '_' for c in str(s))


class FlareSolverrState(object):

    @staticmethod
    def state_path(domain, login=''):
        name = 'flaresolverr_%s_%s.json' % (_safe_name(domain), _safe_name(login))
        return os.path.join(_state_dir(), name)

    @staticmethod
    def load(domain, login=''):
        path = FlareSolverrState.state_path(domain, login)
        try:
            with open(path, 'r') as f:
                data = json.load(f)
            if data.get('domain') != domain:
                _log('state domain mismatch: saved=%s expected=%s, ignoring' % (data.get('domain'), domain))
                return None
            cookies = data.get('cookies', [])
            useragent = data.get('useragent', '')
            latency = float(data.get('latency') or FS_HEDGE_MIN)
            if cookies and useragent:
                _log('loaded state: %d cookies, latency %.1fs, domain=%s' % (len(cookies), latency, domain))
                return {'cookies': cookies, 'useragent': useragent, 'latency': latency, 'domain': domain}
        except Exception as e:
            _log('state load failed: %s' % str(e))
        return None

    @staticmethod
    def save(domain, login='', cookies=None, useragent='', latency=FS_HEDGE_MIN):
        path = FlareSolverrState.state_path(domain, login)
        try:
            with open(path, 'w') as f:
                json.dump({
                    'domain': domain,
                    'cookies': cookies or [],
                    'useragent': useragent,
                    'latency': latency
                }, f)
            _log('state saved: %s' % path)
        except Exception as e:
            _log('state save failed: %s' % str(e))

    @staticmethod
    def drop(domain, login=''):
        path = FlareSolverrState.state_path(domain, login)
        try:
            os.remove(path)
            _log('state dropped: %s' % path)
        except Exception:
            pass

    @staticmethod
    def cookie_header(cookies_list, extra=None):
        jar = dict((c['name'], c['value']) for c in cookies_list)
        if extra:
            jar.update(extra)
        return '; '.join(k + '=' + v for k, v in jar.items())


class FlareSolverrClient(object):

    def __init__(self, base_url, timeout=120, direct_timeout=45):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.direct_timeout = direct_timeout
        self._latency = float(FS_HEDGE_MIN)

    def api(self, payload, timeout=None):
        timeout = timeout or self.timeout
        payload.setdefault('maxTimeout', timeout * 1000)
        import time as _time
        t0 = _time.time()
        req = Request(
            self.base_url + '/v1',
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        try:
            resp = urlopen(req, timeout=timeout + 30)
            result = json.loads(resp.read().decode('utf-8'))
        except Exception as e:
            _log('%s error (%.1fs): %s' % (payload.get('cmd'), _time.time() - t0, e))
            return None

        elapsed = _time.time() - t0
        if result.get('status') != 'ok':
            _log('%s failed (%.1fs): %s' % (payload.get('cmd'), elapsed, result.get('message', '')))
            return None

        solution = result.get('solution') or {}
        _log('%s %.1fs http=%s len=%d' % (
            payload.get('cmd'), elapsed, solution.get('status'),
            len(solution.get('response') or '')))
        return solution

    def chrome_request(self, method, url, params=None):
        payload = {
            'cmd': 'request.get' if method == 'GET' else 'request.post',
            'url': url,
            'disableMedia': True,
        }
        if params:
            if method == 'POST':
                payload['postData'] = urlencode(params, encoding='windows-1251')
            else:
                payload['url'] = url + ('&' if '?' in url else '?') + urlencode(params, encoding='windows-1251')
        solution = self.api(payload)
        if solution is None:
            return None
        return solution.get('response', '')

    def direct_request(self, method, url, params=None, cookies=None, useragent='', timeout=None, binary=False):
        timeout = timeout or self.direct_timeout
        if method == 'POST':
            data = urlencode(params, encoding='windows-1251').encode('ascii') if params else b''
            req = Request(url, data=data, method='POST')
            req.add_header('Content-Type', 'application/x-www-form-urlencoded')
        else:
            if params:
                url = url + ('&' if '?' in url else '?') + urlencode(params, encoding='windows-1251')
            req = Request(url, method=method)

        req.add_header('User-Agent', useragent)
        req.add_header('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8')
        req.add_header('Accept-Language', 'ru-ru,ru;q=0.8,en-us;q=0.5,en;q=0.3')
        req.add_header('Accept-Encoding', 'gzip')
        if cookies:
            cookie_str = FlareSolverrState.cookie_header(cookies) if isinstance(cookies, list) else str(cookies)
            if cookie_str:
                req.add_header('Cookie', cookie_str)

        import time as _time
        t0 = _time.time()
        try:
            resp = urlopen(req, timeout=timeout)
            data = resp.read()
            if resp.headers.get('Content-Encoding') == 'gzip':
                import zlib
                data = zlib.decompressobj(16 + zlib.MAX_WBITS).decompress(data)
        except Exception as e:
            _log('direct %s failed %.1fs: %s' % (method, _time.time() - t0, e))
            return None

        elapsed = _time.time() - t0
        self._latency = round(self._latency * 0.5 + elapsed * 0.5, 2)
        _log('direct %s %.1fs len=%d' % (method, elapsed, len(data)))
        if binary:
            return data
        return data.decode('windows-1251', 'replace')

    def hedged_direct(self, method, url, params=None, cookies=None, useragent='', timeout=None, binary=False):
        result = {}
        done = _thr.Event()

        def attempt(tag):
            body = self.direct_request(method, url, params, cookies=cookies,
                                       useragent=useragent, timeout=timeout, binary=binary)
            if body is not None and tag not in result:
                result[tag] = body
                done.set()
            elif body is None:
                result.setdefault('_failed_' + tag, True)
                if len([k for k in result if k.startswith('_failed_')]) >= 2:
                    done.set()

        first = _thr.Thread(target=attempt, args=('a',))
        first.daemon = True
        first.start()

        hedge_after = min(FS_HEDGE_MAX, max(FS_HEDGE_MIN, self._latency * 3))
        if not done.wait(hedge_after):
            _log('direct still pending, hedging with a second try')
            second = _thr.Thread(target=attempt, args=('b',))
            second.daemon = True
            second.start()
            done.wait(self.direct_timeout + 5)

        return result.get('a') or result.get('b')

    def request(self, method, url, params=None, cookies=None, useragent=''):
        if cookies:
            if method == 'GET':
                body = self.hedged_direct(method, url, params, cookies=cookies, useragent=useragent)
            else:
                body = self.direct_request(method, url, params, cookies=cookies, useragent=useragent)
            if body is not None:
                return body
            _log('direct failed, falling back to Chrome')
        return self.chrome_request(method, url, params)
