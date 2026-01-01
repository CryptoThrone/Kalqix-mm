import time
import hmac
import hashlib
import json
import requests
from eth_account import Account
from eth_account.messages import encode_defunct

Account.enable_unaudited_hdwallet_features()

BASE_URL = "https://testnet-api.kalqix.com"
ORDERS_PATH = "/v1/orders"
ORDERBOOK_PATH = "/v1/markets/BTC_USDC/order-book"

def sign_request(method, path, body, timestamp, api_secret):
    payload = json.dumps(body, separators=(',', ':')) if body else ""
    msg = f"{method}|{path}|{payload}|{timestamp}"
    return hmac.new(api_secret.encode(), msg.encode(), hashlib.sha256).hexdigest()

def sign_order_message(order, wallet_seed):
    acct = Account.from_mnemonic(wallet_seed)
    price = order["price"] if order["order_type"] == "LIMIT" else "MARKET"
    msg = f"{order['side']} {order['quantity']} {order['ticker']} @PRICE: {price}"
    sig = acct.sign_message(encode_defunct(text=msg))
    return msg, "0x" + sig.signature.hex()

def send_signed_request(method, path, body, cfg):
    ts = int(time.time() * 1000)
    sig = sign_request(method, path, body, ts, cfg["API_SECRET"])
    headers = {
        "x-api-key": cfg["API_KEY"],
        "x-api-signature": sig,
        "x-api-timestamp": str(ts),
        "Content-Type": "application/json"
    }
    r = requests.request(method, cfg["BASE_URL"] + path, headers=headers, json=body, timeout=10)
    return r.status_code, r.text

def place_limit(cfg, side, price, qty):
    order = {
        "ticker": cfg["TICKER"],
        "price": str(price),
        "quantity": str(qty),
        "side": side,
        "order_type": "LIMIT"
    }
    msg, sig = sign_order_message(order, cfg["WALLET_SEED"])
    order["message"] = msg
    order["signature"] = sig
    return send_signed_request("POST", ORDERS_PATH, order, cfg)

def run_market_maker(cfg, stop_event):
    print(f"[{cfg['NAME']}] started")

    while not stop_event.is_set():
        try:
            # SIMPLE TEST ORDERS (safe)
            place_limit(cfg, "BUY", "10000", cfg["ORDER_SIZE"])
            time.sleep(2)
            place_limit(cfg, "SELL", "20000", cfg["ORDER_SIZE"])
            time.sleep(10)
        except Exception as e:
            print(f"[{cfg['NAME']}] error:", e)
            time.sleep(5)

    print(f"[{cfg['NAME']}] stopped")
