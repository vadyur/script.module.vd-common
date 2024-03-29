﻿from ..util.log import *

import json
import re
from contextlib import closing
from zipfile import ZipFile, BadZipfile, LargeZipFile
import xml.etree.ElementTree as ET

from ..util import urlopen, HTTPError

import io

from ..util.string import decode_string

def cutStr(s):
	return s.replace('.', ' ').replace('_', ' ').replace('[', ' ').replace(']', ' ').lower().strip()

def sweetpair(l):
	from difflib import SequenceMatcher

	s = SequenceMatcher()
	ratio = []
	for i in range(0, len(l)): ratio.append(0)
	for i in range(0, len(l)):
		for p in range(0, len(l)):
			s.set_seqs(l[i], l[p])
			ratio[i] = ratio[i] + s.quick_ratio()
	id1, id2 = 0, 0
	for i in range(0, len(l)):
		if ratio[id1] <= ratio[i] and i != id2 or id2 == id1 and ratio[id1] == ratio[i]:
			id2 = id1
			id1 = i
		# debug('1 - %d %d' % (id1, id2))
		elif (ratio[id2] <= ratio[i] or id1 == id2) and i != id1:
			id2 = i
		# debug('2 - %d %d' % (id1, id2))

	debug('[sweetpair]: id1 ' + l[id1] + ':' + str(ratio[id1]))
	debug('[sweetpair]: id2 ' + l[id2] + ':' + str(ratio[id2]))

	return [l[id1], l[id2]]


def sortext(filelist):
	result = {}
	for name in filelist:
		ext = name.split('.')[-1]
		try:
			result[ext] = result[ext] + 1
		except:
			result[ext] = 1
	lol = result.items()
	lol = sorted(lol, key=lambda x: x[1])
	debug('[sortext]: lol:' + str(lol))
	popext = lol[-1][0]
	result, i = [], 0
	for name in filelist:
		if name.split('.')[-1] == popext:
			result.append(name)
			i = i + 1
	result = sweetpair(result)
	debug('[sortext]: result:' + str(result))

	return result


def cutFileNames(l):
	from difflib import Differ

	d = Differ()

	text = sortext(l)


	indexes = []
	for i in l:
		indexes.append(l[i])

	newl = []
	for li in l:
		newl.append(cutStr(li[0:len(li) - 1 - len(li.split('.')[-1])]))
	l = newl

	text1 = cutStr(text[0][0:len(text[0]) - 1 - len(text[0].split('.')[-1])])
	text2 = cutStr(text[1][0:len(text[1]) - 1 - len(text[1].split('.')[-1])])
	sep_file = " "
	result = list(d.compare(text1.split(sep_file), text2.split(sep_file)))
	debug(u'[cutFileNames] ' + decode_string(result))

	start = ''
	end = ''

	for res in result:
		if str(res).startswith('-') or str(res).startswith('+') or str(res).startswith('.?'):
			break
		if re.search(r'[Ss]\d{1,3}', str(res)):
			break

		start = start + str(res).strip() + sep_file
	result.reverse()
	for res in result:
		if str(res).startswith('-') or str(res).startswith('+') or str(res).startswith('?'):
			break
		end = sep_file + str(res).strip() + end

	newl = l
	l = {}
	debug('[cutFileNames] [start] ' + start)
	debug('[cutFileNames] [end] ' + end)
	for i, fl in enumerate(newl):
		if cutStr(fl[0:len(start)]) == cutStr(start): fl = fl[len(start):]
		if cutStr(fl[len(fl) - len(end):]) == cutStr(end): fl = fl[0:len(fl) - len(end)]
		try:
			isinstance(int(fl.split(sep_file)[0]), int)
			fl = fl.split(sep_file)[0]
		except:
			pass
		l[fl] = indexes[i]
	debug(u'[cutFileNames] [sorted l]  ' + decode_string(sorted(l, key=lambda x: x)))
	return l


