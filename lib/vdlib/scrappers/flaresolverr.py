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
FS_PROGRESS_DELAY = 1.0


def _log(msg, level=None):
    if _KODI:
        xbmc.log('[FlareSolverr] ' + str(msg), level or xbmc.LOGDEBUG)


def host_port(url):
    try:
        from urllib.parse import urlparse
    except ImportError:
        from urlparse import urlparse
    try:
        return urlparse(str(url)).netloc or ''
    except Exception:
        return ''


def _progress_percent(elapsed, timeout):
    if timeout <= 0:
        return 0
    return max(0, min(99, int(elapsed * 100 / timeout)))


_BACKEND_CACHE = {}


def _backend_cache_path():
    return os.path.join(_state_dir(), 'flaresolverr_backend.json')


def _backend_cache_load():
    try:
        with open(_backend_cache_path(), 'r') as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {}


def _backend_cache_store(base_url, backend):
    try:
        data = _backend_cache_load()
        data[base_url] = backend
        with open(_backend_cache_path(), 'w') as f:
            json.dump(data, f)
    except Exception as e:
        _log('backend cache store failed: %s' % e)


def detect_backend(base_url):
    """Определяет бэкенд: Byparr (FastAPI) отдаёт GET /openapi.json -> 200
    за ~10мс, FlareSolverr (bottle) - 404. /health НЕ используется - у Byparr
    он дёргает browser-статус и живёт ~7с (первый вызов сериализовался бы).

    Кэш: память процесса -> файл в addon_data (чтобы следующие запуски
    плагина не платили пробу) -> живая проба. 'unknown' не сохраняется.
    """
    key = str(base_url or '').rstrip('/')
    if not key:
        return 'unknown'
    if key in _BACKEND_CACHE:
        return _BACKEND_CACHE[key]
    backend = _backend_cache_load().get(key)
    if backend in ('byparr', 'flaresolverr'):
        _BACKEND_CACHE[key] = backend
        return backend

    try:
        resp = urlopen(Request(key + '/openapi.json', method='GET'), timeout=3)
        resp.close()
        backend = 'byparr'  # FastAPI всегда рендерит openapi.json
    except Exception as e:
        code = getattr(e, 'code', None)
        if code == 404:
            backend = 'flaresolverr'  # у bottle нет openapi
        else:
            _log('backend probe %s failed: %s' % (key, e))
            return 'unknown'

    _BACKEND_CACHE[key] = backend
    _backend_cache_store(key, backend)
    _log('backend detected: %s (%s)' % (backend, key))
    return backend


class BrowserProgress(object):
    """Фоновый диалог прогресса (xbmcgui.DialogProgressBG) на время работы
    FlareSolverr/Byparr. Процент считается от elapsed/timeout, обновление
    тикером в фоновом потоке. Диалог появляется не сразу (чтобы не мигал
    на быстрых запросах) и закрывается при выходе из контекста.

    Использование:
        with BrowserProgress(timeout, target=host_port(base_url)):
            ...
    """

    def __init__(self, timeout, target='', heading='FlareSolverr / Byparr'):
        try:
            self.timeout = max(1, int(timeout or 0))
        except (TypeError, ValueError):
            self.timeout = 1
        self.target = str(target or '')
        self.heading = heading
        self._dialog = None
        self._stop = None
        self._thread = None
        self._t0 = 0.0

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *exc):
        self.stop()
        return False

    def start(self):
        if not _KODI:
            return self
        try:
            import time as _time
            self._t0 = _time.time()
            self._stop = _thr.Event()
            self._thread = _thr.Thread(target=self._tick)
            self._thread.daemon = True
            self._thread.start()
        except Exception as e:
            _log('progress start failed: %s' % e)
            self._stop = None
            self._thread = None
        return self

    def _message(self, elapsed):
        msg = '%d / %d s' % (min(int(elapsed), self.timeout), self.timeout)
        if self.target:
            msg += ' \u00b7 ' + self.target
        return msg

    def _ensure_dialog(self):
        if self._dialog is None and _KODI:
            try:
                import xbmcgui
                self._dialog = xbmcgui.DialogProgressBG()
                self._dialog.create(self.heading, self._message(0))
            except Exception as e:
                _log('progress dialog failed: %s' % e)
                self._dialog = None

    def _tick(self):
        import time as _time
        stop = self._stop
        while stop is not None and not stop.wait(0.25):
            try:
                elapsed = _time.time() - self._t0
                if self._dialog is None:
                    if elapsed < FS_PROGRESS_DELAY:
                        continue
                    self._ensure_dialog()
                if self._dialog is not None:
                    self._dialog.update(
                        _progress_percent(elapsed, self.timeout),
                        message=self._message(elapsed))
            except Exception as e:
                _log('progress update failed: %s' % e)
                break

    def stop(self):
        stop, thread = self._stop, self._thread
        self._stop = None
        self._thread = None
        if stop is not None:
            stop.set()
        if thread is not None:
            thread.join(2)
        dialog, self._dialog = self._dialog, None
        if dialog is not None:
            try:
                dialog.close()
            except Exception:
                pass


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

    def backend(self):
        return detect_backend(self.base_url)

    def api(self, payload, timeout=None):
        timeout = timeout or self.timeout
        payload.setdefault('maxTimeout', timeout * 1000)
        backend = self.backend()
        import time as _time
        t0 = _time.time()
        req = Request(
            self.base_url + '/v1',
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        progress = BrowserProgress(
            timeout, target='%s %s' % (backend, host_port(self.base_url))).start()
        try:
            resp = urlopen(req, timeout=timeout + 30)
            result = json.loads(resp.read().decode('utf-8'))
        except Exception as e:
            _log('%s error (%.1fs): %s' % (payload.get('cmd'), _time.time() - t0, e))
            return None
        finally:
            progress.stop()

        elapsed = _time.time() - t0
        if result.get('status') != 'ok':
            _log('%s [%s] failed (%.1fs): %s' % (
                payload.get('cmd'), backend, elapsed, result.get('message', '')))
            return None

        solution = result.get('solution') or {}
        _log('%s [%s] %.1fs http=%s len=%d' % (
            payload.get('cmd'), backend, elapsed, solution.get('status'),
            len(solution.get('response') or '')))
        return solution

    def chrome_request(self, method, url, params=None):
        if method == 'POST':
            # request.post на Byparr молча выполняется как GET без postData
            # (логика страницы ломается), поэтому POST шлём как на логине:
            # браузерный GET снимает cf_clearance, затем прямой POST с куками.
            solution = self.api({
                'cmd': 'request.get',
                'url': url,
                # disableMedia - имя FlareSolverr, blockMedia - у Byparr (тот
                # его игнорирует): без blockMedia goto ждёт "load" картинок,
                # которые режет DPI, и падает по таймауту (~94с, HTTP 502).
                'disableMedia': True,
                'blockMedia': True,
            })
            if not solution:
                return None
            return self.direct_request(
                'POST', url, params,
                cookies=solution.get('cookies') or [],
                useragent=solution.get('userAgent', '') or '')
        payload = {
            'cmd': 'request.get',
            'url': url,
            # disableMedia - имя FlareSolverr, blockMedia - у Byparr (тот его
            # игнорирует): без blockMedia goto ждёт "load" картинок/шрифтов,
            # которые режет DPI, и падает по таймауту (~94с, HTTP 502).
            'disableMedia': True,
            'blockMedia': True,
        }
        if params:
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
