import cgi
from http.server import HTTPServer, BaseHTTPRequestHandler, urllib
import mimetypes
from time import timezone, strftime, localtime, gmtime
import hashlib
import os
import shutil
from io import StringIO
import xml.etree.ElementTree as ET


class File:
    def __init__(self, name, parent):
        self.name = name
        self.parent = parent
        self.realname = parent.realname + name        # '/var/www/mysite/some.txt'
        self.virtualname = parent.virtualname + name  # '/mysite/some.txt'

    def getProperties(self):
        st = os.stat(self.realname)
        properties = {'creationdate' : unixdate2iso8601(st.st_ctime),
                      'getlastmodified' : unixdate2httpdate(st.st_mtime),
                      'displayname' : self.name,
                      'getetag' : hashlib.md5(self.realname.encode()).hexdigest(),
                      'getcontentlength' : st.st_size,
                      'getcontenttype' :  mimetypes.guess_type(self.name),
                      'getcontentlanguage' : None,}
        if self.name[0] == ".":
            properties['ishidden'] = 1
        if not os.access(self.realname, os.W_OK):
            properties['isreadonly'] = 1
        return properties


class DirCollection:
    def __init__(self, fsdir, virdir, parent=None):
        if not os.path.exists(fsdir):
            raise "Local directory (fsdir) not found: " + fsdir
        self.realname = fsdir
        self.name = virdir
        if self.realname[-1] != os.sep:
            if self.realname[-1] == '/': # fix for win/dos/mac separators
                self.realname = self.realname[:-1] + os.sep
            else:
                self.realname += os.sep
        self.virtualname = virdir
        if self.virtualname[-1] != '/':
            self.virtualname += '/'
        self.parent = parent

    def getProperties(self):
        st = os.stat(self.realname)
        properties = {'creationdate' : unixdate2iso8601(st.st_ctime),
                      'getlastmodified' : unixdate2httpdate(st.st_mtime),
                      'displayname' : self.name,
                      'getetag' : hashlib.md5(self.realname.encode()).hexdigest(),
                      'resourcetype' : '<D:collection/>',
                      'iscollection' : 1,
                      'getcontenttype' : 'httpd/unix-directory',}
        if self.name[0] == ".":
            properties['ishidden'] = 1
        if not os.access(self.realname, os.W_OK):
            properties['isreadonly'] = 1
        if self.name == '/':
            properties['isroot'] = 1
        return properties

    def getMembers(self):
        listmembers = os.listdir(self.realname) # get all files and dirs in current directory
        for i, name in enumerate(listmembers):
            if os.path.isdir(self.realname + name):
                listmembers[i] = listmembers[i] + '/'
        members = []
        for name in listmembers:
            if name[-1] == '/':
                members.append(DirCollection(self.realname + name, self.virtualname + name, self))
            else:
                members.append(File(name, self))
        return members

    def findMember(self, name):
        listmembers = os.listdir(self.realname)
        for i, name in enumerate(listmembers):
            if os.path.isdir(self.realname + name):
                listmembers[i] = listmembers[i] + '/'
        if name in listmembers:
            if name[-1] != '/':
                return File(name, self)
            else:
                return DirCollection(self.realname + name, self.virtualname + name, self)
        elif name[-1] != '/':
            name += '/'
            if name in listmembers:
                return DirCollection(self.realname + name, self.virtualname + name, self)


class BufWriter:
    def __init__(self, w, debug=True, headers=None):
        self.w = w
        self.buf = StringIO(u'')
        self.debug = debug
        if debug and headers is not None:
            sys.stderr.write('\n' +     str(headers))

    def write(self, s):
        if self.debug:
            sys.stderr.write(s)
        self.buf.write(s)

    def flush(self):
        if self.debug:
            sys.stderr.write('\n\n')
        self.w.write(self.buf.getvalue().encode('utf-8'))
        self.w.flush()

    def getSize(self):
        return len(self.buf.getvalue().encode('utf-8'))

