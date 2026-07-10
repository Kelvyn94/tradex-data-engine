"""
Currency Strength Analysis - Institutional Grade
Calculates relative strength of currencies across multiple assets.
Used by: Bridgewater Associates, Currency traders
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import logging

from backend.services.database_service import db_service
from backend.config.settings import settings

logger = logging.getLogger(__name__)


class CurrencyStrength:
    """
    Institutional-grade currency strength analysis.
    Calculates relative strength of USD, EUR, GBP, and Gold.
    """
    
    def __init__(self):
        self.strength_scores = {}
        self.last_update = None
        logger.info("CurrencyStrength initialized")
    
    def calculate(self, timeframe: str = 'daily', 
                  lookback: int = 30) -> Dict:
        """
        Calculate currency strength scores.
        
        Args:
            timeframe: Timeframe to use
            lookback: Number of periods to look back
            
        Returns:
            Dictionary with currency strength scores
        """
        # Get all assets
        assets = settings.ASSETS
        
        # Get data
        end_date = datetime.now()
        start_date = end_date - timedelta(days=lookback * 2)
        
        data = {}
        for asset in assets:
            df = db_service.get_candles(asset, timeframe, start_date, end_date)
            if df is not None and not df.empty:
                data[asset] = df.set_index('timestamp')['close']
        
        if len(data) < 2:
            return {'error': 'Not enough data'}
        
        # Align data
        aligned = pd.DataFrame(data).dropna()
        if aligned.empty:
            return {'error': 'No aligned data'}
        
        # Calculate returns
        returns = aligned.pct_change().dropna()
        
        # Calculate strength scores
        strength = {}
        
        # 1. USD Strength (inverse of EURUSD and GBPUSD)
        if 'EURUSD' in returns and 'GBPUSD' in returns:
            # USD is inverse of EUR and GBP
            usd_strength = -np.mean([returns['EURUSD'].mean(), returns['GBPUSD'].mean()])
            strength['USD'] = usd_strength
        
        # 2. EUR Strength (from EURUSD)
        if 'EURUSD' in returns:
            strength['EUR'] = returns['EURUSD'].mean()
        
        # 3. GBP Strength (from GBPUSD)
        if 'GBPUSD' in returns:
            strength['GBP'] = returns['GBPUSD'].mean()
        
        # 4. Gold Strength (from XAUUSD)
        if 'XAUUSD' in returns:
            strength['XAU'] = returns['XAUUSD'].mean()
        
        # 5. Silver Strength (from XAGUSD)
        if 'XAGUSD' in returns:
            strength['XAG'] = returns['XAGUSD'].mean()
        
        # Normalize to 0-100 scale
        max_strength = max(abs(v) for v in strength.values()) if strength else 1
        normalized = {k: (v / max_strength * 50 + 50) for k, v in strength.items()}
        
        # Calculate rankings
        ranked = sorted(normalized.items(), key=lambda x: x[1], reverse=True)
        
        # Determine market sentiment
        avg_strength = np.mean(list(normalized.values()))
        if avg_strength > 55:
            sentiment = 'BULLISH'
        elif avg_strength < 45:
            sentiment = 'BEARISH'
        else:
            sentiment = 'NEUTRAL'
        
        self.strength_scores = {
            'raw_scores': strength,
            'normalized_scores': normalized,
            'ranking': ranked,
            'market_sentiment': sentiment,
            'strongest': ranked[0] if ranked else None,
            'weakest': ranked[-1] if ranked else None,
            'last_update': datetime.now().isoformat()
        }
        
        return self.strength_scores
    
    def get_strength_rankings(self) -> List[Tuple[str, float]]:
        """
        Get currency strength rankings.
        
        Returns:
            List of (currency, strength) tuples sorted by strength
        """
        if not self.strength_scores:
            return []
        
        return self.strength_scores.get('ranking', [])
    
    def get_currency_insights(self) -> List[Dict]:
        """
        Generate insights from currency strength.
        """
        insights = []
        
        if not self.strength_scores:
            return insights
        
        ranking = self.strength_scores.get('ranking', [])
        sentiment = self.strength_scores.get('market_sentiment', 'NEUTRAL')
        
        if ranking:
            # Strongest currency
            strongest = ranking[0]
            insights.append({
                'type': 'STRONGEST_CURRENCY',
                'title': f"{strongest[0]} is the Strongest",
                'description': f"{strongest[0]} shows the highest relative strength at {strongest[1]:.1f}",
                'confidence': 0.7
            })
            
            # Weakest currency
            weakest = ranking[-1]
            if weakest[1] < 45:
                insights.append({
                    'type': 'WEAKEST_CURRENCY',
                    'title': f"{weakest[0]} is the Weakest",
                    'description': f"{weakest[0]} shows the lowest relative strength at {weakest[1]:.1f}",
                    'confidence': 0.7
                })
        
        # Market sentiment
        insights.append({
            'type': 'MARKET_SENTIMENT',
            'title': f"Market is {sentiment}",
            'description': f"Overall currency sentiment is {sentiment} based on strength scores",
            'confidence': 0.6
        })
        
        return insights
    
    def get_trading_recommendations(self) -> List[Dict]:
        """
        Generate trading recommendations based on currency strength.
        """
        recommendations = []
        
        if not self.strength_scores:
            return recommendations
        
        ranking = self.strength_scores.get('ranking', [])
        
        if len(ranking) >= 2:
            # Trade strongest vs weakest
            strongest = ranking[0]
            weakest = ranking[-1]
            
            if strongest[1] > 55 and weakest[1] < 45:
                recommendations.append({
                    'action': 'BUY',
                    'asset': f"{strongest[0]} vs {weakest[0]}",
                    'reason': f"Strongest ({strongest[0]}) vs Weakest ({weakest[0]})",
                    'strength_gap': strongest[1] - weakest[1],
                    'confidence': 0.7
                })
        
        return recommendations