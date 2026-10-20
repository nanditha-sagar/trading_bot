"""Tests for server.py (Flask HTTP adapter)"""
import pytest
from server import app
from bot.paper import paper_engine


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_index_route(client):
    res = client.get("/")
    assert res.status_code == 200
    assert b"Futures Trading" in res.data


def test_market_info_endpoint(client):
    res = client.get("/api/market-info?symbol=BTCUSDT")
    assert res.status_code == 200
    data = res.get_json()
    assert data["symbol"] == "BTCUSDT"
    assert "price" in data


def test_klines_endpoint(client):
    res = client.get("/api/klines?symbol=BTCUSDT&interval=15m")
    assert res.status_code in (200, 502)



def test_status_endpoint(client):
    res = client.get("/api/status")
    assert res.status_code == 200
    data = res.get_json()
    assert "supported_modes" in data
    assert "paper" in data["supported_modes"]
    assert "testnet" in data["supported_modes"]


def test_price_endpoint(client):
    res = client.get("/api/price?symbol=BTCUSDT")
    assert res.status_code == 200
    data = res.get_json()
    assert data["symbol"] == "BTCUSDT"
    assert "price" in data
    assert float(data["price"]) > 0


def test_paper_account_endpoint(client):
    res = client.get("/api/paper/account")
    assert res.status_code == 200
    data = res.get_json()
    assert data["mode"] == "paper"
    assert "balance" in data
    assert "equity" in data


def test_paper_reset_endpoint(client):
    res = client.post("/api/paper/reset")
    assert res.status_code == 200
    data = res.get_json()
    assert data["account"]["balance"] == paper_engine.starting_balance



def test_create_order_paper_mode(client):
    payload = {
        "mode": "paper",
        "symbol": "BTCUSDT",
        "side": "BUY",
        "order_type": "MARKET",
        "quantity": 0.005,
    }
    res = client.post("/api/order", json=payload)
    assert res.status_code == 201
    data = res.get_json()
    assert data["mode"] == "paper"
    order = data["order"]
    assert order["is_simulated"] is True
    assert order["status"] == "FILLED"
    assert "account" in data


def test_paper_and_testnet_orders_separation(client):
    # Fetch paper orders
    res_paper = client.get("/api/orders?mode=paper")
    assert res_paper.status_code == 200
    data_paper = res_paper.get_json()
    assert data_paper["mode"] == "paper"

    # Fetch testnet orders
    res_testnet = client.get("/api/orders?mode=testnet")
    assert res_testnet.status_code == 200
    data_testnet = res_testnet.get_json()
    assert data_testnet["mode"] == "testnet"

    # All paper orders must have is_simulated == True
    for o in data_paper.get("orders", []):
        assert o.get("is_simulated") is True


def test_create_order_validation_error(client):
    # Invalid side
    payload = {
        "mode": "paper",
        "symbol": "BTCUSDT",
        "side": "INVALID_SIDE",
        "order_type": "MARKET",
        "quantity": 0.005,
    }
    res = client.post("/api/order", json=payload)
    assert res.status_code == 422
    data = res.get_json()
    assert "error" in data


def test_testnet_mode_without_keys_returns_error(client, monkeypatch):
    monkeypatch.delenv("BINANCE_API_KEY", raising=False)
    monkeypatch.delenv("BINANCE_API_SECRET", raising=False)
    payload = {
        "mode": "testnet",
        "symbol": "BTCUSDT",
        "side": "BUY",
        "order_type": "MARKET",
        "quantity": 0.002,
    }
    res = client.post("/api/order", json=payload)
    # Testnet without credentials should fail with 500 config error and helpful tip
    assert res.status_code == 500
    data = res.get_json()
    assert "error" in data
    assert "tip" in data


def test_logout_endpoint(client):
    # Set a session value
    with client.session_transaction() as sess:
        sess["user_id"] = "trader_1"

    # Call logout
    res = client.post("/api/logout")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert data["redirect_url"] == "/login"

    # Confirm session cleared
    with client.session_transaction() as sess:
        assert "user_id" not in sess


def test_auth_pages_render(client):
    res_login = client.get("/login")
    assert res_login.status_code == 200
    assert b"Welcome back" in res_login.data

    res_register = client.get("/register")
    assert res_register.status_code == 200
    assert b"Create your account" in res_register.data


def test_auth_me_unauthenticated(client):
    res = client.get("/api/auth/me")
    assert res.status_code == 200
    data = res.get_json()
    assert data["authenticated"] is False


def test_auth_login_missing_credentials(client):
    res = client.post("/api/auth/login", json={})
    assert res.status_code == 400
    data = res.get_json()
    assert "error" in data