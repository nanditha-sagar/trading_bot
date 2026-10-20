# Futures Trading Terminal

A Python-based trading terminal for paper trading and Binance Futures Testnet execution. The project combines a Flask backend, a MySQL-backed user system, and a browser-based trading UI inspired by Groww / Angel One styling.

## Overview

This application provides three main workflows:

1. Paper trading for simulated futures orders with no API keys required.
2. Binance Futures Testnet trading for authenticated users with `.env` credentials.
3. A user account system with registration, login, session-based access, and per-user trade history.

The frontend is served from the `frontend/` directory, while the backend logic lives in `server.py`, `db.py`, and the `bot/` package.

## Features

- User registration and login using a MySQL-backed `users` table
- Session-based authentication with Flask cookies
- Per-user paper trading accounts and isolated in-memory positions
- Paper order simulation with virtual balance, P&L tracking, and account reset
- Binance Futures Testnet order placement using `binance-futures-connector`
- Trade history persistence for authenticated testnet users
- Real-time price lookups and 24h market info via Binance endpoints
- Candlestick charting and market dashboard served in the browser
- CLI order entry for either paper or testnet mode

## Tech Stack

- Python 3.10+
- Flask
- MySQL Connector for Python
- `python-dotenv`
- Binance Futures connector library
- Vanilla HTML, CSS, and JavaScript frontend
- pytest for automated tests

## Repository Structure

```text
trading_bot/
├── bot/
│   ├── __init__.py
│   ├── client.py             # Binance Futures Testnet client
│   ├── logging_config.py     # Application logging setup
│   ├── orders.py             # Testnet order placement and persistence
│   ├── paper.py              # Per-user paper trading engine
│   └── validators.py         # Shared order validation
├── frontend/
│   ├── app.js                # Dashboard behavior and API integration
│   ├── index.html            # Trading dashboard
│   ├── login.html            # Login page
│   ├── register.html         # Registration page
│   └── style.css             # Shared styles
├── tests/
│   ├── conftest.py
│   ├── test_paper.py
│   ├── test_server.py
│   ├── test_testnet.py
│   └── test_validators.py
├── .env.example
├── .gitignore
├── cli.py                    # Command-line trading interface
├── db.py                     # MySQL connection, users, and trade history
├── README.md
├── requirements.txt
├── server.py                 # Flask app and REST API
└── test_db_save.py
```

> The repository also contains a local `venv/` directory. Virtual environments are normally created locally and should not be committed to source control.

## Requirements

Before running the app, make sure you have:

- Python 3.10 or newer
- MySQL server running locally or on a reachable host
- A Binance Futures Testnet account and API keys, only for testnet mode

## Environment Configuration

Copy `.env.example` to `.env` and update the values:

```dotenv
BINANCE_API_KEY=your_testnet_api_key_here
BINANCE_API_SECRET=your_testnet_api_secret_here

DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_NAME=order_bot

FLASK_SECRET_KEY=replace_with_a_random_secret

# Optional paper-trading balance
PAPER_STARTING_BALANCE=10000000.0
```

Notes:

- `BINANCE_API_KEY` and `BINANCE_API_SECRET` are required only for testnet order placement.
- Paper trading does not require Binance credentials.
- `FLASK_SECRET_KEY` is required by `server.py` for session management.
- The code reads `PAPER_STARTING_BALANCE` from the environment. If it is not set, the current code default is `10000000.0` USDT.

## Database Setup

Create the database if it does not already exist:

```sql
CREATE DATABASE order_bot;
```

When the Flask server starts, `server.py` calls `init_db()`. This creates or updates the following tables:

- `users` — usernames, email addresses, salted password hashes, and timestamps
- `trade_history` — accepted Binance Testnet orders associated with users

Paper orders are held in per-user in-memory engines and are not written to the MySQL trade-history table.

## Local Setup

1. Create and activate a virtual environment:

```bash
python -m venv venv
source venv/bin/activate
```

On Windows PowerShell:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Create `.env` from `.env.example` and configure MySQL and Flask settings.

4. Start the Flask server:

```bash
python server.py
```

5. Open the terminal in a browser:

```text
http://localhost:5000
```

## Web Application

The dashboard supports:

