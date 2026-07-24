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
        """
        Generate multi-entry trading signals.

        Previously computed signal_value once from spread_zscore.iloc[-1]
        (only the last row) and assigned it to the ENTIRE signals column -
        broadcasting one end-of-data decision across the whole backtest
        period (severe lookahead bias, confirmed empirically: every
        nonzero row held the identical value). Rewritten to loop
        row-by-row, so each row's entry/exit levels are evaluated against
        that row's own z-score only.
        """
        signals = pd.DataFrame(index=data.index)

        # Extract prices
        price1 = data[f'{self.asset1}_close']
        price2 = data[f'{self.asset2}_close']

        # Calculate spread and z-score (rolling - backward-looking by
        # construction, safe to precompute once)
        spread = price1 - price2
        spread_mean = spread.rolling(window=self.lookback).mean()
        spread_std = spread.rolling(window=self.lookback).std()
        spread_zscore = (spread - spread_mean) / spread_std

        # Initialize signals
        signals['spread'] = spread_zscore
        signals[f'{self.asset1}_signal'] = 0.0
        signals[f'{self.asset2}_signal'] = 0.0

        col1 = signals.columns.get_loc(f'{self.asset1}_signal')
        col2 = signals.columns.get_loc(f'{self.asset2}_signal')

        for i in range(self.lookback, len(price1)):
            z = spread_zscore.iloc[i]
            if pd.isna(z):
                continue

            signal_value = 0.0

            # ENTRY: scale in at multiple levels, using only this row's z-score
            for level_idx, entry_level in enumerate(self.entry_levels):
                # High spread: Short asset1, Long asset2
                if z > entry_level:
                    signal_value += self.position_size * (level_idx + 1)
                # Low spread: Long asset1, Short asset2
                elif z < -entry_level:
                    signal_value -= self.position_size * (level_idx + 1)

            # EXIT: scale out at multiple levels
            for exit_level in self.exit_levels:
                if abs(z) < exit_level:
                    signal_value = signal_value * 0.5  # Reduce position

            if signal_value != 0:
                signals.iloc[i, col1] = -signal_value
                signals.iloc[i, col2] = signal_value
            # else: leave at the 0.0 default already set for this row

        return signals