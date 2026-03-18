# Binance Trading Bot (Futures Testnet)

## 📌 Overview

A Python CLI trading bot that places Market and Limit orders on Binance Futures Testnet (USDT-M) using the official `binance-futures-connector` library. Supports both direct CLI flags and an interactive prompt-based mode.

## 🚀 Features

- Market & Limit Orders with BUY and SELL support
- CLI-based input with validation (Click)
- Interactive prompt mode — guided step-by-step order entry
- Structured code (client / orders / validators / logging)
- Logging of all API requests, responses, and errors to `bot.log`
- Exception handling (input errors, API errors, network failures)
- Order confirmation prompt before execution

## 🛠 Setup

### 1. Install dependencies

```
pip install -r requirements.txt
```

### 2. Configure API keys

Create a `.env` file in the project root:

```
BINANCE_API_KEY=your_testnet_api_key
BINANCE_API_SECRET=your_testnet_api_secret
```

Get your API keys from: https://demo.binance.com → Account → API Management

## ▶️ How to Run

### Option A — Direct CLI flags

**Market Order:**

```
python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.002
```

**Limit Order:**

```
python cli.py --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.002 --price 85000
```

### Option B — Interactive Mode (Bonus: Enhanced CLI UX)

Run without any flags and the bot will guide you step by step:

```
python cli.py
```

```
==================================================
   🤖  Binance Futures Testnet Trading Bot
   📡  Connected to: testnet.binancefuture.com
==================================================

  📌 Symbol  (e.g. BTCUSDT, ETHUSDT)
  Enter [BTCUSDT]:

  📌 Side
     [1] BUY  — go long
     [2] SELL — go short
  Select: 1

  📌 Order Type
     [1] MARKET — execute immediately at best price
     [2] LIMIT  — execute at your specified price
  Select: 1

  📌 Quantity  (min notional: $100)
  Enter [0.002]:
--------------------------------------------------
  ✔  Inputs validated successfully.

  📋 Order Request Summary
--------------------------------------------------
  Symbol      : BTCUSDT
  Side        : BUY
  Type        : MARKET
  Quantity    : 0.002
--------------------------------------------------

  Confirm and place order? [Y/n]: y

  ⏳ Placing order...

  ✅ Order Placed Successfully!
--------------------------------------------------
  Order ID       : 12859175058
  Status         : NEW
  Executed Qty   : 0.000
  Avg Price      : 0.00
  Client Order ID: x8q3piQLRZfC5wiL4jAf
  Time In Force  : GTC
--------------------------------------------------
  📁 Full details saved to bot.log
```

## 📁 Project Structure

```
trading_bot/
  bot/
    __init__.py
    client.py          # Binance UMFutures client wrapper
    orders.py          # Order placement logic
    validators.py      # Input validation
    logging_config.py  # Logging setup
  cli.py               # CLI entry point
  .env                 # API credentials (not committed to git)
  .env.example         # Template for credentials
  bot.log              # API request/response logs
  README.md
  requirements.txt
```

## 📋 Logs

All requests, responses, and errors are logged to `bot.log`:

```
2026-03-18 15:08:51 - INFO - Binance Futures Testnet client initialized successfully.
2026-03-18 15:08:51 - INFO - Order Request: BTCUSDT, BUY, MARKET, 0.002, None
2026-03-18 15:08:52 - INFO - Order Response: {'orderId': 12858999818, 'status': 'NEW', ...}
```

## ⚠️ Assumptions

- Only USDT-M Futures considered
- BTCUSDT used for testing
- Minimum order notional is $100 (Binance Futures requirement)
- Testnet access may require a VPN from certain regions
