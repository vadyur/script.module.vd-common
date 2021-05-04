import sys
if sys.version_info >= (3, 0):
    from xbmcvfs import translatePath, makeLegalFilename, validatePath
else:
    from xbmc import translatePath, makeLegalFilename, validatePath
