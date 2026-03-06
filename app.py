from datetime import datetime
from decimal import Decimal
from functools import wraps
import uuid

from flask import Flask, flash, redirect, render_template, request, session, url_for
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

from models import Account, AuditLog, BankTransaction, Customer, UserAuth, db


app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///bank.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = "change-this-in-production"

db.init_app(app)


# Enable FK checks on SQLite connections.
from sqlalchemy import event
from sqlalchemy.engine import Engine


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def log_event(event_type, customer_id=None, data=None):
    entry = AuditLog(
        customer_id=customer_id,
        event_type=event_type,
        ip_address=request.remote_addr,
        user_agent=request.headers.get("User-Agent", "")[:255],
        event_data=data,
    )
    db.session.add(entry)


def login_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if not session.get("customer_id"):
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)

    return wrapped


def current_customer():
    cid = session.get("customer_id")
    if not cid:
        return None
    return Customer.query.get(cid)


def make_account_number():
    # Simple deterministic-length account number for demo use.
    return datetime.utcnow().strftime("%y%m%d%H%M%S") + str(uuid.uuid4().int)[:4]


def new_reference(prefix="TX"):
    return f"{prefix}-{uuid.uuid4().hex[:16].upper()}"


@app.route("/init-db")
def init_db():
    reset = request.args.get("reset", "0") == "1"
    if reset:
        db.drop_all()
    db.create_all()
    return "Database initialized. Use ?reset=1 to recreate tables."


