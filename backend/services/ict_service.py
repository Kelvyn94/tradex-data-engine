"""
ICT Service - Complete ICT analysis service.
Combines all ICT components for comprehensive analysis.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

from backend.ict.market_structure import MarketStructure
from backend.ict.bos import BOSDetector
from backend.ict.choch import CHOCHDetector
from backend.ict.order_blocks import OrderBlockDetector
from backend.ict.fvg import FVGDetector
from backend.ict.liquidity import LiquidityDetector
from backend.ict.sessions import SessionAnalyzer
from backend.ict.killzone import KillzoneDetector
from backend.ict.premium_discount import PremiumDiscountAnalyzer
from backend.ict.mitigation import MitigationAnalyzer
from backend.ict.dealing_range import DealingRangeAnalyzer
from backend.ict.quarterly_theory import QuarterlyTheoryAnalyzer
from backend.ict.smt import SMTAnalyzer

from backend.services.database_service import db_service

logger = logging.getLogger(__name__)


class ICTService:
    """
    Complete ICT analysis service.
    Combines all ICT components for comprehensive market analysis.
    """
    
    def __init__(self):
        """Initialize all ICT analyzers."""
        self.market_structure = MarketStructure()
        self.bos_detector = BOSDetector()
        self.choch_detector = CHOCHDetector()
        self.order_block_detector = OrderBlockDetector()
        self.fvg_detector = FVGDetector()
        self.liquidity_detector = LiquidityDetector()
        self.session_analyzer = SessionAnalyzer()
        self.killzone_detector = KillzoneDetector()
        self.premium_discount = PremiumDiscountAnalyzer()
        self.mitigation_analyzer = MitigationAnalyzer()
        self.dealing_range = DealingRangeAnalyzer()
        self.quarterly_theory = QuarterlyTheoryAnalyzer()
        self.smt_analyzer = SMTAnalyzer()
        logger.info("ICTService initialized with all components")
    
    def analyze_asset(self, asset: str, timeframe: str = 'daily', 
                      lookback: int = 200) -> Dict[str, Any]:
        """
        Complete ICT analysis for a single asset.
        
        Args:
            asset: Asset symbol
            timeframe: Timeframe to analyze
            lookback: Number of candles to look back
            
        Returns:
            Complete ICT analysis
        """
        # Get data
        df = db_service.get_candles(asset, timeframe, limit=lookback)
        
        if df is None or df.empty:
            return {'error': f'No data for {asset} {timeframe}'}
        
        # Run all analyses
        results = {
            'asset': asset,
            'timeframe': timeframe,
            'timestamp': datetime.now().isoformat()
        }
        
        # Market Structure
        try:
            results['market_structure'] = self.market_structure.analyze(df)
        except Exception as e:
            logger.error(f"Market Structure error: {e}")
            results['market_structure'] = {'error': str(e)}
        
        # BOS
        try:
            results['bos'] = self.bos_detector.detect(df)
            results['latest_bos'] = self.bos_detector.get_latest_bos(df)
        except Exception as e:
            logger.error(f"BOS error: {e}")
            results['bos'] = []
        
        # CHOCH
        try:
            results['choch'] = self.choch_detector.detect(df)
            results['latest_choch'] = self.choch_detector.get_latest_choch(df)
        except Exception as e:
            logger.error(f"CHOCH error: {e}")
            results['choch'] = []
        
        # Order Blocks
        try:
            results['order_blocks'] = self.order_block_detector.find_all_obs(df)
            results['latest_ob'] = self.order_block_detector.get_latest_obs(df)
        except Exception as e:
            logger.error(f"Order Blocks error: {e}")
            results['order_blocks'] = {}
        
        # FVG
        try:
            results['fvgs'] = self.fvg_detector.detect(df)
            results['unfilled_fvgs'] = self.fvg_detector.get_unfilled_fvgs(df)
        except Exception as e:
            logger.error(f"FVG error: {e}")
            results['fvgs'] = []
        
        # Liquidity
        try:
            results['liquidity'] = self.liquidity_detector.detect_liquidity_zones(df)
            results['nearest_liquidity'] = self.liquidity_detector.get_nearest_liquidity(
                df, df['close'].iloc[-1]
            )
        except Exception as e:
            logger.error(f"Liquidity error: {e}")
            results['liquidity'] = {}
        
        # Sessions
        try:
            results['sessions'] = self.session_analyzer.get_session_statistics(df)
            results['current_session'] = self.session_analyzer.get_current_session_info()
        except Exception as e:
            logger.error(f"Sessions error: {e}")
            results['sessions'] = {}
        
        # Killzones
        try:
            results['killzones'] = self.killzone_detector.detect_killzones(df)
            results['best_killzone'] = self.killzone_detector.get_best_killzone(df)
        except Exception as e:
            logger.error(f"Killzones error: {e}")
            results['killzones'] = {}
        
        # Premium/Discount
        try:
            results['premium_discount'] = self.premium_discount.analyze(df)
        except Exception as e:
            logger.error(f"Premium/Discount error: {e}")
            results['premium_discount'] = {}
        
        # Mitigation
        try:
            results['mitigation'] = self.mitigation_analyzer.analyze(df)
            results['mitigation_entries'] = self.mitigation_analyzer.get_mitigation_entries(df)
        except Exception as e:
            logger.error(f"Mitigation error: {e}")
            results['mitigation'] = {}
        
        # Dealing Range
        try:
            results['dealing_range'] = self.dealing_range.analyze(df)
        except Exception as e:
            logger.error(f"Dealing Range error: {e}")
            results['dealing_range'] = {}
        
        # Quarterly Theory
        try:
            results['quarterly_theory'] = self.quarterly_theory.analyze(df)
        except Exception as e:
            logger.error(f"Quarterly Theory error: {e}")
            results['quarterly_theory'] = {}
        
        # Generate combined signal
        try:
            results['signal'] = self._generate_combined_signal(results)
        except Exception as e:
            logger.error(f"Signal generation error: {e}")
            results['signal'] = {'action': 'HOLD', 'confidence': 0}
        
        return results
    
    def analyze_multi_asset(self, assets: List[str], timeframe: str = 'daily') -> Dict:
        """
        Analyze multiple assets and find SMT divergence.
        
        Args:
            assets: List of asset symbols
            timeframe: Timeframe to analyze
            
        Returns:
            Multi-asset ICT analysis
        """
        results = {}
        
        # Analyze each asset
        for asset in assets:
            results[asset] = self.analyze_asset(asset, timeframe)
        
        # Find SMT divergence between assets
        if len(assets) >= 2:
            for i in range(len(assets)):
                for j in range(i+1, len(assets)):
                    asset1 = assets[i]
                    asset2 = assets[j]
                    
                    if asset1 in results and asset2 in results:
                        # Get data
                        df1 = db_service.get_candles(asset1, timeframe, limit=100)
                        df2 = db_service.get_candles(asset2, timeframe, limit=100)
                        
                        if df1 is not None and df2 is not None and not df1.empty and not df2.empty:
                            smt_analysis = self.smt_analyzer.analyze(df1, df2, asset1, asset2)
                            results[f'smt_{asset1}_{asset2}'] = smt_analysis
        
        return results
    
    def _generate_combined_signal(self, analysis: Dict) -> Dict:
        """
        Generate a combined trading signal from all ICT components.
        """
        score = 0
        reasons = []
        confidence = 0
        
        # 1. Market Structure
        structure = analysis.get('market_structure', {})
        if structure and 'current_structure' in structure:
            trend = structure['current_structure'].get('trend', '')
            if trend == 'BULLISH':
                score += 2
                reasons.append('Bullish market structure')
                confidence += 0.1
            elif trend == 'BEARISH':
                score -= 2
                reasons.append('Bearish market structure')
                confidence += 0.1
        
        # 2. BOS
        latest_bos = analysis.get('latest_bos')
        if latest_bos:
            if 'BULLISH' in latest_bos.get('type', ''):
                score += 1
                reasons.append('Bullish BOS detected')
                confidence += 0.05
            else:
                score -= 1
                reasons.append('Bearish BOS detected')
                confidence += 0.05
        
        # 3. CHOCH
        latest_choch = analysis.get('latest_choch')
        if latest_choch:
            if 'BULLISH' in latest_choch.get('type', ''):
                score += 2
                reasons.append('Bullish CHOCH detected (trend reversal)')
                confidence += 0.1
            else:
                score -= 2
                reasons.append('Bearish CHOCH detected (trend reversal)')
                confidence += 0.1
        
        # 4. Order Blocks
        latest_ob = analysis.get('latest_ob')
        if latest_ob:
            if latest_ob.get('type') == 'BULLISH':
                score += 1
                reasons.append('Bullish order block nearby')
                confidence += 0.05
            else:
                score -= 1
                reasons.append('Bearish order block nearby')
                confidence += 0.05
        
        # 5. Premium/Discount
        pd_analysis = analysis.get('premium_discount', {})
        if pd_analysis:
            zone = pd_analysis.get('zone', '')
            if zone == 'DISCOUNT':
                score += 1
                reasons.append('Price in discount zone - buy opportunity')
                confidence += 0.05
            elif zone == 'PREMIUM':
                score -= 1
                reasons.append('Price in premium zone - sell opportunity')
                confidence += 0.05
        
        # 6. Killzone
        killzones = analysis.get('killzones', {})
        for name, data in killzones.items():
            if data.get('is_active', False):
                score += 0.5
                reasons.append(f'Active {name}')
                confidence += 0.03
        
        # Determine action
        if score >= 4:
            action = 'STRONG_BUY'
            confidence += 0.2
        elif score >= 2:
            action = 'BUY'
            confidence += 0.1
        elif score <= -4:
            action = 'STRONG_SELL'
            confidence += 0.2
        elif score <= -2:
            action = 'SELL'
            confidence += 0.1
        else:
            action = 'HOLD'
            confidence += 0
        
        # Cap confidence
        confidence = min(confidence, 1.0)
        
        return {
            'action': action,
            'score': score,
            'confidence': round(confidence, 2),
            'reasons': reasons,
            'signal_strength': 'STRONG' if abs(score) >= 4 else 'MODERATE' if abs(score) >= 2 else 'WEAK'
        }