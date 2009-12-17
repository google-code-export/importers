from .. import sqlite3 as importer
import contextlib
import os
import shutil
import sqlite3
import sys
import tempfile
import unittest


@contextlib.contextmanager
def TestDB():
    directory = tempfile.mkdtemp()
    try:
        path = os.path.join(directory, 'importers_test.db')
        cxn = sqlite3.connect(path)
        with cxn:
            cxn.execute(importer.sql_creation)
        cxn.close()
        yield path
    finally:
        shutil.rmtree(directory)


class Sqlite3HookTest(unittest.TestCase):

    """Test importers.abc.Hook."""

    def test_open_db(self):
        # A path to a DB with the proper table should succeed.
        hook = importer.Hook()
        with TestDB() as db_path:
            db = hook.open(db_path)
            db.close()
            self.assertTrue(isinstance(db, sqlite3.Connection))

    def test_open_bad_db(self):
        # Opening a DB w/o the proper table should fail.
        hook = importer.Hook()
        with TestDB() as db_path:
            db = sqlite3.connect(db_path)
            with db:
                db.execute('DROP TABLE IF EXISTS FS')
            db.close()
            with self.assertRaises(ValueError):
                hook.open(db_path)

    def test_open_bad_file(self):
        # A non-DB file should fail.
        hook = importer.Hook()
        fd, temp_path = tempfile.mkstemp()
        os.close(fd)
        try:
            with self.assertRaises(ValueError):
                hook.open(temp_path)
        finally:
            os.unlink(temp_path)

    def test_finder(self):
        # Should return an instance of the importer.
        hook = importer.Hook()
        with TestDB() as db_path:
            db = hook.open(db_path)
            finder = hook.finder(db, db_path, '')
            self.assertTrue(isinstance(finder, importer.Importer))


class PyFileLoaderTest(unittest.TestCase):

    """Superclass for testing py file loaders.

    Subclasses must provide the following attributes:

        * base_path
            Base path where created files are kept (e.g a directory or archive
            file).
        * importer
            The loader. It must contain a file relative to
            self.relative_file_path with the value of self.data. The location
            of the loader should be self.location.

    """

    location = 'pkg'
    relative_file_path = os.path.join('pkg', 'module.py')
    data = b'fake = True'

    def test_file_exists(self):
        # Test that file_exists returns true for existing paths and false
        # otherwise.
        path = os.path.join(self.base_path, self.relative_file_path)
        self.assertTrue(self.importer.file_exists(path))
        self.assertFalse(self.importer.file_exists('nothing'))

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


class Sqlite3ImporterTest(PyPycFileLoaderTest):

    mutable = True

    def setUp(self):
        self._directory = tempfile.mkdtemp()
        self.base_path = os.path.join(self._directory, 'importers_test.db')
        relative_path = importer.neutralpath(self.relative_file_path)
        self.mtime = 42
        self._cxn = sqlite3.connect(self.base_path)
        with self._cxn:
            self._cxn.execute(importer.sql_creation)
            self._cxn.execute('INSERT INTO FS VALUES (?, ?, ?)',
                                [relative_path, self.mtime, self.data])
        self.importer = importer.Importer(self._cxn, self.base_path,
                                                    self.location)

    def tearDown(self):
        self._cxn.close()
        shutil.rmtree(self._directory)

    def test_loader(self):
        # Returns self.
        self.assertIs(self.importer, self.importer.loader())

    def test_find_module(self):
        # Integration test for find_module.
        loader = self.importer.find_module('pkg.module')
        self.assertIsNotNone(loader)


def main():
    from test.support import run_unittest
    run_unittest(
            Sqlite3HookTest,
            Sqlite3ImporterTest,
            )


if __name__ == '__main__':
    main()
