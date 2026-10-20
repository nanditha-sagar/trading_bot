
from db import get_db_connection, save_trade_order

# Fake Binance response: this does NOT place an exchange order.
fake_response = {
    "orderId": 123456789,
    "symbol": "BTCUSDT",
    "side": "BUY",
    "type": "LIMIT",
    "origQty": "0.001",
    "price": "60000",
    "executedQty": "0",
    "status": "NEW",
    "clientOrderId": "test_order_001"
}

try:
    order_id = save_trade_order(
        response=fake_response,
        symbol="BTCUSDT",
        side="BUY",
        order_type="LIMIT",
        quantity="0.001",
        price="60000"
    )

    print("Test order saved successfully:", order_id)

    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute(
        "SELECT exchange_order_id, symbol, side, status "
        "FROM trade_history WHERE exchange_order_id = %s",
        (order_id,)
    )

    print("Saved record:", cursor.fetchone())

    cursor.close()
    connection.close()

except Exception as error:
    print("Test failed:", error)
