from flask_ckeditor import CKEditorField
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField, TelField, TextAreaField
from wtforms.validators import DataRequired, Email, Length, URL

#User Registration Form
class RegisterForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(min=2, max=80)])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=8, max=128)])
    submit = SubmitField("Register")


#Blog Creation Form
class BlogForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired(), Length(max=250)])
    subtitle = StringField("Subtitle", validators=[DataRequired(), Length(max=250)])
    img_url = StringField("Image URL", validators=[DataRequired(), URL(), Length(max=250)])
    body = CKEditorField("Blog Content", validators=[DataRequired(), Length(min=10)])
    submit = SubmitField("Publish")


#Login form
class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Log In")


#Comments form
class CommentsForm(FlaskForm):
    comment = CKEditorField("Comment", validators=[DataRequired(), Length(min=2, max=5000)])
    submit = SubmitField("Submit")


class DeletePostForm(FlaskForm):
    submit = SubmitField("Delete Post")


class ContactForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(min=2, max=80)])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=120)])
    phone = TelField("Phone Number", validators=[DataRequired(), Length(min=6, max=30)])
    message = TextAreaField("Message", validators=[DataRequired(), Length(min=10, max=5000)])
    submit = SubmitField("Send Message")



