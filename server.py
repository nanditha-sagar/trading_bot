"""
server.py — Flask HTTP adapter for the Binance Futures Trading Bot.

Supports two distinct trading modes:
  1. PAPER TRADING (SIMULATED):
     Zero Binance balance and no API credentials required.
     Simulates MARKET/LIMIT orders, virtual 10,000 USDT balance, positions, and P&L.
     Orders NEVER touch Binance exchange or use real funds.

  2. TESTNET MODE (BINANCE API):
     Authenticates via BINANCE_API_KEY / BINANCE_API_SECRET in .env.
     Sends signed order requests to testnet.binancefuture.com.

Endpoints:
  GET  /api/orders?mode=paper|testnet  — Fetch recent orders for active mode
  POST /api/order                      — Place paper or testnet order
  GET  /api/paper/account              — Get virtual balance, equity, positions, P&L
  POST /api/paper/reset                — Reset virtual balance back to starting balance
  GET  /api/price?symbol=BTCUSDT       — Live market/mark price (no auth required)
  GET  /api/market-info?symbol=BTCUSDT — 24h ticker info (price, change, high, low, volume)
  GET  /api/klines?symbol=BTCUSDT&interval=15m — Candlestick klines data
  GET  /api/status                     — Server configuration and active features
"""

import os
import logging
from datetime import datetime, timezone
import requests
from flask import Flask, jsonify, request
from flask_cors import CORS

from bot.client import get_client
from bot.orders import place_order
from bot.validators import validate_input
from bot.logging_config import setup_logging
from bot.paper import paper_engine

# Logging
setup_logging()
logger = logging.getLogger(__name__)

# App
app = Flask(__name__, static_folder="frontend", static_url_path="")
CORS(app)

# In-memory history for Testnet orders (kept strictly separate from paper orders)
_testnet_order_history: list[dict] = []
MAX_HISTORY = 50


@app.route("/")
def index():
    """Serve the frontend single page app."""
    return app.send_static_file("index.html")


@app.route("/api/status", methods=["GET"])
def get_status():
    """Return backend status and mode availability."""
    has_keys = bool(os.getenv("BINANCE_API_KEY") and os.getenv("BINANCE_API_SECRET"))
    return jsonify({
        "status": "online",
        "has_testnet_keys": has_keys,
        "paper_starting_balance": paper_engine.starting_balance,
        "supported_modes": ["paper", "testnet"],
    })


@app.route("/api/price", methods=["GET"])
def get_price():
    """Get live market mark price for a symbol without authentication."""
    symbol = request.args.get("symbol", "BTCUSDT").strip().upper()
    try:
        price = paper_engine.get_market_price(symbol)
        return jsonify({"symbol": symbol, "price": price})
    except Exception as exc:
        logger.warning("Price lookup error for %s: %s", symbol, exc)
        return jsonify({"symbol": symbol, "price": 85000.0, "is_fallback": True})


@app.route("/api/market-info", methods=["GET"])
def get_market_info():
    """Get 24hr statistics (change percentage, high, low, volume) without authentication."""
    symbol = request.args.get("symbol", "BTCUSDT").strip().upper()
    try:
        res = requests.get(
            "https://fapi.binance.com/fapi/v1/ticker/24hr",
            params={"symbol": symbol},
            timeout=3.0,
        )
        if res.ok:
            data = res.json()
            return jsonify({
                "symbol": symbol,
                "price": float(data.get("lastPrice", 0)),
                "priceChange": float(data.get("priceChange", 0)),
                "priceChangePercent": float(data.get("priceChangePercent", 0)),
                "highPrice": float(data.get("highPrice", 0)),
                "lowPrice": float(data.get("lowPrice", 0)),
                "volume": float(data.get("volume", 0)),
            })
    except Exception as exc:
        logger.debug("Market info fetch failed from primary endpoint: %s", exc)

    # Fallback to testnet or local price
    try:
        res = requests.get(
            "https://testnet.binancefuture.com/fapi/v1/ticker/24hr",
            params={"symbol": symbol},
            timeout=3.0,
        )
        if res.ok:
            data = res.json()
            return jsonify({
                "symbol": symbol,
                "price": float(data.get("lastPrice", 0)),
                "priceChange": float(data.get("priceChange", 0)),
                "priceChangePercent": float(data.get("priceChangePercent", 0)),
                "highPrice": float(data.get("highPrice", 0)),
                "lowPrice": float(data.get("lowPrice", 0)),
                "volume": float(data.get("volume", 0)),
            })
    except Exception:
        pass

    curr_price = paper_engine.get_market_price(symbol)
    return jsonify({
        "symbol": symbol,
        "price": curr_price,
        "priceChange": 0.0,
        "priceChangePercent": 0.0,
        "highPrice": curr_price * 1.01,
        "lowPrice": curr_price * 0.99,
        "volume": 0.0,
        "is_fallback": True,
    })


