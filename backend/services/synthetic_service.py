"""
Service for creating synthetic assets from existing data.
TradeX Data Engine - Synthetic Asset Service
"""

import pandas as pd
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class SyntheticService:
    """Service for creating synthetic assets from existing data."""

    @staticmethod
    def _merge_key(df: pd.DataFrame, timeframe: str) -> pd.Series:
        """
        Key to merge two legs on. Daily/weekly bars from different Yahoo
        tickers are stamped at each *exchange's own* local midnight - COMEX
        futures (GC=F/SI=F) in America/New_York, FX pairs (=X) in
        Europe/London - so the same trading day lands at two different
        absolute instants (e.g. 2026-07-20 00:00-04:00 vs
        2026-07-20 00:00+01:00). Merging on the raw tz-aware timestamp never
        matches (0% match rate, confirmed live), and merging on a
        UTC-converted timestamp is actively wrong: converting London's
        +01:00 (BST) local midnight to UTC lands on the *previous* UTC date,
        which would pair a day with its neighbor instead of failing loudly.
        The correct key is each leg's own local calendar date, unconverted -
        that's what "2026-07-20" means on both tickers regardless of which
        exchange's clock stamped it.
        Intraday bars (1h/30m) are unaffected - both providers tick on the
        same UTC-aligned grid, so exact timestamp equality already works
        (verified: 93/93 and 186/186 matched live) and switching those to a
        date-only key would wrongly cross-join every bar within a day.
        """
        if timeframe in ('daily', 'weekly'):
            return df['timestamp'].dt.date
        return df['timestamp']

    @staticmethod
    def create_xaueur(xauusd: pd.DataFrame, eurusd: pd.DataFrame,
                      timeframe: str = 'daily') -> Optional[pd.DataFrame]:
        """
        Create XAUEUR from XAUUSD and EURUSD.

        XAUEUR = XAUUSD / EURUSD

        Args:
            xauusd: DataFrame with XAUUSD data
            eurusd: DataFrame with EURUSD data
            timeframe: Timeframe of the data

        Returns:
            DataFrame with XAUEUR data
        """
        if xauusd is None or xauusd.empty:
            logger.warning("XAUUSD data is empty")
            return None

        if eurusd is None or eurusd.empty:
            logger.warning("EURUSD data is empty")
            return None

        try:
            # Ensure both dataframes have timestamp as datetime
            xauusd_copy = xauusd.copy()
            eurusd_copy = eurusd.copy()

            xauusd_copy['timestamp'] = pd.to_datetime(xauusd_copy['timestamp'])
            eurusd_copy['timestamp'] = pd.to_datetime(eurusd_copy['timestamp'])

            xauusd_copy['_merge_key'] = SyntheticService._merge_key(xauusd_copy, timeframe)
            eurusd_copy['_merge_key'] = SyntheticService._merge_key(eurusd_copy, timeframe)

            # Merge on _merge_key (calendar date for daily/weekly, exact
            # timestamp for intraday - see _merge_key docstring), but keep
            # XAUUSD's own timestamp as the row's timestamp so downstream
            # storage/queries see one consistent clock for this symbol.
            merged = pd.merge(
                xauusd_copy[['_merge_key', 'timestamp', 'open', 'high', 'low', 'close']],
                eurusd_copy[['_merge_key', 'open', 'high', 'low', 'close']],
                on='_merge_key',
                suffixes=('_xau', '_eur')
            )

            if merged.empty:
                logger.warning("No matching timestamps between XAUUSD and EURUSD")
                return None
            
            # Calculate XAUEUR
            result = pd.DataFrame()
            result['timestamp'] = merged['timestamp']
            
            # XAUEUR = XAUUSD / EURUSD
            result['open'] = merged['open_xau'] / merged['open_eur']
            result['high'] = merged['high_xau'] / merged['low_eur']
            result['low'] = merged['low_xau'] / merged['high_eur']
            result['close'] = merged['close_xau'] / merged['close_eur']
            result['volume'] = 0
            
            # Remove any infinite or NaN values
            result = result.replace([float('inf'), float('-inf')], pd.NA)
            result = result.dropna()
            
            if result.empty:
                logger.warning("All XAUEUR calculations resulted in NaN")
                return None
            
            # Add metadata
            result['symbol'] = 'XAUEUR'
            result['timeframe'] = timeframe
            
            logger.info(f"Created synthetic XAUEUR: {len(result)} rows")
            return result
            
        except Exception as e:
            logger.error(f"Error creating XAUEUR: {e}")
            return None
    
    @staticmethod
    def create_xaugbp(xauusd: pd.DataFrame, gbpusd: pd.DataFrame, 
                      timeframe: str = 'daily') -> Optional[pd.DataFrame]:
        """
        Create XAUGBP from XAUUSD and GBPUSD.
        
        XAUGBP = XAUUSD / GBPUSD
        
        Args:
            xauusd: DataFrame with XAUUSD data
            gbpusd: DataFrame with GBPUSD data
            timeframe: Timeframe of the data
            
        Returns:
            DataFrame with XAUGBP data
        """
        if xauusd is None or xauusd.empty:
            logger.warning("XAUUSD data is empty")
            return None
        
        if gbpusd is None or gbpusd.empty:
            logger.warning("GBPUSD data is empty")
            return None
        
        try:
            # Ensure both dataframes have timestamp as datetime
            xauusd_copy = xauusd.copy()
            gbpusd_copy = gbpusd.copy()
            
            xauusd_copy['timestamp'] = pd.to_datetime(xauusd_copy['timestamp'])
            gbpusd_copy['timestamp'] = pd.to_datetime(gbpusd_copy['timestamp'])

            xauusd_copy['_merge_key'] = SyntheticService._merge_key(xauusd_copy, timeframe)
            gbpusd_copy['_merge_key'] = SyntheticService._merge_key(gbpusd_copy, timeframe)

            # See _merge_key docstring: calendar-date match for daily/weekly,
            # exact timestamp for intraday. XAUUSD's timestamp is kept as
            # the row's timestamp.
            merged = pd.merge(
                xauusd_copy[['_merge_key', 'timestamp', 'open', 'high', 'low', 'close']],
                gbpusd_copy[['_merge_key', 'open', 'high', 'low', 'close']],
                on='_merge_key',
                suffixes=('_xau', '_gbp')
            )

            if merged.empty:
                logger.warning("No matching timestamps between XAUUSD and GBPUSD")
                return None
            
            # Calculate XAUGBP
            result = pd.DataFrame()
            result['timestamp'] = merged['timestamp']
            
            # XAUGBP = XAUUSD / GBPUSD
            result['open'] = merged['open_xau'] / merged['open_gbp']
            result['high'] = merged['high_xau'] / merged['low_gbp']
            result['low'] = merged['low_xau'] / merged['high_gbp']
            result['close'] = merged['close_xau'] / merged['close_gbp']
            result['volume'] = 0
            
            # Remove any infinite or NaN values
            result = result.replace([float('inf'), float('-inf')], pd.NA)
            result = result.dropna()
            
            if result.empty:
                logger.warning("All XAUGBP calculations resulted in NaN")
                return None
            
            # Add metadata
            result['symbol'] = 'XAUGBP'
            result['timeframe'] = timeframe
            
            logger.info(f"Created synthetic XAUGBP: {len(result)} rows")
            return result
            
        except Exception as e:
            logger.error(f"Error creating XAUGBP: {e}")
            return None