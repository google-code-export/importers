from .. import abc as importers_abc
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
            return path

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
            self.assertEqual(finder[0], self.file_path)
            self.assertEqual(finder[1], self.file_path)
            self.assertEqual(finder[2], '')

    def _test_buried_path(self):
        # An archive path with a package path tacked on should find the archive
        # path.
        raise NotImplementedError

    def _test_caching(self):
        # A previously found archive should always be returned, no matter what
        # package path is tacked on.
        raise NotImplementedError

    def _test_directory(self):
        # A directory is a failure.
        raise NotImplementedError

    def _test_no_actual_path(self):
        # A entirely faked path should fail.
        raise NotImplementedError

    def _test_file_not_arvhive(self):
        # A file that is not a proper archive type should fail.
        raise NotImplementedError


def test_main():
    support.run_unittest(ArchiveHookTest)


if __name__ == '__main__':
    test_main()
