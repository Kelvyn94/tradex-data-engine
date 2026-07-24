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

        Previously computed each sub-signal from only the last row
        (.iloc[-1]) and assigned the resulting scalar to the entire
        signals column - broadcasting one end-of-data decision across
        the whole backtest period (severe lookahead bias, confirmed
        empirically: every nonzero row held the identical value).
        Rewritten to loop row-by-row like ICTCorrelationCombined/
        SimpleMomentumStrategy, so each row's signal only uses data up
        to and including that row.
        """
        signals = pd.DataFrame(index=data.index)
        signals[f'{self.asset}_signal'] = 0.0

        price_col = f'{self.asset}_close'
        if price_col not in data.columns:
            return signals

        prices = data[price_col]

        if len(prices) < self.lookback + 1:
            return signals

        # Precompute rolling series once (each is backward-looking by
        # construction - rolling() at index i only uses i and earlier).
        rolling_high = prices.rolling(window=self.lookback).max()
        rolling_low = prices.rolling(window=self.lookback).min()
        returns = prices.pct_change()
        volatility = returns.rolling(window=20).std()
        sma_20 = prices.rolling(window=20).mean()
        sma_50 = prices.rolling(window=50).mean()
        recent_high = prices.rolling(window=50).max()
        recent_low = prices.rolling(window=50).min()

        signal_col = signals.columns.get_loc(f'{self.asset}_signal')

        for i in range(self.lookback + 1, len(prices)):
            bos_signal = self._detect_bos(prices, rolling_high, rolling_low, i)
            momentum_signal = self._detect_momentum(prices, i)
            volatility_signal = self._detect_volatility_breakout(prices, volatility, i)
            trend_signal = self._detect_trend(prices, sma_20, sma_50, i)
            position_signal = self._detect_price_position(prices, recent_high, recent_low, i)

            combined = (
                bos_signal * 0.30 +
                momentum_signal * 0.25 +
                volatility_signal * 0.20 +
                trend_signal * 0.15 +
                position_signal * 0.10
            )

            if combined > self.entry_threshold:
                signals.iloc[i, signal_col] = self.position_size
            elif combined < -self.entry_threshold:
                signals.iloc[i, signal_col] = -self.position_size
            # else: leave at the 0.0 default already set for this row

        return signals

    def _detect_bos(self, prices: pd.Series, rolling_high: pd.Series,
                     rolling_low: pd.Series, i: int) -> float:
        """BOS/CHOCH detection as of row i, using only data up to i."""
        current = prices.iloc[i]
        prev = prices.iloc[i - 1]

        if current > rolling_high.iloc[i - 1]:
            return 1.0
        elif current < rolling_low.iloc[i - 1]:
            return -1.0
        elif i >= 2 and prev > rolling_high.iloc[i - 2] and current < rolling_high.iloc[i - 2]:
            return -0.7
        elif i >= 2 and prev < rolling_low.iloc[i - 2] and current > rolling_low.iloc[i - 2]:
            return 0.7

        return 0

    def _detect_momentum(self, prices: pd.Series, i: int) -> float:
        """Momentum via rate of change, as of row i."""
        if i < 20:
            return 0

        roc_5 = (prices.iloc[i] - prices.iloc[i - 5]) / prices.iloc[i - 5] * 100
        roc_10 = (prices.iloc[i] - prices.iloc[i - 10]) / prices.iloc[i - 10] * 100
        roc_20 = (prices.iloc[i] - prices.iloc[i - 20]) / prices.iloc[i - 20] * 100

        momentum = roc_5 * 0.5 + roc_10 * 0.3 + roc_20 * 0.2

        if momentum > 0.5:
            return 1.0
        elif momentum < -0.5:
            return -1.0
        else:
            return momentum / 0.5

    def _detect_volatility_breakout(self, prices: pd.Series, volatility: pd.Series, i: int) -> float:
        """
        Volatility breakout as of row i. The baseline "average volatility"
        is the expanding mean up to and including row i - the original
        used the mean over the ENTIRE series (including rows after i),
        which was itself a lookahead bug independent of the whole-column
        broadcast issue.
        """
        if i < 20:
            return 0

        current_vol = volatility.iloc[i]
        if pd.isna(current_vol):
            return 0

        avg_vol = volatility.iloc[:i + 1].mean()
        vol_ratio = current_vol / avg_vol if avg_vol and avg_vol > 0 else 1

        if vol_ratio > 1.5:
            return 0.8 if prices.iloc[i] > prices.iloc[i - 1] else -0.8
        elif vol_ratio > 1.2:
            return 0.4 if prices.iloc[i] > prices.iloc[i - 1] else -0.4

        return 0

    def _detect_trend(self, prices: pd.Series, sma_20: pd.Series, sma_50: pd.Series, i: int) -> float:
        """SMA crossover trend detection as of row i."""
        if i < 50:
            return 0

        current = prices.iloc[i]
        sma20_val = sma_20.iloc[i]
        sma50_val = sma_50.iloc[i]

        if pd.isna(sma20_val) or pd.isna(sma50_val):
            return 0

        if current > sma20_val > sma50_val:
            return 1.0
        elif current < sma20_val < sma50_val:
            return -1.0
        elif current > sma20_val:
            return 0.3
        elif current < sma20_val:
            return -0.3

        return 0

    def _detect_price_position(self, prices: pd.Series, recent_high: pd.Series,
                                recent_low: pd.Series, i: int) -> float:
        """Price position relative to recent range, as of row i."""
        if i < 50:
            return 0

        current = prices.iloc[i]
        high = recent_high.iloc[i]
        low = recent_low.iloc[i]

        if pd.isna(high) or pd.isna(low):
            return 0

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
