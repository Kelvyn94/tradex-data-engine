"""
ICT Market Structure Analysis.
Identifies swing highs/lows and overall market structure.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class MarketStructure:
    """
    ICT Market Structure analyzer.
    Identifies swing highs, swing lows, and market phases.
    """
    
    def __init__(self, lookback: int = 100, swing_strength: int = 3):
        """
        Initialize Market Structure analyzer.
        
        Args:
            lookback: Number of candles to look back
            swing_strength: Number of candles to confirm swing
        """
        self.lookback = lookback
        self.swing_strength = swing_strength
        logger.info(f"MarketStructure initialized (lookback={lookback}, swing_strength={swing_strength})")
    
    def analyze(self, df: pd.DataFrame) -> Dict:
        """
        Complete market structure analysis.
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            Dictionary with structure analysis
        """
        if df is None or df.empty:
            return {'error': 'No data'}
        
        # Find swing highs and lows
        swings = self._find_swings(df)
        
        # Detect structure
        structure = self._detect_structure(df, swings)
        
        # Determine market phase
        phase = self._determine_phase(df)
        
        return {
            'swing_highs': swings['highs'],
            'swing_lows': swings['lows'],
            'current_structure': structure,
            'market_phase': phase,
            'current_price': float(df['close'].iloc[-1]),
            'timestamp': df.index[-1] if hasattr(df, 'index') else datetime.now()
        }
    
    def _find_swings(self, df: pd.DataFrame) -> Dict:
        """
        Find swing highs and lows using fractal method.
        """
        high = df['high'].values
        low = df['low'].values
        length = len(high)
        
        swing_highs = []
        swing_lows = []
        
        # Swing detection with confirmation
        for i in range(self.swing_strength, length - self.swing_strength):
            # Check for swing high
            is_swing_high = True
            for j in range(1, self.swing_strength + 1):
                if high[i] <= high[i-j] or high[i] <= high[i+j]:
                    is_swing_high = False
                    break
            
            if is_swing_high:
                swing_highs.append({
                    'index': i,
                    'price': float(high[i]),
                    'timestamp': df.index[i] if hasattr(df, 'index') else i,
                    'strength': self.swing_strength
                })
            
            # Check for swing low
            is_swing_low = True
            for j in range(1, self.swing_strength + 1):
                if low[i] >= low[i-j] or low[i] >= low[i+j]:
                    is_swing_low = False
                    break
            
            if is_swing_low:
                swing_lows.append({
                    'index': i,
                    'price': float(low[i]),
                    'timestamp': df.index[i] if hasattr(df, 'index') else i,
                    'strength': self.swing_strength
                })
        
        return {'highs': swing_highs, 'lows': swing_lows}
    
    def _detect_structure(self, df: pd.DataFrame, swings: Dict) -> Dict:
        """
        Detect current market structure.
        """
        highs = swings['highs']
        lows = swings['lows']
        
        if len(highs) < 2 or len(lows) < 2:
            return {'trend': 'UNDEFINED', 'description': 'Not enough swings'}
        
        # Get recent swings
        recent_highs = highs[-5:] if len(highs) >= 5 else highs
        recent_lows = lows[-5:] if len(lows) >= 5 else lows
        
        # Check for higher highs and higher lows (bullish)
        higher_highs = all(recent_highs[i]['price'] < recent_highs[i+1]['price'] 
                          for i in range(len(recent_highs)-1)) if len(recent_highs) > 1 else False
        
        higher_lows = all(recent_lows[i]['price'] < recent_lows[i+1]['price'] 
                         for i in range(len(recent_lows)-1)) if len(recent_lows) > 1 else False
        
        # Check for lower highs and lower lows (bearish)
        lower_highs = all(recent_highs[i]['price'] > recent_highs[i+1]['price'] 
                         for i in range(len(recent_highs)-1)) if len(recent_highs) > 1 else False
        
        lower_lows = all(recent_lows[i]['price'] > recent_lows[i+1]['price'] 
                        for i in range(len(recent_lows)-1)) if len(recent_lows) > 1 else False
        
        if higher_highs and higher_lows:
            trend = 'BULLISH'
            description = 'Higher highs and higher lows - Uptrend'
        elif lower_highs and lower_lows:
            trend = 'BEARISH'
            description = 'Lower highs and lower lows - Downtrend'
        else:
            trend = 'CONSOLIDATION'
            description = 'No clear trend - Consolidation/Range'
        
        return {
            'trend': trend,
            'description': description,
            'swing_highs_count': len(highs),
            'swing_lows_count': len(lows),
            'recent_high': recent_highs[-1]['price'] if recent_highs else None,
            'recent_low': recent_lows[-1]['price'] if recent_lows else None
        }
    
    def _determine_phase(self, df: pd.DataFrame) -> str:
        """
        Determine market phase (Accumulation, Markup, Distribution, Markdown).
        """
        close = df['close'].values
        length = len(close)
        
        if length < 50:
            return 'UNDEFINED'
        
        # Calculate rate of change
        roc_20 = (close[-1] - close[-20]) / close[-20] * 100 if length >= 20 else 0
        roc_50 = (close[-1] - close[-50]) / close[-50] * 100 if length >= 50 else 0
        
        # Detect volatility compression/expansion
        volatility = np.std(close[-20:]) / np.mean(close[-20:]) if length >= 20 else 0
        avg_volatility = np.std(close) / np.mean(close) if length > 0 else 0
        
        if roc_50 > 5 and roc_20 > 0:
            phase = 'MARKUP'
        elif roc_50 > 5 and roc_20 < 0:
            phase = 'DISTRIBUTION'
        elif roc_50 < -5 and roc_20 < 0:
            phase = 'MARKDOWN'
        elif roc_50 < -5 and roc_20 > 0:
            phase = 'ACCUMULATION'
        elif volatility < avg_volatility * 0.7:
            phase = 'CONSOLIDATION'
        else:
            phase = 'UNDEFINED'
        
        return phase
    
    def get_current_swing(self, df: pd.DataFrame) -> Dict:
        """Get the most recent swing high and low."""
        swings = self._find_swings(df)
        
        return {
            'last_swing_high': swings['highs'][-1] if swings['highs'] else None,
            'last_swing_low': swings['lows'][-1] if swings['lows'] else None,
            'highs_count': len(swings['highs']),
            'lows_count': len(swings['lows'])
        }