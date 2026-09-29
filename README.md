<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Customer Order Form</title>
  <style>
    body {
      margin: 0;
      font-family: Arial, sans-serif;
      background: #f6f9ff;
      display: grid;
      place-items: center;
      min-height: 100vh;
    }
    .wrap {
      width: min(92vw, 720px);
      background: white;
      border-radius: 18px;
      padding: 30px;
      box-shadow: 0 24px 50px rgba(15, 23, 42, 0.08);
    }
    h2 { margin-top: 0; }
    .grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 18px;
    }
    input, select, textarea, button {
      width: 100%;
      box-sizing: border-box;
      padding: 12px;
      margin-top: 8px;
      border-radius: 10px;
      border: 1px solid #dfe7f3;
      font-size: 14px;
    }
    button {
      border: none;
      background: #1f6feb;
      color: white;
      font-weight: 700;
      cursor: pointer;
    }
    .success {
      background: #ecfdf5;
      color: #166534;
      border: 1px solid #bbf7d0;
      border-radius: 10px;
      padding: 12px;
      margin-top: 18px;
    }
    .error { color: #d93025; margin-top: 12px; }
    @media (max-width: 720px) {
      .grid { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <div class="wrap">
    <h2>Customer Order Form</h2>
    {% if success %}
      <div class="success">
        Your order was submitted successfully. Order ID: <strong>{{ order_id }}</strong><br>
        <a href="{{ whatsapp_link }}" target="_blank">Open WhatsApp Order Link</a>
      </div>
    {% endif %}
    {% if error %}<div class="error">{{ error }}</div>{% endif %}
    <form method="POST">
      <div class="grid">
        <div>
          <label>Name</label>
          <input name="name" placeholder="Customer name" required>
        </div>
        <div>
          <label>Phone</label>
          <input name="phone" placeholder="+91 99999 99999">
        </div>
      </div>
      <div style="margin-top: 16px;">
        <label>Product</label>
        <select name="asin" required>
          {% for product in products %}
            <option value="{{ product.asin }}">{{ product.title }} - {{ product.price }}</option>
          {% endfor %}
        </select>
      </div>
      <div style="margin-top: 16px;">
        <label>Notes</label>
        <textarea name="notes" placeholder="Optional notes"></textarea>
      </div>
      <button type="submit" style="margin-top: 20px;">Place Order</button>
    </form>
  </div>
</body>
</html>















































































