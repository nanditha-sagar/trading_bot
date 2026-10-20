"""Tests for bot/validators.py"""
import pytest
from bot.validators import validate_input


def test_validate_valid_market_order():
    # Should not raise
    validate_input("BTCUSDT", "BUY", "MARKET", 0.002)
    validate_input("ETHUSDT", "SELL", "MARKET", 0.1)


def test_validate_valid_limit_order():
    # Should not raise
    validate_input("BTCUSDT", "BUY", "LIMIT", 0.002, 85000.0)
    validate_input("ETHUSDT", "SELL", "LIMIT", 0.5, 2600.0)


def test_validate_empty_symbol():
    with pytest.raises(ValueError, match="Symbol cannot be empty"):
        validate_input("", "BUY", "MARKET", 0.002)
    with pytest.raises(ValueError, match="Symbol cannot be empty"):
        validate_input("   ", "BUY", "MARKET", 0.002)


def test_validate_invalid_side():
    with pytest.raises(ValueError, match="Invalid side 'HOLD'"):
        validate_input("BTCUSDT", "HOLD", "MARKET", 0.002)


def test_validate_invalid_order_type():
    with pytest.raises(ValueError, match="Invalid order type 'STOP_LOSS'"):
        validate_input("BTCUSDT", "BUY", "STOP_LOSS", 0.002)


def test_validate_zero_or_negative_quantity():
    with pytest.raises(ValueError, match="Quantity must be a positive number"):
        validate_input("BTCUSDT", "BUY", "MARKET", 0)
    with pytest.raises(ValueError, match="Quantity must be a positive number"):
        validate_input("BTCUSDT", "BUY", "MARKET", -0.05)


def test_validate_limit_order_missing_or_invalid_price():
    with pytest.raises(ValueError, match="Price is required for LIMIT orders"):
        validate_input("BTCUSDT", "BUY", "LIMIT", 0.002, None)
    with pytest.raises(ValueError, match="Price must be a positive number"):
        validate_input("BTCUSDT", "BUY", "LIMIT", 0.002, 0)
    with pytest.raises(ValueError, match="Price must be a positive number"):
        validate_input("BTCUSDT", "BUY", "LIMIT", 0.002, -500.0)


def test_validate_market_order_with_price():
    with pytest.raises(ValueError, match="Price should not be provided for MARKET orders"):
        validate_input("BTCUSDT", "BUY", "MARKET", 0.002, 85000.0)