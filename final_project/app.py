from flask import Flask, render_template, redirect, url_for, request, session, flash, jsonify
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash
from models import db, User, Portfolio, Investment, Friendship
from functools import wraps
import yfinance as yf
import logging

# Set up logging for yfinance
logging.getLogger('yfinance').setLevel(logging.DEBUG)

app = Flask(__name__)

app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///finance.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

def apology(message, code=400):
    def escape(s):
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
                         ("%", "~p"), ("#", "~h"), ("/", "~s"), ('"', "''")]:
            s = s.replace(old, new)
        return s
    return render_template("apology.html", top=code, bottom=escape(message)), code

def get_stock_price(symbol):
    if not symbol:
        return None

    try:
        # Ensure the symbol is uppercase and stripped of whitespace
        symbol = symbol.strip().upper()

        # Create a Ticker object
        stock = yf.Ticker(symbol)

        # Get stock info
        info = stock.info

        # Check if we got valid data
        if 'regularMarketPrice' in info and info['regularMarketPrice'] is not None:
            return info['regularMarketPrice']

        # Alternative method if regular market price is not available
        hist = stock.history(period='1d')
        if not hist.empty:
            return hist['Close'].iloc[-1]

        return None
    except Exception as e:
        print(f"Error fetching stock price for {symbol}: {str(e)}")
        return None

