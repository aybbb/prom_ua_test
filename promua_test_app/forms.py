from functools import partial

from wtforms import StringField, TextAreaField, PasswordField
from wtforms.validators import DataRequired, EqualTo
from flask_wtf import Form

missing_error = lambda msg: partial(DataRequired,
                                    message="{} : this field is required".format(msg))

equal_error = lambda msg, field: partial(EqualTo,
                                         fieldname=field,
                                         message="{} do not match".format(msg))


class RegistrationForm(Form):

    username = StringField("User name", validators=[missing_error("Username")()])
    password = PasswordField("Password", validators=[missing_error("Password")(),
                                                     equal_error("Password",
                                                                 "password_")()])
    password_ = PasswordField("Repeat password")


class LoginForm(Form):

    username = StringField("User name", validators=[missing_error("Username")()])
    password = PasswordField("Password", validators=[missing_error("Password")()])


class QuestionForm(Form):

    title = StringField("Title", validators=[missing_error("Title")()])
    content = TextAreaField("Content", validators=[missing_error("Content")()])


class AnswerForm(Form):

    content = TextAreaField("Content", validators=[missing_error("Content")()])