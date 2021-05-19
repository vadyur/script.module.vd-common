# -*- coding: utf-8 -*-

from ..util import filesystem, log

from .kodidb import VideoDatabase
from .compat import translatePath

SOURCES_XML_PATH = 'special://userdata/sources.xml'
SOURCES_REAL_PATH = translatePath(SOURCES_XML_PATH)

scrapper_settings = {
	'metadata.themoviedb.org': '<settings version="2"><setting id="keeporiginaltitle" default="true">false</setting><setting id="fanart">true</setting><setting id="landscape" default="true">false</setting><setting id="trailer">true</setting><setting id="language">ru</setting><setting id="tmdbcertcountry" default="true">us</setting><setting id="RatingS" default="true">TMDb</setting><setting id="imdbanyway" default="true">false</setting><setting id="certprefix" default="true">Rated </setting></settings>',
	'metadata.tvshows.themoviedb.org': '<settings version="2"><setting id="keeporiginaltitle" default="true">false</setting><setting id="language" default="true">ru</setting><setting id="titleprefix" default="true">Episode </setting><setting id="titlesuffix" default="true" /><setting id="tmdbart">true</setting><setting id="fanarttvart">true</setting><setting id="tvdbwidebanners">true</setting><setting id="RatingS" default="true">Themoviedb</setting><setting id="fallback">true</setting><setting id="alsoimdb" default="true">false</setting><setting id="tmdbcertcountry" default="true">us</setting><setting id="certprefix" default="true" /></settings>',
}

def need_create(settings):
	if not filesystem.exists(settings.base_path()):
		return True

	# sources = Sources()

	if settings.anime_save and not filesystem.exists(settings.anime_tvshow_path()):
		return True

	if settings.animation_save and not filesystem.exists(settings.animation_path()):
		return True

	if settings.animation_tvshows_save and not filesystem.exists(settings.animation_tvshow_path()):
		return True

	if settings.tvshows_save and not filesystem.exists(settings.tvshow_path()):
		return True

	if settings.documentary_save and not filesystem.exists(settings.documentary_path()):
		return True

	return False

def create_movies_and_tvshows(path, scrapper='metadata.local', scrapper_tv='metadata.local', suffix=''):
	sources = Sources()

	def base_path():
		return path

	path1 = filesystem.join(base_path(), 'Movies')
	if not filesystem.exists(path1):
		filesystem.makedirs(path1)
	sources.add_video(path1, u'Фильмы', 'movies', scrapper, suffix)
	
	path2 = filesystem.join(base_path(), 'TVShows')
	if not filesystem.exists(path2):
		filesystem.makedirs(path2)
	sources.add_video(path2, u'Сериалы', 'tvshows', scrapper_tv, suffix)

	return True

def create(settings, scrapper='metadata.local', scrapper_tv='metadata.local'):

	need_restart = False
	sources = Sources()

	with filesystem.save_make_chdir_context(settings.base_path(), 'sources.create'):

		if settings.anime_save:
			path = settings.anime_tvshow_path()
			if not filesystem.exists(path):
				filesystem.makedirs(path)
			sources.add_video(path, u'Аниме', 'tvshows', scrapper_tv)
			need_restart = True

		if settings.animation_save:
			path = settings.animation_path()
			if not filesystem.exists(path):
				filesystem.makedirs(path)
			sources.add_video(path, u'Мультфильмы', 'movies', scrapper)
			need_restart = True

		if settings.animation_tvshows_save:
			path = settings.animation_tvshow_path()
			if not filesystem.exists(path):
				filesystem.makedirs(path)
			sources.add_video(path, u'Мультсериалы', 'tvshows', scrapper_tv)
			need_restart = True

		if settings.tvshows_save:
			path = settings.tvshow_path()
			if not filesystem.exists(path):
				filesystem.makedirs(path)
			sources.add_video(path, u'Сериалы', 'tvshows', scrapper_tv)
			need_restart = True

		if settings.documentary_save:
			path = settings.documentary_path()
			if not filesystem.exists(path):
				filesystem.makedirs(path)
			sources.add_video(path, u'Документальное', 'movies', scrapper)
			need_restart = True

		if settings.movies_save:
			path = settings.movies_path()
			if not filesystem.exists(path):
				filesystem.makedirs(path)
			sources.add_video(path, u'Фильмы', 'movies', scrapper)
			need_restart = True

	return need_restart


from collections import namedtuple

# noinspection PyPep8Naming
import xml.etree.ElementTree as ET

Source = namedtuple('Source', ['type', 'path', 'label'])


class SourcesException(Exception):
	pass


