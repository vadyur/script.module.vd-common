import requests, random, urllib

arg_proxyurl = 'https://google.com'

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
def proxy_response_check(prox, proxyurl):
    try:
        resp = requests.head(proxyurl, proxies={'http': prox, 'https': prox}, timeout=1)
    except urllib.error.HTTPError as e:
        return e.code
    except Exception as detail:
        return False
    return True

def _get_proxy(url, proto, proxyurl):
    req = requests.get(url)
    if req.ok:
        lines = req.text.splitlines()
        for line in lines:
            progress_dialog(line)
            if proxy_response_check(f'{proto}://{line}', proxyurl) is True:
                progress_dialog("", show=False)
                return line

def get_socks5(proxyurl=arg_proxyurl):
    urls = ['https://raw.githubusercontent.com/prxchk/proxy-list/main/socks5.txt', 
            'https://raw.githubusercontent.com/hookzof/socks5_list/master/proxy.txt']
    
    for url in urls:
        result = _get_proxy(url, 'socks5', proxyurl)
        if result:
            return 'socks5://{}'.format(result)
        
    progress_dialog("", show=False)
    raise Exception("Can't get any proxy")

if __name__ == '__main__':
    print(get_socks5(proxyurl="https://f1news.ru"))