import os
import sqlite3
import threading
import time
import random
from datetime import datetime
from urllib.parse import quote

import requests
from flask import Flask, jsonify, render_template_string, request

# ------------------------------------------------------------
# Config
# ------------------------------------------------------------
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
APP_PORT = int(os.environ.get("PORT", "8080"))
AUTO_POST_INTERVAL = int(os.environ.get("AUTO_POST_INTERVAL", str(60 * 60 * 4)))
DB_PATH = os.environ.get("DATABASE_PATH", "data/affiliate_bot.db")

app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False

# ------------------------------------------------------------
# Database
# ------------------------------------------------------------
def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    conn = get_db_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            price TEXT NOT NULL,
            asin TEXT NOT NULL UNIQUE,
            image_url TEXT,
            description TEXT,
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id TEXT NOT NULL UNIQUE,
            customer TEXT NOT NULL,
            asin TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'new',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    existing = conn.execute("SELECT COUNT(*) AS count FROM products").fetchone()["count"]
    if existing == 0:
        sample_products = [
            (
                "AirPods Pro 2",
                "$189",
                "B0D1XD1ZV3",
                "https://m.media-amazon.com/images/I/61SUj2aKoEL._AC_SL1500_.jpg",
                "4.8* 100K+ #1 USA",
                1,
            ),
            (
                "Gold Cross 14K BEST SELLER",
                "$9.99",
                "B0D3H6XYZ1",
                "https://m.media-amazon.com/images/I/61k+O6Q+8LL._AC_SX679_.jpg",
                "4.6* 2621 reviews Gift Box USA",
                1,
            ),
            (
                "Wireless Earbuds Pro",
                "$39.99",
                "B0C2ABCD12",
                "https://m.media-amazon.com/images/I/61Qb2GZuXSL._AC_SL1500_.jpg",
                "4.7* 18K+ happy buyers",
                1,
            ),
        ]
        conn.executemany(
            """
            INSERT INTO products (title, price, asin, image_url, description, active)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            sample_products,
        )

    conn.commit()
    conn.close()


init_db()

# ------------------------------------------------------------
# Utility functions
# ------------------------------------------------------------
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
        return short_url or amazon_url
    except Exception:
        return amazon_url


def wa_message_link(text):
    return f"https://wa.me/{WHATSAPP_NUMBER}?text={quote(text)}"


def telegram_send_message(text):
    if not BOT_TOKEN or not CHANNEL_ID:
        return False
    try:
        response = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
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
        response = requests.get(
            "https://api.callmebot.com/whatsapp.php"
            f"?phone={WHATSAPP_NUMBER}&text={quote(text)}&apikey={WHATSAPP_API_KEY}",
            timeout=10,
        )
        response.raise_for_status()
        return True
    except Exception:
        return False


def get_active_products():
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT * FROM products WHERE active = 1 ORDER BY id DESC"
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def create_order_record(asin, customer):
    order_id = f"ORD{int(time.time())}"
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO orders (order_id, customer, asin, status) VALUES (?, ?, ?, 'new')",
        (order_id, customer, asin),
    )
    conn.commit()
    conn.close()
    return order_id


# ------------------------------------------------------------
# Routes
# ------------------------------------------------------------
@app.route("/")
def home():
    products = get_active_products()
    conn = get_db_connection()
    order_count = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    conn.close()
    return {
        "status": "online",
        "whatsapp": WHATSAPP_NUMBER,
        "products": len(products),
        "orders": order_count,
        "time": datetime.now().isoformat(),
        "routes": [
            "/genius?asin=...",
            "/wa-status?asin=...",
            "/tg-buyer?asin=...&cust=...",
            "/order?asin=...&cust=...",
            "/api/products",
            "/api/orders",
            "/admin",
        ],
    }


@app.route("/healthz")
def healthz():
    return {"status": "ok"}


@app.route("/genius")
def genius():
    asin = request.args.get("asin", DEFAULT_ASIN)
    in_link, us_link = amazon_links(asin)
    short_url = genius_short_url(asin)
    return {
        "asin": asin,
        "geni_us": short_url,
        "amazon_in": in_link,
        "amazon_us": us_link,
        "whatsapp": WHATSAPP_NUMBER,
    }


@app.route("/wa-status")
def wa_status():
    asin = request.args.get("asin", DEFAULT_ASIN)
    product = next((p for p in get_active_products() if p["asin"] == asin), get_active_products()[0]) if get_active_products() else None
    if not product:
        return {"error": "No active products found"}, 404

    status_text = f"STATUS {product['title']} {genius_short_url(asin)} WA {WHATSAPP_NUMBER}"
    whatsapp_send_message(status_text)
    return {"status": "sent", "product": product["title"], "recipient": WHATSAPP_NUMBER}


@app.route("/tg-buyer")
def tg_buyer():
    asin = request.args.get("asin", DEFAULT_ASIN)
    customer = request.args.get("cust", "Customer")
    product = next((p for p in get_active_products() if p["asin"] == asin), get_active_products()[0]) if get_active_products() else None
    if not product:
        return {"error": "No active products found"}, 404

    message = f"AUTO-BUYER NEW ORDER {customer} {product['title']} ASIN {asin} WA {WHATSAPP_NUMBER}"
    telegram_send_message(message)
    return {"status": "sent", "message": message}


@app.route("/order")
def order():
    asin = request.args.get("asin", DEFAULT_ASIN)
    customer = request.args.get("cust", "Customer")
    order_id = create_order_record(asin, customer)
    order_link = wa_message_link(f"Order {order_id} {asin} by {customer}")
    return {
        "order_id": order_id,
        "customer": customer,
        "asin": asin,
        "wa_link": order_link,
    }


@app.route("/admin")
def admin_dashboard():
    conn = get_db_connection()
    products = conn.execute(
        "SELECT * FROM products ORDER BY id DESC"
    ).fetchall()
    orders = conn.execute(
        "SELECT * FROM orders ORDER BY id DESC LIMIT 50"
    ).fetchall()
    conn.close()

    html = """
    <html>
      <head>
        <title>Affiliate Bot Admin</title>
        <style>
          body { font-family: Arial, sans-serif; margin: 30px; background: #f8f9fb; }
          .card { background: white; border-radius: 12px; padding: 18px; margin-bottom: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); }
          table { width: 100%; border-collapse: collapse; }
          th, td { padding: 10px; border-bottom: 1px solid #eee; text-align: left; }
          input, textarea, button { padding: 10px; margin: 6px 0; width: 100%; box-sizing: border-box; }
          button { background: #1f6feb; color: white; border: none; border-radius: 8px; cursor: pointer; }
          .row { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
        </style>
      </head>
      <body>
        <h1>Affiliate Bot Admin</h1>
        <div class="row">
          <div class="card">
            <h2>Add Product</h2>
            <form action="/api/products" method="post">
              <input name="title" placeholder="Title" required>
              <input name="price" placeholder="Price" required>
              <input name="asin" placeholder="ASIN" required>
              <input name="image_url" placeholder="Image URL">
              <textarea name="description" placeholder="Description"></textarea>
              <button type="submit">Save Product</button>
            </form>
          </div>
          <div class="card">
            <h2>Quick Actions</h2>
            <p><a href="/genius?asin=B0D3H6XYZ1">Test Genius Link</a></p>
            <p><a href="/order?asin=B0D3H6XYZ1&cust=Admin">Create Test Order</a></p>
            <p><a href="/api/orders">View Orders JSON</a></p>
            <p><a href="/api/products">View Products JSON</a></p>
          </div>
        </div>

        <div class="card">
          <h2>Products</h2>
          <table>
            <thead>
              <tr><th>ID</th><th>Title</th><th>Price</th><th>ASIN</th><th>Active</th></tr>
            </thead>
            <tbody>
              {% for product in products %}
              <tr>
                <td>{{ product['id'] }}</td>
                <td>{{ product['title'] }}</td>
                <td>{{ product['price'] }}</td>
                <td>{{ product['asin'] }}</td>
                <td>{{ product['active'] }}</td>
              </tr>
              {% endfor %}
            </tbody>
          </table>
        </div>

        <div class="card">
          <h2>Orders</h2>
          <table>
            <thead>
              <tr><th>ID</th><th>Order ID</th><th>Customer</th><th>ASIN</th><th>Status</th></tr>
            </thead>
            <tbody>
              {% for order in orders %}
              <tr>
                <td>{{ order['id'] }}</td>
                <td>{{ order['order_id'] }}</td>
                <td>{{ order['customer'] }}</td>
                <td>{{ order['asin'] }}</td>
                <td>{{ order['status'] }}</td>
              </tr>
              {% endfor %}
            </tbody>
          </table>
        </div>
      </body>
    </html>
    """
    return render_template_string(html, products=products, orders=orders)


# ------------------------------------------------------------
# API endpoints
# ------------------------------------------------------------
@app.route("/api/products", methods=["GET", "POST"])
def api_products():
    if request.method == "GET":
        products = get_active_products()
        return jsonify(products)

    data = request.form or request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    price = (data.get("price") or "").strip()
    asin = (data.get("asin") or "").strip()
    image_url = (data.get("image_url") or "").strip()
    description = (data.get("description") or "").strip()

    if not title or not price or not asin:
        return {"error": "title, price and asin are required"}, 400

    conn = get_db_connection()
    try:
        conn.execute(
            """
            INSERT INTO products (title, price, asin, image_url, description, active)
            VALUES (?, ?, ?, ?, ?, 1)
            """,
            (title, price, asin, image_url, description),
        )
        conn.commit()
        product_id = conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
    except sqlite3.IntegrityError:
        return {"error": "ASIN already exists"}, 409
    finally:
        conn.close()

    return {"status": "created", "id": product_id}, 201


@app.route("/api/orders", methods=["GET", "POST"])
def api_orders():
    if request.method == "GET":
        conn = get_db_connection()
        rows = conn.execute("SELECT * FROM orders ORDER BY id DESC").fetchall()
        conn.close()
        return jsonify([dict(row) for row in rows])

    data = request.form or request.get_json(silent=True) or {}
    asin = (data.get("asin") or DEFAULT_ASIN).strip()
    customer = (data.get("customer") or data.get("cust") or "Customer").strip()
    order_id = create_order_record(asin, customer)
    return {"status": "created", "order_id": order_id}, 201


# ------------------------------------------------------------
# Background publishing loop
# ------------------------------------------------------------
def auto_post_loop():
    while True:
        try:
            products = get_active_products()
            if products:
                product = random.choice(products)
                asin = product["asin"]
                in_link, us_link = amazon_links(asin)
                short_url = genius_short_url(asin)
                wa_link = wa_message_link(f"Hi I want {product['title']}")
                caption = (
                    f"{product['title']} {product['price']} "
                    f"ONE LINK ALL COUNTRIES "
                    f"geni.us {short_url} "
                    f"IN {in_link} "
                    f"US {us_link} "
                    f"WA Order {WHATSAPP_NUMBER} {wa_link} "
                    f"As Amazon Associate I earn WA {WHATSAPP_NUMBER}"
                )

                telegram_send_photo(product.get("image_url") or "", caption)
                facebook_post_photo(product.get("image_url") or "", caption)
                whatsapp_send_message(caption[:500])
        except Exception:
            pass
        time.sleep(AUTO_POST_INTERVAL)


threading.Thread(target=auto_post_loop, daemon=True).start()


# ------------------------------------------------------------
# Run app
# ------------------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=APP_PORT, debug=False)
























































































































































