"""Tests for testnet mode (bot/client.py and bot/orders.py)"""
from unittest.mock import MagicMock
import pytest
from bot.client import get_client
from bot.orders import place_order


def test_get_client_missing_keys(monkeypatch):
    monkeypatch.delenv("BINANCE_API_KEY", raising=False)
    monkeypatch.delenv("BINANCE_API_SECRET", raising=False)
    with pytest.raises(EnvironmentError, match="BINANCE_API_KEY and BINANCE_API_SECRET must be set"):
        get_client()


def test_get_client_with_keys(monkeypatch):
    monkeypatch.setenv("BINANCE_API_KEY", "test_key")
    monkeypatch.setenv("BINANCE_API_SECRET", "test_secret")
    client = get_client()
    assert client is not None


def test_place_order_market():
    mock_client = MagicMock()
    mock_client.new_order.return_value = {
        "orderId": 12345678,
        "symbol": "BTCUSDT",
        "status": "FILLED",
        "clientOrderId": "test_client_id",
        "price": "0",
        "avgPrice": "82000.00",
        "origQty": "0.002",
        "executedQty": "0.002",
        "timeInForce": "GTC",
        "type": "MARKET",
        "side": "BUY",
    }

    res = place_order(mock_client, "BTCUSDT", "BUY", "MARKET", 0.002)
    mock_client.new_order.assert_called_once_with(
        symbol="BTCUSDT",
        side="BUY",
        type="MARKET",
        quantity=0.002,
    )
    assert res["orderId"] == 12345678
    assert res["status"] == "FILLED"


def test_place_order_limit():
    mock_client = MagicMock()
    mock_client.new_order.return_value = {
        "orderId": 87654321,
        "symbol": "BTCUSDT",
        "status": "NEW",
        "price": "85000.00",
        "executedQty": "0.000",
        "type": "LIMIT",
        "side": "SELL",
    }

    res = place_order(mock_client, "BTCUSDT", "SELL", "LIMIT", 0.005, 85000.0)
    mock_client.new_order.assert_called_once_with(
        symbol="BTCUSDT",
        side="SELL",
        type="LIMIT",
        quantity=0.005,
        price=85000.0,
        timeInForce="GTC",
    )
    assert res["orderId"] == 87654321