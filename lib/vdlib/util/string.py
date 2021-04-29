import sys
if sys.version_info >= (3, 0):
    uni_type = str

    def decode_string(s, codepage='utf-8'):
        if isinstance(s, str):
            return s
        if isinstance(s, bytes):
            return s.decode(codepage)
        return str(s)

    def is_string_type(s):
        return isinstance(s, str)
else:
    uni_type = unicode
    def decode_string(s, codepage='utf-8'):
        if isinstance(s, unicode):
            return s
        if isinstance(s, str):
            return s.decode(codepage)
        return unicode(s)
    def is_string_type(s):
        return isinstance(s, str) or isinstance(s, unicode)

def colored(s, color):
    try:
        return '[COLOR={}]{}[/COLOR]'.format(color, s)
    except UnicodeEncodeError:
        return u'[COLOR={}]{}[/COLOR]'.format(color, s)
