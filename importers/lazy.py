# XXX Rewrite once testing code is removed and put in the proper place.
'''Proof-of-concept lazy importer for Python source code.
DO NOT USE THIS IN REAL CODE! I am CHEATING by using private APIs to importlib,
so don't expect this to always work. This was more for my personal edification.

Simple doctest that creates a module named 'mod' which prints out "imported"
when the module is initialized.
    >>> code = """print("imported")
    ... def fxn(): print("fxn called")"""
    >>> with open('mod.py', 'w') as file:
    ...   file.write(code)
    ...
    48
    >>> import lazy
    >>> import mod
    >>> mod.fxn()
    imported
    fxn called

'''
import imp
from importlib import _bootstrap
import sys
import types


class Module(types.ModuleType):

    """Module class to use in setting __class__."""

    pass


class LazyModule(types.ModuleType):

    def __getattribute__(self, attr):
        # XXX Why can't we use types.ModuleType directly?
        # Remove the __getattribute__ method we are in.
        self.__class__ = Module
        # Fetch the real loader.
        self.__loader__ = super(LazyMixin, self.__loader__)
        # Actually load the module.
        self.__loader__.load_module(self.__name__)
        # Return the requested attribute.
        # XXX what happens if they ask for __getattribute__?
        return getattr(self, attr)


class LazyMixin:

    """Mixin to create a lazy version of a loader."""

    def load_module(self, name):
        # Create a lazy module that will type check.
        module = LazyModule(name)
        # Set the loader on the module as ModuleType will not.
        module.__loader__ = self
        # Insert the module into sys.modules.
        # XXX What to do if it already exists (i.e. reload)?
        sys.modules[name] = module
        return module


# XXX Drop everything below here as was only for testing
class LazyPyLoader(LazyMixin, _bootstrap._PyFileLoader):
    pass


class LazyPyFinder(_bootstrap._PyFileFinder):

    _loader = LazyPyLoader


# Install the finder as a side-effect
import os
sys.path_hooks.insert(0, LazyPyFinder)
for path in ('', os.getcwd()):
    if path in sys.path:
        del sys.path_importer_cache[path]
del path


if __name__ == '__main__':
    import doctest
    doctest.testmod()
