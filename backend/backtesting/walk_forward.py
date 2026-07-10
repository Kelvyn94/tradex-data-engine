"""
Walk-Forward Testing - Institutional Grade
Validates strategy robustness through out-of-sample testing.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Callable
from datetime import datetime, timedelta
import logging

from backend.backtesting.engine import BacktestEngine
from backend.backtesting.statistics import PerformanceStatistics

logger = logging.getLogger(__name__)


class WalkForwardAnalyzer:
    """
    Professional walk-forward testing with:
    - In-sample training
    - Out-of-sample testing
    - Rolling windows
    - Performance consistency check
    """
    
    def __init__(self, train_window: int = 252,
                 test_window: int = 63,
                 step_size: int = 63):
        """
        Initialize walk-forward analyzer.
        
        Args:
            train_window: Training window in days (1 year default)
            test_window: Testing window in days (3 months default)
            step_size: Step size in days (3 months default)
        """
        self.train_window = train_window
        self.test_window = test_window
        self.step_size = step_size
        self.results = []
        logger.info(f"WalkForwardAnalyzer initialized (train={train_window}, test={test_window})")
    
    def analyze(self, strategy: Callable,
                data: Dict[str, pd.DataFrame],
                optimize_func: Optional[Callable] = None) -> Dict:
        """
        Perform walk-forward analysis.
        
        Args:
            strategy: Strategy function
            data: Market data
            optimize_func: Optimization function
            
        Returns:
            Walk-forward results
        """
        # Get date range
        dates = self._get_common_dates(data)
        if dates is None or len(dates) < self.train_window + self.test_window:
            return {'error': 'Insufficient data'}
        
        logger.info(f"Running walk-forward analysis on {len(dates)} days of data")
        
        windows = []
        start_idx = 0
        
        while start_idx + self.train_window + self.test_window <= len(dates):
            train_end = start_idx + self.train_window
            test_end = train_end + self.test_window
            
            train_dates = dates[start_idx:train_end]
            test_dates = dates[train_end:test_end]
            
            # Get train and test data
            train_data = self._slice_data(data, train_dates[0], train_dates[-1])
            test_data = self._slice_data(data, test_dates[0], test_dates[-1])
            
            # Optimize strategy on training data
            if optimize_func:
                optimized_params = optimize_func(train_data)
                optimized_strategy = lambda d: strategy(d, **optimized_params)
            else:
                optimized_strategy = strategy
                optimized_params = {}
            
            # Run backtest on test data
            engine = BacktestEngine()
            result = engine.run(optimized_strategy, test_data)
            
            windows.append({
                'train_start': train_dates[0],
                'train_end': train_dates[-1],
                'test_start': test_dates[0],
                'test_end': test_dates[-1],
                'params': optimized_params,
                'result': result
            })
            
            start_idx += self.step_size
        
        self.results = windows
        
        # Calculate aggregate statistics
        aggregate = self._calculate_aggregate(windows)
        
        return {
            'windows': windows,
            'aggregate': aggregate,
            'total_windows': len(windows)
        }
    
    def _get_common_dates(self, data: Dict[str, pd.DataFrame]) -> List[datetime]:
        """Get common dates across all assets."""
        common_idx = None
        for df in data.values():
            if df is not None and not df.empty:
                if common_idx is None:
                    common_idx = set(df.index)
                else:
                    common_idx = common_idx.intersection(set(df.index))
        
        if common_idx is None:
            return None
        
        return sorted(common_idx)
    
    def _slice_data(self, data: Dict[str, pd.DataFrame],
                    start_date: datetime,
                    end_date: datetime) -> Dict[str, pd.DataFrame]:
        """Slice data to a date range."""
        sliced = {}
        for asset, df in data.items():
            if df is not None and not df.empty:
                sliced[asset] = df.loc[start_date:end_date]
        return sliced
    
    def _calculate_aggregate(self, windows: List[Dict]) -> Dict:
        """Calculate aggregate statistics across windows."""
        if not windows:
            return {}
        
        returns = []
        sharpe_ratios = []
        win_rates = []
        drawdowns = []
        
        for window in windows:
            result = window.get('result', {})
            if result:
                returns.append(result.get('total_return', 0))
                sharpe_ratios.append(result.get('sharpe_ratio', 0))
                win_rates.append(result.get('win_rate', 0))
                drawdowns.append(result.get('max_drawdown', 0))
        
        return {
            'mean_return': np.mean(returns) if returns else 0,
            'std_return': np.std(returns) if returns else 0,
            'mean_sharpe': np.mean(sharpe_ratios) if sharpe_ratios else 0,
            'mean_win_rate': np.mean(win_rates) if win_rates else 0,
            'mean_drawdown': np.mean(drawdowns) if drawdowns else 0,
            'consistency': 1 - (np.std(returns) / (abs(np.mean(returns)) + 0.01)) if returns else 0,
            'total_windows': len(windows)
        }