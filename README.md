Flask Amazon Affiliate Bot

This project is a Flask-based bot that posts product links and order links to Telegram, Facebook, and WhatsApp while automatically rotating Amazon product offers and generating affiliate-style product messages.

Features
- Amazon affiliate / short-link generation using genius URL helper
- Telegram product posting and buyer message support
- Facebook photo posting support
- WhatsApp send support via CallMeBot
- Auto-posting background loop
- Simple Flask endpoints for status, product links, and order creation

Project structure
- bot.py – main Flask app and bot logic
- requirements.txt – Python dependencies
- .env.example – environment variables template
- README.md – usage docs

Setup
1. Create a virtual environment:
   python -m venv .venv
   source .venv/bin/activate
2. Install dependencies:
   pip install -r requirements.txt
3. Copy environment variables:
   cp .env.example .env
4. Fill in the required values in .env
5. Run the bot:
   python bot.py

Environment variables
- BOT_TOKEN
- CHANNEL_ID
- FB_PAGE_ID
- FB_PAGE_TOKEN
- WHATSAPP_NUMBER
- WHATSAPP_API_KEY
- GENIUS_API
- AMAZON_US_TAG
- AMAZON_IN_TAG
- DEFAULT_ASIN

Routes
- / - home status page
- /genius?asin=... - returns Amazon and Genius links
- /wa-status?asin=... - posts a WhatsApp status update
- /tg-buyer?asin=...&cust=... - sends buyer info to Telegram
- /order?asin=...&cust=... - creates an order reference

Notes
- This project is designed for automation and content promotion workflows.
- Some integrations (Telegram, Facebook, WhatsApp) require valid credentials and permissions.
- The app runs a background thread that auto-posts every 4 hours.












































