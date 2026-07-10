"""
Backtesting Engine - Hedge Fund Grade
Professional backtesting for pairs trading strategies.
"""

from backend.backtesting.engine import BacktestEngine
from backend.backtesting.statistics import PerformanceStatistics

__all__ = [
    'BacktestEngine',
    'PerformanceStatistics',
]