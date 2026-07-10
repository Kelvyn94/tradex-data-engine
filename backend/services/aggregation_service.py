"""
Service for aggregating data to higher timeframes.
TradeX Data Engine - Aggregation Service
"""

import pandas as pd
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class AggregationService:
    """Service for aggregating data to higher timeframes."""
    
    @staticmethod
    def aggregate_4h(df: pd.DataFrame) -> Optional[pd.DataFrame]:
        """
        Aggregate 1h data to 4h candles.
        
        Args:
            df: DataFrame with 1h data (must have timestamp, open, high, low, close, volume)
            
        Returns:
            DataFrame with 4h data
        """
        if df is None or df.empty:
            logger.warning("Cannot aggregate empty DataFrame")
            return None
        
        # Make a copy to avoid modifying original
        df_copy = df.copy()
        
        # Ensure timestamp is datetime
        if 'timestamp' in df_copy.columns:
            df_copy['timestamp'] = pd.to_datetime(df_copy['timestamp'])
            df_copy = df_copy.set_index('timestamp')
        else:
            logger.error("DataFrame missing 'timestamp' column")
            return None
        
        # Check if we have the required columns
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        missing_columns = [col for col in required_columns if col not in df_copy.columns]
        if missing_columns:
            logger.error(f"Missing columns: {missing_columns}")
            return None
        
        # Resample to 4h (using lowercase 'h' for hour)
        resampled = df_copy.resample('4h').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        })
        
        # Remove rows with NaN values
        resampled = resampled.dropna()
        
        if resampled.empty:
            logger.warning("No 4h data after aggregation")
            return None
        
        # Reset index to have timestamp as column
        resampled = resampled.reset_index()
        
        # Add metadata if available in original
        if 'symbol' in df.columns:
            resampled['symbol'] = df['symbol'].iloc[0] if not df['symbol'].empty else 'UNKNOWN'
        else:
            resampled['symbol'] = 'UNKNOWN'
        
        if 'timeframe' in df.columns:
            resampled['timeframe'] = '4h'
        else:
            resampled['timeframe'] = '4h'
        
        logger.info(f"Aggregated {len(df)} rows to {len(resampled)} 4h candles")
        
        return resampled
    
    @staticmethod
    def aggregate_weekly(df: pd.DataFrame) -> Optional[pd.DataFrame]:
        """
        Aggregate daily data to weekly candles.
        
        Args:
            df: DataFrame with daily data
            
        Returns:
            DataFrame with weekly data
        """
        if df is None or df.empty:
            logger.warning("Cannot aggregate empty DataFrame")
            return None
        
        df_copy = df.copy()
        
        # Ensure timestamp is datetime
        if 'timestamp' in df_copy.columns:
            df_copy['timestamp'] = pd.to_datetime(df_copy['timestamp'])
            df_copy = df_copy.set_index('timestamp')
        else:
            logger.error("DataFrame missing 'timestamp' column")
            return None
        
        # Check if we have the required columns
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        missing_columns = [col for col in required_columns if col not in df_copy.columns]
        if missing_columns:
            logger.error(f"Missing columns: {missing_columns}")
            return None
        
        # Resample to weekly (W-MON for Monday start)
        resampled = df_copy.resample('W-MON').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        })
        
        # Remove rows with NaN values
        resampled = resampled.dropna()
        
        if resampled.empty:
            logger.warning("No weekly data after aggregation")
            return None
        
        # Reset index to have timestamp as column
        resampled = resampled.reset_index()
        
        # Add metadata if available in original
        if 'symbol' in df.columns:
            resampled['symbol'] = df['symbol'].iloc[0] if not df['symbol'].empty else 'UNKNOWN'
        else:
            resampled['symbol'] = 'UNKNOWN'
        
        if 'timeframe' in df.columns:
            resampled['timeframe'] = 'weekly'
        else:
            resampled['timeframe'] = 'weekly'
        
        logger.info(f"Aggregated {len(df)} rows to {len(resampled)} weekly candles")
        
        return resampled