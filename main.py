#!/usr/bin/env python3
"""
TradeX Data Engine - Main Entry Point
"""

import sys
import argparse
from datetime import datetime, timedelta
from pathlib import Path
import time

sys.path.insert(0, str(Path(__file__).parent))

from backend.services.download_service import DownloadService
from backend.services.database_service import db_service
from backend.services.scheduler_service import scheduler
from backend.config.settings import settings

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='TradeX Data Engine')
    parser.add_argument('command', choices=[
        'download', 'api', 'scheduler', 'insights', 'init_db', 'historical'
    ], help='Command to execute')
    parser.add_argument('--days', type=int, default=5, help='Number of days to download')
    parser.add_argument('--assets', nargs='+', help='Specific assets to download')
    parser.add_argument('--timeframes', nargs='+', help='Specific timeframes to download')
    parser.add_argument('--years', type=int, help='Years of historical data to download')
    parser.add_argument('--host', default='0.0.0.0', help='API host')
    parser.add_argument('--port', type=int, default=8000, help='API port')
    parser.add_argument('--batch-size', type=int, default=2, help='Years per batch for historical download')
    
    args = parser.parse_args()
    
    if args.command == 'download':
        run_download(args)
    elif args.command == 'historical':
        run_historical(args)
    elif args.command == 'api':
        run_api(args)
    elif args.command == 'scheduler':
        run_scheduler()
    elif args.command == 'insights':
        run_insights()
    elif args.command == 'init_db':
        init_database()

