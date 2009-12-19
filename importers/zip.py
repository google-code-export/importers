from . import abc as importers_abc

class Hook(importers_abc.ArchiveHook):

    pass


class Importer(importers_abc.PyFileFinder, importers_abc.PyFileLoader):

    pass
