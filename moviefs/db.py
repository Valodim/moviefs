from sqlalchemy import create_engine, Table, Column, Integer, String, MetaData, ForeignKey, DateTime
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql.expression import ClauseElement

engine = create_engine('sqlite:///movies.db', echo=True)
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

    def __init__(self, name, path):
        self.name = name

    def __repr__(self):
       return "<Genre('%s')>" % (self.name)

class Movie(Base):
    __tablename__ = 'movies'

    id = Column(Integer, primary_key=True)
    name = Column(String(60))
    path = Column(String(128), unique=True)
    res_x = Column(Integer)
    res_y = Column(Integer)
    year = Column(DateTime)

    actors = relationship('Actor', secondary=movie_actors, backref='movies')

    def __init__(self, id, path, info):
        self.path = path

        self.id = id
        self.name = info['movie']['name']
        self.res_x = int(info['attrs']['ID_VIDEO_WIDTH'])
        self.res_y = int(info['attrs']['ID_VIDEO_HEIGHT'])
        self.actors = session.query(Actor).filter(Actor.name.in_(x['name'] for x in info['movie']['cast']['actor'])).all()

    def get_or_create(id, path, info):

        instance = session.query(Movie).filter_by(id = id).first()
        if instance:
            return instance
        else:
            actors = [ ]
            for actor in info['movie']['cast']['actor']:
                Actor.get_or_create(actor['id'], actor['name'])

            movie = Movie(id, path, info)
            session.add(movie)
            return movie
    get_or_create = staticmethod(get_or_create)

    def __repr__(self):
       return "<Movie('%s','%s')>" % (self.name, self.path)

def init():
    Base.metadata.create_all(engine)
