"""
Sentiment service for aggregating sentiment data with rate limit awareness.
"""

import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging

from backend.providers.news_provider import NewsProvider
from backend.services.database_service import db_service
from backend.utils.rate_limiter import rate_limiter_manager

logger = logging.getLogger(__name__)

class SentimentService:
    """
    Service for managing sentiment data with rate limit awareness.
    """
    
    def __init__(self):
        self.news_provider = NewsProvider()
        logger.info("SentimentService initialized")
    
    def update_sentiment(self, days: int = 7) -> Dict[str, int]:
        """
        Update sentiment data for all assets with rate limit awareness.
        """
        from backend.config.settings import settings
        
        results = {}
        
        # Get rate limit status first
        status = self.news_provider.get_rate_limit_status()
        logger.info(f"Current NewsAPI status: {status['requests_used']}/{status['daily_limit']} "
                   f"({status['usage_percent']}%)")
        
        # Calculate how many assets we can process
        remaining = status['requests_remaining']
        assets_to_process = settings.ASSETS[:remaining] if remaining < len(settings.ASSETS) else settings.ASSETS
        
        if remaining < len(settings.ASSETS):
            logger.warning(f"Only processing {len(assets_to_process)} assets due to rate limits")
        
        for asset in assets_to_process:
            try:
                df = self.news_provider.get_sentiment(asset, days)
                
                if df is not None and not df.empty:
                    stored = self._store_sentiment(df)
                    results[asset] = {
                        'stored': stored,
                        'total': len(df),
                        'avg_sentiment': float(df['sentiment_score'].mean())
                    }
                    logger.info(f"Stored {stored} sentiment records for {asset}")
                else:
                    results[asset] = {
                        'stored': 0,
                        'total': 0,
                        'avg_sentiment': 0.0
                    }
                    logger.warning(f"No sentiment data for {asset}")
                    
            except Exception as e:
                logger.error(f"Error updating sentiment for {asset}: {e}")
                results[asset] = {
                    'stored': 0,
                    'total': 0,
                    'avg_sentiment': 0.0,
                    'error': str(e)
                }
        
        # Log skipped assets
        if len(assets_to_process) < len(settings.ASSETS):
            skipped = set(settings.ASSETS) - set(assets_to_process)
            logger.warning(f"Skipped assets due to rate limits: {skipped}")
        
        return results
    
    def _store_sentiment(self, df: pd.DataFrame) -> int:
        """Store sentiment data in database."""
        from backend.database.postgres import db_manager
        from backend.database.models import SentimentData
        
        stored_count = 0
        with db_manager.get_session() as session:
            for _, row in df.iterrows():
                existing = session.query(SentimentData).filter(
                    SentimentData.asset_symbol == row['asset_symbol'],
                    SentimentData.timestamp == row['timestamp'],
                    SentimentData.title == row['title']
                ).first()
                
                if existing:
                    continue
                
                sentiment = SentimentData(
                    asset_symbol=row['asset_symbol'],
                    timestamp=row['timestamp'],
                    source=row.get('source', 'newsapi'),
                    sentiment_score=row['sentiment_score'],
                    title=row.get('title', ''),
                    url=row.get('url', '')
                )
                session.add(sentiment)
                stored_count += 1
            
            session.commit()
        
        return stored_count
    
    def get_latest_sentiment(self, asset: Optional[str] = None, 
                            days: int = 7) -> pd.DataFrame:
        """Get latest sentiment data from database."""
        from backend.database.postgres import db_manager
        from backend.database.models import SentimentData
        
        with db_manager.get_session() as session:
            query = session.query(SentimentData)
            
            if asset:
                query = query.filter(SentimentData.asset_symbol == asset)
            
            cutoff = datetime.now() - timedelta(days=days)
            query = query.filter(SentimentData.timestamp >= cutoff)
            
            query = query.order_by(SentimentData.timestamp.desc())
            results = query.all()
            
            if not results:
                return pd.DataFrame()
            
            data = {
                'timestamp': [r.timestamp for r in results],
                'asset_symbol': [r.asset_symbol for r in results],
                'sentiment_score': [float(r.sentiment_score) if r.sentiment_score else 0.0 for r in results],
                'title': [r.title for r in results],
                'source': [r.source for r in results]
            }
            
            return pd.DataFrame(data)
    
    def get_sentiment_insights(self) -> List[Dict[str, Any]]:
        """Generate sentiment-based insights."""
        insights = []
        
        df = self.get_latest_sentiment(days=3)
        
        if df.empty:
            return insights
        
        asset_sentiment = df.groupby('asset_symbol')['sentiment_score'].mean()
        
        for asset, score in asset_sentiment.items():
            if score > 0.3:
                insights.append({
                    'asset_symbol': asset,
                    'insight_type': 'SENTIMENT',
                    'title': f"Positive Sentiment for {asset}",
                    'description': f"{asset} has strong positive sentiment with score {score:.2f}",
                    'confidence': min(abs(score), 0.8),
                    'supporting_data': {
                        'sentiment_score': float(score),
                        'direction': 'BULLISH'
                    }
                })
            elif score < -0.3:
                insights.append({
                    'asset_symbol': asset,
                    'insight_type': 'SENTIMENT',
                    'title': f"Negative Sentiment for {asset}",
                    'description': f"{asset} has negative sentiment with score {score:.2f}",
                    'confidence': min(abs(score), 0.8),
                    'supporting_data': {
                        'sentiment_score': float(score),
                        'direction': 'BEARISH'
                    }
                })
        
        return insights
    
    def get_rate_limit_status(self) -> Dict:
        """Get current rate limit status."""
        return self.news_provider.get_rate_limit_status()