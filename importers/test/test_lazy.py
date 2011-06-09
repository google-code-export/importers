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
        """As the lazy loader will have already put the module in sys.modules,
        simply return that and modify as necessary as it will be loaded at this
        point."""
        self.loaded = True
        module = sys.modules[fullname]
        module.attr = None
        return module


class MockLazyLoader(lazy.Mixin, MockLoader):
    """Class mixing the mock loader with the lazy mixin."""
    pass


class LazyMixinTest(unittest.TestCase):

    """Test importer.lazy.Mixin."""

    def setUp(self):
        self.name = '_lazy_test_mdoule'
        self.loader = MockLazyLoader()
        self.tearDown()

    def tearDown(self):
        try:
            del sys.modules[self.name]
        except KeyError:
            pass

    def test_attr_access(self):
        # Accessing an attribute should trigger a load.
        module = self.loader.load_module(self.name)
        self.assertFalse(self.loader.loaded)
        self.assertFalse(module.attr)  # Triggers load
        self.assertTrue(self.loader.loaded)
        self.assertFalse(isinstance(module.__loader__, MockLazyLoader))
        # Since __loader__ is now an instance of super(), indirect ways must be
        # used to verify the right thing occurred.
        assert MockLazyLoader.__doc__ != MockLoader.__doc__
        self.assertEqual(module.__loader__.__doc__, MockLoader.__doc__)
        self.assertEqual(module.__class__.__getattribute__,
                            types.ModuleType.__getattribute__)

    def test__getattribute__read(self):
        # Accessing __getattribute__ itself (or any attribute) should trigger
        # the load.
        module = self.loader.load_module(self.name)
        self.assertFalse(self.loader.loaded)
        module.__getattribute__
        self.assertTrue(self.loader.loaded)

    @unittest.expectedFailure
    def test_attr_write(self):
        # Setting an attribute should trigger the load **before** the attribute
        # is actually mutated.
        module = self.loader.load_module(self.name)
        self.assertFalse(self.loader.loaded)
        module.attr = True
        self.assertTrue(self.loader.loaded,
                        'module not loaded after an attribute assignment')
        self.assertTrue(module.attr)

    @unittest.expectedFailure
    def test_imp_reload(self):
        # A reload should trigger an immediate load.
        module = self.loader.load_module(self.name)
        self.assertFalse(self.loader.loaded)
        # XXX failing because there is no finder to return the lazy loader
        imp.reload(module)
        self.assertTrue(self.loader.loaded)

    def test_manual_reload(self):
        # Calling __loader__.load_module() should work w/o issue.
        module = self.loader.load_module(self.name)
        module.attr = True
        module.__loader__.load_module(self.name)  # Reset 'attr' to None
        self.assertFalse(module.attr)


def main():
    from test.support import run_unittest
    run_unittest(LazyMixinTest)


if __name__ == '__main__':
    main()
