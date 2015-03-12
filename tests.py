from http.server import HTTPServer
import urllib.request
import unittest
import webdav
import os

class GetAbsoluteURL(unittest.TestCase):

    def test_root(self):
        path = "/"
        fullpath = webdav.get_absolute_path(path)
        self.assertEqual(fullpath, os.path.join(os.getcwd(), webdav.FILE_DIR, ""))

    def test_root2(self):
        path = ""
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

'''class DELETE_method(unittest.TestCase):

    def setUp(self):
        self.port = 8080
        self.url = "127.0.0.1"
        self.server = HTTPServer(("", self.port), webdav.WebDavHandler)

    def test_delete_file(self):
        req = urllib.request.Request('http://{}:{}/'.format(self.url, self.port), method='OPTIONS')
        resp = req.read()#urllib.request.urlopen(req)
        print(resp.status)
        pass

    def tearDown(self):
        self.server.socket.close()
'''

if __name__ == '__main__':
    unittest.main()