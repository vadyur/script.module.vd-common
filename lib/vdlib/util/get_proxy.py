import queue
import threading
from typing import List
import requests, random, urllib

arg_testurl = 'https://google.com'

def _progress_fn_(address='', show=True):
    if (show):
        print(f'Try {address}')

progress_dialog = _progress_fn_

def _random(url):
    req = requests.get(url)
    if req.ok:
        lines = req.text.splitlines()
        indx = random.randrange(len(lines))
        return lines[indx]

# Function: Checking proxy response
def proxy_response_check(proto: str, proxy: str, testurl: str, result: queue.Queue):
    try:
        progress_dialog(proxy)
        prox = f'{proto}://{proxy}'
        resp = requests.head(testurl, proxies={'http': prox, 'https': prox}, timeout=2)
    except urllib.error.HTTPError as e: # type: ignore
        return e.code
    except Exception as detail:
        return False

    #return True
    result.put(proxy)

def _get_proxy(url, proto, testurl):
    req = requests.get(url)
    if req.ok:
        result = queue.Queue()

        lines = req.text.splitlines()
        for line in lines:
            ##progress_dialog(line)
            ## if proxy_response_check(f'{proto}://{line}', proxyurl) is True:
            ##     progress_dialog("", show=False)
            ##     return line

            th = threading.Thread(
                name='worker',
                target=proxy_response_check,
                args=(proto, line, testurl, result)
            )
            th.start()

        while any(th.is_alive() for th in threading.enumerate() if th.name == 'worker'):
            if not result.empty():
                return result.get()

        if not result.empty():
            return result.get()



def get_socks5(testurl=arg_testurl):
    urls = ['https://raw.githubusercontent.com/prxchk/proxy-list/main/socks5.txt',
            'https://raw.githubusercontent.com/hookzof/socks5_list/master/proxy.txt']

    for url in urls:
        result = _get_proxy(url, 'socks5', testurl)
        if result:
            return 'socks5://{}'.format(result)

    progress_dialog("", show=False)
    raise Exception("Can't get any proxy")

if __name__ == '__main__':
    print(get_socks5(testurl="https://f1news.ru"))