@app.route("/")
@login_required
def index():
    return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        if not username or not password or not confirmation:
            return apology("must provide username and password")
        if password != confirmation:
            return apology("passwords do not match")

        user = User.query.filter_by(username=username).first()
        if user:
            return apology("username already exists")

        hashed_password = generate_password_hash(password)
        new_user = User(username=username, hash=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        session["user_id"] = new_user.id
        return redirect(url_for("index"))

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if not username or not password:
            return apology("must provide username and password")

        user = User.query.filter_by(username=username).first()

        if not user or not check_password_hash(user.hash, password):
            return apology("invalid username or password")

        session["user_id"] = user.id
        return redirect(url_for("index"))

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

@app.route("/create_portfolio", methods=["GET", "POST"])
@login_required
def create_portfolio():
    if request.method == "POST":
        name = request.form.get("name")

        if not name:
            return apology("Portfolio name required", 400)

        new_portfolio = Portfolio(user_id=session["user_id"], name=name)
        db.session.add(new_portfolio)
        db.session.commit()

        return redirect(url_for("index"))

    return render_template("create_portfolio.html")

@app.route("/add_investment/<int:portfolio_id>", methods=["GET", "POST"])
@login_required
def add_investment(portfolio_id):
    if request.method == "POST":
        symbol = request.form.get("symbol")
        quantity = request.form.get("quantity")

        if not symbol or not quantity:
            return apology("Symbol and quantity required", 400)

        try:
            quantity = int(quantity)
            if quantity <= 0:
                return apology("Quantity must be positive", 400)
        except ValueError:
            return apology("Invalid quantity", 400)

        # Clean up the symbol
        symbol = symbol.strip().upper()

        # Verify if the symbol is valid
        price = get_stock_price(symbol)
        if price is None:
            # Add debugging information
            print(f"Failed to get price for symbol: {symbol}")
            return apology(f"Unable to verify stock symbol: {symbol}", 400)

        try:
            new_investment = Investment(
                portfolio_id=portfolio_id,
                symbol=symbol,
                quantity=quantity,
                user_id=session["user_id"]
            )
            db.session.add(new_investment)
            db.session.commit()
            flash(f"Successfully added {quantity} shares of {symbol}", "success")
            return redirect(url_for("view_portfolio", portfolio_id=portfolio_id))
        except Exception as e:
            db.session.rollback()
            print(f"Database error: {str(e)}")
            return apology("Failed to add investment", 500)

    return render_template("add_investment.html", portfolio_id=portfolio_id)

@app.route("/view_portfolio/<int:portfolio_id>")
@login_required
def view_portfolio(portfolio_id):
    portfolio = Portfolio.query.get(portfolio_id)

    if portfolio is None:
        return apology("Portfolio not found", 404)

    if portfolio.user_id != session["user_id"] and not is_friend(session["user_id"], portfolio.user_id):
        return apology("You don't have access to this portfolio", 403)

    investments = Investment.query.filter_by(portfolio_id=portfolio_id).all()

    # Fetch current prices for each investment
    for investment in investments:
        investment.current_price = get_stock_price(investment.symbol)
        if investment.current_price:
            investment.total_value = investment.current_price * investment.quantity
        else:
            investment.total_value = None

    return render_template("view_portfolio.html", portfolio=portfolio, investments=investments)

@app.route("/get_stock_price/<symbol>")
@login_required
def get_stock_price_route(symbol):
    price = get_stock_price(symbol)
    if price:
        return jsonify({"price": price})
    else:
        return jsonify({"error": "Unable to fetch stock price"}), 400

@app.route("/get_portfolio_value/<int:portfolio_id>")
@login_required
def get_portfolio_value(portfolio_id):
    portfolio = Portfolio.query.get(portfolio_id)
    if portfolio is None:
        return jsonify({"error": "Portfolio not found"}), 404

    if portfolio.user_id != session["user_id"] and not is_friend(session["user_id"], portfolio.user_id):
        return jsonify({"error": "You don't have access to this portfolio"}), 403

    investments = Investment.query.filter_by(portfolio_id=portfolio_id).all()
    total_value = 0

    for inv in investments:
        price = get_stock_price(inv.symbol)
        if price:
            total_value += price * inv.quantity

    return jsonify({"total_value": total_value})

def is_friend(user_id, friend_id):
    return Friendship.query.filter(
        (Friendship.user_id == user_id) & (Friendship.friend_id == friend_id)
    ).count() > 0

@app.route("/add_friend", methods=["GET", "POST"])
@login_required
def add_friend():
    if request.method == "POST":
        friend_username = request.form.get("friend_username")
        print(f"Friend username entered: {friend_username}")  # Debugging

        friend = User.query.filter_by(username=friend_username).first()
        if friend is None:
            print("User not found in database.")  # Debugging
            return apology("User not found", 404)

        existing_friendship = Friendship.query.filter_by(user_id=session["user_id"], friend_id=friend.id).first()
        if existing_friendship:
            return apology("Friendship already exists", 400)

        new_friendship = Friendship(user_id=session["user_id"], friend_id=friend.id)
        db.session.add(new_friendship)
        db.session.commit()

        return redirect(url_for("view_friends"))

    return render_template("add_friend.html")

@app.route("/view_friends")
@login_required
def view_friends():
    user_id = session["user_id"]
    friendships = Friendship.query.filter(
        (Friendship.user_id == user_id) | (Friendship.friend_id == user_id)
    ).all()

    friends = set()
    for friendship in friendships:
        if friendship.user_id == user_id:
            friends.add(friendship.friend)
        else:
            friends.add(friendship.user)

    return render_template("view_friends.html", friends=friends)

@app.route('/view_friend_portfolios/<int:friend_id>')
@login_required
def view_friend_portfolios(friend_id):
    friend = User.query.get(friend_id)
    if friend is None:
        flash('Friend not found.', 'danger')
        return redirect(url_for('view_friends'))

    portfolios = Portfolio.query.filter_by(user_id=friend_id).all()

    for portfolio in portfolios:
        investments = Investment.query.filter_by(portfolio_id=portfolio.id).all()
        total_value = 0
        for inv in investments:
            price = get_stock_price(inv.symbol)
            if price:
                total_value += price * inv.quantity
        portfolio.total_value = total_value

    return render_template('view_friend_portfolios.html', friend=friend, portfolios=portfolios)

@app.route("/view_friend_portfolio/<int:friend_id>/<int:portfolio_id>")
@login_required
def view_friend_portfolio(friend_id, portfolio_id):
    friend = User.query.get_or_404(friend_id)
    portfolio = Portfolio.query.filter_by(id=portfolio_id, user_id=friend_id).first_or_404()
    investments = Investment.query.filter_by(portfolio_id=portfolio_id).all()

    for investment in investments:
        investment.current_price = get_stock_price(investment.symbol)
        if investment.current_price:
            investment.total_value = investment.current_price * investment.quantity
        else:
            investment.total_value = None

    return render_template("view_friend_portfolio.html", friend=friend, portfolio=portfolio, investments=investments)

@app.route("/post_portfolio/<int:portfolio_id>", methods=["GET", "POST"])
@login_required
def post_portfolio(portfolio_id):
    if request.method == "POST":
        return redirect(url_for("view_portfolio", portfolio_id=portfolio_id))

    return render_template("post_portfolio.html", portfolio_id=portfolio_id)

@app.route("/my_portfolios")
@login_required
def my_portfolios():
    user = User.query.get(session["user_id"])
    portfolios = Portfolio.query.filter_by(user_id=user.id).all()

    for portfolio in portfolios:
        investments = Investment.query.filter_by(portfolio_id=portfolio.id).all()
        total_value = 0
        for inv in investments:
            price = get_stock_price(inv.symbol)
            if price:
                total_value += price * inv.quantity
        portfolio.total_value = total_value

    return render_template("my_portfolios.html", portfolios=portfolios)

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
