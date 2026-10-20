"""Tests for bot/paper.py (Paper Trading Engine)"""
import pytest
from bot.paper import PaperTradingEngine


@pytest.fixture
def engine():
    """Create a fresh isolated engine instance with 10,000 USDT."""
    eng = PaperTradingEngine(starting_balance=10000.0)
    # Mock market price to 80,000 USDT for deterministic math
    eng.get_market_price = lambda symbol: 80000.0
    return eng


def test_default_balance(engine):
    acc = engine.get_account()
    assert acc["mode"] == "paper"
    assert acc["starting_balance"] == 10000.0
    assert acc["balance"] == 10000.0
    assert acc["equity"] == 10000.0
    assert acc["realized_pnl"] == 0.0
    assert acc["unrealized_pnl"] == 0.0
    assert len(acc["positions"]) == 0


def test_custom_starting_balance():
    eng = PaperTradingEngine(starting_balance=25000.0)
    assert eng.balance == 25000.0
    assert eng.starting_balance == 25000.0


def test_paper_market_buy_execution(engine):
    order = engine.place_order("BTCUSDT", "BUY", "MARKET", 0.05)
    assert order["is_simulated"] is True
    assert "SIMULATED" in order["execution_type"]
    assert order["status"] == "FILLED"
    assert order["side"] == "BUY"
    assert float(order["executedQty"]) == 0.05
    assert float(order["avgPrice"]) == 80000.0
    assert order["clientOrderId"].startswith("PAPER_")

    acc = engine.get_account()
    assert len(acc["positions"]) == 1
    pos = acc["positions"][0]
    assert pos["symbol"] == "BTCUSDT"
    assert pos["side"] == "LONG"
    assert pos["size"] == 0.05
    assert pos["entry_price"] == 80000.0


def test_paper_market_sell_realized_pnl(engine):
    # Buy 0.1 BTC at 80,000
    engine.get_market_price = lambda s: 80000.0
    engine.place_order("BTCUSDT", "BUY", "MARKET", 0.1)

    # Sell 0.1 BTC at 85,000 -> Realized P&L = (85,000 - 80,000) * 0.1 = +500 USDT
    engine.get_market_price = lambda s: 85000.0
    sell_order = engine.place_order("BTCUSDT", "SELL", "MARKET", 0.1)

    assert sell_order["status"] == "FILLED"
    assert sell_order["realized_pnl"] == 500.0

    acc = engine.get_account()
    assert acc["balance"] == 10500.0
    assert acc["realized_pnl"] == 500.0
    assert len(acc["positions"]) == 0  # Position is now flat


def test_paper_short_then_buy_realized_pnl(engine):
    # Short 0.1 BTC at 80,000
    engine.get_market_price = lambda s: 80000.0
    engine.place_order("BTCUSDT", "SELL", "MARKET", 0.1)

    # Buy back at 75,000 -> Realized P&L = (80,000 - 75,000) * 0.1 = +500 USDT
    engine.get_market_price = lambda s: 75000.0
    buy_order = engine.place_order("BTCUSDT", "BUY", "MARKET", 0.1)

    assert buy_order["status"] == "FILLED"
    assert buy_order["realized_pnl"] == 500.0

    acc = engine.get_account()
    assert acc["balance"] == 10500.0
    assert acc["realized_pnl"] == 500.0
    assert len(acc["positions"]) == 0


def test_paper_position_flip(engine):
    # Long 0.1 BTC at 80,000
    engine.get_market_price = lambda s: 80000.0
    engine.place_order("BTCUSDT", "BUY", "MARKET", 0.1)

    # Sell 0.2 BTC at 82,000
    # Closes 0.1 long -> +200 USDT realized P&L
    # Opens 0.1 short at 82,000
    engine.get_market_price = lambda s: 82000.0
    flip_order = engine.place_order("BTCUSDT", "SELL", "MARKET", 0.2)

    assert flip_order["realized_pnl"] == 200.0
    acc = engine.get_account()
    assert acc["balance"] == 10200.0
    assert len(acc["positions"]) == 1
    assert acc["positions"][0]["side"] == "SHORT"
    assert acc["positions"][0]["size"] == -0.1
    assert acc["positions"][0]["entry_price"] == 82000.0


def test_paper_limit_orders(engine):
    engine.get_market_price = lambda s: 80000.0

    # Limit BUY below market -> Resting NEW
    resting = engine.place_order("BTCUSDT", "BUY", "LIMIT", 0.01, 78000.0)
    assert resting["status"] == "NEW"
    assert float(resting["executedQty"]) == 0.0

    # Limit BUY at or above market -> Immediate fill
    marketable = engine.place_order("BTCUSDT", "BUY", "LIMIT", 0.01, 80500.0)
    assert marketable["status"] == "FILLED"
    assert float(marketable["executedQty"]) == 0.01


def test_paper_unrealized_pnl(engine):
    engine.get_market_price = lambda s: 80000.0
    engine.place_order("BTCUSDT", "BUY", "MARKET", 0.1)

    # Price moves to 83,000 -> Unrealized P&L = +300 USDT
    engine.get_market_price = lambda s: 83000.0
    acc = engine.get_account()
    assert acc["unrealized_pnl"] == 300.0
    assert acc["equity"] == 10300.0
    assert acc["balance"] == 10000.0


def test_paper_insufficient_balance(engine):
    engine.get_market_price = lambda s: 80000.0
    # 2.0 BTC at 80,000 = 160,000 USDT (exceeds 10x margin of 10,000 USDT balance)
    with pytest.raises(ValueError, match="exceeds max permitted margin"):
        engine.place_order("BTCUSDT", "BUY", "MARKET", 2.0)


def test_paper_reset_account(engine):
    engine.get_market_price = lambda s: 80000.0
    engine.place_order("BTCUSDT", "BUY", "MARKET", 0.05)
    assert len(engine.orders) > 0
    assert len(engine.positions) > 0

    acc = engine.reset_account()
    assert acc["balance"] == 10000.0
    assert acc["realized_pnl"] == 0.0
    assert len(acc["positions"]) == 0
    assert len(engine.orders) == 0