from .. import sqlite3 as importer
import contextlib
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
            # XXX Should it be TEXT or something else?
            cxn.execute('''CREATE TABLE PythonCode
                           (path PRIMARY KEY, py, pyc, pyo)''')
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

    def _test_bad_path(self):
        # A path not containing a DB should raise ImportError.
        raise NotImplementedError


def main():
    from test.support import run_unittest
    run_unittest(HookTest)


if __name__ == '__main__':
    main()
