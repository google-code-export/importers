from .. import sqlite3 as importer
import contextlib
import imp
from importlib._bootstrap import _suffix_list  # XXX NAUGHTY!
from importlib.test.source.util import writes_bytecode_files
import marshal
import os
import shutil
import sqlite3
import sys
import tempfile
import time
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


class HookTest(unittest.TestCase):

    def test_direct_path(self):
        # A direct path to a sqlite3 DB w/ the proper format should return a
        # finder.
        with TestDB() as path:
            hook = importer.Hook()
            finder = hook(path)  # ImportError is failure.

    def test_indirect_path(self):
        # A path containing a DB plus a package directory should retrn a
        # finder.
        with TestDB() as path:
            indirect_path = os.path.join(path, 'pkg', 'subpkg')
            hook = importer.Hook()
            finder = hook(indirect_path)  # ImportError is failure.

    def test_bad_path(self):
        # A path not containing a DB should raise ImportError.
        hook = importer.Hook()
        with self.assertRaises(ImportError):
            finder = hook(__file__)


class BaseTest(unittest.TestCase):

    def add_file(self, cxn, path, data):
        with cxn:
            cxn.execute('INSERT INTO FS VALUES (?, ?, ?)', [path, 1, data])

    def add_source(self, cxn, path):
        """Create source for the path."""
        path = path + _suffix_list(imp.PY_SOURCE)[0]
        self.add_file(cxn, path, 'path = {!r}\n'.format(path).encode('utf-8'))

    def add_bytecode(self, cxn, path):
        """Add bytecode for the path."""
        source = 'path = {!r}\n'.format(path)
        bc = bytearray(imp.get_magic())
        bc.extend(b'\x01\x00\x00\x00')
        bc.extend(marshal.dumps(compile(source, path, 'exec')))
        path = path + _suffix_list(imp.PY_COMPILED)[0]
        self.add_file(cxn, path, bc)

    def remove_source(self, cxn, path):
        """Remove the source for the path."""
        path = path + _suffix_list(imp.PY_SOURCE)[0]
        with cxn:
            cxn.execute('DELETE FROM FS WHERE path=?', [path])


class FinderTest(BaseTest):

    """Test the sqlite3 finder.

    Each test checks that source, bytecode, and source + bytecode work.

    """

    def run_test(self, name, path, pkg_path=''):
        """Try to find the module at the path containing only source, bytecode
        + source, and just bytecode."""
        with TestDB() as db_path:
            cxn = sqlite3.connect(db_path)
            finder = importer.Finder(cxn, db_path, pkg_path)
            # Source
            self.add_source(cxn, path)
            self.assertIsNotNone(finder.find_module(name))
            # Source + bytecode
            self.add_bytecode(cxn, path)
            self.assertIsNotNone(finder.find_module(name))
            # Bytecode
            self.remove_source(cxn, path)
            self.assertIsNotNone(finder.find_module(name))


    def test_module(self):
        # Look for a module.
        self.run_test('module', 'module')

    def test_package(self):
        # Look for a package.
        name = 'pkg'
        path = 'pkg/__init__'
        self.run_test(name, path)

    def test_module_in_package(self):
        # Look for a module within a package.
        name = 'pkg.mod'
        path = 'pkg/mod'
        pkg_path = 'pkg'
        self.run_test(name, path, pkg_path)

    def test_package_in_package(self):
        # Look for a sub-package.
        name = 'pkg.subpkg'
        path = 'pkg/subpkg/__init__'
        pkg_path = 'pkg'
        self.run_test(name, path, pkg_path)

    def test_package_over_module(self):
        # A package is preferred over a module.
        with TestDB() as db_path:
            cxn = sqlite3.connect(db_path)
            finder = importer.Finder(cxn, db_path, '')
            self.add_source(cxn, 'module')
            self.add_source(cxn, 'module/__init__')
            loader = finder.find_module('module')
            self.assertIsNotNone(loader)
            self.assertEqual(loader._path, 'module/__init__.py')

    def test_failure(self):
        # No module == no finder.
        with TestDB() as db_path:
            cxn = sqlite3.connect(db_path)
            finder = importer.Finder(cxn, db_path, '')
            self.assertIsNone(finder.find_module('module'))


