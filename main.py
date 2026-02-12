import time
import schedule
from datetime import datetime
import traceback
import sys
import threading

# Import data fetchers dynamically or use a map
from data_fetcher import fetch_btc_daily, fetch_hyperliquid_hype_daily
from indicator import calculate_larsson_line
from config import update_asset_state, get_assets, get_current_status, CONFIG_FILE
from email_notifier import send_email

# Helper to map generic exchange check to specific functions
# In a real dynamic system, we'd use ccxt generic fetching, but relying on existing specific functions 
# implies we might need a generic wrapper if we want to support ANY symbol.
# For now, let's assume we implement a generic fetcher or map specific known ones.
# The user asked to add assets via search, implying a generic fetcher is needed.
# Converting data_fetcher to be more generic is required.

import ccxt
import pandas as pd

def fetch_generic_daily(exchange_id: str, symbol: str, limit: int = 100) -> pd.DataFrame:
    """
    Generic fetcher for any CCXT exchange.
    """
    try:
        # Special handling for hyperliquid if needed, but ccxt should handle it
        if exchange_id == 'hyperliquid' and 'HYPE' in symbol:
             # Fallback to the specific function if needed or rely on ccxt
             pass

        exchange_class = getattr(ccxt, exchange_id)
        exchange = exchange_class({'enableRateLimit': True})
        
        # CCXT expects symbols often in specific formats, UI should provide valid ones
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe='1d', limit=limit)
        
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        return df
    except Exception as e:
        print(f"Error fetching {symbol} from {exchange_id}: {e}")
        raise

def check_indicators():
    """
    Check indicators for all configured assets.
    """
    print(f"[{datetime.now()}] Checking indicators...")
    assets = get_assets()
    
    for asset in assets:
        exchange = asset['exchange']
        symbol = asset['symbol']
        
        try:
            # Fetch data
            df = fetch_generic_daily(exchange, symbol, limit=50)
            
            # Calculate Indicator
            df = calculate_larsson_line(df)
            last_row = df.iloc[-1]
            current_color = last_row['color']
            current_price = last_row['close']
            
            print(f"{exchange.upper()} {symbol}: {current_color} (${current_price})")
            
            # Update State
            prev_color = update_asset_state(exchange, symbol, current_color, current_price)
            
            # Alert if changed
            if prev_color and prev_color != current_color:
                subject = f"Market Alert: {symbol} on {exchange.upper()} Changed to {current_color.upper()}"
                body = f"""
                Indicator Update:
                
                Asset: {symbol} ({exchange.upper()})
                New Status: {current_color.upper()}
                Previous Status: {prev_color.upper()}
                Current Price: ${current_price}
                Timestamp: {datetime.now()}
                """
                send_email(subject, body)
                
        except Exception as e:
            print(f"Error processing {exchange} {symbol}: {e}")
            # Don't print stack trace for every failed symbol to keep logs clean, unless debug
            # traceback.print_exc()

def send_weekly_summary():
    """
    Send a summary email with the current status of all indicators.
    """
    print(f"[{datetime.now()}] Sending weekly summary...")
    try:
        status = get_current_status() # dict of "exchange_symbol" -> {color, price, ...}
        assets = get_assets()
        
        body = f"Weekly Trading Indicator Summary\nTimestamp: {datetime.now()}\n\n"
        
        if not assets:
            body += "No assets configured."
        
        for asset in assets:
            key = f"{asset['exchange']}_{asset['symbol']}"
            asset_status = status.get(key, {})
            
            body += f"--- {asset['symbol']} ({asset['exchange'].upper()}) ---\n"
            body += f"Status: {asset_status.get('color', 'Unknown').upper()}\n"
            body += f"Last Price: ${asset_status.get('price', 'N/A')}\n"
            body += f"Last Check: {asset_status.get('last_check', 'Never')}\n\n"
        
        send_email("Weekly Trading Indicator Summary", body)
        
    except Exception as e:
        print(f"Error sending weekly summary: {e}")
        traceback.print_exc()

def run_scheduler():
    """Function to run the scheduler in a separate thread/process."""
    print("Scheduler started.")
    
    # Schedule checks 4x daily
    schedule.every().day.at("08:00").do(check_indicators)
    schedule.every().day.at("12:00").do(check_indicators)
    schedule.every().day.at("16:00").do(check_indicators)
    schedule.every().day.at("20:00").do(check_indicators)
    
    # Schedule weekly summary (Monday 10:00 AM)
    schedule.every().monday.at("10:00").do(send_weekly_summary)
    
    while True:
        schedule.run_pending()
        time.sleep(60)

# Main entry point is now likely webapp.py, but we keep this for testing or standalone usage
def main():
    print("Starting Trading Alert Logic...")
    
    if not CONFIG_FILE.exists():
        print("First run detected (no config). Sending test email...")
        send_email("Trading Alert Server Installed", "The trading alert service has been successfully installed.")
    
    # Initial check
    check_indicators()
    
    # Run scheduler
    run_scheduler()

if __name__ == "__main__":
    main()
