import os
from datetime import datetime
from flask import Flask, render_template, request, redirect
from flask.helpers import url_for
from flask_login.mixins import UserMixin
from flask_login.utils import login_required, logout_user
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from werkzeug import datastructures
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, login_user, current_user


app = Flask(__name__)

app.config['SECRET_KEY'] = 'secret'

# SQL Database Section
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + \
    os.path.join(basedir, 'data.sqlite')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
Migrate(app, db)

login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(db.Model, UserMixin):
    __tablename__ = "Users"
    id = db.Column(db.Integer, primary_key=True)
    firstname = db.Column(db.Text)
    lastname = db.Column(db.Text)

    username = db.Column(db.Text, unique=True)
    password = db.Column(db.Text)

    is_admin = db.Column(db.Boolean)
    gmail = db.Column(db.Text)

    def __init__(self, firstname, lastname, gmail, username, password, is_admin):
        self.firstname = firstname
        self.lastname = lastname
        self.gmail = gmail
        self.username = username
        self.password = generate_password_hash(password)
        self.is_admin = is_admin


class Trips(db.Model):
    __tablename__ = "Trips"
    id = db.Column(db.Integer, primary_key=True)
    customer = db.Column(db.Text)
    date = db.Column(db.DateTime(timezone=True))
    location = db.Column(db.Text)
    distance = db.Column(db.Numeric)
    comment = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('Users.id'))
    user = db.relationship("User", backref="Trips")

    def __init__(self, customer, date, location, distance, comment, user_id):
        self.customer = customer
        self.date = date
        self.location = location
        self.distance = distance
        self.comment = comment
        self.user_id = user_id


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/home")
@login_required
def calendar():
    trips = Trips.query.all()
    users = User.query.all()
    return render_template("calendar.html", trips=trips, users=users)


@app.route("/login", methods=["GET", "POST"])
def login():
    users = User.query.all()
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user = User.query.filter_by(username=username).first()
        if not user or not check_password_hash(user.password, password):
            return redirect(url_for("login"))
        login_user(user)
        return redirect(url_for("calendar"))
    return render_template("login.html", users=users)


@app.route("/register", methods=["GET", "POST"])
def register():
    # redirect to login page if users length > 0
    # query all users
    users = User.query.all()
    # check users count > 0
    if len(users) > 0:
        return redirect(url_for("login"))
    if request.method == "POST":
        firstname = request.form.get("firstname")
        lastname = request.form.get("lastname")
        gmail = request.form.get("gmail")
        username = request.form.get("username")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm-password")
        user = User(firstname=firstname, lastname=lastname,
                    gmail=gmail, username=username, password=password, is_admin=True)
        db.session.add(user)
        db.session.commit()
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


@app.route("/addtrips", methods=["GET", "POST"])
@login_required
def addtrips():
    if request.method == "POST":
        customer = request.form.get("customer")
        date_string = request.form.get("date")
        location = request.form.get("location")
        distance = request.form.get("distance")
        comment = request.form.get("comment")
        user_id = current_user.id

        date = datetime.fromisoformat(date_string)

        trips = Trips(customer=customer, date=date,
                      location=location, distance=distance, comment=comment, user_id=user_id)
        db.session.add(trips)
        db.session.commit()
        return redirect(url_for("calendar"))
    return render_template("addtrips.html")


@app.route("/usersdata")
@login_required
def usersdata():
    # if current user is not admin, redirect to home
    if not current_user.is_admin:
        return redirect(url_for("index"))
    users = User.query.all()
    return render_template("usersdata.html", users=users)


@app.route("/usersdata/add", methods=["GET", "POST"])
@login_required
def addusers():
    # if current user is not admin, redirect to home
    if not current_user.is_admin:
        return redirect(url_for("index"))

    if request.method == "POST":
        firstname = request.form.get("firstname")
        lastname = request.form.get("lastname")
        gmail = request.form.get("gmail")
        username = request.form.get("username")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm-password")
        is_admin = request.form.get("is-admin")
        user = User(firstname=firstname, lastname=lastname,
                    gmail=gmail, username=username, password=password, is_admin=is_admin)
        db.session.add(user)
        db.session.commit()
        return redirect(url_for("usersdata"))

    return render_template("addusers.html")


@app.route("/tripsdata")
@login_required
def tripsdata():
    trips = Trips.query.all()
    return render_template("tripsdata.html", trips=trips)


@app.route("/viewtrips")
@login_required
def viewtrips():
    return render_template("viewtrips.html")


@app.route("/admin")
@login_required
def admin():
    users = User.query.all()
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user = User.query.filter_by(username=username).first()
        if not user or not check_password_hash(user.password, password):
            return redirect(url_for("login"))
        login_user(user)
        return redirect(url_for("calendar"))
    return render_template("admin.html", users=users)
