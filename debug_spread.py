"""
Debug: Check spread data for pairs trading.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from backend.services.database_service import db_service
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

print("=" * 70)
print("🔍 DEBUG: SPREAD ANALYSIS")
print("=" * 70)

# Get data
end_date = datetime.now()
start_date = end_date - timedelta(days=365*2)

print(f"\n📥 Loading data from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")

data = {}
for asset in ['XAUEUR', 'XAUGBP']:
    df = db_service.get_candles(asset, 'daily', start_date, end_date)
    if df is not None and not df.empty:
        df = df.set_index('timestamp')
        data[asset] = df
        print(f"   ✅ {asset}: {len(data[asset])} rows")

# Calculate spread
price1 = data['XAUEUR']['close']
price2 = data['XAUGBP']['close']
spread = price1 - price2

# Calculate z-score
lookback = 30
spread_mean = spread.rolling(window=lookback).mean()
spread_std = spread.rolling(window=lookback).std()
spread_zscore = (spread - spread_mean) / spread_std

print("\n📊 SPREAD STATISTICS")
print("-" * 40)
print(f"Mean Spread: {spread.mean():.4f}")
print(f"Std Spread: {spread.std():.4f}")
print(f"Min Spread: {spread.min():.4f}")
print(f"Max Spread: {spread.max():.4f}")

print("\n📊 Z-SCORE STATISTICS")
print("-" * 40)
print(f"Mean Z-Score: {spread_zscore.mean():.4f}")
print(f"Std Z-Score: {spread_zscore.std():.4f}")
print(f"Min Z-Score: {spread_zscore.min():.4f}")
print(f"Max Z-Score: {spread_zscore.max():.4f}")

print("\n📊 SIGNAL OPPORTUNITIES")
print("-" * 40)

# Count potential signals
thresholds = [1.0, 1.2, 1.5, 2.0]
for threshold in thresholds:
    high_signals = sum(spread_zscore > threshold)
    low_signals = sum(spread_zscore < -threshold)
    total = high_signals + low_signals
    print(f"Threshold {threshold}: {total} potential signals ({high_signals} high, {low_signals} low)")

print("\n📊 RECENT SPREAD BEHAVIOR")
print("-" * 40)
print(spread_zscore.tail(20).to_string())