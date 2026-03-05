from datetime import datetime

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import CheckConstraint


db = SQLAlchemy()


class Customer(db.Model):
    __tablename__ = "customer"

    customer_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    full_name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), nullable=False, unique=True)
    phone = db.Column(db.String(50), nullable=True)
    address_line = db.Column(db.String(255), nullable=True)
    city = db.Column(db.String(100), nullable=True)
    state = db.Column(db.String(100), nullable=True)
    postal_code = db.Column(db.String(20), nullable=True)
    country = db.Column(db.String(100), nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    auth = db.relationship("UserAuth", backref="customer", uselist=False, cascade="all, delete-orphan")
    accounts = db.relationship("Account", backref="customer", lazy=True, cascade="all, delete-orphan")
    beneficiaries = db.relationship("Beneficiary", backref="customer", lazy=True, cascade="all, delete-orphan")


class UserAuth(db.Model):
    __tablename__ = "user_auth"

    auth_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customer.customer_id"), nullable=False, unique=True)
    username = db.Column(db.String(50), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    password_updated_at = db.Column(db.DateTime, nullable=True)
    mfa_enabled = db.Column(db.Boolean, nullable=False, default=False)
    mfa_secret = db.Column(db.String(255), nullable=True)
    last_login_at = db.Column(db.DateTime, nullable=True)
    failed_login_count = db.Column(db.Integer, nullable=False, default=0)


class Account(db.Model):
    __tablename__ = "account"
    __table_args__ = (
        CheckConstraint("account_type IN ('savings', 'current')", name="ck_account_type"),
        CheckConstraint("status IN ('active', 'frozen', 'closed')", name="ck_account_status"),
        CheckConstraint("balance >= 0", name="ck_account_balance_non_negative"),
    )

    account_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customer.customer_id"), nullable=False)
    account_number = db.Column(db.String(30), nullable=False, unique=True)
    account_type = db.Column(db.String(20), nullable=False)
    currency_code = db.Column(db.String(3), nullable=False, default="USD")
    balance = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    status = db.Column(db.String(20), nullable=False, default="active")
    opened_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    closed_at = db.Column(db.DateTime, nullable=True)


class Beneficiary(db.Model):
    __tablename__ = "beneficiary"

    beneficiary_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customer.customer_id"), nullable=False)
    nickname = db.Column(db.String(100), nullable=True)
    beneficiary_name = db.Column(db.String(255), nullable=False)
    beneficiary_account_no = db.Column(db.String(50), nullable=False)
    beneficiary_bank = db.Column(db.String(255), nullable=False)
    ifsc_swift_code = db.Column(db.String(50), nullable=True)
    is_verified = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class BankTransaction(db.Model):
    __tablename__ = "bank_transaction"
    __table_args__ = (
        CheckConstraint(
            "tx_type IN ('deposit', 'withdrawal', 'transfer_out', 'transfer_in', 'bill_payment')",
            name="ck_tx_type",
        ),
        CheckConstraint("status IN ('pending', 'posted', 'failed', 'reversed')", name="ck_tx_status"),
        CheckConstraint("amount > 0", name="ck_tx_amount_positive"),
    )

    transaction_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    account_id = db.Column(db.Integer, db.ForeignKey("account.account_id"), nullable=False)
    related_account_id = db.Column(db.Integer, db.ForeignKey("account.account_id"), nullable=True)
    tx_type = db.Column(db.String(20), nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    reference_no = db.Column(db.String(64), nullable=False, unique=True)
    description = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(20), nullable=False, default="posted")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    posted_at = db.Column(db.DateTime, nullable=True)


class AuditLog(db.Model):
    __tablename__ = "audit_log"

    audit_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customer.customer_id"), nullable=True)
    event_type = db.Column(db.String(100), nullable=False)
    ip_address = db.Column(db.String(64), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    event_data = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
