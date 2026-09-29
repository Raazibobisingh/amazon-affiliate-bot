# Affiliate Bot Project

This project is an automated affiliate marketing bot built with Flask. It supports:

- Amazon ASIN link generation
- Genius short-link conversion helper
- WhatsApp sending via CallMeBot
- Telegram message and photo posting
- Facebook photo posting
- SQLite-backed product and order management
- Admin dashboard and JSON APIs
- Scheduled background posting loop

## Features

- Product catalog stored in SQLite
- Order tracking for customer requests
- Easy product management through `/api/products`
- JSON access to orders at `/api/orders`
- Admin dashboard at `/admin`
- Built-in endpoints for status, buyer messages, and order creation
- Production-friendly environment variable setup

## Project structure

- `app.py` - main Flask application
- `bot.py` - compatibility wrapper
- `.env.example` - environment variable template
- `requirements.txt` - Python dependencies
- `.gitignore` - project ignores

## Quick start

1. Create a virtual environment:

   python -m venv .venv
   source .venv/bin/activate

2. Install dependencies:

   pip install -r requirements.txt

3. Copy the example environment file:

   cp .env.example .env

4. Fill in the values in `.env`.

5. Run the app:

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

## Routes

- `/` - basic app status
- `/healthz` - health check
- `/genius?asin=...` - get Amazon and Genius links
- `/wa-status?asin=...` - send a WhatsApp status
- `/tg-buyer?asin=...&cust=...` - send buyer info to Telegram
- `/order?asin=...&cust=...` - create an order record
- `/admin` - browser-based admin dashboard
- `/api/products` - list or add products
- `/api/orders` - list or create orders

## Admin dashboard

Open the browser to:

- `http://localhost:8080/admin`

You can add products through the form or use the JSON API to manage them.

## Deployment

This app is ready for simple deployment on services like Render, Railway, or a Linux VPS.

Example Render setup:

- Build command: `pip install -r requirements.txt`
- Start command: `python app.py`
- Add your environment variables in the dashboard

## Notes

- The app uses SQLite for local data storage.
- Some integrations require real credentials from Telegram, Facebook, and CallMeBot.
- The auto-post loop can be disabled by setting `AUTO_POST_INTERVAL` to a large value or by removing the thread if you only want manual triggers.



































