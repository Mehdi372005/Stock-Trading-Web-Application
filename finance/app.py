import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from registration import create_registration_blueprint

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def portfolio():
    """Show portfolio of stocks"""

    flash("welcome to your portfolio")# show this message (52 layout.html)

    user_id = session["user_id"]

    rows= db.execute("SELECT * FROM users WHERE id=?",user_id)

    cash=rows[0]["cash"]


    transaction = db.execute(
        """
        SELECT symbol , SUM(shares) AS shares
        FROM transactions
        WHERE user_id=?
        GROUP BY symbol
        HAVING SUM(shares) >0
        """,
        user_id
    )

    total=0

    for stock in transaction :

        info = lookup(stock["symbol"])

        stock["price"] = info["price"]
        stock["total"] = stock["price"] * stock["shares"]
        total += stock["total"]

    total += cash


    return render_template ("portfolio.html",
                            transaction=transaction,
                            cash=cash,
                            total=total,)










@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    if request.method=="GET": # when the user select the icone Buy to open the buy interface
        flash("pick yout stock")
        return render_template("buy.html")
    else:
        user_id = session["user_id"]

        symbol = request.form.get("symbol")
        shares = request.form.get("shares")

        if not symbol :
            return apology ("must provide a symbol" , 400)

        if not shares or not shares.isdigit() or int(shares) <=0 :
            return apology ("invalid shares", 400)

        stock=lookup(symbol)

        if stock is None :
            return apology ("invalid symbol" , 400)

        info = lookup(symbol)
        price= info["price"]
        cost = price * int(shares)

        rows =db.execute(
            "SELECT cash FROM users WHERE id=?",
            user_id
        )

        if rows[0]["cash"] < cost :
            return apology("not enough cash", 400)

        db.execute(
            """
            INSERT INTO transactions (user_id, symbol, shares, price)
            VALUES (?, ?, ?, ?)
            """,
            user_id,
            info["symbol"],
            shares,
            price,
        )

        #after buyin stocks the cash must to be uptaded
        db.execute(
        "UPDATE users SET cash = cash - ? WHERE id = ?",
        cost,
        user_id
        )

        flash("bough with success !")
        return redirect("/")




@app.route("/history")
@login_required
def history():
    """Show history of transactions"""

    user_id = session["user_id"]

    rows = db.execute ("""SELECT symbol, price, shares FROM transactions
                        WHERE user_id= ?
                        ORDER BY timestamp DESC
                        """,
                        user_id
                        )

    for row in rows :
        row["total"] = row["shares"] * row["price"]

    return render_template("history.html",transactions = rows)




@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute(
            "SELECT * FROM users WHERE username = ?", request.form.get("username")
        )

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(
            rows[0]["hash"], request.form.get("password")
        ):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/") #execute the flask function

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "POST" :
        symbol = request.form.get("symbol")

        if not symbol :
            return apology ("must provide a symbol" , 400)

        stock=lookup(symbol)

        if stock is None :
            return apology ("invalid" , 400)

        return render_template("found_quote.html" , stock=stock)

    else :

        return render_template("quote.html")

# @app.route("/register", methods=["GET", "POST"])
# def register():
#     if request.method == "POST":

#         username=request.form.get("username")
#         password=request.form.get("password")
#         confirmation = request.form.get("confirmation")

#         name=db.execute(
#             "SELECT * FROM users WHERE username= ?",
#             username
#         )
#         if len(name)!=0 :
#             return apology("username already exists", 400)

#         if not username:
#             return apology("Must provide username", 400)


#         if not password:
#             return apology("Must provide password", 400)

#         if not confirmation:
#             return apology("Must confirm password", 400)

#         if password!=confirmation :
#             return apology("Password do not match",400)

#         password_safe = generate_password_hash(password) #function from Werkzeug that put the password in a crypted text to avoid stealing the data base and then the user's passwords

#         db.execute(
#             "INSERT INTO users (username, hash) VALUES(?, ?)",
#             username,
#             password_safe
#         )

#         return redirect("/login")
#     else:

#         return render_template("register.html")

def save_finance_user(username, password_hash): #this function will be used into the routes.py from registration folder

    name = db.execute(
        "SELECT * FROM users WHERE username = ?",
        username
    )

    if len(name) != 0:
        raise ValueError("Username already exists")

    db.execute(
        "INSERT INTO users (username, hash) VALUES (?, ?)",
        username,
        password_hash
    )

# create the blueprint
registration = create_registration_blueprint(save_finance_user)
app.register_blueprint(registration)

@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    user_id = session["user_id"]

    if request.method == "GET":

        transaction =db.execute(
            """
            SELECT symbol, SUM(shares) AS shares
            FROM transactions
            WHERE user_id = ?
            GROUP BY symbol
            HAVING SUM(shares) > 0
            """,
            user_id
        )

        for stock in transaction :
            info = lookup(stock["symbol"])
            stock["price"] = info["price"]
            stock["total"] = stock["price"] * stock["shares"]

        return render_template("sell.html" , transaction=transaction)
    else:

        symbol = request.form.get("symbol")
        shares = request.form.get("shares")

        if not shares or not shares.isdigit() or int(shares) <=0 :
            return apology ("invalid shares", 400)

        rows = db.execute(
            """
            SELECT SUM(shares) AS owned
            FROM transactions
            WHERE user_id = ? AND symbol = ?
            """,
            user_id,
            symbol
        )

        owned = rows[0]["owned"] or 0

        if int(shares) > owned:
            return apology("Not enough shares", 400)

        info = lookup(symbol)
        price = info["price"]

        shares = int(shares)
        total = price*shares


        db.execute(
        "INSERT INTO transactions (user_id, symbol, shares, price) VALUES (?, ?, ?, ?)",
        user_id,
        symbol,
        -shares,
        price
        )



        db.execute(
           "UPDATE users SET cash = cash + ? WHERE id= ?",
           total,
           user_id
        )

        return redirect ("/")












