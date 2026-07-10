"""
Correlation Engine for TradeX Data Engine.
Institutional-grade multi-timeframe correlation analysis.
"""

from backend.correlation.matrix import CorrelationMatrix
from backend.correlation.rolling import RollingCorrelation
from backend.correlation.strength import CurrencyStrength
from backend.correlation.divergence import DivergenceDetector
from backend.correlation.heatmap import CorrelationHeatmap
from backend.correlation.multi_timeframe import MultiTimeframeCorrelation

__all__ = [
    'CorrelationMatrix',
    'RollingCorrelation',
    'CurrencyStrength',
    'DivergenceDetector',
    'CorrelationHeatmap',
    'MultiTimeframeCorrelation',
]