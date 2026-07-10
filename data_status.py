"""
Check complete data status - CSV and Database
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import os
import pandas as pd
from datetime import datetime

from backend.database.postgres import db_manager
from backend.database.models import AssetCandle
from backend.config.settings import settings
from sqlalchemy import func, text

print("=" * 70)
print("📊 TRADEX DATA ENGINE - COMPLETE DATA STATUS")
print("=" * 70)
print(f"Checked: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 70)

# ============================================
# 1. CSV DATA STATUS
# ============================================
print("\n📁 1. CSV FILES (Raw Data)")
print("-" * 40)

raw_dir = Path('data/raw')
if raw_dir.exists():
    total_csv = 0
    total_size = 0
    
    for asset_dir in raw_dir.iterdir():
        if asset_dir.is_dir():
            csv_files = list(asset_dir.rglob('*.csv'))
            if csv_files:
                asset_size = sum(f.stat().st_size for f in csv_files) / 1024 / 1024
                print(f"  📊 {asset_dir.name}: {len(csv_files)} files ({asset_size:.2f} MB)")
                total_csv += len(csv_files)
                total_size += asset_size
    
    print(f"\n  ✅ Total: {total_csv} CSV files ({total_size:.2f} MB)")
else:
    print("  ❌ Raw data directory not found")

# ============================================
# 2. DATABASE STATUS
# ============================================
print("\n💾 2. NEON POSTGRESQL DATABASE")
print("-" * 40)

with db_manager.get_session() as session:
    # Total candles
    total = session.query(AssetCandle).count()
    print(f"  Total Candles: {total:,}")
    
    # Per asset
    print("\n  Per Asset:")
    for asset in settings.ASSETS:
        count = session.query(AssetCandle).filter(
            AssetCandle.asset_symbol == asset
        ).count()
        pct = (count / total * 100) if total > 0 else 0
        print(f"    {asset}: {count:,} ({pct:.1f}%)")
    
    # Per timeframe
    print("\n  Per Timeframe:")
    for tf in ['weekly', 'daily', '4h', '1h', '30m']:
        count = session.query(AssetCandle).filter(
            AssetCandle.timeframe == tf
        ).count()
        pct = (count / total * 100) if total > 0 else 0
        print(f"    {tf}: {count:,} ({pct:.1f}%)")
    
    # Data range per asset
    print("\n  Data Range:")
    for asset in settings.ASSETS:
        first = session.query(func.min(AssetCandle.timestamp)).filter(
            AssetCandle.asset_symbol == asset
        ).scalar()
        last = session.query(func.max(AssetCandle.timestamp)).filter(
            AssetCandle.asset_symbol == asset
        ).scalar()
        if first and last:
            days = (last - first).days
            years = days / 365
            print(f"    {asset}: {first.strftime('%Y-%m-%d')} to {last.strftime('%Y-%m-%d')} ({years:.1f} years)")
        else:
            print(f"    {asset}: No data")
    
    # Database size
    result = session.execute(text('SELECT pg_database_size(current_database()) / 1024 / 1024 as size_mb'))
    db_size = result.fetchone()[0]
    print(f"\n  Database Size: {db_size} MB")
    print(f"  Free space: {1024 - db_size} MB remaining ({(1024 - db_size) / 1024 * 100:.1f}%)")

# ============================================
# 3. SUMMARY
# ============================================
print("\n" + "=" * 70)
print("📊 SUMMARY")
print("=" * 70)

with db_manager.get_session() as session:
    total = session.query(AssetCandle).count()
    print(f"  ✅ Total Data: {total:,} candles stored")
    print(f"  ✅ Assets: {len(settings.ASSETS)}")
    print(f"  ✅ Timeframes: {len(settings.TIMEFRAMES)}")
    print(f"  ✅ Database: {db_size} MB / 1 GB")

print("\n" + "=" * 70)
print("📈 DATA COVERAGE")
print("=" * 70)

with db_manager.get_session() as session:
    print("\n  Expected vs Actual:")
    expected_total = 0
    for asset in settings.ASSETS:
        for tf in settings.TIMEFRAMES:
            # Expected candles based on historical targets
            target_years = {
                'weekly': 15, 'daily': 10, '4h': 10, '1h': 5, '30m': 5
            }
            expected = target_years.get(tf, 5) * 365
            if tf == 'weekly':
                expected = expected // 7
            elif tf == '4h':
                expected = expected * 6
            elif tf == '1h':
                expected = expected * 24
            elif tf == '30m':
                expected = expected * 48
            
            count = session.query(AssetCandle).filter(
                AssetCandle.asset_symbol == asset,
                AssetCandle.timeframe == tf
            ).count()
            
            if count > 0:
                pct = (count / expected * 100) if expected > 0 else 0
                status = "✅" if pct > 80 else "⚠️" if pct > 50 else "❌"
                print(f"    {status} {asset} {tf}: {count:,}/{expected:,} ({pct:.0f}%)")
    
print("=" * 70)