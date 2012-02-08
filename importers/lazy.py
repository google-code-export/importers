"""Lazy loader mixin.

The returned module from the lazy mixin will delay calling the underlying
loader until an attribute is accessed on the module. If the load is actually a
reload then the load is done immediately.

Be aware that the loader set on the module's __loader__ attribute will not
instance check to the loader that was called to load the module as it is an
instance of super.

The mixin is designed to be mixed in with a normal loader through multiple
inheritance, e.g.::

    class LazyLoader(importers.lazy.Mixin, Loader):
        pass

The mixin must come before the actual loader that will perform the loading in
order to override the load_module() method.

"""
import sys
import types


class Module(types.ModuleType):

    """Module class to use when setting __class__ after a load.

    This class exists as __class__ can only be re-assigned to heap types (which
    types.ModuleType is not).

    """

    pass


class LazyModule(types.ModuleType):

    def __getattribute__(self, attr):
        """Load the module and return an attribute's value.

        The __class__ attribute is replaced in order to use types.ModuleType's
        __getattribute__ implementation instead of this method.

        The __loader__ attribute is also replaced with the super() object based
        off of Mixin. This does break introspection on the loader (e.g.,
        ``isinstance(loader, importlib.abc.Loader)``), but it allows for
        the mixin to appear anywhere in the MRO and still be properly stripped
        out.

        """
        # Remove this __getattribute__ method we are in by re-assigning.
        self.__class__ = Module
        # Fetch the real loader.
        self.__loader__ = super(Mixin, self.__loader__)
        # Actually load the module.
        self.__loader__.load_module(self.__name__)
        # Return the requested attribute.
        return getattr(self, attr)


class Mixin:

    """Mixin to create a lazy version of a loader.

    Loads are triggered by accessing an attribute on the lazy module that is
    returned by this mixin. In the case of reloads the load_module() call to
    the next loader is performed immediately.

    """

    def load_module(self, name):
        # Don't be lazy during a reload.
        if name in sys.modules:
            return super().load_module(name)
        # Create a lazy module that will type check.
        module = LazyModule(name)
        # Set the loader on the module as ModuleType will not.
        module.__loader__ = self
        # Insert the module into sys.modules.
        sys.modules[name] = module
        return module

