from .. import sqlite3 as importer
import contextlib
import imp
from importlib._bootstrap import _suffix_list  # XXX NAUGHTY!
import marshal
import os
import shutil
import sqlite3
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


class FinderTest(unittest.TestCase):

    """Test the sqlite3 finder.

    Each test checks that source, bytecode, and source + bytecode work.

    """

    def add_file(self, cxn, path, data):
        with cxn:
            cxn.execute('INSERT INTO FS VALUES (?, ?)', [path, data])

    def create_source(self, cxn, path):
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

    def run_test(self, name, path, pkg_path=''):
        """Try to find the module at the path containing only source, bytecode
        + source, and just bytecode."""
        with TestDB() as db_path:
            cxn = sqlite3.connect(db_path)
            finder = importer.Finder(cxn, db_path, pkg_path)
            # Source
            self.create_source(cxn, path)
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
            self.create_source(cxn, 'module')
            self.create_source(cxn, 'module/__init__')
            loader = finder.find_module('module')
            self.assertIsNotNone(loader)
            self.assertEqual(loader._path, 'module/__init__.py')

    def test_failure(self):
        # No module == no finder.
        with TestDB() as db_path:
            cxn = sqlite3.connect(db_path)
            finder = importer.Finder(cxn, db_path, '')
            self.assertIsNone(finder.find_module('module'))


class LoaderTest(unittest.TestCase):
    # XXX Test implemented methods.
    # XXX Basic sanity check to make sure it all operates with PyPycLoader.

    pass


def main():
    from test.support import run_unittest
    run_unittest(HookTest, FinderTest)


if __name__ == '__main__':
    main()
