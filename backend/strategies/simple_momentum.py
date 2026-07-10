"""
Simple Momentum Strategy - Tested and Working.
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class SimpleMomentumStrategy:
    """
    Simple momentum strategy that generates signals based on price movement.
    This is a TESTED strategy that works with the backtest engine.
    """
    
    def __init__(self,
                 asset: str = 'EURUSD',
                 lookback: int = 20,
                 entry_threshold: float = 0.005,
                 position_size: float = 0.05):
        """
        Initialize strategy.
        
        Args:
            asset: Asset to trade
            lookback: Lookback period for momentum
            entry_threshold: Minimum return % to enter (0.5%)
            position_size: Position size as % of capital
        """
        self.asset = asset
        self.lookback = lookback
        self.entry_threshold = entry_threshold
        self.position_size = position_size
        
        logger.info(f"SimpleMomentumStrategy: {asset}")
    
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Generate trading signals based on momentum.
        """
        signals = pd.DataFrame(index=data.index)
        signals[f'{self.asset}_signal'] = 0.0
        
        price_col = f'{self.asset}_close'
        if price_col not in data.columns:
            return signals
        
        prices = data[price_col]
        
        if len(prices) < self.lookback + 1:
            return signals
        
        # Calculate momentum (return over lookback period)
        momentum = prices.pct_change(periods=self.lookback)
        
        # Generate signals
        for i in range(self.lookback + 1, len(prices)):
            if momentum.iloc[i] > self.entry_threshold:
                signals.iloc[i, signals.columns.get_loc(f'{self.asset}_signal')] = self.position_size
            elif momentum.iloc[i] < -self.entry_threshold:
                signals.iloc[i, signals.columns.get_loc(f'{self.asset}_signal')] = -self.position_size
        
        return signals
    