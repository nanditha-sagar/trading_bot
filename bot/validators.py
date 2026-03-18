VALID_SIDES = {"BUY", "SELL"}
VALID_ORDER_TYPES = {"MARKET", "LIMIT"}


def validate_input(symbol, side, order_type, quantity, price=None):
    if not symbol or not symbol.strip():
        raise ValueError("Symbol cannot be empty. Example: BTCUSDT")

    if side.upper() not in VALID_SIDES:
        raise ValueError(f"Invalid side '{side}'. Must be BUY or SELL.")

    if order_type.upper() not in VALID_ORDER_TYPES:
        raise ValueError(f"Invalid order type '{order_type}'. Must be MARKET or LIMIT.")

    if quantity <= 0:
        raise ValueError("Quantity must be a positive number.")

    if order_type.upper() == "LIMIT":
        if price is None:
            raise ValueError("Price is required for LIMIT orders. Use --price <value>.")
        if price <= 0:
            raise ValueError("Price must be a positive number.")

    if order_type.upper() == "MARKET" and price is not None:
        raise ValueError("Price should not be provided for MARKET orders.")