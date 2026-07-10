"""
Database service for storing and retrieving data.
"""

import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import logging

from backend.database.postgres import db_manager
from backend.database.models import (
    AssetCandle, MacroIndicator, SentimentData, 
    TechnicalIndicator, TradingSignal, AIInsight
)
from sqlalchemy import and_, desc, func

logger = logging.getLogger(__name__)

class DatabaseService:
    """Service for database operations."""
    
    def __init__(self):
        self.db_manager = db_manager
    
    # ==================== CANDLE OPERATIONS ====================
    
    def store_candles(self, df: pd.DataFrame, asset: str, timeframe: str) -> int:
        """
        Store candle data in database.
        
        Args:
            df: DataFrame with candle data
            asset: Asset symbol
            timeframe: Timeframe
            
        Returns:
            Number of records stored
        """
        if df is None or df.empty:
            return 0
        
        stored_count = 0
        with self.db_manager.get_session() as session:
            for _, row in df.iterrows():
                # Check if candle already exists
                existing = session.query(AssetCandle).filter(
                    AssetCandle.asset_symbol == asset,
                    AssetCandle.timeframe == timeframe,
                    AssetCandle.timestamp == row['timestamp']
                ).first()
                
                if existing:
                    # Update existing candle
                    existing.open = row['open']
                    existing.high = row['high']
                    existing.low = row['low']
                    existing.close = row['close']
                    existing.volume = row.get('volume', 0)
                    existing.is_synthetic = row.get('is_synthetic', False)
                else:
                    # Create new candle
                    candle = AssetCandle(
                        asset_symbol=asset,
                        timeframe=timeframe,
                        timestamp=row['timestamp'],
                        open=row['open'],
                        high=row['high'],
                        low=row['low'],
                        close=row['close'],
                        volume=row.get('volume', 0),
                        is_synthetic=row.get('is_synthetic', False)
                    )
                    session.add(candle)
                stored_count += 1
            
            session.commit()
            logger.info(f"Stored {stored_count} candles for {asset} {timeframe}")
        
        return stored_count
    
    def get_candles(self, asset: str, timeframe: str, 
                   start_date: Optional[datetime] = None,
                   end_date: Optional[datetime] = None,
                   limit: Optional[int] = None) -> pd.DataFrame:
        """
        Retrieve candle data from database.
        
        Args:
            asset: Asset symbol
            timeframe: Timeframe
            start_date: Start date (optional)
            end_date: End date (optional)
            limit: Limit number of records (optional)
            
        Returns:
            DataFrame with candle data
        """
        with self.db_manager.get_session() as session:
            query = session.query(AssetCandle).filter(
                AssetCandle.asset_symbol == asset,
                AssetCandle.timeframe == timeframe
            )
            
            if start_date:
                query = query.filter(AssetCandle.timestamp >= start_date)
            if end_date:
                query = query.filter(AssetCandle.timestamp <= end_date)
            
            query = query.order_by(AssetCandle.timestamp)
            
            if limit:
                query = query.limit(limit)
            
            results = query.all()
            
            if not results:
                return pd.DataFrame()
            
            # Convert to DataFrame
            data = {
                'timestamp': [r.timestamp for r in results],
                'open': [float(r.open) for r in results],
                'high': [float(r.high) for r in results],
                'low': [float(r.low) for r in results],
                'close': [float(r.close) for r in results],
                'volume': [r.volume for r in results],
                'symbol': [r.asset_symbol for r in results],
                'timeframe': [r.timeframe for r in results]
            }
            
            return pd.DataFrame(data)
    
    def get_latest_candle(self, asset: str, timeframe: str) -> Optional[AssetCandle]:
        """Get the latest candle for an asset."""
        with self.db_manager.get_session() as session:
            return session.query(AssetCandle).filter(
                AssetCandle.asset_symbol == asset,
                AssetCandle.timeframe == timeframe
            ).order_by(desc(AssetCandle.timestamp)).first()
    
    def get_candle_dates(self, asset: str, timeframe: str) -> List[datetime]:
        """Get all dates for which we have candles."""
        with self.db_manager.get_session() as session:
            results = session.query(AssetCandle.timestamp).filter(
                AssetCandle.asset_symbol == asset,
                AssetCandle.timeframe == timeframe
            ).order_by(AssetCandle.timestamp).all()
            return [r[0] for r in results]
    
    # ==================== TECHNICAL INDICATORS ====================
    
    def store_indicator(self, asset: str, timeframe: str, 
                        timestamp: datetime, indicator_name: str, 
                        value: float) -> None:
        """Store a technical indicator value."""
        with self.db_manager.get_session() as session:
            indicator = TechnicalIndicator(
                asset_symbol=asset,
                timeframe=timeframe,
                timestamp=timestamp,
                indicator_name=indicator_name,
                value=value
            )
            session.add(indicator)
            session.commit()
    
    def store_indicators(self, df: pd.DataFrame, asset: str, 
                         timeframe: str, indicator_name: str) -> int:
        """Store multiple indicator values."""
        if df is None or df.empty:
            return 0
        
        stored_count = 0
        with self.db_manager.get_session() as session:
            for _, row in df.iterrows():
                # Check if exists
                existing = session.query(TechnicalIndicator).filter(
                    TechnicalIndicator.asset_symbol == asset,
                    TechnicalIndicator.timeframe == timeframe,
                    TechnicalIndicator.timestamp == row['timestamp'],
                    TechnicalIndicator.indicator_name == indicator_name
                ).first()
                
                if existing:
                    existing.value = row['value']
                else:
                    indicator = TechnicalIndicator(
                        asset_symbol=asset,
                        timeframe=timeframe,
                        timestamp=row['timestamp'],
                        indicator_name=indicator_name,
                        value=row['value']
                    )
                    session.add(indicator)
                stored_count += 1
            
            session.commit()
            logger.info(f"Stored {stored_count} {indicator_name} values for {asset}")
        
        return stored_count
    
    def get_indicators(self, asset: str, timeframe: str, 
                       indicator_name: str,
                       start_date: Optional[datetime] = None,
                       end_date: Optional[datetime] = None) -> pd.DataFrame:
        """Retrieve indicator values."""
        with self.db_manager.get_session() as session:
            query = session.query(TechnicalIndicator).filter(
                TechnicalIndicator.asset_symbol == asset,
                TechnicalIndicator.timeframe == timeframe,
                TechnicalIndicator.indicator_name == indicator_name
            )
            
            if start_date:
                query = query.filter(TechnicalIndicator.timestamp >= start_date)
            if end_date:
                query = query.filter(TechnicalIndicator.timestamp <= end_date)
            
            query = query.order_by(TechnicalIndicator.timestamp)
            results = query.all()
            
            if not results:
                return pd.DataFrame()
            
            data = {
                'timestamp': [r.timestamp for r in results],
                'value': [float(r.value) for r in results]
            }
            return pd.DataFrame(data)
    
    # ==================== AI INSIGHTS ====================
    
    def store_insight(self, insight: Dict[str, Any]) -> int:
        """Store an AI-generated insight."""
        with self.db_manager.get_session() as session:
            ai_insight = AIInsight(
                asset_symbol=insight['asset_symbol'],
                timestamp=datetime.now(),
                insight_type=insight['insight_type'],
                title=insight['title'],
                description=insight['description'],
                confidence=insight['confidence'],
                supporting_data=insight.get('supporting_data', {})
            )
            session.add(ai_insight)
            session.commit()
            return ai_insight.id
    
    def get_latest_insights(self, asset: Optional[str] = None, 
                           limit: int = 10) -> List[Dict[str, Any]]:
        """Get latest AI insights."""
        with self.db_manager.get_session() as session:
            query = session.query(AIInsight)
            if asset:
                query = query.filter(AIInsight.asset_symbol == asset)
            query = query.order_by(desc(AIInsight.timestamp)).limit(limit)
            results = query.all()
            
            return [{
                'id': r.id,
                'asset_symbol': r.asset_symbol,
                'insight_type': r.insight_type,
                'title': r.title,
                'description': r.description,
                'confidence': float(r.confidence) if r.confidence else None,
                'supporting_data': r.supporting_data,
                'created_at': r.created_at
            } for r in results]
    
    # ==================== SIGNALS ====================
    
    def store_signal(self, signal: Dict[str, Any]) -> int:
        """Store a trading signal."""
        with self.db_manager.get_session() as session:
            trading_signal = TradingSignal(
                asset_symbol=signal['asset_symbol'],
                timestamp=datetime.now(),
                signal_type=signal['signal_type'],
                confidence=signal.get('confidence', 0.0),
                strategy=signal.get('strategy', 'technical'),
                metadata=signal.get('metadata', {})
            )
            session.add(trading_signal)
            session.commit()
            return trading_signal.id
    
    def get_latest_signals(self, asset: Optional[str] = None,
                          limit: int = 10) -> List[Dict[str, Any]]:
        """Get latest trading signals."""
        with self.db_manager.get_session() as session:
            query = session.query(TradingSignal)
            if asset:
                query = query.filter(TradingSignal.asset_symbol == asset)
            query = query.order_by(desc(TradingSignal.timestamp)).limit(limit)
            results = query.all()
            
            return [{
                'id': r.id,
                'asset_symbol': r.asset_symbol,
                'signal_type': r.signal_type,
                'confidence': float(r.confidence) if r.confidence else None,
                'strategy': r.strategy,
                'metadata': r.signal_metadata,
                'created_at': r.created_at
            } for r in results]
    
    # ==================== MACRO DATA ====================
    
    def store_macro(self, indicator_name: str, timestamp: datetime,
                   value: float, source: str = 'FRED') -> None:
        """Store macro indicator data."""
        with self.db_manager.get_session() as session:
            macro = MacroIndicator(
                indicator_name=indicator_name,
                timestamp=timestamp,
                value=value,
                source=source
            )
            session.add(macro)
            session.commit()
    
    def get_macro(self, indicator_name: str,
                 start_date: Optional[datetime] = None,
                 end_date: Optional[datetime] = None) -> pd.DataFrame:
        """Retrieve macro indicator data."""
        with self.db_manager.get_session() as session:
            query = session.query(MacroIndicator).filter(
                MacroIndicator.indicator_name == indicator_name
            )
            
            if start_date:
                query = query.filter(MacroIndicator.timestamp >= start_date)
            if end_date:
                query = query.filter(MacroIndicator.timestamp <= end_date)
            
            query = query.order_by(MacroIndicator.timestamp)
            results = query.all()
            
            if not results:
                return pd.DataFrame()
            
            data = {
                'timestamp': [r.timestamp for r in results],
                'value': [float(r.value) for r in results]
            }
            return pd.DataFrame(data)

# Create global database service instance
db_service = DatabaseService()