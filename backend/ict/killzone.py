"""
ICT Killzone Detection.
Identifies high-probability trading periods within sessions.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta, time
from typing import Dict, List, Optional
import pytz
import logging

from backend.ict.sessions import SessionAnalyzer

logger = logging.getLogger(__name__)


class KillzoneDetector:
    """
    ICT Killzone detector.
    Identifies high-probability trading periods.
    """
    
    KILLZONES = {
        'LONDON_KILLZONE': {
            'start': time(2, 0),    # 2:00 AM EST
            'end': time(5, 0),      # 5:00 AM EST
            'session': 'LONDON',
            'label': 'London Killzone',
            'confidence': 0.75
        },
        'NY_KILLZONE': {
            'start': time(8, 0),    # 8:00 AM EST
            'end': time(11, 0),     # 11:00 AM EST
            'session': 'NY_AM',
            'label': 'New York Killzone',
            'confidence': 0.80
        },
        'NY_PM_KILLZONE': {
            'start': time(13, 0),   # 1:00 PM EST
            'end': time(16, 0),     # 4:00 PM EST
            'session': 'NY_PM',
            'label': 'New York PM Killzone',
            'confidence': 0.70
        },
        'ASIA_KILLZONE': {
            'start': time(20, 0),   # 8:00 PM EST
            'end': time(23, 0),     # 11:00 PM EST
            'session': 'ASIA',
            'label': 'Asia Killzone',
            'confidence': 0.55
        }
    }
    
    def __init__(self):
        self.session_analyzer = SessionAnalyzer()
        logger.info("KillzoneDetector initialized")
    
    def detect_killzones(self, df: pd.DataFrame) -> Dict:
        """
        Detect killzone periods in the data.
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            Dictionary with killzone analysis
        """
        if df is None or df.empty:
            return {}
        
        # Analyze sessions first
        df_analyzed = self.session_analyzer.analyze_candles(df)
        
        results = {}
        
        for killzone_name, killzone_info in self.KILLZONES.items():
            # Filter data within killzone
            killzone_data = df_analyzed[df_analyzed['killzone'] == killzone_name]
            
            if killzone_data.empty:
                results[killzone_name] = {
                    'count': 0,
                    'avg_range': 0,
                    'avg_volatility': 0,
                    'win_rate': 0,
                    'is_active': False
                }
                continue
            
            # Calculate statistics
            avg_range = (killzone_data['high'] - killzone_data['low']).mean()
            avg_volatility = killzone_data['close'].pct_change().std()
            
            wins = (killzone_data['close'] > killzone_data['open']).sum()
            win_rate = wins / len(killzone_data) * 100 if len(killzone_data) > 0 else 0
            
            results[killzone_name] = {
                'count': len(killzone_data),
                'avg_range': float(avg_range),
                'avg_volatility': float(avg_volatility),
                'win_rate': float(win_rate),
                'confidence': killzone_info['confidence'],
                'is_active': False
            }
        
        # Check if currently in a killzone
        now = datetime.now(pytz.timezone('US/Eastern'))
        current_killzone = self.session_analyzer.get_killzone(now)
        
        if current_killzone and current_killzone['killzone'] in results:
            results[current_killzone['killzone']]['is_active'] = True
            results[current_killzone['killzone']]['current_info'] = current_killzone
        
        return results
    
    def get_best_killzone(self, df: pd.DataFrame) -> Optional[Dict]:
        """
        Get the best performing killzone.
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            Best killzone information
        """
        results = self.detect_killzones(df)
        
        if not results:
            return None
        
        # Find killzone with highest win rate
        best = None
        best_score = -1
        
        for name, data in results.items():
            if data['count'] > 10:  # Need enough samples
                score = data['win_rate'] * data['confidence']
                if score > best_score:
                    best_score = score
                    best = {
                        'name': name,
                        **data
                    }
        
        return best
    
    def is_killzone_active(self) -> bool:
        """Check if currently in a killzone."""
        now = datetime.now(pytz.timezone('US/Eastern'))
        killzone_info = self.session_analyzer.get_killzone(now)
        return killzone_info['is_active'] if killzone_info else False
    
    def get_next_killzone(self) -> Dict:
        """Get information about the next killzone."""
        now = datetime.now(pytz.timezone('US/Eastern'))
        
        # Find next killzone
        for killzone_name, killzone_info in self.KILLZONES.items():
            start_time = killzone_info['start']
            
            next_start = now.replace(
                hour=start_time.hour,
                minute=start_time.minute,
                second=0,
                microsecond=0
            )
            
            # If start time already passed today, add a day
            if next_start <= now:
                next_start += timedelta(days=1)
            
            return {
                'killzone': killzone_name,
                'label': killzone_info['label'],
                'session': killzone_info['session'],
                'start_time': start_time.strftime('%H:%M'),
                'end_time': killzone_info['end'].strftime('%H:%M'),
                'next_start': next_start.isoformat(),
                'confidence': killzone_info['confidence']
            }
        
        return {}