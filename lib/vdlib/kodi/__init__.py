
from typing import Tuple

def get_kodi_version() -> Tuple[str, str, str, str]:
    import xbmc
    str_version = xbmc.getInfoLabel('System.BuildVersion')
    parts = str_version.split(' ')
    major, minor = parts[0].split('.')

    # Git:20240406-60c4500054
    date = ''
    commit = ''
    last_part = parts[-1]
    if 'Git:' in last_part:
        git_part = last_part.split('Git:')[1]
        date, commit = git_part.split('-')
    return major, minor, date, commit