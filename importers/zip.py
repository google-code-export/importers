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

    pass
