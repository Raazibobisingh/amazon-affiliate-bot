import os
import time
import random
import threading
from datetime import datetime
from urllib.parse import quote

import requests
from flask import Flask, request

# ---------------------------
# Config
# ---------------------------
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
CHANNEL_ID = os.environ.get("CHANNEL_ID", "@yourchannel")
FB_PAGE_ID = os.environ.get("FB_PAGE_ID", "")
FB_PAGE_TOKEN = os.environ.get("FB_PAGE_TOKEN", "")
WHATSAPP_NUMBER = os.environ.get("WHATSAPP_NUMBER", "918830782569")
WHATSAPP_API_KEY = os.environ.get("WHATSAPP_API_KEY", "")
GENIUS_API = os.environ.get("GENIUS_API", "")
AMAZON_US_TAG = os.environ.get("AMAZON_US_TAG", "dainty04-20")
AMAZON_IN_TAG = os.environ.get("AMAZON_IN_TAG", "dainty04-21")
DEFAULT_ASIN = os.environ.get("DEFAULT_ASIN", "B0D3H6XYZ1")

app = Flask(__name__)
ORDERS = []

# ---------------------------
# Product Catalog
# ---------------------------
PRODUCTS = [
    {
        "t": "AirPods Pro 2",
        "p": "$189",
        "a": "B0D1XD1ZV3",
        "i": "https://m.media-amazon.com/images/I/61SUj2aKoEL._AC_SL1500_.jpg",
        "d": "4.8* 100K+ #1 USA",
    },
    {
        "t": "Gold Cross 14K BEST SELLER",
        "p": "$9.99",
        "a": "B0D3H6XYZ1",
        "i": "https://m.media-amazon.com/images/I/61k+O6Q+8LL._AC_SX679_.jpg",
        "d": "4.6* 2621 reviews Gift Box USA",
    },
    {
        "t": "Wireless Earbuds Pro",
        "p": "$39.99",
        "a": "B0C2ABCD12",
        "i": "https://m.media-amazon.com/images/I/61Qb2GZuXSL._AC_SL1500_.jpg",
        "d": "4.7* 18K+ happy buyers",
    },
] * 25

# ---------------------------
# Utility Functions
# ---------------------------
def amazon_links(asin):
    in_link = f"https://www.amazon.in/dp/{asin}?tag={AMAZON_IN_TAG}"
    us_link = f"https://www.amazon.com/dp/{asin}?tag={AMAZON_US_TAG}"
    return in_link, us_link


def genius_short_url(asin):
    amazon_url = f"https://www.amazon.com/dp/{asin}?tag={AMAZON_US_TAG}"
    if not GENIUS_API:
        return amazon_url

    try:
        response = requests.post(
            "https://api.geni.us/v1/short",
            headers={"Authorization": f"Bearer {GENIUS_API}"},
            json={"url": amazon_url},
            timeout=5,
        )
        response.raise_for_status()
        payload = response.json()
        short_url = payload.get("shortUrl")
        if short_url:
            return short_url
        return amazon_url
    except Exception:
        return amazon_url


def wa_message_link(text):
    return f"https://wa.me/{WHATSAPP_NUMBER}?text={quote(text)}"


def telegram_send_message(text):
    if not BOT_TOKEN or not CHANNEL_ID:
        return False
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        response = requests.post(
            url,
            data={"chat_id": CHANNEL_ID, "text": text},
            timeout=10,
        )
        response.raise_for_status()
        return True
    except Exception:
        return False


def telegram_send_photo(image_url, caption):
    if not BOT_TOKEN or not CHANNEL_ID:
        return False
    try:
        response = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",
            data={
                "chat_id": CHANNEL_ID,
                "caption": caption[:1024],
                "photo": image_url,
            },
            timeout=15,
        )
        response.raise_for_status()
        return True
    except Exception:
        return False


