import time, os, pickle, hashlib
from functools import wraps
from shutil import copyfile
from copy import deepcopy
from typing import Callable, Any, Union
import atexit



class Storage():
    def __init__(self, storage_dir, filename='storage.pcl'):
        """
        Class constructor

        :type storage_dir: str
        :type filename: str
        """
        self._storage = {}
        self._hash = None
        self._filename = os.path.join(storage_dir, filename)
        try:
            with open(self._filename, 'rb') as fo:
                contents = fo.read()
            self._storage = pickle.loads(contents)
            self._hash = hashlib.md5(contents).hexdigest()
        except (IOError, pickle.PickleError, EOFError, AttributeError):
            pass

    def __enter__(self):
        return self

    def __exit__(self, t, v, tb):
        self.flush()

    def __getitem__(self, key):
        return self._storage[key]

    def __setitem__(self, key, value):
        self._storage[key] = value

    def __delitem__(self, key):
        del self._storage[key]

    def __iter__(self):
        return iter(self._storage)

    def __len__(self):
        return len(self._storage)

    def __str__(self):
        return '<Storage {0}>'.format(self._storage)

    def flush(self):
        print(f"Flushing storage to {self._filename}")
        """
        Save storage contents to disk

        This method saves new and changed :class:`Storage` contents to disk
        and invalidates the Storage instance. Unchanged Storage is not saved
        but simply invalidated.
        """
        contents = pickle.dumps(self._storage, protocol=2)
        if self._hash is None or hashlib.md5(contents).hexdigest() != self._hash:
            tmp = self._filename + '.tmp'
            start = time.time()
            while os.path.exists(tmp):
                if time.time() - start > 2.0:
                    raise TimeoutError(
                        'Exceeded timeout for saving {0} contents!'.format(self)
                    )
                time.sleep(0.1)
            try:
                with open(tmp, 'wb') as fo:
                    fo.write(contents)
                copyfile(tmp, self._filename)
            finally:
                if os.path.exists(tmp):
                    os.remove(tmp)

    def copy(self):
        """
        Make a copy of storage contents

        .. note:: this method performs a *deep* copy operation.

        :return: a copy of storage contents
        :rtype: dict
        """
        return deepcopy(self._storage)

import xbmc
use_simpleplugin = not hasattr(xbmc, '__kodistubs__')

storage_path = '.'
if use_simpleplugin:
    try:
        from simpleplugin import Plugin
        plugin = Plugin()
        mem_storage = plugin.get_mem_storage('***cache***')
        storage_path = plugin.profile_dir
    except ImportError:
        use_simpleplugin = False

if not use_simpleplugin:
    mem_storage = {}

storage = Storage(storage_path)
atexit.register(storage.flush)

def _get_duration_in_seconds(duration: Union[int, float, str]) -> float:
    """
    Convert duration to seconds.
    Supports:
        - 's' for seconds
        - 'm' for minutes
        - 'h' for hours
        - 'd' for days
        - int/float: treated as minutes
    """
    if isinstance(duration, str):
        duration = duration.strip().lower()
        if duration.endswith('s'):
            return int(duration[:-1])
        if duration.endswith('m'):
            return int(duration[:-1]) * 60
        if duration.endswith('h'):
            return int(duration[:-1]) * 60 * 60
        if duration.endswith('d'):
            return int(duration[:-1]) * 60 * 60 * 24
        # It's a string but without a recognized suffix, treat as minutes.
        return float(duration) * 60
    # It's a number. Treat as minutes.
    return duration * 60


def cached(duration: Union[int, float, str] = 10) -> Callable:
    """
    Decorator to cache function results using a persistent storage (e.g., dict-like object on disk).

    :param storage: dict-like persistent storage (must support __getitem__, __setitem__)
    :param duration: Cache duration. A number is interpreted as minutes.
                     A string can be specified with a suffix of 'm' for minutes or 's' for seconds.
                     E.g., '10m', '600s'. Default is 10 minutes.
    """
    seconds = _get_duration_in_seconds(duration)
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            key = func.__name__ + str(args) + str(kwargs)
            now = time.time()
            try:
                data, timestamp = storage[key]
                if now - timestamp < seconds:
                    return data
            except Exception:
                pass
            data = func(*args, **kwargs)
            storage[key] = (data, now)
            return data
        return wrapper
    return decorator

def mem_cached(duration: Union[int, float, str] = 10) -> Callable:
    """
    Decorator to cache function results using an in-memory storage (e.g., dict).

    :param mem_storage: dict-like in-memory storage (must support __getitem__, __setitem__)
    :param duration: Cache duration. A number is interpreted as minutes.
                     A string can be specified with a suffix of 'm' for minutes or 's' for seconds.
                     E.g., '10m', '600s'. Default is 10 minutes.
    """
    seconds = _get_duration_in_seconds(duration)
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            key = func.__name__ + str(args) + str(kwargs)
            now = time.time()
            try:
                data, timestamp = mem_storage[key]
                if now - timestamp < seconds:
                    return data
            except Exception:
                pass
            data = func(*args, **kwargs)
            mem_storage[key] = (data, now)
            return data
        return wrapper
    return decorator