def run_download(args):
    """Run the download pipeline (daily updates)."""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=args.days)
    
    print(f"\n{'='*60}")
    print(f"TRADEX DATA ENGINE - DAILY UPDATE")
    print(f"{'='*60}")
    print(f"Date Range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    print(f"Assets: {args.assets or settings.ASSETS}")
    print(f"Timeframes: {args.timeframes or settings.TIMEFRAMES}")
    print(f"{'='*60}\n")
    
    service = DownloadService()
    result = service.run_download_pipeline(
        start_date=start_date,
        end_date=end_date,
        assets=args.assets,
        timeframes=args.timeframes
    )
    
    store_result_in_db(result)
    
    print(f"\n{'='*60}")
    print(f"UPDATE COMPLETE")
    print(f"{'='*60}")
    print(f"Success Rate: {result.get('success_rate', 'N/A')}")
    print(f"Total Attempts: {result.get('total_attempts', 0)}")
    print(f"Successful: {result.get('total_success', 0)}")
    print(f"{'='*60}\n")

def run_historical(args):
    """Run historical data download."""
    print(f"\n{'='*60}")
    print(f"TRADEX DATA ENGINE - HISTORICAL DOWNLOAD")
    print(f"{'='*60}")
    
    # Determine which assets to download
    assets = args.assets or settings.ASSETS
    
    # Determine which timeframes to download
    timeframes = args.timeframes or settings.TIMEFRAMES
    
    # Determine years to download
    if args.years:
        # Use custom years
        years_map = {tf: args.years for tf in timeframes}
    else:
        # Use historical targets from settings
        years_map = {tf: settings.HISTORICAL_TARGETS.get(tf, 5) for tf in timeframes}
    
    print(f"Assets: {assets}")
    print(f"Timeframes: {timeframes}")
    print(f"Years: {years_map}")
    print(f"Batch Size: {args.batch_size or settings.DOWNLOAD_BATCH_SIZE} years per batch")
    print(f"{'='*60}\n")
    
    service = DownloadService()
    total_stored = 0
    
    for tf in timeframes:
        years = years_map.get(tf, 5)
        print(f"\n📥 Downloading {tf} data ({years} years)...")
        print("-" * 40)
        
        # Download in batches to avoid memory issues
        batch_size = args.batch_size or settings.DOWNLOAD_BATCH_SIZE
        total_batches = (years + batch_size - 1) // batch_size
        
        for batch_num in range(total_batches):
            batch_start_year = years - (batch_num * batch_size)
            batch_end_year = max(0, batch_start_year - batch_size)
            
            end_date = datetime.now()
            start_date = end_date - timedelta(days=batch_start_year * 365)
            
            if batch_end_year > 0:
                # This is not the last batch, download full batch
                end_date = end_date - timedelta(days=batch_end_year * 365)
            # else: last batch, download to current date
            
            print(f"  Batch {batch_num + 1}/{total_batches}: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
            
            result = service.run_download_pipeline(
                start_date=start_date,
                end_date=end_date,
                assets=assets,
                timeframes=[tf]
            )
            
            # Store in database
            batch_stored = store_result_in_db(result)
            total_stored += batch_stored
            
            # Add delay between batches to avoid rate limiting
            if batch_num < total_batches - 1:
                print(f"  ⏳ Waiting 2 seconds before next batch...")
                time.sleep(2)
        
        print(f"  ✅ {tf} download complete")
    
    print(f"\n{'='*60}")
    print(f"HISTORICAL DOWNLOAD COMPLETE")
    print(f"{'='*60}")
    print(f"Total candles stored: {total_stored}")
    print(f"{'='*60}\n")
    
    # Show data coverage
    print("\n📊 Data Coverage Summary:")
    print("-" * 40)
    check_data_coverage(assets, timeframes)

def store_result_in_db(result) -> int:
    """Store download result in database."""
    total_stored = 0
    
    for asset, timeframes in result.get('results', {}).items():
        for tf, data in timeframes.items():
            if data.get('success') and data.get('rows', 0) > 0:
                import pandas as pd
                from pathlib import Path
                
                raw_path = Path(data.get('raw_path', ''))
                if raw_path and raw_path.exists():
                    df = pd.read_csv(raw_path)
                    if not df.empty:
                        df['timestamp'] = pd.to_datetime(df['timestamp'])
                        stored = db_service.store_candles(df, asset, tf)
                        total_stored += stored
                        print(f"    ✅ {asset} {tf}: {stored} candles stored")
    
    return total_stored

def check_data_coverage(assets=None, timeframes=None):
    """Check data coverage for assets and timeframes."""
    from backend.database.postgres import db_manager
    from backend.database.models import AssetCandle
    
    if assets is None:
        assets = settings.ASSETS
    if timeframes is None:
        timeframes = settings.TIMEFRAMES
    
    with db_manager.get_session() as session:
        for asset in assets:
            print(f"\n{asset}:")
            for tf in timeframes:
                count = session.query(AssetCandle).filter(
                    AssetCandle.asset_symbol == asset,
                    AssetCandle.timeframe == tf
                ).count()
                
                if count > 0:
                    # Get date range
                    first = session.query(AssetCandle.timestamp).filter(
                        AssetCandle.asset_symbol == asset,
                        AssetCandle.timeframe == tf
                    ).order_by(AssetCandle.timestamp.asc()).first()
                    
                    last = session.query(AssetCandle.timestamp).filter(
                        AssetCandle.asset_symbol == asset,
                        AssetCandle.timeframe == tf
                    ).order_by(AssetCandle.timestamp.desc()).first()
                    
                    if first and last:
                        days = (last[0] - first[0]).days
                        years = days / 365
                        print(f"  ✅ {tf}: {count} candles ({years:.1f} years, {first[0].strftime('%Y-%m-%d')} to {last[0].strftime('%Y-%m-%d')})")
                    else:
                        print(f"  ✅ {tf}: {count} candles")
                else:
                    print(f"  ❌ {tf}: No data")

def run_api(args):
    """Run the API server."""
    print(f"\n🚀 Starting TradeX Data Engine API...")
    print(f"   Host: {args.host}")
    print(f"   Port: {args.port}")
    print(f"   Docs: http://{args.host}:{args.port}/docs")
    print(f"\n{'='*60}\n")
    
    import uvicorn
    uvicorn.run(
        "backend.api.app:app",
        host=args.host,
        port=args.port,
        reload=True
    )

def run_scheduler():
    """Run the scheduler service."""
    print(f"\n⏰ Starting TradeX Data Engine Scheduler...")
    print(f"{'='*60}\n")
    
    scheduler.start()
    
    try:
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Stopping scheduler...")
        scheduler.stop()

def run_insights():
    """Generate AI insights."""
    print(f"\n🤖 Generating AI Insights...")
    print(f"{'='*60}\n")
    
    from backend.services.ai_insight_service import AIInsightService
    ai_service = AIInsightService()
    insights = ai_service.generate_enhanced_insights()
    
    stored = 0
    for insight in insights:
        db_service.store_insight(insight)
        stored += 1
        print(f"  💡 {insight['title']}")
    
    print(f"\n✅ Generated {stored} insights")

def init_database():
    """Initialize the database."""
    print(f"\n🗄️ Initializing Database...")
    print(f"{'='*60}\n")
    
    from backend.database.postgres import db_manager
    db_manager.create_tables()
    
    print(f"✅ Database initialized successfully")
    print(f"   URL: {settings.DATABASE_URL}")

if __name__ == "__main__":
    main()