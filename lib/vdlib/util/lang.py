def get_language(full: bool = False) -> str:
    try:
        import xbmc
        lang = xbmc.getLanguage(xbmc.ISO_639_1, full)

        if not lang:
            lang = "en"

        return lang

    except Exception:
        return "en"

def _translate(sId: int, addonId: str) -> str:
    from xbmcaddon import Addon
    addon = Addon(addonId)
    return addon.getLocalizedString(sId)

def translate_torrspy(id: int) -> str:
    return _translate(id, 'script.service.torrspy')

