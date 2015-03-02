import cgi
from http.server import HTTPServer, BaseHTTPRequestHandler
import os
import shutil

FILE_DIR = "files"
FILE_PATH = os.path.join(os.getcwd(), FILE_DIR)
ALLOW_DIRS = []

def get_absolute_path(path):
    return os.path.join(FILE_PATH, *path.split('/'))


class WebDavHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            if not self.path or self.path == "/":
                raise IOError
            file = open(get_absolute_path(self.path), "rb").read()
        except IOError:
            self.send_error(404,"File Not Found: {}".format(self.path))
        else:
            self.send_response(200)
            self.send_header("Content-type", "application/octet-stream")
            self.end_headers()
            self.wfile.write(file)

    def do_POST(self):
        self.do_PUT()

    def do_HEAD(self):
        self.send_response(200)

    def do_PUT(self):
        try:
            if self.path.endswith('/'):
                raise IOError
            file = open(get_absolute_path(self.path), "wb")
        except IOError:
            self.send_error(404,"File Not Found or Not Created: {}".format(self.path))
        else:
            form = cgi.FieldStorage(fp=self.rfile,
                                    headers=self.headers,
                                    environ={'REQUEST_METHOD':'PUT',
                                             'CONTENT_TYPE':self.headers['Content-Type'],}
                                    )
            self.send_response(200)
            self.end_headers()
            file.write(form['file'].file.read())
            file.close()

    def do_DELETE(self):
        path = get_absolute_path(self.path)
        try:
            os.remove(path)
        except FileNotFoundError:
            self.send_error(404,"File Not Found: {}".format(self.path))
        except OSError:
            os.removedirs(path)
        self.send_response(200)
        self.end_headers()

    def do_PROPFIND(self):
        pass

    def do_MKCOL(self):
        try:
            os.mkdir(get_absolute_path(self.path))
        except OSError:
            self.send_response(403)
        else:
            self.send_response(200)
        self.end_headers()

    def do_COPY(self):
        try:
            shutil.copy2(get_absolute_path(self.path), get_absolute_path(self.headers['Destination']))
        except FileNotFoundError:
            self.send_response(403)
        self.send_response(200)
        self.end_headers()

    def do_MOVE(self):
        try:
            shutil.move(get_absolute_path(self.path), get_absolute_path(self.headers['Destination']))
        except FileNotFoundError:
            self.send_response(403)
        self.send_response(200)
        self.end_headers()


if __name__ == "__main__":
     try:
         port = 8080
         server = HTTPServer(("", port), WebDavHandler)
         print("started httpserver: http://localhost:{}".format(port))
         server.serve_forever()
     except KeyboardInterrupt:
         print("^C received, shutting down server")
         server.socket.close()
