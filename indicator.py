"""
Larsson Line Indicator Implementation
Ported from Pine Script to Python
"""
import pandas as pd
import numpy as np


def smma(series: pd.Series, length: int) -> pd.Series:
    """
    Smoothed Moving Average (SMMA) - Wilder's Smoothing
    Equivalent to Pine Script's smma function.
    """
    result = pd.Series(index=series.index, dtype=float)
    
    # First value is SMA
    sma_first = series.iloc[:length].mean()
    result.iloc[length - 1] = sma_first
    
    # Subsequent values use SMMA formula
    for i in range(length, len(series)):
        result.iloc[i] = (result.iloc[i - 1] * (length - 1) + series.iloc[i]) / length
    
    return result


def calculate_larsson_line(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate Larsson Line indicator values.
    
    Args:
        df: DataFrame with 'high' and 'low' columns
        
    Returns:
        DataFrame with added columns: v1, m1, m2, v2, signal, color
    """
    # hl2 = (high + low) / 2
    hl2 = (df['high'] + df['low']) / 2
    
    # Calculate SMMA values
    v1 = smma(hl2, 15)
    m1 = smma(hl2, 19)
    m2 = smma(hl2, 25)
    v2 = smma(hl2, 29)
    
    # Determine pattern states (p1, p2, p3)
    # p2 = transition zone (silver)
    # p3 = bearish (navy) - v1 < v2
    # p1 = bullish (orange) - v1 >= v2
    
    p2 = ((v1 < m1) != (v1 < v2)) | ((m2 < v2) != (v1 < v2))
    p3 = (~p2) & (v1 < v2)
    p1 = (~p2) & (~p3)
    
    # Assign colors
    def get_color(row_p1, row_p2, row_p3):
        if row_p1:
            return 'orange'  # Bullish - BUY
        elif row_p2:
            return 'silver'  # Transition
        else:
            return 'navy'    # Bearish - SELL
    
    colors = [get_color(p1.iloc[i], p2.iloc[i], p3.iloc[i]) for i in range(len(p1))]
    
    result = df.copy()
    result['v1'] = v1
    result['m1'] = m1
    result['m2'] = m2
    result['v2'] = v2
    result['p1'] = p1
    result['p2'] = p2
    result['p3'] = p3
    result['color'] = colors
    
    return result


def detect_signals(df: pd.DataFrame) -> pd.DataFrame:
    """
    Detect buy/sell signals based on color changes.
    
    Returns DataFrame with 'signal' column:
    - 'BUY': When color changes TO orange
    - 'SELL': When color changes TO navy
    - None: No signal
    """
    df = df.copy()
    df['prev_color'] = df['color'].shift(1)
    
    signals = []
    for i in range(len(df)):
        if pd.isna(df['prev_color'].iloc[i]):
            signals.append(None)
        elif df['color'].iloc[i] == 'orange' and df['prev_color'].iloc[i] != 'orange':
            signals.append('BUY')
        elif df['color'].iloc[i] == 'navy' and df['prev_color'].iloc[i] != 'navy':
            signals.append('SELL')
        else:
            signals.append(None)
    
    df['signal'] = signals
    return df
