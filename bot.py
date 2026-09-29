import os
import random
import sqlite3
import threading
import time
from datetime import datetime
from functools import wraps
from urllib.parse import quote

import requests
from flask import Flask, jsonify, redirect, render_template_string, request, session, url_for

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
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")
SECRET_KEY = os.environ.get("SECRET_KEY", "change-me-please")

app = Flask(__name__)
app.secret_key = SECRET_KEY
app.config["JSON_SORT_KEYS"] = False

# ------------------------------------------------------------
# DB helpers
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
            phone TEXT,
            notes TEXT,
            asin TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'new',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    # Compatibility migration for older DBs
    try:
        conn.execute("SELECT phone FROM orders LIMIT 1")
    except sqlite3.DatabaseError:
        conn.execute("ALTER TABLE orders ADD COLUMN phone TEXT")
    try:
        conn.execute("SELECT notes FROM orders LIMIT 1")
    except sqlite3.DatabaseError:
        conn.execute("ALTER TABLE orders ADD COLUMN notes TEXT")

    if conn.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 0:
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
# Auth
# ------------------------------------------------------------
def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect(url_for("admin_login"))
        return view(*args, **kwargs)

    return wrapped


# ------------------------------------------------------------
# Product/order helpers
# ------------------------------------------------------------
def get_active_products():
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT * FROM products WHERE active = 1 ORDER BY id DESC"
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_all_products():
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM products ORDER BY id DESC").fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_all_orders():
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM orders ORDER BY id DESC LIMIT 200").fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_product_by_id(product_id):
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_product_by_asin(asin):
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM products WHERE asin = ?", (asin,)).fetchone()
    conn.close()
    return dict(row) if row else None


