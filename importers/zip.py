from . import abc as importers_abc
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
        super().__init__(location)

    def file_exists(self, path):
        raise NotImplementedError

    def loader(self, *args, **kwargs):
        return self

    def get_data(self, path):
        raise NotImplementedError

