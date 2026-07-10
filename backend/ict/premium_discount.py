"""
ICT Premium/Discount Zones.
Identifies overbought and oversold zones within the dealing range.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class PremiumDiscountAnalyzer:
    """
    ICT Premium/Discount analyzer.
    Identifies premium (overbought) and discount (oversold) zones.
    """
    
    def __init__(self, lookback: int = 100):
        """
        Initialize Premium/Discount analyzer.
        
        Args:
            lookback: Number of candles to look back for range
        """
        self.lookback = lookback
        logger.info(f"PremiumDiscountAnalyzer initialized (lookback={lookback})")
    
    def analyze(self, df: pd.DataFrame) -> Dict:
        """
        Analyze premium/discount zones.
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            Dictionary with premium/discount analysis
        """
        if df is None or df.empty:
            return {'error': 'No data'}
        
        # Get the dealing range
        dealing_range = self._get_dealing_range(df)
        
        if dealing_range is None:
            return {'error': 'No dealing range found'}
        
        high = dealing_range['high']
        low = dealing_range['low']
        mid = (high + low) / 2
        current_price = df['close'].iloc[-1]
        
        # Calculate position within the range (0-100%)
        position = (current_price - low) / (high - low) * 100
        
        # Determine zone
        if position > 70:
            zone = 'PREMIUM'
            description = f"Price is in premium zone ({position:.1f}% of range)"
            action = 'LOOK_TO_SELL'
        elif position < 30:
            zone = 'DISCOUNT'
            description = f"Price is in discount zone ({position:.1f}% of range)"
            action = 'LOOK_TO_BUY'
        else:
            zone = 'FAIR_VALUE'
            description = f"Price is in fair value zone ({position:.1f}% of range)"
            action = 'WAIT'
        
        return {
            'zone': zone,
            'position': float(position),
            'description': description,
            'action': action,
            'range_high': float(high),
            'range_low': float(low),
            'range_mid': float(mid),
            'current_price': float(current_price),
            'premium_level': float(high - (high - low) * 0.3),
            'discount_level': float(low + (high - low) * 0.3)
        }
    
    def _get_dealing_range(self, df: pd.DataFrame) -> Optional[Dict]:
        """
        Get the dealing range (consolidation area).
        """
        if len(df) < self.lookback:
            return None
        
        recent = df.iloc[-self.lookback:]
        
        # Find the range
        high = recent['high'].max()
        low = recent['low'].min()
        
        # Check if range is significant
        range_size = (high - low) / low
        avg_range_size = (df['high'].max() - df['low'].min()) / df['low'].min()
        
        if range_size < avg_range_size * 0.1:
            # Range is too small, use larger lookback
            return self._get_dealing_range(df.iloc[-self.lookback*2:])
        
        return {
            'high': float(high),
            'low': float(low),
            'range_size': float(range_size)
        }
    
    def get_entry_zones(self, df: pd.DataFrame) -> Dict:
        """
        Get entry zones based on premium/discount.
        """
        analysis = self.analyze(df)
        
        return {
            'premium_entry': {
                'zone': 'SELL_ZONE',
                'level': analysis.get('premium_level'),
                'description': 'Look for sell entries in premium zone'
            },
            'discount_entry': {
                'zone': 'BUY_ZONE',
                'level': analysis.get('discount_level'),
                'description': 'Look for buy entries in discount zone'
            },
            'analysis': analysis
        }