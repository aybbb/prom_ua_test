import datetime

from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship, backref

from sqlalchemy import UnicodeText, Integer, Text
from sqlalchemy import DateTime, ForeignKey
from sqlalchemy import Column
from sqlalchemy import func, select, desc

import bcrypt


class Base(object):

    @declared_attr
    def __tablename__(self):
        name = self.__name__

        def split_upper(line):
            for ind in range(1, len(line)):
                if line[ind].isupper():
                    if not line[ind + 1:].islower():
                        return [line[:ind].lower()] + split_upper(line[ind:])
                    else:
                        return [line[:ind].lower(), line[ind:].lower()]
            return [line.lower()]
        return "_".join(split_upper(name))


Base = declarative_base(cls=Base)


class User(Base):

    id = Column("id", Integer, primary_key=True)
    username = Column("username", UnicodeText, nullable=False, unique=True)
    password = Column("password", Text, nullable=False)
    questions = relationship(
        "Question",
        backref=backref("author", order_by=id)
    )
    answers = relationship(
        "Answer",
        backref=backref("author", order_by=id)
    )

    def __init__(self, username, password):
        self.username = username
        self.password = bcrypt.hashpw(password,
                                      bcrypt.gensalt(10))

    @staticmethod
    def is_authenticated():
        return True

    @staticmethod
    def is_active():
        return True

    @staticmethod
    def is_anonymous():
        return False

    def get_id(self):
        return getattr(self, "id")

    def check_password(self, password):
        return self.password == bcrypt.hashpw(password,
                                              self.password)

    def voted_for(self, answer_id):
        return answer_id in [x.answer_id for x in self.ratings]



class Question(Base):

    id = Column("id", Integer, primary_key=True)
    title = Column("title", UnicodeText, nullable=False)
    content = Column("content", UnicodeText, nullable=False)
    date = Column("date", DateTime, nullable=False)
    user_id = Column(Integer, ForeignKey("user.id"))
    answers = relationship(
        "Answer",
        backref=backref("question")
    )

    def __init__(self, title, content):
        self.title = title
        self.content = content
        self.date = datetime.datetime.now()

    @hybrid_property
    def answers_count(self):
        return len(self.answers)


class Answer(Base):

    id = Column("id", Integer, primary_key=True)
    content = Column("content", UnicodeText, nullable=False)
    date = Column("date", DateTime, nullable=False)
    user_id = Column(Integer, ForeignKey("user.id"))
    question_id = Column(Integer, ForeignKey("question.id"))
    ratings = relationship(
        "AnswerRating",
        backref=backref("answer")
    )

    def __init__(self, content):
        self.content = content
        self.date = datetime.datetime.now()

    @hybrid_property
    def rating(self):
        return sum([x.rating for x in self.ratings])

    @rating.expression
    def rating(cls):
        return select([func.sum(AnswerRating.rating)]).\
            where(AnswerRating.answer_id == cls.id)


class AnswerRating(Base):

    answer_id = Column(Integer, ForeignKey("answer.id"), primary_key=True)
    user_id = Column(Integer, ForeignKey("user.id"), primary_key=True)
    rating = Column("rating", Integer, nullable=False)
    user = relationship(
        "User",
        backref=backref("ratings")
    )

    def __init__(self, rating):
        self.rating = rating