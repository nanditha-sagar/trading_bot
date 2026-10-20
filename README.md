# Binance Trading Bot (Futures Testnet & Paper Trading)

## 📌 Overview

A Python trading bot and modern web trading terminal supporting two distinct execution modes:

1. **📝 Paper Trading (Simulated):** Works with **zero Binance balance and without API credentials**. Simulates MARKET and LIMIT orders, virtual USDT balance (default 10,000 USDT), position tracking, margin requirements, and real-time realized & unrealized P&L calculated against live public ticker prices.
2. **📡 Binance Testnet:** Direct integration with Binance Futures Testnet (USDT-M) using the official `binance-futures-connector` library. Requires API credentials in `.env`.

Both modes are accessible through a **Groww / Angel One inspired Web Trading Terminal** and an interactive **CLI tool**.

---

## 🚀 Key Features

- **Dual Modes (Paper Trading & Testnet):** Complete separation between paper simulation and real testnet execution.
- **Zero-Key Paper Trading:** Practice trading strategies immediately without Binance API keys or testnet balance.
- **Configurable Virtual Balance:** Default starting balance of 10,000 USDT, configurable via `PAPER_STARTING_BALANCE`.
- **Live Candlestick Charting:** Real-time HTML5 Canvas candlestick chart with multiple intervals (`1m`, `5m`, `15m`, `1h`, `4h`), crosshairs, moving averages, and volume indicators.
- **WebSocket Price Streaming:** Live Binance public WebSocket ticker streams with real-time price updates and 24h market stats (High, Low, Volume, Change).
- **Portfolio & Margin Summary:** Real-time visibility into Virtual Balance, Total Equity, Available Margin, Realized P&L, and live Unrealized P&L.
- **Position & P&L Simulation:** Accurately tracks LONG and SHORT positions, position flips, and computes realized/unrealized P&L based on linear USDT-M futures formulas.
- **Safety Confirmation Modal:** Built-in order review modal with estimated order values before execution.
- **CLI with Interactive Mode:** Guided step-by-step CLI order entry with prompt mode or direct terminal flags.
- **Automated Test Suite:** Comprehensive pytest suite with 33 unit and integration tests covering paper engine, validators, testnet client, and server API.
- **Structured Audit Logging:** Every simulated and testnet trade is timestamped and recorded in `bot.log`.

---

## 🛠 Setup

### 1. Prerequisites & Environment

Make sure you have Python 3.10+ installed. Create and activate a virtual environment:

**Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure API Keys (Only needed for Testnet Mode)

> [!NOTE]
> For **Paper Trading mode**, **NO API KEYS ARE REQUIRED**. You can skip this step and start paper trading immediately!

For **Testnet mode**, create a `.env` file in the project root:

```ini
BINANCE_API_KEY=your_testnet_api_key
BINANCE_API_SECRET=your_testnet_api_secret

# Optional: customize paper trading starting balance (default: 10000.0)
PAPER_STARTING_BALANCE=10000.0
```

