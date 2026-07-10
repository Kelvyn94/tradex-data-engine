"""
Correlation Matrix - Multi-Timeframe Institutional Grade
Calculates correlations across all timeframes for 6 assets.
Used by: Bridgewater Associates, AQR Capital
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import logging
from scipy import stats
from scipy.stats import spearmanr, pearsonr

from backend.services.database_service import db_service
from backend.config.settings import settings

logger = logging.getLogger(__name__)


class CorrelationMatrix:
    """
    Institutional-grade multi-timeframe correlation matrix.
    Calculates correlations for all 6 assets across all timeframes.
    """
    
    # Define asset groups for correlation analysis
    ASSET_GROUPS = {
        'FX_PAIRS': ['EURUSD', 'GBPUSD'],
        'PRECIOUS_METALS': ['XAUUSD', 'XAGUSD', 'XAUEUR', 'XAUGBP'],
        'ALL': ['EURUSD', 'GBPUSD', 'XAUUSD', 'XAGUSD', 'XAUEUR', 'XAUGBP']
    }
    
    # Expected correlations based on market logic
    EXPECTED_CORRELATIONS = {
        ('XAUUSD', 'XAGUSD'): 0.85,
        ('XAUUSD', 'XAUEUR'): 0.95,
        ('XAUUSD', 'XAUGBP'): 0.90,
        ('XAGUSD', 'XAUEUR'): 0.80,
        ('XAGUSD', 'XAUGBP'): 0.75,
        ('XAUEUR', 'XAUGBP'): 0.95,
        ('EURUSD', 'GBPUSD'): 0.70,
        ('XAUUSD', 'EURUSD'): 0.40,
        ('XAUUSD', 'GBPUSD'): 0.35,
    }
    
    def __init__(self):
        self.correlation_matrix = None
        self.p_value_matrix = None
        self.significance_matrix = None
        self.assets = []
        self.last_update = None
        self.timeframes = ['30m', '1h', '4h', 'daily', 'weekly']
        self.multi_timeframe_results = {}
        logger.info("CorrelationMatrix initialized (multi-timeframe)")
    
    def calculate(self, assets: Optional[List[str]] = None, 
                  timeframe: str = 'daily',
                  lookback: int = 252,
                  method: str = 'pearson') -> Dict:
        """
        Calculate correlation matrix for a specific timeframe.
        """
        if assets is None:
            assets = settings.ASSETS
        
        self.assets = assets
        
        # Get data for all assets
        data = {}
        end_date = datetime.now()
        start_date = end_date - timedelta(days=lookback * 2)
        
        for asset in assets:
            df = db_service.get_candles(asset, timeframe, start_date, end_date)
            if df is not None and not df.empty:
                data[asset] = df.set_index('timestamp')['close']
        
        if len(data) < 2:
            logger.warning("Not enough assets for correlation")
            return {'error': 'Not enough assets'}
        
        # Align all data to common timestamps
        aligned_data = self._align_data(data)
        
        if aligned_data.empty:
            return {'error': 'No common timestamps'}
        
        # Calculate returns
        returns = aligned_data.pct_change().dropna()
        
        # Calculate correlation matrix
        if method == 'pearson':
            corr_matrix = returns.corr(method='pearson')
        else:
            corr_matrix = returns.corr(method='spearman')
        
        # Calculate p-values and significance
        p_values = pd.DataFrame(index=corr_matrix.index, columns=corr_matrix.columns)
        significance = pd.DataFrame(index=corr_matrix.index, columns=corr_matrix.columns)
        
        for i in range(len(corr_matrix.columns)):
            for j in range(len(corr_matrix.columns)):
                if i != j:
                    col1 = returns.iloc[:, i]
                    col2 = returns.iloc[:, j]
                    if method == 'pearson':
                        corr, p_val = pearsonr(col1, col2)
                    else:
                        corr, p_val = spearmanr(col1, col2)
                    p_values.iloc[i, j] = p_val
                    significance.iloc[i, j] = p_val < 0.05
        
        self.correlation_matrix = corr_matrix
        self.p_value_matrix = p_values
        self.significance_matrix = significance
        self.last_update = datetime.now()
        
        # Generate correlation insights
        insights = self._generate_insights(corr_matrix)
        
        return {
            'correlation_matrix': corr_matrix,
            'p_values': p_values,
            'significance': significance,
            'method': method,
            'lookback': lookback,
            'timeframe': timeframe,
            'assets': assets,
            'last_update': self.last_update.isoformat(),
            'insights': insights
        }
    
    def calculate_all_timeframes(self, assets: Optional[List[str]] = None,
                                 lookback: int = 252) -> Dict:
        """
        Calculate correlation matrices for ALL timeframes.
        This is the hedge fund method!
        """
        if assets is None:
            assets = settings.ASSETS
        
        results = {}
        insights = []
        
        for tf in self.timeframes:
            tf_result = self.calculate(assets, tf, lookback)
            results[tf] = tf_result
            
            # Extract insights for this timeframe
            if 'insights' in tf_result:
                insights.extend(tf_result['insights'])
        
        # Generate cross-timeframe insights
        cross_insights = self._generate_cross_timeframe_insights(results)
        insights.extend(cross_insights)
        
        self.multi_timeframe_results = results
        
        return {
            'timeframes': results,
            'insights': insights,
            'assets': assets,
            'lookback': lookback,
            'timestamp': datetime.now().isoformat()
        }
    
    def _generate_insights(self, corr_matrix: pd.DataFrame) -> List[Dict]:
        """
        Generate insights from correlation matrix.
        """
        insights = []
        assets = corr_matrix.columns
        
        # Find highest correlations
        highest_pairs = []
        for i in range(len(assets)):
            for j in range(i + 1, len(assets)):
                corr = corr_matrix.iloc[i, j]
                highest_pairs.append({
                    'asset1': assets[i],
                    'asset2': assets[j],
                    'correlation': corr
                })
        
        highest_pairs = sorted(highest_pairs, key=lambda x: abs(x['correlation']), reverse=True)
        
        # Top 3 strongest correlations
        for pair in highest_pairs[:3]:
            if abs(pair['correlation']) > 0.7:
                insights.append({
                    'type': 'STRONG_CORRELATION',
                    'asset1': pair['asset1'],
                    'asset2': pair['asset2'],
                    'correlation': pair['correlation'],
                    'description': f"{pair['asset1']} and {pair['asset2']} are strongly correlated ({pair['correlation']:.2f})",
                    'action': 'MONITOR_PAIR'
                })
        
        # Check for deviations from expected correlations
        for (asset1, asset2), expected in self.EXPECTED_CORRELATIONS.items():
            if asset1 in assets and asset2 in assets:
                actual = corr_matrix.loc[asset1, asset2]
                deviation = actual - expected
                if abs(deviation) > 0.2:
                    insights.append({
                        'type': 'CORRELATION_DEVIATION',
                        'asset1': asset1,
                        'asset2': asset2,
                        'expected': expected,
                        'actual': actual,
                        'deviation': deviation,
                        'description': f"{asset1}/{asset2} correlation is {deviation:.2f} from expected ({expected:.2f})",
                        'action': 'INVESTIGATE'
                    })
        
        return insights
    
    def _generate_cross_timeframe_insights(self, results: Dict) -> List[Dict]:
        """
        Generate insights across timeframes.
        """
        insights = []
        
        # Check if correlation patterns are consistent across timeframes
        asset_pairs = []
        for tf, result in results.items():
            if 'correlation_matrix' in result:
                matrix = result['correlation_matrix']
                for i in range(len(matrix.columns)):
                    for j in range(i + 1, len(matrix.columns)):
                        asset_pairs.append({
                            'asset1': matrix.columns[i],
                            'asset2': matrix.columns[j],
                            'timeframe': tf,
                            'correlation': matrix.iloc[i, j]
                        })
        
        # Find pairs with consistent high correlation
        pair_correlations = {}
        for item in asset_pairs:
            key = f"{item['asset1']}_{item['asset2']}"
            if key not in pair_correlations:
                pair_correlations[key] = []
            pair_correlations[key].append(item['correlation'])
        
        for key, corrs in pair_correlations.items():
            if len(corrs) == len(self.timeframes):
                avg_corr = np.mean(corrs)
                std_corr = np.std(corrs)
                if avg_corr > 0.7 and std_corr < 0.15:
                    asset1, asset2 = key.split('_')
                    insights.append({
                        'type': 'CONSISTENT_CORRELATION',
                        'asset1': asset1,
                        'asset2': asset2,
                        'average': avg_corr,
                        'stability': 1 - std_corr,
                        'description': f"{asset1} and {asset2} are consistently correlated across all timeframes ({avg_corr:.2f})",
                        'action': 'TRADE_CORRELATION'
                    })
        
        return insights
    
    def _align_data(self, data: Dict[str, pd.Series]) -> pd.DataFrame:
        """Align multiple time series to common timestamps."""
        df = pd.DataFrame(data)
        # FIXED: Use ffill() instead of fillna(method='ffill')
        df = df.ffill()
        df = df.dropna()
        return df
    
    def get_strong_correlations(self, threshold: float = 0.7) -> List[Dict]:
        """Get pairs with strong correlations."""
        if self.correlation_matrix is None:
            return []
        
        strong_pairs = []
        assets = self.correlation_matrix.columns
        
        for i in range(len(assets)):
            for j in range(i + 1, len(assets)):
                corr = self.correlation_matrix.iloc[i, j]
                p_val = self.p_value_matrix.iloc[i, j]
                is_significant = self.significance_matrix.iloc[i, j]
                
                if abs(corr) >= threshold:
                    strong_pairs.append({
                        'asset1': assets[i],
                        'asset2': assets[j],
                        'correlation': float(corr),
                        'p_value': float(p_val),
                        'significant': bool(is_significant),
                        'type': 'POSITIVE' if corr > 0 else 'NEGATIVE',
                        'strength': self._get_strength_label(abs(corr))
                    })
        
        return sorted(strong_pairs, key=lambda x: abs(x['correlation']), reverse=True)
    
    def get_correlation_summary(self) -> Dict:
        """Get summary statistics of correlation matrix."""
        if self.correlation_matrix is None:
            return {}
        
        corr_values = []
        for i in range(len(self.correlation_matrix.columns)):
            for j in range(i + 1, len(self.correlation_matrix.columns)):
                corr_values.append(self.correlation_matrix.iloc[i, j])
        
        return {
            'mean_correlation': float(np.mean(corr_values)),
            'median_correlation': float(np.median(corr_values)),
            'std_correlation': float(np.std(corr_values)),
            'max_correlation': float(np.max(corr_values)),
            'min_correlation': float(np.min(corr_values)),
            'strong_positive': len([c for c in corr_values if c > 0.7]),
            'strong_negative': len([c for c in corr_values if c < -0.7]),
            'weak': len([c for c in corr_values if abs(c) < 0.3]),
            'significant_pairs': self._count_significant_pairs()
        }
    
    def _get_strength_label(self, correlation: float) -> str:
        """Get strength label for correlation."""
        if correlation >= 0.9:
            return 'VERY_STRONG'
        elif correlation >= 0.7:
            return 'STRONG'
        elif correlation >= 0.5:
            return 'MODERATE'
        elif correlation >= 0.3:
            return 'WEAK'
        else:
            return 'VERY_WEAK'
    
    def _count_significant_pairs(self) -> int:
        """Count statistically significant pairs."""
        if self.significance_matrix is None:
            return 0
        
        count = 0
        for i in range(len(self.significance_matrix.columns)):
            for j in range(i + 1, len(self.significance_matrix.columns)):
                if self.significance_matrix.iloc[i, j]:
                    count += 1
        return count