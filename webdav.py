from http.server import HTTPServer, BaseHTTPRequestHandler, urllib
import mimetypes
from time import timezone, strftime, localtime, gmtime
import hashlib
import os
import shutil
from io import StringIO
import xml.etree.ElementTree as ET
from mutagen.easyid3 import EasyID3


class Paths:
    struct = {}

    def __init__(self, path='.'):
        for file in os.listdir(path):
            if path != '.':
                file = path + os.sep + file
            if file.endswith('.mp3'):
                audio = EasyID3(file)
                self.addAudio(file, *self.getData(file))
                if DEBUG:
                    print("{}:{}:{}".format(audio['artist'][0],
                                            audio['album'][0],
                                            audio['title'][0]))

    def addArtist(self, artist):
        if artist not in self.struct:
            self.struct[artist] = {}

    def addAlbum(self, artist, album):
        self.addArtist(artist)
        if album not in self.struct[artist]:
            self.struct[artist][album] = {}

    def addAudio(self, filename, artist, album, audio):
        self.addAlbum(artist, album)
        if audio not in self.struct[artist][album]:
            self.struct[artist][album][audio] = filename

    def getFilename(self, artist, album, audio):
        art = self.struct.get(artist)
        if art is None:
            return
        alb = art.get(album)
        if alb is None:
            return
        aud = alb.get(audio)
        return aud

    def getArtists(self):
        return self.struct.keys()

    def getAlbums(self, artist):
        return self.struct.get(artist)

    def getAudios(self, artist, album):
        alb = self.getAlbums(artist)
        if alb is not None:
            return alb.get(album)

    def getBasefile(self, artist=None, album=None):
        if artist is None:
            art = list(self.struct.keys())[0]
            return self.getBasefile(art)
        if album is None:
            out = list(list(self.struct.values())[0].values())[0]
        else:
            out = self.struct[artist][album]
        return list(out.values())[0]

    def getData(self, filename, root=False):
        if not root and filename.endswith('.mp3'):
            audio = EasyID3(filename)
            return audio['artist'][0], audio['album'][0], audio['title'][0] + ".mp3"
        elif root:
            return os.sep, '', ''


'''
    def saveMember(self, rfile, name, size, req):
        # save a member file
        fname = os.path.join(self.realname, urllib.parse.unquote(name))
        f = open(fname, 'wb')
        if size > 0:    # if size=0 ,just save a empty file.
            writ = 0
            bs = 65536
            while True:
                if size != -1 and (bs > size - writ):
                    bs = size - writ
                buf = rfile.read(bs)
                if len(buf) == 0:
                    break
                f.write(buf)
                writ += len(buf)
                if size != -1 and writ >= size:
                    break
        f.close()
'''

class File:
    def __init__(self, name, filename, parent):
        self.name = name
        self.basefile = filename
        self.parent = parent

    def getProperties(self):
        st = os.stat(self.basefile)
        properties = {'creationdate': unixdate2iso8601(st.st_ctime),
                      'getlastmodified': unixdate2httpdate(st.st_mtime),
                      'displayname': self.name,
                      'getetag': hashlib.md5(self.name.encode()).hexdigest(),
                      'getcontentlength': st.st_size,
                      'getcontenttype':  mimetypes.guess_type(self.basefile),
                      'getcontentlanguage': None, }
        if self.basefile[0] == ".":
            properties['ishidden'] = 1
        if not os.access(self.basefile, os.W_OK):
            properties['isreadonly'] = 1
        return properties


