from contextlib import contextmanager
from threading import Lock

from sqlalchemy import Column, ForeignKey, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy.orm import relationship, sessionmaker


class Base:
    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()


Base = declarative_base(cls=Base)
_Session = sessionmaker()
_lock = Lock()


class Poll(Base):
    id = Column(Integer, primary_key=True)
    addr = Column(String(500), nullable=False)
    question = Column(String(500), nullable=False)
    # date = Column(DateTime, default=func.now())

    options = relationship(
        "Option", backref="poll", cascade="all, delete, delete-orphan"
    )
    votes = relationship("Vote", backref="poll", cascade="all, delete, delete-orphan")


class Option(Base):
    id = Column(Integer, primary_key=True)
    poll_id = Column(Integer, ForeignKey("poll.id"), primary_key=True)
    text = Column(String(150), nullable=False)


class Vote(Base):
    addr = Column(String(500), primary_key=True)
    poll_id = Column(Integer, ForeignKey("poll.id"), primary_key=True)
    value = Column(Integer, nullable=False)


@contextmanager
def session_scope():
    """Provide a transactional scope around a series of operations."""
    with _lock:
        session = _Session()
        try:
            yield session
            session.commit()
        except:
            session.rollback()
            raise
        finally:
            session.close()


def init(path: str, debug: bool = False) -> None:
    """Initialize engine."""
    engine = create_engine(path, echo=debug)
    Base.metadata.create_all(engine)
    _Session.configure(bind=engine)
