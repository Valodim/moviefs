from fuse import FUSE, LoggingMixIn, Operations
import db

import itertools
from stat import S_IFREG, S_IFDIR, S_IFLNK
from time import time
from errno import *
import os

class BaseMovieFS(Operations):
    """
      This base filesystem handles the last level, which is typically movies.
      For any operation that is passed here, the last element of the path will
      be treated as a movie name, exposing a directory with its info.

      Stuff handled here in caps: /fstype/...[/...]/MOVIEDIR/MOVIEINFO

    """
    def __init__(self, pathbase, db):
        self.pathbase = pathbase
        self.db = db

    def readdir(self, pieces, fh):
        # shouldn't happen - this is typically the case handled by inheriting classes
        if len(pieces) == 0:
            raise OSError(ENOENT, '')
        else:
            # we have an actual movie selected here - just return its personal directory
            movie = db.movieFromCache(pieces[-1])
            if not movie:
                raise OSError(ENOENT, '')
            return ['.', '..', os.path.basename(movie.path).replace(os.sep, ' '), 'info' ]

    def readlink(self, pieces):
        # need at least two levels for this to make sense: -2 is the movie dir, -1 is the filename
        if len(pieces) <= 1:
            raise OSError(ENOENT, '')
        else:
            movie = db.movieFromCache(pieces[-2])
            # we have an actual movie selected here - just return its personal directory
            if not movie:
                raise OSError(ENOENT, '')
            return os.path.abspath( self.pathbase + '/' + movie.path )

    def getattr(self, pieces, fh=None):
        if len(pieces) <= 1:
            # probably a directory.. either way, this is just here for convenience.
            st = {
                'st_mode': S_IFDIR | 0755,
                'st_nlink': 2,
            }
            st['st_ctime'] = st['st_mtime'] = st['st_atime'] = time()
            return st
        else:
            movie = db.movieFromCache(pieces[-2])
            if movie is None:
                raise OSError(ENOENT, '')
            if pieces[-1] == 'info':
                # otherwise, it's a symbolic link
                st = {
                    'st_mode': S_IFREG | 0644,
                    'st_size': len(movie.printinfo()),
                    'st_nlink': 1,
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

    def read(self, pieces, size, offset, fh=None):
        if len(pieces) <= 1 or pieces[-1] != 'info':
            raise OSError(ENOENT, '')
        movie = db.movieFromCache(pieces[-2])
        return movie.printinfo()

class MultiLevelFS(BaseMovieFS):
    """
      This is a sub-filesystem type that has exactly one extra criteria for the
      movie, thus two levels.

      Stuff handled here in caps: /fstype/CRITERIA/moviedir/movieinfo

      The only thing that differs in subclasses is the list of criteria and
      assorted movies.
    """

    def __init__(self, *args):
        BaseMovieFS.__init__(self, *args)
        self.levelCache = { }

    def readdir(self, pieces, fh):
        # we NEED the list of criteria!
        if len(self.levels) == 0:
            raise OSError(ENOTSUP, '')
        if len(pieces) < len(self.levels):
            return self.cachedir(pieces)
        else:
            return super(MultiLevelFS, self).readdir(pieces, fh)

    def cachedir(self, pieces):
        joined = '/'.join(pieces)
        if joined not in self.levelCache:
            self.levelCache[joined] = self.levels[len(pieces)](self, pieces)
        return self.levelCache[joined]

    def getattr(self, pieces, fh=None):
        if len(pieces) == 0:
            # top dir: it's a directory
            st = {
                'st_mode': S_IFDIR | 0755,
                'st_nlink': 2,
            }
            st['st_ctime'] = st['st_mtime'] = st['st_atime'] = time()
            return st
        elif len(pieces) <= len(self.levels):
            # for all subdirectories..
            for i in range(1, len(pieces)):
                # see if this entry exists in the dir cache
                if pieces[i] not in self.cachedir(pieces[0:i]):
                    raise OSError(ENOENT, '')
            st = {
                'st_mode': S_IFDIR | 0755,
                'st_nlink': 2,
            }
            st['st_ctime'] = st['st_mtime'] = st['st_atime'] = time()
            return st
        else:
            return super(MultiLevelFS, self).getattr(pieces, fh)

class TitleFS(MultiLevelFS):
    """ Trivial filesystem, just list by title and let BaseMovieFS handle all the rest. """
    def level_one(self, pieces):
        return list(x[0].replace(os.sep, '_') for x in itertools.chain(self.db.query(db.Movie.name)))

    levels = [ level_one ]

class ImdbFS(MultiLevelFS):
    """ Trivial filesystem, just list by title and let BaseMovieFS handle all the rest. """
    def level_one(self, pieces):
        return list(x[0].replace(os.sep, '_') for x in itertools.chain(self.db.query(db.Movie.imdb_id)))

    levels = [ level_one ]

class RuntimeFS(MultiLevelFS):
    """ Simple two-level filesystem, shows a list of actors. """
    def level_one(self, pieces):
        return list(str(x[0]*10) for x in filter(lambda x: x[0] is not None, self.db.query(db.Movie.runtime.op("/")(10)).distinct()))
    def level_two(self, pieces):
        # the first level should be an actor
        return list(x[0].replace(os.sep, '_') for x in itertools.chain(self.db.query(db.Movie.name).filter(db.Movie.runtime.op("/")(10)==int(pieces[0])/10)))
        # it's not?!
        if not movies:
            raise OSError(ENOENT, '')
        # it is. show a list of all his movies
        return list(x.name for x in movie)

    levels = [ level_one, level_two ]

class GenreFS(MultiLevelFS):
    """ Simple two-level filesystem, shows a list of actors. """
    def level_one(self, pieces):
        return list(x[0] for x in self.db.query(db.Genre.name))
    def level_two(self, pieces):
        # the first level should be an actor
        genre = self.db.query(db.Genre).filter_by(name=pieces[0]).first()
        # it's not?!
        if not genre:
            raise OSError(ENOENT, '')
        # it is. show a list of all his movies
        return list(x.name for x in genre.movies)

    levels = [ level_one, level_two ]

class ActorFS(MultiLevelFS):
    """ Simple two-level filesystem, shows a list of actors. """
    def level_one(self, pieces):
        return list(x[0] for x in self.db.query(db.Actor.name))
    def level_two(self, pieces):
        # the first level should be an actor
        actor = self.db.query(db.Actor).filter_by(name=pieces[0]).first()
        # it's not?!
        if not actor:
            raise OSError(ENOENT, '')
        # it is. show a list of all his movies
        return list(x.name for x in actor.movies)

    levels = [ level_one, level_two ]

class YearFS(MultiLevelFS):
    """ Simple two-level filesystem, shows a list of actors. """
    def level_one(self, pieces):
        years = list(str(x[0]) for x in self.db.query(db.Movie.year).distinct())
        print years
        if len(years) == 0:
            raise OSError(ENOENT, '')
        return years
    def level_two(self, pieces):
        movies = list(x[0] for x in self.db.query(db.Movie.name).filter_by(year=pieces[0]))
        if len(movies) == 0:
            raise OSError(ENOENT, '')
        return movies

    levels = [ level_one, level_two ]

# can't use LoggingMixIn, because we overwrite __call__ ourself!
class MovieFS(Operations):
    """
    Top-Level movie filesystem, this is what gets mounted. This is mainly
    plumbing to delegate calls down to the different sub-filesystems.
    """
    def __init__(self, pathbase, db):
        self.pathbase = pathbase
        self.db = db

        self.dir_patterns = {
            'title':     TitleFS(pathbase, db),
            'actor':     ActorFS(pathbase, db),
            'genre':     GenreFS(pathbase, db),
            'year':      YearFS(pathbase, db),
            'imdb':      ImdbFS(pathbase, db),
            'runtime':   RuntimeFS(pathbase, db),
        }

    def __call__(self, op, path, *args):
        """ Delegate calls down to the different file systems.
            This function basically takes the first element of the requested
            op's path, and hands down the op call to the associated sub fs
            from the dir_patterns dict.
        """
        ret = '[Unhandled Exception]'
        try:
            # root is the only directory we handle in this class
            if path == '/':
                print '->', op, path, repr(args)
                ret = getattr(self, op)(path, *args)
            # for everything else, consult the seven wise regexes
            else:
                pieces = list(x.decode('utf-8') for x in path.split('/')[1:])
                if pieces[0] not in self.dir_patterns:
                    print '!>', op, path, repr(args)
                    raise OSError(ENOENT, '')
                print '~>', self.dir_patterns[pieces[0]], op, path, repr(args)
                ret = getattr(self.dir_patterns[pieces[0]], op)(pieces[1:], *args)
            # do some encoding magic here
            if isinstance(ret, list):
                ret = list(x.encode('utf-8') for x in ret)
            else:
                try:
                    ret = ret.encode('utf-8')
                except AttributeError:
                    pass
            return ret
        except OSError, e:
            ret = str(e)
            raise
        finally:
            print '<-', op, repr(ret)

    def getattr(self, path, fh=None):
        """ This handles only the attributes of the root directory """
        st = {
            'st_mode': S_IFDIR | 0755,
            'st_nlink': 2,
        }
        st['st_ctime'] = st['st_mtime'] = st['st_atime'] = time()
        return st

    def readdir(self, path, fh):
        """ This handles only the file listing of the root directory """
        return ['.', '..' ] + self.dir_patterns.keys()

def mount(mountpoint, pathbase, db):
    fuse = FUSE(MovieFS(pathbase, db), mountpoint, foreground=True, nothreads=True, allow_other=True)

