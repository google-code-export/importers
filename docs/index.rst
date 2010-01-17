.. importers documentation master file, created by
   sphinx-quickstart on Fri Jan  8 17:12:34 2010.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

:mod:`importers` -- Code to help write importers
=======================================================

.. module:: importers
   :synopsis: Code to help write importers.

PyPI page: http://pypi.python.org/pypi/importers

Project page (including issue tracker): http://code.google.com/p/importers/

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


Functions
---------

.. function:: remove_file(file_path, full_path)

    Strip *file_path* from the beginning of *full_path*, returning the relative
    path suffix that is left. This function is useful when working with paths
    that start with the absolute path to an archive file and end with the
    relative path within a package.


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

        An abstract method that should return the :term:`finder` for the
        specified *location* within the *archive*.

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

    A subclass of :class:`types.ModuleType`. When a module that is lazily loaded
    is actually loaded it will be a subclass of this class.

.. class:: LazyModule

    A subclass of :class:`types.ModuleType`. This is the class that lazily loaded
    modules inherit from *before* they are actually loaded. Accessing any
    attribute on an instance of this class will trigger the actual loading of
    the module.

.. class:: Mixin

    A mixin to use with a :term:`loader` to make it lazily load modules. Being
    a mixin, this class must come **before** the loader that is being used to
    do the actual loading of the module.


:mod:`importers.sqlite3` --- Importer for sqlite3 database files
----------------------------------------------------------------

An importer for Python source and bytecode that uses :mod:`sqlite3` databases
as the archive format. The sqlite3 database is expected to have a table named
``FS`` with the following schema::

    CREATE TABLE FS (path TEXT PRIMARY KEY, mtime INTEGER, data BLOB);

The *path* column stores the relative path to a "file" in the archive (e.g.
``pkg/__init__.py``). *mtime* is the modification time for the "file". The
*data* column stores the contents of the "file".

.. class:: Hook

    A subclass of :class:`importers.abc.ArchiveHook` that uses :mod:`sqlite3`
    databases.

    .. method:: open(path)

        An implementation of :meth:`importers.abc.ArchiveHook.open`. The file
        path is tested to see if it is an acceptable database by opening it and
        verifying that the ``FS`` table exists.

    .. method:: finder(archive, archive_path, location)

        An implementation of :meth:`importers.abc.ArchiveHook.finder` that
        returns an instance of :class:`importers.sqlite3.Importer`.


.. class:: Importer(db, db_path, location)

    An implementation of :class:`importers.abc.PyFileFinder` and
    :class:`importers.abc.PyPycFileLoader`. The *db* is the
    :class:`sqlite3.Connection` instance of the database to use, *db_path* is the
    file path to the open database, and *location* is the relative package
    location that the importer is to search in.

    .. method:: loader(\*args, \*\*kwargs)

        An implementation of :meth:`importers.abc.PyFileFinder` that returns
        ``self``.

    .. method:: file_exists(path)

        An implementation of :meth:`importers.abc.PyFileFinder.file_exists` and
        :meth:`importers.abc.PyPycFileLoader.file_exists`. *path* is expected
        to be an absolute path. A file's existence is based on stripping off
        the database's path from *path* and seeing if the remaining file path
        matches a value in the ``path`` column in the ``FS`` table.

    .. method:: get_data(path)

        An implementation of :meth:`importers.abc.PyPycFileLoader.get_data.`. *path* can
        be an absolute path (in which case the database file path is stripped
        off) or a relative one (in which case the path is used directly to
        compare against the ``path`` column in the ``FS`` table). The value
        stored in the ``data`` column is returned as bytes.

    .. method:: path_mtime(path)

        An implementation of :meth:`importers.abc.PyPycFileLoader.path_mtime`.
        *path* is expected to be an absolute path. The value found in the
        ``mtime`` column is returned.

    .. method:: write_data(path, data)

        An implementation of :meth:`importers.abc.PyPycFileLoader.write_data`.
        *path* is expected to be an absolute path. A row is added to the
        database with the value of ``(path, int(time.time()), data)``.


:mod:`importers.zip` -- Importer for zip files
----------------------------------------------

An importer for Python source (but not bytecode) that uses zip files as the
archive format.

.. class:: Hook

    An implementation of :class:`importers.abc.ArchiveHook`.

    .. method:: open(path)

        Returns the :class:`zipfile.ZipFile` instance for *path* if
        :func:`zipfile.is_zipfile` says the path is a zipfile.

    .. method:: finder(archive, archive_path, location)

        Returns an instance of :class:`Importer` for the passed-in zipfile and
        package location.

.. class:: Importer(archive, archive_path, location)

    An implementation of both :class:`importers.abc.PyFileFinder` and
    :class:`importers.abc.PyFileLoader`. *archive* is to be an instance of
    :class:`zipfile.ZipFile`, *archive_path* is the absolute path to the
    zipfile, and *location* is the relative package path that the importer is
    to search in.

    .. method:: file_exists(path)

        Return :const:`True` if *path* (which should be absolute) exists in the
        zipfile based on the removal of the zipfile path.

    .. method:: loader(\*args, \*\*kwargs)

        Returns ``self``.

    .. method:: get_data(path)

        Return the bytes found at *path*. The argument is expected to be an
        absolute path.


.. Indices and tables
    ==================
    * :ref:`genindex`
    * :ref:`modindex`
    * :ref:`search`
