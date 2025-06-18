# -*- coding: utf-8 -*-

from typing import Optional, Dict

def executeJSONRPC(q):
    import json, xbmc
    s = json.dumps(q)
    res = xbmc.executeJSONRPC(s)
    return json.loads(res)

class JSONRPC_API(object):
    def __init__(self, name):
        self._name = name

    def __getattribute__(self, name):
        _name = object.__getattribute__(self, '_name')
        def run(limits={}, sort={}, filter={}, **params):
            q = {	"jsonrpc": "2.0",
                    "method": _name + "." + name,
                    "params": params,
                    "id": "JSONRPC_API"
            }

            if limits:
                q['params']['limits'] = limits
            if sort:
                q['params']['sort'] = sort
            if filter:
                q['params']['filter'] = filter

            try:
                res = executeJSONRPC(q)
                return res['result']
            except KeyError:
                return {}
        return run

VideoLibrary	= JSONRPC_API('VideoLibrary')
JSONRPC			= JSONRPC_API('JSONRPC')
GUI				= JSONRPC_API('GUI')
Files			= JSONRPC_API('Files')
Player			= JSONRPC_API('Player')

def remove_movie_by_id(id):
    r = VideoLibrary.RemoveMovie(movieid=id)
    pass

def update_movie_by_id(self, id, fields={}):
    params = fields.copy()
    params['movieid'] = id
    r = VideoLibrary.SetMovieDetails(**params)

def get_tvshow(tvshow_id):
    res = VideoLibrary.GetTVShowDetails(tvshowid=int(tvshow_id),
                properties=["title", "originaltitle", "year", "file", "imdbnumber"])

    if 'tvshowdetails' in res:
        return res['tvshowdetails']
    return res

def get_episodes(tvshow_id):
    result = VideoLibrary.GetEpisodes(
                tvshowid=int(tvshow_id),
                properties=["season", "episode", "file"])

    try:
        return result['episodes']
    except KeyError:
        return []

def get_tvshows(imdb_id):
    result = VideoLibrary.GetTVShows(properties=["imdbnumber"])
    for show in result['tvshows']:
        if show["imdbnumber"] == imdb_id:
            yield show['tvshowid']

def update_episode(e, api_data):

    """
    playcount, runtime, director, plot, rating, votes, lastplayed, writer,
    firstaired, productioncode, season, episode, originaltitle, thumbnail,
    fanart, art, resume, userrating, ratings, dateadded,
    """

    params = {'episodeid': e['episodeid']}
    for key in ['title', 'plot']:
        params[key] = api_data[key]

    result = VideoLibrary.SetEpisodeDetails(**params)
    pass

def remove_episode(e):
    # VideoLibrary.RemoveEpisode
    # http://kodi.wiki/view/JSON-RPC_API/v8#VideoLibrary.RemoveEpisode
    result = VideoLibrary.RemoveEpisode(episodeid=e['episodeid'])

def player_open(url: str):
    # type: (str) -> None
    """
    Open a URL in the Kodi player.
    :param url: The URL to open.
    """
    result = Player.Open(item={'file': url})
    pass  # Handle the result if needed, currently just opens the URL in the player.

def get_first_active_player_id():  # type: () -> Optional[int]
    """
    Возвращает playerid первого активного плеера или None, если нет активных плееров.
    """
    players = Player.GetActivePlayers()
    if players:
        return players[0]['playerid']
    return None

def player_stop():  # type: () -> None
    """
    Stop the Kodi player.
    """
    player_id = get_first_active_player_id()
    if player_id is not None:
        result = Player.Stop(playerid=player_id)
    pass  # Handle the result if needed, currently just stops the player.

def player_get_resume():  # type: () -> Optional[Dict]
    def get_seconds(hours=0, minutes=0, seconds=0, **kwargs):  # type: (int, int, int, ...) -> int
        return int(hours) * 3600 + int(minutes) * 60 + int(seconds)

    player_id = get_first_active_player_id()
    if player_id is not None:
        result = Player.GetProperties(playerid=player_id, properties=["time", "totaltime"])
        if result:
            return {
                'time': get_seconds(**result['time']),
                'totaltime': get_seconds(**result['totaltime'])
            }
    pass

def player_seek(seconds: int):
    """
    Seek the Kodi player to a specific time.
    :param seconds: The number of seconds to seek to.
    """
    player_id = get_first_active_player_id()
    if player_id is not None:
        result = Player.Seek(playerid=player_id, value={'seconds': seconds})
    pass  # Handle the result if needed, currently just seeks to the specified time.