def FileNamesPrepare(filename):
	my_season = None
	my_episode = None

	try:
		if int(filename):
			my_episode = int(filename)
			debug(u'[FileNamesPrepare] ' + str([my_season, my_episode, filename]))
			return [my_season, my_episode, filename]
	except:
		pass

	urls = [r's(\d+)e(\d+)', r's(\d+) e(\d+)', r'(\d+)[x|-](\d+)', r'E(\d+)', r'Ep(\d+)', r'\((\d+)\)', r'S(\d+)e(\d+)', r'S(\d+)E(\d+)', r'S(\d+)\.E(\d+)',r'S(\d+)\.e(\d+)' ,r's(\d+)\.e(\d+)']
	for file in urls:
		match = re.compile(file, re.DOTALL | re.I | re.IGNORECASE).findall(filename)
		if match:
			try:
				my_episode = int(match[1])
				my_season = int(match[0])
			except:
				try:
					my_episode = int(match[0])
				except:
					try:
						my_episode = int(match[0][1])
						my_season = int(match[0][0])
					except:
						try:
							my_episode = int(match[0][0])
						except:
							break
			if my_season and my_season > 100: my_season = None
			if my_episode:
				if my_episode > 1000:
					dm = divmod(my_episode, 100)
					if dm[0] + 1 == dm[1]:
						my_episode = dm[0]
					else:
						my_episode = None
				elif my_episode > 365:
					my_episode = None
			try:
				debug('[FileNamesPrepare] ' + '%d %d %s' % (my_season, my_episode, filename))
			except TypeError:
				debug('[FileNamesPrepare]: TypeError')
				debug('[FileNamesPrepare] ' + str([my_season, my_episode, filename]))
				pass
			return [my_season, my_episode, filename]

	return None


def get_list(dirlist):
	files = []
	if len(dirlist) > 1:
		cutlist = cutFileNames(dirlist)
	else:
		cutlist = dirlist
	for fn in cutlist:
		x = FileNamesPrepare(fn)
		if x:
			x.append(cutlist[fn])
			files.append(x)
		else:
			debug(fn, lineno())

	return files


def seasonfromname(name):
	match = re.compile('(\d+)', re.I).findall(name)
	if match:
		try:
			num = int(match[0])
			return num if num > 0 and num < 20 else None
		except:
			pass
	return None


def parse_torrent(info, season=None):
	dirlists = dict()

	if 'files' in info:
		for i, f in enumerate(info['files']):
			fname = f['path'][-1]
			try:
				parent = f['path'][-2]
			except:
				parent = '.'

			if parent not in dirlists:
				dirlists[parent] = dict()

			debug(fname)
			from ..util.base import is_file_playable
			if is_file_playable(fname):
				dirlists[parent][fname] = i 

	files = []
	for dirname in dirlists:
		dirlist = dirlists[dirname]
		save_season = season
		for item in get_list(dirlist):
			if item is not None:
				if season is None:
					if item[0] is None:
						season = seasonfromname(info['name'])
						if season is None:
							try:
								season = seasonfromname(dirname)
							except:
								pass
					else:
						season = item[0]

				name = item[2]
				index = item[3]

				if season is None:
					season = 1

				files.append({'name': name, 'season': season, 'episode': item[1], 'index': index})
				season = save_season
			else:
				# TODO
				continue

	files.sort(key=lambda x: (x['season'], x['episode']))
	return files


def season_from_title(fulltitle):
	parts = re.split(r'[,;\(\)\[\]]', fulltitle)
	for part in parts:
		if u'сезонов' in part.lower():
			return None
		if u'сезоны' in part.lower():
			return None
		if u'сезон' in part.lower():
			if re.search('\d+\D+\d+', part):
				return None
			match = re.search('(\d+)', part)
			if match:
				return int(match.group(1))

	return None



# TheTVDB
# 1. http://thetvdb.com/api/GetSeriesByRemoteID.php?imdbid=ttxxxxxxx&language=ru	id=<Data><Series><id>
# 2. http://thetvdb.com/api/1D62F2F90030C444/series/<id>/all/ru.zip					zip -> banners.xml, actors.xml, ru.xml

