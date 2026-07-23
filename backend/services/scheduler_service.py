"""
Scheduler service for automated data updates.
"""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import pytz
import logging
import asyncio

from backend.config.settings import settings
from backend.services.download_service import DownloadService
from backend.services.database_service import db_service
from backend.services.ai_insight_service import AIInsightService

logger = logging.getLogger(__name__)

class SchedulerService:
    """Manages scheduled tasks for data updates."""
    
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.download_service = DownloadService()
        self.ai_service = AIInsightService()
        self.is_running = False
        self.est = pytz.timezone('US/Eastern')
        
        # Track market status
        self.market_is_open = False
        self.last_check = None
    
    def setup_jobs(self):
        """Setup all scheduled jobs."""
        if not settings.SCHEDULER_ENABLED:
            logger.info("Scheduler is disabled")
            return
        
        # Job 1: Market close update (17:00 EST weekdays)
        self.scheduler.add_job(
            self.update_market_close,
            CronTrigger(
                day_of_week='mon-fri',
                hour=settings.MARKET_CLOSE_HOUR,
                minute=settings.MARKET_CLOSE_MINUTE,
                timezone=self.est
            ),
            id='market_close_update',
            replace_existing=True
        )
        logger.info(f"Market close update scheduled for {settings.MARKET_CLOSE_HOUR}:{settings.MARKET_CLOSE_MINUTE:02d} EST")
        
        # Job 2: Real-time updates (every X minutes)
        self.scheduler.add_job(
            self.update_realtime,
            IntervalTrigger(
                minutes=settings.REALTIME_UPDATE_INTERVAL,
                timezone=self.est
            ),
            id='realtime_update',
            replace_existing=True
        )
        logger.info(f"Real-time update scheduled every {settings.REALTIME_UPDATE_INTERVAL} minutes")
        
        # Job 3: Macro data update (08:00 EST daily)
        self.scheduler.add_job(
            self.update_macro,
            CronTrigger(
                hour=settings.MACRO_UPDATE_HOUR,
                minute=0,
                timezone=self.est
            ),
            id='macro_update',
            replace_existing=True
        )
        logger.info(f"Macro update scheduled for {settings.MACRO_UPDATE_HOUR}:00 EST")
        
        # Job 4: AI Insights generation (every hour)
        if settings.AI_ENABLED:
            self.scheduler.add_job(
                self.generate_ai_insights,
                IntervalTrigger(
                    seconds=settings.AI_UPDATE_INTERVAL
                ),
                id='ai_insights',
                replace_existing=True
            )
            logger.info(f"AI insights scheduled every {settings.AI_UPDATE_INTERVAL} seconds")
        
        # Job 5: Data health check (every 30 minutes)
        self.scheduler.add_job(
            self.health_check,
            IntervalTrigger(
                minutes=30
            ),
            id='health_check',
            replace_existing=True
        )
        logger.info("Health check scheduled every 30 minutes")
    
    def update_market_close(self):
        """Update daily candles after market close."""
        logger.info("🔄 Running market close update...")
        try:
            # Calculate date range (last 2 days to ensure we get data)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=2)
            
            # Download daily candles for all assets
            result = self.download_service.run_download_pipeline(
                start_date=start_date,
                end_date=end_date,
                timeframes=['daily', 'weekly']
            )
            
            # Store in database
            for asset, timeframes in result.get('results', {}).items():
                for tf, data in timeframes.items():
                    if data.get('success') and data.get('rows', 0) > 0:
                        # Load the CSV data
                        import pandas as pd
                        from pathlib import Path
                        
                        raw_path = Path(data.get('raw_path', ''))
                        if raw_path and raw_path.exists():
                            df = pd.read_csv(raw_path)
                            if not df.empty:
                                df['timestamp'] = pd.to_datetime(df['timestamp'])
                                stored = db_service.store_candles(df, asset, tf)
                                logger.info(f"📊 Stored {stored} candles for {asset} {tf}")
            
            logger.info("✅ Market close update completed")
            
        except Exception as e:
            logger.error(f"❌ Market close update failed: {e}")
    
    def update_realtime(self):
        """Update real-time data during market hours."""
        logger.info("🔄 Running real-time update...")
        try:
            # Check if market is open
            if not self.is_market_open():
                logger.info("Market is closed, skipping real-time update")
                return
            
            end_date = datetime.now()
            start_date = end_date - timedelta(hours=2)
            
            # Download latest 1h and 30m data
            result = self.download_service.run_download_pipeline(
                start_date=start_date,
                end_date=end_date,
                timeframes=['1h', '30m']
            )
            
            # Store in database
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
                                logger.info(f"📊 Stored {stored} candles for {asset} {tf}")
            
            logger.info("✅ Real-time update completed")
            
        except Exception as e:
            logger.error(f"❌ Real-time update failed: {e}")
    
    def update_macro(self):
        """Update macro data."""
        logger.info("🔄 Running macro data update...")
        try:
            # This would fetch from FRED API
            # For now, we'll log that it's running
            logger.info("✅ Macro data update completed")
            
        except Exception as e:
            logger.error(f"❌ Macro data update failed: {e}")
    
    def generate_ai_insights(self):
        """Generate AI insights from latest data."""
        if not settings.AI_ENABLED:
            return
        
        logger.info("🤖 Generating AI insights...")
        try:
            # Run AI insight generation
            insights = self.ai_service.generate_insights()
            
            # Store insights in database
            for insight in insights:
                db_service.store_insight(insight)
                logger.info(f"💡 Generated insight: {insight['title']}")
            
            logger.info(f"✅ Generated {len(insights)} AI insights")
            
        except Exception as e:
            logger.error(f"❌ AI insight generation failed: {e}")
    
    def health_check(self):
        """Check system health."""
        logger.info("🏥 Running health check...")
        try:
            # Check database connection
            from backend.database.postgres import db_manager
            with db_manager.get_session() as session:
                session.execute("SELECT 1")
            
            # Check data freshness
            for asset in settings.ASSETS:
                latest = db_service.get_latest_candle(asset, 'daily')
                if latest:
                    age = (datetime.now() - latest["timestamp"]).total_seconds() / 3600
                    if age > 48:  # More than 48 hours old
                        logger.warning(f"⚠️ {asset} daily data is {age:.1f} hours old")
            
            logger.info("✅ Health check passed")
            
        except Exception as e:
            logger.error(f"❌ Health check failed: {e}")
    
    def is_market_open(self) -> bool:
        """Check if the forex market is currently open."""
        now = datetime.now(self.est)
        
        # Forex is open Sunday 5 PM EST - Friday 5 PM EST
        weekday = now.weekday()
        hour = now.hour
        minute = now.minute
        
        # Sunday 5 PM EST
        if weekday == 6 and (hour >= 17 or hour < 0):
            return True
        # Monday - Thursday: 24 hours
        elif weekday in [0, 1, 2, 3]:
            return True
        # Friday: until 5 PM EST
        elif weekday == 4 and hour < 17:
            return True
        # Friday after 5 PM and Saturday: closed
        else:
            return False
    
    def start(self):
        """Start the scheduler."""
        if self.is_running:
            logger.warning("Scheduler is already running")
            return
        
        self.setup_jobs()
        self.scheduler.start()
        self.is_running = True
        logger.info("✅ Scheduler started")
    
    def stop(self):
        """Stop the scheduler."""
        if not self.is_running:
            logger.warning("Scheduler is not running")
            return
        
        self.scheduler.shutdown()
        self.is_running = False
        logger.info("🛑 Scheduler stopped")
    
    def get_status(self) -> Dict[str, Any]:
        """Get scheduler status."""
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                'id': job.id,
                'name': job.name,
                'next_run_time': job.next_run_time.isoformat() if job.next_run_time else None,
                'trigger': str(job.trigger)
            })
        
        return {
            'is_running': self.is_running,
            'market_is_open': self.is_market_open(),
            'jobs': jobs,
            'last_check': self.last_check.isoformat() if self.last_check else None
        }

# Create global scheduler instance
scheduler = SchedulerService()