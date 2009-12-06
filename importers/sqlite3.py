sql_creation = [
    '''CREATE TABLE PythonCode
         (path TEXT PRIMARY KEY, py BLOB, pyc BLOB, pyo BLOB);''',
    '''CREATE TRIGGER clear_bc AFTER UPDATE OF py ON PythonCode
         BEGIN
           UPDATE PythonCode SET pyc=NULL, pyo=NULL WHERE path = new.path;
         END;''',
]

__doc__ = """
Import machinery for using a sqlite3 database as the storage mechanism for
Python source and bytecode.

The code in this module assumes that the following SQL was used to create the
database being used::

    {sql}

The 'path' column contains the relative, OS-neutral, path (i.e. '/' path
separator) which lacks a file extension for where the file would exist on a
file system. The 'py' column contains the source code, stored as bytes. The
'pyc' and 'pyo' columns store the bytecode based on whether or not ``-O`` has
been passed to the interpreter. Both columns are stored as bytes.

""".format(sql='  \n'.join(sql_creation))

import importlib.abc
from importlib._bootstrap import _check_name  # XXX VERY VERY NAUGHTY!
import os
import sqlite3


def super_paths(path):
    suffix_parts = []
    while path:
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
        database with the proper schema."""
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
        cur = cxn.cursor()
        try:
            cur.execute("""SELECT name FROM sqlite_master
                            WHERE type='table'""")
        except sqlite3.DatabaseError:  # Might be non-DB file.
            raise ValueError
        for rows in cur:
            if rows[0] == 'PythonCode':
                # XXX Verify table columns?
                return cxn
        else:
            raise ValueError


class Finder(importlib.abc.Finder):

    """See if a module is stored in the sqlite3 database."""

    def __init__(self, cxn, db_path, path):
        """Create a finder bound to a sqlite3 connection with the specified
        package path location."""
        self._cxn = cxn
        self._db_path = db_path
        self._path = path

    def find_module(self, fullname):
        """See if the specified module is contained within the database."""
        mod_name = fullname.rpartition('.')[-1]
        if self._path:
            module = '/'.join([self._path, mod_name])
        else:
            module = mod_name
        package = '/'.join([module, '__init__'])
        for path in (package, module):
            cursor = self._cxn.execute('SELECT py, pyc, pyo FROM PythonCode '
                                       'WHERE path=?', [path])
            if cursor.fetchone():
                return Loader(self._cxn, fullname, path)
        else:
            return None


class Loader(importlib.abc.PyPycLoader):

    """Load the module found by the finder.

    The loader will ONLY load the module as passed in during instance creation.
    If other modules are needed then new loader instances should be created by
    the proper finder.

    """

    def __init__(self, cxn, name, path):
        """Store the open database, the name of the found module, and the path
        to the module."""
        self._cxn = cxn
        self._name = name
        self._path = path


    @_check_name
    def source_path(self, fullname):
        # XXX Raise ImportError if source not in the db
        raise NotImplementedError

    def get_data(self, path):
        # XXX return the source or bytecode (do based on file extension)
        raise NotImplementedError

    @_check_name
    def is_package(self, fullname):
        # XXX Base it on the path and if it ends in __init__
        raise NotImplementedError

    @_check_name
    def source_mtime(self, fullname):
        # XXX checks
        return 1

    @_check_name
    def bytecode_path(self, fullname):
        # XXX
        raise NotImplementedError

    @_check_name
    def write_bytecode(self, fullname, bytecode):
        # XXX
        raise NotImplementedError

