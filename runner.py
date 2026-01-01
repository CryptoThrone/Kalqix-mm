import json
import sys
import threading
import signal
from cryptography.fernet import Fernet
import kalqix

stop_event = threading.Event()

def shutdown(sig, frame):
    print("Stopping wallet...")
    stop_event.set()

signal.signal(signal.SIGINT, shutdown)
signal.signal(signal.SIGTERM, shutdown)

def main(path):
    with open(path) as f:
        data = json.load(f)

    fernet = Fernet(data["_key"].encode())

    cfg = {
        "NAME": data["name"],
        "API_KEY": fernet.decrypt(data["api_key"].encode()).decode(),
        "API_SECRET": fernet.decrypt(data["api_secret"].encode()).decode(),
        "WALLET_SEED": fernet.decrypt(data["wallet_seed"].encode()).decode(),
        "BASE_URL": "https://testnet-api.kalqix.com",
        "TICKER": "BTC/USDC",
        "ORDER_SIZE": 0.001
    }

    kalqix.run_market_maker(cfg, stop_event)

if __name__ == "__main__":
    main(sys.argv[1])

