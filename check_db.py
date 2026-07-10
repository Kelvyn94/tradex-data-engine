"""
Check database status.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from backend.database.postgres import db_manager
from backend.database.models import AssetCandle
from backend.config.settings import settings
from sqlalchemy import text

print("=" * 60)
print("📊 DATABASE STATUS")
print("=" * 60)

# Total candles
with db_manager.get_session() as session:
    total = session.query(AssetCandle).count()
    print(f"\nTotal candles: {total:,}")
    
    # Per asset
    print("\n📈 Per Asset:")
    for asset in settings.ASSETS:
        count = session.query(AssetCandle).filter(
            AssetCandle.asset_symbol == asset
        ).count()
        print(f"  {asset}: {count:,}")
    
    # Per timeframe
    print("\n⏰ Per Timeframe:")
    for tf in ['weekly', 'daily', '4h', '1h', '30m']:
        count = session.query(AssetCandle).filter(
            AssetCandle.timeframe == tf
        ).count()
        print(f"  {tf}: {count:,}")
    
    # Database size - FIXED
    result = session.execute(
        text('SELECT pg_database_size(current_database()) / 1024 / 1024 as size_mb')
    )
    size_mb = result.fetchone()[0]
    print(f"\n💾 Database size: {size_mb} MB")

print("=" * 60)