class SourceAlreadyExists(SourcesException):
	def __init__(self, *args, **kwargs):
		label = kwargs.pop('label')
		super(SourceAlreadyExists, self).__init__(self, 'Source with label "%s" already exists' % label,
												  *args, **kwargs)


class UnknownMediaType(SourcesException):
	def __init__(self, *args, **kwargs):
		media_type = kwargs.pop('media_type')
		super(UnknownMediaType, self).__init__(self, 'Unknown media type: %s' % media_type,
											   *args, **kwargs)


def comp_str_nc(s1, s2):
	if s1 and s2:
		return s1.lower() == s2.lower()

	return s1 == s2


class Sources(object):

	def __init__(self):
		if not filesystem.exists(SOURCES_REAL_PATH):
			with filesystem.fopen(SOURCES_REAL_PATH, 'w') as src:
				src.write('<sources>\n'
						  '    <programs>\n'
				          '        <default pathversion="1"></default>\n'
				          '    </programs>\n'
				          '    <video>\n'
				          '        <default pathversion="1"></default>\n'
				          '    </video>\n'
				          '    <music>\n'
				          '        <default pathversion="1"></default>\n'
				          '    </music>\n'
				          '    <pictures>\n'
				          '        <default pathversion="1"></default>\n'
				          '    </pictures>\n'
				          '    <files>\n'
				          '        <default pathversion="1"></default>\n'
				          '    </files>\n'
						  '</sources>\n'
				)

		self.xml_tree = ET.parse(SOURCES_REAL_PATH)
		self.sources = None

	def get(self, media_type=None, normalize=True):
		if self.sources is None:
			self.sources = []
			for t in self.xml_tree.getroot():
				m_type = t.tag
				if media_type is not None and m_type != media_type:
					continue
				for s in t.findall('source'):
					label = s.find('name').text
					if normalize:
						path = filesystem.normpath(s.find('path').text)
					else:
						path = s.find('path').text
					self.sources.append(Source(m_type, path, label))
		return self.sources

	def has(self, media_type=None, label=None, path=None):
		if path:
			path = filesystem.normpath(path)
		return any((comp_str_nc(s.path, path) or path is None) and (s.label == label or label is None)
				   for s in self.get(media_type))

	def add(self, media_type, path, label):
		if self.has(media_type, label, path):
			raise SourceAlreadyExists(label=label)
		for t in self.xml_tree.getroot():
			if t.tag == media_type:
				s = ET.SubElement(t, 'source')
				ET.SubElement(s, 'name').text = label
				ET.SubElement(s, 'path', {'pathversion': '1'}).text = path
				ET.SubElement(s, 'allowsharing').text = 'true'
				self.xml_tree.write(SOURCES_REAL_PATH, 'utf-8')
				return
		raise UnknownMediaType(media_type=media_type)

	def add_video(self, path, label, content, scrapper, suffix=''):
		label = label + suffix
		path = filesystem.join(path, '')
		try:
			self.add('video', path, label)
		except SourceAlreadyExists as e:
			log.print_tb(e)

		db = VideoDB()
		scan_recursive = bool(content == 'movies')
		db.update_path(path, content, scan_recursive, 0, 0, scrapper=scrapper)


class VideoDB(VideoDatabase):
	def __init__(self):
		VideoDatabase.__init__(self)
		self.conn = self.create_connection()

	def get_path(self, path):
		# self.ensure_connected()
		c = self.conn.cursor()
		c.execute(self.sql_request("SELECT * FROM path WHERE strPath=?"), (path,))
		return c.fetchone()

	def path_exists(self, path):
		return bool(self.get_path(path))

	def update_path(self, path, content, 
					scan_recursive=False, 
					use_folder_names=False, 
					no_update=False, 
					scrapper = 'metadata.local'):
		scan_recursive = 2147483647 if scan_recursive else 0

		str_settings=scrapper_settings.get(scrapper, '')

		c = self.conn.cursor()
		if self.path_exists(path):
			c.execute(self.sql_request(
				"UPDATE path SET strContent=?, strScraper=?, scanRecursive=?, "
				"useFolderNames=?, strSettings=?, noUpdate=?, exclude=0 WHERE strPath=?"),
				(content, scrapper, scan_recursive, use_folder_names, str_settings, no_update, path))
		else:
			now_func = 'NOW()' if self.DB == 'mysql' else "DATETIME('now')"
		
			c.execute(self.sql_request(
				"INSERT INTO path (strPath, strContent, strScraper, scanRecursive, "
				"useFolderNames, strSettings, noUpdate, exclude, dateAdded) "
				"VALUES (?, ?, ?, ?, ?, ?, ?, 0, " + now_func + ")"),
				(path, content, scrapper, scan_recursive, use_folder_names, str_settings, no_update))

		self.conn.commit()
