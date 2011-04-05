from fuse import FUSE, LoggingMixIn, Operations
import db

import itertools
from stat import S_IFDIR
from time import time
import os

class TitleFS(Operations):
    def __init__(self, pathbase, db):
        self.pathbase = pathbase
        self.db = db

    def readdir(self, pieces, fh):
        print pieces
        return list(x[0].encode() for x in self.db.query(db.Movie.name).all())

    def getattr(self, path, fh=None):
        st = {
            'st_mode': S_IFDIR | 0755,
            'st_nlink': 2,
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

