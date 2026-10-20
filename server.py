"""
server.py — Minimal Flask HTTP adapter for the Binance Futures Testnet Trading Bot.

Exposes two endpoints consumed by the frontend:
  POST /api/order  — validate and place an order
  GET  /api/orders — return the in-memory recent-order history

API credentials are read server-side from .env and are never sent to the browser.
"""

import logging
from datetime import datetime, timezone
from flask import Flask, jsonify, request
from flask_cors import CORS

from bot.client import get_client
from bot.orders import place_order
from bot.validators import validate_input
from bot.logging_config import setup_logging

# Logging
setup_logging()
logger = logging.getLogger(__name__)

# App
app = Flask(__name__, static_folder="frontend", static_url_path="")
CORS(app)

# In-memory order history (most-recent first, capped at 50).
_order_history = []
MAX_HISTORY = 50


@app.route("/")
def index():
    return app.send_static_file("index.html")


@app.route("/api/orders", methods=["GET"])
def get_orders():
    return jsonify({"orders": _order_history})


@app.route("/api/order", methods=["POST"])
def create_order():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON."}), 400

    symbol = str(data.get("symbol", "")).strip().upper()
    side = str(data.get("side", "")).strip().upper()
    order_type = str(data.get("order_type", "")).strip().upper()

    try:
        quantity = float(data.get("quantity", 0))
    except (TypeError, ValueError):
        return jsonify({"error": "quantity must be a number."}), 400

    price_raw = data.get("price")
    price = None
    if price_raw not in (None, "", "null"):
        try:
            price = float(price_raw)
        except (TypeError, ValueError):
            return jsonify({"error": "price must be a number."}), 400

    # Validation (reuses existing bot logic)
    try:
        validate_input(symbol, side, order_type, quantity, price)
    except ValueError as exc:
        logger.warning("Validation failed: %s", exc)
        return jsonify({"error": str(exc)}), 422

    # Place order
    try:
        client = get_client()
        order = place_order(client, symbol, side, order_type, quantity, price)
    except EnvironmentError as exc:
        logger.error("Configuration error: %s", exc)
        return jsonify({"error": str(exc)}), 500
    except RuntimeError as exc:
        logger.error("Order failed: %s", exc)
        return jsonify({"error": str(exc)}), 502
    except Exception as exc:
        logger.exception("Unexpected error placing order")
        return jsonify({"error": "Unexpected server error: " + str(exc)}), 500

    # Record in history
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "symbol": symbol,
        "side": side,
        "order_type": order_type,
        "quantity": quantity,
        "price": price,
    }
    record.update(order)
    _order_history.insert(0, record)
    if len(_order_history) > MAX_HISTORY:
        _order_history.pop()

    return jsonify({"order": record}), 201


if __name__ == "__main__":
    print("\n" + "=" * 55)
    print("  Binance Futures Testnet Trading Bot - Web UI")
    print("  http://localhost:5000")
    print("  Testnet: testnet.binancefuture.com")
    print("=" * 55 + "\n")
    app.run(host="0.0.0.0", port=5000, debug=False)
