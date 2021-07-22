try:
    from xbmc import translatePath, makeLegalFilename, validatePath
except ImportError:
    from xbmcvfs import translatePath, makeLegalFilename, validatePath
