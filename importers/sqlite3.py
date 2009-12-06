sql_creation = """CREATE TABLE FS (path TEXT PRIMARY KEY, data BLOB);"""

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


# XXX Best to use OS-neutral paths or let users deal with it?
def super_paths(path):
    suffix_parts = []
    while path:
        # XXX Escape pre-existing backslashes
        yield path, os.sep.join(suffix_parts)
        new_path, suffix_part = os.path.split(path)
        # Since os.path.split('/') == ('/', '') ...
        if new_path == path:
            break
        else:
            path = new_path
            suffix_parts.append(suffix_part)


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
        with self._cxn:
            cursor = self._cxn.execute('SELECT path FROM FS WHERE path=?',
                                        [path])
            return bool(cursor.fetchone())

    def loader(self, fullname, path):
        return Loader(self._cxn, self._db_path, fullname, path)

    def find_module(self, fullname):
        """See if the specified module is contained within the database."""
        mod_name = fullname.rpartition('.')[-1]
        extensions = _suffix_list(imp.PY_COMPILED) + _suffix_list(imp.PY_SOURCE)
        if self._path:
            module = '/'.join([self._path, mod_name])
        else:
            module = mod_name
        package = '/'.join([module, '__init__'])
        for base_path, is_pkg in ((package, True), (module, False)):
            for ext in extensions:
                path = base_path + ext
                if path in self:
                    return self.loader(fullname, path)
        else:
            return None


class Loader(importlib.abc.PyPycLoader):

    """Load the module found by the finder.

    The loader will ONLY load the module as passed in during instance creation.
    If other modules are needed then new loader instances should be created by
    the proper finder.

    """

    def __init__(self, cxn, db_path, name, path):
        """Store the open database, the name of the found module, and the path
        to the module."""
        self._cxn = cxn
        self._name = name
        self._path = path

    def fetch_code(self):
        """Return the source and bytecode (if any) for the path the loader was
        created for."""
        sql_select = ('SELECT py, py{} FROM PythonCode '
                      'WHERE path=?'.format('c' if __debug__ else 'o'))

        with self._cxn:
            cursor = self._cxn.execute(sql_select, [self._path])
            return tuple(cursor)

    @_check_name
    def source_path(self, fullname):
        """Return the source 'path' to the module if the source is available,
        return None if bytecode exists, else raise ImportError.

        A two-item tuple is returned for source path where the second item is
        the string 'py'.

        """
        source, bytecode = self.fetch_code()
        if source:
            return (self._path, 'py')
        elif bytecode:
            return None
        else:
            raise ImportError('{} cannot be handled by this '
                                'loader'.format(fullname))

    def get_data(self, path):
        """Return data for the path.

        Source and bytecode paths are represented by a two-item tuple. The
        first item is the path to the module being loaded. The second item
        specifies whether the path represents source or bytecode.

        """
        if (isinstance(path, collections.Sequence) and len(path) == 2 and
                path[0] == self.__path and path[1] in {'py', 'pyc', 'pyo'}):
            source, bytecode = self.fetch_code()
            if path[1] == 'py':
                return source
            if path[1] == 'pyc' and __debug__:
                return bytecode
            elif path[1] == 'pyo' and not __debug__:
                return bytecode
        # Fall-through failure case.
        raise IOError("the path {!r} does not exist".format(path))

    @_check_name
    def is_package(self, fullname):
        """Return if the module is a package based on whether the path ends in
        '/__init__'."""
        return self._path.endswith('/__init__')

    @_check_name
    def source_mtime(self, fullname):
        """Return 1 for the source mtime.

        Database trigger should guarantee that if the 'py' column is changed
        for a row that the 'pyc' and 'pyo' columns are set to NULL.

        """
        return 1

    @_check_name
    def bytecode_path(self, fullname):
        """Return the path to the bytecode of the module (if present), None if
        source is present, or raise ImportError.

        A two-item tuple is used to represent the path. The first item is the
        path itself with the second item being either 'pyc' or 'pyo' depending
        on whether __debug__ is true.

        """
        source, bytecode = self.fetch_code()
        if bytecode:
            return (self._path, 'py{}'.format('c' if __debug__ else 'o'))
        elif source:
            return None
        else:
            raise ImportError('{} is not handled by this '
                                'loader'.format(fullname))

    @_check_name
    def write_bytecode(self, fullname, bytecode):
        """Write the bytecode into the database."""
        bc_column = 'py{}'.format('c' if __debug__ else 'o')
