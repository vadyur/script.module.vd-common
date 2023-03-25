# coding: utf-8

from __future__ import absolute_import
from vdlib.util import quote_plus

import requests, re, json
from bs4 import BeautifulSoup

from requests.packages.urllib3.exceptions import InsecureRequestWarning

from vdlib.util.log import debug
from vdlib.scrappers.base import clean_html

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


class RuTrackerBase(object):
    def __init__(self, settings):
        self.settings = settings
        self._session = None

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

    def make_session(self):
        s = requests.Session()
        if not self.check_login(s):
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
            return False
        """
        except BaseException:
            import xbmc
            xbmc.log(self.settings.rt_cookies)
            return False
        """
        resp = session.get('https://%s/forum/index.php' % self.baseurl, cookies=js)
        if re.compile('<input.+?type="text" name="login_username"').search(resp.text):
            return False
        return True

    def login(self, session):
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
            #captchaCode = self.askCaptcha('http:'+captchaMatch.group(1))
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
        return self.session.get(url, data=data, headers=headers, cookies=cookies)

    def post_request(self, url, data=None, headers=None, cookies=None):
        return self.session.post(url, data=data, headers=headers, cookies=cookies)

    def torrent_download(self, url, path):
        t = re.search('(\d+)$', url).group(1)
        referer = 'https://%s/forum/viewtopic.php?t=%s' % (self.baseurl, t)
        headers = {'Referer': referer,
                    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/45.0.2454.101 YaBrowser/15.10.2454.3658 Safari/537.36',
                    'Origin': 'https://%s' % self.baseurl, 
                    'Upgrade-Insecure-Requests': '1'
                    }
        data = { 't': t	}

        js = json.loads(self.settings.get_setting('rt_cookies'))
    
        r = self.post_request(url, headers=headers, data=data, cookies=js)
        if r.ok:
            with open(path, 'wb') as fd:
                for chunk in r.iter_content(chunk_size=128):
                    fd.write(chunk)			

    def search(self, title):
        if not self.check_settings():
            return

        url = 'https://{}/forum/tracker.php?nm={}'.format(
            self.baseurl,
            quote_plus(title)
        )
        headers = {'Referer': url}

        data = { 'max': '1', 'nm': title.encode('cp1251') }

        r = self.post_request(url, headers=headers, data=data)
        if r.ok:
            bs = BeautifulSoup(clean_html(r.text), 'html.parser')
            for tr in bs.find_all('tr', class_='hl-tr'):
                try:
                    title = tr.find('a', class_='tLink').get_text()
                except AttributeError:
                    continue

                indx = title.find('[')
                info = title[indx:].strip('[]')
                title = title[:indx].strip()
                seeds = tr.find('b', class_='seedmed').get_text()
                if seeds == '0':
                    continue

                td_dl = tr.find('td', class_='tor-size')
                dl_link = td_dl.a['href']

                yield {
                    'title': title,	'info': info,
                    'seeds': seeds,
                    'leechers': tr.find('td', class_='leechmed').get_text(),
                    'size': td_dl.get_text().strip(u'\n ↓'),
                    'dl_link': 'https://%s/forum/' % self.baseurl + dl_link
                }        



