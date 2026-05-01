from typing import Dict, List
from vdlib.util.lang import get_language

uni_type = str

LUnits: Dict[str, List[str]] = {
    "en": ["B", "KB", "MB", "GB", "TB"],
    "ru": ["Б", "Кб", "Мб", "Гб", "Тб"],
}


def decode_string(s, codepage='utf-8'):
    if isinstance(s, str):
        return s
    if isinstance(s, bytes):
        return s.decode(codepage)
    return str(s)

def is_string_type(s):
    return isinstance(s, str)

def colored(s, color):
    try:
        return '[COLOR={}]{}[/COLOR]'.format(color, s)
    except UnicodeEncodeError:
        return u'[COLOR={}]{}[/COLOR]'.format(color, s)

def humanizeSize(size: int) -> str:
    UNITS = LUnits.get(get_language())
    if UNITS is None:
        UNITS = LUnits['en']

    HUMANFMT = "%.2f %s"
    HUMANRADIX = 1024

    fsize: float = size
    for u in UNITS[:-1]:
        if fsize < HUMANRADIX:
            return HUMANFMT % (fsize, u)
        fsize /= HUMANRADIX

    return HUMANFMT % (fsize, UNITS[-1])
