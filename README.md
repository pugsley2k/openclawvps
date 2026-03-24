# 🔍 Pokemon Card Bargain Finder

A Flask web app that helps you find the best deals on Pokemon cards across eBay and Vinted by comparing prices to market averages.

## Features

✨ **Card Lookup** - Search by card name and get market prices from Pokemon TCG API  
🛒 **eBay Integration** - Scan eBay UK listings and compare to market price  
💰 **Vinted Scraping** - Track listings on Vinted.co.uk  
📋 **Watchlist** - Save cards to monitor, stored in SQLite  
⚡ **Auto-Scan** - Background thread scans watchlist every 60 minutes  
🔔 **Telegram Alerts** - Get notified when deals are found (optional)  
📊 **Dashboard** - Single-page web UI with search, results, and watchlist  

## Tech Stack

- **Backend**: Python + Flask
- **Frontend**: HTML5 + CSS3 + Vanilla JavaScript
- **Database**: SQLite3
- **APIs**: Pokemon TCG API (free), eBay OAuth2, Vinted web scraping

## Installation

### 1. Clone/Create Project

```bash
cd /data/.openclaw/workspace/pokemon-bargain-finder
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Set Up Environment Variables

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Edit `.env` and update with your credentials:
- **eBay API**: Already filled with test credentials
- **Telegram** (optional): Add your bot token and chat ID to receive deal alerts

### 4. Run the App

```bash
python app.py
```

You should see:
```
============================================================
🔍 Pokemon Card Bargain Finder
============================================================
✅ Database initialized
✅ Background scanner started (60-minute intervals)
📍 Starting Flask app on http://0.0.0.0:5000
============================================================
```

### 5. Access the Web UI

Open your browser and go to:
```
http://localhost:5000
or
http://<your-vps-ip>:5000
```

## Usage

### Search for a Card

1. Enter a card name in the search bar (e.g., "Charizard", "Pikachu EX")
2. Adjust the **Discount Threshold** slider (10-50%) to filter deals
3. Click **Search**
4. Results show eBay and Vinted listings with prices, market price, and discount %

### Add to Watchlist

1. Fill in the watchlist form:
   - Card name (required)
   - Card set (optional)
   - Threshold % (default 20)
2. Click **+ Add to Watchlist**
3. The background scanner will check your watchlist every 60 minutes
4. Any deals found will appear in the **Recent Deals** section
5. If Telegram is configured, you'll get alerts

### View Recent Deals

The **Recent Deals** section shows all deals found by the auto-scanner, with:
- Card name
- Source (eBay or Vinted)
- Price and market comparison
- Discount percentage
- Direct link to listing

## File Structure

```
pokemon-bargain-finder/
├── app.py                 # Flask backend
├── requirements.txt       # Python dependencies
├── .env.example          # Environment variable template
├── README.md             # This file
├── pokemon_watchlist.db  # SQLite database (auto-created)
├── templates/
│   └── index.html        # Main dashboard
└── static/
    ├── style.css         # Styling
    └── app.js            # Frontend JavaScript
```

## API Endpoints

### Search
```
POST /api/search
Body: { "card_name": "Charizard", "threshold": 20 }
```

### Watchlist
```
GET /api/watchlist          # Get all watched cards
POST /api/watchlist         # Add card to watchlist
DELETE /api/watchlist       # Remove card from watchlist
```

### Deals
```
GET /api/deals              # Get all found deals
```

### Health Check
```
GET /health                 # Check app status
```

## Configuration

### eBay API

The app uses OAuth2 Client Credentials flow. Add your eBay API credentials to `.env`:
- **Client ID**: Add your eBay Client ID
- **Client Secret**: Add your eBay Client Secret
- **Marketplace**: EBAY_GB (UK)
- **Currency**: GBP

### Telegram Alerts

To enable Telegram notifications:

1. Create a bot with @BotFather on Telegram
2. Get your chat ID
3. Add to `.env`:
   ```
   TELEGRAM_BOT_TOKEN=your_bot_token
   TELEGRAM_CHAT_ID=your_chat_id
   ```

### Auto-Scan Interval

Edit `app.py` line ~220 to change the scan interval:
```python
time.sleep(3600)  # 60 minutes in seconds
```

## Database Schema

### Watchlist Table
```
- id (PRIMARY KEY)
- card_name (TEXT)
- card_set (TEXT)
- added_at (TIMESTAMP)
- threshold (INTEGER) - default 20%
```

### Deals Table
```
- id (PRIMARY KEY)
- card_name (TEXT)
- source (TEXT) - eBay or Vinted
- listing_title (TEXT)
- price (REAL)
- market_price (REAL)
- discount_percent (REAL)
- url (TEXT)
- found_at (TIMESTAMP)
```

## Troubleshooting

### "Connection refused" to eBay API
- Check your internet connection
- eBay API may be rate-limiting; wait a few minutes and try again

### "No listings found"
- Card name may not exist or have no current listings
- Try a more specific name (e.g., "Charizard EX" instead of "Charizard")

### Telegram alerts not working
- Check that both `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` are set (not "placeholder")
- Verify bot is still active in Telegram

### Database errors
- Delete `pokemon_watchlist.db` and restart app to reinitialize
- Make sure `/data/.openclaw/workspace/pokemon-bargain-finder/` is writable

## Notes

- **Be respectful**: Vinted scraping uses polite delays and User-Agent headers
- **Price currencies**: Market prices may be in EUR or USD; UI will indicate the source
- **Results cache**: Listings are displayed from real-time API calls, not cached
- **Background scanning**: Runs in a daemon thread; safely stops when app exits

## License

Built with ❤️ for Pokemon card hunters!

## Future Enhancements

- [ ] TCGPlayer integration
- [ ] Cardmarket integration
- [ ] Email alerts
- [ ] Deal history/analytics
- [ ] Price tracking charts
- [ ] Mobile app

---

**Questions?** Check the app logs or review the source code. Happy hunting! 🎴
