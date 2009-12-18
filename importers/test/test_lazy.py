from .. import lazy
import imp
import importlib.abc
import sys
import types
import unittest


class MockLoader(importlib.abc.Loader):

    """Mock loader to be subclassed w/ the lazy mixin.

    The 'loaded' attribute is set to true when load_module() has been called.

    """

    def __init__(self):
        self.loaded = False

    def load_module(self, fullname):
        self.loaded = True
        try:
            return sys.modules[fullname]
        except KeyError:
            module = imp.new_module(fullname)
            sys.modules[fullname] = module
            return module


class MockLazyLoader(lazy.Mixin, MockLoader):

    pass


class LazyMixinTest(unittest.TestCase):

    """Test importer.lazy.Mixin."""

    def setUp(self):
        self.loader = MockLazyLoader()
        self.name = 'module'

    def tearDown(self):
        try:
            del sys.modules[self.name]
        except KeyError:
            pass

    def test_attr_access(self):
        # Accessing an attribute should trigger a load.
        module = self.loader.load_module(self.name)
        self.assertFalse(self.loader.loaded)
        module.__name__
        self.assertTrue(self.loader.loaded)
        self.assertFalse(isinstance(module.__loader__, MockLazyLoader))
        self.assertEqual(module.__class__.__getattribute__,
                            types.ModuleType.__getattribute__)

    def test__getattribute__access(self):
        # Accessing __getattribute__ itself should trigger the load.
        module = self.loader.load_module(self.name)
        self.assertFalse(self.loader.loaded)
        module.__getattribute__
        self.assertTrue(self.loader.loaded)

    def test_reload(self):
        # A reload should trigger an immediate load.
        sys.modules[self.name] = imp.new_module(self.name)
        module = self.loader.load_module(self.name)
        self.assertTrue(self.loader.loaded)


def main():
    from test.support import run_unittest
    run_unittest(LazyMixinTest)


if __name__ == '__main__':
    main()
