from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

Base = declarative_base()


class Author(Base):
    __tablename__ = "authors"

    id = Column(Integer, primary_key=True)
    username = Column(String(50), nullable=False, unique=True)

    # 一个作者可以有多个主题帖和多个回帖
    topics = relationship(
        "Topic", back_populates="author", cascade="all, delete-orphan"
    )
    posts = relationship("Post", back_populates="author", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Author(id={self.id}, username='{self.username}')>"


class Board(Base):
    __tablename__ = "boards"

    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False, unique=True)
    description = Column(String(200))

    # 一个板块包含多个主题帖
    topics = relationship("Topic", back_populates="board", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Board(id={self.id}, name='{self.name}')>"


class Topic(Base):
    __tablename__ = "topics"

    id = Column(Integer, primary_key=True)
    reid = Column(Integer, unique=True)
    title = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    content = Column(Text, nullable=False)

    author_id = Column(Integer, ForeignKey("authors.id"), nullable=False)
    board_id = Column(Integer, ForeignKey("boards.id"), nullable=False)

    author = relationship("Author", back_populates="topics")
    board = relationship("Board", back_populates="topics")
    posts = relationship("Post", back_populates="topic", cascade="all, delete-orphan")

    def __repr__(self):
        return (
            f"<Topic(id={self.id}, title='{self.title}', author_id={self.author_id})>"
        )


class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=False)
    author_id = Column(Integer, ForeignKey("authors.id"), nullable=False)
    reply_to_id = Column(Integer, ForeignKey('posts.id'), nullable=True)  # 可为空

    topic = relationship("Topic", back_populates="posts")
    author = relationship("Author", back_populates="posts")

    parent = relationship("Post", remote_side=[id], back_populates="replies")
    replies = relationship("Post", back_populates="parent")

    def __repr__(self):
        return f"<Post(id={self.id}, content='{self.content[:20]}...', topic_id={self.topic_id}, author_id={self.author_id})>"


def make_session(postgres: str):
    engine = create_engine(postgres, echo=False)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()
