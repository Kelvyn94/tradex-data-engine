"""
Free news sentiment provider using NewsAPI with intelligent rate limiting.
Free Tier: 100 requests/day - evenly distributed.
"""

import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import logging
import time

from backend.utils.rate_limiter import rate_limiter_manager

logger = logging.getLogger(__name__)

class NewsProvider:
    """Free news sentiment provider with intelligent rate limiting."""
    
    def __init__(self, api_key: str = None):
        from backend.config.settings import settings
        self.api_key = api_key or settings.NEWS_API_KEY
        self.base_url = "https://newsapi.org/v2/everything"
        
        # Get rate limiter
        self.rate_limiter = rate_limiter_manager.get_limiter('newsapi')
        if not self.rate_limiter:
            from backend.utils.rate_limiter import RateLimiter
            self.rate_limiter = RateLimiter('newsapi', 100, 2.0)
            rate_limiter_manager.limiters['newsapi'] = self.rate_limiter
        
        logger.info(f"NewsProvider initialized with intelligent rate limiting")
        status = self.rate_limiter.get_status()
        logger.info(f"Rate limit status: {status['requests_used']}/{status['daily_limit']} used "
                   f"({status['usage_percent']}%)")
    
    def get_sentiment(self, symbol: str, days: int = 7) -> Optional[pd.DataFrame]:
        """
        Get news sentiment for an asset with intelligent rate limiting.
        """
        try:
            # Check rate limits - will wait if needed
            if not self.rate_limiter.wait_if_needed():
                logger.warning(f"Rate limit reached for {symbol}, skipping")
                return None
            
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # Get symbol name for query
            query = self._get_query(symbol)
            
            params = {
                'q': query,
                'from': start_date.strftime('%Y-%m-%d'),
                'to': end_date.strftime('%Y-%m-%d'),
                'sortBy': 'publishedAt',
                'language': 'en',
                'apiKey': self.api_key,
                'pageSize': 50
            }
            
            response = requests.get(self.base_url, params=params, timeout=30)
            data = response.json()
            
            if data.get('status') != 'ok':
                logger.warning(f"News API error for {symbol}: {data.get('message')}")
                return None
            
            articles = data.get('articles', [])
            
            if not articles:
                logger.info(f"No news articles found for {symbol}")
                return None
            
            # Convert to DataFrame
            df = pd.DataFrame(articles)
            
            # Calculate sentiment scores
            df['sentiment_score'] = df['title'].apply(self._calculate_sentiment)
            df['timestamp'] = pd.to_datetime(df['publishedAt'])
            df['asset_symbol'] = symbol
            df['source'] = 'newsapi'
            
            # Select relevant columns
            result = df[['timestamp', 'asset_symbol', 'sentiment_score', 'title', 'url', 'source']]
            
            # Get current rate limit status
            status = self.rate_limiter.get_status()
            logger.info(f"Retrieved {len(result)} articles for {symbol} "
                       f"({status['requests_used']}/{status['daily_limit']} used, "
                       f"{status['usage_percent']}%)")
            return result
            
        except Exception as e:
            logger.error(f"Error getting news sentiment for {symbol}: {e}")
            return None
    
    def _get_query(self, symbol: str) -> str:
        """Get search query for symbol."""
        query_map = {
            'EURUSD': 'EUR OR USD OR euro OR dollar OR forex',
            'GBPUSD': 'GBP OR USD OR pound OR dollar OR forex',
            'XAUUSD': 'gold OR XAU OR precious metals OR gold price',
            'XAGUSD': 'silver OR XAG OR precious metals OR silver price',
            'XAUEUR': 'gold OR XAU OR precious metals',
            'XAUGBP': 'gold OR XAU OR precious metals',
        }
        return query_map.get(symbol, symbol)
    
    def _calculate_sentiment(self, text: str) -> float:
        """Calculate sentiment score from text."""
        if not text:
            return 0.0
        
        # Enhanced sentiment word lists
        positive_words = [
            'up', 'rise', 'gain', 'positive', 'bullish', 'higher', 'breakout', 
            'rally', 'surge', 'growth', 'strong', 'profit', 'upside',
            'opportunity', 'support', 'breakthrough', 'momentum', 'upward',
            'boost', 'jump', 'soar', 'recovery', 'strength', 'outperform'
        ]
        
        negative_words = [
            'down', 'fall', 'loss', 'negative', 'bearish', 'lower', 'crash', 
            'drop', 'slump', 'decline', 'weak', 'risk', 'downside',
            'concern', 'fear', 'uncertainty', 'volatility', 'downward',
            'plunge', 'tumble', 'weakness', 'selloff', 'pressure'
        ]
        
        text_lower = text.lower()
        score = 0.0
        
        # Count positive and negative words
        pos_count = sum(1 for word in positive_words if word in text_lower)
        neg_count = sum(1 for word in negative_words if word in text_lower)
        
        # Calculate score
        total = pos_count + neg_count
        if total > 0:
            score = (pos_count - neg_count) / total
        
        return max(-1.0, min(1.0, score))
    
    def get_market_sentiment(self, days: int = 7) -> Dict[str, float]:
        """
        Get average sentiment for all assets with rate limiting.
        """
        from backend.config.settings import settings
        
        sentiment_results = {}
        
        for asset in settings.ASSETS:
            df = self.get_sentiment(asset, days)
            if df is not None and not df.empty:
                sentiment_results[asset] = float(df['sentiment_score'].mean())
            else:
                sentiment_results[asset] = 0.0
        
        return sentiment_results
    
    def get_rate_limit_status(self) -> Dict:
        """Get current rate limit status."""
        return self.rate_limiter.get_status()