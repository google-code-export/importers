import abc
import collections
import imp
import importlib.abc
import os


def _super_paths(path):
    """Returns an iterator which yields a pair of paths created by splitting
    the original path at different points.

    Splitting starts from the end of the path and works backwards. This is to
    allow for an optimization where if a file is desired but a directory is
    found first then the search can cease early.

    """
    suffix_parts = collections.deque(maxlen=path.count(os.sep))
    while path:
        yield path, (os.path.join(*suffix_parts) if suffix_parts else '')
        new_path, suffix_part = os.path.split(path)
        # Since os.path.split('/') == ('/', '') ...
        if new_path == path:
            break
        else:
            path = new_path
            suffix_parts.appendleft(suffix_part)


def _file_search(location, fullname, exists, *types_):
    """Search for a file representing the module in the specified location of
    the proper type.

    'exists' is expected to be a callable that takes a file path and returns a
    boolean on whether the path exists or not. 'types_' contains the file types
    the module can be as represented by imp module constants
    (e.g.  imp.PY_SOURCE).

    """
    tail_name = fullname.rpartition('.')[-1]
    extensions = [x[0] for x in imp.get_suffixes()
                    if x[2] in types_]
    module_path = os.path.join(location, tail_name)
    pkg_path = os.path.join(module_path, '__init__')
    for base_path in (pkg_path, module_path):
        for ext in extensions:
            path = base_path + ext
            if exists(path):
                return path
    else:
        return None


def _is_package_file(path):
    """Check if a file path is for a package's __init__ file."""
    file_name = os.path.basename(path)
    return os.path.splitext(file_name)[0] == '__init__'


class ArchiveHook(metaclass=abc.ABCMeta):

    """ABC for path hooks handling archive files (e.g. zipfiles).

    The hook keeps a cache of opened archives so that multiple connections to
    the archive files are not needed. Deletion of the hook will call the
    close() method on all archives.

    Abstract methods:

        * open
        * finder

    """

    def __init__(self):
        """Initialize the internal cache of archives."""
        self._archives = {}

    def __del__(self):
        """Close all archives, raising the last exception triggered
        (if any)."""
        exception = None
        for archive in self._archives:
            try:
                archive.close()
            except AttributeError:
                continue
            except Exception as exc:
                exception = exc
        if exception:
            raise exception

    @abc.abstractmethod
    def open(self, path:str) -> object:
        """Open the (potential) path to an archive, raising ValueError if it is
        not a path to an archive."""
        raise NotImplementedError

    @abc.abstractmethod
    def finder(self, archive:object, archive_path:str, location:str) -> importlib.abc.Finder:
        """Return a finder for the open archive at the specified location."""
        raise NotImplementedError

    def __call__(self, path):
        """See if the path contains an archive file path, returning a finder if
        appropriate."""
        for pre_path, location in _super_paths(path):
            if pre_path in self._archives:
                return self.finder(self._archives[pre_path], pre_path,
                                    location)

        for pre_path, location in _super_paths(path):
            if os.path.isfile(pre_path):
                try:
                    archive = self.open(pre_path)
                except ValueError:
                    continue
                self._archives[pre_path] = archive
                return self.finder(archive, pre_path, location)
            elif os.path.isdir(pre_path):
                msg = "{} does not contain a file path".format(path)
                raise ImportError(msg)
        else:
            msg = "{} does not contain a path to an archive".format(path)
            raise ImportError(msg)


class PyFileFinder(importlib.abc.Finder):

    """ABC for finding Python source files.

    Abstract methods:

        * file_exists
        * loader

    """

    def __init__(self, location):
        """Store the location that the finder searches in."""
        self.location = location

    @abc.abstractmethod
    def file_exists(self, path:str) -> bool:
        """Return true if the path exists, else false."""
        raise NotImplementedError

    @abc.abstractmethod
    def loader(self, fullname:str, path:str) -> importlib.abc.Loader:
        """Return the loader for the module found at the specified path."""
        raise NotImplementedError

    def find_module(self, fullname):
        """Find the module's file path."""
        path = _file_search(self.location, fullname, self.file_exists,
                            imp.PY_SOURCE, imp.PY_COMPILED)
        if path is not None:
            return self.loader(fullname, path)
        else:
            return None


class PyFileLoader(importlib.abc.PyLoader):

    """ABC for loading Python source files.

    Abstract methods:

        * get_data: inherited
        * file_exists

    """

    def __init__(self, location):
        """Store the location that the loader searches in."""
        self.location = location

    @abc.abstractmethod
    def file_exists(self, path:str) -> bool:
        """Return true if the file exists, else false."""
        raise NotImplementedError

    def source_path(self, fullname):
        """Return the source path for the module."""
        return _file_search(self.location, fullname, self.file_exists,
                            imp.PY_SOURCE)

    def is_package(self, fullname):
        """Determine if the module is a package based on whether the file is
        named '__init__'."""
        # TODO(Python3.2): path = self.get_filename(fullname)
        path = self.source_path(fullname)
        if path is None:
            raise ImportError("cannot handle {}".format(fullname))
        return _is_package_file(path)


class PyPycFileLoader(importlib.abc.PyPycLoader, PyFileLoader):

    """ABC for loading Python source and bytecode files.

    Abstract methods:

        * get_data: inherited
        * file_exists: inherited
        * path_mtime
        * write_data

    """

    source_path = PyFileLoader.source_path

    # TODO(Python 3.2): remove
    def is_package(self, fullname):
        try:
            return PyFileLoader.is_package(self, fullname)
        except ImportError:
            path = self.bytecode_path(fullname)
            if path is None:
                raise ImportError("cannot handle {}".format(fullname))
            return _is_package_file(path)

    def bytecode_path(self, fullname):
        """Return the path to the bytecode file."""
        return _file_search(self.location, fullname, self.file_exists,
                            imp.PY_COMPILED)

    @abc.abstractmethod
    def path_mtime(self, path:str) -> int:
        """Return the modification time for the specified path, raising IOError
        if the path cannot be found."""
        raise NotImplementedError

    def source_mtime(self, fullname):
        source_path = self.source_path(fullname)
        try:
            return self.path_mtime(source_path)
        except IOError:
            raise ImportError("no modification time for {}".format(fullname))

    @abc.abstractmethod
    def write_data(self, path:str, data:bytes) -> bool:
        """Try to write the data to the path, returning a boolean based on
        whether the bytes were actually written."""
        raise NotImplementedError

    def write_bytecode(self, fullname, data):
        """Write the bytecode file if possible."""
        bytecode_path = self.bytecode_path(fullname)
        if bytecode_path is None:
            source_path = self.source_path(fullname)
            if source_path is None:
                raise ImportError("cannot find a path to {}".format(fullname))
            base_path = os.path.splitext(source_path)[0]
            bytecode_ext = next(x[0] for x in imp.get_suffixes()
                                        if x[2] == imp.PY_COMPILED)
            bytecode_path = base_path + bytecode_ext
        return self.write_data(bytecode_path, data)

