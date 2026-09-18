# coding: utf-8

from __future__ import absolute_import
from vdlib.util import quote_plus

import os, json
import requests, re
from bs4 import BeautifulSoup

from requests.packages.urllib3.exceptions import InsecureRequestWarning

from vdlib.util.log import debug
from vdlib.scrappers.base import clean_html

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


class _FakeResponse(object):
    """Wrapper to make FlareSolverr string responses look like requests.Response."""
    def __init__(self, text, status_code=200):
        self.text = text
        self.status_code = status_code
        self.ok = 200 <= status_code < 400


class RuTrackerBase(object):
    def __init__(self, settings):
        self.settings = settings
        self._session = None
        self._fs_url = None
        self._fs_client = None
        self._fs_state = None

        try:
            fs_url = self.settings.get_setting('rt_flaresolverr_url')
            if fs_url:
                self._fs_url = fs_url.strip().rstrip('/')
        except Exception:
            pass

    @property
    def session(self):
        if not self._session:
            self._session = self.make_session()
        return self._session

    @property
    def username(self):
        return self.settings.get_setting('rt_username')

    @property
    def password(self):
        return self.settings.get_setting('rt_password')

    @property
    def baseurl(self):
        return self.settings.get_setting('rt_baseurl')

    def _get_fs_client(self):
        if self._fs_client is None and self._fs_url:
            from vdlib.scrappers.flaresolverr import FlareSolverrClient
            timeout = 120
            direct_timeout = 45
            try:
                t = self.settings.get_setting('rt_flaresolverr_timeout')
                if t:
                    timeout = int(t)
            except (ValueError, TypeError):
                pass
            try:
                t = self.settings.get_setting('rt_flaresolverr_direct_timeout')
                if t:
                    direct_timeout = int(t)
            except (ValueError, TypeError):
                pass
            self._fs_client = FlareSolverrClient(self._fs_url, timeout, direct_timeout)
        return self._fs_client

    def _load_flaresolverr_state(self):
        if not self._fs_url:
            return None
        from vdlib.scrappers.flaresolverr import FlareSolverrState
        login = self.username or ''
        self._fs_state = FlareSolverrState.load(self.baseurl, login)
        return self._fs_state

    def make_session(self):
        try:
            import xbmc
        except ImportError:
            xbmc = None
        s = requests.Session()

        if self._fs_url:
            fs_state = self._load_flaresolverr_state()
            if fs_state:
                for c in fs_state['cookies']:
                    s.cookies.set(c['name'], c['value'], domain=c.get('domain', ''), path=c.get('path', '/'))
                s.headers['User-Agent'] = fs_state['useragent']
                debug('RuTrackerBase: FlareSolverr cookies injected for %s (%d cookies)' % (self.baseurl, len(fs_state['cookies'])))
            elif self._fs_url:
                debug('RuTrackerBase: FlareSolverr enabled but no state for %s' % self.baseurl)

        try:
            login_cookies = json.loads(self.settings.get_setting('rt_cookies'))
            if login_cookies:
                for name, value in login_cookies.items():
                    s.cookies.set(name, value, domain='.%s' % self.baseurl, path='/forum/')
        except (ValueError, TypeError):
            pass

        if self._fs_url and self._fs_state:
            debug('RuTrackerBase: FlareSolverr state loaded, skipping check_login')
        elif not self.check_login(s):
            self._session = s
            self.login(s)
        return s

    def check_settings(self):
        if not self.username or not self.password or not self.baseurl:
            return False
        return True

    def check_login(self, session):
        try:
            js = json.loads(self.settings.get_setting('rt_cookies'))
        except ValueError:
            js = {}

        if not js and session.cookies:
            js = dict((c.name, c.value) for c in session.cookies)

        if not js:
            debug('RuTrackerBase: no cookies, not logged in')
            return False

        resp = session.get('https://%s/forum/index.php' % self.baseurl, cookies=js)
        debug('RuTrackerBase: check_login status=%d len=%d' % (resp.status_code, len(resp.text)))
        if re.compile('<input.+?type="text" name="login_username"').search(resp.text):
            debug('RuTrackerBase: login form found, not logged in')
            return False
        if re.compile('challenge-platform').search(resp.text):
            debug('RuTrackerBase: Cloudflare challenge detected, not logged in')
            return False
        return True

    def _login_via_flaresolverr(self):
        debug('RuTrackerBase: login via FlareSolverr for %s' % self.baseurl)
        from vdlib.scrappers.flaresolverr import FlareSolverrState
        client = self._get_fs_client()
        if client is None:
            return False

        FlareSolverrState.drop(self.baseurl, self.username or '')

        params = {
            'login_username': self.username,
            'login_password': self.password,
            'login': '\u0432\u0445\u043e\u0434',
            'redirect': 'index.php'
        }
        solution = client.api({
            'cmd': 'request.post',
            'url': 'https://%s/forum/login.php' % self.baseurl,
            'postData': '&'.join('%s=%s' % (k, v) for k, v in params.items()),
            'disableMedia': True,
        })
        if solution is None:
            debug('RuTrackerBase: FlareSolverr login failed')
            return False

        body = solution.get('response', '')
        cookies = solution.get('cookies', [])
        useragent = solution.get('userAgent', '') or solution.get('useragent', '')

        if re.search(r'login_username', body):
            debug('RuTrackerBase: FlareSolverr login form still present after POST')
            return False

        if cookies:
            FlareSolverrState.save(self.baseurl, self.username or '',
                                    cookies=cookies, useragent=useragent,
                                    latency=client._latency)
            self._fs_state = {'cookies': cookies, 'useragent': useragent,
                              'latency': client._latency, 'domain': self.baseurl}
            for c in cookies:
                self._session.cookies.set(c['name'], c['value'],
                                          domain=c.get('domain', ''), path=c.get('path', '/'))
            if useragent:
                self._session.headers['User-Agent'] = useragent
            debug('RuTrackerBase: FlareSolverr login OK, %d cookies saved' % len(cookies))
            return True

        debug('RuTrackerBase: FlareSolverr login - no cookies in response')
        return False

    def login(self, session):
        if self._fs_url:
            return self._login_via_flaresolverr()

        pageContent = session.get('https://%s/forum/login.php' % (self.baseurl))
        captchaMatch = re.compile(
            '(//static\.t-ru\.org/captcha/\d+/\d+/[0-9a-f]+\.jpg\?\d+).+?name="cap_sid" value="(.+?)".+?name="(cap_code_[0-9a-f]+)"',
            re.DOTALL | re.MULTILINE).search(pageContent.text)
        data = {
            'login_password': self.password,
            'login_username': self.username,
            'login': '%C2%F5%EE%E4',
            'redirect': 'index.php'
        }
        if captchaMatch:
            captcha = 'http:'+captchaMatch.group(1)
            captchaCode = ''
            if captchaCode:
                data['cap_sid'] = captchaMatch.group(2)
                data[captchaMatch.group(3)] = captchaCode
            else:
                return False
            
        r = session.post(
            'https://%s/forum/login.php' % self.baseurl,
            data=data,
            allow_redirects = False
        )

        if r.ok:
            c = requests.utils.dict_from_cookiejar(r.cookies)
            self.settings.set_setting('rt_cookies', json.dumps(c))
            return c

    def get_request(self, url, data=None, headers=None, cookies=None):
        if self._fs_url and not self._fs_state:
            self._load_flaresolverr_state()
        if self._fs_url and self._fs_state:
            client = self._get_fs_client()
            if client:
                body = client.request('GET', url, params=data,
                                      cookies=self._fs_state['cookies'],
                                      useragent=self._fs_state['useragent'])
                if body is not None:
                    return _FakeResponse(body)
            return _FakeResponse('', 503)
        r = self.session.get(url, data=data, headers=headers, cookies=cookies)
        if self._fs_url and self._fs_state:
            client = self._get_fs_client()
            if client:
                body = client.request('GET', url, params=data,
                                      cookies=self._fs_state['cookies'],
                                      useragent=self._fs_state['useragent'])
                if body is not None:
                    return _FakeResponse(body)
        return r

    def post_request(self, url, data=None, headers=None, cookies=None):
        if self._fs_url and not self._fs_state:
            self._load_flaresolverr_state()
        if self._fs_url and self._fs_state:
            client = self._get_fs_client()
            if client:
                body = client.request('POST', url, params=data,
                                      cookies=self._fs_state['cookies'],
                                      useragent=self._fs_state['useragent'])
                if body is not None:
                    return _FakeResponse(body)
            return _FakeResponse('', 503)
        r = self.session.post(url, data=data, headers=headers, cookies=cookies)
        if self._fs_url and self._fs_state:
            client = self._get_fs_client()
            if client:
                body = client.request('POST', url, params=data,
                                      cookies=self._fs_state['cookies'],
                                      useragent=self._fs_state['useragent'])
                if body is not None:
                    return _FakeResponse(body)
        return r

    def search(self, title):
        if not self.check_settings():
            return

        url = 'https://{}/forum/tracker.php?nm={}'.format(
            self.baseurl,
            quote_plus(title)
        )
        headers = {'Referer': url}

        data = { 'max': '1', 'nm': title }

        r = self.post_request(url, headers=headers, data=data)
        if r.ok:
            bs = BeautifulSoup(clean_html(r.text), 'html.parser')
            for tr in bs.find_all('tr', class_='hl-tr'):
                try:
                    title = tr.find('a', class_='tLink').get_text()
                except AttributeError:
                    continue

                indx = title.find('[')
                if indx < 0:
                    continue
                info = title[indx:].strip('[]')
                title = title[:indx].strip()

                seed_el = tr.find('b', class_='seedmed')
                if not seed_el:
                    seed_el = tr.find('span', class_='seedmed')
                if not seed_el:
                    continue
                seeds = seed_el.get_text()
                if seeds == '0':
                    continue

                leech_el = tr.find('td', class_='leechmed')
                leechers = leech_el.get_text() if leech_el else '0'

                td_dl = tr.find('td', class_='tor-size')
                if not td_dl or not td_dl.a:
                    continue
                dl_link = td_dl.a['href']

                yield {
                    'title': title,	'info': info,
                    'seeds': seeds,
                    'leechers': leechers,
                    'size': td_dl.get_text().strip(u'\n ↓'),
                    'dl_link': 'https://%s/forum/' % self.baseurl + dl_link
                }        
