"""
ICT BOS (Break of Structure) Detection.
Identifies when price breaks previous swing highs/lows.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import logging

from backend.ict.market_structure import MarketStructure

logger = logging.getLogger(__name__)


class BOSDetector:
    """
    ICT Break of Structure detector.
    Identifies BOS (break of previous swing high/low).
    """
    
    def __init__(self, confirmation_candles: int = 2):
        """
        Initialize BOS detector.
        
        Args:
            confirmation_candles: Number of candles to confirm BOS
        """
        self.confirmation_candles = confirmation_candles
        self.market_structure = MarketStructure()
        logger.info(f"BOSDetector initialized (confirmation={confirmation_candles})")
    
    def detect(self, df: pd.DataFrame) -> List[Dict]:
        """
        Detect all BOS events in the data.
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            List of BOS events
        """
        if df is None or df.empty:
            return []
        
        bos_events = []
        swings = self.market_structure._find_swings(df)
        
        highs = swings['highs']
        lows = swings['lows']
        
        if len(highs) < 2 or len(lows) < 2:
            return bos_events
        
        # Check for bullish BOS (break above previous high)
        for i in range(1, len(highs)):
            if highs[i]['price'] > highs[i-1]['price']:
                # Check for confirmation
                high_idx = highs[i]['index']
                if high_idx + self.confirmation_candles < len(df):
                    # Check if price stays above the broken level
                    above_level = all(
                        df['close'].iloc[high_idx + j] > highs[i-1]['price']
                        for j in range(self.confirmation_candles)
                    )
                    
                    if above_level:
                        bos_events.append({
                            'type': 'BULLISH_BOS',
                            'timestamp': highs[i]['timestamp'],
                            'index': high_idx,
                            'break_level': float(highs[i-1]['price']),
                            'new_high': float(highs[i]['price']),
                            'confirmed': True,
                            'strength': 'STRONG' if above_level else 'WEAK'
                        })
        
        # Check for bearish BOS (break below previous low)
        for i in range(1, len(lows)):
            if lows[i]['price'] < lows[i-1]['price']:
                low_idx = lows[i]['index']
                if low_idx + self.confirmation_candles < len(df):
                    below_level = all(
                        df['close'].iloc[low_idx + j] < lows[i-1]['price']
                        for j in range(self.confirmation_candles)
                    )
                    
                    if below_level:
                        bos_events.append({
                            'type': 'BEARISH_BOS',
                            'timestamp': lows[i]['timestamp'],
                            'index': low_idx,
                            'break_level': float(lows[i-1]['price']),
                            'new_low': float(lows[i]['price']),
                            'confirmed': True,
                            'strength': 'STRONG' if below_level else 'WEAK'
                        })
        
        return bos_events
    
    def get_latest_bos(self, df: pd.DataFrame) -> Optional[Dict]:
        """Get the most recent BOS event."""
        bos_events = self.detect(df)
        return bos_events[-1] if bos_events else None
    
    def is_active_bos(self, df: pd.DataFrame, lookback: int = 10) -> bool:
        """Check if there's an active BOS within the lookback period."""
        bos_events = self.detect(df)
        if not bos_events:
            return False
        
        latest = bos_events[-1]
        current_idx = len(df) - 1
        return (current_idx - latest['index']) <= lookback