import os
import json
import threading
from cryptography.fernet import Fernet
import runner

WALLETS_DIR = "wallets"
threads = []


def setup_wallets():
    n = int(input("How many wallets? "))
    os.makedirs(WALLETS_DIR, exist_ok=True)

    for i in range(1, n + 1):
        print(f"\nWallet {i}")
        name = f"wallet{i}"
        api_key = input("API Key: ")
        api_secret = input("API Secret: ")
        seed = input("Wallet Seed: ")

        key = Fernet.generate_key()
        f = Fernet(key)

        data = {
            "name": name,
            "_key": key.decode(),
            "api_key": f.encrypt(api_key.encode()).decode(),
            "api_secret": f.encrypt(api_secret.encode()).decode(),
            "wallet_seed": f.encrypt(seed.encode()).decode(),
        }

        with open(f"{WALLETS_DIR}/{name}.json", "w") as fp:
            json.dump(data, fp, indent=2)

        print(f"{name} saved")


def start_all():
    for file in os.listdir(WALLETS_DIR):
        if file.endswith(".json"):
            t = threading.Thread(
                target=runner.main,
                args=(f"{WALLETS_DIR}/{file}",),
                daemon=True,
            )
            threads.append(t)
            t.start()

    print("\nAll wallets started. Press Ctrl+C to stop.\n")

    try:
        for t in threads:
            t.join()
    except KeyboardInterrupt:
        print("Stopping all wallets...")


def main():
    print("1) Setup wallets")
    print("2) Start all wallets")

    c = input("Choose: ")

    if c == "1":
        setup_wallets()
    elif c == "2":
        start_all()


if __name__ == "__main__":
    main()

