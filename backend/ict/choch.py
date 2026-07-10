"""
ICT CHOCH (Change of Character) Detection.
Identifies when market structure changes (trend reversal signals).
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import logging

from backend.ict.market_structure import MarketStructure

logger = logging.getLogger(__name__)


class CHOCHDetector:
    """
    ICT Change of Character detector.
    Identifies CHOCH (trend reversal signals).
    """
    
    def __init__(self, confirmation_candles: int = 3):
        """
        Initialize CHOCH detector.
        
        Args:
            confirmation_candles: Number of candles to confirm CHOCH
        """
        self.confirmation_candles = confirmation_candles
        self.market_structure = MarketStructure()
        logger.info(f"CHOCHDetector initialized (confirmation={confirmation_candles})")
    
    def detect(self, df: pd.DataFrame) -> List[Dict]:
        """
        Detect all CHOCH events in the data.
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            List of CHOCH events
        """
        if df is None or df.empty:
            return []
        
        choch_events = []
        swings = self.market_structure._find_swings(df)
        
        highs = swings['highs']
        lows = swings['lows']
        
        if len(highs) < 3 or len(lows) < 3:
            return choch_events
        
        # Check for bullish CHOCH (failed lower low, then higher high)
        for i in range(2, len(lows)):
            # Failed break of low (bearish trap)
            if lows[i]['price'] < lows[i-1]['price']:
                # Check for reversal: price moves above the previous high
                low_idx = lows[i]['index']
                
                # Find the next swing high after this low
                next_highs = [h for h in highs if h['index'] > low_idx]
                if next_highs:
                    next_high = next_highs[0]
                    
                    # Check if this high breaks above the previous high
                    prev_high = highs[i-1] if i-1 < len(highs) else None
                    if prev_high and next_high['price'] > prev_high['price']:
                        choch_events.append({
                            'type': 'BULLISH_CHOCH',
                            'timestamp': next_high['timestamp'],
                            'index': next_high['index'],
                            'description': 'Failed low break followed by higher high',
                            'low_break': float(lows[i]['price']),
                            'previous_high': float(prev_high['price']),
                            'new_high': float(next_high['price']),
                            'strength': 'STRONG'
                        })
        
        # Check for bearish CHOCH (failed higher high, then lower low)
        for i in range(2, len(highs)):
            # Failed break of high (bull trap)
            if highs[i]['price'] > highs[i-1]['price']:
                high_idx = highs[i]['index']
                
                # Find the next swing low after this high
                next_lows = [l for l in lows if l['index'] > high_idx]
                if next_lows:
                    next_low = next_lows[0]
                    
                    # Check if this low breaks below the previous low
                    prev_low = lows[i-1] if i-1 < len(lows) else None
                    if prev_low and next_low['price'] < prev_low['price']:
                        choch_events.append({
                            'type': 'BEARISH_CHOCH',
                            'timestamp': next_low['timestamp'],
                            'index': next_low['index'],
                            'description': 'Failed high break followed by lower low',
                            'high_break': float(highs[i]['price']),
                            'previous_low': float(prev_low['price']),
                            'new_low': float(next_low['price']),
                            'strength': 'STRONG'
                        })
        
        return choch_events
    
    def get_latest_choch(self, df: pd.DataFrame) -> Optional[Dict]:
        """Get the most recent CHOCH event."""
        choch_events = self.detect(df)
        return choch_events[-1] if choch_events else None
    
    def is_choch_active(self, df: pd.DataFrame, lookback: int = 20) -> bool:
        """Check if there's an active CHOCH within the lookback period."""
        choch_events = self.detect(df)
        if not choch_events:
            return False
        
        latest = choch_events[-1]
        current_idx = len(df) - 1
        return (current_idx - latest['index']) <= lookback