@app.route("/api/klines", methods=["GET"])
def get_klines():
    """Get candlestick klines for chart visualization without authentication."""
    symbol = request.args.get("symbol", "BTCUSDT").strip().upper()
    interval = request.args.get("interval", "15m").strip()
    limit = int(request.args.get("limit", 60))

    try:
        res = requests.get(
            "https://fapi.binance.com/fapi/v1/klines",
            params={"symbol": symbol, "interval": interval, "limit": limit},
            timeout=4.0,
        )
        if res.ok:
            raw = res.json()
            candles = [
                {
                    "time": int(k[0]),
                    "open": float(k[1]),
                    "high": float(k[2]),
                    "low": float(k[3]),
                    "close": float(k[4]),
                    "volume": float(k[5]),
                }
                for k in raw
            ]
            return jsonify({"symbol": symbol, "interval": interval, "candles": candles})
    except Exception as exc:
        logger.debug("Klines fetch failed: %s", exc)

    # Fallback to testnet
    try:
        res = requests.get(
            "https://testnet.binancefuture.com/fapi/v1/klines",
            params={"symbol": symbol, "interval": interval, "limit": limit},
            timeout=4.0,
        )
        if res.ok:
            raw = res.json()
            candles = [
                {
                    "time": int(k[0]),
                    "open": float(k[1]),
                    "high": float(k[2]),
                    "low": float(k[3]),
                    "close": float(k[4]),
                    "volume": float(k[5]),
                }
                for k in raw
            ]
            return jsonify({"symbol": symbol, "interval": interval, "candles": candles})
    except Exception:
        pass

    return jsonify({"symbol": symbol, "interval": interval, "candles": [], "error": "Unable to fetch live klines"}), 502


@app.route("/api/orders", methods=["GET"])
def get_orders():
    """
    Return recent orders for the requested mode.
    Keeps paper and testnet order histories strictly separated.
    """
    mode = request.args.get("mode", "paper").strip().lower()
    if mode == "testnet":
        return jsonify({"orders": _testnet_order_history, "mode": "testnet"})
    return jsonify({"orders": paper_engine.orders, "mode": "paper"})


@app.route("/api/paper/account", methods=["GET"])
def get_paper_account():
    """Return the paper trading virtual account state (balance, equity, positions, P&L)."""
    return jsonify(paper_engine.get_account())


@app.route("/api/paper/reset", methods=["POST"])
def reset_paper_account():
    """Reset the virtual paper account to its starting balance."""
    account = paper_engine.reset_account()
    return jsonify({"message": "Paper account reset successfully.", "account": account})


@app.route("/api/order", methods=["POST"])
def create_order():
    """
    Place an order in either PAPER or TESTNET mode.

    JSON payload:
      {
        "mode":       "paper" | "testnet", // default is "paper"
        "symbol":     "BTCUSDT",
        "side":       "BUY" | "SELL",
        "order_type": "MARKET" | "LIMIT",
        "quantity":   0.002,
        "price":      95000.0 // required only for LIMIT
      }
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON."}), 400

    mode = str(data.get("mode", "paper")).strip().lower()
    if mode not in ("paper", "testnet"):
        return jsonify({"error": f"Invalid mode '{mode}'. Must be 'paper' or 'testnet'."}), 400

    symbol = str(data.get("symbol", "")).strip().upper()
    side = str(data.get("side", "")).strip().upper()
    order_type = str(data.get("order_type", "")).strip().upper()

    try:
        quantity = float(data.get("quantity", 0))
    except (TypeError, ValueError):
        return jsonify({"error": "quantity must be a valid number."}), 400

    price_raw = data.get("price")
    price = None
    if price_raw not in (None, "", "null"):
        try:
            price = float(price_raw)
        except (TypeError, ValueError):
            return jsonify({"error": "price must be a valid number."}), 400

    # 1. Validation (shared validation rules)
    try:
        validate_input(symbol, side, order_type, quantity, price)
    except ValueError as exc:
        logger.warning("Validation failed: %s", exc)
        return jsonify({"error": str(exc)}), 422

    # 2. Branch execution strictly by mode
    if mode == "paper":
        # ── Paper Trading Mode (Simulated, zero API keys, no Binance calls) ──
        try:
            order = paper_engine.place_order(symbol, side, order_type, quantity, price)
            account = paper_engine.get_account()
            return jsonify({
                "order": order,
                "mode": "paper",
                "account": account,
            }), 201
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 422
        except Exception as exc:
            logger.exception("Unexpected error in paper trading")
            return jsonify({"error": f"Paper simulation error: {exc}"}), 500

    else:
        # ── Testnet Mode (Calls real Binance Futures Testnet API) ─────────────
        try:
            client = get_client()
            order = place_order(client, symbol, side, order_type, quantity, price)
        except EnvironmentError as exc:
            logger.error("Configuration error in testnet: %s", exc)
            return jsonify({
                "error": str(exc),
                "tip": "Configure BINANCE_API_KEY and BINANCE_API_SECRET in .env, or switch to Paper Trading mode to trade with zero keys.",
            }), 500
        except RuntimeError as exc:
            logger.error("Order failed on Binance testnet: %s", exc)
            return jsonify({"error": str(exc)}), 502
        except Exception as exc:
            logger.exception("Unexpected error placing testnet order")
            return jsonify({"error": f"Unexpected server error: {exc}"}), 500

        # Record testnet order in testnet-only history
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "symbol": symbol,
            "side": side,
            "order_type": order_type,
            "quantity": quantity,
            "price": price,
            "is_simulated": False,
        }
        record.update(order)
        _testnet_order_history.insert(0, record)
        if len(_testnet_order_history) > MAX_HISTORY:
            _testnet_order_history.pop()

        return jsonify({
            "order": record,
            "mode": "testnet",
        }), 201


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  Binance Futures Trading Bot — Groww/Angel One UI")
    print("  http://localhost:5000")
    print("  Paper Trading Mode: Active (Virtual 10,000 USDT)")
    print("  Testnet Mode: testnet.binancefuture.com")
    print("=" * 60 + "\n")
    app.run(host="0.0.0.0", port=5000, debug=False)