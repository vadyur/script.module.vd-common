# -*- coding: utf-8 -*-

import log

from torrent2http import State, Engine, MediaType, Encryption
#from contextlib import closing
from torrentplayer import TorrentPlayer

import urlparse, urllib, time, filesystem, xbmc, xbmcaddon

def path2url(path):
	return urlparse.urljoin('file:', urllib.pathname2url(path))
	
_addon      =   xbmcaddon.Addon('')
_ADDON_NAME =   _addon.getAddonInfo('id')

dht_routers 		= ["router.bittorrent.com:6881","router.utorrent.com:6881"]
user_agent 			= 'uTorrent/2200(24683)'

def getSetting(settings_name):
	return _addon.getSetting(settings_name)


class Torrent2HTTPPlayer(TorrentPlayer):
	
	def debug(self, msg):
		try:
			import log
			log.debug('[Torrent2HTTPPlayer] %s' % msg)
		except:
			pass
			
	def debug_assignment(self, value, varname):
		try:
			self.debug('%s: %s' % (varname, str(value)))
		except:
			pass
		return value
		
	def __init__(self, settings):
		self.engine = None
		self.file_id = None
		self.settings = settings
		self.download_path = None
		
		self.pre_buffer_bytes 	= self.debug_assignment(int(getSetting('pre_buffer_bytes'))*1024*1024, 'pre_buffer_bytes')
		
		self.debug('__init__')
		
	def close(self):
		if self.engine != None:
			self.engine.close()
			self.engine = None
			
		self.debug('close')
		
	def __exit__(self):
		self.debug('__exit__')
		self.close()
		
	def _AddTorrent(self, path):

		if filesystem.exists(path):
			if path.startswith(r'\\'):
				tempPath = xbmc.translatePath('special://temp').decode('utf-8')
				destPath = filesystem.join(tempPath, 't2h.torrent')
				filesystem.copyfile(path, destPath)
				path = destPath

			uri = path2url(path)
		else:
			uri = path
		self.debug('AddTorrent: ' + uri)


		add_trackers = []
		if getSetting('add_tracker'):
			add_trackers.append(getSetting('add_tracker'))

		download_path = self.settings.storage_path
		if download_path == '':
			download_path = xbmc.translatePath('special://temp')
			
		self.debug('download_path: %s' % download_path)	
		self.download_path = download_path
		
		encryption = self.debug_assignment( Encryption.ENABLED if getSetting('encryption') == 'true' else Encryption.DISABLED ,'encryption')
		upload_limit = self.debug_assignment( int(getSetting("upload_limit")) * 1024 if getSetting("upload_limit") != "" else 0 ,"upload_limit")
		download_limit = self.debug_assignment( int(getSetting("download_limit")) * 1024 if getSetting("download_limit") != "" else 0 ,"download_limit")

		if getSetting("connections_limit") not in ["",0,"0"]:
			connections_limit = self.debug_assignment( int(getSetting("connections_limit")), "connections_limit")
		else:
			connections_limit = None

		use_random_port = self.debug_assignment( True if getSetting('use_random_port') == 'true' else False, 'use_random_port')
		listen_port = self.debug_assignment( int(getSetting("listen_port")) if getSetting("listen_port") != "" else 6881, "listen_port")
		
		args = {'uri': uri, 'download_path': download_path, 'user_agent': user_agent, 'encryption': encryption,
							'upload_kbps': upload_limit, 'download_kbps': download_limit, 'connections_limit': connections_limit,
							'keep_incomplete': False, 'keep_complete': True, 'keep_files': True, 'dht_routers': dht_routers, 'use_random_port': use_random_port, 'listen_port': listen_port,
							'log_files_progress': True, 'trackers': add_trackers, 'startup_timeout': 1000 }

		try:
			args['resume_file'] = filesystem.join(self.settings.torrents_path(), self.info_hash + '.resume')
		except BaseException as e:
			log.print_tb(e)
			args['resume_file'] = filesystem.join(download_path, self.info_hash + '.resume')
		self.debug('resume file is: ' + args['resume_file'])

		self.engine = Engine(**args)

		#self.engine.start()
		
	def CheckTorrentAdded(self):
		if self.engine:
			status = self.engine.status()
			self.engine.check_torrent_error(status)

			self.debug('CheckTorrentAdded')

			if status.state == State.CHECKING_FILES:
				self.debug('State.CHECKING_FILES')
				return False
		else:
			return TorrentPlayer.CheckTorrentAdded(self)
		
		return True
		
	def _GetLastTorrentData(self):
		while True:
			time.sleep(0.2)
			
			# Get torrent files list, filtered by video file type only
			files = self.engine.list() #(media_types=[MediaType.VIDEO])
			# If torrent metadata is not loaded yet then continue
			if files is None:
				self.debug('files is None')
				continue
				
			self.debug('files len: ' + str(len(files)))
			
			# Torrent has no video files
			if not files or len(files) > 0:
				break
				
		info_hash = ''
		playable_items = []
		for item in files:
			if TorrentPlayer.is_playable(item.name):
				playable_items.append({'index': item.index, 'name': item.name, 'size': long(item.size)})
		
		return { 'info_hash': info_hash, 'files': playable_items }
		
	def StartBufferFile(self, fileIndex):
		self._AddTorrent(self.path)

		'''
		try:
			files = self.engine.list()
			debug('StartBufferFile: has files')
			item = files[fileIndex]
			debug('StartBufferFile: has item')
			local_file = filesystem.join(self.download_path, item.name)
			debug('StartBufferFile: local_file = ' + local_file.encode('utf-8'))
			if filesystem.exists(local_file):
				debug('StartBufferFile: %s exists' % local_file.encode('utf-8'))
				self.download_path = local_file
				self.engine.close()	
				return
			else:
				debug('StartBufferFile: %s is not exists' % local_file.encode('utf-8'))
				self.download_path = None
		except:
			debug('StartBufferFile: exception trown')
			self.download_path = None
		'''

		self.download_path = None
		
		#if fileIndex != 0:
		#self.engine.close()
		self.engine.start(fileIndex)
		#status = self.engine.file_status(fileIndex)
		self.file_id = fileIndex
		
		self.debug('StartBufferFile: %d' % fileIndex)
		
	def CheckBufferComplete(self):
		if not self.download_path is None:
			return True
		
		status = self.engine.status()
		self.debug('CheckBufferComplete: ' + str(status.state_str))
		if status.state == State.DOWNLOADING:
			# Wait until minimum pre_buffer_bytes downloaded before we resolve URL to XBMC
			f_status = self.engine.file_status(self.file_id)
			self.debug('f_status.download %d' % f_status.download)
			if f_status.download >= self.pre_buffer_bytes:
				return True

		return status.state in [State.FINISHED, State.SEEDING]

	def GetBufferingProgress(self):
		f_status = self.engine.file_status(self.file_id)
		
		try:
			progress = int(round(float(f_status.download) / self.pre_buffer_bytes, 2) * 100)
			self.debug('GetBufferingProgress: %d' % progress)
			if progress > 99: 
				progress = 99
		except:
			progress = 0
		
	
		return progress

	def updateDialogInfo(self, progress, progressBar):
		f_status = self.engine.file_status(self.file_id)
		status = self.engine.status()
		
		if f_status is None or status is None:
			return
		
		dialogText = u'Загружено: ' + "%d MB / %d MB" % \
													(int(f_status.download / 1024 / 1024), int(f_status.size / 1024 / 1024))
		peersText = u' [%s: %s; %s: %s]' % (u'Сидов', status.num_seeds, u'Пиров', status.num_peers)
		speedsText = u'%s: %d Mbit/s; %s: %d Mbit/s' % (
			u'Загрузка', int(status.download_rate / 1024 * 8),
			u'Отдача', int(status.upload_rate / 1024 * 8))
		progressBar.update(progress, dialogText + '          ' + peersText, speedsText)
		
	def GetTorrentInfo(self):
		f_status = self.engine.file_status(self.file_id)
		status = self.engine.status()
		
		if f_status is None or status is None:
			return None

		try:
			return { 	'downloaded' : 	int(f_status.download / 1024 / 1024),
						'size' : 		int(f_status.size / 1024 / 1024),
						'dl_speed' : 	int(status.download_rate),
						'ul_speed' :	int(status.upload_rate),
						'num_seeds' :	status.num_seeds, 
						'num_peers' :	status.num_peers
					}
		except:
			pass
			
		return None

	def GetStreamURL(self, playable_item):
		if self.download_path is None:
			f_status = self.engine.file_status(self.file_id)
			self.debug('GetStreamURL: %s' % f_status.url)
			return f_status.url
		else:
			self.debug('GetStreamURL: %s' % self.download_path)
			return self.download_path