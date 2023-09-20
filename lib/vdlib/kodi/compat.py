try:
    from xbmcvfs import translatePath, makeLegalFilename, validatePath
except ImportError:
    from xbmc import translatePath, makeLegalFilename, validatePath #type: ignore