- Paper and Testnet mode switching
- User sign-in and registration
- Symbol selection and Binance market data
- Candlestick charts with `1m`, `5m`, `15m`, `1h`, and `4h` intervals
- BUY/LONG and SELL/SHORT orders
- MARKET and LIMIT orders
- Order confirmation before submission
- Open positions, order history, and trade history views
- Virtual balance, equity, realized P&L, and unrealized P&L
- Paper-account reset

The dashboard, login page, and registration page are served by Flask from `frontend/`.

## Running the CLI

The CLI supports both paper and testnet workflows.

Paper mode — no Binance API keys required:

```bash
python cli.py --paper --symbol BTCUSDT --side BUY --type MARKET --quantity 0.002
```

Paper LIMIT order:

```bash
python cli.py --paper --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.002 --price 85000
```

Testnet mode — requires Binance credentials in `.env`:

```bash
python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.002
```

Interactive mode:

```bash
python cli.py
```

The CLI validates the symbol, side, order type, quantity, and limit price, then asks for confirmation before placing the order.

## API Endpoints

### Public endpoints

- `GET /` — serves the trading dashboard
- `GET /login` — serves the login page
- `GET /register` — serves the registration page
- `GET /api/status` — reports service status, key availability, supported modes, and configured paper balance
- `GET /api/price?symbol=BTCUSDT` — returns a current or fallback price
- `GET /api/market-info?symbol=BTCUSDT` — returns 24-hour market statistics
- `GET /api/klines?symbol=BTCUSDT&interval=15m&limit=60` — returns candlestick data
- `POST /api/auth/register` — creates a user account
- `POST /api/auth/login` — authenticates a user
- `GET /api/auth/me` — returns the current session user
- `POST /api/logout` — clears the current session

### Authenticated endpoints

- `GET /api/orders?mode=paper` — returns the current user's paper orders
- `GET /api/orders?mode=testnet` — returns the current user's persisted testnet orders
- `GET /api/paper/account` — returns paper balance, equity, P&L, and positions
- `POST /api/paper/reset` — resets the current user's paper account
- `POST /api/order` — places a paper or testnet order

Example order request:

```json
{
  "mode": "paper",
  "symbol": "BTCUSDT",
  "side": "BUY",
  "order_type": "MARKET",
  "quantity": 0.002
}
```

For a LIMIT order, include a positive `price` value.

## Paper Trading Behavior

The paper engine in `bot/paper.py` simulates futures-style order execution without placing orders on Binance.

It:

- Maintains a virtual USDT balance
- Keeps separate paper state for each authenticated user
- Supports MARKET and LIMIT orders
- Fetches public Binance prices and falls back to cached prices when necessary
- Tracks LONG and SHORT positions
- Calculates realized and unrealized P&L
- Supports position increases, reductions, and flips
- Enforces a virtual balance and maximum notional check
- Stores the most recent paper orders in memory

Paper LIMIT orders are marked `FILLED` when the simulated limit price crosses the current market price; otherwise they remain `NEW`.

## Testnet Trading Behavior

In Testnet mode, the application:

1. Loads `BINANCE_API_KEY` and `BINANCE_API_SECRET` from `.env`.
2. Creates a Binance `UMFutures` client pointed at `https://testnet.binancefuture.com`.
3. Validates and submits the order through the Binance Futures API.
4. Saves accepted order details to MySQL under the authenticated user.

Do not use production Binance credentials with this project. Testnet mode is intended for testing against Binance Futures Testnet.

## Testing

Run the test suite with:

```bash
pytest -v tests/
```

The tests cover paper-trading behavior, validators, Flask endpoints, and testnet client/order logic.

## Logging

The application configures logging through `bot/logging_config.py`. Trading requests, paper executions, Binance errors, and persistence problems are logged for troubleshooting. Check the generated `bot.log` file when diagnosing runtime issues.

## Important Notes

- This project is for development and educational use; it is not financial advice or a production exchange platform.
- Paper trading is simulated and does not use real funds.
- Testnet orders are sent to Binance Futures Testnet, not the production exchange.
- Market data depends on network access to Binance public endpoints.
- The current server initializes the database during import/startup, so valid MySQL configuration is needed before running `server.py`.
- Passwords are stored using the project’s salted SHA-256 implementation. For production deployments, use a dedicated password-hashing algorithm such as Argon2id or bcrypt.

## License

This repository does not currently include a license file.
