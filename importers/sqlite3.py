import os


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

    def __call__(path):
        """Return a finder if the path contains the location of a sqlite3
        database with the proper schema."""
        # XXX normpath
        # XXX normcase
        original_path = path
        # XXX Also check cache as that's cheap.
        while not os.path.exists(path):
            # XXX Does it leave on a trailing '/'? What does that do to
            #     os.path.exists?
            level_up = os.path.dirname(path)
            if level_up == path:
                message = "{} does not contain an existent path"
                raise ImportError(message.format(original_path))
            else:
                path = level_up
        if not os.path.isfile(path):
            raise ImportError("{} is not a file".format(path))
        # XXX verify path is a sqlite3 database; check schema.
        # XXX Return from cache. Key for file location or package path?
        # XXX return finder