class DirCollection:
    MIME_TYPE = 'httpd/unix-directory'

    def __init__(self, basefile, type, virtualfs, parent):
        self.basefile = basefile
        self.artist, alb, aud = virtualfs.getData(basefile, type == 'root')
        self.name = self.virtualname = self.artist
        if type == 'album':
            self.name = self.album = alb
            self.virtualname += os.sep + self.album
        self.parent = parent
        self.virtualfs = virtualfs
        self.type = type

    def getProperties(self):
        st = os.stat(self.basefile)
        properties = {'creationdate': unixdate2iso8601(st.st_ctime),
                      'getlastmodified': unixdate2httpdate(st.st_mtime),
                      'displayname': self.name,
                      'getetag': hashlib.md5(self.name.encode()).hexdigest(),
                      'resourcetype': '<D:collection/>',
                      'iscollection': 1,
                      'getcontenttype': self.MIME_TYPE, }
        if self.virtualname[0] == ".":
            properties['ishidden'] = 1
        if not os.access(self.basefile, os.W_OK):
            properties['isreadonly'] = 1
        if self.parent is None:
            properties['isroot'] = 1
        return properties

    def getMembers(self):
        members = []
        if self.type == 'root':
            for artist in self.virtualfs.getArtists():
                basefile = self.virtualfs.getBasefile(artist)
                members += [DirCollection(basefile,
                                          'artist',
                                          self.virtualfs,
                                          self)]
        elif self.type == 'artist':
            for album in self.virtualfs.getAlbums(self.artist):
                basefile = self.virtualfs.getBasefile(self.artist, album)
                members += [DirCollection(basefile,
                                          'album',
                                          self.virtualfs,
                                          self)]
        elif self.type == "album":
            for audio, filename in self.virtualfs.getAudios(self.artist,
                                                            self.album).items():
                members += [File(audio, filename, self)]
        return members

    def findMember(self, name):
        if name[-1] == '/':
            name = name[:-1]
        if self.type == 'root':
            listmembers = self.virtualfs.getArtists()
        elif self.type == 'artist':
            listmembers = self.virtualfs.getAlbums(self.artist)
        elif self.type == 'album':
            listmembers = self.virtualfs.getAudios(self.artist, self.album)

        if name in listmembers:
            if self.type == 'root':
                return DirCollection(self.virtualfs.getBasefile(),
                                     'artist',
                                     self.virtualfs,
                                     self)
            elif self.type == 'artist':
                return DirCollection(self.virtualfs.getBasefile(self.artist),
                                     'album',
                                     self.virtualfs,
                                     self)
            elif self.type == 'album':
                filename = self.virtualfs.getFilename(self.artist, self.album, name)
                return File(name, filename ,self)




class BufWriter:
    def __init__(self, w, debug=True, headers=None):
        self.w = w
        self.buf = StringIO(u'')
        self.debug = debug
        if debug and headers is not None:
            sys.stderr.write('\n' + str(headers))

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
    server_version = 'PythonAudioServer 0.1 alpha'
    all_props = ['name', 'parentname', 'href', 'ishidden', 'isreadonly',
                 'getcontenttype', 'contentclass', 'getcontentlanguage',
                 'creationdate', 'lastaccessed', 'getlastmodified',
                 'getcontentlength', 'iscollection', 'isstructureddocument',
                 'defaultdocument', 'displayname', 'isroot', 'resourcetype']

    basic_props = ['name', 'getcontenttype', 'getcontentlength',
                   'creationdate', 'iscollection']

    def do_OPTIONS(self):
        self.send_response(200, WebDavHandler.server_version)
        self.send_header('Allow', 'GET, HEAD, POST, PUT, DELETE, OPTIONS, PROPFIND, PROPPATCH, MKCOL, MOVE, COPY')
        self.send_header('Content-length', '0')
        self.send_header('DAV', '1,2')
        self.send_header('MS-Author-Via', 'DAV')
        self.end_headers()
        if DEBUG:
            sys.stderr.write('\n' + str(self.headers) + '\n')

    def do_POST(self):
        self.do_PUT()

    def do_HEAD(self, GET=False):
        path, elem = self.path_elem()
        if not elem:
            if not GET:
                self.send_response(404, 'Object not found')
                self.end_headers()
            return 404
        try:
            props = elem.getProperties()
        except:
            if not GET:
                self.send_response(500, "Error retrieving properties")
                self.end_headers()
            return 500
        if not GET:
            self.send_response(200, 'OK')
        if type(elem) == File:
            self.send_header("Content-type", props['getcontenttype'])
            self.send_header("Last-modified", props['getlastmodified'])
        else:
            try:
                ctype = props['getcontenttype']
            except:
                ctype = DirCollection.MIME_TYPE
            self.send_header("Content-type", ctype)
        if not GET:
            self.end_headers()
        if DEBUG:
            sys.stderr.write('\n' + str(self.headers) + '\n')
        return 200

    def do_GET(self):
        try:
            if not self.path or self.path == "/":
                raise IOError
            path = get_absolute_path(self.path)
            file = open(path, "rb").read()
        except IOError:
            self.send_error(404,"File Not Found: {}".format(self.path))
        else:
            self.send_response(201, "Created")
            self.do_HEAD(GET=True)
            self.end_headers()
            self.wfile.write(file)
            if DEBUG:
                sys.stderr.write(path)
        sys.stderr.write('\n')

    def do_PUT(self):
        try:
            if 'Content-length' in self.headers:
                size = int(self.headers['Content-length'])
            elif 'Transfer-Encoding' in self.headers:
                if self.headers['Transfer-Encoding'].lower() == 'chunked':
                    size = -2
            else:
                size = -1
            path, elem = path_elem_prev(self.path)
            ename = path[-1]
        except:
            self.send_response(400, 'Cannot parse request')
            self.send_header('Content-length', '0')
            self.end_headers()
            return
        try:
            elem.saveMember(self.rfile, ename, size, self)
        except:
            self.send_response(500, 'Cannot save file')
            self.send_header('Content-length', '0')
            self.end_headers()
            return
        if size == 0:
            self.send_response(201, 'Created')
        else:
            self.send_response(200, 'OK')
        #self.send_header('Content-length', '0')
        self.end_headers()
        if DEBUG:
            sys.stderr.write('\n' + str(self.headers) + '\n')

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
        if DEBUG:
            sys.stderr.write('\n' + str(self.headers) + '\n')

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
                elem = get_absolute_path('')
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
        w.write('<D:multistatus xmlns:D="DAV:">\n')
        #  xmlns:Z="urn:schemas-microsoft-com:"
        def write_props_member(w, m):
            w.write('<D:response>\n<D:href>{}</D:href>\n<D:propstat>\n<D:prop>\n'.format(m.name))
            props = m.getProperties()       # get the file or dir props
            if ('quota-available-bytes' in wished_props) or \
               ('quota-used-bytes'in wished_props) or \
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
        if DEBUG:
            sys.stderr.write('\n' + str(self.headers) + '\n')

    def do_COPY(self):
        oldpath = get_absolute_path(self.path)
        newpath = get_absolute_path(self.headers['Destination'])
        if (os.path.isfile(oldpath)==True):
            shutil.copyfile(oldpath, newpath)
        self.send_response(201, "Created")
        self.send_header('Content-length', '0')
        self.end_headers()
        if DEBUG:
            sys.stderr.write('\n' + str(self.headers) + '\n')

    def do_MOVE(self):
        oldpath = get_absolute_path(self.path)
        dest = self.headers['Destination']
        port = str(self.server.server_port)
        virtualaddr = dest[dest.find(port) + len(port):]
        newpath = get_absolute_path(virtualaddr)
        if os.path.isfile(oldpath) and not os.path.isfile(newpath):
            shutil.move(oldpath, newpath)
        if os.path.isdir(oldpath) and not os.path.isdir(newpath):
            os.rename(oldpath, newpath)
        self.send_response(201, "Created")
        self.send_header('Content-length', '0')
        self.end_headers()
        if DEBUG:
            sys.stderr.write('\n' + str(self.headers) + '\n')

    def path_elem(self):
        #Returns split path and Member object of the last element
        path = split_path(urllib.parse.unquote(self.path))
        elem = ROOT
        for e in path:
            elem = elem.findMember(e)
            if elem == None:
                break
        return (path, elem)


