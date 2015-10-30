from random import choice

from db_engine.db_models import *
from db_engine.db_session import DBSession

from faker import internet, lorem

from __config import *


session = DBSession(DB_USER_NAME, DB_PASSWORD, DB_HOST,
                    DB_BASE_NAME, LOGGER_NAME)


def setup_db():
    users = []
    questions = []
    answers = []

    for _ in range(100):
        user = User(internet.user_name(), "1")
        users.append(user)

    session.add_all(users)
    session.commit()

    for _ in range(10):
        question = Question(lorem.paragraph(1), lorem.paragraphs(10))
        question.author = choice(users)
        questions.append(question)

    session.add_all(questions)
    session.commit()

    for q in questions:
        for _ in range(choice([2, 10])):
            answer = Answer(lorem.sentence(3))
            answer.author = choice(users)
            answer.question = q
            answers.append(answer)

    for a in answers:
        for u in users:
            rating = AnswerRating(choice([1, -1]))
            rating.user = u
            a.ratings.append(rating)

    session.add_all(answers)
    session.commit()


setup_db()