def facebook_post_photo(image_url, caption):
    if not FB_PAGE_ID or not FB_PAGE_TOKEN:
        return False
    try:
        response = requests.post(
            f"https://graph.facebook.com/{FB_PAGE_ID}/photos",
            data={
                "url": image_url,
                "caption": caption,
                "access_token": FB_PAGE_TOKEN,
            },
            timeout=15,
        )
        response.raise_for_status()
        return True
    except Exception:
        return False


def whatsapp_send_message(text):
    if not WHATSAPP_API_KEY:
        return False
    try:
        url = (
            f"https://api.callmebot.com/whatsapp.php"
            f"?phone={WHATSAPP_NUMBER}&text={quote(text)}&apikey={WHATSAPP_API_KEY}"
        )
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return True
    except Exception:
        return False


# ---------------------------
# Routes
# ---------------------------
@app.route("/")
def home():
    return (
        f"BOT LIVE WA {WHATSAPP_NUMBER} "
        f"Products {len(PRODUCTS)} "
        f"Orders {len(ORDERS)} "
        f"Time {datetime.now()} "
        "/genius /wa-status /tg-buyer /order"
    )


@app.route("/genius")
def genius():
    asin = request.args.get("asin", DEFAULT_ASIN)
    in_link, us_link = amazon_links(asin)
    short_url = genius_short_url(asin)
    return (
        f"geni.us {short_url} "
        f"IN {in_link} "
        f"US {us_link} "
        f"WA {WHATSAPP_NUMBER}"
    )


@app.route("/wa-status")
def wa_status():
    asin = request.args.get("asin", random.choice(PRODUCTS)["a"])
    product = next((x for x in PRODUCTS if x["a"] == asin), PRODUCTS[0])
    short_url = genius_short_url(asin)

    status_text = (
        f"STATUS {product['t']} {short_url} "
        f"WA {WHATSAPP_NUMBER}"
    )

    whatsapp_send_message(status_text)
    return f"WA Status Posted {product['t']} to {WHATSAPP_NUMBER}"


@app.route("/tg-buyer")
def tg_buyer():
    asin = request.args.get("asin", DEFAULT_ASIN)
    customer = request.args.get("cust", "Customer")
    product = next((x for x in PRODUCTS if x["a"] == asin), PRODUCTS[0])

    message = (
        f"AUTO-BUYER NEW ORDER {customer} "
        f"{product['t']} ASIN {asin} WA {WHATSAPP_NUMBER}"
    )
    telegram_send_message(message)
    return f"TG Buyer {asin} {customer} WA {WHATSAPP_NUMBER}"


@app.route("/order")
def order():
    asin = request.args.get("asin", DEFAULT_ASIN)
    customer = request.args.get("cust", "Customer")

    order_id = f"ORD{int(time.time())}"
    ORDERS.append({"id": order_id, "asin": asin, "customer": customer})

    order_link = wa_message_link(f"Order {order_id} {asin} by {customer}")
    return (
        f"Order {order_id} Created "
        f"WA {order_link}"
    )


# ---------------------------
# Auto posting loop
# ---------------------------
def auto_post_loop():
    while True:
        try:
            product = random.choice(PRODUCTS)
            asin = product["a"]

            in_link, us_link = amazon_links(asin)
            short_url = genius_short_url(asin)

            wa_link = wa_message_link(f"Hi I want {product['t']}")

            caption = (
                f"{product['t']} {product['p']} "
                f"ONE LINK ALL COUNTRIES "
                f"geni.us {short_url} "
                f"IN {in_link} "
                f"US {us_link} "
                f"WA Order {WHATSAPP_NUMBER} {wa_link} "
                f"As Amazon Associate I earn WA {WHATSAPP_NUMBER}"
            )

            telegram_send_photo(product["i"], caption)
            facebook_post_photo(product["i"], caption)
            whatsapp_send_message(caption[:500])

            time.sleep(14400)
        except Exception:
            time.sleep(60)


# ---------------------------
# Run app
# ---------------------------
threading.Thread(target=auto_post_loop, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)




























































































































































































