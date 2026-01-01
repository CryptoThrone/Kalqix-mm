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

SESSION = requests.Session()
SESSION.headers.update({"Content-Type": "application/json"})


def log(name, msg):
    print(f"[{name}] {msg}", flush=True)


def sign_request(method, path, body, ts, secret):
    payload = json.dumps(body, separators=(",", ":")) if body else ""
    raw = f"{method}|{path}|{payload}|{ts}"
    return hmac.new(secret.encode(), raw.encode(), hashlib.sha256).hexdigest()


def sign_order(order, seed):
    acct = Account.from_mnemonic(seed)
    price = order["price"] if order["order_type"] == "LIMIT" else "MARKET"
    msg = f"{order['side']} {order['quantity']} {order['ticker']} @PRICE: {price}"
    sig = acct.sign_message(encode_defunct(text=msg))
    return msg, "0x" + sig.signature.hex()


def send(method, path, body, cfg):
    ts = int(time.time() * 1000)
    sig = sign_request(method, path, body, ts, cfg["API_SECRET"])

    headers = {
        "x-api-key": cfg["API_KEY"],
        "x-api-signature": sig,
        "x-api-timestamp": str(ts),
    }

    try:
        r = SESSION.request(
            method,
            BASE_URL + path,
            headers=headers,
            json=body,
            timeout=5,
        )
        return r.status_code, r.text
    except requests.exceptions.RequestException as e:
        return None, str(e)


def get_orderbook(cfg):
    try:
        r = SESSION.get(BASE_URL + ORDERBOOK_PATH, timeout=5)
        return r.json()
    except Exception:
        return None


def place_limit(cfg, side, price):
    order = {
        "ticker": "BTC/USDC",
        "price": str(price),
        "quantity": "0.001",
        "side": side,
        "order_type": "LIMIT",
    }

    msg, sig = sign_order(order, cfg["WALLET_SEED"])
    order["message"] = msg
    order["signature"] = sig

    return send("POST", ORDERS_PATH, order, cfg)


def run_market_maker(cfg, stop_event):
    name = cfg["NAME"]
    log(name, "Market maker started")

    while not stop_event.is_set():
        try:
            log(name, "Fetching orderbook...")
            ob = get_orderbook(cfg)

            if not ob or "BUY" not in ob or "SELL" not in ob:
                log(name, "Orderbook unavailable, retrying...")
                time.sleep(5)
                continue

            bid = float(ob["BUY"][0]["price"])
            ask = float(ob["SELL"][0]["price"])
            mid = (bid + ask) / 2

            buy_price = round(mid * 0.999, 2)
            sell_price = round(mid * 1.001, 2)

            log(name, f"Placing BUY @ {buy_price}")
            code, resp = place_limit(cfg, "BUY", buy_price)
            log(name, f"BUY response: {code} {resp}")

            time.sleep(2)

            log(name, f"Placing SELL @ {sell_price}")
            code, resp = place_limit(cfg, "SELL", sell_price)
            log(name, f"SELL response: {code} {resp}")

            log(name, "Cycle complete, sleeping...\n")
            time.sleep(10)

        except Exception as e:
            log(name, f"ERROR: {e}")
            time.sleep(5)

    log(name, "Stopped cleanly")

