import json
import threading
import signal
import sys
from cryptography.fernet import Fernet
import kalqix

stop_event = threading.Event()


def shutdown(sig, frame):
    print("Shutdown signal received", flush=True)
    stop_event.set()


signal.signal(signal.SIGINT, shutdown)
signal.signal(signal.SIGTERM, shutdown)


def main(cfg_path):
    with open(cfg_path) as f:
        data = json.load(f)

    fernet = Fernet(data["_key"].encode())

    cfg = {
        "NAME": data["name"],
        "API_KEY": fernet.decrypt(data["api_key"].encode()).decode(),
        "API_SECRET": fernet.decrypt(data["api_secret"].encode()).decode(),
        "WALLET_SEED": fernet.decrypt(data["wallet_seed"].encode()).decode(),
    }

    kalqix.run_market_maker(cfg, stop_event)


if __name__ == "__main__":
    main(sys.argv[1])

