"""
ICT Liquidity Zones Detection.
Identifies areas where stop losses and limit orders are likely located.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class LiquidityDetector:
    """
    ICT Liquidity Zone detector.
    Identifies liquidity pools and stop-loss areas.
    """
    
    def __init__(self, lookback: int = 100, zone_width: float = 0.002):
        """
        Initialize Liquidity detector.
        
        Args:
            lookback: Number of candles to look back
            zone_width: Width of liquidity zone as percentage
        """
        self.lookback = lookback
        self.zone_width = zone_width
        logger.info(f"LiquidityDetector initialized (lookback={lookback})")
    
    def detect_liquidity_zones(self, df: pd.DataFrame) -> Dict:
        """
        Detect liquidity zones (above/below swing points).
        
        Returns:
            Dictionary with buy and sell liquidity zones
        """
        if df is None or df.empty:
            return {'buy_liquidity': [], 'sell_liquidity': []}
        
        swings = self._find_swings(df)
        
        buy_liquidity = []
        sell_liquidity = []
        
        # Sell liquidity: above swing highs (where stops are placed)
        for high in swings['highs'][-10:]:  # Last 10 swing highs
            sell_liquidity.append({
                'type': 'SELL_LIQUIDITY',
                'level': float(high['price']),
                'zone_high': float(high['price'] * (1 + self.zone_width)),
                'zone_low': float(high['price'] * (1 - self.zone_width)),
                'timestamp': high['timestamp'],
                'strength': self._calculate_strength(df, high['price'], 'high')
            })
        
        # Buy liquidity: below swing lows (where stops are placed)
        for low in swings['lows'][-10:]:  # Last 10 swing lows
            buy_liquidity.append({
                'type': 'BUY_LIQUIDITY',
                'level': float(low['price']),
                'zone_high': float(low['price'] * (1 + self.zone_width)),
                'zone_low': float(low['price'] * (1 - self.zone_width)),
                'timestamp': low['timestamp'],
                'strength': self._calculate_strength(df, low['price'], 'low')
            })
        
        return {
            'buy_liquidity': buy_liquidity,
            'sell_liquidity': sell_liquidity
        }
    
    def _find_swings(self, df: pd.DataFrame) -> Dict:
        """Find swing highs and lows."""
        high = df['high'].values
        low = df['low'].values
        length = len(high)
        
        swing_highs = []
        swing_lows = []
        
        swing_strength = 3
        
        for i in range(swing_strength, length - swing_strength):
            # Swing high
            if high[i] == max(high[i-swing_strength:i+swing_strength+1]):
                swing_highs.append({
                    'price': high[i],
                    'timestamp': df.index[i] if hasattr(df, 'index') else i
                })
            
            # Swing low
            if low[i] == min(low[i-swing_strength:i+swing_strength+1]):
                swing_lows.append({
                    'price': low[i],
                    'timestamp': df.index[i] if hasattr(df, 'index') else i
                })
        
        return {'highs': swing_highs, 'lows': swing_lows}
    
    def _calculate_strength(self, df: pd.DataFrame, price: float, 
                            level_type: str) -> str:
        """Calculate strength of liquidity zone."""
        recent = df.iloc[-50:]  # Last 50 candles
        
        if level_type == 'high':
            # How many times price tested this level
            touches = sum(1 for h in recent['high'] if abs(h - price) / price < 0.001)
        else:
            touches = sum(1 for l in recent['low'] if abs(l - price) / price < 0.001)
        
        if touches > 5:
            return 'STRONG'
        elif touches > 2:
            return 'MODERATE'
        else:
            return 'WEAK'
    
    def get_nearest_liquidity(self, df: pd.DataFrame, current_price: float) -> Dict:
        """Get nearest buy and sell liquidity zones."""
        zones = self.detect_liquidity_zones(df)
        
        buy_zones = zones['buy_liquidity']
        sell_zones = zones['sell_liquidity']
        
        nearest_buy = None
        nearest_sell = None
        
        # Nearest buy liquidity (below current price)
        for zone in buy_zones:
            if zone['level'] < current_price:
                if nearest_buy is None or zone['level'] > nearest_buy['level']:
                    nearest_buy = zone
        
        # Nearest sell liquidity (above current price)
        for zone in sell_zones:
            if zone['level'] > current_price:
                if nearest_sell is None or zone['level'] < nearest_sell['level']:
                    nearest_sell = zone
        
        return {
            'nearest_buy': nearest_buy,
            'nearest_sell': nearest_sell
        }