"""
Aggressive ICT Strategy - Generates more trading signals.
Uses multiple ICT concepts with lower thresholds.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ICTAggressiveStrategy:
    """
    Aggressive ICT strategy with multiple signal sources.
    """
    
    def __init__(self,
                 asset: str = 'EURUSD',
                 timeframe: str = 'daily',
                 position_size: float = 0.05,
                 lookback: int = 50,
                 entry_threshold: float = 0.5):
        """
        Initialize aggressive ICT strategy.
        
        Args:
            asset: Primary asset to trade
            timeframe: Timeframe to use
            position_size: Position size as % of capital (5%)
            lookback: Lookback period
            entry_threshold: Lower threshold for entries (0.5)
        """
        self.asset = asset
        self.timeframe = timeframe
        self.position_size = position_size
        self.lookback = lookback
        self.entry_threshold = entry_threshold
        
        logger.info(f"ICTAggressiveStrategy: {asset} {timeframe}")
    
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Generate aggressive trading signals.
        """
        signals = pd.DataFrame(index=data.index)
        signals[f'{self.asset}_signal'] = 0.0
        
        price_col = f'{self.asset}_close'
        if price_col not in data.columns:
            return signals
        
        prices = data[price_col]
        
        if len(prices) < self.lookback:
            return signals
        
        # 1. Market Structure (BOS/CHOCH)
        bos_signal = self._detect_bos(prices)
        
        # 2. Momentum (RSI-like)
        momentum_signal = self._detect_momentum(prices)
        
        # 3. Volatility Breakout
        volatility_signal = self._detect_volatility_breakout(prices)
        
        # 4. Trend Strength
        trend_signal = self._detect_trend(prices)
        
        # 5. Price Position (near highs/lows)
        position_signal = self._detect_price_position(prices)
        
        # Combine signals (aggressive weighting)
        combined = (
            bos_signal * 0.30 +
            momentum_signal * 0.25 +
            volatility_signal * 0.20 +
            trend_signal * 0.15 +
            position_signal * 0.10
        )
        
        # Apply position sizing
        if combined > self.entry_threshold:
            signals[f'{self.asset}_signal'] = self.position_size
        elif combined < -self.entry_threshold:
            signals[f'{self.asset}_signal'] = -self.position_size
        elif abs(combined) < 0.2:
            signals[f'{self.asset}_signal'] = 0.0
        
        return signals
    
    def _detect_bos(self, prices: pd.Series) -> float:
        """Simple BOS detection."""
        if len(prices) < self.lookback:
            return 0
        
        rolling_high = prices.rolling(window=self.lookback).max()
        rolling_low = prices.rolling(window=self.lookback).min()
        
        current = prices.iloc[-1]
        prev = prices.iloc[-2]
        
        # Bullish BOS
        if current > rolling_high.iloc[-2]:
            return 1.0
        # Bearish BOS
        elif current < rolling_low.iloc[-2]:
            return -1.0
        # CHOCH
        elif prev > rolling_high.iloc[-3] and current < rolling_high.iloc[-3]:
            return -0.7
        elif prev < rolling_low.iloc[-3] and current > rolling_low.iloc[-3]:
            return 0.7
        
        return 0
    
    def _detect_momentum(self, prices: pd.Series) -> float:
        """Detect momentum using rate of change."""
        if len(prices) < 10:
            return 0
        
        roc_5 = (prices.iloc[-1] - prices.iloc[-5]) / prices.iloc[-5] * 100
        roc_10 = (prices.iloc[-1] - prices.iloc[-10]) / prices.iloc[-10] * 100
        roc_20 = (prices.iloc[-1] - prices.iloc[-20]) / prices.iloc[-20] * 100
        
        # Weighted momentum
        momentum = roc_5 * 0.5 + roc_10 * 0.3 + roc_20 * 0.2
        
        if momentum > 0.5:
            return 1.0
        elif momentum < -0.5:
            return -1.0
        else:
            return momentum / 0.5
    
    def _detect_volatility_breakout(self, prices: pd.Series) -> float:
        """Detect volatility breakout."""
        if len(prices) < 20:
            return 0
        
        # Calculate ATR-like volatility
        returns = prices.pct_change().dropna()
        volatility = returns.rolling(window=20).std()
        
        current_vol = volatility.iloc[-1]
        avg_vol = volatility.mean()
        vol_ratio = current_vol / avg_vol if avg_vol > 0 else 1
        
        # Breakout if volatility is high
        if vol_ratio > 1.5:
            # Check direction
            if prices.iloc[-1] > prices.iloc[-2]:
                return 0.8
            else:
                return -0.8
        elif vol_ratio > 1.2:
            # Moderate breakout
            if prices.iloc[-1] > prices.iloc[-2]:
                return 0.4
            else:
                return -0.4
        
        return 0
    
    def _detect_trend(self, prices: pd.Series) -> float:
        """Detect trend using SMA crossovers."""
        if len(prices) < 50:
            return 0
        
        sma_20 = prices.rolling(window=20).mean()
        sma_50 = prices.rolling(window=50).mean()
        
        current = prices.iloc[-1]
        sma20_val = sma_20.iloc[-1]
        sma50_val = sma_50.iloc[-1]
        
        if current > sma20_val > sma50_val:
            return 1.0
        elif current < sma20_val < sma50_val:
            return -1.0
        elif current > sma20_val:
            return 0.3
        elif current < sma20_val:
            return -0.3
        
        return 0
    
    def _detect_price_position(self, prices: pd.Series) -> float:
        """Detect price position relative to recent range."""
        if len(prices) < 50:
            return 0
        
        recent_high = prices.rolling(window=50).max()
        recent_low = prices.rolling(window=50).min()
        
        current = prices.iloc[-1]
        high = recent_high.iloc[-1]
        low = recent_low.iloc[-1]
        range_size = high - low
        
        if range_size == 0:
            return 0
        
        position = (current - low) / range_size
        
        if position > 0.8:
            return -0.5  # Near resistance - bearish
        elif position < 0.2:
            return 0.5   # Near support - bullish
        elif position > 0.6:
            return -0.2
        elif position < 0.4:
            return 0.2
        
        return 0