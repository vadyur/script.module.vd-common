# -*- coding: utf-8 -*-
KB = 1024
MB = KB * KB
GB = KB * MB

from sys import version_info
from . import filesystem

def make_fullpath(title, ext):
	if filesystem._is_abs_path(title):
		dir_path = filesystem.dirname(title)
		filename = filesystem.basename(title)
		pass
	else:
		dir_path = None
		filename = title

	if '/' in title:
		pass

	result = filename.replace(':', '').replace('/', '#').replace('?', '').replace('"', "''").strip() + ext
	if dir_path:
		result = filesystem.join(dir_path, result)

	return result

def remove_script_tags(file):
	import re
	pattern = r'<script[\s\S]+?/script>'
	subst = ""
	if version_info >= (3, 0) and isinstance(file, bytes):
		pattern = pattern.encode('utf-8')
		subst = b""

	c_pattern = re.compile(pattern)
	return re.sub(c_pattern, subst, file)

def clean_html(page):
	page = remove_script_tags(page)

	if version_info >= (3, 0) and isinstance(page, bytes):
		return page.replace(b"</sc'+'ript>", b"").replace(b'</bo"+"dy>', b'').replace(b'</ht"+"ml>', b'')
	else:
		return page.replace("</sc'+'ript>", "").replace('</bo"+"dy>', '').replace('</ht"+"ml>', '')

def striphtml(data):
	import re
	p = re.compile(r'<.*?>')
	return p.sub('', data)

def detect_mpg(str_detect):
	try:
		str_detect = str_detect.lower()
		return 'divx' in str_detect or 'xvid' in str_detect or 'mpeg2' in str_detect or 'mpeg-2' in str_detect
	except:
		return False

def detect_h264(str_detect):
	try:
		str_detect = str_detect.lower()
		return 'avc' in str_detect or 'h264' in str_detect or 'h.264' in str_detect
	except:
		return False

def detect_h265(str_detect):
	try:
		str_detect = str_detect.lower()
		return 'hevc' in str_detect or 'h265' in str_detect or 'h.265' in str_detect
	except:
		return False

stripPairs = (
	('<p>', '\n'),
	('<li>', '\n'),
	('<br>', '\n'),
	('<.+?>', ' '),
	('</.+?>', ' '),
	('&nbsp;', ' ',),
	('&laquo;', '"',),
	('&raquo;', '"',),
	('&ndash;', '-'),
)

def stripHtml(string):
	import re
	# from xml.sax.saxutils import unescape
	for (html, replacement) in stripPairs:
		string = re.sub(html, replacement, string)

	string = string.replace('&mdash;', u'—')
	string = string.replace('&#151;', u'—')
	return string.strip(' \t\n\r')

def is_file_playable(name):
	import os
	filename, file_extension = os.path.splitext(name)
	return file_extension in ['.mkv', '.mp4', '.ts', '.avi', '.m2ts', '.mov']