Get your Testnet API keys from: [Binance Futures Testnet](https://testnet.binancefuture.com) (or https://demo.binance.com) → Account → API Management.

---

## ▶️ How to Run

### Method 1 — Web Trading Terminal (Recommended)

Start the local Flask server:

```bash
python server.py
```

Then open **[http://localhost:5000](http://localhost:5000)** in your browser.

#### Highlights of the Web UI:
- **Mode Switcher:** Toggle between **📝 Paper Trading** (zero risk, simulated) and **📡 Testnet** (live testnet API) via tabs in the header.
- **Interactive Candlestick Chart:** Toggle timeframes (`1m`, `5m`, `15m`, `1h`, `4h`) and search any USDT pair (e.g., `BTCUSDT`, `ETHUSDT`, `SOLUSDT`).
- **Portfolio Metrics Bar:** Monitor your Virtual Balance, Total Equity, Available Margin, and live Realized/Unrealized P&L.
- **One-Click Account Reset:** Reset virtual balance and positions back to starting values anytime.
- **Order Panel & Confirmation Modal:** Select BUY/LONG or SELL/SHORT, MARKET or LIMIT, specify quantity and price, review estimated margin and cost in the confirmation modal before submission.
- **Order & Position History:** View real-time simulated and testnet orders, execution prices, timestamps, and status tags.

---

### Method 2 — CLI (Paper Trading Mode — No API Keys Needed)

Execute simulated paper orders directly from your terminal using the `--paper` flag:

**Market Order (Simulated):**
```bash
python cli.py --paper --symbol BTCUSDT --side BUY --type MARKET --quantity 0.002
```

**Limit Order (Simulated):**
```bash
python cli.py --paper --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.002 --price 85000
```

**Interactive Guided Mode:**
Run `python cli.py` without arguments and select option `[2] PAPER`:

```text
=======================================================
   🤖  Binance Futures Trading Bot — PAPER TRADING
   📝  Execution: SIMULATED (No real funds / no API keys)
   💰  Virtual Balance: 10,000.00 USDT
=======================================================

  📌 Trading Mode
     [1] TESTNET — Binance Futures Testnet (requires API keys in .env)
     [2] PAPER   — Simulated trading (virtual 10,000 USDT, zero API keys)
  Select: 2
```

---

### Method 3 — CLI (Testnet Mode — Requires `.env` API Keys)

**Market Order:**
```bash
python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.002
```

**Limit Order:**
```bash
python cli.py --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.002 --price 85000
```

---

## 📡 Backend API Endpoints

The Flask server (`server.py`) exposes REST endpoints used by the Web Terminal:

| Method | Endpoint | Query / Body Params | Description |
|---|---|---|---|
| `GET` | `/` | — | Serves the single-page web terminal UI |
| `GET` | `/api/status` | — | Backend health, mode availability, key status |
| `GET` | `/api/price` | `symbol` (e.g. `BTCUSDT`) | Real-time mark/market price |
| `GET` | `/api/market-info` | `symbol` (e.g. `BTCUSDT`) | 24h ticker price, high, low, volume, percent change |
| `GET` | `/api/klines` | `symbol`, `interval` | Historical OHLCV candlestick data for chart rendering |
| `GET` | `/api/orders` | `mode=paper` or `testnet` | Order history for the active mode |
| `POST` | `/api/order` | JSON: `symbol`, `side`, `type`, `quantity`, `price`, `mode` | Place a simulated paper order or testnet order |
| `GET` | `/api/paper/account` | — | Virtual balance, equity, open positions, P&L metrics |
| `POST` | `/api/paper/reset` | — | Reset paper trading account to initial balance |

---

## 🧪 Running Tests

A test suite of 33 unit and integration tests is included:

```bash
# Using active venv:
pytest -v tests/

# Or via Windows venv directly:
.\venv\Scripts\pytest -v tests/
```

### Test Coverage Breakdown:
- `tests/test_paper.py` (10 tests): Virtual balance initialization, market & limit order execution, position updates, realized P&L, unrealized P&L, position flipping, margin sufficiency checks, and account reset.
- `tests/test_validators.py` (8 tests): Input validation for symbols, sides (`BUY`/`SELL`), order types (`MARKET`/`LIMIT`), positive quantities, and limit prices.
- `tests/test_testnet.py` (4 tests): Environment variable configuration, client initialization, payload construction, and error handling.
- `tests/test_server.py` (11 tests): Flask endpoints, candlestick klines, 24h ticker info, price routes, status checks, paper trading execution, and strict mode separation.

---

## 📁 Project Structure

```text
trading_bot/
├── bot/
│   ├── __init__.py          # Module exports (client, orders, paper_engine)
│   ├── client.py            # Binance UMFutures testnet client wrapper
│   ├── orders.py            # Testnet order placement logic
│   ├── paper.py             # Paper Trading simulation engine (P&L, balance, fills)
│   ├── validators.py        # Shared order input validation
│   └── logging_config.py    # Multi-handler logging setup
├── frontend/
│   ├── index.html           # Single-page trading terminal UI
│   ├── style.css            # Clean, modern trading terminal stylesheet
│   └── app.js               # Frontend controller (WebSockets, charts, order flow)
├── tests/
│   ├── conftest.py          # Pytest path and environment configuration
│   ├── test_paper.py        # Paper trading engine unit tests
│   ├── test_server.py       # API adapter integration tests
│   ├── test_testnet.py      # Testnet client & order placement tests
│   └── test_validators.py   # Input validation tests
├── cli.py                   # CLI entry point (supports --paper, testnet & interactive)
├── server.py                # Flask server adapter for Web UI & REST endpoints
├── .env.example             # Example environment variables template
├── bot.log                  # Request and trade audit log
├── README.md                # Project documentation
└── requirements.txt         # Project dependencies
```

---

## 📋 Audit Logs

All trading activities—simulated paper trades and testnet API calls—are recorded in `bot.log`:

```text
2026-10-20 17:03:42 - INFO - [PAPER TRADING] Order executed: id=9000000001 BUY 0.002 BTCUSDT @ 81435.6, status=FILLED, PnL=0.00, virtual_bal=10000.00
2026-10-20 17:08:12 - INFO - Order Request: BTCUSDT, BUY, MARKET, 0.002, None
```

---

## ⚠️ Notes & Assumptions

- **Paper Trading:** Completely isolated in-memory simulation. Orders never touch the Binance exchange and require zero credentials or funds.
- **Futures P&L Calculation:** Calculated according to standard linear USDT-M futures formulas:
  - **Long:** `(exit_price - entry_price) * size`
  - **Short:** `(entry_price - exit_price) * size`
- **Testnet Access:** Requires valid testnet API credentials in `.env` and network access to `testnet.binancefuture.com`.