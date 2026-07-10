"""
Divergence Detection - Multi-Timeframe Institutional Grade
Detects when correlated assets diverge across different timeframes.
Used by: Millennium Management, Two Sigma
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import logging
from scipy import stats

from backend.services.database_service import db_service
from backend.config.settings import settings

logger = logging.getLogger(__name__)


class DivergenceDetector:
    """
    Multi-timeframe divergence detection.
    """
    
    def __init__(self, window: int = 60, threshold: float = 2.0):
        self.window = window
        self.threshold = threshold
        self.divergences = {}
        self.timeframes = ['30m', '1h', '4h', 'daily', 'weekly']
        logger.info(f"DivergenceDetector initialized (window={window}, threshold={threshold})")
    
    def detect(self, asset1: str, asset2: str,
               timeframe: str = 'daily',
               lookback: int = 365) -> Dict:
        """Detect divergence between two assets on a specific timeframe."""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=lookback * 2)
        
        df1 = db_service.get_candles(asset1, timeframe, start_date, end_date)
        df2 = db_service.get_candles(asset2, timeframe, start_date, end_date)
        
        if df1 is None or df2 is None or df1.empty or df2.empty:
            return {'error': 'No data for one or both assets'}
        
        df1 = df1.set_index('timestamp')['close']
        df2 = df2.set_index('timestamp')['close']
        
        common_idx = df1.index.intersection(df2.index)
        df1 = df1.loc[common_idx]
        df2 = df2.loc[common_idx]
        
        # Calculate spread z-score
        spread = df1 - df2
        spread_mean = spread.rolling(window=self.window).mean()
        spread_std = spread.rolling(window=self.window).std()
        spread_zscore = (spread - spread_mean) / spread_std
        
        # Detect divergences
        divergences = []
        for i in range(self.window, len(spread_zscore)):
            if abs(spread_zscore.iloc[i]) > self.threshold:
                if i > 0 and abs(spread_zscore.iloc[i-1]) <= self.threshold:
                    divergences.append({
                        'date': spread_zscore.index[i].isoformat() if hasattr(spread_zscore.index[i], 'isoformat') else str(spread_zscore.index[i]),
                        'type': 'SPREAD_DIVERGENCE',
                        'direction': 'POSITIVE' if spread_zscore.iloc[i] > 0 else 'NEGATIVE',
                        'z_score': float(spread_zscore.iloc[i]),
                        'description': f"{asset1} diverging from {asset2} on {timeframe} by {abs(spread_zscore.iloc[i]):.2f} std devs"
                    })
        
        return {
            'asset1': asset1,
            'asset2': asset2,
            'timeframe': timeframe,
            'current_zscore': float(spread_zscore.iloc[-1]) if not spread_zscore.empty else 0,
            'is_diverging': abs(spread_zscore.iloc[-1]) > self.threshold if not spread_zscore.empty else False,
            'divergences': divergences[-5:],
            'total_divergences': len(divergences)
        }
    
    def detect_all_timeframes(self, asset1: str, asset2: str) -> Dict:
        """Detect divergences across all timeframes."""
        results = {}
        
        for tf in self.timeframes:
            results[tf] = self.detect(asset1, asset2, tf)
        
        return results
    
    def detect_all_pairs(self, assets: Optional[List[str]] = None) -> Dict:
        """Detect divergences for all pairs across all timeframes."""
        if assets is None:
            assets = settings.ASSETS
        
        results = {}
        
        for i in range(len(assets)):
            for j in range(i + 1, len(assets)):
                key = f"{assets[i]}_{assets[j]}"
                results[key] = self.detect_all_timeframes(assets[i], assets[j])
        
        return results