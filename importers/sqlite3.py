"""Import machinery for using a sqlite3 database as the storage mechanism for
Python source and bytecode.

path | source | bytecode | optimized

"""
import importlib.abc
import os
import sqlite3


def super_paths(path):
    suffix_parts = []
    while path:
        yield path, os.sep.join(suffix_parts)
        new_path, suffix_part = os.path.split(path)
        # os.path.split('/') == ('/', '')
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
        cxn = sqlite3.connect(path)
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
        self._path = path
        self._full_path = os.path.join(db_path, path)

    def find_module(self, fullname):
        """See if the specified module is contained within the database."""
        # XXX Create path
        # XXX See if in DB


class Loader(importlib.abc.PyLoader):

    def source_path(self, fullname):
        # XXX Raise ImportError if source not in the db
        raise NotImplementedError

    def get_data(self, path):
        # XXX return the source
        raise NotImplementedError

    def is_package(self, fullname):
        # XXX Base it on the path and if it ends in __init__
        raise NotImplementedError
