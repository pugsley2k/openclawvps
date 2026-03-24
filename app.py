import os
import sqlite3
import threading
import time
import requests
import base64
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
from bs4 import BeautifulSoup

load_dotenv()

app = Flask(__name__)
app.config['DATABASE'] = 'pokemon_watchlist.db'

# Configuration
EBAY_CLIENT_ID = os.getenv('EBAY_CLIENT_ID', 'your_ebay_client_id')
EBAY_CLIENT_SECRET = os.getenv('EBAY_CLIENT_SECRET', 'your_ebay_client_secret')
EBAY_TOKEN_URL = 'https://api.auth.ebay.com/oauth2/token'
EBAY_SEARCH_URL = 'https://api.ebay.com/buy/browse/v1/item_summary/search'

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', 'placeholder')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', 'placeholder')

POKEMON_TCG_API = 'https://api.pokemontcg.io/v2/cards'
VINTED_URL = 'https://www.vinted.co.uk/catalog'

# Global state
ebay_token = None
ebay_token_expiry = 0
scan_running = False

# ==================== DATABASE ====================
def init_db():
    """Initialize SQLite database for watchlist."""
    conn = sqlite3.connect(app.config['DATABASE'])
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS watchlist (
                    id INTEGER PRIMARY KEY,
                    card_name TEXT NOT NULL,
                    card_set TEXT,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    threshold INTEGER DEFAULT 20
                )''')
    c.execute('''CREATE TABLE IF NOT EXISTS deals (
                    id INTEGER PRIMARY KEY,
                    card_name TEXT NOT NULL,
                    source TEXT,
                    listing_title TEXT,
                    price REAL,
                    market_price REAL,
                    discount_percent REAL,
                    url TEXT,
                    found_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )''')
    conn.commit()
    conn.close()

def get_db():
    """Get database connection."""
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    return conn

# ==================== EBAY API ====================
def get_ebay_token():
    """Get OAuth2 access token from eBay."""
    global ebay_token, ebay_token_expiry
    
    # Return cached token if still valid
    if ebay_token and time.time() < ebay_token_expiry:
        return ebay_token
    
    auth_string = f"{EBAY_CLIENT_ID}:{EBAY_CLIENT_SECRET}"
    auth_bytes = auth_string.encode('ascii')
    auth_base64 = base64.b64encode(auth_bytes).decode('ascii')
    
    headers = {
        'Authorization': f'Basic {auth_base64}',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    
    data = {'grant_type': 'client_credentials', 'scope': 'https://api.ebay.com/oauth/api_scope/buy.browse'}
    
    try:
        response = requests.post(EBAY_TOKEN_URL, headers=headers, data=data, timeout=10)
        if response.status_code == 200:
            token_data = response.json()
            ebay_token = token_data['access_token']
            ebay_token_expiry = time.time() + token_data['expires_in'] - 300  # Refresh 5 min early
            return ebay_token
    except Exception as e:
        print(f"Error getting eBay token: {e}")
    
    return None

def search_ebay(card_name, threshold=20):
    """Search eBay for card listings."""
    token = get_ebay_token()
    if not token:
        return []
    
    headers = {'Authorization': f'Bearer {token}'}
    params = {
        'q': card_name,
        'fieldgroups': 'FULL',
        'limit': '50',
        'marketplaceId': 'EBAY_GB',
        'filter': 'priceCurrency:GBP'
    }
    
    results = []
    try:
        response = requests.get(EBAY_SEARCH_URL, headers=headers, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            for item in data.get('itemSummaries', []):
                listing = {
                    'source': 'eBay',
                    'title': item.get('title', 'N/A'),
                    'price': item.get('price', {}).get('value', 0),
                    'currency': item.get('price', {}).get('currency', 'GBP'),
                    'url': item.get('itemWebUrl', ''),
                    'condition': item.get('condition', 'Unknown')
                }
                results.append(listing)
    except Exception as e:
        print(f"Error searching eBay: {e}")
    
    return results

# ==================== POKEMON TCG API ====================
def get_market_price(card_name):
    """Get market price from Pokemon TCG API."""
    try:
        params = {'q': f'name:{card_name}'}
        response = requests.get(POKEMON_TCG_API, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('data'):
                card = data['data'][0]
                
                # Try cardmarket price first (EUR), then TCGPlayer (USD)
                cardmarket_price = card.get('cardmarket', {}).get('prices', {}).get('averageSellPrice')
                if cardmarket_price:
                    return {'price': cardmarket_price, 'currency': 'EUR', 'source': 'CardMarket'}
                
                tcgplayer_price = card.get('tcgplayer', {}).get('prices', {}).get('normal', {}).get('market')
                if tcgplayer_price:
                    return {'price': tcgplayer_price, 'currency': 'USD', 'source': 'TCGPlayer'}
    except Exception as e:
        print(f"Error fetching market price: {e}")
    
    return None

# ==================== VINTED SCRAPING ====================
def search_vinted(card_name, threshold=20):
    """Scrape Vinted.co.uk for card listings."""
    results = []
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
    }
    
    url = f"{VINTED_URL}?search_text={card_name.replace(' ', '+')}"
    
    try:
        time.sleep(1)  # Be polite to Vinted
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Parse Vinted listings (adjust selectors as needed)
            items = soup.find_all('a', class_='item-box')
            
            for item in items[:20]:  # Limit to 20 results
                try:
                    title_elem = item.find('p', class_='item-title')
                    price_elem = item.find('p', class_='item-price')
                    
                    if title_elem and price_elem:
                        title = title_elem.get_text(strip=True)
                        price_text = price_elem.get_text(strip=True)
                        
                        # Parse price (e.g., "£12.50")
                        price = 0
                        try:
                            price = float(price_text.replace('£', '').replace(',', '').strip())
                        except:
                            pass
                        
                        listing = {
                            'source': 'Vinted',
                            'title': title,
                            'price': price,
                            'currency': 'GBP',
                            'url': item.get('href', ''),
                            'condition': 'Unknown'
                        }
                        results.append(listing)
                except Exception as e:
                    print(f"Error parsing Vinted item: {e}")
    
    except Exception as e:
        print(f"Error scraping Vinted: {e}")
    
    return results

# ==================== TELEGRAM ALERTS ====================
def send_telegram_alert(card_name, deals):
    """Send deal alerts via Telegram."""
    if TELEGRAM_BOT_TOKEN == 'placeholder' or TELEGRAM_CHAT_ID == 'placeholder':
        print(f"[Telegram] Placeholder credentials - would send alert for {card_name}")
        return
    
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        
        message = f"🔥 *Deal Found!* 🔥\n\n*Card:* {card_name}\n\n"
        for deal in deals[:3]:  # Top 3 deals
            discount = deal.get('discount_percent', 0)
            message += f"📍 {deal['source']}: £{deal['price']:.2f} (-{discount:.1f}%)\n"
            message += f"   {deal['url']}\n\n"
        
        payload = {
            'chat_id': TELEGRAM_CHAT_ID,
            'text': message,
            'parse_mode': 'Markdown'
        }
        
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            print(f"[Telegram] Alert sent for {card_name}")
    except Exception as e:
        print(f"Error sending Telegram alert: {e}")

# ==================== BACKGROUND SCANNER ====================
def auto_scan_watchlist():
    """Background thread that scans watchlist every 60 minutes."""
    global scan_running
    
    while scan_running:
        try:
            conn = get_db()
            c = conn.cursor()
            c.execute('SELECT id, card_name, threshold FROM watchlist')
            cards = c.fetchall()
            conn.close()
            
            for card in cards:
                card_name = card['card_name']
                threshold = card['threshold']
                
                # Get market price
                market_data = get_market_price(card_name)
                if not market_data:
                    continue
                
                market_price = market_data['price']
                
                # Search eBay and Vinted
                ebay_listings = search_ebay(card_name, threshold)
                vinted_listings = search_vinted(card_name, threshold)
                all_listings = ebay_listings + vinted_listings
                
                # Find deals
                deals = []
                for listing in all_listings:
                    price = listing['price']
                    discount = ((market_price - price) / market_price) * 100 if market_price > 0 else 0
                    
                    if discount >= threshold:
                        deals.append({
                            'source': listing['source'],
                            'title': listing['title'],
                            'price': price,
                            'market_price': market_price,
                            'discount_percent': discount,
                            'url': listing['url']
                        })
                
                # Save deals and send alerts
                if deals:
                    conn = get_db()
                    c = conn.cursor()
                    for deal in deals:
                        c.execute('''INSERT INTO deals 
                                     (card_name, source, listing_title, price, market_price, discount_percent, url)
                                     VALUES (?, ?, ?, ?, ?, ?, ?)''',
                                  (card_name, deal['source'], deal['title'], deal['price'],
                                   deal['market_price'], deal['discount_percent'], deal['url']))
                    conn.commit()
                    conn.close()
                    
                    send_telegram_alert(card_name, deals)
                
                time.sleep(2)  # Be polite to APIs
            
            print(f"[Auto-scan] Watchlist scanned at {datetime.now()}")
        except Exception as e:
            print(f"Error in auto-scan: {e}")
        
        # Sleep for 60 minutes
        time.sleep(3600)

def start_background_scanner():
    """Start the background scanner thread."""
    global scan_running
    if not scan_running:
        scan_running = True
        thread = threading.Thread(target=auto_scan_watchlist, daemon=True)
        thread.start()
        print("[Auto-scan] Background scanner started")

# ==================== FLASK ROUTES ====================
@app.route('/')
def index():
    """Render main dashboard."""
    return render_template('index.html')

@app.route('/api/search', methods=['POST'])
def api_search():
    """Search for card on eBay and Vinted."""
    data = request.json
    card_name = data.get('card_name', '')
    threshold = data.get('threshold', 20)
    
    if not card_name:
        return jsonify({'error': 'Card name required'}), 400
    
    # Get market price
    market_data = get_market_price(card_name)
    
    # Search both platforms
    ebay_results = search_ebay(card_name, threshold)
    vinted_results = search_vinted(card_name, threshold)
    
    # Enrich with discount info
    for listing in ebay_results + vinted_results:
        if market_data:
            market_price = market_data['price']
            listing['market_price'] = market_price
            listing['market_currency'] = market_data['currency']
            listing['market_source'] = market_data['source']
            listing['discount_percent'] = ((market_price - listing['price']) / market_price * 100) if market_price > 0 else 0
    
    return jsonify({
        'ebay': ebay_results,
        'vinted': vinted_results,
        'market_price': market_data
    })

@app.route('/api/watchlist', methods=['GET', 'POST', 'DELETE'])
def api_watchlist():
    """Manage watchlist."""
    conn = get_db()
    c = conn.cursor()
    
    if request.method == 'GET':
        c.execute('SELECT id, card_name, card_set, threshold, added_at FROM watchlist ORDER BY added_at DESC')
        items = [dict(row) for row in c.fetchall()]
        conn.close()
        return jsonify(items)
    
    elif request.method == 'POST':
        data = request.json
        card_name = data.get('card_name', '')
        card_set = data.get('card_set', '')
        threshold = data.get('threshold', 20)
        
        if not card_name:
            conn.close()
            return jsonify({'error': 'Card name required'}), 400
        
        # Check if already in watchlist
        c.execute('SELECT id FROM watchlist WHERE card_name = ? AND card_set = ?', (card_name, card_set))
        if c.fetchone():
            conn.close()
            return jsonify({'error': 'Card already in watchlist'}), 400
        
        c.execute('''INSERT INTO watchlist (card_name, card_set, threshold)
                     VALUES (?, ?, ?)''', (card_name, card_set, threshold))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Card added to watchlist'})
    
    elif request.method == 'DELETE':
        data = request.json
        card_id = data.get('id')
        
        if not card_id:
            conn.close()
            return jsonify({'error': 'ID required'}), 400
        
        c.execute('DELETE FROM watchlist WHERE id = ?', (card_id,))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Card removed from watchlist'})

@app.route('/api/deals', methods=['GET'])
def api_deals():
    """Get recent deals."""
    conn = get_db()
    c = conn.cursor()
    c.execute('''SELECT * FROM deals ORDER BY found_at DESC LIMIT 100''')
    deals = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify(deals)

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({'status': 'ok', 'port': 5000, 'app': 'Pokemon Card Bargain Finder'})

# ==================== MAIN ====================
if __name__ == '__main__':
    print("=" * 60)
    print("🔍 Pokemon Card Bargain Finder")
    print("=" * 60)
    
    # Initialize database
    init_db()
    print("✅ Database initialized")
    
    # Start background scanner
    start_background_scanner()
    print("✅ Background scanner started (60-minute intervals)")
    
    print(f"📍 Starting Flask app on http://0.0.0.0:5000")
    print("=" * 60)
    
    # Run Flask app
    app.run(host='0.0.0.0', port=5000, debug=False)
