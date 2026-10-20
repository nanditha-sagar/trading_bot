import os
import logging
from flask import Flask, jsonify, request, session

import requests
from flask_cors import CORS
from dotenv import load_dotenv

from db import (
    get_trade_history,
    init_db,
    register_user,
    authenticate_user,
    get_user_by_id,
)
from bot.client import get_client
from bot.orders import place_order
from bot.validators import validate_input
from bot.logging_config import setup_logging
from bot.paper import get_paper_engine
from functools import wraps

# Load environment variables from .env
load_dotenv()

# Logging
setup_logging()
logger = logging.getLogger(__name__)

# Initialize database tables on server startup
init_db()

# Flask app
app = Flask(__name__, static_folder="frontend", static_url_path="")
app.secret_key = os.environ["FLASK_SECRET_KEY"]
CORS(app)

def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        user_id = session.get("user_id")

        if not user_id:
            return jsonify({
                "error": "Please log in to access this feature.",
                "authenticated": False
            }), 401

        # Confirm the account still exists.
        try:
            user = get_user_by_id(user_id)
        except Exception:
            logger.exception("Failed to validate the current user")
            return jsonify({"error": "Unable to verify your account."}), 500

        if not user:
            session.clear()
            return jsonify({
                "error": "Your session is invalid. Please log in again.",
                "authenticated": False
            }), 401

        return func(*args, **kwargs)

    return wrapper


# ── Page Routes ──────────────────────────────────────────────────
@app.route("/")
def index():
    """Serve the trading dashboard single-page application."""
    return app.send_static_file("index.html")


@app.route("/login")
def login_page():
    """Serve the login web page."""
    return app.send_static_file("login.html")


@app.route("/register")
@app.route("/signin")
def register_page():
    """Serve the register / sign-in web page."""
    return app.send_static_file("register.html")


# ── Authentication API Endpoints ─────────────────────────────────
@app.route("/api/auth/register", methods=["POST"])
def auth_register():
    """Register a new user account."""
    data = request.get_json(silent=True) or {}
    username = str(data.get("username", "")).strip()
    email = str(data.get("email", "")).strip()
    password = str(data.get("password", "")).strip()

    try:
        user = register_user(username, email, password)
        session["user_id"] = user["id"]
        session["username"] = user["username"]
        return jsonify({
            "status": "success",
            "message": "Account created successfully.",
            "user": user,
        }), 201
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        logger.exception("User registration failed")
        return jsonify({"error": f"Registration failed: {exc}"}), 500


@app.route("/api/auth/login", methods=["POST"])
def auth_login():
    """Authenticate existing user credentials."""
    data = request.get_json(silent=True) or {}
    identifier = str(data.get("identifier", "")).strip()
    password = str(data.get("password", "")).strip()

    if not identifier or not password:
        return jsonify({"error": "Please provide your username/email and password."}), 400

    try:
        user = authenticate_user(identifier, password)
        if not user:
            return jsonify({"error": "Invalid username or password."}), 401

        session.clear()
        session["user_id"] = user["id"]
        session["username"] = user["username"]
        
        return jsonify({
            "status": "success",
            "message": "Logged in successfully.",
            "user": user,
        }), 200
    except Exception as exc:
        logger.exception("User login error")
        return jsonify({"error": f"Login failed: {exc}"}), 500


@app.route("/api/auth/me", methods=["GET"])
def auth_me():
    """Return the currently logged-in user profile, if any."""
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"authenticated": False, "user": None}), 200

    try:
        user = get_user_by_id(user_id)
        if not user:
            session.clear()
            return jsonify({"authenticated": False, "user": None}), 200
        return jsonify({
            "authenticated": True,
            "user": {
                "id": user["id"],
                "username": user["username"],
                "email": user["email"]
            }
        }), 200
    except Exception as exc:
        logger.exception("Failed to fetch user profile")
        return jsonify({"authenticated": False, "error": str(exc)}), 500


@app.route("/api/logout", methods=["POST"])
def logout():
    """Clear session data and return status."""
    session.clear()
    return jsonify({
        "status": "success",
        "message": "Logged out successfully.",
        "redirect_url": "/login"
    })


@app.route("/api/status", methods=["GET"])
def get_status():
    """Return backend status and mode availability."""
    has_keys = bool(
        os.getenv("BINANCE_API_KEY") and os.getenv("BINANCE_API_SECRET")
    )
    return jsonify({
        "status": "online",
        "has_testnet_keys": has_keys,
        "paper_starting_balance": float(
    os.getenv("PAPER_STARTING_BALANCE", "10000000.0")
),
        "supported_modes": ["paper", "testnet"],
    })


@app.route("/api/price", methods=["GET"])
def get_price():
    """Get the current market price for a symbol."""
    symbol = request.args.get("symbol", "BTCUSDT").strip().upper()
    try:
        price = get_paper_engine(0).get_market_price(symbol)
        return jsonify({"symbol": symbol, "price": price})
    except Exception as exc:
        logger.warning("Price lookup error for %s: %s", symbol, exc)
        return jsonify({"symbol": symbol, "price": 85000.0, "is_fallback": True})


