import os
import logging
from dotenv import load_dotenv
from binance.um_futures import UMFutures

load_dotenv()

logger = logging.getLogger(__name__)

TESTNET_BASE_URL = "https://testnet.binancefuture.com"


def get_client() -> UMFutures:
    api_key = os.getenv("BINANCE_API_KEY")
    api_secret = os.getenv("BINANCE_API_SECRET")

    if not api_key or not api_secret:
        raise EnvironmentError(
            "BINANCE_API_KEY and BINANCE_API_SECRET must be set in your .env file."
        )

    client = UMFutures(
        key=api_key,
        secret=api_secret,
        base_url=TESTNET_BASE_URL,
    )

    logger.info("Binance Futures Testnet client initialized successfully.")
    return client
