"""
Yahoo Finance data provider for the TradeX Data Engine.
"""

import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import logging

from backend.providers.base_provider import BaseProvider

logger = logging.getLogger(__name__)

class YahooProvider(BaseProvider):
    """
    Yahoo Finance data provider implementation.
    """
    
    def __init__(self):
        """Initialize Yahoo Provider."""
        self.name = "yahoo"
        self.supported_assets = ['EURUSD', 'GBPUSD', 'XAUUSD', 'XAGUSD']
        # Note: XAUEUR and XAUGBP are not available on Yahoo
        self.timeframe_map = {
            'weekly': '1wk',
            'daily': '1d',
            '4h': '1h',  # Will be aggregated
            '1h': '1h',
            '30m': '30m',
        }
        logger.info("YahooProvider initialized")
    
    def download_asset(self, symbol: str, timeframe: str, 
                      start_date: datetime, end_date: datetime) -> Optional[pd.DataFrame]:
        """
        Download asset data from Yahoo Finance.
        """
        try:
            # Check if asset is supported
            if symbol not in self.supported_assets:
                logger.warning(f"Asset {symbol} not supported by Yahoo")
                return None
            
            # Convert symbol to Yahoo format
            yahoo_symbol = self._convert_symbol(symbol)
            
            # Convert timeframe to Yahoo format
            yahoo_interval = self.timeframe_map.get(timeframe, '1d')
            
            logger.info(f"Downloading {symbol} ({yahoo_symbol}) {timeframe} from {start_date} to {end_date}")
            
            # Download data
            ticker = yf.Ticker(yahoo_symbol)
            df = ticker.history(
                start=start_date,
                end=end_date,
                interval=yahoo_interval,
                auto_adjust=True
            )
            
            if df.empty:
                logger.warning(f"No data downloaded for {symbol}")
                return None
            
            # Clean up the dataframe
            df = self._clean_dataframe(df, symbol, timeframe)
            
            logger.info(f"Downloaded {len(df)} rows for {symbol}")
            return df
            
        except Exception as e:
            logger.error(f"Error downloading {symbol}: {e}")
            return None
    
    def _convert_symbol(self, symbol: str) -> str:
        """Convert asset symbol to Yahoo Finance format."""
        if symbol in ['EURUSD', 'GBPUSD']:
            return f"{symbol}=X"
        elif symbol == 'XAUUSD':
            return 'GC=F'
        elif symbol == 'XAGUSD':
            return 'SI=F'
        return symbol
    
    def _clean_dataframe(self, df: pd.DataFrame, symbol: str, timeframe: str) -> pd.DataFrame:
        """Clean and normalize the downloaded dataframe."""
        df = df.reset_index()
        df.columns = df.columns.str.lower()
        df.rename(columns={'date': 'timestamp'}, inplace=True)
        
        expected_columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        df = df[expected_columns]
        
        df['symbol'] = symbol
        df['timeframe'] = timeframe
        
        return df
    
    def get_supported_assets(self) -> List[str]:
        return self.supported_assets
    
    def get_timeframes(self) -> List[str]:
        return list(self.timeframe_map.keys())
    
    def validate_symbol(self, symbol: str) -> bool:
        return symbol in self.supported_assets
