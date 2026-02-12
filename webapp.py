from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import functools
import threading
import schedule
import time
import ccxt
from config import get_assets, add_asset, remove_asset, get_current_status
from main import check_indicators, send_weekly_summary, run_scheduler

app = Flask(__name__)
app.secret_key = 'super_secret_key_change_this_in_prod' # In a real app, use env var

# Simple hardcoded credentials
USERS = {
    "admin": "password123" # Change this!
}

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
        if USERS.get(username) == password:
            session['user'] = username
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error="Invalid credentials")
    return render_template('login.html')

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
            "last_check": s.get("last_check", "Never")
        })
    return render_template('dashboard.html', assets=display_assets)

@app.route('/api/search_assets')
@login_required
def search_assets():
    query = request.args.get('q', '').upper()
    if not query:
        return jsonify([])
    
    # This is heavy, in production cache markets
    # For now we search in popular exchanges only
    results = []
    exchanges = ['binance', 'hyperliquid', 'bybit', 'coinbase']
    
    for ex_name in exchanges:
        try:
            exchange_class = getattr(ccxt, ex_name)
            exchange = exchange_class()
            # We can't load all markets every request.
            # Ideally load once globally or on startup.
            # Optimizing: Just return valid format suggestion if query looks complete?
            # Or use a lighter check. 
            # For this simple app, we might rely on user knowing the symbol or 
            # try to fetch ticker for the query to validate.
            
            # Let's try to fetch ticker if query looks like a symbol
            # This is slow and rate limited. 
            # Better approach: Just let user type exchange and symbol managed by client side logic 
            # or partial matching if we load markets.
            pass
        except:
             pass
    
    # Simplified: return dummy suggestions or require manual input for now
    # Implementing full CCXT search is complex due to API limits and size.
    # We will return the query as a suggestion to add
    return jsonify([
        {"exchange": "binance", "symbol": f"{query}/USDT"},
        {"exchange": "hyperliquid", "symbol": f"{query}/USDC:USDC"}
    ])

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
    
    return app
