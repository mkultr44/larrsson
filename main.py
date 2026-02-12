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
import yfinance as yf

def fetch_generic_daily(exchange_id: str, symbol: str, limit: int = 100) -> pd.DataFrame:
    """
    Generic fetcher for CCXT exchanges and Yahoo Finance.
    """
    try:
        # Yahoo Finance Handling
        if exchange_id == 'yahoo':
            # yfinance uses 'history'
            # limit in days roughly? yfinance takes period or start/end.
            # We can approximate limit -> days. calling history(period='1y') is safe.
            ticker = yf.Ticker(symbol)
            # Fetch plenty of data to ensure we have enough for 300 candles (approx 1.5y)
            # '2y' should be safe for daily candles.
            df = ticker.history(period='2y')
            
            if df.empty:
                raise ValueError(f"No data found for {symbol} on Yahoo Finance")
                
            # yfinance returns: Open, High, Low, Close, Volume, Dividends, Stock Splits
            # Columns are capitalized.
            df = df.rename(columns={
                "Open": "open", 
                "High": "high", 
                "Low": "low", 
                "Close": "close", 
                "Volume": "volume"
            })
            
            # Index is DatetimeIndex already (localized? often yes)
            # Ensure naive timezone or utc to match ccxt (usually UTC timestamps or naive)
            if df.index.tz is not None:
                df.index = df.index.tz_convert(None)
                
            df.index.name = 'timestamp'
            
            # yfinance often returns the current unfinished day.
            # We might want to keep it or drop it depending on preference.
            # For now, keep it.
            
            return df.tail(limit)

        # Special handling for hyperliquid if needed
        if exchange_id == 'hyperliquid' and 'HYPE' in symbol:
             pass

        exchange_class = getattr(ccxt, exchange_id)
        exchange = exchange_class({'enableRateLimit': True})
        
        # CCXT expects symbols often in specific formats
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
            df = fetch_generic_daily(exchange, symbol, limit=300)
            
            # Calculate Indicator
            df = calculate_larsson_line(df)
            last_row = df.iloc[-1]
            current_color = last_row['color']
            current_price = last_row['close']
            
            # Calculate 24h Change
            change_24h = 0.0
            if len(df) >= 2:
                prev_close = df.iloc[-2]['close']
                change_24h = ((current_price - prev_close) / prev_close) * 100
            
            # Get last 7 days history (close prices)
            # We want strictly the last 7 values for the graph
            history_7d = df['close'].tail(30).tolist() # Take 30 to be safe/richer graph, front end can slice
            
            print(f"{exchange.upper()} {symbol}: {current_color} (${current_price}) {change_24h:.2f}%")
            
            # Update State
            prev_color = update_asset_state(exchange, symbol, current_color, current_price, change_24h, history_7d)
            
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
