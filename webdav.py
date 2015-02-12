from http.server import HTTPServer, BaseHTTPRequestHandler

class WebDavHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        super(WebDavHandler, self).do_Get()

if __name__ == "__main__":
     try:
         server = HTTPServer(("", 8080), WebDavHandler)
         print("started httpserver...")
         server.serve_forever()
     except KeyboardInterrupt:
         print("^C received, shutting down server")
         server.socket.close()
