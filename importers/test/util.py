import os
import sys
import unittest


class PyFileFinderTest(unittest.TestCase):

    """Superclass for testing py file finders.

    Do not that no tests are performed for the loader() method on finders as
    they are very finder-specific.

    Subclasses must provide the following attributes:

        * base_path
            Base path where created files are kept (e.g a directory or archive
            file).
        * importer
            The finder. It must contain a file relative to
            self.relative_file_path with the value of self.data. The location
            of the loader should be self.location.

    """

    location = 'pkg'
    relative_file_path = os.path.join('pkg', 'module.py')
    data = b'fake = True'

    def test_file_exists_for_finder(self):
        # Test that file_exists returns true for existing paths and false
        # otherwise.
        path = os.path.join(self.base_path, self.relative_file_path)
        self.assertTrue(self.importer.file_exists(path))
        self.assertFalse(self.importer.file_exists('nothing'))

    def test_find_module(self):
        # Integration test for find_module.
        loader = self.importer.find_module('pkg.module')
        self.assertIsNotNone(loader)


class PyFileLoaderTest(unittest.TestCase):

    """Superclass for testing py file loaders.

    Subclasses must provide the same attributes as PyFileFinderTest requires
    except self.importer is set to the loader.

    """

    location = 'pkg'
    relative_file_path = os.path.join('pkg', 'module.py')
    data = b'fake = True'

    # Re-use the finder file_exists() tests.
    test_file_exists_for_loader = PyFileFinderTest.test_file_exists_for_finder

    def test_get_data(self):
        # Should return the data that is stored.
        path = os.path.join(self.base_path, self.relative_file_path)
        self.assertEqual(self.importer.get_data(path), self.data)

    def test_load_module(self):
        # Integration test for load_module().
        module = self.importer.load_module('pkg.module')
        try:
            self.assertTrue(hasattr(module, 'fake'))
            self.assertEqual(module.fake, True)
        finally:
            del sys.modules['pkg.module']

class PyPycFileLoaderTest(PyFileLoaderTest):

    """Superclass for testing py/pyc file loaders.

    Subclasses must provide the following attributes in addition to the one's
    required by the subclass:

        * mtime
            The modification time for the file.
        * mutable
            True/false value indicating if the loader can write data.

    """

    def test_path_mtime(self):
        # Should return the proper mtime.
        path = os.path.join(self.base_path, self.relative_file_path)
        self.assertEqual(self.importer.path_mtime(path), self.mtime)

    def test_write_data(self):
        # Should write the data to the DB.
        if not self.mutable:
            self.skip("loader must support file mutation")
        path = os.path.join(self.base_path, self.relative_file_path)
        new_data = b'fake = False'
        self.assertTrue(self.importer.write_data(path, new_data))
        self.assertEqual(self.importer.get_data(path), new_data)

    # XXX protect w/ writes_bytecode_file decorator
    def _test_load_module_w_bytecode(self):
        # XXX
        self.fail()
