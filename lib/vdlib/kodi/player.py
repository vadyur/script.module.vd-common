# coding: utf-8

from ..util.string import decode_string
from ..torrent import torrent2httpplayer, torrserverplayer
# from ..torrent import aceplayer, yatpplayer, 
import time, sys
import xbmc, xbmcgui, xbmcplugin
from ..util.log import debug

class OurDialogProgress(xbmcgui.DialogProgress):
    def create(self, heading, line1="", line2="", line3=""):
        try:
            xbmcgui.DialogProgress.create(self, heading, line1, line2, line3)
        except TypeError:
            message = line1
            if line2:
                message += '\n' + line2
            if line3:
                message += '\n' + line3
            xbmcgui.DialogProgress.create(self, heading, message)

    def update(self, percent, line1="", line2="", line3=""):
        try:
            xbmcgui.DialogProgress.update(self, int(percent), line1, line2, line3)
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
#		elif torrent_player == 'YATP':
#			player = yatpplayer.YATPPlayer()
#		elif torrent_player == 'Ace Stream':
#			player = aceplayer.AcePlayer(settings)

		if not player:
			return

		player.AddTorrent(path)
		while not player.CheckTorrentAdded():
			info_dialog.update(0, u'Проверяем файлы', ' ', ' ')
			time.sleep(1)

		files = player.GetLastTorrentData()['files']
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

		handle = int(sys.argv[1])
		list_item = xbmcgui.ListItem(path=playable_url)

		if video_info:
			if isinstance(video_info, dict):
				list_item.setInfo('video', video_info)
			elif callable(video_info):
				list_item.setArt(video_info())

		if art:
			if isinstance(art, dict):
				list_item.setArt(art)
			elif callable(art):
				list_item.setArt(art())

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