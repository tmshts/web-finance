import os

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.route("/")
@login_required #user must be logged in in oder to see the index.page
def index():
    """Show portfolio of stocks"""

    rows = db.execute("SELECT name, symbol, SUM(shares) as number_of_shares FROM purchase WHERE user_id=:id GROUP BY symbol HAVING number_of_shares", id=session["user_id"])

    portfolio = [] # create dictionary
    grand_total = 0
    for row in rows:
        stock = lookup(row["symbol"]) # look up fo each symbol which is in the purchase group
        # append to the dictionary portfolio
        portfolio.append({
            "name": row["name"],
            "symbol": stock["symbol"],
            "shares": row["number_of_shares"],
            "price": stock["price"],
            "total_value": stock["price"] * row["number_of_shares"]
            })
        grand_total = grand_total + stock["price"] * row["number_of_shares"]

    # cash story
    row_cash = db.execute("SELECT cash FROM users WHERE id=:id", id=session["user_id"])
    cash = current_cash = row_cash[0]["cash"]
    current_cash = round(cash, 2)

    grand_total = round(grand_total + current_cash, 2)

    return render_template("index.html", portfolio=portfolio, current_cash = current_cash, grand_total=grand_total)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "GET":
        return render_template("buy.html")
    else: # method POST
        # symbol
        # convert symbol to uppercase
        symbol = request.form.get("symbol").upper()
        if not symbol:
            return apology("You must provide a correct stock´s symbol.", 403)

        # check whether the typed symbol exists
        dic = lookup(symbol)
        if dic is None:
            return apology("Stock you looked up did not exist.", 403)

        # shares
        shares = request.form.get("shares")
        if not shares:
            return apology("You must provide how many share you wish to buy.", 403)

        # user has to input digit
        if not request.form.get("shares").isdigit():
            return apology("Input has to be a positive integer", 403)

        shares_int = int(shares)
        #if shares_int <= 0:
        #    return apology("Input has to be a positive integer", 403)


        # check whether user have cash to buy the stock
        row = db.execute("SELECT cash FROM users WHERE id=:id", id=session["user_id"])
        current_cash = row[0]["cash"]

        dic = lookup(symbol)
        current_price=dic["price"]

        investment=current_price * shares_int

        if current_cash < investment:
            return apology("You can not afford to buy this amount of shares.", 403)

        updated_cash = current_cash - investment

        db.execute("UPDATE users SET cash=:updated_cash WHERE id=:id", updated_cash=updated_cash, id=session["user_id"])

        db.execute("INSERT INTO purchase (user_id, name, symbol, shares, price) VALUES(:user_id, :name, :symbol, :shares, :price)", user_id=session["user_id"], name=dic["name"], symbol=dic["symbol"], shares=shares_int, price=dic["price"])

        flash("The stock has been bought.")

        return redirect("/")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""

    rows = db.execute("SELECT name, symbol, shares, price, time_of_transaction FROM purchase WHERE user_id=:id", id=session["user_id"])

    #portfolio = []
    for row in rows:
            {"name": row["name"],
            "symbol": row["symbol"],
            "shares": row["shares"],
            "price": row["price"],
            "time_of_transaction": row["time_of_transaction"]}

        # same but kind of redundancy
    #    portfolio.append({
     #       "name": row["name"],
      #      "symbol": row["symbol"],
       #     "shares": row["shares"],
        #    "price": row["price"],
         #   "time_of_transaction": row["time_of_transaction"]
          #  })

    return render_template("history.html", rows=rows)


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
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        # important!
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

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
    if request.method == "GET":
        return render_template("quote.html")
    else: # post method
        symbol = request.form.get("symbol").upper()
        if not symbol:
            return apology("You must provide a correct stock´s symbol.", 403)

        #dic = []
        dic = lookup(symbol)
        if dic is None:
            return apology("Stock you looked up did not exist.", 403)

        return render_template("quoted.html", namelook=dic["name"], pricelook=dic["price"], symbollook=dic["symbol"])


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "GET":
        return render_template("register.html")
    else: # request.method == "POST"
        username = request.form.get("username")
        if not username:
            return apology("You must provide an username.", 403)
        username_check = db.execute("SELECT username FROM users WHERE username = :username", username=request.form.get("username"))
        if username is username_check:
            return apology("The username is already taken. Please provide another username.", 403)
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")
        if not password:
            return apology("You must provide a password.", 403)
            #return render_template("apology.html", message="You must provide a password.")
        if not confirmation:
            return apology("You must confirm your password.", 403)
            #return render_template("apology.html", message="You must confirm your password.")
        if password != confirmation:
            return apology("The password does not match with the confirmation of password.", 403)
            #return render_template("apology.html", message="The password does not match with the confirmation of password.")
        hash = generate_password_hash (request.form.get("password"))
                #(
                #password,
                #method: str=str,
                #salt_length: int = 8)

        # insert registration data into table
        db.execute("INSERT INTO users (username, hash) VALUES (:username, :hash)", username=username, hash=hash)

        return redirect("/")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method == "GET":
        # dropdown menu for my portfolio´s symbols
        rows = db.execute("SELECT symbol FROM purchase WHERE user_id=:id GROUP BY symbol", id=session["user_id"])

        # add my every symbol to my symbols dictionary
        symbols = []
        for row in rows:
            symbols.append(row["symbol"])

        return render_template("sell.html", symbols=symbols)
    else: # method POST

        # symbol
        symbol = request.form.get("symbol")
        if not symbol:
            return apology("You must provide a correct stock´s symbol.", 403)

        # not necessary because of dropdown menu
        #dic = lookup(symbol)
        #if dic is None:
        #    return apology("Stock you looked up did not exist.", 403)

        #shares
        shares = request.form.get("shares")

        if not shares:
            return apology("You must provide how many shares you wish to sell.", 403)

        if not request.form.get("shares").isdigit():
            return apology("Input has to be a positive integer", 403)

        shares_int = int(shares)

        # check whether I can sell more shares than I have
        rows = db.execute("SELECT symbol, SUM(shares) as number_of_shares FROM purchase WHERE user_id=:id GROUP BY symbol", id=session["user_id"])
        for row in rows:
            if row["symbol"] == symbol:
                if shares_int > row["number_of_shares"]:
                    return apology("You do not have so many shares.", 403)

        # change current cash
        row = db.execute("SELECT cash FROM users WHERE id=:id", id=session["user_id"])
        current_cash = row[0]["cash"]

        dic = lookup(symbol)
        current_price=dic["price"]

        investment=current_price * shares_int

        updated_cash = current_cash + investment

        db.execute("UPDATE users SET cash=:updated_cash WHERE id=:id", updated_cash=updated_cash, id=session["user_id"])

        db.execute("INSERT INTO purchase (user_id, name, symbol, shares, price) VALUES(:user_id, :name, :symbol, :shares, :price)", user_id=session["user_id"], name=dic["name"], symbol=dic["symbol"], shares= - 1 * shares_int, price=dic["price"])

        flash("The stock has been sold.")

        return redirect("/")


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
