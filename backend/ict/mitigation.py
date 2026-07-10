"""
ICT Mitigation Analysis.
Identifies when price returns to order blocks and FVGs.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import logging

from backend.ict.order_blocks import OrderBlockDetector
from backend.ict.fvg import FVGDetector

logger = logging.getLogger(__name__)


class MitigationAnalyzer:
    """
    ICT Mitigation analyzer.
    Identifies when price returns to order blocks and FVGs.
    """
    
    def __init__(self, threshold: float = 0.001):
        """
        Initialize Mitigation analyzer.
        
        Args:
            threshold: Price threshold for mitigation (0.1% by default)
        """
        self.threshold = threshold
        self.ob_detector = OrderBlockDetector()
        self.fvg_detector = FVGDetector()
        logger.info(f"MitigationAnalyzer initialized (threshold={threshold})")
    
    def analyze(self, df: pd.DataFrame) -> Dict:
        """
        Analyze mitigation opportunities.
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            Dictionary with mitigation analysis
        """
        if df is None or df.empty:
            return {'error': 'No data'}
        
        current_price = df['close'].iloc[-1]
        
        # Find order blocks
        obs = self.ob_detector.find_all_obs(df)
        
        # Find FVGs
        fvgs = self.fvg_detector.detect(df)
        
        # Check for mitigation
        ob_mitigation = self._check_ob_mitigation(obs, current_price)
        fvg_mitigation = self._check_fvg_mitigation(fvgs, current_price)
        
        return {
            'order_block_mitigation': ob_mitigation,
            'fvg_mitigation': fvg_mitigation,
            'current_price': float(current_price),
            'has_mitigation': ob_mitigation.get('has_mitigation', False) or fvg_mitigation.get('has_mitigation', False)
        }
    
    def _check_ob_mitigation(self, obs: Dict, current_price: float) -> Dict:
        """
        Check if price is mitigating an order block.
        """
        all_obs = obs.get('bullish', []) + obs.get('bearish', [])
        
        if not all_obs:
            return {'has_mitigation': False, 'obs': []}
        
        mitigated = []
        
        for ob in all_obs:
            # Check if price is within OB zone
            if ob.get('type') == 'BULLISH':
                ob_high = ob.get('high', 0)
                if ob_high > 0:
                    distance = abs(current_price - ob_high) / ob_high
                    if distance < self.threshold:
                        mitigated.append({
                            **ob,
                            'mitigation_type': 'BULLISH_OB_MITIGATION',
                            'distance': float(distance)
                        })
            else:
                ob_low = ob.get('low', 0)
                if ob_low > 0:
                    distance = abs(current_price - ob_low) / ob_low
                    if distance < self.threshold:
                        mitigated.append({
                            **ob,
                            'mitigation_type': 'BEARISH_OB_MITIGATION',
                            'distance': float(distance)
                        })
        
        return {
            'has_mitigation': len(mitigated) > 0,
            'obs': mitigated
        }
    
    def _check_fvg_mitigation(self, fvgs: List, current_price: float) -> Dict:
        """
        Check if price is mitigating an FVG.
        """
        if not fvgs:
            return {'has_mitigation': False, 'fvgs': []}
        
        mitigated = []
        
        for fvg in fvgs:
            if fvg.get('is_filled', True):
                continue
            
            gap_low = fvg.get('gap_low', 0)
            gap_high = fvg.get('gap_high', 0)
            
            # Check if price is within FVG zone
            if gap_low <= current_price <= gap_high:
                mitigated.append({
                    **fvg,
                    'mitigation_type': f"{fvg.get('type', '')}_FVG_MITIGATION"
                })
        
        return {
            'has_mitigation': len(mitigated) > 0,
            'fvgs': mitigated
        }
    
    def get_mitigation_entries(self, df: pd.DataFrame) -> List[Dict]:
        """
        Get potential entry points from mitigation.
        """
        analysis = self.analyze(df)
        
        if not analysis.get('has_mitigation', False):
            return []
        
        entries = []
        
        # Check order block mitigations
        for ob in analysis.get('order_block_mitigation', {}).get('obs', []):
            if ob.get('type') == 'BULLISH':
                entries.append({
                    'type': 'BUY',
                    'entry': ob.get('high', 0),
                    'stop': ob.get('low', 0),
                    'target': ob.get('high', 0) + (ob.get('high', 0) - ob.get('low', 0)) * 1.5,
                    'source': 'OB_MITIGATION',
                    'confidence': 0.7 if ob.get('strength') == 'STRONG' else 0.5
                })
            else:
                entries.append({
                    'type': 'SELL',
                    'entry': ob.get('low', 0),
                    'stop': ob.get('high', 0),
                    'target': ob.get('low', 0) - (ob.get('high', 0) - ob.get('low', 0)) * 1.5,
                    'source': 'OB_MITIGATION',
                    'confidence': 0.7 if ob.get('strength') == 'STRONG' else 0.5
                })
        
        return entries