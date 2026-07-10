"""
ICT Dealing Range Analysis.
Identifies the range where price is expected to trade (bias).
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class DealingRangeAnalyzer:
    """
    ICT Dealing Range analyzer.
    Identifies the key range for trading bias.
    """
    
    def __init__(self, lookback: int = 50, atr_multiple: float = 1.5):
        """
        Initialize Dealing Range analyzer.
        
        Args:
            lookback: Number of candles to look back
            atr_multiple: ATR multiple for range boundaries
        """
        self.lookback = lookback
        self.atr_multiple = atr_multiple
        logger.info(f"DealingRangeAnalyzer initialized (lookback={lookback})")
    
    def analyze(self, df: pd.DataFrame) -> Dict:
        """
        Analyze dealing range.
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            Dictionary with dealing range analysis
        """
        if df is None or df.empty:
            return {'error': 'No data'}
        
        recent = df.iloc[-self.lookback:]
        atr = self._calculate_atr(df, 14)
        
        # Find range
        high = recent['high'].max()
        low = recent['low'].min()
        mid = (high + low) / 2
        
        # Calculate ATR-based boundaries
        current_atr = atr.iloc[-1] if not atr.empty else (high - low) * 0.1
        atr_range = current_atr * self.atr_multiple
        
        current_price = df['close'].iloc[-1]
        
        # Determine bias
        if current_price > high - atr_range * 0.3:
            bias = 'BULLISH'
            description = f"Price near upper range, bullish bias"
        elif current_price < low + atr_range * 0.3:
            bias = 'BEARISH'
            description = f"Price near lower range, bearish bias"
        else:
            bias = 'NEUTRAL'
            description = f"Price in middle range, neutral bias"
        
        return {
            'range_high': float(high),
            'range_low': float(low),
            'range_mid': float(mid),
            'range_size': float(high - low),
            'current_price': float(current_price),
            'atr': float(current_atr),
            'bias': bias,
            'description': description,
            'upper_boundary': float(high + atr_range * 0.3),
            'lower_boundary': float(low - atr_range * 0.3),
            'entry_zones': {
                'buy_zone': float(low + (high - low) * 0.2),
                'sell_zone': float(high - (high - low) * 0.2)
            }
        }
    
    def _calculate_atr(self, df: pd.DataFrame, period: int) -> pd.Series:
        """Calculate ATR."""
        high = df['high']
        low = df['low']
        close = df['close'].shift(1)
        
        tr1 = high - low
        tr2 = (high - close).abs()
        tr3 = (low - close).abs()
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        
        return atr
    
    def get_trading_zones(self, df: pd.DataFrame) -> Dict:
        """
        Get trading zones based on dealing range.
        """
        analysis = self.analyze(df)
        
        return {
            'buy_zone': {
                'entry': analysis['entry_zones']['buy_zone'],
                'stop': analysis['lower_boundary'],
                'target': analysis['range_mid']
            },
            'sell_zone': {
                'entry': analysis['entry_zones']['sell_zone'],
                'stop': analysis['upper_boundary'],
                'target': analysis['range_mid']
            },
            'analysis': analysis
        }