sql_creation = """CREATE TABLE FS
                    (path TEXT PRIMARY KEY, mtime INTEGER, data BLOB);"""

__doc__ = """
Import machinery for using a sqlite3 database as the storage mechanism for
Python source and bytecode.

The code in this module assumes that the following SQL was used to create the
database being used::

  {}

The 'path' column contains the relative, OS-neutral path (i.e. '/' path
separator only) of the files stored in the database. The 'data' column is the
raw bytes for that file.

""".format(sql_creation)

import imp
import importlib.abc
# XXX VERY VERY NAUGHTY!
from importlib._bootstrap import _check_name, _suffix_list
import os
import sqlite3
import time


def neutralpath(path):
    """Convert a path to only use forward slashes."""
    if os.sep != '/':
        return path.replace(os.sep, '/')
    else:
        return path


def super_paths(path):
    suffix_parts = []
    while path:
        # XXX Escape pre-existing backslashes
        yield path, os.path.join(suffix_parts)
        new_path, suffix_part = os.path.split(path)
        # Since os.path.split('/') == ('/', '') ...
        if new_path == path:
            break
        else:
            path = new_path
            suffix_parts.append(suffix_part)


def remove_file(file_path, full_path):
    if not full_path.startswith(file_path + os.sep):
        raise ValueError('{} does not start with {}'.format(full_path,
                                                            file_path))
    return full_path[len(file_path)+len(os.sep):]


class Hook:

    """sys.path_hook callable for sqlite3 databases.

    Connection objects are cached for future re-use.

    """

    def __init__(self):
        """Initialize the hook."""
        self._cxn_cache = {}

    def __del__(self):
        """Close all cached Connection objects."""
        for cxn in self._cxn_cache.values():
            cxn.close()

    def __call__(self, path):
        """Return a finder if the path contains the location of a sqlite3
        database with the required table."""
        original = path
        for subpath, suffix in super_paths(path):
            if subpath in self._cxn_cache:
                return Finder(self._cxn_cache[subpath], subpath, suffix)

        for subpath, suffix in super_paths(path):
            if os.path.isfile(subpath):
                try:
                    cxn = self.open(subpath)
                    self._cxn_cache[subpath] = cxn
                    return Finder(cxn, subpath, suffix)
                except ValueError:
                    continue
            elif os.path.isdir(subpath):
                message = "{} does not contain a file path"
                raise ImportError(message.format(original))
        else:
            message = "{} does not contain a path to a proper sqlite3 database"
            raise ImportError(message.format(original))

    def open(self, path):
        """Verify that a path points to a sqlite3 database."""
        cxn = sqlite3.connect(path, detect_types=sqlite3.PARSE_DECLTYPES)
        try:
            with cxn:
                cursor = cxn.execute("""SELECT name FROM sqlite_master
                                        WHERE type='table' and name='FS'""")
                if len(list(cursor)) == 1:
                    # XXX Verify table structure?
                    return cxn
                else:
                    raise ValueError
        except sqlite3.DatabaseError:
            raise ValueError  # Path is not a sqlite3 file.


class Finder(importlib.abc.Finder):

    """See if a module is stored in the sqlite3 database."""

    def __init__(self, cxn, db_path, path):
        """Create a finder bound to a sqlite3 connection with the specified
        package path location."""
        self._cxn = cxn
        self._db_path = db_path
        self._path = path

    def __contains__(self, path):
        """Return True if the path is in the db."""
        path = neutralpath(path)
        with self._cxn:
            cursor = self._cxn.execute('SELECT path FROM FS WHERE path=?',
                                        [path])
            return bool(cursor.fetchone())

    def loader(self, fullname, path, is_pkg):
        return Loader(self._cxn, self._db_path, fullname, path, is_pkg)

    def find_module(self, fullname):
        """See if the specified module is contained within the database."""
        mod_name = fullname.rpartition('.')[-1]
        extensions = _suffix_list(imp.PY_COMPILED) + _suffix_list(imp.PY_SOURCE)
        if self._path:
            module = os.path.join(self._path, mod_name)
        else:
            module = mod_name
        package = os.path.join(module, '__init__')
        for base_path, is_pkg in ((package, True), (module, False)):
            for ext in extensions:
                path = base_path + ext
                if path in self:
                    return self.loader(fullname, path, is_pkg)
        else:
            return None


class Loader(importlib.abc.PyPycLoader):

    """Load the module found by the finder.

    The loader will ONLY load the module as passed in during instance creation.
    If other modules are needed then new loader instances should be created by
    the proper finder.

    """

    def __init__(self, cxn, db_path, name, path, is_pkg):
        """Store the open database, the name of the found module, and the path
        to the module."""
        self._cxn = cxn
        self._db_path = db_path
        self._name = name
        self._path = path
        self._is_pkg = is_pkg

    def _path_exists(self, path):
        path = neutralpath(path)
        with self._cxn:
            cursor = self._cxn.execute('SELECT path FROM FS WHERE path=?',
                                        [path])
            return bool(cursor.fetchone())

    @_check_name
    def source_path(self, fullname):
        """Return the source 'path' to the module if the source is available,
        else return None.

        Validity checks if the module can be imported through bytecode is
        handled based on the finder that created this loader found
        **something** and no source was found.

        """
        for ext in _suffix_list(imp.PY_SOURCE):
            path = os.path.splitext(self._path)[0] + ext
            if self._path_exists(path):
                return os.path.join(self._db_path, path)
        else:
            return None

    @_check_name
    def bytecode_path(self, fullname):
        """Return the path to the bytecode of the module (if present), else
        return None.

        It is assumed that the loader can handle loading the module from source
        if the bytecode doesn't exist as the finder would not have found
        anything for the module.

        """
        for ext in _suffix_list(imp.PY_COMPILED):
            path = os.path.splitext(self._path)[0] + ext
            if self._path_exists(path):
                return os.path.join(self._db_path, path)
            else:
                return None

    def get_data(self, path):
        """Return data for the path.

        If a path is relative it is assumed to be anchored to the root of the
        db.

        """
        if os.path.isabs(path):
            if not path.startswith(self._db_path + os.sep):
                raise IOError("{} not pointing to {}".format(path,
                                                             self._db_path))
            path = path[len(self._db_path)+1:]
        path = neutralpath(path)
        with self._cxn:
            cursor = self._cxn.execute('SELECT data FROM FS WHERE path=?',
                                        [path])
            result = cursor.fetchone()
            if result:
                return result[0]
        # Fall-through failure case.
        raise IOError("the path {!r} does not exist".format(path))

    @_check_name
    def is_package(self, fullname):
        """Return if the module is a package."""
        return self._is_pkg

    @_check_name
    def source_mtime(self, fullname):
        """Return the source mtime.

        Because sqlite3 BEFORE triggers have undefined behavior if used on the
        row being updated there is no database schema protection to make sure
        the mtime for a source file is updated if modified.

        """
        path = self.source_path(fullname)
        path = neutralpath(remove_file(self._db_path, path))
        with self._cxn:
            cursor = self._cxn.execute('SELECT mtime FROM FS WHERE path=?',
                                        [path])
            return cursor.fetchone()[0]

    @_check_name
    def write_bytecode(self, fullname, bytecode):
        """Write the bytecode into the database."""
        path = self.bytecode_path(fullname)
        if path is None:
            path = self.source_path(fullname) + 'c' if __debug__ else 'o'
        path = remove_file(self._db_path, path)
        path = neutralpath(path)
        with self._cxn:
            self._cxn.execute('INSERT OR REPLACE INTO FS VALUES (?, ?, ?)',
                                [path, int(time.time()), bytecode])
