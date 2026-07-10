"""
Pairs Trading Strategy V2 - Multi-Entry Version
Takes multiple positions and exits progressively.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class PairsTradingStrategyV2:
    """
    Multi-entry pairs trading with:
    - Multiple entry levels (scaling in)
    - Progressive exits
    - Dynamic position sizing
    """
    
    def __init__(self,
                 lookback: int = 20,
                 entry_levels: List[float] = None,
                 exit_levels: List[float] = None,
                 position_size: float = 0.05,
                 asset1: str = 'XAUEUR',
                 asset2: str = 'XAUGBP'):
        """
        Initialize multi-entry pairs trading strategy.
        
        Args:
            lookback: Rolling window for correlation
            entry_levels: List of z-score thresholds for entries (e.g., [1.0, 1.5, 2.0])
            exit_levels: List of z-score thresholds for exits (e.g., [0.5, 0.3, 0.1])
            position_size: Position size per entry
        """
        self.lookback = lookback
        self.entry_levels = entry_levels or [0.8, 1.2, 1.6]
        self.exit_levels = exit_levels or [0.5, 0.3, 0.1]
        self.position_size = position_size
        self.asset1 = asset1
        self.asset2 = asset2
        
        logger.info(f"Multi-Entry PairsTradingStrategyV2: {asset1}/{asset2}")
    
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """Generate multi-entry trading signals."""
        signals = pd.DataFrame(index=data.index)
        
        # Extract prices
        price1 = data[f'{self.asset1}_close']
        price2 = data[f'{self.asset2}_close']
        
        # Calculate spread and z-score
        spread = price1 - price2
        spread_mean = spread.rolling(window=self.lookback).mean()
        spread_std = spread.rolling(window=self.lookback).std()
        spread_zscore = (spread - spread_mean) / spread_std
        
        # Initialize signals
        signals['spread'] = spread_zscore
        signals[f'{self.asset1}_signal'] = 0.0
        signals[f'{self.asset2}_signal'] = 0.0
        
        # Build cumulative signal based on entry levels
        signal_value = 0.0
        
        # ENTRY: Scale in at multiple levels
        for i, entry_level in enumerate(self.entry_levels):
            # High spread: Short asset1, Long asset2
            if spread_zscore.iloc[-1] > entry_level:
                signal_value += self.position_size * (i + 1)
            # Low spread: Long asset1, Short asset2
            elif spread_zscore.iloc[-1] < -entry_level:
                signal_value -= self.position_size * (i + 1)
        
        # EXIT: Scale out at multiple levels
        for exit_level in self.exit_levels:
            if abs(spread_zscore.iloc[-1]) < exit_level:
                signal_value = signal_value * 0.5  # Reduce position
        
        # Apply signals
        if signal_value > 0:
            signals[f'{self.asset1}_signal'] = -signal_value
            signals[f'{self.asset2}_signal'] = signal_value
        elif signal_value < 0:
            signals[f'{self.asset1}_signal'] = -signal_value
            signals[f'{self.asset2}_signal'] = signal_value
        else:
            signals[f'{self.asset1}_signal'] = 0.0
            signals[f'{self.asset2}_signal'] = 0.0
        
        return signals