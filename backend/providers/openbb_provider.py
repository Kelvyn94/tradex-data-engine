"""
OpenBB Provider for TradeX Data Engine.
"""

import pandas as pd
from datetime import datetime
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)

class OpenBBProvider:
    """OpenBB data provider implementation."""
    
    def __init__(self):
        self.name = "openbb"
        self.asset_map = {
            'EURUSD': 'EURUSD=X',
            'GBPUSD': 'GBPUSD=X',
            'XAUUSD': 'GC=F',      # Gold Futures
            'XAGUSD': 'SI=F',      # Silver Futures
            'XAUEUR': None,        # Not available on Yahoo - synthetic
            'XAUGBP': None,        # Not available on Yahoo - synthetic
        }
        self.timeframe_map = {
            'weekly': '1W',        # FIXED: Use '1W' not '1wk'
            'daily': '1d',
            '4h': '1h',            # We'll aggregate 4h from 1h
            '1h': '1h',
            '30m': '30m',
        }
        logger.info("OpenBBProvider initialized")
        logger.info(f"Supported assets: {self.get_supported_assets()}")
        logger.info(f"Supported timeframes: {self.get_timeframes()}")
    
    def download_asset(self, symbol: str, timeframe: str, 
                      start_date: datetime, end_date: datetime) -> Optional[pd.DataFrame]:
        try:
            from openbb import obb
            
            if symbol not in self.asset_map:
                logger.warning(f"Asset {symbol} not supported")
                return None
            
            yahoo_symbol = self.asset_map[symbol]
            
            # Skip assets not available
            if yahoo_symbol is None:
                logger.warning(f"Asset {symbol} not available on Yahoo Finance")
                return None
            
            # Get interval, handle weekly specially
            interval = self.timeframe_map.get(timeframe, '1d')
            
            logger.info(f"Downloading {symbol} ({yahoo_symbol}) {timeframe} via OpenBB")
            
            # Download data using OpenBB
            data = obb.equity.price.historical(
                symbol=yahoo_symbol,
                start_date=start_date.strftime('%Y-%m-%d'),
                end_date=end_date.strftime('%Y-%m-%d'),
                interval=interval,
                provider='yfinance'
            )
            
            # Check if we got data
            if not data or not hasattr(data, 'results') or not data.results:
                logger.warning(f"No data for {symbol}")
                return None
            
            # Convert results to DataFrame
            records = []
            for item in data.results:
                if hasattr(item, '__dict__'):
                    record = item.__dict__.copy()
                    record = {k: v for k, v in record.items() if not k.startswith('_')}
                    records.append(record)
                else:
                    records.append(item)
            
            if not records:
                logger.warning(f"No records to convert for {symbol}")
                return None
            
            # Create DataFrame
            df = pd.DataFrame(records)
            
            # Rename columns to standard format
            df.rename(columns={
                'date': 'timestamp',
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'volume': 'volume'
            }, inplace=True)
            
            # Ensure all required columns exist
            required = ['timestamp', 'open', 'high', 'low', 'close']
            for col in required:
                if col not in df.columns:
                    logger.warning(f"Missing column {col} in data for {symbol}")
                    return None
            
            # Add volume if missing
            if 'volume' not in df.columns:
                df['volume'] = 0
            
            # Ensure timestamp is datetime
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # Add metadata
            df['symbol'] = symbol
            df['timeframe'] = timeframe
            
            # Sort by timestamp
            df = df.sort_values('timestamp').reset_index(drop=True)
            
            logger.info(f"Downloaded {len(df)} rows for {symbol} {timeframe}")
            return df
            
        except Exception as e:
            logger.error(f"Error downloading {symbol} {timeframe}: {e}")
            return None
    
    def get_supported_assets(self) -> List[str]:
        return [asset for asset, symbol in self.asset_map.items() if symbol is not None]
    
    def get_timeframes(self) -> List[str]:
        return list(self.timeframe_map.keys())
    
    def validate_symbol(self, symbol: str) -> bool:
        return symbol in self.asset_map and self.asset_map[symbol] is not None