DEBUG = True
#DEBUG = False
FILE_DIR = "files"
FILE_PATH = os.path.join(os.getcwd(), FILE_DIR)
VIRTUALFS = Paths(FILE_PATH)
ROOT = DirCollection(FILE_PATH, 'root', VIRTUALFS, None)
ALLOW_DIRS = []

def get_absolute_path(path):
    #return os.path.join(FILE_PATH, *urllib.parse.unquote(path).split('/'))
    data = split_path(urllib.parse.unquote(path))
    filename = VIRTUALFS.getFilename(data[0], data[1], data[2])
    return os.path.join(FILE_PATH, filename)


def real_path(path):
    return path

def virt_path(path):
    return path

def unixdate2iso8601(d):
    tz = timezone / 3600
    tz = '%+03d' % tz
    return strftime('%Y-%m-%dT%H:%M:%S', localtime(d)) + tz + ':00'

def unixdate2httpdate(d):
    return strftime('%a, %d %b %Y %H:%M:%S GMT', gmtime(d))

def split_path(path):
    # split'/dir1/dir2/file' in ['dir1/', 'dir2/', 'file']
    out = path.split('/')[1:]
    while out and out[-1] in ('', '/'):
        out = out[:-1]
        if len(out) > 0:
            out[-1] += '/'
    return out

def path_elem_prev(path):
    # Returns split path (see split_path())
    # and Member object of the next to last element
    path = split_path(urllib.parse.unquote(path))
    elem = ROOT
    for e in path[:-1]:
        elem = elem.findMember(e)
        if elem is None:
            break
    return (path, elem)


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
        print("started webdav server: http://127.0.1.1:{}".format(port))
        server.serve_forever()
    except KeyboardInterrupt:
        print("received, shutting down server")
        server.shutdown()
