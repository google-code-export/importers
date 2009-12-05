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
            for statement in importer.sql_creation:
                cxn.execute(statement)
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

    def _test_module(self):
        # Look for a module.
        raise NotImplementedError

    def _test_package(self):
        # Look for a package.
        raise NotImplementedError

    def _test_module_in_package(self):
        # Look for a module within a package.
        raise NotImplementedError

    def _test_package_in_package(self):
        # Look for a sub-package.
        raise NotImplementedError

    def _test_package_over_module(self):
        # A package is preferred over a module.
        raise NotImplementedError

    def _test_failure(self):
        # No module == no finder.
        raise NotImplementedError

class LoaderTest(unittest.TestCase):

    def _test_module(self):
        # Load from a module.
        raise NotImplementedError

    def _test_package(self):
        # Load a package.
        raise NotImplementedError

    def _test_lacking_parent(self):
        # Not having a parent package loaded should not be a problem.
        raise NotImplementedError

    def _test_module_reuse(self):
        # Module should be reused if in sys.modules.
        raise NotImplementedError

    def _test_state_after_failure(self):
        # A failure to load a module should not alter a pre-existing instance.
        raise NotImplementedError

    def _test_bad_syntax(self):
        # Bad syntax == SyntaxError.
        raise NotImplementedError

    # XXX Care about bytecode tests? Triggers could guarantee state.


def main():
    from test.support import run_unittest
    run_unittest(HookTest, FinderTest)


if __name__ == '__main__':
    main()
