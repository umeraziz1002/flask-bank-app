PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS customer (
  customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
  full_name TEXT NOT NULL,
  email TEXT NOT NULL UNIQUE,
  phone TEXT,
  address_line TEXT,
  city TEXT,
  state TEXT,
  postal_code TEXT,
  country TEXT,
  is_active INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_auth (
  auth_id INTEGER PRIMARY KEY AUTOINCREMENT,
  customer_id INTEGER NOT NULL UNIQUE,
  username TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  password_updated_at TEXT,
  mfa_enabled INTEGER NOT NULL DEFAULT 0,
  mfa_secret TEXT,
  last_login_at TEXT,
  failed_login_count INTEGER NOT NULL DEFAULT 0,
  FOREIGN KEY (customer_id) REFERENCES customer(customer_id)
);

CREATE TABLE IF NOT EXISTS account (
  account_id INTEGER PRIMARY KEY AUTOINCREMENT,
  customer_id INTEGER NOT NULL,
  account_number TEXT NOT NULL UNIQUE,
  account_type TEXT NOT NULL CHECK(account_type IN ('savings','current')),
  currency_code TEXT NOT NULL DEFAULT 'USD',
  balance NUMERIC NOT NULL DEFAULT 0.00,
  status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active','frozen','closed')),
  opened_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  closed_at TEXT,
  FOREIGN KEY (customer_id) REFERENCES customer(customer_id)
);

CREATE TABLE IF NOT EXISTS bank_transaction (
  transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
  account_id INTEGER NOT NULL,
  related_account_id INTEGER,
  tx_type TEXT NOT NULL CHECK(tx_type IN ('deposit','withdrawal','transfer_out','transfer_in','bill_payment')),
  amount NUMERIC NOT NULL CHECK(amount > 0),
  reference_no TEXT NOT NULL UNIQUE,
  description TEXT,
  status TEXT NOT NULL DEFAULT 'posted' CHECK(status IN ('pending','posted','failed','reversed')),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  posted_at TEXT,
  FOREIGN KEY (account_id) REFERENCES account(account_id),
  FOREIGN KEY (related_account_id) REFERENCES account(account_id)
);

CREATE TABLE IF NOT EXISTS audit_log (
  audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
  customer_id INTEGER,
  event_type TEXT NOT NULL,
  ip_address TEXT,
  user_agent TEXT,
  event_data TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (customer_id) REFERENCES customer(customer_id)
);

CREATE INDEX IF NOT EXISTS idx_account_customer ON account(customer_id);
CREATE INDEX IF NOT EXISTS idx_tx_account_time ON bank_transaction(account_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_customer_time ON audit_log(customer_id, created_at DESC);
