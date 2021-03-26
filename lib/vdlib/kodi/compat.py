import sys
if sys.version_info >= (3, 0):
    from xbmcvfs import translatePath
else:
    from xbmc import translatePath