@app.route("/")
def index():
    if not session.get("customer_id"):
        return redirect(url_for("login"))
    return redirect(url_for("dashboard"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        full_name = request.form["full_name"].strip()
        email = request.form["email"].strip().lower()
        username = request.form["username"].strip()
        password = request.form["password"]

        customer = Customer(
            full_name=full_name,
            email=email,
            phone=request.form.get("phone", "").strip() or None,
            address_line=request.form.get("address_line", "").strip() or None,
            city=request.form.get("city", "").strip() or None,
            state=request.form.get("state", "").strip() or None,
            postal_code=request.form.get("postal_code", "").strip() or None,
            country=request.form.get("country", "").strip() or None,
        )
        db.session.add(customer)
        db.session.flush()

        auth = UserAuth(
            customer_id=customer.customer_id,
            username=username,
            password_hash=generate_password_hash(password),
            password_updated_at=datetime.utcnow(),
        )
        db.session.add(auth)

        primary_account = Account(
            customer_id=customer.customer_id,
            account_number=make_account_number(),
            account_type="savings",
            currency_code="USD",
            balance=Decimal("0.00"),
            status="active",
        )
        db.session.add(primary_account)

        try:
            log_event("register_success", customer_id=customer.customer_id, data=f"username={username}")
            db.session.commit()
            flash("Registration successful. Please log in.", "success")
            return redirect(url_for("login"))
        except IntegrityError:
            db.session.rollback()
            flash("Registration failed. Email/username might already exist.", "error")

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]

        auth = UserAuth.query.filter_by(username=username).first()
        if not auth or not auth.customer or not auth.customer.is_active:
            flash("Invalid username or password.", "error")
            return render_template("login.html")

        if not check_password_hash(auth.password_hash, password):
            auth.failed_login_count += 1
            log_event("login_failed", customer_id=auth.customer_id, data=f"username={username}")
            db.session.commit()
            flash("Invalid username or password.", "error")
            return render_template("login.html")

        auth.failed_login_count = 0
        auth.last_login_at = datetime.utcnow()
        session["customer_id"] = auth.customer_id
        log_event("login_success", customer_id=auth.customer_id)
        db.session.commit()
        return redirect(url_for("dashboard"))

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    cid = session.get("customer_id")
    session.clear()
    log_event("logout", customer_id=cid)
    db.session.commit()
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    customer = current_customer()
    accounts = Account.query.filter_by(customer_id=customer.customer_id).order_by(Account.account_id).all()
    total_balance = sum((Decimal(a.balance) for a in accounts), Decimal("0.00"))
    return render_template("dashboard.html", customer=customer, accounts=accounts, total_balance=total_balance)


@app.route("/accounts", methods=["GET", "POST"])
@login_required
def accounts():
    customer = current_customer()

    if request.method == "POST":
        account_type = request.form["account_type"]
        new_account = Account(
            customer_id=customer.customer_id,
            account_number=make_account_number(),
            account_type=account_type,
            currency_code="USD",
            balance=Decimal("0.00"),
            status="active",
        )
        db.session.add(new_account)
        db.session.commit()
        flash("New account created.", "success")
        return redirect(url_for("accounts"))

    account_list = Account.query.filter_by(customer_id=customer.customer_id).order_by(Account.account_id).all()
    return render_template("accounts.html", accounts=account_list)


@app.route("/balance")
@login_required
def balance():
    customer = current_customer()
    account_list = Account.query.filter_by(customer_id=customer.customer_id).order_by(Account.account_id).all()
    return render_template("balance.html", accounts=account_list)


@app.route("/transactions", methods=["GET", "POST"])
@login_required
def transactions():
    customer = current_customer()
    my_accounts = Account.query.filter_by(customer_id=customer.customer_id, status="active").order_by(Account.account_id).all()

    if request.method == "POST":
        account_id = int(request.form["account_id"])
        tx_type = request.form["tx_type"]
        amount = Decimal(request.form["amount"])

        account = Account.query.filter_by(account_id=account_id, customer_id=customer.customer_id).first()
        if not account:
            flash("Invalid account selected.", "error")
            return redirect(url_for("transactions"))

        if amount <= 0:
            flash("Amount must be positive.", "error")
            return redirect(url_for("transactions"))

        if tx_type == "withdrawal" and Decimal(account.balance) < amount:
            flash("Insufficient balance.", "error")
            return redirect(url_for("transactions"))

        if tx_type == "deposit":
            account.balance = Decimal(account.balance) + amount
        else:
            account.balance = Decimal(account.balance) - amount

        tx = BankTransaction(
            account_id=account.account_id,
            tx_type=tx_type,
            amount=amount,
            reference_no=new_reference("CASH"),
            description=f"{tx_type} via web",
            status="posted",
            posted_at=datetime.utcnow(),
        )
        db.session.add(tx)
        log_event("cash_transaction", customer_id=customer.customer_id, data=f"{tx_type}:{amount}")
        db.session.commit()
        flash("Transaction completed.", "success")
        return redirect(url_for("transactions"))

    account_ids = [a.account_id for a in my_accounts]
    history = (
        BankTransaction.query.filter(BankTransaction.account_id.in_(account_ids))
        .order_by(BankTransaction.created_at.desc())
        .limit(100)
        .all()
    ) if account_ids else []

    return render_template("transactions.html", accounts=my_accounts, transactions=history)


@app.route("/transfer", methods=["GET", "POST"])
@login_required
def transfer():
    customer = current_customer()
    my_accounts = Account.query.filter_by(customer_id=customer.customer_id, status="active").order_by(Account.account_id).all()

    if request.method == "POST":
        from_account_id = int(request.form["from_account_id"])
        destination_account_number = request.form["destination_account_number"].strip()
        amount = Decimal(request.form["amount"])

        if amount <= 0:
            flash("Amount must be positive.", "error")
            return redirect(url_for("transfer"))

        source = Account.query.filter_by(account_id=from_account_id, customer_id=customer.customer_id, status="active").first()
        if not source:
            flash("Invalid source account.", "error")
            return redirect(url_for("transfer"))

        if Decimal(source.balance) < amount:
            flash("Insufficient balance.", "error")
            return redirect(url_for("transfer"))

        if destination_account_number == source.account_number:
            flash("Source and destination accounts cannot be the same.", "error")
            return redirect(url_for("transfer"))

        destination = Account.query.filter_by(account_number=destination_account_number, status="active").first()
        ref = new_reference("TRF")

        source.balance = Decimal(source.balance) - amount
        out_tx = BankTransaction(
            account_id=source.account_id,
            related_account_id=destination.account_id if destination else None,
            tx_type="transfer_out",
            amount=amount,
            reference_no=ref + "-O",
            description=f"Transfer to account {destination_account_number}",
            status="posted",
            posted_at=datetime.utcnow(),
        )
        db.session.add(out_tx)

        if destination:
            destination.balance = Decimal(destination.balance) + amount
            in_tx = BankTransaction(
                account_id=destination.account_id,
                related_account_id=source.account_id,
                tx_type="transfer_in",
                amount=amount,
                reference_no=ref + "-I",
                description=f"Transfer from account {source.account_number}",
                status="posted",
                posted_at=datetime.utcnow(),
            )
            db.session.add(in_tx)

        log_event(
            "transfer",
            customer_id=customer.customer_id,
            data=f"from={source.account_number},to={destination_account_number},amount={amount}",
        )
        db.session.commit()

        if destination:
            flash("Transfer sent and receiver account credited.", "success")
        else:
            flash("Transfer recorded as external transfer.", "success")
        return redirect(url_for("transfer"))

    return render_template("transfer.html", accounts=my_accounts)


@app.route("/history")
@login_required
def history():
    customer = current_customer()
    my_account_ids = [a.account_id for a in Account.query.filter_by(customer_id=customer.customer_id).all()]
    txs = (
        BankTransaction.query.filter(BankTransaction.account_id.in_(my_account_ids))
        .order_by(BankTransaction.created_at.desc())
        .all()
    ) if my_account_ids else []
    return render_template("history.html", transactions=txs)


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
