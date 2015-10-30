from flask import g, render_template, request, redirect, url_for

from flask_login import LoginManager, login_user, logout_user, current_user
from flask_login import login_required

from sqlalchemy.orm import joinedload, contains_eager
from sqlalchemy.exc import IntegrityError

from .extensions.flask_new_classy import FlaskView, before, route

from db_engine.db_session import DBSession
from db_engine.db_models import *

from .forms import RegistrationForm, LoginForm, QuestionForm, AnswerForm

from __config import *

login_manager = LoginManager()


def before_request():
    """Setup database session and current user"""

    g.db_session = DBSession(DB_USER_NAME, DB_PASSWORD, DB_HOST,
                             DB_BASE_NAME, LOGGER_NAME)

    g.current_user = current_user


def teardown_app_context(*args, **kwargs):
    """Clear db session"""

    g.db_session.remove()


class UserView(FlaskView):

    @staticmethod
    @login_manager.user_loader
    def load_user(user_id):
        query = g.db_session.query(User).\
            outerjoin(User.ratings).\
            options(joinedload(User.ratings)).\
            filter(User.id == user_id)
        msg = "Cant find user with id {}"

        return g.db_session.get_one_or_log(query, msg)

    @route("/register/", methods=["GET", "POST"])
    def registration(self):
        """Register new user"""
        form = RegistrationForm(request.form)
        if request.method == "POST" and form.validate():
            user = User(
                request.form["username"],
                request.form["password"]
            )
            try:
                g.db_session.add(user)
                g.db_session.commit()

            except IntegrityError:

                form.errors["username"] = ["Username already taken"]

                return render_template("register.html", form=form)

            return redirect(url_for("IndexView:get"))

        return render_template("register.html", form=form)

    @route("/login/", methods=["GET", "POST"])
    def login(self):
        form = LoginForm(request.form)
        if request.method == "POST" and form.validate():

            username = request.form["username"]
            password = request.form["password"]

            query = g.db_session.query(User).\
                filter(User.username == username)

            msg = "Cant find user with username - {}"

            user = g.db_session.get_one_or_log(query, msg)

            if user and user.check_password(password):
                login_user(user)

                return redirect(url_for("IndexView:get"))

        return render_template("login.html", form=form)

    def logout(self):
        if current_user.is_authenticated:
            logout_user()

            return redirect(url_for("IndexView:get"))


class IndexView(FlaskView):

    route_base = "/"

    @staticmethod
    def get_latest_questions():
        """Get questions for main page"""
        g.questions = g.db_session.query(Question).\
            order_by(desc(Question.date)).all()

    @staticmethod
    def get_single_question(id_):
        """Get single question

            :param id_:
                Question id

        """
        query = g.db_session.query(Question).\
            outerjoin(Question.answers).\
            options(contains_eager(Question.answers)).\
            filter(Question.id == id_).\
            order_by(desc(Answer.rating))

        msg = "can't find question with id {}"

        g.question = g.db_session.get_one_or_log(query, msg.format(id_))

    @staticmethod
    def get_answer(id_):
        """Get answer to rate for"""
        query = g.db_session.query(Answer).\
            filter(Answer.id == id_)

        msg = "Can't find answer with id {}"

        g.answer = g.db_session.get_one_or_log(query, msg)

    @before(get_latest_questions)
    def get(self):
        """Index page"""
        return render_template("index.html")

    @before(get_single_question)
    @route("/question/<id_>", methods=["GET", "POST"])
    def show_question(self, id_):
        """Show single question page

            :param id_:
                Question id

        """
        if g.current_user.is_authenticated:
            g.answer_form = AnswerForm()
            if request.method == "POST" and g.answer_form.validate():
                answer = Answer(
                    request.form["content"]
                )
                answer.author = current_user
                answer.question_id = id_
                g.db_session.add(answer)
                g.db_session.commit()
                return redirect(url_for("IndexView:show_question", id_=id_))
        return render_template("question.html")

    @login_required
    @route("/question/new", methods=["GET", "POST"])
    def create_question(self):
        """Aks new question"""
        form = QuestionForm(request.form)
        if request.method == "POST" and form.validate():

            question = Question(
                request.form["title"],
                request.form["content"],
            )
            question.author = current_user

            g.db_session.add(question)
            g.db_session.commit()

            return redirect("/")

        return render_template("question_new.html", form=form)

    @before(get_answer)
    @login_required
    @route("/answer/rate/<id_>")
    def rate_answer(self, id_):
        """Rate answer

            :param id_:
                Answer id to rate

        """
        if g.answer:
            rating = -1
            if request.args.get("action") == "up":
                rating = 1
            rate = AnswerRating(rating)

            rate.user = current_user
            rate.answer_id = id_
            g.answer.ratings.append(rate)
            g.db_session.add(g.answer)
            g.db_session.commit()

            return redirect(url_for("IndexView:show_question", id_=g.answer.question_id))