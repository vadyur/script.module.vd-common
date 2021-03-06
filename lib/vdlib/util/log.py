import inspect

try:
	from xbmc import log
except:
	def log(s):
		from .string import decode_string
		s = decode_string(s)
		print(s)

try:
	import xbmcaddon
	_addon = xbmcaddon.Addon('')
	prefix = _addon.getAddonInfo('id')
except (ImportError, RuntimeError) as e:
	prefix = None

import sys
try:
	handle = int(sys.argv[1])
	prefix += ': ' + sys.argv[1]
except:
	pass

def debug(s, line = None):
	from .string import uni_type

	if isinstance(s, BaseException):
		print_tb(s)
		return
	elif not isinstance(s, str) or not isinstance(s, uni_type):
		s = uni_type(s)

	if prefix:
		if line:
			message = u'[{}: {}] {}'.format(prefix, line, s)
		else:
			message = u'[{}]  {}'.format(prefix, s)
	else:
		if line:
			message = u'[{}]  {}'.format(line, s)
		else:
			message =  s
			
	log( message)
	

def print_tb(e=None):
	import sys
	exc_type, exc_val, exc_tb = sys.exc_info()
	import traceback
	traceback.print_exception(exc_type, exc_val, exc_tb, limit=10, file=sys.stderr)

	if e:
		debug(str(e))

def lineno():
	"""Returns the current line number in our program."""
	return inspect.currentframe().f_back.f_lineno

def fprint_tb(filename):
	import sys
	exc_type, exc_val, exc_tb = sys.exc_info()
	import traceback

	from . import filesystem

	with filesystem.fopen(filename, 'w') as out:
		traceback.print_exception(exc_type, exc_val, exc_tb, limit=10, file=out)


class dump_context:
	def __init__(self, module, use_timestamp=True):
		self.module			= module
		self.use_timestamp	= use_timestamp

	def timestamp(self):
		if self.use_timestamp:
			import time
			return time.strftime('%Y%m%d_%H%M%S')
		else:
			return ''

	def filename(self):
		from . import filesystem

		name = self.module + self.timestamp() + '.log'
		try:
			from xbmc import translatePath
			path = translatePath('special://logpath/MA_logs/')
			if not filesystem.exists(path):
				filesystem.makedirs(path)
			_filename = filesystem.join(path, name)
		except ImportError:
			_filename = filesystem.abspath(filesystem.join( __file__ ,'../../..', name))
		return _filename

	def __enter__(self):
		fn = self.filename()

		return self

	def __exit__(self, exc_type, exc_val, exc_tb):
		from . import filesystem
		if exc_type:
			with filesystem.fopen(self.filename(), 'w') as out:
				import traceback
				traceback.print_exception(exc_type, exc_val, exc_tb, limit=10, file=out)
			return True
