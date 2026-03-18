import logging
from binance.error import ClientError, ServerError

logger = logging.getLogger(__name__)


def place_order(client, symbol, side, order_type, quantity, price=None):
    params = {
        "symbol": symbol.upper(),
        "side": side.upper(),
        "type": order_type.upper(),
        "quantity": quantity,
    }

    if order_type.upper() == "LIMIT":
        params["price"] = price
        params["timeInForce"] = "GTC"

    logger.info("Order Request: %s, %s, %s, %s, %s",
                symbol, side, order_type, quantity, price)

    try:
        response = client.new_order(**params)
        logger.info("Order Response: %s", response)
        return response

    except ClientError as e:
        logger.error("Client error: status=%s, code=%s, message=%s",
                     e.status_code, e.error_code, e.error_message)
        raise RuntimeError(f"Binance API error {e.error_code}: {e.error_message}") from e

    except ServerError as e:
        logger.error("Server error: %s", e)
        raise RuntimeError("Binance server error. Please try again later.") from e

    except Exception as e:
        logger.error("Unexpected error: %s", e)
        raise