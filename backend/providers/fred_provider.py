"""
FRED (Federal Reserve Economic Data) provider with intelligent rate limiting.
Free Tier: 1000 requests/day - evenly distributed.
"""

import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import logging
import time

from backend.utils.rate_limiter import rate_limiter_manager

logger = logging.getLogger(__name__)

class FREDProvider:
    """FRED data provider with intelligent rate limiting."""
    
    def __init__(self, api_key: str = None):
        from backend.config.settings import settings
        self.api_key = api_key or settings.FRED_API_KEY
        self.base_url = "https://api.stlouisfed.org/fred"
        
        # Get rate limiter
        self.rate_limiter = rate_limiter_manager.get_limiter('fred')
        if not self.rate_limiter:
            from backend.utils.rate_limiter import RateLimiter
            self.rate_limiter = RateLimiter('fred', 1000, 1.0)
            rate_limiter_manager.limiters['fred'] = self.rate_limiter
        
        # Critical series only - simplified
        self.series_map = {
            'FEDFUNDS': {'id': 'FEDFUNDS', 'name': 'Federal Funds Rate'},
            'UNRATE': {'id': 'UNRATE', 'name': 'Unemployment Rate'},
            'DGS10': {'id': 'DGS10', 'name': '10-Year Treasury Yield'},
        }
        
        logger.info(f"FREDProvider initialized with {len(self.series_map)} series")
        status = self.rate_limiter.get_status()
        logger.info(f"Rate limit status: {status['requests_used']}/{status['daily_limit']} used "
                   f"({status['usage_percent']}%)")
    
    def get_series(self, series_id: str, start_date: Optional[datetime] = None, 
                   end_date: Optional[datetime] = None) -> Optional[pd.DataFrame]:
        """
        Get data from FRED API with intelligent rate limiting.
        """
        try:
            # Check rate limits
            if not self.rate_limiter.wait_if_needed():
                logger.warning(f"Rate limit reached for {series_id}, skipping")
                return None
            
            if start_date is None:
                start_date = datetime.now() - timedelta(days=365)
            if end_date is None:
                end_date = datetime.now()
            
            url = f"{self.base_url}/series/observations"
            params = {
                'series_id': series_id,
                'api_key': self.api_key,
                'file_type': 'json',
                'observation_start': start_date.strftime('%Y-%m-%d'),
                'observation_end': end_date.strftime('%Y-%m-%d'),
            }
            
            response = requests.get(url, params=params, timeout=30)
            data = response.json()
            
            if 'observations' not in data:
                logger.warning(f"No data for {series_id}")
                return None
            
            # Convert to DataFrame - FIXED: handle missing date column
            df = pd.DataFrame(data['observations'])
            
            # Check if 'date' column exists
            if 'date' not in df.columns:
                logger.error(f"No 'date' column in FRED response for {series_id}")
                return None
            
            df['date'] = pd.to_datetime(df['date'])
            df['value'] = pd.to_numeric(df['value'], errors='coerce')
            
            # Filter out None values
            df = df[['date', 'value']]
            df = df.dropna()
            df = df.rename(columns={'date': 'timestamp'})
            
            if df.empty:
                logger.warning(f"Empty data for {series_id}")
                return None
            
            logger.info(f"Downloaded {len(df)} rows for {series_id}")
            return df
            
        except Exception as e:
            logger.error(f"Error downloading {series_id}: {e}")
            return None
    
    def get_all_series(self, start_date: Optional[datetime] = None,
                      end_date: Optional[datetime] = None) -> Dict[str, pd.DataFrame]:
        """Download all series."""
        results = {}
        
        for name, info in self.series_map.items():
            df = self.get_series(info['id'], start_date, end_date)
            if df is not None:
                results[name] = df
                logger.info(f"Downloaded {name}: {len(df)} rows")
        
        return results
    
    def get_latest_values(self) -> Dict[str, float]:
        """Get latest values for all series."""
        latest_values = {}
        
        for name, info in self.series_map.items():
            df = self.get_series(info['id'], datetime.now() - timedelta(days=30), datetime.now())
            if df is not None and not df.empty:
                latest_values[name] = float(df['value'].iloc[-1])
            else:
                latest_values[name] = None
        
        return latest_values
    
    def get_rate_limit_status(self) -> Dict:
        """Get current rate limit status."""
        return self.rate_limiter.get_status()