"""
Rolling Correlation - Dynamic Multi-Timeframe Analysis
Tracks how correlations change over time across all timeframes.
Used by: Two Sigma, Renaissance Technologies
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import logging

from backend.services.database_service import db_service
from backend.config.settings import settings

logger = logging.getLogger(__name__)


class RollingCorrelation:
    """
    Dynamic multi-timeframe rolling correlation analysis.
    """
    
    def __init__(self, window: int = 60):
        self.window = window
        self.rolling_correlations = {}
        self.correlation_history = {}
        self.timeframes = ['30m', '1h', '4h', 'daily', 'weekly']
        logger.info(f"RollingCorrelation initialized (window={window})")
    
    def calculate(self, asset1: str, asset2: str, 
                  timeframe: str = 'daily',
                  lookback: int = 730) -> Dict:
        """Calculate rolling correlation for a specific timeframe."""
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
        
        returns1 = df1.pct_change()
        returns2 = df2.pct_change()
        
        rolling_corr = returns1.rolling(window=self.window).corr(returns2)
        
        return {
            'asset1': asset1,
            'asset2': asset2,
            'timeframe': timeframe,
            'current_correlation': float(rolling_corr.iloc[-1]) if not rolling_corr.empty else None,
            'mean_correlation': float(rolling_corr.mean()) if not rolling_corr.empty else None,
            'std_correlation': float(rolling_corr.std()) if not rolling_corr.empty else None,
            'correlation_history': rolling_corr.to_dict()
        }
    
    def calculate_all_timeframes(self, asset1: str, asset2: str) -> Dict:
        """Calculate rolling correlation across all timeframes."""
        results = {}
        
        for tf in self.timeframes:
            results[tf] = self.calculate(asset1, asset2, tf)
        
        return results
    
    def calculate_pair_matrix(self, assets: List[str]) -> Dict:
        """Calculate rolling correlations for all pairs."""
        results = {}
        
        for i in range(len(assets)):
            for j in range(i + 1, len(assets)):
                key = f"{assets[i]}_{assets[j]}"
                results[key] = self.calculate_all_timeframes(assets[i], assets[j])
        
        return results