class WebDavHandler(BaseHTTPRequestHandler):
    server_version = 'PythonWebDav 0.1 alpha'
    all_props = ['name', 'parentname', 'href', 'ishidden', 'isreadonly', 'getcontenttype',
                'contentclass', 'getcontentlanguage', 'creationdate', 'lastaccessed', 'getlastmodified',
                'getcontentlength', 'iscollection', 'isstructureddocument', 'defaultdocument',
                'displayname', 'isroot', 'resourcetype']
    basic_props = ['name', 'getcontenttype', 'getcontentlength', 'creationdate', 'iscollection']

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
        self.send_header('Content-length', '0')
        self.end_headers()

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
        depth = 'infinity'
        if 'Depth' in self.headers:
            depth = self.headers['Depth'].lower()
        if 'Content-length' in self.headers:
            req = self.rfile.read(int(self.headers['Content-length'])).decode("utf-8")
        else:
            req = self.rfile.read().decode("utf-8")
        root = ET.fromstring(req)
        wished_all = False
        ns = {'D': 'DAV:'}
        if len(root) == 0:
            wished_props = WebDavHandler.basic_props
        else:
            if root.find('allprop'):
                wished_props = WebDavHandler.all_props
                wished_all = True
            else:
                wished_props = []
                for prop in root.find('D:prop', ns):
                    wished_props.append(prop.tag[len(ns['D']) + 2:])
        path, elem = self.path_elem()
        if not elem:
            if len(path) >= 1: # it's a non-existing file
                self.send_response(404, 'Not Found')
                self.send_header('Content-length', '0')
                self.end_headers()
                return
            else:
                elem = get_absolute_path()
        if depth != '0' and not elem:   #or elem.type != Member.M_COLLECTION:
            self.send_response(406, 'This is not allowed')
            self.send_header('Content-length', '0')
            self.end_headers()
            return
        self.send_response(207, 'Multi-Status')          #Multi-Status
        self.send_header('Content-Type', 'text/xml')
        self.send_header("charset",'"utf-8"')
        w = BufWriter(self.wfile, debug=DEBUG, headers=self.headers)
        w.write('<?xml version="1.0" encoding="utf-8" ?>\n')
        w.write('<D:multistatus xmlns:D="DAV:" xmlns:Z="urn:schemas-microsoft-com:">\n')

        def write_props_member(w, m):
            w.write('<D:response>\n<D:href>{}</D:href>\n<D:propstat>\n<D:prop>\n'.format(m.virtualname))
            props = m.getProperties()       # get the file or dir props
            if ('quota-available-bytes' in wished_props) or ('quota-used-bytes'in wished_props) or \
                    ('quota' in wished_props) or ('quotaused'in wished_props):
                svfs = os.statvfs('/')
                props['quota-used-bytes'] = (svfs.f_blocks - svfs.f_bavail) * svfs.f_frsize
                props['quotaused'] = (svfs.f_blocks - svfs.f_bavail) * svfs.f_frsize
                props['quota-available-bytes'] = svfs.f_bavail * svfs.f_frsize
                props['quota'] = svfs.f_bavail * svfs.f_frsize
            for i in wished_props:
                if i not in props:
                    w.write('  <D:{}/>\n'.format(i))
                else:
                    w.write('  <D:{tag}>{text}</D:{tag}>\n'.format(tag=i, text=str(props[i])))
            w.write('</D:prop>\n<D:status>HTTP/1.1 200 OK</D:status>\n</D:propstat>\n</D:response>\n')

        write_props_member(w, elem)
        if depth == '1':
            for m in elem.getMembers():
                write_props_member(w,m)
        w.write('</D:multistatus>')
        self.send_header('Content-Length', str(w.getSize()))
        self.end_headers()
        w.flush()

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

    def path_elem(self):
        #Returns split path and Member object of the last element
        path = split_path(urllib.parse.unquote(self.path))
        elem = ROOT
        for e in path:
            elem = elem.findMember(e)
            if elem == None:
                break
        return (path, elem)

FILE_DIR = "files"
FILE_PATH = os.path.join(os.getcwd(), FILE_DIR)
ROOT = DirCollection(FILE_PATH, '/')
ALLOW_DIRS = []
DEBUG = True

def get_absolute_path(path):
    return os.path.join(FILE_PATH, *path.split('/'))

def unixdate2iso8601(d):
    tz = timezone / 3600
    tz = '%+03d' % tz
    return strftime('%Y-%m-%dT%H:%M:%S', localtime(d)) + tz + ':00'

def unixdate2httpdate(d):
    return strftime('%a, %d %b %Y %H:%M:%S GMT', gmtime(d))

def split_path(path):
        # split'/dir1/dir2/file' in ['dir1', 'dir2', 'file']
        out = path.split('/')[1:]
        while out and out[-1] in ('','/'):
           out = out[:-1]
           if len(out) > 0:
              out[-1] += '/'
        return out


if __name__ == "__main__":
    import sys
    args = sys.argv[1:]
    port = 8080
    if '-p' in args:
        i = args.index('-p')
        port = int(args[i + 1])
    if '-u' in args:
        i = args.index('-u')
        url = args[i + 1]
    else:
        url = ''
    try:
        server = HTTPServer((url, port), WebDavHandler)
        print("started httpserver: http://127.0.1.1:{}".format(port))
        server.serve_forever()
        print("...")
    except KeyboardInterrupt:
        print("received, shutting down server")
        server.shutdown()
