# Affiliate Bot Project

This project is an automated affiliate marketing bot built with Flask. It includes:

- Amazon ASIN link generation
- Genius short-link conversion helper
- WhatsApp sending via CallMeBot
- Telegram message and photo posting
- Facebook photo posting
- SQLite-backed product and order management
- Admin dashboard with login protection
- Product edit/delete toggling
- Customer order intake flow for WhatsApp automation
- JSON APIs for products and orders
- Scheduled background posting loop
- Deployment configuration for Render / Railway / Linux VPS

## Features

- Product catalog stored in SQLite
- Order tracking for customer requests
- Admin login protection via `ADMIN_USERNAME` and `ADMIN_PASSWORD`
- Add, edit, enable/disable, and delete products from the dashboard
- Quick WhatsApp customer intake and status updates
- Built-in API endpoints for automation and integrations
- Browser admin dashboard at `/admin`
- Render-ready startup configuration

## Project structure

- `app.py` - main Flask application
- `bot.py` - compatibility startup wrapper
- `.env.example` - environment variables template
- `requirements.txt` - dependency list
- `.gitignore` - project ignores
- `Procfile` - Render/Railway deployment hook
- `render.yaml` - Render config
- `railway.json` - Railway config

## Quick start

1. Create a virtual environment:

   python -m venv .venv
   source .venv/bin/activate

2. Install dependencies:

   pip install -r requirements.txt

3. Copy the example environment file:

   cp .env.example .env

4. Fill in the values in `.env`.

5. Start the app:

   python app.py

## Important environment variables

- `BOT_TOKEN` - Telegram bot token
- `CHANNEL_ID` - Telegram chat ID or username
- `FB_PAGE_ID` - Facebook page ID
- `FB_PAGE_TOKEN` - Facebook page access token
- `WHATSAPP_NUMBER` - WhatsApp mobile number with country code
- `WHATSAPP_API_KEY` - CallMeBot API key
- `GENIUS_API` - Genius shortener token if available
- `AMAZON_US_TAG` - Amazon US affiliate tag
- `AMAZON_IN_TAG` - Amazon India affiliate tag
- `DEFAULT_ASIN` - default product ASIN for quick testing
- `AUTO_POST_INTERVAL` - posting loop delay in seconds
- `DATABASE_PATH` - where SQLite DB is stored
- `ADMIN_USERNAME` - admin login username
- `ADMIN_PASSWORD` - admin login password
- `SECRET_KEY` - Flask session secret key

## Admin access

Open:

- `http://localhost:8080/admin/login`

Default credentials:

- Username: `admin`
- Password: `admin123`

Change these immediately in `.env`.

## Routes

- `/` - basic app status
- `/healthz` - health check
- `/genius?asin=...` - get Amazon and Genius links
- `/wa-status?asin=...` - send a WhatsApp status
- `/tg-buyer?asin=...&cust=...` - send buyer info to Telegram
- `/order?asin=...&cust=...` - create an order record
- `/api/order-intake` - customer intake JSON endpoint
- `/admin/login` - admin login page
- `/admin` - protected dashboard
- `/api/products` - list or add products
- `/api/orders` - list or create orders

## Product management

From the admin panel you can:

- add a product
- edit a product
- enable or disable it
- delete it
- view product + order history

## Customer order intake

You can post JSON like this:

```bash
curl -X POST http://localhost:8080/api/order-intake \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John",
    "phone": "+918888888888",
    "asin": "B0D3H6XYZ1",
    "notes": "Gift order"
  }'
```

This creates a DB record and sends an order alert via WhatsApp if the API key is configured.

## Deployment

### Render

The repository includes `render.yaml`.

1. Push this repo to GitHub.
2. Create a new Render Web Service.
3. Connect the repo.
4. Add environment variables from `.env.example`.
5. Deploy.

### Railway

The repository includes `railway.json`.

1. Import the repo into Railway.
2. Add the environment variables.
3. Deploy.

### Linux VPS

Example:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python app.py
```

## Notes

- SQLite stores app data locally.
- Some integrations require real credentials from Telegram, Facebook, and CallMeBot.
- The auto-post loop can be disabled by setting `AUTO_POST_INTERVAL` very high or removing the loop.
- Change the admin credentials in `.env` before exposing the server to the internet.

































