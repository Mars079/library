import csv
import os
import requests

from flask import Flask, session, render_template, request, redirect, url_for, jsonify
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

app = Flask(__name__)


# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"

Session(app)

# Set up database
engine = create_engine("postgres://eihlqaagoqafiz:b88014c70e4195f1e91ef436da25435bf45d4986ea49728d363a90bc64931d12@ec2-107-22-228-141.compute-1.amazonaws.com:5432/d8u7rj319n10u6")
db = scoped_session(sessionmaker(bind=engine))

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/signup', methods=['GET', 'POST'])
def signUp():
    if request.method == 'GET':
        return render_template('signup.html')
    
    if request.method == 'POST':
        username = str(request.form.get('username'))
        password = str(request.form.get('password'))
        warning = ["Password or Username is too short", "Username already exists"]
        verifyUserInDb = db.execute("SELECT * FROM users WHERE username = :username", {'username': username}).fetchone()
        if not verifyUserInDb:
            #Verify if user's not already in database and create account.
            if len(username) >= 4 and len(password) >= 6:
                db.execute('INSERT INTO users (username, password) VALUES (:username, :password)', 
                          {'username': username, 'password': password})
                db.commit()
                session['user'] = username
                return redirect(url_for('home'))
            else:
                return render_template('signup.html', warning=warning[0])
        else:
            #handle when user already exists.
            return render_template('signup.html', warning=warning[1])
                    
@app.route('/signin', methods=['GET', 'POST'])
def signIn():
    if request.method == 'GET':
        return render_template('signin.html')
    
    if request.method == 'POST':
        #Gets the username and password from the inputs.
        username = request.form.get('username')
        password = request.form.get('password')
        warning = ["User does not exists", "Wrong password"]
        verifyUserInDb = db.execute('SELECT * FROM users WHERE username = :username', {'username': username}).fetchmany(2)
        #Verify if user exists in Database and
        #logs if yes.
        if not verifyUserInDb:
            return render_template('signin.html', warning=warning[0])
        else:
            #checks if provided password is equal to database password
            for db_username, db_password in verifyUserInDb:
                if password != db_password:
                    return render_template('signin.html', warning=warning[1])
                else:
                    session['user'] = db_username
                    return redirect(url_for('home'))

@app.route('/logout')
def logout():
    #logout the user
    if 'user' in session:
        session.pop('user', None)
        return redirect(url_for('index'))
    else:
        return 'Not logged'

@app.route('/home')
def home():
        if 'user' in session:
            return render_template('home.html')
        else:
            return redirect(url_for('signIn'))


@app.route('/home/books')
def bookSearch():
    if 'user' in session:
        searchBook = request.args.get('search')
        bookList = db.execute("SELECT isbn, title, author FROM books WHERE isbn iLIKE :search OR title iLIKE :search OR author iLIKE :search", {'search':"%"+searchBook+"%"}).fetchall()
        if not bookList:
            error = "No books, isbns or authors matching this credentials"
            return render_template('bookList.html', error=error)
        else:
            return render_template('bookList.html', bookList=bookList, search=searchBook)
    else:
        return redirect(url_for('signIn'))

@app.route('/book/<isbn>', methods=['GET', 'POST'])
def book(isbn):
    
    book = db.execute('SELECT * FROM books WHERE isbn = :isbn', {'isbn': isbn})
    showReviews = db.execute('SELECT * FROM reviews WHERE isbn = :isbn', {'isbn': isbn}).fetchall()

    if request.method == 'GET':
        res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "t1o4qDhiBkAlI5BjFctQA", "isbns": isbn})
        r = res.json()
        reviewsCounts = r["books"][0]["reviews_count"]
        averageScore = r["books"][0]["average_rating"]
        return render_template('bookDetails.html', book=book, showReviews=showReviews, isbn=isbn, reviewsCounts=reviewsCounts, averageScore=averageScore)
    
    if request.method == 'POST':
        if 'user' in session:
            username = session['user']
            verifyUserInDb = db.execute('SELECT username FROM reviews WHERE username = :username AND isbn = :isbn', {'username': username, 'isbn': isbn}).fetchone()
            warning = ["Review succesfully uploaded", "Avaliation must have at least 4 characters", "You already sent an analysis"]
            if not verifyUserInDb:
                avaliation = str(request.form.get('review'))
                rating = int(request.form.get('book_rating'))
                if len(avaliation) < 500 and len(avaliation) >= 4:
                    db.execute("INSERT INTO reviews (isbn, username, avaliation, rating) VALUES (:isbn, :username, :avaliation, :rating)", {'isbn': isbn, 'username': username, 'avaliation': avaliation, 'rating': rating})
                    db.commit()
                    return render_template('bookDetails.html', isbn=isbn, showReviews=showReviews, book=book, warning=warning[0])
                else:
                    return render_template('bookDetails.html', isbn=isbn, showReviews=showReviews, book=book, warning=warning[1])
            else:
                return render_template('bookDetails.html', isbn=isbn, showReviews=showReviews, book=book, warning=warning[2])
        else:
            return redirect(url_for('signIn'))

@app.route('/api/<isbn>')
def jsonBook(isbn):
    book = db.execute('SELECT * FROM books WHERE isbn = :isbn', {'isbn': isbn})
    for isbn, title, author, year in book:
        res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "t1o4qDhiBkAlI5BjFctQA", "isbns": isbn})
        r = res.json()
        reviewsCounts = r["books"][0]["reviews_count"]
        averageScore = r["books"][0]["average_rating"]
        jsonBook = {'isbn': isbn, 'title': title, 'author': author, 'year': year, 'review_count': reviewsCounts, 'average_rating': averageScore}
        return jsonify(jsonBook)

