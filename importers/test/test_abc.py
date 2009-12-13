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

    def test_module(self):
        # Find a module.
        for extra in ('', BC):
            path = '/module.py' + extra
            finder = MockPyFileFinder('/', path)
            self.assertIsNotNone(finder.find_module('module'),
                                    'did not find {}'.format(path))

    def test_package(self):
        # Find a package.
        for extra in ('', BC):
            path = '/pkg/__init__.py' + extra
            finder = MockPyFileFinder('/', path)
            self.assertIsNotNone(finder.find_module('pkg'))

    def test_submodule(self):
        # Find a module in a package.
        for extra in ('', BC):
            path = '/pkg/module.py' + extra
            finder = MockPyFileFinder('/pkg', path)
            self.assertIsNotNone(finder.find_module('pkg.module'))

    def test_subpackage(self):
        # Find a package within a package.
        for extra in ('', BC):
            path = '/pkg/sub/__init__.py' + extra
            finder = MockPyFileFinder('/pkg', path)
            self.assertIsNotNone(finder.find_module('pkg.sub'))

    # XXX subpackage
    # XXX package over module
    # XXX failure


def test_main():
    support.run_unittest(
                            ArchiveHookTest,
                            PyFileFinderTest,
                        )


if __name__ == '__main__':
    test_main()
