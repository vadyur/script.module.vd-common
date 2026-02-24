# -*- coding: utf-8 -*-

import re

from vdlib.scrappers.movieapi import TMDB_API

videoextensions = [
    '.m4v', '.3g2', '.3gp', '.nsv', '.tp', '.ts', '.ty', '.strm', '.pls', '.rm', '.rmvb', '.mpd', '.m3u', '.m3u8', '.ifo', '.mov', '.qt', '.divx', '.xvid',
    '.bivx', '.vob', '.nrg', '.img', '.iso', '.udf', '.pva', '.wmv', '.asf', '.asx', '.ogm', '.m2v', '.avi', '.bin', '.dat', '.mpg', '.mpeg', '.mp4',
    '.mkv', '.mk3d', '.avc', '.vp3', '.svq3', '.nuv', '.viv', '.dv', '.fli', '.flv', '.001', '.wpl', '.xspf', '.zip', '.vdr', '.dvr-ms', '.xsp', '.mts',
    '.m2t', '.m2ts', '.evo', '.ogv', '.sdp', '.avs', '.rec', '.url', '.pxml', '.vc1', '.h264', '.rcv', '.rss', '.mpls', '.mpl', '.webm', '.bdmv',
    '.bdm', '.wtv', '.trp', '.f4v'
]

cleandatetime = r'(.*[^ _\,\.\(\)\[\]\-])[ _\.\(\)\[\]\-]+(19[0-9][0-9]|20[0-9][0-9])([ _\,\.\(\)\[\]\-]|[^0-9]$)?'

cleanstrings = [
   r'[ _\,\.\(\)\[\]\-](ac3|dts|custom|dc|remastered|divx|divx5|dsr|dsrip|dutch|dvd|dvd5|dvd9|dvdrip|dvdscr|dvdscreener|screener|dvdivx|cam|fragment|fs|hdtv|hdrip|hdtvrip|internal|limited|multisubs|ntsc|ogg|ogm|pal|pdtv|proper|repack|rerip|retail|r3|r5|bd5|se|svcd|swedish|german|read.nfo|nfofix|unrated|extended|ws|telesync|ts|telecine|tc|brrip|bdrip|480p|480i|576p|576i|720p|720i|1080p|1080i|3d|hrhd|hrhdtv|hddvd|bluray|x264|h264|xvid|xvidvd|xxx|www.www|cd[1-9]|\[.*\])([ _\,\.\(\)\[\]\-]|$)',
   r'(\[.*\])',
]

year_pattern = r'(19[0-9][0-9]|20[0-9][0-9])'

def is_video(filename):
    # type: (str) -> bool
    for ext in videoextensions:
        if filename.endswith(ext):
            return True
    return False

def is_episode(filename):
    # type: (str) -> bool
    pattern = r'[s|S]\d+[e|E]\d+'
    return True if re.search(pattern, filename) else False

def extract_title_date(filename):
    # type: (str) -> tuple
    title = filename

    m = re.search(cleandatetime, title)
    if m:
        title = m.group(1)
        date = m.group(2)
    else:
        date = None

    for clinning_re in cleanstrings:
        m = re.search(clinning_re, title)
        if m:
            title = title.replace(m.group(1), '')

    if date:
        for date_part in [ '['+date+']', '('+date+')' ]:
            if date_part in title:
                title = title.split(date_part)[0]

    if '[' in title:
        title = title.split('[')[0]

    title = title.replace('.', ' ').strip()

    return title, date

def validate_part(part):
    keys =  [u'Сезон', u'Серии', u'сезон', u'серии']
    for key in keys:
        if key in part:
            return False

    patterns = [r'\d из \d', r'\d of \d', r'\d\s*-\s*\d']
    for pattern in patterns:
        if re.search(pattern, part):
            return False

    return True

def clean_part(part):
    part = re.sub(r'^\[.+?\]', '', part)
    part = re.sub(r'\[.+?\].+', '', part)
    #part = re.sub(r'\(.+?\)', part)
    return part.strip()

