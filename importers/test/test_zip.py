from .. import zip as importer
from . import util
import os
import shutil
import tempfile
import unittest
import zipfile


def create_zip(file_path, data):
    """Create a zip file containing a file."""
    directory = tempfile.mkdtemp()
    base_path = os.path.join(directory, 'archive.zip')
    zip_ = zipfile.ZipFile(base_path, 'w')
    zip_.writestr(file_path, data)
    zip_.close()
    return base_path


class ZipHookTest(unittest.TestCase):

    """Test importers.zip.Hook."""

    def setUp(self):
        self.path = create_zip('module.py', b'fake = True')
        self.hook = importer.Hook()

    def tearDown(self):
        shutil.rmtree(os.path.dirname(self.path))

    def test_zip(self):
        # Finding a zip file directly specified.
        found = self.hook.open(self.path)
        self.assertTrue(isinstance(found, zipfile.ZipFile))

    def test_non_zip(self):
        # Finding a file that is not a zipfile should fail.
        with open(self.path) as file:
            file.write('abcd')
        with self.assertRaises(ValueError):
            self.hook.open(self.path)

    def test_finder(self):
        zip_ = self.hook.open(self.path)
        finder = self.hook.finder(zip_, self.path, '')
        self.assertTrue(isinstance(finder, importer.Importer))


class ZipImporterTest(util.PyFileFinderTest, util.PyFileLoaderTest):

    """Test importers.zip.Importer."""

    def setUp(self):
        self.base_path = create_zip(self.relative_file_path, self.data)
        zip_ = zipfile.ZipFile(self.base_path)
        self.importer = importer.Importer(zip_, self.base_path, self.location)

    def tearDown(self):
        shutil.rmtree(os.path.dirname(self.base_path))

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