def create_order_record(asin, customer, phone=None, notes=None, status="new"):
    order_id = f"ORD{int(time.time())}"
    conn = get_db_connection()
    conn.execute(
        """
        INSERT INTO orders (order_id, customer, phone, notes, asin, status)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (order_id, customer, phone, notes, asin, status),
    )
    conn.commit()
    conn.close()
    return order_id


def update_order_status(order_id, status):
    conn = get_db_connection()
    conn.execute("UPDATE orders SET status = ? WHERE order_id = ?", (status, order_id))
    conn.commit()
    conn.close()


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
        return payload.get("shortUrl") or amazon_url
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


def send_order_whatsapp_alert(name, phone, product_name, asin, notes=None):
    message = (
        f"New customer order\n"
        f"Name: {name}\n"
        f"Phone: {phone}\n"
        f"Product: {product_name}\n"
        f"ASIN: {asin}\n"
    )
    if notes:
        message += f"Notes: {notes}\n"
    message += f"WA: {WHATSAPP_NUMBER}"
    return whatsapp_send_message(message)


# ------------------------------------------------------------
# Views: public endpoints
# ------------------------------------------------------------
@app.route("/")
def home():
    return {
        "status": "online",
        "whatsapp": WHATSAPP_NUMBER,
        "products": len(get_active_products()),
        "orders": len(get_all_orders()),
        "time": datetime.now().isoformat(),
        "routes": [
            "/genius?asin=...",
            "/wa-status?asin=...",
            "/tg-buyer?asin=...&cust=...",
            "/order?asin=...&cust=...",
            "/api/products",
            "/api/orders",
            "/admin/login",
        ],
    }


@app.route("/healthz")
def healthz():
    return {"status": "ok"}


@app.route("/genius")
def genius():
    asin = request.args.get("asin", DEFAULT_ASIN)
    in_link, us_link = amazon_links(asin)
    return {
        "asin": asin,
        "geni_us": genius_short_url(asin),
        "amazon_in": in_link,
        "amazon_us": us_link,
        "whatsapp": WHATSAPP_NUMBER,
    }


@app.route("/wa-status")
def wa_status():
    asin = request.args.get("asin", DEFAULT_ASIN)
    products = get_active_products()
    product = next((p for p in products if p["asin"] == asin), products[0] if products else None)
    if not product:
        return {"error": "No active products found"}, 404

    status_text = f"STATUS {product['title']} {genius_short_url(asin)} WA {WHATSAPP_NUMBER}"
    whatsapp_send_message(status_text)
    return {"status": "sent", "product": product["title"], "recipient": WHATSAPP_NUMBER}


@app.route("/tg-buyer")
def tg_buyer():
    asin = request.args.get("asin", DEFAULT_ASIN)
    customer = request.args.get("cust", "Customer")
    products = get_active_products()
    product = next((p for p in products if p["asin"] == asin), products[0] if products else None)
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
    whatsapp_link = wa_message_link(f"Order {order_id} {asin} by {customer}")
    return {
        "order_id": order_id,
        "customer": customer,
        "asin": asin,
        "wa_link": whatsapp_link,
    }


@app.route("/api/order-intake", methods=["POST"])
def api_order_intake():
    data = request.form or request.get_json(silent=True) or {}
    name = (data.get("name") or data.get("customer") or "Customer").strip()
    phone = (data.get("phone") or "").strip()
    asin = (data.get("asin") or DEFAULT_ASIN).strip()
    notes = (data.get("notes") or "").strip()

    product = get_product_by_asin(asin)
    if not product:
        return {"error": "ASIN not found"}, 404

    order_id = create_order_record(asin, name, phone=phone, notes=notes)
    send_order_whatsapp_alert(name, phone or "Not provided", product["title"], asin, notes)
    return {
        "status": "created",
        "order_id": order_id,
        "product": product["title"],
        "customer": name,
        "phone": phone,
    }, 201


# ------------------------------------------------------------
# Admin login + dashboard
# ------------------------------------------------------------
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session["admin_logged_in"] = True
            return redirect(url_for("admin_dashboard"))
        return render_template_string(
            """
            <html><body style='font-family: Arial; padding: 40px;'>
            <h2>Admin Login</h2>
            <form method='POST'>
              <p><input name='username' placeholder='Username' required></p>
              <p><input name='password' type='password' placeholder='Password' required></p>
              <p><button type='submit'>Login</button></p>
            </form>
            <p style='color: red;'>Invalid username or password.</p>
            </body></html>
            """
        )

    return render_template_string(
        """
        <html><body style='font-family: Arial; padding: 40px;'>
        <h2>Admin Login</h2>
        <form method='POST'>
          <p><input name='username' placeholder='Username' required></p>
          <p><input name='password' type='password' placeholder='Password' required></p>
          <p><button type='submit'>Login</button></p>
        </form>
        </body></html>
        """
    )


@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_logged_in", None)
    return redirect(url_for("admin_login"))


@app.route("/admin")
@admin_required
def admin_dashboard():
    products = get_all_products()
    orders = get_all_orders()
    return render_template_string(
        """
        <html>
          <head>
            <title>Affiliate Bot Admin</title>
            <style>
              body { font-family: Arial, sans-serif; margin: 24px; background: #f5f7fb; }
              .card { background: white; border-radius: 12px; padding: 18px; margin-bottom: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); }
              .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
              table { width: 100%; border-collapse: collapse; }
              th, td { padding: 10px; text-align: left; border-bottom: 1px solid #eee; }
              input, textarea, button, select { width: 100%; padding: 9px; margin: 5px 0; box-sizing: border-box; }
              button { border: none; border-radius: 8px; background: #1f6feb; color: white; cursor: pointer; }
              .small-btn { background: #12a454; }
              .danger { background: #d93025; }
              .link { display: inline-block; margin: 8px 12px 8px 0; }
              a { color: #1f6feb; text-decoration: none; }
            </style>
          </head>
          <body>
            <h1>Affiliate Bot Admin</h1>
            <p><a href="/admin/logout">Logout</a></p>

            <div class="grid">
              <div class="card">
                <h2>Add Product</h2>
                <form method="POST" action="/api/products">
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
                <tr><th>ID</th><th>Title</th><th>Price</th><th>ASIN</th><th>Status</th><th>Actions</th></tr>
                {% for product in products %}
                <tr>
                  <td>{{ product['id'] }}</td>
                  <td>{{ product['title'] }}</td>
                  <td>{{ product['price'] }}</td>
                  <td>{{ product['asin'] }}</td>
                  <td>{{ 'Active' if product['active'] else 'Inactive' }}</td>
                  <td>
                    <a href="/admin/products/{{ product['id'] }}/edit">Edit</a> |
                    <form style="display:inline" method="POST" action="/admin/products/{{ product['id'] }}/toggle">
                      <button class="small-btn" type="submit">{{ 'Disable' if product['active'] else 'Enable' }}</button>
                    </form>
                    |
                    <form style="display:inline" method="POST" action="/admin/products/{{ product['id'] }}/delete" onsubmit="return confirm('Delete this product?');">
                      <button class="danger" type="submit">Delete</button>
                    </form>
                  </td>
                </tr>
                {% endfor %}
              </table>
            </div>

            <div class="card">
              <h2>Orders</h2>
              <table>
                <tr><th>ID</th><th>Order ID</th><th>Customer</th><th>Phone</th><th>ASIN</th><th>Status</th></tr>
                {% for order in orders %}
                <tr>
                  <td>{{ order['id'] }}</td>
                  <td>{{ order['order_id'] }}</td>
                  <td>{{ order['customer'] }}</td>
                  <td>{{ order['phone'] or '—' }}</td>
                  <td>{{ order['asin'] }}</td>
                  <td>{{ order['status'] }}</td>
                </tr>
                {% endfor %}
              </table>
            </div>
          </body>
        </html>
        """,
        products=products,
        orders=orders,
    )


@app.route("/admin/products/<int:product_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_product(product_id):
    product = get_product_by_id(product_id)
    if not product:
        return "Product not found", 404

    if request.method == "POST":
        title = request.form.get("title", product["title"]).strip()
        price = request.form.get("price", product["price"]).strip()
        asin = request.form.get("asin", product["asin"]).strip()
        image_url = request.form.get("image_url", product.get("image_url") or "").strip()
        description = request.form.get("description", product.get("description") or "").strip()
        active = 1 if request.form.get("active") == "on" else 0

        conn = get_db_connection()
        conn.execute(
            """
            UPDATE products
            SET title = ?, price = ?, asin = ?, image_url = ?, description = ?, active = ?
            WHERE id = ?
            """,
            (title, price, asin, image_url, description, active, product_id),
        )
        conn.commit()
        conn.close()
        return redirect(url_for("admin_dashboard"))

    return render_template_string(
        """
        <html><body style='font-family: Arial; padding: 30px;'>
        <h2>Edit Product</h2>
        <form method='POST'>
          <p><input name='title' value='{{ product["title"] }}' required></p>
          <p><input name='price' value='{{ product["price"] }}' required></p>
          <p><input name='asin' value='{{ product["asin"] }}' required></p>
          <p><input name='image_url' value='{{ product.get("image_url") or "" }}'></p>
          <p><textarea name='description'>{{ product.get("description") or "" }}</textarea></p>
          <p><label><input type='checkbox' name='active' {% if product['active'] %}checked{% endif %}> Active</label></p>
          <p><button type='submit'>Save Changes</button></p>
        </form>
        <p><a href='/admin'>Back to dashboard</a></p>
        </body></html>
        """,
        product=product,
    )


@app.route("/admin/products/<int:product_id>/delete", methods=["POST"])
@admin_required
def delete_product(product_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/products/<int:product_id>/toggle", methods=["POST"])
@admin_required
def toggle_product(product_id):
    product = get_product_by_id(product_id)
    if not product:
        return "Product not found", 404

    conn = get_db_connection()
    conn.execute("UPDATE products SET active = ? WHERE id = ?", (0 if product["active"] else 1, product_id))
    conn.commit()
    conn.close()
    return redirect(url_for("admin_dashboard"))


# ------------------------------------------------------------
# API endpoints
# ------------------------------------------------------------
@app.route("/api/products", methods=["GET", "POST"])
def api_products():
    if request.method == "GET":
        return jsonify(get_all_products())

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


@app.route("/api/products/<int:product_id>", methods=["GET", "PUT", "DELETE"])
def api_product_detail(product_id):
    product = get_product_by_id(product_id)
    if not product:
        return {"error": "Product not found"}, 404

    if request.method == "GET":
        return jsonify(product)

    if request.method == "PUT":
        data = request.form or request.get_json(silent=True) or {}
        title = (data.get("title") or product["title"]).strip()
        price = (data.get("price") or product["price"]).strip()
        asin = (data.get("asin") or product["asin"]).strip()
        image_url = (data.get("image_url") or product.get("image_url") or "").strip()
        description = (data.get("description") or product.get("description") or "").strip()
        active = int(data.get("active", product["active"]))

        conn = get_db_connection()
        conn.execute(
            """
            UPDATE products
            SET title = ?, price = ?, asin = ?, image_url = ?, description = ?, active = ?
            WHERE id = ?
            """,
            (title, price, asin, image_url, description, active, product_id),
        )
        conn.commit()
        conn.close()
        return {"status": "updated", "id": product_id}

    if request.method == "DELETE":
        conn = get_db_connection()
        conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
        conn.commit()
        conn.close()
        return {"status": "deleted", "id": product_id}


@app.route("/api/orders", methods=["GET", "POST"])
def api_orders():
    if request.method == "GET":
        return jsonify(get_all_orders())

    data = request.form or request.get_json(silent=True) or {}
    asin = (data.get("asin") or DEFAULT_ASIN).strip()
    customer = (data.get("customer") or data.get("cust") or "Customer").strip()
    phone = (data.get("phone") or "").strip()
    notes = (data.get("notes") or "").strip()
    order_id = create_order_record(asin, customer, phone=phone, notes=notes)
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





























































