import os

from flask import Flask, session, render_template, request, redirect, url_for, jsonify
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
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


@app.route("/")
def index():
    return "Project 1: TODO"

@app.route("/entrance")
def entrance():
    return render_template("entrance.html")

@app.route("/viewRegister")
def viewRegister():
    return render_template("viewRegister.html")

@app.route("/viewLogin")
def viewLogin():
    return render_template("viewLogin.html")

@app.route("/search/<string:name>", methods = ["POST"])
def search(name):    
    info = request.form.get("book")   

    info =  ('%' + info + '%')
    books = db.execute("SELECT * FROM books WHERE (isbn LIKE :info) OR (title LIKE :info) OR (author LIKE :info)", {"info": info}).fetchall()

    if books == []:
        return "No books found"
    elif books[1:] == []:
        temp = books[0]       
        return redirect(url_for('homePage',name = name, isbn = temp.isbn))       
    else:
        return render_template("books.html", books =  books, name = name)

@app.route("/register", methods=["POST"])
def register():
    name = request.form.get("name")
    password = request.form.get("password")    
    user = db.execute("SELECT * FROM users WHERE name = :name", {"name":name}).fetchone()
    
    if user is not None:
        return render_template("inform.html",message = "Name is already used!")

    db.execute("INSERT INTO users (name, password) VALUES (:name, :password)",
            {"name": name, "password": password})
    db.commit()
    return render_template("inform.html",message = "Register Successful!")

@app.route("/login", methods=["POST"])
def login():
    name = request.form.get("name")
    password = request.form.get("password")
    
    temp = db.execute("SELECT * FROM users WHERE (name = :name) AND (password = :password)", {"name":name, "password": password}).fetchone()
    
    if temp is None:      
        return render_template("inform.html",message = "Account is invalid!")          
    else:        
        firstBook = db.execute("SELECT * FROM books").fetchone()
        return redirect(url_for('homePage',name = name, isbn = firstBook.isbn))       

@app.route("/review/<string:name>/<string:isbn>", methods=["POST"])
def review(name, isbn):
    reviews = request.form.get("reviews")
    rate = request.form.get("rate")
    
    check = db.execute("SELECT * FROM reviews WHERE user_name = :name",{"name": name}).fetchone()
    if check is not None:
        return "You already reviewed!"

    db.execute ("INSERT INTO reviews (book_isbn, user_name, reviews, rate) VALUES (:isbn, :name, :reviews, :rate)",
                {"isbn": isbn, "name": name, "reviews":reviews, "rate": rate})
    db.commit()
    return "Commented!"
    
@app.route("/homePage/<string:name>/<string:isbn>")
def homePage(name, isbn):
    book = db.execute("SELECT * FROM books WHERE isbn = :isbn",{"isbn": isbn}).fetchone()
    reviews = db.execute("SELECT * FROM reviews WHERE book_isbn=:isbn",{"isbn":isbn}).fetchall()

    res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "a2cOYsYBs3Elc6DpzWxABA", "isbns": isbn})
 
    if res.status_code != 200: 
        rate = 0.0
    else:        
        data = res.json()
        rate = data["books"][0]["average_rating"] 

    if reviews == []:
        return render_template("homePage.html", book = book, name = name, rate = rate)
    else:            
        return render_template("homePage.html",book = book, name = name, reviews = reviews, rate = rate)

@app.route("/info/api/<string:isbn>", methods = ["GET"])
def info(isbn):
    temp = '%' + isbn + '%'
    book = db.execute("SELECT * FROM books WHERE isbn LIKE :isbn", {"isbn": temp}).fetchone()
    if book is None:
            return jsonify({"error": "Invalid isbn"}), 422
    res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "a2cOYsYBs3Elc6DpzWxABA", "isbns": isbn})

    if res.status_code != 200:    
        return jsonify({
                "title": book.title,
                "author": book.author,
                "year": book.year,
                "isbn": book.isbn                    
        })
    else:
        data = res.json()
        count = data["books"][0]["work_reviews_count"]    
        average = data["books"][0]["average_rating"]
        return jsonify({
                    "title": book.title,
                    "author": book.author,
                    "year": book.year,
                    "isbn": book.isbn,
                    "review_count": count,
                    "average_score": average
            })