"""Import machinery for using a sqlite3 database as the storage mechanism for
Python source and bytecode.

path | source | bytecode | optimized
XXX separate table for bytecode and use trigger to update?

"""
import importlib.abc
import os

# XXX generator for paths starting from the bottom and working your way up

def super_paths(path):
    path_parts = path.split(os.sep)
    for pivot in range(len(path_parts)):
        yield (os.sep.join(path_parts[:-pivot]),
                os.sep.join(path_parts[-pivot:]))


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
        for path, suffix in super_paths(path):
            if path in self.cxn_cache:
                return Finder(self._cxn_cache[path], path, suffix)

        for path, suffix in super_paths(path):
            if os.path.isfile(path):
                try:
                    cxn = self.open(path)
                    self.cxn_cache[path] = cxn
                    return Finder(cxn, path, suffix)
                except ValueError:
                    continue
            elif os.path.isdir(path):
                message = "{} does not contain a file path"
                raise ImportError(message.format(original))
        else:
            message = "{} does not contain a path to a proper sqlite3 database"
            raise ImportError(message.format(original))

    def open(self, path):
        """Verify that a path points to a sqlite3 database."""
        cxn = sqlite3.connect(path)
        cur = cxn.cursor()
        # XXX Use an OR check for name field to verify all tables exist
        cur.execute("""SELECT name FROM sqlite_master
                        WHERE type='table';""")
        tables = list(cur)
        # XXX Verify all desired tables exist; check schema w/ sql column?
        raise ValueError


class Finder(importlib.abc.Finder):

    """See if a module is stored in the sqlite3 database."""

    def __init__(self, cxn, db_path, path):
        """Create a finder bound to a sqlite3 connection with the specified
        package path location."""
        self._cxn = cxn
        # XXX Normalize paths to match how DB would have been constructed
        #     e.g. forward slash
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
