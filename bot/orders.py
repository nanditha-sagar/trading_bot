import logging

from binance.error import ClientError, ServerError
from db import save_trade_order

logger = logging.getLogger(__name__)


def place_order(
    client,
    symbol,
    side,
    order_type,
    quantity,
    price=None,
    user_id=None,
):
    """
    Place a Binance Testnet order and save it for the authenticated user.
    """

    # Never place an order without an authenticated user ID.
    if user_id is None:
        raise ValueError("An authenticated user ID is required.")

    symbol = symbol.upper()
    side = side.upper()
    order_type = order_type.upper()

    if side not in ("BUY", "SELL"):
        raise ValueError("Side must be BUY or SELL.")

    if order_type not in ("MARKET", "LIMIT"):
        raise ValueError("Order type must be MARKET or LIMIT.")

    if quantity is None or float(quantity) <= 0:
        raise ValueError("Quantity must be greater than zero.")

    params = {
        "symbol": symbol,
        "side": side,
        "type": order_type,
        "quantity": quantity,
    }

    if order_type == "LIMIT":
        if price is None or float(price) <= 0:
            raise ValueError(
                "A positive price is required for LIMIT orders."
            )

        params["price"] = price
        params["timeInForce"] = "GTC"

    logger.info(
        "Order request: user_id=%s symbol=%s side=%s type=%s",
        user_id,
        symbol,
        side,
        order_type,
    )

    try:
        response = client.new_order(**params)
        logger.info(
            "Binance accepted order: order_id=%s",
            response.get("orderId"),
        )

    except ClientError as e:
        logger.error(
            "Binance client error: status=%s code=%s message=%s",
            e.status_code,
            e.error_code,
            e.error_message,
        )
        raise RuntimeError(
            f"Binance API error {e.error_code}: {e.error_message}"
        ) from e

    except ServerError as e:
        logger.error("Binance server error: %s", e)
        raise RuntimeError(
            "Binance server error. Check the exchange before retrying."
        ) from e

    # Save the accepted order against the authenticated user.
    try:
        save_trade_order(
            response=response,
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            user_id=user_id,
        )

        logger.info(
            "Order saved: user_id=%s order_id=%s",
            user_id,
            response.get("orderId"),
        )

    except Exception:
        # The exchange may already have accepted the order.
        # Do not automatically retry placement, as this could
        # create a duplicate order.
        logger.exception(
            "Order %s was accepted by Binance but could not be saved "
            "for user_id=%s.",
            response.get("orderId"),
            user_id,
        )

        # Report the persistence failure so the caller knows the
        # order history may not reflect the accepted exchange order.
        raise RuntimeError(
            "The exchange accepted the order, but saving it to the "
            "database failed. Check Binance Testnet before retrying."
        )

    return response
