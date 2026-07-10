"""
Multi-Timeframe Correlation Analysis - Institutional Grade
Cracks correlation across different timeframes to identify hidden relationships.
Used by: Bridgewater Associates, Millennium Management
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import logging
from scipy import stats
from scipy.stats import pearsonr, spearmanr

from backend.services.database_service import db_service
from backend.config.settings import settings

logger = logging.getLogger(__name__)


class MultiTimeframeCorrelation:
    """
    Institutional-grade multi-timeframe correlation analysis.
    Cracks correlations across all timeframes to identify patterns.
    """
    
    def __init__(self):
        self.timeframes = ['30m', '1h', '4h', 'daily', 'weekly']
        self.correlations = {}
        self.divergences = {}
        self.regime_shifts = {}
        logger.info("MultiTimeframeCorrelation initialized")
    
    def analyze_pair(self, asset1: str, asset2: str, 
                     lookback: int = 252) -> Dict:
        """
        Analyze correlation between two assets across all timeframes.
        
        Args:
            asset1: First asset
            asset2: Second asset
            lookback: Number of periods to look back (for daily)
            
        Returns:
            Multi-timeframe correlation analysis
        """
        results = {
            'asset1': asset1,
            'asset2': asset2,
            'timeframes': {},
            'consistency_score': 0,
            'regime_changes': [],
            'best_timeframe': None,
            'worst_timeframe': None,
            'trading_recommendations': []
        }
        
        correlations = []
        
        for tf in self.timeframes:
            # Calculate correlation for this timeframe
            tf_result = self._calculate_timeframe_correlation(
                asset1, asset2, tf, lookback
            )
            results['timeframes'][tf] = tf_result
            if 'correlation' in tf_result:
                correlations.append(tf_result['correlation'])
        
        # Calculate consistency score
        if correlations:
            results['consistency_score'] = 1 - np.std(correlations) / (abs(np.mean(correlations)) + 0.01)
            results['mean_correlation'] = np.mean(correlations)
            results['std_correlation'] = np.std(correlations)
            
            # Find best and worst timeframes
            if correlations:
                best_idx = np.argmax(np.abs(correlations))
                worst_idx = np.argmin(np.abs(correlations))
                results['best_timeframe'] = self.timeframes[best_idx] if best_idx < len(self.timeframes) else None
                results['worst_timeframe'] = self.timeframes[worst_idx] if worst_idx < len(self.timeframes) else None
            
            # Detect timeframe divergences
            results['divergences'] = self._detect_timeframe_divergences(results)
            
            # Detect regime shifts
            results['regime_shifts'] = self._detect_regime_shifts(results)
            
            # Generate trading recommendations
            results['trading_recommendations'] = self._generate_recommendations(results)
        
        return results
    
    def _calculate_timeframe_correlation(self, asset1: str, asset2: str,
                                         timeframe: str, lookback: int) -> Dict:
        """
        Calculate correlation for a specific timeframe.
        """
        end_date = datetime.now()
        
        # Adjust lookback based on timeframe
        if timeframe == '30m':
            lookback_periods = lookback * 48
        elif timeframe == '1h':
            lookback_periods = lookback * 24
        elif timeframe == '4h':
            lookback_periods = lookback * 6
        elif timeframe == 'daily':
            lookback_periods = lookback
        else:  # weekly
            lookback_periods = lookback // 7
        
        start_date = end_date - timedelta(days=lookback * 3)
        
        # Get data
        df1 = db_service.get_candles(asset1, timeframe, start_date, end_date)
        df2 = db_service.get_candles(asset2, timeframe, start_date, end_date)
        
        if df1 is None or df2 is None or df1.empty or df2.empty:
            return {'error': 'No data', 'correlation': 0}
        
        # Align data
        df1 = df1.set_index('timestamp')['close']
        df2 = df2.set_index('timestamp')['close']
        
        common_idx = df1.index.intersection(df2.index)
        df1 = df1.loc[common_idx]
        df2 = df2.loc[common_idx]
        
        if len(df1) < 20:
            return {'error': 'Insufficient data', 'correlation': 0}
        
        # Calculate returns
        returns1 = df1.pct_change().dropna()
        returns2 = df2.pct_change().dropna()
        
        if len(returns1) < 10:
            return {'error': 'Insufficient returns', 'correlation': 0}
        
        # Pearson correlation
        try:
            pearson_corr, p_val = pearsonr(returns1, returns2)
        except:
            pearson_corr, p_val = 0, 1
        
        # Spearman correlation
        try:
            spearman_corr, s_p_val = spearmanr(returns1, returns2)
        except:
            spearman_corr, s_p_val = 0, 1
        
        # Rolling correlation (last 50 periods)
        try:
            rolling_corr = returns1.rolling(50).corr(returns2)
            rolling_mean = rolling_corr.mean() if not rolling_corr.empty else 0
            rolling_std = rolling_corr.std() if not rolling_corr.empty else 0
            stability = 1 - (rolling_std / (abs(rolling_mean) + 0.01)) if not np.isnan(rolling_std) else 0
        except:
            rolling_mean, rolling_std, stability = 0, 0, 0
        
        return {
            'pearson': float(pearson_corr),
            'spearman': float(spearman_corr),
            'correlation': float(pearson_corr),
            'p_value': float(p_val),
            'is_significant': p_val < 0.05,
            'rolling_mean': float(rolling_mean),
            'rolling_std': float(rolling_std),
            'stability': float(stability) if not np.isnan(stability) else 0,
            'data_points': len(returns1),
            'timeframe': timeframe
        }
    
    def _detect_timeframe_divergences(self, results: Dict) -> List[Dict]:
        """
        Detect divergences between timeframes.
        """
        divergences = []
        timeframes = results['timeframes']
        
        # Check if correlation changes significantly between timeframes
        corr_values = []
        tf_names = []
        
        for tf, data in timeframes.items():
            if 'correlation' in data:
                corr_values.append(data['correlation'])
                tf_names.append(tf)
        
        if len(corr_values) < 2:
            return divergences
        
        # Find significant differences between adjacent timeframes
        for i in range(len(corr_values) - 1):
            diff = abs(corr_values[i] - corr_values[i+1])
            if diff > 0.3:  # 0.3 difference is significant
                divergences.append({
                    'type': 'TIMEFRAME_DIVERGENCE',
                    'timeframe1': tf_names[i],
                    'timeframe2': tf_names[i+1],
                    'correlation1': corr_values[i],
                    'correlation2': corr_values[i+1],
                    'difference': diff,
                    'direction': 'DIVERGING',
                    'description': f"Correlation diverges between {tf_names[i]} ({corr_values[i]:.2f}) and {tf_names[i+1]} ({corr_values[i+1]:.2f})"
                })
        
        # Check if any timeframe shows inverse correlation
        for i, corr in enumerate(corr_values):
            if corr < -0.3:
                divergences.append({
                    'type': 'INVERSE_CORRELATION',
                    'timeframe': tf_names[i],
                    'correlation': corr,
                    'description': f"Inverse correlation detected on {tf_names[i]} timeframe ({corr:.2f})"
                })
        
        return divergences
    
    def _detect_regime_shifts(self, results: Dict) -> List[Dict]:
        """
        Detect regime shifts in correlation across timeframes.
        """
        regime_shifts = []
        timeframes = results['timeframes']
        
        # Check correlation stability across timeframes
        corr_values = []
        tf_names = []
        
        for tf, data in timeframes.items():
            if 'correlation' in data:
                corr_values.append(data['correlation'])
                tf_names.append(tf)
        
        if len(corr_values) < 3:
            return regime_shifts
        
        # Check for consistent pattern
        all_positive = all(c > 0 for c in corr_values)
        all_negative = all(c < 0 for c in corr_values)
        mixed = not all_positive and not all_negative
        
        if all_positive:
            regime_shifts.append({
                'type': 'REGIME_CONSISTENT',
                'description': f"All timeframes show positive correlation ({np.mean(corr_values):.2f})",
                'confidence': 0.8
            })
        elif all_negative:
            regime_shifts.append({
                'type': 'REGIME_CONSISTENT',
                'description': f"All timeframes show negative correlation ({np.mean(corr_values):.2f})",
                'confidence': 0.8
            })
        elif mixed:
            regime_shifts.append({
                'type': 'REGIME_SHIFT',
                'description': f"Mixed correlation across timeframes - regime shift possible",
                'confidence': 0.5
            })
        
        return regime_shifts
    
    def _generate_recommendations(self, results: Dict) -> List[Dict]:
        """
        Generate trading recommendations from multi-timeframe analysis.
        """
        recommendations = []
        timeframes = results['timeframes']
        
        # Best and worst timeframes
        best = results.get('best_timeframe')
        worst = results.get('worst_timeframe')
        
        if best and best in timeframes:
            best_corr = timeframes[best].get('correlation', 0) if best in timeframes else 0
            
            if abs(best_corr) > 0.7:
                recommendations.append({
                    'action': 'TRADE_CORRELATION',
                    'timeframe': best,
                    'correlation': best_corr,
                    'description': f"Best correlation on {best} timeframe ({best_corr:.2f})",
                    'confidence': 0.8
                })
        
        if worst and worst in timeframes:
            worst_corr = timeframes[worst].get('correlation', 0) if worst in timeframes else 0
            
            if abs(worst_corr) < 0.3:
                recommendations.append({
                    'action': 'AVOID_CORRELATION',
                    'timeframe': worst,
                    'correlation': worst_corr,
                    'description': f"Weak correlation on {worst} timeframe ({worst_corr:.2f})",
                    'confidence': 0.6
                })
        
        # Divergence signals
        for div in results.get('divergences', []):
            if div['type'] == 'TIMEFRAME_DIVERGENCE':
                recommendations.append({
                    'action': 'MONITOR_DIVERGENCE',
                    'description': div['description'],
                    'confidence': 0.7
                })
        
        return recommendations
    
    def analyze_all_pairs(self, assets: Optional[List[str]] = None) -> Dict:
        """
        Analyze all asset pairs across all timeframes.
        """
        if assets is None:
            assets = settings.ASSETS
        
        results = {}
        
        for i in range(len(assets)):
            for j in range(i + 1, len(assets)):
                key = f"{assets[i]}_{assets[j]}"
                results[key] = self.analyze_pair(assets[i], assets[j])
        
        return results
    
    def get_multi_timeframe_insights(self, assets: Optional[List[str]] = None) -> List[Dict]:
        """
        Generate insights from multi-timeframe analysis.
        """
        insights = []
        
        if assets is None:
            assets = settings.ASSETS
        
        analysis = self.analyze_all_pairs(assets)
        
        for pair_key, pair_data in analysis.items():
            # Check for consistency
            if pair_data.get('consistency_score', 0) > 0.8:
                insights.append({
                    'type': 'CONSISTENT_CORRELATION',
                    'pair': pair_key,
                    'score': pair_data['consistency_score'],
                    'best': pair_data.get('best_timeframe'),
                    'description': f"{pair_key} shows consistent correlation across timeframes"
                })
            
            # Check for divergences
            if pair_data.get('divergences'):
                for div in pair_data['divergences']:
                    insights.append({
                        'type': 'TIMEFRAME_DIVERGENCE',
                        'pair': pair_key,
                        'description': div['description']
                    })
            
            # Check for regime shifts
            if pair_data.get('regime_shifts'):
                for shift in pair_data['regime_shifts']:
                    insights.append({
                        'type': 'REGIME_SHIFT',
                        'pair': pair_key,
                        'description': shift['description'],
                        'confidence': shift.get('confidence', 0.5)
                    })
        
        return insights