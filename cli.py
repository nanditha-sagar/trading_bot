import sys
import click

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from bot.client import get_client
from bot.orders import place_order
from bot.validators import validate_input
from bot.logging_config import setup_logging
from bot.paper import paper_engine

setup_logging()


def print_banner(mode: str = "TESTNET"):
    click.echo("\n" + "=" * 55)
    if mode == "PAPER":
        click.echo("   🤖  Binance Futures Trading Bot — PAPER TRADING")
        click.echo("   📝  Execution: SIMULATED (No real funds / no API keys)")
        click.echo(f"   💰  Virtual Balance: {paper_engine.balance:,.2f} USDT")
    else:
        click.echo("   🤖  Binance Futures Testnet Trading Bot")
        click.echo("   📡  Connected to: testnet.binancefuture.com")
    click.echo("=" * 55)


def print_separator():
    click.echo("-" * 55)


def print_success(order, is_paper: bool = False):
    if is_paper:
        click.echo("\n  ✅ Simulated Paper Order Placed!")
        print_separator()
        click.echo(f"  {'Execution':<16}: SIMULATED (PAPER TRADING)")
        click.echo(f"  {'Order ID':<16}: {order.get('orderId', 'N/A')}")
        click.echo(f"  {'Status':<16}: {order.get('status', 'N/A')}")
        click.echo(f"  {'Executed Qty':<16}: {order.get('executedQty', 'N/A')}")
        avg_price = order.get("avgPrice") or order.get("price", "N/A")
        click.echo(f"  {'Simulated Price':<16}: {avg_price} USDT")
        click.echo(f"  {'Client Order ID':<16}: {order.get('clientOrderId', 'N/A')}")
        if order.get("realized_pnl"):
            click.echo(f"  {'Realized P&L':<16}: {order.get('realized_pnl'):+,.2f} USDT")
        click.echo(f"  {'Virtual Balance':<16}: {order.get('virtual_balance', paper_engine.balance):,.2f} USDT")
        print_separator()
        click.echo("  📁 Simulation logged to bot.log\n")
    else:
        click.echo("\n  ✅ Order Placed Successfully!")
        print_separator()
        click.echo(f"  {'Order ID':<16}: {order.get('orderId', 'N/A')}")
        click.echo(f"  {'Status':<16}: {order.get('status', 'N/A')}")
        click.echo(f"  {'Executed Qty':<16}: {order.get('executedQty', 'N/A')}")
        avg_price = order.get("avgPrice") or order.get("price", "N/A")
        click.echo(f"  {'Avg Price':<16}: {avg_price}")
        click.echo(f"  {'Client Order ID':<16}: {order.get('clientOrderId', 'N/A')}")
        click.echo(f"  {'Time In Force':<16}: {order.get('timeInForce', 'N/A')}")
        print_separator()
        click.echo("  📁 Full details saved to bot.log\n")


def prompt_mode():
    click.echo("\n  📌 Trading Mode")
    click.echo("     [1] TESTNET — Binance Futures Testnet (requires API keys in .env)")
    click.echo("     [2] PAPER   — Simulated trading (virtual 10,000 USDT, zero API keys)")
    choice = click.prompt("  Select", type=click.Choice(["1", "2"]), default="1", show_choices=False)
    return "TESTNET" if choice == "1" else "PAPER"


def prompt_symbol():
    click.echo("\n  📌 Symbol  (e.g. BTCUSDT, ETHUSDT)")
    return click.prompt("  Enter", default="BTCUSDT").strip().upper()


def prompt_side():
    click.echo("\n  📌 Side")
    click.echo("     [1] BUY  — go long")
    click.echo("     [2] SELL — go short")
    choice = click.prompt("  Select", type=click.Choice(["1", "2"]), show_choices=False)
    return "BUY" if choice == "1" else "SELL"


def prompt_order_type():
    click.echo("\n  📌 Order Type")
    click.echo("     [1] MARKET — execute immediately at best price")
    click.echo("     [2] LIMIT  — execute at your specified price")
    choice = click.prompt("  Select", type=click.Choice(["1", "2"]), show_choices=False)
    return "MARKET" if choice == "1" else "LIMIT"


def prompt_quantity():
    click.echo("\n  📌 Quantity  (min notional: $100)")
    return click.prompt("  Enter", type=float, default=0.002)


