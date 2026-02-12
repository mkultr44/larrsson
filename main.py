import time
import schedule
from datetime import datetime
import traceback
import sys

from data_fetcher import fetch_btc_daily, fetch_hyperliquid_hype_daily
from indicator import calculate_larsson_line
from config import update_exchange_color, get_current_status
from email_notifier import send_email

def check_indicators():
    """
    Check indicators for all exchanges, update state, and send alerts if changed.
    """
    print(f"[{datetime.now()}] Checking indicators...")
    try:
        # --- Binance (BTC/USDT) ---
        try:
            df_btc = fetch_btc_daily(limit=50)
            df_btc = calculate_larsson_line(df_btc)
            last_btc = df_btc.iloc[-1]
            current_color_btc = last_btc['color']
            current_price_btc = last_btc['close']
            
            print(f"Binance BTC/USDT: {current_color_btc} (${current_price_btc})")
            
            prev_color = update_exchange_color("binance", current_color_btc, current_price_btc)
            
            if prev_color and prev_color != current_color_btc:
                subject = f"Market Alert: BTC/USDT Changed to {current_color_btc.upper()}"
                body = f"""
                Bitcoin Indicator Update:
                
                New Status: {current_color_btc.upper()}
                Previous Status: {prev_color.upper()}
                Current Price: ${current_price_btc}
                Timestamp: {datetime.now()}
                """
                send_email(subject, body)
                
        except Exception as e:
            print(f"Error checking Binance: {e}")
            traceback.print_exc()

        # --- Hyperliquid (HYPE/USDC) ---
        try:
            df_hype = fetch_hyperliquid_hype_daily(limit=50)
            df_hype = calculate_larsson_line(df_hype)
            last_hype = df_hype.iloc[-1]
            current_color_hype = last_hype['color']
            current_price_hype = last_hype['close']
            
            print(f"Hyperliquid HYPE/USDC: {current_color_hype} (${current_price_hype})")
            
            prev_color = update_exchange_color("hyperliquid", current_color_hype, current_price_hype)
            
            if prev_color and prev_color != current_color_hype:
                subject = f"Market Alert: HYPE/USDC Changed to {current_color_hype.upper()}"
                body = f"""
                HYPE Token Indicator Update:
                
                New Status: {current_color_hype.upper()}
                Previous Status: {prev_color.upper()}
                Current Price: ${current_price_hype}
                Timestamp: {datetime.now()}
                """
                send_email(subject, body)
                
        except Exception as e:
            print(f"Error checking Hyperliquid: {e}")
            traceback.print_exc()

    except Exception as e:
        print(f"Critical error in check loop: {e}")
        traceback.print_exc()


def send_weekly_summary():
    """
    Send a summary email with the current status of all indicators.
    """
    print(f"[{datetime.now()}] Sending weekly summary...")
    try:
        status = get_current_status()
        
        binance_status = status.get("binance", {})
        hyperliquid_status = status.get("hyperliquid", {})
        
        body = f"""
        Weekly Trading Indicator Summary
        Timestamp: {datetime.now()}
        
        --- Binance (BTC/USDT) ---
        Status: {binance_status.get('color', 'Unknown').upper()}
        Last Price: ${binance_status.get('price', 'N/A')}
        Last Check: {binance_status.get('last_check', 'Never')}
        
        --- Hyperliquid (HYPE/USDC) ---
        Status: {hyperliquid_status.get('color', 'Unknown').upper()}
        Last Price: ${hyperliquid_status.get('price', 'N/A')}
        Last Check: {hyperliquid_status.get('last_check', 'Never')}
        """
        
        send_email("Weekly Trading Indicator Summary", body)
        
    except Exception as e:
        print(f"Error sending weekly summary: {e}")
        traceback.print_exc()


def main():
    print("Starting Trading Alert Server...")
    
    # Check if this is a fresh install (state.json does not exist)
    # CONFIG_FILE is defined in config.py, we need to import it or check manually
    from config import CONFIG_FILE
    
    if not CONFIG_FILE.exists():
        print("First run detected. Sending test email...")
        send_email("Trading Alert Server Installed", "The trading alert service has been successfully installed and started.\n\nYou will receive alerts when indicators change color.")
    else:
        print("Existing configuration found. Skipping test email.")
    
    # Initial check on startup
    check_indicators()
    
    # Schedule checks 4x daily
    schedule.every().day.at("08:00").do(check_indicators)
    schedule.every().day.at("12:00").do(check_indicators)
    schedule.every().day.at("16:00").do(check_indicators)
    schedule.every().day.at("20:00").do(check_indicators)
    
    # Schedule weekly summary (Monday 10:00 AM)
    schedule.every().monday.at("10:00").do(send_weekly_summary)
    
    print("Schedule set. Waiting for jobs...")
    
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Stopping server...")
