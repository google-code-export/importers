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

from . import remove_file
from . import abc as importers_abc
import os
import sqlite3
import time


def neutralpath(path):
    """Convert a path to only use forward slashes."""
    if os.sep != '/':
        return path.replace(os.sep, '/')
    else:
        return path


class Hook(importers_abc.ArchiveHook):

    """Archive hook for sqlite3 databases"""

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

    def finder(self, archive, archive_path, location):
        """Return a sqlite3 importer."""
        return Importer(archive, archive_path, location)


class Importer(importers_abc.PyFileFinder, importers_abc.PyPycFileLoader):

    """Importer for sqlite3 databases."""

    def __init__(self, db, db_path, location):
        super().__init__(os.path.join(db_path, location))
        self._cxn = db
        self._db_path = db_path

    def loader(self, *args, **kwargs):
        return self

    def file_exists(self, path):
        try:
            path = remove_file(self._db_path, path)
        except ValueError:
            return False
        path = neutralpath(path)
        with self._cxn:
            cursor = self._cxn.execute('SELECT path FROM FS WHERE path=?',
                                        [path])
            return bool(cursor.fetchone())

    def get_data(self, path):
        """Return data for the path.

        If the path is relative it is assumed to be anchored to the root of the
        database.

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

    def path_mtime(self, path):
        """Return the modification time for the path."""
        path = neutralpath(remove_file(self._db_path, path))
        with self._cxn:
            cursor = self._cxn.execute('SELECT mtime FROM FS WHERE path=?',
                                        [path])
            result = cursor.fetchone()
            if not result:
                raise IOError("{} does not exist".format(path))
            return result[0]

    def write_data(self, path, data):
        """Write the data to the path."""
        path = neutralpath(remove_file(self._db_path, path))
        with self._cxn:
            self._cxn.execute('INSERT OR REPLACE INTO FS VALUES (?, ?, ?)',
                                [path, int(time.time()), data])
        return True
