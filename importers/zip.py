from . import remove_file
from . import abc as importers_abc
import os
import zipfile

class Hook(importers_abc.ArchiveHook):

    """Import hook for zipfiles."""

    def open(self, path):
        """Open the zip file."""
        if not zipfile.is_zipfile(path):
            raise ValueError("{} is not a zipfile", path)
        return zipfile.ZipFile(path, 'r')

    def finder(self, archive, archive_path, location):
        return Importer(archive, archive_path, location)


class Importer(importers_abc.PyFileFinder, importers_abc.PyFileLoader):

    """Importer for zipfiles."""

    def __init__(self, archive, archive_path, location):
        self._archive = archive
        self._archive_path = archive_path
        super().__init__(os.path.join(archive_path, location))

    def file_exists(self, path):
        """Check if the file exists in the zip file."""
        try:
            path = remove_file(self._archive_path, path)
        except ValueError:
            return False
        try:
            self._archive.getinfo(path)
            return True
        except KeyError:
            return False

    def loader(self, *args, **kwargs):
        return self

    def get_data(self, path):
        try:
            path = remove_file(self._archive_path, path)
        except ValueError:
            raise IOError("{!r} does not exist".format(path))
        return self._archive.read(path)
