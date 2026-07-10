"""
ICT Trading Sessions Analysis.
Identifies London, New York, and Asia sessions with proper timezone handling.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta, time
from typing import Dict, List, Optional, Tuple
import pytz
import logging

logger = logging.getLogger(__name__)


class SessionAnalyzer:
    """
    ICT Session analyzer.
    Identifies London, New York, and Asia sessions.
    
    Session Times (New York Time / EST):
    - Asia Session: 6:00 PM - 12:00 AM (18:00 - 00:00 EST)
    - London Session: 1:00 AM - 5:00 AM (01:00 - 05:00 EST)
    - New York AM Session: 7:00 AM - 12:00 PM (07:00 - 12:00 EST)
    - New York PM Session: 12:00 PM - 6:00 PM (12:00 - 18:00 EST)
    """
    
    # Session definitions in EST (New York Time)
    SESSIONS = {
        'ASIA': {
            'start': time(18, 0),   # 6:00 PM EST
            'end': time(0, 0),      # 12:00 AM EST (midnight)
            'label': 'Asia Session',
            'timezone': 'US/Eastern'
        },
        'LONDON': {
            'start': time(1, 0),    # 1:00 AM EST
            'end': time(5, 0),      # 5:00 AM EST
            'label': 'London Session',
            'timezone': 'US/Eastern'
        },
        'NY_AM': {
            'start': time(7, 0),    # 7:00 AM EST
            'end': time(12, 0),     # 12:00 PM EST
            'label': 'New York AM Session',
            'timezone': 'US/Eastern'
        },
        'NY_PM': {
            'start': time(12, 0),   # 12:00 PM EST
            'end': time(18, 0),     # 6:00 PM EST
            'label': 'New York PM Session',
            'timezone': 'US/Eastern'
        }
    }
    
    # Killzone definitions (most active periods)
    KILLZONES = {
        'LONDON_KILLZONE': {
            'start': time(2, 0),    # 2:00 AM EST
            'end': time(5, 0),      # 5:00 AM EST
            'label': 'London Killzone',
            'session': 'LONDON'
        },
        'NY_KILLZONE': {
            'start': time(8, 0),    # 8:00 AM EST
            'end': time(11, 0),     # 11:00 AM EST
            'label': 'New York Killzone',
            'session': 'NY_AM'
        },
        'NY_PM_KILLZONE': {
            'start': time(13, 0),   # 1:00 PM EST
            'end': time(16, 0),     # 4:00 PM EST
            'label': 'New York PM Killzone',
            'session': 'NY_PM'
        }
    }
    
    def __init__(self, timezone_str: str = 'US/Eastern'):
        """
        Initialize Session Analyzer.
        
        Args:
            timezone_str: Timezone string (default: US/Eastern)
        """
        self.timezone = pytz.timezone(timezone_str)
        logger.info(f"SessionAnalyzer initialized (timezone={timezone_str})")
    
    def get_session(self, timestamp: datetime) -> Dict:
        """
        Get the session for a given timestamp.
        
        Args:
            timestamp: Datetime to check
            
        Returns:
            Dictionary with session information
        """
        # Convert to EST if needed
        if timestamp.tzinfo is None:
            timestamp = self.timezone.localize(timestamp)
        else:
            timestamp = timestamp.astimezone(self.timezone)
        
        dt_time = timestamp.time()
        
        # Check each session
        for session_name, session_info in self.SESSIONS.items():
            start = session_info['start']
            end = session_info['end']
            
            # Handle sessions that cross midnight (Asia)
            if start > end:  # Crosses midnight
                if dt_time >= start or dt_time < end:
                    return {
                        'session': session_name,
                        'label': session_info['label'],
                        'start_time': start.strftime('%H:%M'),
                        'end_time': end.strftime('%H:%M'),
                        'is_active': True
                    }
            else:
                if start <= dt_time < end:
                    return {
                        'session': session_name,
                        'label': session_info['label'],
                        'start_time': start.strftime('%H:%M'),
                        'end_time': end.strftime('%H:%M'),
                        'is_active': True
                    }
        
        return {
            'session': 'CLOSED',
            'label': 'Market Closed',
            'start_time': '--:--',
            'end_time': '--:--',
            'is_active': False
        }
    
    def get_killzone(self, timestamp: datetime) -> Optional[Dict]:
        """
        Get the killzone for a given timestamp.
        
        Args:
            timestamp: Datetime to check
            
        Returns:
            Dictionary with killzone information or None
        """
        if timestamp.tzinfo is None:
            timestamp = self.timezone.localize(timestamp)
        else:
            timestamp = timestamp.astimezone(self.timezone)
        
        dt_time = timestamp.time()
        
        for killzone_name, killzone_info in self.KILLZONES.items():
            start = killzone_info['start']
            end = killzone_info['end']
            
            if start <= dt_time < end:
                return {
                    'killzone': killzone_name,
                    'label': killzone_info['label'],
                    'session': killzone_info['session'],
                    'start_time': start.strftime('%H:%M'),
                    'end_time': end.strftime('%H:%M'),
                    'is_active': True
                }
        
        return {
            'killzone': 'NONE',
            'label': 'No Active Killzone',
            'session': None,
            'start_time': '--:--',
            'end_time': '--:--',
            'is_active': False
        }
    
    def analyze_candles(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add session and killzone information to candle data.
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            DataFrame with added session columns
        """
        if df is None or df.empty:
            return df
        
        # Ensure timestamp is datetime
        if 'timestamp' in df.columns:
            timestamps = pd.to_datetime(df['timestamp'])
        else:
            timestamps = df.index
        
        # Create new columns
        df = df.copy()
        df['session'] = ''
        df['session_label'] = ''
        df['killzone'] = ''
        df['killzone_label'] = ''
        df['is_killzone'] = False
        
        for i, ts in enumerate(timestamps):
            # Get session
            session_info = self.get_session(ts)
            df.loc[df.index[i], 'session'] = session_info['session']
            df.loc[df.index[i], 'session_label'] = session_info['label']
            
            # Get killzone
            killzone_info = self.get_killzone(ts)
            df.loc[df.index[i], 'killzone'] = killzone_info['killzone']
            df.loc[df.index[i], 'killzone_label'] = killzone_info['label']
            df.loc[df.index[i], 'is_killzone'] = killzone_info['is_active']
        
        return df
    
    def get_session_statistics(self, df: pd.DataFrame) -> Dict:
        """
        Calculate session statistics.
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            Dictionary with session statistics
        """
        if df is None or df.empty:
            return {}
        
        # Add session info
        df_analyzed = self.analyze_candles(df)
        
        stats = {}
        
        for session_name in self.SESSIONS.keys():
            session_data = df_analyzed[df_analyzed['session'] == session_name]
            
            if session_data.empty:
                stats[session_name] = {
                    'count': 0,
                    'avg_range': 0,
                    'avg_change': 0,
                    'win_rate': 0
                }
                continue
            
            # Calculate statistics
            avg_range = (session_data['high'] - session_data['low']).mean()
            avg_change = session_data['close'].pct_change().mean()
            
            # Calculate win rate (price closed higher than opened)
            wins = (session_data['close'] > session_data['open']).sum()
            win_rate = wins / len(session_data) * 100
            
            stats[session_name] = {
                'count': len(session_data),
                'avg_range': float(avg_range),
                'avg_change': float(avg_change),
                'win_rate': float(win_rate)
            }
        
        return stats
    
    def get_killzone_statistics(self, df: pd.DataFrame) -> Dict:
        """
        Calculate killzone statistics.
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            Dictionary with killzone statistics
        """
        if df is None or df.empty:
            return {}
        
        # Add killzone info
        df_analyzed = self.analyze_candles(df)
        
        stats = {}
        
        for killzone_name in self.KILLZONES.keys():
            killzone_data = df_analyzed[df_analyzed['killzone'] == killzone_name]
            
            if killzone_data.empty:
                stats[killzone_name] = {
                    'count': 0,
                    'avg_range': 0,
                    'avg_change': 0,
                    'win_rate': 0
                }
                continue
            
            # Calculate statistics
            avg_range = (killzone_data['high'] - killzone_data['low']).mean()
            avg_change = killzone_data['close'].pct_change().mean()
            
            wins = (killzone_data['close'] > killzone_data['open']).sum()
            win_rate = wins / len(killzone_data) * 100
            
            stats[killzone_name] = {
                'count': len(killzone_data),
                'avg_range': float(avg_range),
                'avg_change': float(avg_change),
                'win_rate': float(win_rate)
            }
        
        return stats
    
    def get_current_session_info(self) -> Dict:
        """
        Get current session information.
        
        Returns:
            Dictionary with current session info
        """
        now = datetime.now(self.timezone)
        
        session_info = self.get_session(now)
        killzone_info = self.get_killzone(now)
        
        return {
            'timestamp': now.isoformat(),
            'session': session_info,
            'killzone': killzone_info,
            'is_market_open': session_info['is_active']
        }
    
    def get_session_range(self, df: pd.DataFrame, session_name: str) -> Tuple[float, float]:
        """
        Get the high and low range for a specific session.
        
        Args:
            df: DataFrame with OHLCV data
            session_name: Name of the session
            
        Returns:
            Tuple of (high, low) for the session
        """
        df_analyzed = self.analyze_candles(df)
        session_data = df_analyzed[df_analyzed['session'] == session_name]
        
        if session_data.empty:
            return (0, 0)
        
        return (
            float(session_data['high'].max()),
            float(session_data['low'].min())
        )
    
    def get_next_session_start(self) -> datetime:
        """
        Get the start time of the next session.
        
        Returns:
            Datetime of the next session start
        """
        now = datetime.now(self.timezone)
        
        # Get current session
        current = self.get_session(now)
        current_name = current['session']
        
        # Find next session
        session_names = list(self.SESSIONS.keys())
        current_idx = session_names.index(current_name) if current_name in session_names else -1
        
        # If in a session, get next session
        if current_idx >= 0:
            next_idx = (current_idx + 1) % len(session_names)
            next_session = session_names[next_idx]
        else:
            next_session = 'ASIA'
        
        # Get the start time of next session
        session_info = self.SESSIONS[next_session]
        start_time = session_info['start']
        
        # Calculate next occurrence
        next_start = now.replace(
            hour=start_time.hour,
            minute=start_time.minute,
            second=0,
            microsecond=0
        )
        
        # If start time already passed today, add a day
        if next_start <= now:
            next_start += timedelta(days=1)
        
        return next_start