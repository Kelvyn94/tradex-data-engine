"""
Correlation Service - Complete Multi-Timeframe Correlation Analysis.
Combines all correlation components for comprehensive multi-timeframe analysis.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging

from backend.correlation.matrix import CorrelationMatrix
from backend.correlation.rolling import RollingCorrelation
from backend.correlation.strength import CurrencyStrength
from backend.correlation.divergence import DivergenceDetector
from backend.correlation.heatmap import CorrelationHeatmap
from backend.correlation.multi_timeframe import MultiTimeframeCorrelation

from backend.services.database_service import db_service
from backend.config.settings import settings

logger = logging.getLogger(__name__)


class CorrelationService:
    """
    Complete multi-timeframe correlation analysis service.
    """
    
    def __init__(self):
        """Initialize all correlation components."""
        self.matrix = CorrelationMatrix()
        self.rolling = RollingCorrelation()
        self.strength = CurrencyStrength()
        self.divergence = DivergenceDetector()
        self.heatmap = CorrelationHeatmap()
        self.multi_timeframe = MultiTimeframeCorrelation()
        logger.info("CorrelationService initialized (multi-timeframe)")
    
    def analyze_all(self, timeframe: str = 'daily', 
                    lookback: int = 252) -> Dict[str, Any]:
        """Run complete correlation analysis for a specific timeframe."""
        assets = settings.ASSETS
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'timeframe': timeframe,
            'assets': assets
        }
        
        # 1. Correlation Matrix
        try:
            results['matrix'] = self.matrix.calculate(assets, timeframe, lookback)
            results['strong_correlations'] = self.matrix.get_strong_correlations()
            results['summary'] = self.matrix.get_correlation_summary()
        except Exception as e:
            logger.error(f"Matrix error: {e}")
            results['matrix'] = {'error': str(e)}
        
        # 2. Currency Strength
        try:
            results['currency_strength'] = self.strength.calculate(timeframe, lookback)
        except Exception as e:
            logger.error(f"Strength error: {e}")
            results['currency_strength'] = {'error': str(e)}
        
        # 3. Divergence Detection
        try:
            results['divergences'] = self.divergence.detect_all_pairs(assets)
        except Exception as e:
            logger.error(f"Divergence error: {e}")
            results['divergences'] = {'error': str(e)}
        
        # 4. Heatmap
        try:
            results['heatmap'] = self.heatmap.generate(assets, timeframe, lookback)
        except Exception as e:
            logger.error(f"Heatmap error: {e}")
            results['heatmap'] = {'error': str(e)}
        
        return results
    
    def analyze_multi_timeframe(self, assets: Optional[List[str]] = None) -> Dict:
        """
        Multi-timeframe correlation analysis - HEDGE FUND METHOD!
        Cracks correlation across ALL timeframes.
        """
        if assets is None:
            assets = settings.ASSETS
        
        # 1. Matrix across all timeframes
        matrix_results = self.matrix.calculate_all_timeframes(assets)
        
        # 2. Multi-timeframe pair analysis
        mtf_results = self.multi_timeframe.analyze_all_pairs(assets)
        insights = self.multi_timeframe.get_multi_timeframe_insights(assets)
        
        # 3. Rolling correlations across all timeframes
        rolling_results = self.rolling.calculate_pair_matrix(assets)
        
        # 4. Divergences across all timeframes
        divergence_results = self.divergence.detect_all_pairs(assets)
        
        # 5. Heatmaps across all timeframes
        heatmap_results = self.heatmap.generate_all_timeframes(assets)
        
        return {
            'timestamp': datetime.now().isoformat(),
            'assets': assets,
            'timeframes': self.matrix.timeframes,
            'matrix': matrix_results,
            'pair_analysis': mtf_results,
            'insights': insights,
            'rolling': rolling_results,
            'divergences': divergence_results,
            'heatmaps': heatmap_results,
            'summary': self._get_summary(matrix_results, insights)
        }
    
    def _get_summary(self, matrix_results: Dict, insights: List) -> Dict:
        """Get summary of multi-timeframe analysis."""
        # Find most correlated pair across all timeframes
        pair_correlations = {}
        
        timeframes_data = matrix_results.get('timeframes', {})
        for tf, result in timeframes_data.items():
            if 'correlation_matrix' in result:
                matrix = result['correlation_matrix']
                for i in range(len(matrix.columns)):
                    for j in range(i + 1, len(matrix.columns)):
                        key = f"{matrix.columns[i]}_{matrix.columns[j]}"
                        if key not in pair_correlations:
                            pair_correlations[key] = []
                        pair_correlations[key].append(matrix.iloc[i, j])
        
        # Average correlations across timeframes
        avg_correlations = {}
        for pair, corrs in pair_correlations.items():
            if len(corrs) == len(self.matrix.timeframes):
                avg_correlations[pair] = np.mean(corrs)
        
        sorted_pairs = sorted(avg_correlations.items(), key=lambda x: abs(x[1]), reverse=True)
        
        # Find best pairs for trading
        best_pairs = []
        for pair, corr in sorted_pairs[:5]:
            asset1, asset2 = pair.split('_')
            best_pairs.append({
                'pair': f"{asset1}/{asset2}",
                'average_correlation': corr,
                'recommendation': 'TRADE' if abs(corr) > 0.7 else 'MONITOR'
            })
        
        return {
            'most_correlated_pairs': best_pairs,
            'total_pairs_analyzed': len(avg_correlations),
            'timeframes_analyzed': self.matrix.timeframes
        }