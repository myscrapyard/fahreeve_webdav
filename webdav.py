from http.server import HTTPServer, BaseHTTPRequestHandler
import os

WORK_DIR = "files"
WORK_PATH = os.getcwd() + os.path.sep + WORK_DIR + os.path.sep
ALLOW_DIRS = []

class WebDavHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path[1:]
        try:
            if not path:
                raise IOError
            file = open(WORK_PATH + self.path, "rb").read()
        except IOError:
            self.send_error(404,"File Not Found: %s" % path)
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
        pass

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
         server = HTTPServer(("", 8080), WebDavHandler)
         print("started httpserver...")
         server.serve_forever()
     except KeyboardInterrupt:
         print("^C received, shutting down server")
         server.socket.close()
