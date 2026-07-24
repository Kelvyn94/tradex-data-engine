"""
Performance Statistics - Institutional Grade
Comprehensive performance metrics for strategy evaluation.
Used by: Hedge funds, quantitative analysts
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import logging
from scipy import stats

logger = logging.getLogger(__name__)


class PerformanceStatistics:
    """
    Professional performance statistics with:
    - Risk-adjusted returns (Sharpe, Sortino, Calmar)
    - Drawdown analysis
    - Win rate analysis
    - Factor analysis
    """
    
    def __init__(self, risk_free_rate: float = 0.02):
        """
        Initialize statistics calculator.
        
        Args:
            risk_free_rate: Annual risk-free rate (2% default)
        """
        self.risk_free_rate = risk_free_rate
        self.trades = []
        self.equity_curve = None
        self.daily_returns = None
        self.periods_per_year = None
        self.logger = logger
    
    def calculate_all(self, equity_curve: pd.Series,
                      trades: List[Dict]) -> Dict:
        """
        Calculate all performance statistics.

        Args:
            equity_curve: Series of equity values, indexed by timestamp.
                Works for any bar frequency (weekly/daily/4h/1h/30m) -
                annualization is inferred from the actual timestamps
                rather than assuming daily bars.
            trades: List of trade dictionaries

        Returns:
            Complete performance metrics
        """
        self.trades = trades
        self.equity_curve = equity_curve

        # "daily_returns" is a legacy name - it's really "per-period
        # returns," whatever the equity curve's actual bar frequency is.
        self.daily_returns = equity_curve.pct_change().dropna()
        self.periods_per_year = self._infer_periods_per_year()
        
        results = {
            # Basic metrics
            'total_return': self._calculate_total_return(),
            'annualized_return': self._calculate_annualized_return(),
            'volatility': self._calculate_volatility(),
            
            # Risk-adjusted returns
            'sharpe_ratio': self._calculate_sharpe_ratio(),
            'sortino_ratio': self._calculate_sortino_ratio(),
            'calmar_ratio': self._calculate_calmar_ratio(),
            
            # Drawdown analysis
            'max_drawdown': self._calculate_max_drawdown(),
            'avg_drawdown': self._calculate_avg_drawdown(),
            'max_drawdown_duration': self._calculate_max_drawdown_duration(),
            
            # Trade statistics
            'total_trades': len(trades),
            'win_rate': self._calculate_win_rate(),
            'average_win': self._calculate_average_win(),
            'average_loss': self._calculate_average_loss(),
            'profit_factor': self._calculate_profit_factor(),
            'expectancy': self._calculate_expectancy(),
            
            # Advanced metrics
            'kelly_fraction': self._calculate_kelly_fraction(),
            'recovery_factor': self._calculate_recovery_factor(),
            
            # Trade distribution
            'avg_trade_duration': self._calculate_avg_trade_duration(),
            'max_consecutive_wins': self._calculate_max_consecutive_wins(),
            'max_consecutive_losses': self._calculate_max_consecutive_losses(),
        }
        
        return results
    
    def _infer_periods_per_year(self) -> float:
        """
        Infer how many equity-curve periods occur per calendar year from
        the actual timestamps, instead of assuming daily bars (252/year).
        This engine's data spans weekly/daily/4h/1h/30m timeframes - a
        hardcoded 252 silently misstates annualized return/Sharpe/Sortino
        for anything but literal daily bars (e.g. treating 4h bars as
        daily bars overstates annualized volatility by ~sqrt(6x)).
        """
        if self.equity_curve is None or len(self.equity_curve) < 2:
            return 252.0

        index = self.equity_curve.index
        if not isinstance(index, pd.DatetimeIndex):
            return 252.0  # no real timestamps available - fall back

        total_seconds = (index[-1] - index[0]).total_seconds()
        if total_seconds <= 0:
            return 252.0

        seconds_per_period = total_seconds / (len(index) - 1)
        seconds_per_year = 365.25 * 24 * 3600
        return seconds_per_year / seconds_per_period

    def _calculate_total_return(self) -> float:
        """Calculate total return."""
        if self.equity_curve is None or len(self.equity_curve) < 2:
            return 0

        return (self.equity_curve.iloc[-1] - self.equity_curve.iloc[0]) / self.equity_curve.iloc[0]

    def _calculate_annualized_return(self) -> float:
        """Calculate annualized return from actual elapsed calendar time,
        not a bar-count/252 assumption."""
        if self.equity_curve is None or len(self.equity_curve) < 2:
            return 0

        total_return = self._calculate_total_return()
        index = self.equity_curve.index

        if isinstance(index, pd.DatetimeIndex):
            total_seconds = (index[-1] - index[0]).total_seconds()
            years = total_seconds / (365.25 * 24 * 3600) if total_seconds > 0 else 0
        else:
            years = len(self.equity_curve) / 252  # fallback: no real timestamps

        if years <= 0:
            return 0

        return (1 + total_return) ** (1 / years) - 1

    def _calculate_volatility(self) -> float:
        """Calculate annualized volatility."""
        if self.daily_returns is None or self.daily_returns.empty:
            return 0

        periods_per_year = getattr(self, 'periods_per_year', None) or self._infer_periods_per_year()
        return self.daily_returns.std() * np.sqrt(periods_per_year)

    def _calculate_sharpe_ratio(self) -> float:
        """Calculate Sharpe ratio."""
        if self.daily_returns is None or self.daily_returns.empty:
            return 0

        periods_per_year = getattr(self, 'periods_per_year', None) or self._infer_periods_per_year()
        excess_returns = self.daily_returns - self.risk_free_rate / periods_per_year
        if excess_returns.std() == 0:
            return 0

        return (excess_returns.mean() / excess_returns.std()) * np.sqrt(periods_per_year)

    def _calculate_sortino_ratio(self) -> float:
        """Calculate Sortino ratio (downside risk only)."""
        if self.daily_returns is None or self.daily_returns.empty:
            return 0

        periods_per_year = getattr(self, 'periods_per_year', None) or self._infer_periods_per_year()
        downside_returns = self.daily_returns[self.daily_returns < 0]
        if len(downside_returns) == 0 or downside_returns.std() == 0:
            return 0

        excess_returns = self.daily_returns - self.risk_free_rate / periods_per_year
        downside_deviation = downside_returns.std() * np.sqrt(periods_per_year)

        return (excess_returns.mean() * periods_per_year) / downside_deviation
    
    def _calculate_calmar_ratio(self) -> float:
        """Calculate Calmar ratio (return / max drawdown)."""
        annual_return = self._calculate_annualized_return()
        max_drawdown = self._calculate_max_drawdown()
        
        if max_drawdown == 0:
            return 0
        
        return annual_return / abs(max_drawdown)
    
    def _calculate_max_drawdown(self) -> float:
        """Calculate maximum drawdown."""
        if self.equity_curve is None or len(self.equity_curve) < 2:
            return 0
        
        peak = self.equity_curve.iloc[0]
        max_drawdown = 0
        
        for value in self.equity_curve:
            if value > peak:
                peak = value
            drawdown = (peak - value) / peak
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        return max_drawdown
    
    def _calculate_avg_drawdown(self) -> float:
        """Calculate average drawdown."""
        if self.equity_curve is None or len(self.equity_curve) < 2:
            return 0
        
        drawdowns = []
        peak = self.equity_curve.iloc[0]
        
        for value in self.equity_curve:
            if value > peak:
                peak = value
            drawdown = (peak - value) / peak
            if drawdown > 0:
                drawdowns.append(drawdown)
        
        if not drawdowns:
            return 0
        
        return sum(drawdowns) / len(drawdowns)
    
    def _calculate_max_drawdown_duration(self) -> int:
        """Calculate maximum drawdown duration in days."""
        if self.equity_curve is None or len(self.equity_curve) < 2:
            return 0
        
        max_duration = 0
        current_duration = 0
        peak = self.equity_curve.iloc[0]
        
        for value in self.equity_curve:
            if value > peak:
                peak = value
                current_duration = 0
            else:
                current_duration += 1
                if current_duration > max_duration:
                    max_duration = current_duration
        
        return max_duration
    
    def _calculate_win_rate(self) -> float:
        """Calculate win rate."""
        if not self.trades:
            return 0
        
        trades_with_pnl = [t for t in self.trades if 'pnl' in t]
        if not trades_with_pnl:
            return 0
        
        wins = sum(1 for t in trades_with_pnl if t['pnl'] > 0)
        return wins / len(trades_with_pnl)
    
    def _calculate_average_win(self) -> float:
        """Calculate average win."""
        if not self.trades:
            return 0
        
        wins = [t['pnl'] for t in self.trades if 'pnl' in t and t['pnl'] > 0]
        if not wins:
            return 0
        
        return sum(wins) / len(wins)
    
    def _calculate_average_loss(self) -> float:
        """Calculate average loss."""
        if not self.trades:
            return 0
        
        losses = [t['pnl'] for t in self.trades if 'pnl' in t and t['pnl'] < 0]
        if not losses:
            return 0
        
        return sum(losses) / len(losses)
    
    def _calculate_profit_factor(self) -> float:
        """Calculate profit factor (total wins / total losses)."""
        if not self.trades:
            return 0
        
        total_wins = sum(t['pnl'] for t in self.trades if 'pnl' in t and t['pnl'] > 0)
        total_losses = abs(sum(t['pnl'] for t in self.trades if 'pnl' in t and t['pnl'] < 0))
        
        if total_losses == 0:
            return float('inf')
        
        return total_wins / total_losses
    
    def _calculate_expectancy(self) -> float:
        """Calculate expectancy per trade."""
        if not self.trades:
            return 0
        
        trades_with_pnl = [t for t in self.trades if 'pnl' in t]
        if not trades_with_pnl:
            return 0
        
        total_pnl = sum(t['pnl'] for t in trades_with_pnl)
        return total_pnl / len(trades_with_pnl)
    
    def _calculate_kelly_fraction(self) -> float:
        """Calculate Kelly fraction."""
        win_rate = self._calculate_win_rate()
        avg_win = self._calculate_average_win()
        avg_loss = abs(self._calculate_average_loss())
        
        if avg_loss == 0:
            return 0
        
        return win_rate - ((1 - win_rate) * avg_loss / avg_win)
    
    def _calculate_recovery_factor(self) -> float:
        """Calculate recovery factor (total return / max drawdown)."""
        total_return = self._calculate_total_return()
        max_drawdown = self._calculate_max_drawdown()
        
        if max_drawdown == 0:
            return 0
        
        return total_return / abs(max_drawdown)
    
    def _calculate_avg_trade_duration(self) -> float:
        """Calculate average trade duration in hours."""
        # Simplified: would need entry/exit times
        return 0
    
    def _calculate_max_consecutive_wins(self) -> int:
        """Calculate maximum consecutive wins."""
        if not self.trades:
            return 0
        
        max_wins = 0
        current_wins = 0
        
        for t in self.trades:
            if 'pnl' in t and t['pnl'] > 0:
                current_wins += 1
                if current_wins > max_wins:
                    max_wins = current_wins
            else:
                current_wins = 0
        
        return max_wins
    
    def _calculate_max_consecutive_losses(self) -> int:
        """Calculate maximum consecutive losses."""
        if not self.trades:
            return 0
        
        max_losses = 0
        current_losses = 0
        
        for t in self.trades:
            if 'pnl' in t and t['pnl'] < 0:
                current_losses += 1
                if current_losses > max_losses:
                    max_losses = current_losses
            else:
                current_losses = 0
        
        return max_losses