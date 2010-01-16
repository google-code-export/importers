.. importers documentation master file, created by
   sphinx-quickstart on Fri Jan  8 17:12:34 2010.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

:mod:`importers` -- Code to help write importers
=======================================================

.. module:: importers
   :synopsis: Code to help write importers.

.. toctree::
   :maxdepth: 2


Introduction
------------

The :mod:`importers` project is meant to act as a testing ground for new code
and ideas that could potentially end up in the :mod:`importlib` package in
Python's standard library. Currently the code revolves around making it easier
to create importers or new importers using modules from the standard
library.

This documentation assumes that you understand the :mod:`importlib`
documentation. All paths mentioned in this module are formatted according to
the rules of the operating system the code is running on (i.e. paths are not
all normalized to using ``/`` as the path separator).

There are also some new terms introduced by this project.

.. glossary::

    location
        The place within a package where an importer is anchored to. A location
        can either be an absolute path (e.g. a directory on the file system
        that is within a package) or a relative one (e.g. the directory within
        a package, relative to the root of the package). An absolute location
        path does not need to be a correct path; it could contain both the path
        to an archive file plus the location within a package to be searching
        (e.g. ``/path/to/archive.zip/some/pkg`` where ``/path/to/archive.zip``
        is the path to a zip file and ``some/pkg`` is the path to the relative
        location within a package).


:mod:`importers.abc` -- Abstract base classes to help create importers
----------------------------------------------------------------------

.. module:: importers.abc
   :synopsis: Abstract base classes to help create importers.

The :mod:`importers.abc` module contains abstract base classes that ease in the
development of importers.


.. class:: ArchiveHook

    An ABC to help in creating a hook for :attr:`sys.path_hooks` which revolves
    around paths which point to an archive of modules (i.e. a file that
    contains multiple modules).

    .. method:: open(path)

        An abstract method that given a path should return the object
        representing the archive specified by
        the path. If the path does not point to a file that is of the proper
        type, raise :exc:`ValueError`.

        The value for *path* will always be for a file that exists. It will
        never be for a directory or a non-existent path.

        The archive object returned by this method will be cached by the hook
        for future use. When the hook is deleted and its :meth:`__del__` method
        is called, the archive objects will have their :meth:`close` methods
        called if they exist.

    .. method:: finder(archive, archive_path, location)

        An abstract method that should return the :term:`finder` for the specified *location* within the
        *archive*.

        *archive_path* will be the path that was passed to
        :meth:`ArchiveHook.open` while *archive* will be the object returned
        by the method. *location* is the relative path within the package that
        the path given to the hook is pointing to (e.g. if the hook was given
        ``/path/to/archive.zip/pkg/loc`` and the archive exists as
        ``/path/to/archive.zip``, then *location* would be ``pkg/loc``).

    .. method:: __call__(path)

        If the hook can handle *path*, then return the object returned by
        :meth:`finder`, else raise :exc:`ImportError`.


.. class:: PyFileFinder(location)

    An ABC to help in constructing a :term:`finder` for Python source files
    which works with file paths. Inherits from :class:`importlib.abc.Finder`.

    The *location* argument to the constructor is expected to be an absolute
    path to where the finder is expected to be searching. 

    .. method:: file_exists(path)

        Abstract method that sould return true if the path exists within the
        location where the :term:`finder` is searching, else return false. The
        path should be given as an absolute path.

    .. method:: loader(fullname, path)

        Abstract method that should return the loader to be used for the module
        named *fullname* as found at the specified *path*. For importers that
        act as both a :term:`finder` and a :term:`loader`, returning ``self``
        is the proper action to take.


.. class:: PyFileLoader(location)

    An abstract base class designed for working with file paths to load Python
    source files. The class inherits from :class:`importlib.abc.PyLoader`
    (which includes the need to implement
    :meth:`importlib.abc.PyLoader.get_data`).

    The *location* argument is the absolute path to where the loader should be
    searching.

    .. method:: file_exists(path)

        An abstract method which returns the boolean representing whether the
        path exists or not. The method must at least work with absolute paths.
        Support for relative paths is undefined because of ambiguity of where
        to anchor the search (location, archive file root, etc.).


.. class:: PyPycFileLoader(location)

    An abstract base class designed for working with file paths to load Python
    source and bytecode files. The class inherits from
    :class:`PyFileLoader` and all of its abstract methods.


    .. method:: path_mtime(path)

        Return the mtime for *path*. The value of *path* is expected to be an
        absolute path.

    .. method:: write_data(path, data)

        Try to write the *data* bytes to *path*, returning a boolean based on
        whether it occurred or not. The value of *path* is expected to be an
        absolute path.


:mod:`importers.lazy` -- Lazy loader mix-in
-------------------------------------------

A set of classes to allow for the lazy loading of modules. The benefits of lazy
loading is startup time; modules are loaded as needed, preventing the load of
modules that are not needed until much later to be postponed. This does lead to
the drawback, though, of any import errors being triggers at the time of
initial module usage instead of at the import statement that caused the import
in the first place.

.. class:: Module

    A subclass of :cls:`types.ModuleType`. When a module that is lazily loaded
    is actually loaded it will be a subclass of this class.

.. class:: LazyModule

    A subclass of :cls:`types.ModuleType`. This is the class that lazily loaded
    modules inherit from *before* they are actually loaded. Accessing any
    attribute on an instance of this class will trigger the actual loading of
    the module.

.. class:: Mixin

    A mixin to use with a :term:`loader` to make it lazily load modules. Being
    a mixin, this class must come **before** the loader that is being used to
    do the actual loading of the module.


:mod:`importers.sqlite3` --- Importer for sqlite3 database files
----------------------------------------------------------------

XXX


:mod:`importers.zip` -- Importer for zip files
----------------------------------------------

XXX


.. Indices and tables
    ==================
    * :ref:`genindex`
    * :ref:`modindex`
    * :ref:`search`
