"""
Macro service for managing FRED data.
"""

import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging

from backend.providers.fred_provider import FREDProvider
from backend.services.database_service import db_service

logger = logging.getLogger(__name__)

class MacroService:
    """
    Service for managing macroeconomic data.
    """
    
    def __init__(self):
        self.fred_provider = FREDProvider()
        logger.info("MacroService initialized")
    
    def update_macro_data(self, days: int = 30) -> Dict[str, int]:
        """
        Update macro data from FRED.
        """
        start_date = datetime.now() - timedelta(days=days)
        end_date = datetime.now()
        
        results = {}
        
        # Get all series from FRED
        data = self.fred_provider.get_all_series(start_date, end_date)
        
        for indicator_name, df in data.items():
            if df is not None and not df.empty:
                stored = self._store_macro_data(indicator_name, df)
                results[indicator_name] = stored
                logger.info(f"Stored {stored} records for {indicator_name}")
            else:
                results[indicator_name] = 0
        
        return results
    
    def _store_macro_data(self, indicator_name: str, df: pd.DataFrame) -> int:
        """
        Store macro data in database.
        """
        from backend.database.postgres import db_manager
        from backend.database.models import MacroIndicator
        
        stored_count = 0
        with db_manager.get_session() as session:
            for _, row in df.iterrows():
                try:
                    # Check if exists
                    existing = session.query(MacroIndicator).filter(
                        MacroIndicator.indicator_name == indicator_name,
                        MacroIndicator.timestamp == row['timestamp']
                    ).first()
                    
                    if existing:
                        existing.value = row['value']
                    else:
                        macro = MacroIndicator(
                            indicator_name=indicator_name,
                            timestamp=row['timestamp'],
                            value=row['value'],
                            source='FRED'
                        )
                        session.add(macro)
                    stored_count += 1
                except Exception as e:
                    logger.error(f"Error storing {indicator_name}: {e}")
                    continue
            
            session.commit()
        
        return stored_count
    
    def get_latest_macro(self) -> Dict[str, Any]:
        """Get latest macro indicators."""
        latest = self.fred_provider.get_latest_values()
        
        result = {
            'indicators': latest,
            'summary': self._get_macro_summary(latest)
        }
        
        return result
    
    def _get_macro_summary(self, indicators: Dict[str, float]) -> Dict[str, Any]:
        """Generate macro summary."""
        summary = {}
        
        # Interest Rates
        if 'FEDFUNDS' in indicators and indicators['FEDFUNDS'] is not None:
            rate = indicators['FEDFUNDS']
            summary['interest_rates'] = {
                'fed_funds': rate,
                'status': 'HIGH' if rate > 5 else 'MODERATE' if rate > 2 else 'LOW'
            }
        
        # Employment
        if 'UNRATE' in indicators and indicators['UNRATE'] is not None:
            rate = indicators['UNRATE']
            summary['employment'] = {
                'unemployment': rate,
                'status': 'LOW' if rate < 4 else 'MODERATE' if rate < 6 else 'HIGH'
            }
        
        # Treasury Yield
        if 'DGS10' in indicators and indicators['DGS10'] is not None:
            yield_10 = indicators['DGS10']
            summary['treasury'] = {
                'ten_year_yield': yield_10,
                'status': 'HIGH' if yield_10 > 4.5 else 'MODERATE' if yield_10 > 2.5 else 'LOW'
            }
        
        return summary
    
    def get_macro_insights(self) -> List[Dict[str, Any]]:
        """Generate macro-based insights."""
        insights = []
        latest = self.fred_provider.get_latest_values()
        
        # Fed Funds Rate insight
        if latest.get('FEDFUNDS') and latest['FEDFUNDS'] is not None:
            rate = latest['FEDFUNDS']
            if rate > 5:
                insights.append({
                    'asset_symbol': 'GLOBAL',
                    'insight_type': 'MACRO',
                    'title': "High Interest Rate Environment",
                    'description': f"Fed Funds rate at {rate:.2f}% - elevated rates may impact markets",
                    'confidence': 0.7,
                    'supporting_data': {'fed_funds_rate': rate}
                })
            elif rate < 2:
                insights.append({
                    'asset_symbol': 'GLOBAL',
                    'insight_type': 'MACRO',
                    'title': "Low Interest Rate Environment",
                    'description': f"Fed Funds rate at {rate:.2f}% - accommodative monetary policy",
                    'confidence': 0.7,
                    'supporting_data': {'fed_funds_rate': rate}
                })
        
        # Unemployment insight
        if latest.get('UNRATE') and latest['UNRATE'] is not None:
            rate = latest['UNRATE']
            if rate < 4:
                insights.append({
                    'asset_symbol': 'GLOBAL',
                    'insight_type': 'MACRO',
                    'title': "Strong Labor Market",
                    'description': f"Unemployment at {rate:.1f}% - historically low levels",
                    'confidence': 0.6,
                    'supporting_data': {'unemployment_rate': rate}
                })
            elif rate > 6:
                insights.append({
                    'asset_symbol': 'GLOBAL',
                    'insight_type': 'MACRO',
                    'title': "Weak Labor Market",
                    'description': f"Unemployment at {rate:.1f}% - elevated levels",
                    'confidence': 0.6,
                    'supporting_data': {'unemployment_rate': rate}
                })
        
        return insights