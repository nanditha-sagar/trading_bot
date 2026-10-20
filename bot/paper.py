"""
bot/paper.py — Paper Trading Engine for Binance Futures.

Simulates MARKET and LIMIT order execution with zero Binance balance and
without any API keys. Maintains a virtual USDT balance, open positions,
and calculates realized/unrealized P&L.
"""

import os
import uuid
import logging
from datetime import datetime, timezone
import requests

from bot.validators import validate_input

logger = logging.getLogger(__name__)

# Default virtual starting balance is 10,000 USDT (configurable via env)
DEFAULT_STARTING_BALANCE = float(os.getenv("PAPER_STARTING_BALANCE", "10000000.0"))


class PaperTradingEngine:
    """In-memory Paper Trading Engine for Binance Futures simulation."""

    def __init__(self, starting_balance: float = None):
        self.starting_balance = starting_balance if starting_balance is not None else DEFAULT_STARTING_BALANCE
        self.balance = float(self.starting_balance)
        self.realized_pnl = 0.0
        self.positions: dict[str, dict] = {}  # symbol -> {"size": float, "entry_price": float}
        self.orders: list[dict] = []
        self.order_counter = 9000000000
        self._price_cache: dict[str, float] = {
            "BTCUSDT": 85000.0,
            "ETHUSDT": 2500.0,
            "SOLUSDT": 180.0,
            "BNBUSDT": 600.0,
        }

    def get_market_price(self, symbol: str) -> float:
        """
        Fetch public mark/ticker price without requiring API credentials.
        Falls back to testnet ticker, then cache/defaults if offline.
        """
        sym = symbol.upper()
        # 1. Try public Binance Futures production ticker (no auth needed)
        try:
            res = requests.get(
                "https://fapi.binance.com/fapi/v1/ticker/price",
                params={"symbol": sym},
                timeout=2.5,
            )
            if res.ok:
                data = res.json()
                price = float(data.get("price", 0))
                if price > 0:
                    self._price_cache[sym] = price
                    return price
        except Exception as exc:
            logger.debug("Public fapi price fetch failed: %s", exc)

        # 2. Try public Binance Futures testnet ticker (no auth needed)
        try:
            res = requests.get(
                "https://testnet.binancefuture.com/fapi/v1/ticker/price",
                params={"symbol": sym},
                timeout=2.5,
            )
            if res.ok:
                data = res.json()
                price = float(data.get("price", 0))
                if price > 0:
                    self._price_cache[sym] = price
                    return price
        except Exception as exc:
            logger.debug("Testnet price fetch failed: %s", exc)

        # 3. Use last known price for this symbol if available, otherwise fetch single ticker
        if sym in self._price_cache:
            return self._price_cache[sym]

        try:
            res = requests.get(
                "https://fapi.binance.com/fapi/v1/ticker/price",
                params={"symbol": sym},
                timeout=4.0,
            )
            if res.ok:
                price = float(res.json().get("price", 0))
                if price > 0:
                    self._price_cache[sym] = price
                    return price
        except Exception:
            pass

        raise RuntimeError(f"Real market price for symbol '{sym}' is currently unavailable from Binance Futures.")


    def get_unrealized_pnl(self) -> float:
        """Calculate total unrealized P&L across all open positions."""
        total_upnl = 0.0
        for sym, pos in self.positions.items():
            size = pos.get("size", 0.0)
            if abs(size) < 1e-8:
                continue
            entry = pos.get("entry_price", 0.0)
            curr = self.get_market_price(sym)
            if size > 0:  # LONG
                total_upnl += (curr - entry) * size
            else:  # SHORT
                total_upnl += (entry - curr) * abs(size)
        return total_upnl

    def get_account(self) -> dict:
        """Return the virtual account balance, equity, and open positions."""
        upnl = self.get_unrealized_pnl()
        equity = self.balance + upnl

        pos_list = []
        for sym, pos in self.positions.items():
            size = pos.get("size", 0.0)
            if abs(size) < 1e-8:
                continue
            entry = pos.get("entry_price", 0.0)
            curr = self.get_market_price(sym)
            pos_upnl = (curr - entry) * size if size > 0 else (entry - curr) * abs(size)
            pos_list.append({
                "symbol": sym,
                "size": round(size, 4),
                "side": "LONG" if size > 0 else "SHORT",
                "entry_price": round(entry, 2),
                "mark_price": round(curr, 2),
                "unrealized_pnl": round(pos_upnl, 2),
                "notional": round(abs(size) * curr, 2),
            })

        return {
            "mode": "paper",
            "starting_balance": round(self.starting_balance, 2),
            "balance": round(self.balance, 2),
            "equity": round(equity, 2),
            "realized_pnl": round(self.realized_pnl, 2),
            "unrealized_pnl": round(upnl, 2),
            "positions": pos_list,
        }

    def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: float,
        price: float = None,
    ) -> dict:
        """
        Simulate order placement and execution.
        Validates inputs, calculates fills, updates positions and balances.
        """
        # Validate inputs with existing validators
        validate_input(symbol, side, order_type, quantity, price)

        sym = symbol.strip().upper()
        sd = side.strip().upper()
        ot = order_type.strip().upper()
        qty = float(quantity)
        pr = float(price) if price is not None else None

        market_price = self.get_market_price(sym)

        # Determine execution price and fill status
        if ot == "MARKET":
            exec_price = market_price
            status = "FILLED"
            executed_qty = qty
        else:  # LIMIT
            exec_price = pr
            # Limit order fill logic:
            # BUY limit fills if limit price >= current market price
            # SELL limit fills if limit price <= current market price
            if (sd == "BUY" and pr >= market_price) or (sd == "SELL" and pr <= market_price):
                status = "FILLED"
                executed_qty = qty
            else:
                # Resting limit order
                status = "NEW"
                executed_qty = 0.0

        # Margin / Balance check
        order_notional = qty * (pr if pr else exec_price)
        available_balance = self.balance + self.get_unrealized_pnl()

        # Reject if balance is negative or order notional exceeds 10x leverage equivalent of available balance
        if available_balance <= 0:
            raise ValueError(
                f"Insufficient virtual balance ({available_balance:.2f} USDT). "
                f"Reset paper trading balance to continue."
            )
        if order_notional > available_balance * 10:
            raise ValueError(
                f"Virtual order value (~{order_notional:,.2f} USDT) exceeds max permitted margin "
                f"for virtual balance ({available_balance:,.2f} USDT)."
            )

        order_realized_pnl = 0.0

        # If filled, update positions and calculate realized P&L
        if status == "FILLED":
            current_pos = self.positions.get(sym, {"size": 0.0, "entry_price": 0.0})
            curr_size = current_pos["size"]
            curr_entry = current_pos["entry_price"]

            if abs(curr_size) < 1e-8:
                # Opening new position
                new_size = qty if sd == "BUY" else -qty
                self.positions[sym] = {"size": new_size, "entry_price": exec_price}
            elif (curr_size > 0 and sd == "BUY") or (curr_size < 0 and sd == "SELL"):
                # Increasing existing position in same direction
                add_qty = qty if sd == "BUY" else -qty
                new_size = curr_size + add_qty
                new_entry = (abs(curr_size) * curr_entry + qty * exec_price) / abs(new_size)
                self.positions[sym] = {"size": new_size, "entry_price": new_entry}
            else:
                # Closing or flipping position in opposite direction
                close_qty = min(abs(curr_size), qty)
                if curr_size > 0:  # was LONG, now SELL
                    pnl = (exec_price - curr_entry) * close_qty
                else:  # was SHORT, now BUY
                    pnl = (curr_entry - exec_price) * close_qty

                order_realized_pnl = pnl
                self.realized_pnl += pnl
                self.balance += pnl

                rem_order_qty = qty - close_qty
                if rem_order_qty > 1e-8:
                    # Flipped position
                    new_size = rem_order_qty if sd == "BUY" else -rem_order_qty
                    self.positions[sym] = {"size": new_size, "entry_price": exec_price}
                else:
                    # Reduced or flat
                    rem_pos = abs(curr_size) - close_qty
                    if rem_pos > 1e-8:
                        new_size = rem_pos if curr_size > 0 else -rem_pos
                        self.positions[sym] = {"size": new_size, "entry_price": curr_entry}
                    else:
                        self.positions[sym] = {"size": 0.0, "entry_price": 0.0}

        self.order_counter += 1
        order_id = self.order_counter
        client_order_id = f"PAPER_{uuid.uuid4().hex[:10].upper()}"
        now_iso = datetime.now(timezone.utc).isoformat()

        order_record = {
            "orderId": order_id,
            "symbol": sym,
            "status": status,
            "clientOrderId": client_order_id,
            "price": f"{pr:.2f}" if pr else f"{exec_price:.2f}",
            "avgPrice": f"{exec_price:.2f}" if status == "FILLED" else "0.00",
            "origQty": f"{qty:.4f}",
            "executedQty": f"{executed_qty:.4f}",
            "cumQuote": f"{round(executed_qty * exec_price, 2):.2f}",
            "timeInForce": "GTC",
            "type": ot,
            "side": sd,
            "timestamp": now_iso,
            # Prominent simulation metadata
            "is_simulated": True,
            "execution_type": "SIMULATED (PAPER TRADING)",
            "simulated_price": exec_price,
            "realized_pnl": round(order_realized_pnl, 4),
            "virtual_balance": round(self.balance, 2),
        }

        self.orders.insert(0, order_record)
        if len(self.orders) > 100:
            self.orders.pop()

        logger.info(
            "[PAPER TRADING] Order executed: id=%s %s %s %s @ %s, status=%s, PnL=%.2f, virtual_bal=%.2f",
            order_id, sd, qty, sym, exec_price, status, order_realized_pnl, self.balance,
        )
        return order_record

    def reset_account(self) -> dict:
        """Reset virtual balance, positions, and orders to initial state."""
        self.balance = float(self.starting_balance)
        self.realized_pnl = 0.0
        self.positions = {}
        self.orders = []
        logger.info("[PAPER TRADING] Virtual account reset to %.2f USDT.", self.starting_balance)
        return self.get_account()


# Separate in-memory paper trading engine for each user.
_paper_engines = {}


def get_paper_engine(user_id):
    """Return the paper trading engine belonging to one user."""
    if user_id is None:
        raise ValueError("An authenticated user ID is required.")

    user_id = int(user_id)

    if user_id not in _paper_engines:
        _paper_engines[user_id] = PaperTradingEngine()

    return _paper_engines[user_id]