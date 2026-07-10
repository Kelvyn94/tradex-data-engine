"""
Technical indicators module for TradeX Data Engine.
"""

import pandas as pd
import numpy as np
from typing import Optional, Union

def calculate_sma(df: pd.DataFrame, period: int = 20, column: str = 'close') -> pd.Series:
    """
    Calculate Simple Moving Average.
    
    Args:
        df: DataFrame with OHLCV data
        period: SMA period
        column: Column to calculate SMA on
        
    Returns:
        Series with SMA values
    """
    if df is None or df.empty:
        return pd.Series()
    
    if column not in df.columns:
        return pd.Series()
    
    return df[column].rolling(window=period).mean()

def calculate_ema(df: pd.DataFrame, period: int = 20, column: str = 'close') -> pd.Series:
    """
    Calculate Exponential Moving Average.
    
    Args:
        df: DataFrame with OHLCV data
        period: EMA period
        column: Column to calculate EMA on
        
    Returns:
        Series with EMA values
    """
    if df is None or df.empty:
        return pd.Series()
    
    if column not in df.columns:
        return pd.Series()
    
    return df[column].ewm(span=period, adjust=False).mean()

def calculate_rsi(df: pd.DataFrame, period: int = 14, column: str = 'close') -> Optional[pd.Series]:
    """
    Calculate Relative Strength Index.
    
    Args:
        df: DataFrame with OHLCV data
        period: RSI period
        column: Column to calculate RSI on
        
    Returns:
        Series with RSI values
    """
    if df is None or df.empty:
        return None
    
    if column not in df.columns:
        return None
    
    delta = df[column].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    
    return rsi

def calculate_macd(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9, column: str = 'close') -> Optional[dict]:
    """
    Calculate MACD (Moving Average Convergence Divergence).
    
    Args:
        df: DataFrame with OHLCV data
        fast: Fast EMA period
        slow: Slow EMA period
        signal: Signal line period
        column: Column to calculate MACD on
        
    Returns:
        Dictionary with macd, signal, and histogram series
    """
    if df is None or df.empty:
        return None
    
    if column not in df.columns:
        return None
    
    ema_fast = calculate_ema(df, fast, column)
    ema_slow = calculate_ema(df, slow, column)
    
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    
    return {
        'macd': macd_line,
        'signal': signal_line,
        'histogram': histogram
    }

def calculate_bollinger(df: pd.DataFrame, period: int = 20, std_dev: int = 2, column: str = 'close') -> Optional[dict]:
    """
    Calculate Bollinger Bands.
    
    Args:
        df: DataFrame with OHLCV data
        period: Moving average period
        std_dev: Number of standard deviations
        column: Column to calculate on
        
    Returns:
        Dictionary with upper, middle, and lower bands
    """
    if df is None or df.empty:
        return None
    
    if column not in df.columns:
        return None
    
    middle = df[column].rolling(window=period).mean()
    std = df[column].rolling(window=period).std()
    
    upper = middle + (std * std_dev)
    lower = middle - (std * std_dev)
    
    return {
        'upper': upper,
        'middle': middle,
        'lower': lower
    }

def calculate_atr(df: pd.DataFrame, period: int = 14) -> Optional[pd.Series]:
    """
    Calculate Average True Range.
    
    Args:
        df: DataFrame with OHLCV data
        period: ATR period
        
    Returns:
        Series with ATR values
    """
    if df is None or df.empty:
        return None
    
    required = ['high', 'low', 'close']
    for col in required:
        if col not in df.columns:
            return None
    
    high = df['high']
    low = df['low']
    close = df['close'].shift(1)
    
    tr1 = high - low
    tr2 = (high - close).abs()
    tr3 = (low - close).abs()
    
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    
    return atr

def calculate_adx(df: pd.DataFrame, period: int = 14) -> Optional[dict]:
    """
    Calculate Average Directional Index.
    
    Args:
        df: DataFrame with OHLCV data
        period: ADX period
        
    Returns:
        Dictionary with adx, plus_di, and minus_di
    """
    if df is None or df.empty:
        return None
    
    required = ['high', 'low', 'close']
    for col in required:
        if col not in df.columns:
            return None
    
    high = df['high']
    low = df['low']
    close = df['close']
    
    # True Range
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    # Directional Movement
    up_move = high - high.shift(1)
    down_move = low.shift(1) - low
    
    plus_dm = up_move.where((up_move > down_move) & (up_move > 0), 0)
    minus_dm = down_move.where((down_move > up_move) & (down_move > 0), 0)
    
    # Smoothed averages
    atr = tr.rolling(window=period).mean()
    plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
    minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr)
    
    # ADX
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
    adx = dx.rolling(window=period).mean()
    
    return {
        'adx': adx,
        'plus_di': plus_di,
        'minus_di': minus_di
    }