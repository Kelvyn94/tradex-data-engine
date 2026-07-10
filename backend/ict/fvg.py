"""
ICT FVG (Fair Value Gap) Detection.
Identifies 3-candle patterns with gaps.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class FVGDetector:
    """
    ICT Fair Value Gap detector.
    Identifies FVG (3-candle gap patterns).
    """
    
    def __init__(self, min_gap_size: float = 0.0005):
        """
        Initialize FVG detector.
        
        Args:
            min_gap_size: Minimum gap size to consider as FVG
        """
        self.min_gap_size = min_gap_size
        logger.info(f"FVGDetector initialized (min_gap_size={min_gap_size})")
    
    def detect(self, df: pd.DataFrame) -> List[Dict]:
        """
        Detect all FVGs in the data.
        """
        if df is None or df.empty:
            return []
        
        fvgs = []
        high = df['high'].values
        low = df['low'].values
        close = df['close'].values
        open_vals = df['open'].values
        
        for i in range(1, len(df) - 1):
            # Bullish FVG: gap up (low of current > high of previous)
            if low[i] > high[i-1]:
                gap_size = low[i] - high[i-1]
                if gap_size > self.min_gap_size:
                    fvgs.append({
                        'type': 'BULLISH',
                        'timestamp': df.index[i] if hasattr(df, 'index') else i,
                        'index': i,
                        'gap_high': float(low[i]),
                        'gap_low': float(high[i-1]),
                        'gap_size': float(gap_size),
                        'body_high': float(high[i]),
                        'body_low': float(low[i]),
                        'fill_probability': self._calculate_fill_probability(df, i, 'bullish'),
                        'is_filled': self._is_filled(df, i, 'bullish')
                    })
            
            # Bearish FVG: gap down (high of current < low of previous)
            if high[i] < low[i-1]:
                gap_size = low[i-1] - high[i]
                if gap_size > self.min_gap_size:
                    fvgs.append({
                        'type': 'BEARISH',
                        'timestamp': df.index[i] if hasattr(df, 'index') else i,
                        'index': i,
                        'gap_high': float(low[i-1]),
                        'gap_low': float(high[i]),
                        'gap_size': float(gap_size),
                        'body_high': float(high[i]),
                        'body_low': float(low[i]),
                        'fill_probability': self._calculate_fill_probability(df, i, 'bearish'),
                        'is_filled': self._is_filled(df, i, 'bearish')
                    })
        
        return fvgs
    
    def _calculate_fill_probability(self, df: pd.DataFrame, idx: int, 
                                     fvg_type: str) -> float:
        """Calculate probability of FVG being filled."""
        # Simplified: based on historical fill rates
        lookback = min(100, idx)
        
        if lookback < 10:
            return 0.5
        
        # Count filled gaps in lookback period
        filled = 0
        total = 0
        
        high = df['high'].values
        low = df['low'].values
        
        for i in range(max(0, idx - lookback), idx):
            if fvg_type == 'bullish':
                if i > 0 and low[i] > high[i-1]:
                    total += 1
                    if self._is_filled(df, i, 'bullish'):
                        filled += 1
            else:
                if i > 0 and high[i] < low[i-1]:
                    total += 1
                    if self._is_filled(df, i, 'bearish'):
                        filled += 1
        
        if total == 0:
            return 0.6
        
        return filled / total
    
    def _is_filled(self, df: pd.DataFrame, idx: int, fvg_type: str, 
                   lookahead: int = 50) -> bool:
        """Check if FVG has been filled."""
        if idx + lookahead >= len(df):
            return False
        
        high = df['high'].values
        low = df['low'].values
        
        if fvg_type == 'bullish':
            gap_low = high[idx-1]
            gap_high = low[idx]
        else:
            gap_low = high[idx]
            gap_high = low[idx-1]
        
        for i in range(idx + 1, min(idx + lookahead, len(df))):
            # Price has entered the gap
            if low[i] <= gap_high and high[i] >= gap_low:
                return True
        
        return False
    
    def get_unfilled_fvgs(self, df: pd.DataFrame) -> List[Dict]:
        """Get all unfilled FVGs."""
        all_fvgs = self.detect(df)
        return [f for f in all_fvgs if not f.get('is_filled', True)]
    
    def get_active_fvgs(self, df: pd.DataFrame) -> List[Dict]:
        """Get FVGs that are likely to be filled soon."""
        fvgs = self.detect(df)
        return [f for f in fvgs if f.get('fill_probability', 0) > 0.6]