# noinspection SpellCheckingInspection
class TheTVDBAPI(object):
	__base_url = 'http://thetvdb.com/api/'
	__apikey = '1D62F2F90030C444'
	__lang = 'ru'

	dictEpisodes = {
		'Overview': 'plot',
		'EpisodeName': 'title',
		'EpisodeNumber': 'episode',
		'SeasonNumber': 'season',
		'Rating': 'rating',
		'FirstAired': 'aired',
		'Director': 'director'
	}

	def __init__(self, imdbId):
		self.tvdb_banners = None
		self.tvdb_ru = None

		if imdbId is None:
			return

		try:
			response1 = urlopen(self.__base_url + 'GetSeriesByRemoteID.php?imdbid=%s&language=%s' % (imdbId, self.__lang) )
			try:
				xml_data = decode_string(response1.read())
				self.thetvdbid = re.search(r'<id>(\d+)</id>', xml_data).group(1)
			except AttributeError:
				return
		except HTTPError as e:
			debug('TheTVDBAPI: ' + str(e))
			return

		url2 = self.__base_url + self.__apikey + '/series/%s/all/%s.zip' % (self.thetvdbid, self.__lang)
		debug(url2)

		response2 = urlopen(url2)
		try:
			f = io.BytesIO(response2.read())
			with closing(ZipFile(f, 'r')) as zf:
				with closing(zf.open('banners.xml', 'r')) as banners:
					self.tvdb_banners = ET.fromstring(banners.read())
				with closing(zf.open('ru.xml')) as ru:
					self.tvdb_ru = ET.fromstring(ru.read())
		except BadZipfile as bz:
			debug(str(bz))
		except LargeZipFile as lz:
			debug(str(lz))

	def getEpisode(self, season, episode):
		res = {}
		if self.tvdb_ru is None:
			return res

		for ep in self.tvdb_ru:
			if ep.tag == 'Episode':
				try:
					episode_number = int(ep.find('EpisodeNumber').text)
					season_number = int(ep.find('SeasonNumber').text)
				except BaseException as e:
					print_tb(e)
					continue
				if int(episode_number) != episode or int(season_number) != season:
					continue

				for child in ep:
					if child.text is not None:
						if child.tag in self.dictEpisodes and len(child.text) > 0:
							res[self.dictEpisodes[child.tag]] = child.text
						if child.tag == 'filename' and len(child.text) > 0:
							res['thumb'] = 'http://thetvdb.com/banners/' + child.text
					else:
						pass

		return res

	def getArt(self, type):
		result = []
		if self.tvdb_banners is None:
			return result

		baseurl = 'http://thetvdb.com/banners/'
		for banner in self.tvdb_banners:
			BannerType = banner.find('BannerType')
			if BannerType is not None:
				if BannerType.text == type:
					BannerPath = banner.find('BannerPath')
					ThumbnailPath = banner.find('ThumbnailPath')

					if BannerPath is not None and ThumbnailPath is not None:
						result.append({'path': baseurl + BannerPath.text, 'thumb': baseurl + ThumbnailPath.text})
		return result

	def Fanart(self):
		return self.getArt('fanart')

	def Poster(self):
		return self.getArt('poster')

	def getTitle(self):
		if self.tvdb_ru is None:
			return None

		Series = self.tvdb_ru.find('Series')
		if Series is not None:
			SeriesName = Series.find('SeriesName')
			if SeriesName is not None:
				return SeriesName.text

		return None

	def get_premiered(self):
		if self.tvdb_ru is None:
			return None

		Series = self.tvdb_ru.find('Series')
		if Series is not None:
			premiered = Series.find('FirstAired')
			if premiered is not None:
				return premiered.text

		return None


