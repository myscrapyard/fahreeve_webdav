from http.server import HTTPServer, BaseHTTPRequestHandler
import os

FILE_DIR = "files"
FILE_PATH = os.path.join(os.getcwd(), FILE_DIR)
ALLOW_DIRS = []

def get_absolute_path(path):
    return os.path.join(FILE_PATH, *path[1:].split('/'))


class WebDavHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            if not self.path or self.path == "/":
                raise IOError
            file = open(get_absolute_path(self.path), "rb").read()
        except IOError:
            self.send_error(404,"File Not Found: %s" % self.path)
        else:
            self.send_response(200)
            self.send_header("Content-type", "application/octet-stream")
            self.end_headers()
            self.wfile.write(file)

    def do_POST(self):
        pass

    def do_HEAD(self):
        self.send_response(200)

    def do_PUT(self):
        pass

    def do_DELETE(self):
        path = get_absolute_path(self.path)
        try:
            os.remove(path)
        except FileNotFoundError:
            self.send_error(404,"File Not Found: %s" % self.path)
        except OSError:
            os.removedirs(path)
        self.send_response(200)
        self.end_headers()

    def do_PROPFIND(self):
        pass

    def do_MKCOL(self):
        pass

    def do_COPY(self):
        pass

    def do_MOVE(self):
        pass


if __name__ == "__main__":
     try:
         port = 8080
         server = HTTPServer(("", port), WebDavHandler)
         print("started httpserver: http://localhost:%d".format(port))
         server.serve_forever()
     except KeyboardInterrupt:
         print("^C received, shutting down server")
         server.socket.close()
