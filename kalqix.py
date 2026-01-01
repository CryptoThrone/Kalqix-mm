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
BALANCE_PATH = "/v1/wallet/balances"


def sign_request(method, path, body, timestamp, api_secret):
    payload = json.dumps(body, separators=(",", ":")) if body else ""
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
    r = requests.request(
        method,
        cfg["BASE_URL"] + path,
        headers=headers,
        json=body,
        timeout=10
    )
    try:
        return r.status_code, r.json()
    except Exception:
        return r.status_code, {"raw": r.text}


def get_balances(cfg):
    code, data = send_signed_request("GET", BALANCE_PATH, None, cfg)
    balances = {}
    if code == 200:
        for b in data.get("data", []):
            balances[b["asset"]] = float(b["available"])
    return balances


def get_orderbook(cfg):
    r = requests.get(cfg["BASE_URL"] + ORDERBOOK_PATH, timeout=10)
    return r.json()


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
            print(f"[{cfg['NAME']}] Fetching orderbook...")
            ob = get_orderbook(cfg)

            bids = ob.get("BUY", [])
            asks = ob.get("SELL", [])

            if not bids or not asks:
                print(f"[{cfg['NAME']}] Empty orderbook, skipping")
                time.sleep(5)
                continue

            best_bid = float(bids[0]["price"])
            best_ask = float(asks[0]["price"])
            mid = (best_bid + best_ask) / 2

            buy_price = round(mid * 0.999, 2)
            sell_price = round(mid * 1.001, 2)

            balances = get_balances(cfg)
            usdc = balances.get("USDC", 0)
            btc = balances.get("BTC", 0)

            if usdc >= buy_price * cfg["ORDER_SIZE"]:
                print(f"[{cfg['NAME']}] Placing BUY @ {buy_price}")
                code, resp = place_limit(cfg, "BUY", buy_price, cfg["ORDER_SIZE"])
                print(f"[{cfg['NAME']}] BUY response:", code, resp)
            else:
                print(f"[{cfg['NAME']}] Skipping BUY (USDC insufficient)")

            if btc >= cfg["ORDER_SIZE"]:
                print(f"[{cfg['NAME']}] Placing SELL @ {sell_price}")
                code, resp = place_limit(cfg, "SELL", sell_price, cfg["ORDER_SIZE"])
                print(f"[{cfg['NAME']}] SELL response:", code, resp)
            else:
                print(f"[{cfg['NAME']}] Skipping SELL (BTC insufficient)")

            print(f"[{cfg['NAME']}] Cycle complete, sleeping...\n")
            time.sleep(10)

        except Exception as e:
            print(f"[{cfg['NAME']}] ERROR:", e)
            time.sleep(5)

    print(f"[{cfg['NAME']}] stopped cleanly")

