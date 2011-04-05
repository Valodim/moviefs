from fuse import FUSE, LoggingMixIn, Operations
import db

import itertools
from stat import S_IFDIR
from time import time

class MovieFS(LoggingMixIn, Operations):

    def __init__(self, pathbase, db):
        self.pathbase = pathbase
        self.db = db

    def getattr(self, path, fh=None):
        if path == '/' or True:
            st = dict(st_mode=(S_IFDIR | 0755), st_nlink=2)
        else:
            raise FuseOSError(ENOENT)
        st['st_ctime'] = st['st_mtime'] = st['st_atime'] = time()
        return st

    def readdir(self, path, fh):
        if path == '/':
            return ['.', '..', 'title']
        else:
            pieces = path.split('/')
            topdir = pieces[1]
            return ['.', '..'] + self.readdir_types[topdir](self, pieces)

    def readdir_title(self, pieces):
        print pieces
        return list(x[0].encode() for x in self.db.query(db.Movie.name).all())

    readdir_types = {
        'title': readdir_title
    }

    def readlink(self, path):
        return self.sftp.readlink(path)

    # Disable unused operations:
    access = None
    flush = None
    getxattr = None
    listxattr = None
    open = None
    opendir = None
    release = None
    releasedir = None
    statfs = None
    write = None

def mount(mountpoint, pathbase, db):
    fuse = FUSE(MovieFS(pathbase, db), mountpoint, foreground=True, nothreads=True)
