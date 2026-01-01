import os
import json
import threading
from cryptography.fernet import Fernet
import subprocess

WALLETS_DIR = "wallets"

def setup_wallets():
    n = int(input("How many wallets to run? "))

    os.makedirs(WALLETS_DIR, exist_ok=True)

    for i in range(1, n + 1):
        print(f"\nConfiguring wallet {i}")

        name = f"wallet{i}"
        api_key = input("API Key: ")
        api_secret = input("API Secret: ")
        seed = input("Wallet Seed: ")

        key = Fernet.generate_key()
        fernet = Fernet(key)

        data = {
            "name": name,
            "_key": key.decode(),
            "api_key": fernet.encrypt(api_key.encode()).decode(),
            "api_secret": fernet.encrypt(api_secret.encode()).decode(),
            "wallet_seed": fernet.encrypt(seed.encode()).decode()
        }

        with open(f"{WALLETS_DIR}/{name}.json", "w") as f:
            json.dump(data, f, indent=2)

        print(f"{name} saved.")

def start_all():
    for file in os.listdir(WALLETS_DIR):
        if file.endswith(".json"):
            subprocess.Popen(["python3", "runner.py", f"{WALLETS_DIR}/{file}"])

def main():
    print("1) Setup wallets")
    print("2) Start all wallets")

    choice = input("Choose: ")

    if choice == "1":
        setup_wallets()
    elif choice == "2":
        start_all()

if __name__ == "__main__":
    main()
