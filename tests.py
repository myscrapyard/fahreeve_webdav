import unittest
import webdav
import os

class GetAbsoluteURL(unittest.TestCase):

    def test_root(self):
        path = "/"
        fullpath = webdav.get_absolute_path(path)
        self.assertEqual(fullpath, os.path.join(os.getcwd(), webdav.FILE_DIR, ""))

    def test_file(self):
        path = "/file"
        fullpath = webdav.get_absolute_path(path)
        self.assertEqual(fullpath, os.path.join(os.getcwd(), webdav.FILE_DIR, "file"))

    def test_dir(self):
        path = "/dir/"
        fullpath = webdav.get_absolute_path(path)
        self.assertEqual(fullpath, os.path.join(os.getcwd(), webdav.FILE_DIR, "dir/"))

    def test_dir_and_file(self):
        path = "/dir/file"
        fullpath = webdav.get_absolute_path(path)
        self.assertEqual(fullpath, os.path.join(os.getcwd(), webdav.FILE_DIR, "dir", "file"))

    def test_dir_and_dir(self):
        path = "/dir/dir/"
        fullpath = webdav.get_absolute_path(path)
        self.assertEqual(fullpath, os.path.join(os.getcwd(), webdav.FILE_DIR, "dir", "dir/"))


if __name__ == '__main__':
    unittest.main()