from flask import Flask, abort, render_template, redirect, url_for, flash, request
from flask_bootstrap import Bootstrap5
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import Integer, String, Text, ForeignKey
from flask_ckeditor import CKEditor
from forms import RegisterForm, BlogForm, LoginForm, CommentsForm, DeletePostForm, ContactForm
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin, LoginManager, current_user, login_user, logout_user, login_required
from typing import List
from dotenv import load_dotenv
from markupsafe import Markup
import bleach
import datetime
import hashlib
import os
import smtplib
from email.message import EmailMessage

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
if not app.config['SECRET_KEY']:
    raise RuntimeError("SECRET_KEY is missing. Add it to your .env file.")
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DB_URI', 'sqlite:///Blogs.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['WTF_CSRF_ENABLED'] = True
Bootstrap5(app)
ckeditor = CKEditor(app)

# For adding profile images to the comment section
def gravatar_url(email, size=100, default="identicon", rating="g"):
    email_hash = hashlib.md5(email.strip().lower().encode("utf-8")).hexdigest()
    return f"https://www.gravatar.com/avatar/{email_hash}?s={size}&d={default}&r={rating}"

app.jinja_env.filters['gravatar'] = gravatar_url

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# CREATE DATABASE
class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
db.init_app(app)

# User Table
class Users(UserMixin, db.Model):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String, nullable=False)
    posts: Mapped[List["BlogPost"]] = relationship(
        back_populates="author",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    user_comments: Mapped[List["Comments"]] = relationship(
        back_populates="comment_author",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    author: Mapped[Users] = relationship(back_populates="posts", lazy="joined")
    title: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    subtitle: Mapped[str] = mapped_column(String(250), nullable=False)
    date: Mapped[str] = mapped_column(String(250), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    img_url: Mapped[str] = mapped_column(String(250), nullable=False)
    blog_comments: Mapped[List["Comments"]] = relationship(
        back_populates="parent_post",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

class Comments(db.Model):
    __tablename__ = "comments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    comment_author: Mapped[Users] = relationship(back_populates="user_comments", lazy="joined")
    post_id: Mapped[int] = mapped_column(ForeignKey("blog_posts.id"), nullable=False)
    parent_post: Mapped["BlogPost"] = relationship(back_populates="blog_comments", lazy="joined")

with app.app_context():
    db.create_all()

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(Users, int(user_id))

def is_admin(user):
    if not user or not user.is_authenticated:
        return False
    admin_emails = {
        email.strip().lower()
        for email in os.environ.get("ADMIN_EMAILS", "").split(",")
        if email.strip()
    }
    return user.email.lower() in admin_emails

def can_manage_post(post):
    return current_user.is_authenticated and (
        post.author_id == current_user.id or is_admin(current_user)
    )

# Registration
@app.route('/register', methods=["POST", "GET"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('get_all_posts'))

    form = RegisterForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        if Users.query.filter_by(email=email).first():
            flash("The email is already registered. Please login instead!", "danger")
            return redirect(url_for('login'))

        new_user = Users(
            name=form.name.data.strip(),
            email=email,
            password=generate_password_hash(form.password.data, method='pbkdf2:sha256', salt_length=8)
        )
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        flash("Registration Successful!", "success")
        return redirect(url_for('get_all_posts'))

    return render_template('register.html', form=form)

@app.route('/login', methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('get_all_posts'))

    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        user = Users.query.filter_by(email=email).first()
        if not user:
            flash("The email does not exist. Please register first.", "danger")
            return redirect(url_for('register'))
        if not check_password_hash(user.password, form.password.data):
            flash("Wrong password. Please try again!", "danger")
            return redirect(url_for('login'))

        login_user(user)
        flash("Login Successful!", "success")
        return redirect(url_for('get_all_posts'))

    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Logged out successfully!", "success")
    return redirect(url_for('get_all_posts'))

@app.route('/')
def get_all_posts():
    posts = db.session.execute(db.select(BlogPost).order_by(BlogPost.id.desc())).scalars().all()
    return render_template("index.html", all_posts=posts)

@app.route('/show_post/<int:post_id>', methods=["GET", "POST"])
def show_post(post_id):
    comment_form = CommentsForm()
    requested_post = db.get_or_404(BlogPost, post_id)

    if comment_form.validate_on_submit():
        if not current_user.is_authenticated:
            flash("Login required. Please log in.", "danger")
            return redirect(url_for('login'))

        db.session.add(Comments(
            text=comment_form.comment.data,
            author_id=current_user.id,
            post_id=post_id
        ))
        db.session.commit()
        flash("Comment added!", "success")
        return redirect(url_for('show_post', post_id=post_id))

    return render_template("post.html", post=requested_post, form=comment_form)

@app.route('/make-post', methods=["POST", "GET"])
@login_required
def make_post():
    form = BlogForm()
    if form.validate_on_submit():
        new_blog = BlogPost(
            title=form.title.data.strip(),
            author_id=current_user.id,
            subtitle=form.subtitle.data.strip(),
            date=datetime.date.today().isoformat(),
            img_url=form.img_url.data.strip(),
            body=form.body.data
        )
        db.session.add(new_blog)
        db.session.commit()
        flash("Post Created!", "success")
        return redirect(url_for('show_post', post_id=new_blog.id))
    return render_template('make-post.html', form=form)

@app.route("/edit-post/<int:post_id>", methods=["GET", "POST"])
@login_required
def edit_post(post_id):
    post = db.get_or_404(BlogPost, post_id)
    if not can_manage_post(post):
        abort(403)

    edit_form = BlogForm(obj=post)
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data.strip()
        post.subtitle = edit_form.subtitle.data.strip()
        post.img_url = edit_form.img_url.data.strip()
        post.body = edit_form.body.data
        post.date = datetime.date.today().isoformat()
        db.session.commit()
        flash("Post Edited!", "success")
        return redirect(url_for('show_post', post_id=post.id))

    return render_template("make-post.html", edit_form=edit_form, is_edit=True)

@app.route('/delete_post/<int:post_id>', methods=["POST"])
@login_required
def delete_post(post_id):
    post = db.get_or_404(BlogPost, post_id)
    if not can_manage_post(post):
        abort(403)

    form = DeletePostForm()
    if not form.validate_on_submit():
        abort(400)

    db.session.delete(post)
    db.session.commit()
    flash("Post Deleted!", "success")
    return redirect(url_for('get_all_posts'))

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/contact", methods=["GET", "POST"])
def contact():
    form = ContactForm()
    msg_sent = False

    if form.validate_on_submit():
        smtp_host = os.environ.get("SMTP_HOST")
        smtp_port = int(os.environ.get("SMTP_PORT", "587"))
        smtp_user = os.environ.get("SMTP_USER")
        smtp_password = os.environ.get("SMTP_PASSWORD")
        contact_to = os.environ.get("CONTACT_EMAIL")

        if smtp_host and smtp_user and smtp_password and contact_to:
            message = EmailMessage()
            message["Subject"] = f"Blog contact from {form.name.data.strip()}"
            message["From"] = smtp_user
            message["To"] = contact_to
            message["Reply-To"] = form.email.data.strip()
            message.set_content(
                f"Name: {form.name.data.strip()}\n"
                f"Email: {form.email.data.strip()}\n"
                f"Phone: {form.phone.data.strip()}\n\n"
                f"Message:\n{form.message.data.strip()}"
            )
            try:
                with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as server:
                    server.starttls()
                    server.login(smtp_user, smtp_password)
                    server.send_message(message)
                msg_sent = True
                flash("Your message was sent successfully!", "success")
            except smtplib.SMTPException:
                flash("The message could not be sent. Please try again later.", "danger")
        else:
            flash("Contact email is not configured by the site administrator.", "warning")

    return render_template("contact.html", form=form, msg_sent=msg_sent)

@app.errorhandler(403)
def forbidden(_error):
    return render_template("403.html"), 403

def sanitize_html(value):
    allowed_tags = [
        "p", "br", "strong", "em", "u", "b", "i", "s",
        "ul", "ol", "li", "blockquote", "a", "h1", "h2", "h3", "h4"
    ]
    allowed_attributes = {"a": ["href", "title"]}
    clean = bleach.clean(
        value,
        tags=allowed_tags,
        attributes=allowed_attributes,
        protocols=["http", "https", "mailto"],
        strip=True
    )
    return Markup(clean)

app.jinja_env.filters['sanitize'] = sanitize_html
app.jinja_env.globals['is_admin'] = is_admin
app.jinja_env.globals['can_manage_post'] = can_manage_post

if __name__ == "__main__":
    app.run(debug=False, port=5003)





