from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import functools
import threading
import schedule
import time
import ccxt
from config import get_assets, add_asset, remove_asset, get_current_status, get_admin_password, set_admin_password
from main import check_indicators, send_weekly_summary, run_scheduler

app = Flask(__name__)
app.secret_key = 'super_secret_key_change_this_in_prod' # In a real app, use env var

def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if session.get('user') is None:
            return redirect(url_for('login'))
        return view(**kwargs)
    return wrapped_view

@app.route('/login', methods=('GET', 'POST'))
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Only support 'admin' user for now
        if username == 'admin' and password == get_admin_password():
            session['user'] = username
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error="Invalid credentials")
    return render_template('login.html')

@app.route('/api/change_password', methods=['POST'])
@login_required
def api_change_password():
    data = request.json
    new_password = data.get('new_password')
    if new_password:
        set_admin_password(new_password)
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "Password cannot be empty"}), 400

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def dashboard():
    assets = get_assets()
    status = get_current_status()
    # Enrich asset list with status
    display_assets = []
    for asset in assets:
        key = f"{asset['exchange']}_{asset['symbol']}"
        s = status.get(key, {})
        display_assets.append({
            "exchange": asset['exchange'],
            "symbol": asset['symbol'],
            "color": s.get("color", "Unknown"),
            "price": s.get("price", "-"),
            "change_24h": s.get("change_24h", 0),
            "history_7d": s.get("history_7d", []),
            "last_check": s.get("last_check", "Never")
        })
    return render_template('dashboard.html', assets=display_assets)

# --- Market Data Cache ---
class MarketIndexer:
    def __init__(self):
        self.markets = []
        self.lock = threading.Lock()
        self.is_loading = False
        self.exchanges_to_index = ['binance', 'bybit', 'kraken', 'coinbase', 'okx']
        # Hyperliquid is special in CCXT, check availability or add manually if needed
        # For now we stick to standard ccxt structure
        
    def start_indexing(self):
        t = threading.Thread(target=self._index_worker)
        t.daemon = True
        t.start()
        
    def _index_worker(self):
        print("Starting market indexing...")
        self.is_loading = True
        all_markets = []
        
        # Add Hyperliquid manually or via custom call if ccxt support is limited/different
        # CCXT supports hyperliquid now, let's try standard fetch
        # but mix in explicit list if needed.
        exchanges = self.exchanges_to_index + ['hyperliquid']
        
        for ex_name in exchanges:
            try:
                if not hasattr(ccxt, ex_name):
                    continue
                    
                exchange = getattr(ccxt, ex_name)()
                try:
                    markets = exchange.load_markets()
                    # Flatten to list
                    for symbol, data in markets.items():
                        # We want: symbol, exchange, type (spot/swap)
                        all_markets.append({
                            "symbol": symbol,
                            "exchange": ex_name,
                            "type": data.get('type', 'spot'),
                            "base": data.get('base', ''),
                            "quote": data.get('quote', '')
                        })
                except Exception as e:
                    print(f"Failed to load markets for {ex_name}: {e}")
                finally:
                    exchange.close()
            except Exception as e:
                print(f"Error init exchange {ex_name}: {e}")
                
        with self.lock:
            self.markets = all_markets
            self.is_loading = False
        print(f"Market indexing complete. {len(self.markets)} markets found.")

    def search(self, query):
        query = query.upper()
        if not query:
            return []
            
        with self.lock:
            if self.is_loading and not self.markets:
                return [{"symbol": "Loading markets...", "exchange": "System", "description": "Please wait"}]
            
            # Simple linear search - can be optimized
            results = []
            count = 0
            for m in self.markets:
                if query in m['symbol'].upper().replace('/', ''):
                     results.append(m)
                     count += 1
                     if count >= 20: break
            return results

indexer = MarketIndexer()

@app.route('/api/search_assets')
@login_required
def search_assets():
    query = request.args.get('q', '')
    results = indexer.search(query)
    return jsonify(results)

@app.route('/api/add_asset', methods=['POST'])
@login_required
def api_add_asset():
    data = request.json
    exchange = data.get('exchange')
    symbol = data.get('symbol')
    if exchange and symbol:
        add_asset(exchange, symbol)
        # Trigger an immediate check for this asset?
        threading.Thread(target=check_indicators).start()
        return jsonify({"success": True})
    return jsonify({"success": False}), 400

@app.route('/api/delete_asset', methods=['POST'])
@login_required
def api_delete_asset():
    data = request.json
    exchange = data.get('exchange')
    symbol = data.get('symbol')
    if exchange and symbol:
        remove_asset(exchange, symbol)
        return jsonify({"success": True})
    return jsonify({"success": False}), 400

@app.route('/api/trigger_check', methods=['POST'])
@login_required
def trigger_check():
    threading.Thread(target=check_indicators).start()
    return jsonify({"success": True, "message": "Check triggered"})

# Background Scheduler Thread
def start_scheduler():
    # Loop indefinitely
    while True:
        schedule.run_pending()
        time.sleep(1)

# Initialize Scheduler
# We need to ensure this runs only once, Gunicorn might spawn multiple workers.
# With Gunicorn, simpler to run scheduler as a separate process or use a lock.
# For this setup: We will start it in the main block if run directly,
# OR we rely on a separate service for scheduling if using multiple workers.
# BUT, simplest for single-server app:
# Use specific flag or lock file to ensure one scheduler.
# OR just run app with 1 worker.

if __name__ == '__main__':
    # Dev mode
    # Init scheduler
    schedule.every().day.at("08:00").do(check_indicators)
    schedule.every().day.at("12:00").do(check_indicators)
    schedule.every().day.at("16:00").do(check_indicators)
    schedule.every().day.at("20:00").do(check_indicators)
    schedule.every().monday.at("10:00").do(send_weekly_summary)
    
    t = threading.Thread(target=start_scheduler)
    t.daemon = True
    t.start()
    
    indexer.start_indexing()
    
    app.run(host='0.0.0.0', port=5000, debug=True)

# Gunicorn entry point hook
def create_app():
    # Setup schedule for production
    # Note: If Gunicorn restarts workers, this might duplicate if not careful.
    # But for a simple app with 1 worker (sufficient here), it's fine.
    schedule.clear()
    schedule.every().day.at("08:00").do(check_indicators)
    schedule.every().day.at("12:00").do(check_indicators)
    schedule.every().day.at("16:00").do(check_indicators)
    schedule.every().day.at("20:00").do(check_indicators)
    schedule.every().monday.at("10:00").do(send_weekly_summary)
    
    t = threading.Thread(target=start_scheduler)
    t.daemon = True
    t.start()
    
    # Start indexer
    indexer.start_indexing()
    
    return app
