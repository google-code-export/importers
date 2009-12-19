from .. import zip as importer
from . import util
import os
import shutil
import tempfile
import unittest
import zipfile

class ZipHookTest(unittest.TestCase):

    """Test importers.zip.Hook."""

    pass


class ZipImporterTest(util.PyFileFinderTest, util.PyFileLoaderTest):

    """Test importers.zip.Importer."""

    def setUp(self):
        # XXX self.base_path
        # XXX self.importer
        self._directory = tempfile.mkdtemp()
        self.base_path = os.path.join(self._directory, 'archive.zip')
        zip_ = zipfile.ZipFile(self.base_path, 'w')
        zip_.writestr(self.relative_file_path, self.data)
        zip_.close()
        zip_ = zipfile.ZipFile(self.base_path)
        self.importer = importer.Importer(zip_, self.base_path, self.location)

    def tearDown(self):
        shutil.rmtree(self._directory)

    def test_loader(self):
        # Should return self.
        self.assertIs(self.importer, self.importer.loader())


def main():
    from test.support import run_unittest
    run_unittest(
            ZipHookTest,
            ZipImporterTest,
            )

if __name__ == '__main__':
    main()
