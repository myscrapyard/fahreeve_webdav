from http.server import HTTPServer
import unittest
import http.client
import multiprocessing
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

class HEAD_method(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super(HEAD_method, cls).setUpClass()
        cls.port = 8080
        cls.url = "localhost"
        httpd = HTTPServer(("", cls.port), webdav.WebDavHandler)
        cls.server = multiprocessing.Process(target=httpd.serve_forever)
        cls.server.start()

    def test_head1(self):
        conn = http.client.HTTPConnection(self.url, self.port)
        conn.request("HEAD", "/")
        res = conn.getresponse()
        self.assertEqual(res.status, 200)

    def test_head2(self):
        conn = http.client.HTTPConnection(self.url, self.port)
        conn.request("HEAD", "")
        res = conn.getresponse()
        self.assertEqual(res.status, 200)

    def test_head3(self):
        conn = http.client.HTTPConnection(self.url, self.port)
        conn.request("HEAD", "/file")
        res = conn.getresponse()
        self.assertEqual(res.status, 200)

    def test_head4(self):
        conn = http.client.HTTPConnection(self.url, self.port)
        conn.request("HEAD", "/dir/")
        res = conn.getresponse()
        self.assertEqual(res.status, 200)

    @classmethod
    def tearDownClass(cls):
        cls.server.terminate()
        super(HEAD_method, cls).setUpClass()


if __name__ == '__main__':
    unittest.main()