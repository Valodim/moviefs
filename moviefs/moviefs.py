from fuse import FUSE, LoggingMixIn, Operations
import db

import itertools
from stat import S_IFDIR, S_IFLNK
from time import time
import os

class TitleFS(Operations):
    def __init__(self, pathbase, db):
        self.pathbase = pathbase
        self.db = db

    def readdir(self, pieces, fh):
        if len(pieces) == 1:
            return list(x[0].encode() for x in self.db.query(db.Movie.name).all())
        else:
            # we have an actual movie selected here - just return its personal directory
            movie = self.db.query(db.Movie).filter_by(name=pieces[1]).first()
            return ['.', '..', os.path.basename(movie.path.encode()) ]

    def readlink(self, pieces):
        if len(pieces) == 1:
            raise OSError(ENOENT)
        else:
            # we have an actual movie selected here - just return its personal directory
            movie = self.db.query(db.Movie).filter_by(name=pieces[1]).first()
            return os.path.abspath( self.pathbase + '/' + movie.path ).encode()

    def getattr(self, pieces, fh=None):
        if len(pieces) <= 2:
            # top dir: it's a directory
            st = {
                'st_mode': S_IFDIR | 0755,
                'st_nlink': 2,
            }
            st['st_ctime'] = st['st_mtime'] = st['st_atime'] = time()
            return st
        else:
            # otherwise, it's a symbolic link
            st = {
                'st_mode': S_IFLNK | 0777,
                'st_nlink': 1,
            }
            st['st_ctime'] = st['st_mtime'] = st['st_atime'] = time()
            return st

class DirectorFS(Operations):
    def __init__(self, pathbase, db):
        self.pathbase = pathbase
        self.db = db

    def readdir(self, pieces, fh):
        return list(x[0].encode() for x in self.db.query(db.Movie.name).all())

    def getattr(self, path, fh=None):
        st = {
            'st_mode': S_IFDIR | 0755,
            'st_nlink': 2,
        }
        st['st_ctime'] = st['st_mtime'] = st['st_atime'] = time()
        return st

# can't use LoggingMixIn, because we overwrite __call__ ourself!
class MovieFS(Operations):
    def __init__(self, pathbase, db):
        self.pathbase = pathbase
        self.db = db

        self.dir_patterns = {
            'title':     TitleFS(pathbase, db),
            'director':  DirectorFS(pathbase, db),
        }

    def __call__(self, op, path, *args):
        ret = '[Unhandled Exception]'
        try:
            # root is the only directory we handle in this class
            if path == '/':
                print '->', op, path, repr(args)
                ret = getattr(self, op)(path, *args)
            # for everything else, consult the seven wise regexes
            else:
                pieces = path.split('/')[1:]
                if pieces[0] in self.dir_patterns:
                    print '~>', self.dir_patterns[pieces[0]], op, path, repr(args)
                    ret = getattr(self.dir_patterns[pieces[0]], op)(pieces, *args)
            return ret
        except OSError, e:
            ret = str(e)
            raise
        finally:
            print '<-', op, repr(ret)

    def getattr(self, path, fh=None):
        st = {
            'st_mode': S_IFDIR | 0755,
            'st_nlink': 2,
        }
        st['st_ctime'] = st['st_mtime'] = st['st_atime'] = time()
        return st

    def readdir(self, path, fh):
        return ['.', '..' ] + self.dir_patterns.keys()

def mount(mountpoint, pathbase, db):
    fuse = FUSE(MovieFS(pathbase, db), mountpoint, foreground=True, nothreads=True)

