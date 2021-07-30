from math import sin, cos, sqrt, atan2, radians
import os
from datetime import date, datetime
from flask import Flask, render_template, request, redirect
from flask.helpers import flash, url_for
from flask_login.mixins import UserMixin
from flask_login.utils import login_required, logout_user
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from werkzeug import datastructures
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, login_user, current_user
import requests
from sqlalchemy import extract

app = Flask(__name__)

app.config['SECRET_KEY'] = 'secret'

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
# SQL Database Section
# basedir = os.path.abspath(os.path.dirname(__file__))
# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + \
#    os.path.join(basedir, 'data.sqlite')
uri = os.getenv("DATABASE_URL")  # or other relevant config var
if uri.startswith("postgres://"):
    uri = uri.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
Migrate(app, db)

login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.init_app(app)


def getDistanceFromGoogle(start_latitude, start_longitude, finish_latitude, finish_longitude):
    # return None if start and finish positions are None
    if start_latitude is None:
        return None
    if start_longitude is None:
        return None
    if finish_latitude is None:
        return None
    if finish_longitude is None:
        return None

    response = requests.get(
        f"https://maps.googleapis.com/maps/api/distancematrix/json?origins={start_latitude},{start_longitude}&destinations={finish_latitude},{finish_longitude}&key={GOOGLE_API_KEY}")
    distance = response.json()["rows"][0]["elements"][0]["distance"]["value"]

    return distance


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
    report = db.Column(db.Boolean)
    user_id = db.Column(db.Integer, db.ForeignKey('Users.id'))
    user = db.relationship("User", backref="Trips")

    # start location
    # latitute, logitude
    start_latitude = db.Column(db.Numeric)
    start_longitude = db.Column(db.Numeric)

    # finish location
    # latitute, logitude
    finish_latitude = db.Column(db.Numeric)
    finish_longitude = db.Column(db.Numeric)

    def __init__(self, customer, date, location, distance, user_id, report=False):
        self.customer = customer
        self.date = date
        self.location = location
        self.distance = distance
        self.report = report
        self.user_id = user_id

    def distanceBetweenTwoPoints(self):
        # return None if start and finish positions are None
        if self.start_latitude is None:
            return None
        if self.start_longitude is None:
            return None
        if self.finish_latitude is None:
            return None
        if self.finish_longitude is None:
            return None

        # approximate radius of earth in km
        R = 6373.0

        lat1 = radians(self.start_latitude)
        lon1 = radians(self.start_longitude)
        lat2 = radians(self.finish_latitude)
        lon2 = radians(self.finish_longitude)

        dlon = lon2 - lon1
        dlat = lat2 - lat1

        a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))

        distance = R * c
        return distance


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/home")
@login_required
def calendar():
    month_year = request.args.get("month")
    filter_date = date.today()
    if month_year:
        filter_date = datetime.strptime(month_year, '%Y-%m').date()

    trips = []
    total_distance = 0
    pricePerDistance = 5
    if current_user.is_admin:
        trips = Trips.query.filter(
            extract('year', Trips.date) == filter_date.year, extract('month', Trips.date) == filter_date.month)
        for trip in trips:
            if trip.distance is not None:
                total_distance += trip.distance
    else:
        # else, show user's trips
        trips = Trips.query.filter_by(user_id=current_user.id)
        for trip in trips:
            if trip.distance is not None:
                total_distance += trip.distance
    return render_template("calendar.html", trips=trips, total_distance=total_distance, total_price=total_distance*pricePerDistance/1000, month=month_year)


@app.route("/login", methods=["GET", "POST"])
def login():
    users = User.query.all()
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user = User.query.filter_by(username=username).first()
        if not user or not check_password_hash(user.password, password):
            flash("User Not Found or Incorrect Password")
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

        # TODO: check whether password == confirm_password
        if password != confirm_password:
            flash("Password not match!!!")
            return redirect(url_for("addusers"))

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
        report = request.form.get("report")
        user_id = current_user.id

        date = datetime.fromisoformat(date_string)

        trips = Trips(customer=customer, date=date,
                      location=location, distance=distance, user_id=user_id)
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

# delete function


@app.route("/delete-user/<int:id>")
@login_required
def deleteUser(id):
    User.query.filter_by(id=id).delete()
    db.session.commit()
    return redirect(url_for("usersdata"))


@app.route("/delete-trips/<int:id>")
@login_required
def deleteTrips(id):
    Trips.query.filter_by(id=id).delete()
    db.session.commit()
    return redirect(url_for("calendar"))


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

        if password != confirm_password:
            flash("Password not match!!!")
            return redirect(url_for("addusers"))

        user = User(firstname=firstname, lastname=lastname,
                    gmail=gmail, username=username, password=password, is_admin=is_admin)
        db.session.add(user)
        db.session.commit()
        return redirect(url_for("usersdata"))

    return render_template("addusers.html")


# /viewtrips/:tripid
# /viewtrips/1


@app.route("/viewtrips/<int:id>", methods=["GET", "POST"])
@login_required
def viewtrips(id):
    trip = Trips.query.get(id)

    # check if method is POST
    if request.method == "POST":
        start_latitude = request.form.get("start-latitude")
        start_longitude = request.form.get("start-longitude")
        finish_latitude = request.form.get("finish-latitude")
        finish_longitude = request.form.get("finish-longitude")
        report = request.form.get("report")
        print(report)

        # if has both start and finish location
        distance = getDistanceFromGoogle(
            start_latitude, start_longitude, finish_latitude, finish_longitude)

        trip.start_latitude = start_latitude
        trip.start_longitude = start_longitude
        trip.finish_latitude = finish_latitude
        trip.finish_longitude = finish_longitude
        trip.distance = distance
        trip.report = True if report == 'yes' else False

        db.session.add(trip)
        db.session.commit()

        return redirect(url_for("calendar"))
    return render_template("viewtrips.html", trip=trip)