def clean_title(part):
    part = clean_part(part)
    part = re.sub(r'\(.+?\)', '', part)
    part = part.replace('.', ' ')

    part = re.sub(r'[Ss]\d.+', '', part)
    part = re.sub(r'\w{2,3}Rip.+', '', part)
    part = re.sub(r'720.+', '', part)
    part = re.sub(r'1080.+', '', part)
    part = re.sub(r'2160.+', '', part)
    part = re.sub(r'WEB-DL.+', '', part)

    return part.strip(' -\t')

def _extract_KT_title_year(title):
    pattern = r'\[KT\] (.+) \((19[0-9][0-9]|20[0-9][0-9])\)'
    m = re.match(pattern, title)
    if m:
        return { 'title': m.group(1), 'year': m.group(2) }

def _find_date_period(source):
    m = re.search(r'/ (19[0-9][0-9]|20[0-9][0-9])\s*-\s*(19[0-9][0-9]|20[0-9][0-9]) /', source)
    if m:
        return m.group(1), m.group(2)

def cut_by_season_episodes(title: str):
    pattern = r'([Ss]\d+[Ee][\d-]+)'
    m = re.search(pattern, title)
    if m:
        sep = m.group(1)
        title = title.split(sep)[0].rstrip(' -.,=[(')
    return title


def cut_by_year(title: str, year: str):
    return title.split(year)[0].strip()


def extract_original_title_year(title):
    source = title
    year = None
    original_title = None

    video_info = _extract_KT_title_year(title)
    if video_info:
        return video_info

    title = clean_title(title)
    if '/' in source:
        parts = source.split('/')
        title = clean_title(parts[0])
        parts[0] = title

        parts = [ clean_part(part) for part in parts ]
        parts = list(filter(validate_part, parts))

        original_title = parts[1] if len(parts) >= 2 else None

        m = re.search(r'/ (19[0-9][0-9]|20[0-9][0-9]) /', source)
        if m:
            year = m.group(1)
            parts = source.split(m.group(0))[0]
            parts = parts.split('/')
            original_title = parts[-1]
        elif _find_date_period(source):
            year = _find_date_period(source)[0]
        else:
            for part in reversed(parts[1:]):
                m = re.search(year_pattern, part.strip())
                if m:
                    original_title, year = extract_title_date(part)
                    if original_title and year:
                        break
                    year = m.group(1)

    if not year:
        m = re.search(year_pattern, source)
        if m:
            year = m.group(1)

    video_info = {'title': title.strip()}
    if original_title:
        if not year:
            original_title, year = extract_title_date(original_title.strip())
        video_info['originaltitle'] = cut_by_season_episodes(original_title).strip()
    if year:
        video_info['year'] = year
        video_info['title'] = cut_by_year(video_info['title'], year).strip()

        if original_title and year in original_title:
            del video_info['originaltitle']

    video_info['title'] = cut_by_season_episodes(video_info['title']).strip()

    return video_info

def extract_filename(url):
    from torrserve_stream.engine import Engine
    return Engine.extract_filename_from_play_url(url)

def from_translit(text):
    from transliterate import translit, detect_language
    l = detect_language(text)
    r = translit(text, 'ru')
    return r

def test(url):
    n = extract_filename(url)
    if n:
        t, d = extract_title_date(n)
        r = from_translit(t)

        return n, t, d, r

def get_tmdb_movie_item(imdbnumber):
    from vdlib.scrappers.movieapi import TMDB_API, tmdb_movie_item
    tmdb = TMDB_API(imdb_id=imdbnumber)
    result = tmdb_movie_item(tmdb.tmdb_data)
    return result