@app.route("/api/market-info", methods=["GET"])
def get_market_info():
    """Get 24-hour market statistics without authentication."""
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

    # Fallback to Binance Futures Testnet.
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
    except Exception as exc:
        logger.debug("Testnet market info fetch failed: %s", exc)

    try:
        curr_price = get_paper_engine(0).get_market_price(symbol)
    except Exception:
        curr_price = 85000.0

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
    """Get candlestick data for chart visualization."""
    symbol = request.args.get("symbol", "BTCUSDT").strip().upper()
    interval = request.args.get("interval", "15m").strip()

    try:
        limit = int(request.args.get("limit", 60))
    except (TypeError, ValueError):
        return jsonify({"error": "limit must be an integer."}), 400

    # Keep request size within a reasonable range for the exchange API.
    limit = max(1, min(limit, 1500))

    for base_url in (
        "https://fapi.binance.com/fapi/v1/klines",
        "https://testnet.binancefuture.com/fapi/v1/klines",
    ):
        try:
            res = requests.get(
                base_url,
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
                return jsonify({
                    "symbol": symbol,
                    "interval": interval,
                    "candles": candles,
                })
        except Exception as exc:
            logger.debug("Klines fetch failed from %s: %s", base_url, exc)

    return jsonify({
        "symbol": symbol,
        "interval": interval,
        "candles": [],
        "error": "Unable to fetch live klines",
    }), 502


@app.route("/api/orders", methods=["GET"])
@login_required
def get_orders():
    """Return order history belonging to the logged-in user."""
    user_id = session["user_id"]
    mode = request.args.get("mode", "paper").strip().lower()

    if mode == "testnet":
        try:
            orders = get_trade_history(user_id=user_id, limit=50)
            return jsonify({"orders": orders, "mode": "testnet"})
        except Exception:
            logger.exception("Failed to load user Testnet history")
            return jsonify({"error": "Unable to load trading history."}), 500

    if mode == "paper":
        engine = get_paper_engine(session["user_id"])
        return jsonify({
            "orders": engine.orders,
            "mode": "paper"
        })
    return jsonify({"error": "Invalid mode. Use paper or testnet."}), 400


@app.route("/api/paper/account", methods=["GET"])
@login_required
def get_paper_account():
    engine = get_paper_engine(session["user_id"])
    return jsonify(engine.get_account())


@app.route("/api/paper/reset", methods=["POST"])
@login_required
def reset_paper_account():
    engine = get_paper_engine(session["user_id"])
    account = engine.reset_account()

    return jsonify({
        "message": "Paper account reset successfully.",
        "account": account
    })

@app.route("/api/order", methods=["POST"])
@login_required
def create_order():
    """Place an order in PAPER or Binance Futures TESTNET mode."""

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "error": "Request body must be a JSON object."
        }), 400

    user_id = session["user_id"]

    mode = str(data.get("mode", "paper")).strip().lower()

    if mode not in ("paper", "testnet"):
        return jsonify({
            "error": "Invalid mode. Must be 'paper' or 'testnet'."
        }), 400

    symbol = str(data.get("symbol", "")).strip().upper()
    side = str(data.get("side", "")).strip().upper()
    order_type = str(data.get("order_type", "")).strip().upper()

    try:
        quantity = float(data.get("quantity", 0))
    except (TypeError, ValueError):
        return jsonify({
            "error": "Quantity must be a valid number."
        }), 400

    price_raw = data.get("price")
    price = None

    if price_raw not in (None, "", "null"):
        try:
            price = float(price_raw)
        except (TypeError, ValueError):
            return jsonify({
                "error": "Price must be a valid number."
            }), 400

    try:
        validate_input(symbol, side, order_type, quantity, price)
    except ValueError as exc:
        logger.warning("Order validation failed: %s", exc)
        return jsonify({"error": str(exc)}), 422

    # PAPER TRADING — use this user's own engine.
    if mode == "paper":
        try:
            engine = get_paper_engine(user_id)

            order = engine.place_order(
                symbol, side, order_type, quantity, price
            )

            account = engine.get_account()

            return jsonify({
                "order": order,
                "mode": "paper",
                "account": account
            }), 201

        except ValueError as exc:
            return jsonify({"error": str(exc)}), 422

        except Exception:
            logger.exception(
                "Paper order failed for user_id=%s", user_id
            )
            return jsonify({
                "error": "An unexpected paper trading error occurred."
            }), 500

    # BINANCE FUTURES TESTNET — associate the order with this user.
    try:
        client = get_client()

        order = place_order(
            client,
            symbol,
            side,
            order_type,
            quantity,
            price,
            user_id=user_id
        )

    except EnvironmentError as exc:
        logger.error("Testnet configuration error: %s", exc)
        return jsonify({
            "error": str(exc),
            "tip": (
                "Configure BINANCE_API_KEY and BINANCE_API_SECRET "
                "in your .env file, or switch to Paper Trading."
            )
        }), 500

    except RuntimeError as exc:
        logger.error("Testnet order error: %s", exc)
        return jsonify({"error": str(exc)}), 502

    except Exception:
        logger.exception(
            "Unexpected Testnet order error for user_id=%s", user_id
        )
        return jsonify({
            "error": "An unexpected server error occurred."
        }), 500

    return jsonify({
        "order": order,
        "mode": "testnet"
    }), 201


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  Binance Futures Trading Bot — Groww/Angel One UI")
    print("  http://localhost:5000")
    print("  Paper Trading Mode: Active (Virtual 10,000 USDT)")
    print("  Testnet Mode: testnet.binancefuture.com")
    print("=" * 60 + "\n")
    app.run(host="0.0.0.0", port=5000, debug=False)
