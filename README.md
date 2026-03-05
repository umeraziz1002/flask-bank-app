# flask-bank-app

Flask + SQLite online banking demo with:
- Registration and login
- Account creation and balance check
- Deposit / withdrawal
- Beneficiary management
- Money transfer
- Transaction history

## Setup (recommended: virtual environment)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Run

```powershell
python app.py
```

Initialize database:
- `http://127.0.0.1:5000/init-db`
- For schema reset: `http://127.0.0.1:5000/init-db?reset=1`

## Important
If you see errors like:
- `module 'sqlalchemy' has no attribute '__all__'`
- `Can't replace canonical symbol for '__firstlineno__' ...`

you are running with incompatible global packages. Activate `.venv` and reinstall dependencies there.
