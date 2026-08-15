# -*- coding: utf-8 -*-

import pickle, base64
from typing import Optional, Dict, Any

import xbmc

def get_sort_index(play_url: str) -> Optional[int]:
    from torrserve_stream import Engine
    from torrserve_stream import Settings
    ts_settings = Settings()

    hash = Engine.extract_hash_from_play_url(play_url)
    name = Engine.extract_filename_from_play_url(play_url)

    engine = Engine(hash=hash, **ts_settings.engine_args)
    return engine.get_ts_index(name)


class PlayerVideoInfo(object):
    def __init__(self, player: Optional[xbmc.Player]) -> None:
        self.player: Optional[xbmc.Player] = player
        self.time: Optional[float] = None
        self.total_time: Optional[float] = None
        self.video_info: Optional[Dict[str, Any]] = None
        self.media_type: Optional[str] = None
        self.play_url: Optional[str] = None
        self.sort_index: Optional[int] = None

    def update(self) -> None:
        if self.player and self.player.isPlayingVideo():
            try:
                video_info_tag = self.player.getVideoInfoTag()

                self.time = self.player.getTime()
                self.total_time = self.player.getTotalTime()

                self.video_info = self.player.getVideoInfo() # type: ignore
                self.media_type = video_info_tag.getMediaType()

                self.play_url = self.player.getPlayingFile()
                if self.play_url:
                    self.sort_index = get_sort_index(self.play_url)
            except BaseException:
                from vdlib.util.log import print_tb
                print_tb()
                self.reset()

    def reset(self) -> None:
        self.time = None
        self.total_time = None
        self.video_info = None
        self.media_type = None
        self.play_url = None
        self.sort_index = None

    def dumps(self) -> str:
        data: Dict[str, Any] = self.__dict__.copy()
        data.pop('player')
        s = pickle.dumps(data)
        s = base64.b64encode(s)
        if isinstance(s, str):
            return s
        else:
            return s.decode('ascii') # type: ignore

    def loads(self, s: str) -> None:
        bb = base64.b64decode(s)
        d = pickle.loads(bb)
        self.__dict__.update(d)
