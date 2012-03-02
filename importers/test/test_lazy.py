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

    def get_module(self):
        """Return the lazily-loaded module."""
        return self.loader.load_module(self.name)

    def test_attr_access(self):
        # Accessing an attribute should trigger a load.
        module = self.get_module()
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
        # Should not be able to triger the old __getattribute__.
        module.__loader__ = None
        self.assertFalse(module.__loader__)  # Trigger an attribute get.
        self.assertFalse(module.__loader__)

    def test__getattribute__read(self):
        # Accessing __getattribute__ itself (or any attribute) should trigger
        # the load.
        module = self.get_module()
        self.assertFalse(self.loader.loaded)
        self.assertIsNone(module.attr)
        self.assertTrue(self.loader.loaded)

    def test_attr_write(self):
        # Setting an attribute should not cause it to be lost.
        module = self.get_module()
        self.assertFalse(self.loader.loaded)
        module.attr = True
        module.new_attr = 42
        self.assertFalse(self.loader.loaded)
        self.assertTrue(module.attr)
        self.assertTrue(self.loader.loaded)
        self.assertEqual(module.new_attr, 42)

    def test_renamed(self):
        # Survive __name__ being changed.
        module = self.get_module()
        module.__name__ = 'changed name'
        self.assertIsNone(module.attr)
        self.assertEquals(module.__name__, 'changed name')

    @unittest.expectedFailure
    def test_imp_reload_unloaded(self):
        # Reloading an unloaded module should not cause issues.
        module = self.get_module()
        self.assertFalse(self.loader.loaded)
        # XXX failing because there is no finder to return the lazy loader
        imp.reload(module)
        self.assertTrue(self.loader.loaded)

    @unittest.expectedFailure
    def test_imp_reload_loaded(self):
        # A loaded module should reload w/o issue.
        module = self.get_module()
        module.new_attr = 42
        self.assertIsNone(module.attr)
        imp.reload(module)
        self.assertTrue(hasattr(module, 'new_attr'))
        self.assertEqual(module.new_attr, 42)

    def test_manual_reload(self):
        # Calling __loader__.load_module() should work w/o issue.
        module = self.get_module()
        module.attr = True
        module.__loader__.load_module(self.name)  # Reset 'attr' to None
        self.assertFalse(module.attr)

    def test_isinstance(self):
        # Should be considered a module.
        module = self.get_module()
        self.assertTrue(isinstance(module, types.ModuleType))
        self.assertTrue(module.__name__)  # Trigger load.
        self.assertTrue(isinstance(module, types.ModuleType))


def main():
    from test.support import run_unittest
    run_unittest(LazyMixinTest)


if __name__ == '__main__':
    main()
