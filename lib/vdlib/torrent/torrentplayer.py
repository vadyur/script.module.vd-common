# -*- coding: utf-8 -*-
import os, sys

from ..util.log import debug, print_tb
from ..util import filesystem
from ..util.string import decode_string

if sys.version_info < (3, 0):
	from .bencode import BTFailure as BTError
	from .bencode import bdecode, bencode
else:
	from .bencodepy import BencodeDecodeError as BTError
	from .bencodepy import bdecode, bencode


def _log(s):
	debug('TorrentPlayer: {}'.format(s))

def _(s):
	try:
		if isinstance(s, str):
			return s.encode('utf-8')
	except UnicodeEncodeError:
		pass
	return s

class TorrentPlayer(object):

	def __init__(self):
		self._decoded	= None
		self._info_hash = None

	@property
	def decoded(self):
		if not self._decoded:
			data = None
			with filesystem.fopen(self.path, 'rb') as torr:
				data = torr.read()

			if data is None:
				return None

			try:
				self._decoded = bdecode(data)
			except BTError:
				debug("Can't decode torrent data (invalid torrent link?)")
				return None

		return self._decoded

	@property
	def info_hash(self):
		if not self._info_hash:
			try:
				import hashlib
				info = self.decoded[_('info')]
				self._info_hash = hashlib.sha1(bencode(info)).hexdigest()
			except:
				return None

		# 878e51a0c03967e90fd3371a06d77f0d86ba5e1d
		return self._info_hash

	@staticmethod
	def is_playable(name):
		filename, file_extension = os.path.splitext(name)
		return file_extension in ['.mkv', '.mp4', '.ts', '.avi', '.m2ts', '.mov']

	def AddTorrent(self, path):
		#raise NotImplementedError("def ###: not imlemented.\nPlease Implement this method")
		self.path = path

	def CheckTorrentAdded(self):
		#raise NotImplementedError("def ###: not imlemented.\nPlease Implement this method")
		return filesystem.exists(self.path)

	def updateCheckingProgress(self, progressBar):
		pass

	@staticmethod
	def Name(name):
		try:
			return decode_string(name)
		except UnicodeDecodeError:
			try:
				import chardet
				enc = chardet.detect(name)
				debug('confidence: {0}'.format(enc['confidence']))
				debug('encoding: {0}'.format(enc['encoding']))
				if enc['confidence'] > 0.5:
					try:
						name = name.decode(enc['encoding'])
					except UnicodeDecodeError:
						pass
				else:
					print_tb()
			except BaseException as e:
				print_tb()
				
		return name

	def GetLastTorrentData(self):

		decoded =self.decoded

		if decoded is None:
			return None

		info = decoded[_('info')]

		def info_name():
			if _('name.utf-8') in info:
				return info[_('name.utf-8')]
			else:
				return info[_('name')]

		def f_path(f):
			if _('path.utf-8') in f:
				return f['path.utf-8']
			else:
				return f['path']

		name = '.'
		playable_items = []
		try:
			if _('files') in info:
				for i, f in enumerate(info[_('files')]):
					# debug(i)
					# debug(f)
					name = os.sep.join(f_path(f))
					size = f[_('length')]
					#debug(name)
					if TorrentPlayer.is_playable(name):
						playable_items.append({'index': i, 'name': TorrentPlayer.Name(name), 'size': size})
					name = TorrentPlayer.Name(info_name())
			else:
				playable_items = [ {'index': 0, 'name': TorrentPlayer.Name(info_name()), 'size': info[_('length')] } ]
		except UnicodeDecodeError:
			return None

		return { 'info_hash': self.info_hash, 'announce': decoded[_('announce')], 'files': playable_items, 'name': name }

	def GetTorrentInfo(self):
		try:
			return { 'downloaded' : 	100,
			            'size' : 		100,
			            'dl_speed' : 	1,
			            'ul_speed' :	0,
			            'num_seeds' :	1,
			            'num_peers' :	0
			            }
		except:
			pass

		return None

	def StartBufferFile(self, fileIndex):
		pass

	def CheckBufferComplete(self):
		pass

	def GetBufferingProgress(self):
		pass

	def GetStreamURL(self, playable_item):
		pass

	def updateDialogInfo(self, progress, progressBar):
		pass

	def GetBufferingProgress(self):
		return 100

	def CheckBufferComplete(self):
		return True

	def loop(self):
		pass

def test():
	file = '/Users/vd/.kodi/temp/lazyf1.torrent'

	tp = TorrentPlayer()
	tp.AddTorrent(file)

	d = tp.decoded

	ltd = tp.GetLastTorrentData()
	pass