def prompt_price():
    click.echo("\n  📌 Limit Price (USDT)")
    return click.prompt("  Enter", type=float)


@click.command()
@click.option("--mode", type=click.Choice(["TESTNET", "PAPER"], case_sensitive=False), default=None, help="Trading mode: TESTNET or PAPER (default: TESTNET)")
@click.option("--paper", is_flag=True, default=False, help="Run in Paper Trading mode (virtual balance, no API keys)")
@click.option("--symbol", default=None, help="Trading pair, e.g. BTCUSDT")
@click.option("--side", default=None, type=click.Choice(["BUY", "SELL"], case_sensitive=False))
@click.option("--type", "order_type", default=None, type=click.Choice(["MARKET", "LIMIT"], case_sensitive=False))
@click.option("--quantity", type=float, default=None, help="Order quantity")
@click.option("--price", type=float, default=None, help="Limit price (required for LIMIT orders)")
def main(mode, paper, symbol, side, order_type, quantity, price):
    """Binance Futures Trading Bot — place MARKET or LIMIT orders in Testnet or Paper mode."""

    # Determine mode
    if paper:
        active_mode = "PAPER"
    elif mode:
        active_mode = mode.upper()
    elif not any([symbol, side, order_type, quantity]):
        # Full interactive mode: ask for mode
        active_mode = prompt_mode()
    else:
        active_mode = "TESTNET"

    print_banner(mode=active_mode)

    # Interactive prompts if flags not provided
    if not symbol:
        symbol = prompt_symbol()
    if not side:
        side = prompt_side()
    if not order_type:
        order_type = prompt_order_type()
    if not quantity:
        quantity = prompt_quantity()
    if order_type.upper() == "LIMIT" and price is None:
        price = prompt_price()

    # Validate
    print_separator()
    try:
        validate_input(symbol, side, order_type, quantity, price)
        click.echo("  ✔  Inputs validated successfully.")
    except ValueError as e:
        click.echo(f"\n  ❌ Validation Error: {e}")
        raise SystemExit(1)

    # Summary
    click.echo(f"\n  📋 Order Request Summary [{'SIMULATED' if active_mode == 'PAPER' else 'TESTNET'}]")
    print_separator()
    click.echo(f"  {'Mode':<12}: {active_mode}")
    click.echo(f"  {'Symbol':<12}: {symbol.upper()}")
    click.echo(f"  {'Side':<12}: {side.upper()}")
    click.echo(f"  {'Type':<12}: {order_type.upper()}")
    click.echo(f"  {'Quantity':<12}: {quantity}")
    if price:
        click.echo(f"  {'Price':<12}: {price} USDT")
        est_value = quantity * price
        click.echo(f"  {'Est. Value':<12}: ~${est_value:,.2f} USDT")
    print_separator()

    # Confirm
    if not click.confirm("\n  Confirm and place order?", default=True):
        click.echo("\n  ⚠️  Order cancelled by user.\n")
        raise SystemExit(0)

    click.echo(f"\n  ⏳ Placing {'simulated ' if active_mode == 'PAPER' else ''}order...")

    # Place order
    if active_mode == "PAPER":
        try:
            order = paper_engine.place_order(symbol, side, order_type, quantity, price)
            print_success(order, is_paper=True)
        except ValueError as e:
            click.echo(f"\n  ❌ Paper Trading Error: {e}")
            raise SystemExit(1)
        except Exception as e:
            click.echo(f"\n  ❌ Unexpected Error: {e}")
            raise SystemExit(1)
    else:
        # TESTNET mode (requires API credentials)
        try:
            client = get_client()
            order = place_order(client, symbol, side, order_type, quantity, price)
            print_success(order, is_paper=False)
        except EnvironmentError as e:
            click.echo(f"\n  ❌ Configuration Error: {e}")
            click.echo("  💡 Tip: Check your .env file has valid API keys.\n")
            raise SystemExit(1)
        except RuntimeError as e:
            click.echo(f"\n  ❌ Order Failed: {e}")
            click.echo("  💡 Tip: Check bot.log for full error details.\n")
            raise SystemExit(1)
        except Exception as e:
            click.echo(f"\n  ❌ Unexpected Error: {e}")
            raise SystemExit(1)


if __name__ == "__main__":
    main()