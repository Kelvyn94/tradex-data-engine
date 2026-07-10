"""
ICT SMT (Smart Money Technique) Divergence Detection.
Identifies divergence between correlated assets.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class SMTAnalyzer:
    """
    ICT SMT (Smart Money Technique) analyzer.
    Detects divergence between correlated assets.
    """
    
    def __init__(self, lookback: int = 50):
        """
        Initialize SMT analyzer.
        
        Args:
            lookback: Number of candles to look back
        """
        self.lookback = lookback
        logger.info(f"SMTAnalyzer initialized (lookback={lookback})")
    
    def analyze(self, asset1_df: pd.DataFrame, asset2_df: pd.DataFrame,
               asset1_name: str = 'Asset1', asset2_name: str = 'Asset2') -> Dict:
        """
        Analyze SMT divergence between two assets.
        
        Args:
            asset1_df: DataFrame for asset 1
            asset2_df: DataFrame for asset 2
            asset1_name: Name of asset 1
            asset2_name: Name of asset 2
            
        Returns:
            Dictionary with SMT analysis
        """
        if asset1_df is None or asset1_df.empty or asset2_df is None or asset2_df.empty:
            return {'error': 'No data'}
        
        # Align data
        aligned = self._align_data(asset1_df, asset2_df)
        
        if aligned is None:
            return {'error': 'Could not align data'}
        
        df1, df2 = aligned
        
        # Calculate divergence
        divergence = self._detect_divergence(df1, df2)
        
        # Calculate correlation
        correlation = self._calculate_correlation(df1, df2)
        
        return {
            'asset1': asset1_name,
            'asset2': asset2_name,
            'divergence': divergence,
            'correlation': correlation,
            'has_divergence': len(divergence) > 0
        }
    
    def _align_data(self, df1: pd.DataFrame, df2: pd.DataFrame) -> Optional[Tuple[pd.DataFrame, pd.DataFrame]]:
        """Align two dataframes on timestamp."""
        if 'timestamp' not in df1.columns or 'timestamp' not in df2.columns:
            return None
        
        # Find common timestamps
        common_idx = set(df1['timestamp']).intersection(set(df2['timestamp']))
        common_idx = sorted(common_idx)
        
        if len(common_idx) < 10:
            return None
        
        df1_aligned = df1[df1['timestamp'].isin(common_idx)].sort_values('timestamp')
        df2_aligned = df2[df2['timestamp'].isin(common_idx)].sort_values('timestamp')
        
        return (df1_aligned, df2_aligned)
    
    def _detect_divergence(self, df1: pd.DataFrame, df2: pd.DataFrame) -> List[Dict]:
        """
        Detect divergence between two assets.
        """
        divergences = []
        
        # Get swing highs and lows
        swings1 = self._find_swings(df1)
        swings2 = self._find_swings(df2)
        
        # Check for bearish divergence: higher high in asset1, lower high in asset2
        for i in range(1, len(swings1['highs'])):
            high1 = swings1['highs'][i]
            high2 = None
            
            # Find corresponding high in asset2
            for h2 in swings2['highs']:
                if abs(h2['timestamp'] - high1['timestamp']) < timedelta(hours=4):
                    high2 = h2
                    break
            
            if high2 and high1['price'] > swings1['highs'][i-1]['price']:
                if high2['price'] < swings2['highs'][i-1]['price']:
                    divergences.append({
                        'type': 'BEARISH_DIVERGENCE',
                        'timestamp': high1['timestamp'],
                        'description': f"Higher high in asset1 ({high1['price']:.4f}) vs lower high in asset2 ({high2['price']:.4f})",
                        'asset1_high': float(high1['price']),
                        'asset2_high': float(high2['price'])
                    })
        
        # Check for bullish divergence: lower low in asset1, higher low in asset2
        for i in range(1, len(swings1['lows'])):
            low1 = swings1['lows'][i]
            low2 = None
            
            for l2 in swings2['lows']:
                if abs(l2['timestamp'] - low1['timestamp']) < timedelta(hours=4):
                    low2 = l2
                    break
            
            if low2 and low1['price'] < swings1['lows'][i-1]['price']:
                if low2['price'] > swings2['lows'][i-1]['price']:
                    divergences.append({
                        'type': 'BULLISH_DIVERGENCE',
                        'timestamp': low1['timestamp'],
                        'description': f"Lower low in asset1 ({low1['price']:.4f}) vs higher low in asset2 ({low2['price']:.4f})",
                        'asset1_low': float(low1['price']),
                        'asset2_low': float(low2['price'])
                    })
        
        return divergences
    
    def _find_swings(self, df: pd.DataFrame) -> Dict:
        """Find swing highs and lows."""
        high = df['high'].values
        low = df['low'].values
        timestamps = df['timestamp'].values
        length = len(high)
        
        swing_highs = []
        swing_lows = []
        
        swing_strength = 3
        
        for i in range(swing_strength, length - swing_strength):
            # Swing high
            if high[i] == max(high[i-swing_strength:i+swing_strength+1]):
                swing_highs.append({
                    'price': high[i],
                    'timestamp': timestamps[i]
                })
            
            # Swing low
            if low[i] == min(low[i-swing_strength:i+swing_strength+1]):
                swing_lows.append({
                    'price': low[i],
                    'timestamp': timestamps[i]
                })
        
        return {'highs': swing_highs, 'lows': swing_lows}
    
    def _calculate_correlation(self, df1: pd.DataFrame, df2: pd.DataFrame) -> float:
        """Calculate correlation between two assets."""
        # Use close prices
        close1 = df1['close'].values
        close2 = df2['close'].values
        
        if len(close1) < 2:
            return 0
        
        correlation = np.corrcoef(close1, close2)[0, 1]
        return float(correlation)