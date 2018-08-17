import os

from flask import Flask, session, render_template, request
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from helpers import *

import requests

app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


@app.route("/", methods=["GET", "POST"])
def index():

    # Ensure user is logged in first
    if session.get("user_id") is None:
        return redirect("/login")

    # User reached route via POST (submitted a form)
    if request.method == "POST":

        # Ensure book is submitted
        if not request.form.get("book"):
            return error("must sumbit info of book for search")

        # Search for book in database
        search = request.form.get("book").lower()
        book = "%" + search + "%"
        books = db.execute("SELECT * FROM books WHERE (LOWER(isbn) LIKE :book) OR (LOWER(title) LIKE :book) OR (LOWER(author) LIKE :book) LIMIT 15", {"book": book}).fetchall()

        # if no matching results, show error message
        if len(books) == 0:
            return error("No matching results")

        # if matching results, show lists of books
        else:
            return render_template("results.html", search=search, books=books)

    # User reached route via GET
    else:
        return render_template("index.html")


@app.route("/book/<isbn>")
def book(isbn):

    # Ensure user is logged in first
    if session.get("user_id") is None:
        return redirect("/login")

    # Query for book data
    book = db.execute("SELECT * FROM books WHERE isbn=:isbn", {"isbn": isbn}).fetchone()
    if book is None:
        return error("Error in retrieving data")

    # Query for book ratings from Goodreads API
    res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "lV6JRoF2Xl75SN1f9SgOmQ", "isbns": isbn})
    data = res.json()
    books = data["books"][0]
    rating_count = books["work_ratings_count"]
    avg_rating = books["average_rating"]

    # Query for book reviews

    # Display book page for details
    return render_template("book.html", book=book, rating_count=rating_count, avg_rating=avg_rating)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return error("must submit username")

        # Ensure password was sumbitted
        elif not request.form.get("password"):
            return error("must submit password")

        # Query for username and password
        username = request.form.get("username")
        password = request.form.get("password")
        user_id = db.execute("SELECT id FROM users WHERE (username=:username AND password=:password)", {"username": username, "password": password}).fetchone()

        # Ensure username exists and password matches
        if user_id is None:
            return error("user does not exist or password does not match")

        # If login credentials passes, store in session
        session["user_id"] = user_id;

        return redirect("/")

        # Ensure username exists and password is correct
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():

    # Forget any user_id
    session.clear()

    # Redirect to login page
    return redirect("/")


@app.route("/register", methods=["GET", "POST"])
def register():

    # User reached route via POST
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return error("must submit username")
        # Ensure password was sumbitted
        elif not request.form.get("password"):
            return error("must submit password")
        # Ensure confirmation was submitted
        elif not request.form.get("comfirmation"):
            return error("must confirm password")
        # Ensure confirmation and password match
        elif not request.form.get("comfirmation") == request.form.get("password"):
            return error("password not matching")

        # Register username and password into database (w/o hashing)
        username = request.form.get("username")
        password = request.form.get("password")
        db.execute("INSERT INTO users(username, password) VALUES(:username, :password)", {"username": username, "password": password})
        db.commit()

        # Log in credentials automatically
        user_id = db.execute("SELECT id FROM users WHERE (username=:username AND password=:password)", {"username": username, "password": password}).fetchone()
        if user_id is None:
            return error("not registered")
        session["user_id"] = user_id;

        # redirect user to login page
        return redirect("/")

    # User reached route via GET
    else:
        return render_template("register.html")