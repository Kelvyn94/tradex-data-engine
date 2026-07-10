"""
ICT Quarterly Theory.
Analyzes quarterly, monthly, and weekly levels.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class QuarterlyTheoryAnalyzer:
    """
    ICT Quarterly Theory analyzer.
    Identifies key quarterly, monthly, and weekly levels.
    """
    
    def __init__(self):
        logger.info("QuarterlyTheoryAnalyzer initialized")
    
    def analyze(self, df: pd.DataFrame) -> Dict:
        """
        Analyze quarterly theory levels.
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            Dictionary with quarterly theory analysis
        """
        if df is None or df.empty:
            return {'error': 'No data'}
        
        # Ensure timestamp is datetime
        if 'timestamp' in df.columns:
            timestamps = pd.to_datetime(df['timestamp'])
        else:
            timestamps = df.index
        
        current_price = df['close'].iloc[-1]
        current_date = timestamps[-1]
        
        # Calculate levels
        quarterly_levels = self._get_quarterly_levels(df)
        monthly_levels = self._get_monthly_levels(df)
        weekly_levels = self._get_weekly_levels(df)
        
        return {
            'quarterly_levels': quarterly_levels,
            'monthly_levels': monthly_levels,
            'weekly_levels': weekly_levels,
            'current_price': float(current_price),
            'current_date': current_date.isoformat() if hasattr(current_date, 'isoformat') else str(current_date),
            'nearest_resistance': self._find_nearest_resistance(quarterly_levels, current_price),
            'nearest_support': self._find_nearest_support(quarterly_levels, current_price)
        }
    
    def _get_quarterly_levels(self, df: pd.DataFrame) -> Dict:
        """Get quarterly open, high, low."""
        if 'timestamp' not in df.columns:
            return {'open': 0, 'high': 0, 'low': 0}
        
        # Get data for current quarter
        current_date = df['timestamp'].max()
        quarter_start = current_date - timedelta(days=current_date.day - 1)
        quarter_start = quarter_start - timedelta(days=quarter_start.month % 3 - 1)
        
        quarter_data = df[df['timestamp'] >= quarter_start]
        
        if quarter_data.empty:
            return {'open': 0, 'high': 0, 'low': 0}
        
        return {
            'open': float(quarter_data['open'].iloc[0]) if not quarter_data.empty else 0,
            'high': float(quarter_data['high'].max()) if not quarter_data.empty else 0,
            'low': float(quarter_data['low'].min()) if not quarter_data.empty else 0,
            'start': quarter_start.isoformat() if hasattr(quarter_start, 'isoformat') else str(quarter_start)
        }
    
    def _get_monthly_levels(self, df: pd.DataFrame) -> Dict:
        """Get monthly open, high, low."""
        if 'timestamp' not in df.columns:
            return {'open': 0, 'high': 0, 'low': 0}
        
        current_date = df['timestamp'].max()
        month_start = current_date - timedelta(days=current_date.day - 1)
        
        month_data = df[df['timestamp'] >= month_start]
        
        if month_data.empty:
            return {'open': 0, 'high': 0, 'low': 0}
        
        return {
            'open': float(month_data['open'].iloc[0]) if not month_data.empty else 0,
            'high': float(month_data['high'].max()) if not month_data.empty else 0,
            'low': float(month_data['low'].min()) if not month_data.empty else 0,
            'start': month_start.isoformat() if hasattr(month_start, 'isoformat') else str(month_start)
        }
    
    def _get_weekly_levels(self, df: pd.DataFrame) -> Dict:
        """Get weekly open, high, low."""
        if 'timestamp' not in df.columns:
            return {'open': 0, 'high': 0, 'low': 0}
        
        current_date = df['timestamp'].max()
        week_start = current_date - timedelta(days=current_date.weekday())
        
        week_data = df[df['timestamp'] >= week_start]
        
        if week_data.empty:
            return {'open': 0, 'high': 0, 'low': 0}
        
        return {
            'open': float(week_data['open'].iloc[0]) if not week_data.empty else 0,
            'high': float(week_data['high'].max()) if not week_data.empty else 0,
            'low': float(week_data['low'].min()) if not week_data.empty else 0,
            'start': week_start.isoformat() if hasattr(week_start, 'isoformat') else str(week_start)
        }
    
    def _find_nearest_resistance(self, levels: Dict, current_price: float) -> float:
        """Find nearest resistance level."""
        resistances = [
            levels.get('high', 0),
            levels.get('open', 0)
        ]
        
        nearest = None
        for level in resistances:
            if level > current_price:
                if nearest is None or level < nearest:
                    nearest = level
        
        return float(nearest) if nearest else 0
    
    def _find_nearest_support(self, levels: Dict, current_price: float) -> float:
        """Find nearest support level."""
        supports = [
            levels.get('low', 0),
            levels.get('open', 0)
        ]
        
        nearest = None
        for level in supports:
            if level < current_price:
                if nearest is None or level > nearest:
                    nearest = level
        
        return float(nearest) if nearest else 0