import time
import hmac
import hashlib
import json
import random
import requests
from eth_account import Account
from eth_account.messages import encode_defunct

Account.enable_unaudited_hdwallet_features()

BASE_URL = "https://testnet-api.kalqix.com"
ORDERS_PATH = "/v1/orders"
ORDERBOOK_PATH = "/v1/markets/BTC_USDC/order-book"


def sign_request(method, path, body, timestamp, api_secret):
    payload = json.dumps(body, separators=(",", ":")) if body else ""
    msg = f"{method}|{path}|{payload}|{timestamp}"
    return hmac.new(api_secret.encode(), msg.encode(), hashlib.sha256).hexdigest()


def sign_order_message(order, wallet_seed):
    acct = Account.from_mnemonic(wallet_seed)
    price = order["price"] if order["order_type"] == "LIMIT" else "MARKET"
    message = f"{order['side']} {order['quantity']} {order['ticker']} @PRICE: {price}"
    signed = acct.sign_message(encode_defunct(text=message))
    return message, "0x" + signed.signature.hex()


def send_signed_request(method, path, body, cfg):
    ts = int(time.time() * 1000)
    sig = sign_request(method, path, body, ts, cfg["API_SECRET"])
    headers = {
        "x-api-key": cfg["API_KEY"],
        "x-api-signature": sig,
        "x-api-timestamp": str(ts),
        "Content-Type": "application/json"
    }
    r = requests.request(
        method,
        cfg["BASE_URL"] + path,
        headers=headers,
        json=body,
        timeout=15
    )
    try:
        return r.status_code, r.json()
    except Exception:
        return r.status_code, {"raw": r.text}


def get_orderbook(cfg):
    code, data = send_signed_request("GET", ORDERBOOK_PATH, None, cfg)
    if code != 200:
        return None
    return data


def place_limit(cfg, side, price, qty):
    order = {
        "ticker": cfg["TICKER"],
        "price": f"{price:.2f}",
        "quantity": f"{qty:.6f}",
        "side": side,
        "order_type": "LIMIT"
    }
    msg, sig = sign_order_message(order, cfg["WALLET_SEED"])
    order["message"] = msg
    order["signature"] = sig
    return send_signed_request("POST", ORDERS_PATH, order, cfg)


def random_order_size():
    # Random size between 0.001 and 0.01 BTC
    return round(random.uniform(0.001, 0.01), 6)


def run_market_maker(cfg, stop_event):
    print(f"[{cfg['NAME']}] Market maker started")

    while not stop_event.is_set():
        try:
            print(f"[{cfg['NAME']}] Fetching orderbook...")
            ob = get_orderbook(cfg)

            if not ob or "BUY" not in ob or "SELL" not in ob:
                print(f"[{cfg['NAME']}] Orderbook unavailable, retrying...")
                time.sleep(5)
                continue

            best_bid = float(ob["BUY"][0]["price"])
            best_ask = float(ob["SELL"][0]["price"])
            mid = (best_bid + best_ask) / 2

            spread = cfg.get("SPREAD", 0.001)
            buy_price = mid * (1 - spread)
            sell_price = mid * (1 + spread)

            qty = random_order_size()
            print(f"[{cfg['NAME']}] Order size chosen: {qty} BTC")

            print(f"[{cfg['NAME']}] Placing BUY @ {buy_price:.2f}")
            code, resp = place_limit(cfg, "BUY", buy_price, qty)
            print(f"[{cfg['NAME']}] BUY response:", code, resp)

            time.sleep(1)

            print(f"[{cfg['NAME']}] Placing SELL @ {sell_price:.2f}")
            code, resp = place_limit(cfg, "SELL", sell_price, qty)
            print(f"[{cfg['NAME']}] SELL response:", code, resp)

            print(f"[{cfg['NAME']}] Cycle complete, sleeping...\n")
            time.sleep(cfg.get("REFRESH_INTERVAL", 10))

        except Exception as e:
            print(f"[{cfg['NAME']}] error:", e)
            time.sleep(5)

    print(f"[{cfg['NAME']}] Market maker stopped")

