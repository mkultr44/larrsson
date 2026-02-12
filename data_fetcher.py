"""
Data fetching module using CCXT
Fetches OHLCV data for BTC/USDT
"""
import ccxt
import pandas as pd
from datetime import datetime, timedelta


def fetch_btc_daily(exchange_id: str = 'binance', symbol: str = 'BTC/USDT', 
                    limit: int = 100) -> pd.DataFrame:
    """
    Fetch daily OHLCV data for Bitcoin.
    
    Args:
        exchange_id: Exchange to use (default: binance)
        symbol: Trading pair (default: BTC/USDT)
        limit: Number of candles to fetch (default: 100)
        
    Returns:
        DataFrame with columns: timestamp, open, high, low, close, volume
    """
    try:
        exchange_class = getattr(ccxt, exchange_id)
        exchange = exchange_class({
            'enableRateLimit': True
        })
        
        # Fetch daily candles
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe='1d', limit=limit)
        
        # Convert to DataFrame
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        
        return df
        
    except Exception as e:
        print(f"Error fetching data: {e}")
        raise


def fetch_hyperliquid_hype_daily(symbol: str = 'HYPE/USDC:USDC', 
                                  limit: int = 100) -> pd.DataFrame:
    """
    Fetch daily OHLCV data for HYPE token from Hyperliquid.
    
    Args:
        symbol: Trading pair (default: HYPE/USDC:USDC perpetual)
        limit: Number of candles to fetch (default: 100)
        
    Returns:
        DataFrame with columns: timestamp, open, high, low, close, volume
    """
    try:
        exchange = ccxt.hyperliquid({
            'enableRateLimit': True
        })
        
        # Fetch daily candles
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe='1d', limit=limit)
        
        # Convert to DataFrame
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        
        return df
        
    except Exception as e:
        print(f"Error fetching Hyperliquid data: {e}")
        raise
