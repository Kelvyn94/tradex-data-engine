"""
ICT Order Blocks Detection.
Identifies bullish and bearish order blocks.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class OrderBlockDetector:
    """
    ICT Order Block detector.
    Identifies bullish and bearish order blocks.
    """
    
    def __init__(self, lookback: int = 100, min_candle_size: float = 0.001):
        """
        Initialize Order Block detector.
        
        Args:
            lookback: Number of candles to look back
            min_candle_size: Minimum candle size to consider as OB
        """
        self.lookback = lookback
        self.min_candle_size = min_candle_size
        logger.info(f"OrderBlockDetector initialized (lookback={lookback})")
    
    def find_bullish_obs(self, df: pd.DataFrame) -> List[Dict]:
        """
        Find bullish order blocks.
        Bullish OB = Last down candle before an up move.
        """
        if df is None or df.empty:
            return []
        
        obs = []
        close = df['close'].values
        open_vals = df['open'].values
        high = df['high'].values
        low = df['low'].values
        
        for i in range(2, len(df) - 1):
            # Check if this is a down candle (bearish)
            if close[i] < open_vals[i]:
                # Check if next candle is bullish (up move)
                if close[i+1] > open_vals[i+1]:
                    # Check candle size
                    candle_size = abs(close[i] - open_vals[i])
                    avg_size = np.mean(abs(close[max(0, i-20):i] - open_vals[max(0, i-20):i]))
                    
                    if candle_size > avg_size * 0.5:  # Significant candle
                        # Calculate OB zone
                        ob_zone = {
                            'type': 'BULLISH',
                            'timestamp': df.index[i] if hasattr(df, 'index') else i,
                            'index': i,
                            'high': float(high[i]),
                            'low': float(low[i]),
                            'open': float(open_vals[i]),
                            'close': float(close[i]),
                            'body_size': float(candle_size),
                            'entry_price': float(high[i]),  # Entry above high
                            'stop_loss': float(low[i]),      # Stop below low
                            'take_profit_1': float(high[i] + (high[i] - low[i]) * 1.5),
                            'take_profit_2': float(high[i] + (high[i] - low[i]) * 3),
                            'strength': 'STRONG' if candle_size > avg_size else 'NORMAL'
                        }
                        obs.append(ob_zone)
        
        return obs
    
    def find_bearish_obs(self, df: pd.DataFrame) -> List[Dict]:
        """
        Find bearish order blocks.
        Bearish OB = Last up candle before a down move.
        """
        if df is None or df.empty:
            return []
        
        obs = []
        close = df['close'].values
        open_vals = df['open'].values
        high = df['high'].values
        low = df['low'].values
        
        for i in range(2, len(df) - 1):
            # Check if this is an up candle (bullish)
            if close[i] > open_vals[i]:
                # Check if next candle is bearish (down move)
                if close[i+1] < open_vals[i+1]:
                    # Check candle size
                    candle_size = abs(close[i] - open_vals[i])
                    avg_size = np.mean(abs(close[max(0, i-20):i] - open_vals[max(0, i-20):i]))
                    
                    if candle_size > avg_size * 0.5:
                        ob_zone = {
                            'type': 'BEARISH',
                            'timestamp': df.index[i] if hasattr(df, 'index') else i,
                            'index': i,
                            'high': float(high[i]),
                            'low': float(low[i]),
                            'open': float(open_vals[i]),
                            'close': float(close[i]),
                            'body_size': float(candle_size),
                            'entry_price': float(low[i]),    # Entry below low
                            'stop_loss': float(high[i]),      # Stop above high
                            'take_profit_1': float(low[i] - (high[i] - low[i]) * 1.5),
                            'take_profit_2': float(low[i] - (high[i] - low[i]) * 3),
                            'strength': 'STRONG' if candle_size > avg_size else 'NORMAL'
                        }
                        obs.append(ob_zone)
        
        return obs
    
    def find_all_obs(self, df: pd.DataFrame) -> Dict:
        """Find all order blocks (bullish and bearish)."""
        return {
            'bullish': self.find_bullish_obs(df),
            'bearish': self.find_bearish_obs(df)
        }
    
    def get_latest_obs(self, df: pd.DataFrame) -> Optional[Dict]:
        """Get the most recent order block."""
        all_obs = self.find_all_obs(df)
        
        bullish = all_obs['bullish']
        bearish = all_obs['bearish']
        
        all_obs_list = bullish + bearish
        if not all_obs_list:
            return None
        
        return sorted(all_obs_list, key=lambda x: x['index'])[-1]