from sqlalchemy import create_engine, Table, Column, Integer, String, MetaData, ForeignKey, DateTime
from sqlalchemy import or_, func
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql.expression import ClauseElement

from datetime import datetime

engine = create_engine('sqlite:///movies.db') # echo=True)
Session = sessionmaker(bind=engine)
session = Session()

Base = declarative_base()

def get_or_create(model, defaults=None, **kwargs):
    instance = session.query(model).filter_by(**kwargs).first()
    if instance:
        return instance, False
    else:
        params = dict((k, v) for k, v in kwargs.iteritems() if not isinstance(v, ClauseElement))
        if defaults is not None:
            params.update(defaults)
        instance = model(**params)
        session.add(instance)
        return instance, True

movie_actors = Table('movie_actors', Base.metadata,
    Column('actor_id', Integer, ForeignKey('actors.id')),
    Column('movie_id', Integer, ForeignKey('movies.id'))
)

movie_directors = Table('movie_directors', Base.metadata,
    Column('director_id', Integer, ForeignKey('directors.id')),
    Column('movie_id', Integer, ForeignKey('movies.id'))
)

movie_genres = Table('movie_genres', Base.metadata,
    Column('genre_id', Integer, ForeignKey('genres.id')),
    Column('movie_id', Integer, ForeignKey('movies.id'))
)

class Director(Base):
    __tablename__ = 'directors'

    id = Column(Integer, primary_key=True)
    name = Column(String(60), unique=True)

    def __init__(self, id, name):
        self.id = id
        self.name = name

    def get_or_create(id, name):
        act, _ = get_or_create(Director, id = id, name = name)
        return act
    get_or_create = staticmethod(get_or_create)

class Actor(Base):
    __tablename__ = 'actors'

    id = Column(Integer, primary_key=True)
    name = Column(String(60), unique=True)

    def __init__(self, id, name):
        self.id = id
        self.name = name

    def get_or_create(id, name):
        act, _ = get_or_create(Actor, id = id, name = name)
        return act
    get_or_create = staticmethod(get_or_create)

class Genre(Base):
    __tablename__ = 'genres'

    id = Column(Integer, primary_key=True)
    name = Column(String(60))
    url = Column(String(128))

    def __init__(self, name, url):
        self.name = name
        self.url = url

    def get_or_create(name, url):
        act, _ = get_or_create(Genre, name = name, defaults={ 'url': url })
        return act
    get_or_create = staticmethod(get_or_create)

    def __repr__(self):
       return "<Genre('%s')>" % (self.name)

class Movie(Base):
    __tablename__ = 'movies'

    id = Column(Integer, primary_key=True)
    name = Column(String(60))
    path = Column(String(128), unique=True)

    released = Column(DateTime)
    year = Column(Integer)
    homepage = Column(String(128))
    imdb_id = Column(String(16))
    tagline = Column(String(256))

    res_x = Column(Integer)
    res_y = Column(Integer)

    runtime = Column(Integer)
    budget = Column(Integer)
    revenue = Column(Integer)

    actors = relationship('Actor', secondary=movie_actors, backref='movies')
    directors = relationship('Director', secondary=movie_directors, backref='movies')
    genres = relationship('Genre', secondary=movie_genres, backref='movies')

    def __init__(self, id, path, info):

        self.id = id
        self.path = path.decode('utf-8')
        self.name = info['movie']['name']

        self.released = datetime.strptime(info['movie']['released'], '%Y-%m-%d')
        self.year = self.released.year
        self.homepage = info['movie']['homepage']
        self.imdb_id = info['movie']['imdb_id']
        self.tagline = info['movie']['tagline']

        self.res_x = int(info['attrs']['ID_VIDEO_WIDTH'])
        self.res_y = int(info['attrs']['ID_VIDEO_HEIGHT'])

        self.runtime = int(info['movie']['runtime']) if info['movie']['runtime'] is not None else None
        self.budget = int(info['movie']['budget']) if info['movie']['budget'] is not None else None
        self.revenue = int(info['movie']['revenue']) if info['movie']['revenue'] is not None else None

        self.actors = session.query(Actor).filter(Actor.name.in_(x['name'] for x in info['movie']['cast']['actor'])).all()
        if 'director' in info['movie']['cast']:
            self.directors = session.query(Director).filter(Director.name.in_(x['name'] for x in info['movie']['cast']['director'])).all()
        self.genres = session.query(Genre).filter(Genre.name.in_(info['movie']['categories']['genre'].keys())).all()

    def get_or_create(id, path, info):

        instance = session.query(Movie).filter_by(id = id).first()
        if instance:
            return instance
        else:
            genres = [ ]
            for genre in info['movie']['categories']['genre']:
                Genre.get_or_create(genre, info['movie']['categories']['genre'][genre])

            directors = [ ]
            if 'director' in info['movie']['cast']:
                for director in info['movie']['cast']['director']:
                    Director.get_or_create(director['id'], director['name'])

            actors = [ ]
            for actor in info['movie']['cast']['actor']:
                Actor.get_or_create(actor['id'], actor['name'])

            movie = Movie(id, path, info)
            session.add(movie)
            return movie
    get_or_create = staticmethod(get_or_create)

    def printinfo(self):
        return u"""
{} ({})
'{}'

Genres: {}

Released: {}
Runtime: {} Minutes
Homepage: {}
Imdb id: {}

Movie Resolution: {}x{}

Actors:
 - {}

""".format(self.name, self.year, self.tagline, ', '.join(x.name for x in self.genres), self.released.strftime('%d. %B %Y'), self.runtime, self.homepage, self.imdb_id, self.res_x, self.res_y, '\n - '.join(x.name for x in self.actors) )

    def __repr__(self):
       return "<Movie('%s','%s')>" % (self.name, self.path)

movie_cache = { }
def movieFromCache(queryname):
    if queryname is None:
        return None
    if queryname in movie_cache:
        return movie_cache[queryname]
    movie = session.query(Movie).filter(or_(Movie.name.like(queryname), Movie.imdb_id==queryname)).first()
    movie_cache[queryname] = movie
    if movie is not None:
        movie_cache[movie.imdb_id] = movie
    return movie_cache[queryname]

def init():
    Base.metadata.create_all(engine)
