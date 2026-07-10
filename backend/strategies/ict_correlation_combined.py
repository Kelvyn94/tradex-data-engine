"""
ICT + Correlation Combined Strategy - Backtest Ready.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ICTCorrelationCombined:
    """
    Combined ICT + Correlation strategy with backtest-ready signals.
    """
    
    def __init__(self,
                 asset: str = 'EURUSD',
                 timeframe: str = 'daily',
                 lookback: int = 50,
                 position_size: float = 0.05,
                 ict_weight: float = 0.6,
                 correlation_weight: float = 0.4,
                 correlation_assets: List[str] = None):
        """
        Initialize ICT + Correlation strategy.
        
        Args:
            asset: Primary asset to trade
            timeframe: Timeframe to use
            lookback: Lookback period
            position_size: Position size as % of capital
            ict_weight: Weight of ICT signals (0.6)
            correlation_weight: Weight of correlation signals (0.4)
            correlation_assets: Assets for correlation check
        """
        self.asset = asset
        self.timeframe = timeframe
        self.lookback = lookback
        self.position_size = position_size
        self.ict_weight = ict_weight
        self.correlation_weight = correlation_weight
        self.correlation_assets = correlation_assets or ['GBPUSD', 'XAUUSD']
        
        logger.info(f"ICT+Correlation Combined: {asset}")
    
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Generate combined trading signals.
        """
        signals = pd.DataFrame(index=data.index)
        signals[f'{self.asset}_signal'] = 0.0
        signals['ict_signal'] = 0.0
        signals['correlation_signal'] = 0.0
        signals['combined_signal'] = 0.0
        
        price_col = f'{self.asset}_close'
        if price_col not in data.columns:
            return signals
        
        prices = data[price_col]
        
        if len(prices) < self.lookback + 1:
            return signals
        
        # 1. ICT Signals
        ict_signals = self._get_ict_signals(data)
        
        # 2. Correlation Signals
        correlation_signals = self._get_correlation_signals(data)
        
        # 3. Combine Signals
        for i in range(self.lookback + 1, len(prices)):
            ict_val = ict_signals.iloc[i] if i < len(ict_signals) else 0
            corr_val = correlation_signals.iloc[i] if i < len(correlation_signals) else 0
            
            combined = (ict_val * self.ict_weight) + (corr_val * self.correlation_weight)
            
            signals.iloc[i, signals.columns.get_loc('ict_signal')] = ict_val
            signals.iloc[i, signals.columns.get_loc('correlation_signal')] = corr_val
            signals.iloc[i, signals.columns.get_loc('combined_signal')] = combined
            
            # Apply position sizing
            if combined > 0.2:
                signals.iloc[i, signals.columns.get_loc(f'{self.asset}_signal')] = self.position_size
            elif combined < -0.2:
                signals.iloc[i, signals.columns.get_loc(f'{self.asset}_signal')] = -self.position_size
        
        return signals
    
    def _get_ict_signals(self, data: pd.DataFrame) -> pd.Series:
        """
        Generate ICT-based signals.
        """
        price_col = f'{self.asset}_close'
        prices = data[price_col]
        
        signals = pd.Series(index=data.index, dtype=float)
        signals[:] = 0.0
        
        if len(prices) < self.lookback:
            return signals
        
        # BOS detection
        rolling_high = prices.rolling(window=self.lookback).max()
        rolling_low = prices.rolling(window=self.lookback).min()
        
        for i in range(self.lookback + 1, len(prices)):
            signal = 0.0
            
            # Bullish BOS
            if prices.iloc[i] > rolling_high.iloc[i-1]:
                signal += 0.5
            # Bearish BOS
            elif prices.iloc[i] < rolling_low.iloc[i-1]:
                signal -= 0.5
            
            # Order Block detection (simplified)
            if i > 2:
                if prices.iloc[i-1] < prices.iloc[i-2] and prices.iloc[i] > prices.iloc[i-1]:
                    signal += 0.3
                elif prices.iloc[i-1] > prices.iloc[i-2] and prices.iloc[i] < prices.iloc[i-1]:
                    signal -= 0.3
            
            # FVG detection (simplified)
            if i > 2:
                if prices.iloc[i] > prices.iloc[i-1] and prices.iloc[i-1] > prices.iloc[i-2]:
                    signal += 0.2
                elif prices.iloc[i] < prices.iloc[i-1] and prices.iloc[i-1] < prices.iloc[i-2]:
                    signal -= 0.2
            
            signals.iloc[i] = signal
        
        return signals
    
    def _get_correlation_signals(self, data: pd.DataFrame) -> pd.Series:
        """
        Generate correlation-based signals.
        """
        price_col = f'{self.asset}_close'
        prices = data[price_col]
        
        signals = pd.Series(index=data.index, dtype=float)
        signals[:] = 0.0
        
        if len(prices) < self.lookback:
            return signals
        
        # Calculate correlation with other assets
        for i in range(self.lookback + 1, len(prices)):
            signal = 0.0
            bullish_count = 0
            bearish_count = 0
            
            for corr_asset in self.correlation_assets:
                corr_col = f'{corr_asset}_close'
                if corr_col in data.columns:
                    # Check if correlation asset is moving in same direction
                    if i > 1:
                        asset_move = prices.iloc[i] - prices.iloc[i-1]
                        corr_move = data[corr_col].iloc[i] - data[corr_col].iloc[i-1]
                        
                        if (asset_move > 0 and corr_move > 0) or (asset_move < 0 and corr_move < 0):
                            bullish_count += 1
                        else:
                            bearish_count += 1
            
            # Correlation signal
            if bullish_count > bearish_count:
                signal = 0.4
            elif bearish_count > bullish_count:
                signal = -0.4
            
            signals.iloc[i] = signal
        
        return signals