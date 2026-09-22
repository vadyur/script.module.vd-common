# coding: utf-8

from typing import Optional

from ..util.string import decode_string
from ..torrent import torrent2httpplayer, torrserverplayer
# from ..torrent import aceplayer, yatpplayer,
import os, sys, time
import xbmc, xbmcgui, xbmcplugin, xbmcaddon
from ..util.log import debug
from .compat import translatePath

from torrserve_stream.engine import Engine
from torrserve_stream.settings import Settings

vdlib_addon = xbmcaddon.Addon(id='script.module.vd-common')
locString = vdlib_addon.getLocalizedString

class OurDialogProgress(xbmcgui.DialogProgress):
    def create(self, heading, line1="", line2="", line3=""):
        try:
            xbmcgui.DialogProgress.create(self, heading, line1, line2, line3) # type: ignore
        except TypeError:
            message = line1
            if line2:
                message += '\n' + line2
            if line3:
                message += '\n' + line3
            xbmcgui.DialogProgress.create(self, heading, message)

    def update(self, percent, line1="", line2="", line3=""):
        try:
            xbmcgui.DialogProgress.update(self, int(percent), line1, line2, line3) # type: ignore
        except TypeError:
            message = line1
            if line2:
                message += '\n' + line2
            if line3:
                message += '\n' + line3
            xbmcgui.DialogProgress.update(self, int(percent), message)


def _log(s):
    debug(u'vdlib.kodi.player: {}'.format(decode_string(s)))

def play_torrent(path, settings, info_dialog, title_dialog, video_info=None, art=None):
    player = None

    try:
        _log(path)
        torrent_player = settings.get_setting('torrent_player')

        _log(torrent_player)

        if torrent_player == 'torrent2http':
            player = torrent2httpplayer.Torrent2HTTPPlayer(settings)
        elif torrent_player == 'TorrServer':
            player = torrserverplayer.TorrServerPlayer(settings)
#        elif torrent_player == 'YATP':
#            player = yatpplayer.YATPPlayer()
#        elif torrent_player == 'Ace Stream':
#            player = aceplayer.AcePlayer(settings)

        if not player:
            return

        player.AddTorrent(path)
        while not player.CheckTorrentAdded():
            info_dialog.update(0, u'Проверяем файлы', ' ', ' ')
            time.sleep(1)

        td = player.GetLastTorrentData()
        if not td:
            return
        files = td['files']
        playable_item = files[0]

        player.StartBufferFile(0)

        if not player.CheckTorrentAdded():
            info_dialog.update(0, u'%s: проверка файлов' % title_dialog)

        while not info_dialog.iscanceled() and not player.CheckTorrentAdded():
            xbmc.sleep(1000)

        info_dialog.update(0, u'%s: буфферизация' % title_dialog)

        while not player.CheckBufferComplete():
            percent = player.GetBufferingProgress()
            if percent >= 0:
                player.updateDialogInfo(percent, info_dialog)

            time.sleep(1)

        info_dialog.update(0)
        info_dialog.close()

        playable_url = player.GetStreamURL(playable_item)
        _log(playable_url)

        if not playable_url:
            return

        handle = int(sys.argv[1])
        list_item = xbmcgui.ListItem(path=playable_url)

        if video_info:
            if isinstance(video_info, dict):
                list_item.setInfo('video', video_info)
            elif callable(video_info):
                list_item.setInfo('video', video_info()) # type: ignore

        if art:
            if isinstance(art, dict):
                list_item.setArt(art)
            elif callable(art):
                list_item.setArt(art()) # type: ignore

        xbmc_player = xbmc.Player()
        xbmcplugin.setResolvedUrl(handle, True, list_item)

        while not xbmc_player.isPlaying():
            xbmc.sleep(300)

        _log('!!!!!!!!!!!!!!!!! Start PLAYING !!!!!!!!!!!!!!!!!!!!!')

        # Wait until playing finished or abort requested
        while not xbmc.Monitor().abortRequested() and xbmc_player.isPlaying():
            player.loop()
            xbmc.sleep(1000)

        _log('!!!!!!!!!!!!!!!!! END PLAYING !!!!!!!!!!!!!!!!!!!!!')
    except BaseException as e:
        from ..util.log import print_tb
        print_tb(e)

    finally:
        if player:
            player.close()
    #return url


class xPlayer(xbmc.Player):

    def __init__(self, hash=None, index=None):
        self.index = index
        self.paused = False
        self._engine: Optional[Engine] = None
        xbmc.Player.__init__(self)
        self.init_engine(hash, index)

    def init_engine(self, hash: Optional[str], index: Optional[int]):
        if not self._engine:
            s = Settings()
            self._engine = Engine(**s.engine_args)
        self._engine.hash = hash
        self.index = index

    @property
    def engine(self):
        if self._engine:
            return self._engine

        s = Settings()
        self._engine = Engine(**s.engine_args)
        return self._engine

    def onStarted(self, file: str):
        from ..util.log import debug as _debug
        _debug('xPlayer.onStarted file={}'.format(file))
        try:
            hash = Engine.extract_hash_from_play_url(file)
            index = Engine.extract_file_index_from_play_url(file)
            _debug('xPlayer.onStarted hash={} index={}'.format(hash, index))
            self.init_engine(hash, index)
        except Exception as e:
            import traceback
            _debug('xPlayer.onStarted error: {} {}'.format(type(e).__name__, str(e)))
            _debug('xPlayer.onStarted traceback: {}'.format(traceback.format_exc()))

    def onPlayBackStarted(self):
        file = self.getPlayingFile()
        if file:
            self.onStarted(file)

    def onPlayBackPaused(self):
        pass

    def onPlayBackResumed(self):
        self.paused = False

    def onPlayBackStopped(self):
        self.paused = False
