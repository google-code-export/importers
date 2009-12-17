from .. import sqlite3 as importer
from . import util
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


class Sqlite3ImporterTest(util.PyFileFinderTest, util.PyPycFileLoaderTest):

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


def main():
    from test.support import run_unittest
    run_unittest(
            Sqlite3HookTest,
            Sqlite3ImporterTest,
            )


if __name__ == '__main__':
    main()
