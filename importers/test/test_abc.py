from .. import abc as importers_abc
import os
import tempfile
from test import support
import unittest


class MockArchiveHook(importers_abc.ArchiveHook):

    """A mock ArchiveHook implementation."""

    def __init__(self, file_path):
        self._file_path = file_path
        super().__init__()

    def open(self, path):
        if path != self._file_path:
            raise ValueError
        else:
            return [path]  # Need a unique ID every time.

    def finder(self, *args):
        return args


class ArchiveHookTest(unittest.TestCase):

    """Test importers.abc.ArchiveHook."""

    def setUp(self):
        self.file_path = tempfile.mkstemp()[1]
        self.addCleanup(support.unlink, self.file_path)

    def test_obvious_path(self):
        # A path directly pointing to an archive should work.
        hook = MockArchiveHook(self.file_path)
        try:
            finder = hook(self.file_path)
        except ImportError:
            self.fail("hook could not find direct path to archive")
        else:
            self.assertEqual(finder[0][0], self.file_path)
            self.assertEqual(finder[1], self.file_path)
            self.assertEqual(finder[2], '')

    def test_buried_path(self):
        # An archive path with a package path tacked on should find the archive
        # path.
        pkg_path = os.path.join('some', 'pkg', 'stuff')
        path = os.path.join(self.file_path, pkg_path)
        hook = MockArchiveHook(self.file_path)
        try:
            finder = hook(path)
        except ImportError:
            self.fail("hook could not find {} in {}".format(self.file_path,
                                                            path))
        else:
            self.assertEqual(finder[0][0], self.file_path)
            self.assertEqual(finder[1], self.file_path)
            self.assertEqual(finder[2], pkg_path)

    def test_caching(self):
        # A previously found archive should always be returned, no matter what
        # package path is tacked on.
        hook = MockArchiveHook(self.file_path)
        archive1 = hook(self.file_path)[0]
        finder = hook(os.path.join(self.file_path, 'pkg'))
        self.assertIs(archive1, finder[0])
        self.assertEqual(finder[2], 'pkg')

    def test_directory(self):
        # A directory is a failure.
        directory = os.path.dirname(self.file_path)
        hook = MockArchiveHook(self.file_path)
        with self.assertRaises(ImportError):
            hook(directory)

    def test_no_actual_path(self):
        # A entirely faked path should fail.
        fake_path = '/a/b/c/d/e/f'
        hook = MockArchiveHook(self.file_path)
        with self.assertRaises(ImportError):
            hook(fake_path)

    def test_file_not_archive(self):
        # A file that is not a proper archive type should fail.
        hook = MockArchiveHook('nonexistentfile')
        with self.assertRaises(ImportError):
            hook(self.file_path)


class MockPyFileFinder(importers_abc.PyFileFinder):

    """Mock PyFileFinder implementation."""

    def __init__(self, location, *args):
        """Set what files "exist"."""
        self._paths = set(args)
        super().__init__(location)

    def file_exists(self, path):
        return path in self._paths

    def loader(self, *args):
        return args


BC = 'c' if __debug__ else 'o'

class PyFileFinderTest(unittest.TestCase):

    """Test importers.abc.PyFileFinder."""

    def finder_test(self, fullname, location, source_path):
        for extra in ('', BC):
            path = source_path + extra
            finder = MockPyFileFinder(location, path)
            loader = finder.find_module(fullname)
            self.assertIsNotNone(loader)
            if not None:
                self.assertEqual(loader[0], fullname)
                self.assertEqual(loader[1], path)

    def test_module(self):
        # Find a module.
        self.finder_test('module', '/', '/module.py')

    def test_package(self):
        # Find a package.
        self.finder_test('pkg', '/', '/pkg/__init__.py')

    def test_submodule(self):
        # Find a module in a package.
        self.finder_test('pkg.submodule', '/pkg', '/pkg/submodule.py')

    def test_subpackage(self):
        # Find a package within a package.
        self.finder_test('pkg.subpkg', '/pkg', '/pkg/subpkg/__init__.py')

    def test_package_over_module(self):
        # Packages should be preferred over modules.
        finder = MockPyFileFinder('/', '/module.py', '/module/__init__.py')
        loader = finder.find_module('module')
        self.assertIsNotNone(loader)
        self.assertEqual(loader[0], 'module')
        self.assertEqual(loader[1], '/module/__init__.py')

    def test_failure(self):
        # Not finding anything leads to None being returned.
        finder = MockPyFileFinder('/')
        loader = finder.find_module('module')
        self.assertIsNone(loader)


class MockPyFileLoader(importers_abc.PyFileLoader):

    def __init__(self, location, *paths):
        self._paths = set(paths)
        super().__init__(location)

    def get_data(self, path):
        return path

    def file_exists(self, path):
        return path in self._paths


class PyFileLoaderTest(unittest.TestCase):

    """Test importers.abc.PyFileLoader."""

    def test_source_path(self):
        # Should return the path to the source or None if there isn't any.
        loader = MockPyFileLoader('/', '/module.py')
        self.assertEqual(loader.source_path('module'), '/module.py')
        bc_path = '/module.py' + BC
        loader = MockPyFileLoader('/', bc_path)
        self.assertIsNone(loader.source_path('module'))
        loader = MockPyFileLoader('/', 'nothing.py')
        self.assertIsNone(loader.source_path('module'))

    def test_is_package(self):
        # Should return true for package as delineated by their __init__.py
        # file (both source and bytecode).
        test_values = (('module.py', False), ('module/__init__.py', True))
        for path, result in test_values:
            loader = MockPyFileLoader('/', '/' + path)
            self.assertEqual(loader.is_package('module'), result)
        loader = MockPyFileLoader('/', '/prefix__init__.py')
        self.assertFalse(loader.is_package('prefix__init__'))
        loader = MockPyFileLoader('/', '/__init__suffix.py')
        self.assertFalse(loader.is_package('__init__suffix'))


def test_main():
    support.run_unittest(
                            ArchiveHookTest,
                            PyFileFinderTest,
                            PyFileLoaderTest,
                        )


if __name__ == '__main__':
    test_main()