class MyShowsAPI(object):
	myshows = None
	myshows_ep = None

	dictMyShows = {	
		'title': 'title',
		'airDate': 'aired',
		'shortName': 'short',
		'image': 'thumb',
		'seasonNumber': 'season',
		'episodeNumber': 'episode',
		'started': 'premiered'
	}

	def __init__(self, title, ruTitle, imdbId=None, kinopoiskId=None):
		if imdbId:
			try:
				imdbId = int(re.search('(\d+)', imdbId).group(1))
				debug(imdbId)
			except:
				imdbId = None

		if kinopoiskId:
			try:
				kinopoiskId = int(re.search('(\d+)', kinopoiskId).group(1))
			except:
				kinopoiskId = None

		from ..util import quote
		base_url = 'http://api.myshows.me/shows/search/?q='
		url = base_url + quote(title.encode('utf-8'))
		try:
			self.myshows = json.load(urlopen(url))
		except HTTPError as e:
			debug('TVShowAPI: ' + str(e))
			return

		if not self.valid():
			url = base_url + quote(ruTitle.encode('utf-8'))
			self.myshows = json.load(urlopen(url))

		if self.valid():
			debug(url)
			# debug(unicode(json.dumps(self.myshows, sort_keys=True, indent=4, separators=(',', ': ')), 'unicode-escape').encode('utf-8'))
			id = self.get_myshows_id(imdbId, kinopoiskId)
			debug(id)
			if id != 0:
				url = 'http://api.myshows.me/shows/' + str(id)
				self.myshows_ep = json.load(urlopen(url))
				if self.valid_ep():
					debug(url)

		debug(str(self.valid()))
		debug(str(self.valid_ep()))

	def get_myshows_id(self, imdbId, kinopoiskId):
		# try:
		if True:
			if self.valid():
				for key in self.myshows.keys():
					debug(key)
					section = self.myshows[str(key)]
					if imdbId:
						if section['imdbId'] == imdbId:
							return section['id']

					if kinopoiskId:
						if section['kinopoiskId'] == kinopoiskId:
							return section['id']

					if imdbId is None or kinopoiskId is None:
						return section['id']
		else:
			# except:
			pass

		return 0

	def valid(self):
		if self.myshows != None:
			return len(self.myshows) > 0
		else:
			return False

	def valid_ep(self):
		if self.myshows_ep != None:
			return len(self.myshows_ep) > 0
		else:
			return False

	def data(self):
		if self.valid_ep():
			return self.myshows_ep

		'''
		if self.valid():
			for key in self.myshows.keys():
				return self.myshows.get(key, None)
		'''

		return None

	def getEpisode(self, season, episode):
		res = {}
		if self.valid_ep():
			for episode_data in self.myshows_ep.get('episodes', []):
				ep = self.myshows_ep['episodes'][episode_data]
				if ep['seasonNumber'] != season or ep['episodeNumber'] != episode:
					continue
				for tag in ep:
					if tag in self.dictMyShows:
						res[self.dictMyShows[tag]] = ep[tag]
		return res

	def getYear(self):
		if self.data():
			return self.data().get('year')
		else:
			return None

	def get_premiered(self):
		if self.data():
			s = self.data().get('started')
			if s:
				import datetime, time
				debug(s)
				try:
					try:
						d = datetime.datetime.strptime(s, '%b/%d/%Y')
					except TypeError:
						d = datetime.datetime(*(time.strptime(s, '%b/%d/%Y')[0:6]))
				except:
					d = None
				if d:
					return d.strftime('%Y-%m-%d')
		return None

	def episodes(self, season):
		ren_items = {'airDate': 'aired',
					 'shortName': 'short',
					 'seasonNumber': 'season',
					 'episodeNumber': 'episode'}
		episodes__ = []
		if self.valid_ep():
			for episode in self.myshows_ep['episodes']:
				ep = self.myshows_ep['episodes'][episode].copy()
				if ep['seasonNumber'] == season and ep['episodeNumber'] != 0:
					for key in ren_items:
						ep[ren_items[key]] = ep.pop(key)
					episodes__.append(ep)


		return sorted(episodes__, key=lambda k: k['episode'])

class TVShowAPI(TheTVDBAPI, MyShowsAPI):
	imdb_api	= {}

	@staticmethod
	def get_by(title, ruTitle, imdbId=None, kinopoiskId=None):
		if imdbId and imdbId in TVShowAPI.imdb_api:
			return TVShowAPI.imdb_api[imdbId]

		api = TVShowAPI(title, ruTitle, imdbId, kinopoiskId)
		if imdbId:
			TVShowAPI.imdb_api[imdbId] = api

		return api


	def __init__(self, title, ruTitle, imdbId=None, kinopoiskId=None):
		TheTVDBAPI.__init__(self, imdbId)
		MyShowsAPI.__init__(self, title, ruTitle, imdbId, kinopoiskId)
		#KinopoiskAPI.__init__(self, kinopoiskId)


	def Title(self):
		title = TheTVDBAPI.getTitle(self)
		if title is not None:
			return title

		d = self.data()
		if d is not None:
			try:
				return d.get('ruTitle', None)
			except AttributeError:
				pass

		return None

	def Episode(self, season, episode):
		from ..util.base import stripHtml
		data_ms = MyShowsAPI.getEpisode(self, season, episode)
		data_tmdb = TheTVDBAPI.getEpisode(self, season, episode)

		res = data_ms.copy()
		res.update(data_tmdb)

		if 'plot' in res:
			res['plot'] = stripHtml(res['plot'])

		return res

	def Year(self):
		res = MyShowsAPI.getYear(self)
		return res

	def Premiered(self):
		res = MyShowsAPI.get_premiered(self)
		if res:
			return res
		res = TheTVDBAPI.get_premiered(self)

		return res

'''
class AniDBAPI(object):
	base_url = 'http://api.anidb.net:9001/httpapi?request=anime&client=xbmcscrap&clientver=1&protover=1'
	def __init__(self, title):
'''