def find_tmdb_movie_item(video_info, art={}):
    from vdlib.scrappers.movieapi import TMDB_API, tmdb_movie_item

    def find_by_art(results, art):
        if 'poster' in art:
            parts = art['poster'].split('/')
            is_tmdb = False
            for part in parts:
                if 'tmdb' in part:
                    is_tmdb = True
            if is_tmdb and len(parts):
                posterId = parts[-1]
                if posterId:
                    posterId = posterId.split('?')[0]
                    for item in results:
                        if posterId in item.poster():
                            return item
                        for img in item.json_data_.get('images', {}).get('posters', []):
                            if posterId in img['file_path']:
                                return item

    def find_by(title):
        # null = без языка, остальные — коды ISO 639-1 для постеров/фонов
        image_langs = 'null,en,ru,uk,de,fr,es,it,pt,pl,tr,ja,ko,zh,hu,cs,sk'
        results = TMDB_API.search(title, append_to_response='images,external_ids,credits', include_image_language=image_langs)
        if len(results) == 1:
            result = results[0]     # type: tmdb_movie_item
            return result

        by_art = find_by_art(results, art)
        if by_art:
            return by_art

        def str_func(tmdb, loc):
            return tmdb == loc

        def date_func(tmdb, loc):
            return str(tmdb) == str(loc)

        filters = {
            'originaltitle': str_func,
            'plot': str_func,
            'year': date_func,
            'title': str_func
        }

        for field in filters:
            def filter_func(res):
                tmdb_info = res.get_info()
                return filters[field](tmdb_info.get(field), video_info.get(field))
            if field in video_info:
                filtered = list(filter(filter_func, results))
                if len(filtered) == 1:
                    results = filtered
                    break

        if len(results):
            result = results[0] # type: tmdb_movie_item
            return result

    for field in ['originaltitle', 'title']:
        title = video_info.get(field)
        if title:
            result = find_by(title)
            if result:
                return result


def update_video_info_from_tmdb(video_info, art={}, url=None):
    if video_info.get("imdbnumber"):
        tmdb_movie_item = get_tmdb_movie_item(video_info["imdbnumber"])
        video_info.update(tmdb_movie_item.get_info())
        return

    tmdb_movie_item = find_tmdb_movie_item(video_info, art)
    if tmdb_movie_item:
        imdbnumber = tmdb_movie_item.imdb()
        video_info.update(tmdb_movie_item.get_info())
        if imdbnumber:
            video_info['imdbnumber'] = imdbnumber
        if tmdb_movie_item.type == 'movie':
            video_info['mediatype'] = 'movie'
        elif tmdb_movie_item.type == 'tv':
            video_info['mediatype'] = 'tvshow'
            update_video_info_episode_from_tmdb(video_info, tmdb_movie_item.tmdb_id(), url)

def update_video_info_episode_from_tmdb(video_info, tmdb_id, url):
    from vdlib.scrappers.tvshowapi import TVShowAPI

    if video_info.get("mediatype") != "tvshow" or not url:
        return
    if not video_info.get("imdbnumber"):
        return

    # узнаем сезон и эпизод из url

    # Пример url: .../stream/Some.Show.S01E02.mkv?... или .../stream/Some.Show.1x02.mkv?...
    # Попробуем извлечь сезон и эпизод из url
    patterns = [
        r'[Ss](\d{1,2})[Ee](\d{1,2})',   # S01E02
        r'(\d{1,2})[xX](\d{1,2})',       # 1x02
        r'[Сс]езон[ _-]?(\d{1,2})[ _-]?[Сс]ерия[ _-]?(\d{1,2})', # Сезон 1 Серия 2
    ]

    season_number = None
    episode_number = None

    for pat in patterns:
        m = re.search(pat, url)
        if m:
            season_number = int(m.group(1))
            episode_number = int(m.group(2))
            break

    if season_number is not None:
        video_info['season'] = season_number
    if episode_number is not None:
        video_info['episode'] = episode_number

    if season_number is not None and episode_number is not None:
        api = TMDB_API(tmdb_id=tmdb_id, type='tv', append_to_response=f"season/{season_number}")
        episodes = api.episodes(season_number)
        season_info = api.season(season_number)
        for episode_info in episodes:
            if episode_info.get('episode_number') == episode_number:
                video_info['tvshowtitle'] = video_info['title']
                video_info['title'] = episode_info['name']
                episode_overview: str = episode_info['overview']
                if episode_number == 1 and season_info:
                    season_overview: str = season_info.get('overview', '')
                    video_info['plot'] = '\n\n'.join([season_overview, episode_overview]).strip('\n')
                else:
                    video_info['plot'] = episode_overview

                video_info["episode"] = episode_number
                video_info["season"] = season_number
                video_info['mediatype'] = 'episode'
