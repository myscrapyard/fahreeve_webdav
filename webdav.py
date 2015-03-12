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
    server_version = 'PythonWebDav 0.1 alpha'

    def do_OPTIONS(self):
        self.send_response(200, WebDavHandler.server_version)
        self.send_header('Allow', 'GET, HEAD, POST, PUT, DELETE, OPTIONS, PROPFIND, PROPPATCH, MKCOL, MOVE, COPY')
        self.send_header('Content-length', '0')
        self.send_header('DAV', '1,2')
        self.send_header('MS-Author-Via', 'DAV')
        self.end_headers()

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
        if self.path.endswith('/'):
            self.send_response(400, 'Cannot parse request')
            self.send_header('Content-length', '0')
            self.end_headers()
            return
        try:
            file = open(get_absolute_path(self.path), "wb")
        except IOError:
            self.send_error(500, 'Cannot save file')
        else:
            form = cgi.FieldStorage(fp=self.rfile,
                                    headers=self.headers,
                                    environ={'REQUEST_METHOD':'PUT',
                                             'CONTENT_TYPE':self.headers['Content-Type'],}
                                    )
            self.send_response(201, 'Created')
            self.send_header('Content-length', '0')
            self.end_headers()
            file.write(form['file'].file.read())
            file.close()

    def do_DELETE(self):
        if self.path == '' or self.path == '/':
            self.send_error(404, 'Object not found')
            self.send_header('Content-length', '0')
            self.end_headers()
            return

        path = get_absolute_path(self.path)

        if os.path.isfile(path):
            os.remove(path)
            self.send_response(204, 'No Content')
        elif os.path.isdir(path):
            shutil.rmtree(path)
            self.send_response(204, 'No Content')
        else:
            self.send_response(404,'Not Found')
        self.send_header('Content-length', '0')
        self.end_headers()

    def do_PROPFIND(self):
        pass

    def do_MKCOL(self):
        if self.path != '' or self.path != '/':
            path = get_absolute_path(self.path)
            if not os.path.isdir(path):
                os.mkdir(path)
                self.send_response(201, "Created")
                self.send_header('Content-length', '0')
                self.end_headers()
                return
        self.send_response(403, "OK")
        self.send_header('Content-length', '0')
        self.end_headers()

    def do_COPY(self):
        oldpath = get_absolute_path(self.path)
        newpath = get_absolute_path(self.headers['Destination'])
        if (os.path.isfile(oldpath)==True):
            shutil.copyfile(oldpath, newpath)
        self.send_response(201, "Created")
        self.send_header('Content-length', '0')
        self.end_headers()

    def do_MOVE(self):
        oldpath = get_absolute_path(self.path)
        newpath = get_absolute_path(self.headers['Destination'])
        if os.path.isfile(oldpath) and not os.path.isfile(newpath):
            shutil.move(oldpath, newpath)
        if os.path.isdir(oldpath) and not os.path.isdir(newpath):
            os.rename(oldpath, newpath)
        self.send_response(201, "Created")
        self.send_header('Content-length', '0')
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