class LoaderTest(BaseTest):
    # XXX Test implemented methods.
    # XXX Basic sanity check to make sure it all operates with PyPycLoader.

    def test_source_path(self):
        # Make sure the source path is returned for the module.
        # If no source but bytecode, return None.
        # Nothing leads to ImportError.
        name = 'module'
        source_path = 'module.py'
        bc_path = source_path + ('c' if __debug__ else 'o')
        with TestDB() as db_path:
            cxn = sqlite3.connect(db_path)
            loader = importer.Loader(cxn, db_path, 'module', bc_path, False)
            # Wrong module -> ImportError
            with self.assertRaises(ImportError):
                loader.source_path('something')
            # Just bytecode -> None
            self.add_bytecode(cxn, name)
            self.assertIsNone(loader.source_path('module'))
            # Source -> path
            self.add_source(cxn, name)
            full_path = os.path.join(db_path, source_path)
            self.assertEqual(loader.source_path('module'), full_path)

    def test_bytecode_path(self):
        # Test that the expected bytecode path is returned.
        name = 'module'
        bc_path = 'module.py' + ('c' if __debug__ else 'o')
        with TestDB() as db_path:
            cxn = sqlite3.connect(db_path)
            loader = importer.Loader(cxn, db_path, 'module', bc_path, False)
            # Wrong module
            with self.assertRaises(ImportError):
                loader.bytecode_path('something')
            self.add_source(cxn, name)
            self.assertIsNone(loader.bytecode_path(name))
            self.add_bytecode(cxn, name)
            full_path = os.path.join(db_path, bc_path)
            self.assertEqual(loader.bytecode_path(name), full_path)

    def test_get_data(self):
        # Bytes should be returned for the data of the specified path.
        # XXX Test relative paths
        with TestDB() as db_path:
            cxn = sqlite3.connect(db_path)
            loader = importer.Loader(cxn, db_path, 'module', 'module.py',
                                        False)
            self.add_source(cxn, 'module')
            data = loader.get_data('module.py')
            self.assertEqual(data, b"path = 'module.py'\n")

    def test_is_package(self):
        # Package should return true, modules false.
        with TestDB() as db_path:
            cxn = sqlite3.connect(db_path)
            self.add_source(cxn, 'module')
            loader = importer.Loader(cxn, db_path, 'module', 'module.py',
                                        False)
            self.assertFalse(loader.is_package('module'))
            self.add_source(cxn, 'pkg/__init__')
            loader = importer.Loader(cxn, db_path, 'pkg', 'pkg/__init__.py',
                                        True)
            self.assertTrue(loader.is_package('pkg'))

    def test_source_mtime(self):
        # Should return 1 (default value being set by mock code).
        with TestDB() as db_path:
            cxn = sqlite3.connect(db_path)
            self.add_source(cxn, 'module')
            loader = importer.Loader(cxn, db_path, 'module', 'module.py',
                                        False)
            self.assertEqual(loader.source_mtime('module'), 1)

    @writes_bytecode_files
    def test_write_bytecode(self):
        # Bytecode should end up in the database.
        bytecode_path = 'module.py' + ('c' if __debug__ else 'o')
        with TestDB() as db_path:
            cxn = sqlite3.connect(db_path)
            self.add_source(cxn, 'module')
            loader = importer.Loader(cxn, db_path, 'module', 'module.py',
                                        False)
            loader.write_bytecode('module', b'fake')
            current_time = time.time()
            with cxn:
                cursor = cxn.execute('SELECT mtime, data FROM FS where path=?',
                                        [bytecode_path])
                mtime, data = cursor.fetchone()
            self.assertEqual(data, b'fake')
            self.assertLessEqual(mtime - current_time, 1)

    def test_loading(self):
        # Basic sanity check.
        name = 'module'
        source_path = 'module.py'
        bytecode_path = source_path + ('c' if __debug__ else 'o')
        with TestDB() as db_path:
            cxn = sqlite3.connect(db_path)
            self.add_source(cxn, name)
            loader = importer.Loader(cxn, db_path, name, source_path,
                                        False)
            try:
                module = loader.load_module(name)
            finally:
                try:
                    del sys.modules[name]
                except KeyError:
                    pass
            self.assertEqual(module.path, source_path)
            self.assertEqual(module.__file__,
                                os.path.join(db_path, source_path))
            if not sys.dont_write_bytecode:
                with cxn:
                    query = 'SELECT mtime, data from FS where path=?'
                    result = cxn.execute(query, [source_path])
                    if not result:
                        self.fail('bytecode not written')



class Hook2Test(unittest.TestCase):

    """Test importers.abc.Hook2."""

    def test_open_db(self):
        # A path to a DB with the proper table should succeed.
        hook = importer.Hook2()
        with TestDB() as db_path:
            db = hook.open(db_path)
            db.close()
            self.assertTrue(isinstance(db, sqlite3.Connection))

    def test_open_bad_db(self):
        # Opening a DB w/o the proper table should fail.
        hook = importer.Hook2()
        with TestDB() as db_path:
            db = sqlite3.connect(db_path)
            with db:
                db.execute('DROP TABLE IF EXISTS FS')
            db.close()
            with self.assertRaises(ValueError):
                hook.open(db_path)

    def test_open_bad_file(self):
        # A non-DB file should fail.
        hook = importer.Hook2()
        fd, temp_path = tempfile.mkstemp()
        os.close(fd)
        try:
            with self.assertRaises(ValueError):
                hook.open(temp_path)
        finally:
            os.unlink(temp_path)

    def test_finder(self):
        # Should return an instance of Sqlite3Importer.
        hook = importer.Hook2()
        with TestDB() as db_path:
            db = hook.open(db_path)
            finder = hook.finder(db, db_path, '')
            self.assertTrue(isinstance(finder, importer.Sqlite3Importer))


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
    data = b'fake'

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
        new_data = b'more fake'
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
        self.importer = importer.Sqlite3Importer(self._cxn, self.base_path,
                                                    self.location)

    def tearDown(self):
        self._cxn.close()
        shutil.rmtree(self._directory)

    def test_loader(self):
        # Returns self.
        self.assertIs(self.importer, self.importer.loader())


class IntegrationTest(unittest.TestCase):

    """Test that integration of all components."""

    pass


def main():
    from test.support import run_unittest
    #run_unittest(HookTest, FinderTest, LoaderTest)
    run_unittest(
            Hook2Test,
            Sqlite3ImporterTest,
            )


if __name__ == '__main__':
    main()
