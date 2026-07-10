"""
Database models for TradeX Data Engine.
Uses SQLAlchemy ORM with PostgreSQL.
"""

from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Boolean, 
    Text, JSON, Numeric, Index, BigInteger
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()

class AssetCandle(Base):
    """Asset price candle data."""
    __tablename__ = 'asset_candles'
    __table_args__ = {'schema': 'data_engine'}
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    asset_symbol = Column(String(20), nullable=False)
    timeframe = Column(String(10), nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    open = Column(Numeric(20, 8), nullable=False)
    high = Column(Numeric(20, 8), nullable=False)
    low = Column(Numeric(20, 8), nullable=False)
    close = Column(Numeric(20, 8), nullable=False)
    volume = Column(BigInteger, default=0)
    is_synthetic = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    __table_args__ = (
        Index('idx_candle_lookup', 'asset_symbol', 'timeframe', 'timestamp'),
        Index('idx_candle_asset_time', 'asset_symbol', 'timestamp'),
        Index('idx_candle_timeframe_time', 'timeframe', 'timestamp'),
    )

class MacroIndicator(Base):
    """Macroeconomic indicators."""
    __tablename__ = 'macro_indicators'
    __table_args__ = {'schema': 'data_engine'}
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    indicator_name = Column(String(50), nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    value = Column(Numeric(20, 8))
    source = Column(String(50))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index('idx_macro_name_time', 'indicator_name', 'timestamp'),
    )

class SentimentData(Base):
    """Sentiment data from news and social media."""
    __tablename__ = 'sentiment_data'
    __table_args__ = {'schema': 'data_engine'}
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    asset_symbol = Column(String(20), nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    source = Column(String(50))
    sentiment_score = Column(Numeric(5, 4))
    title = Column(Text)
    url = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index('idx_sentiment_asset_time', 'asset_symbol', 'timestamp'),
    )

class TechnicalIndicator(Base):
    """Pre-calculated technical indicators."""
    __tablename__ = 'technical_indicators'
    __table_args__ = {'schema': 'data_engine'}
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    asset_symbol = Column(String(20), nullable=False)
    timeframe = Column(String(10), nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    indicator_name = Column(String(50), nullable=False)
    value = Column(Numeric(20, 8))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index('idx_tech_lookup', 'asset_symbol', 'timeframe', 'indicator_name', 'timestamp'),
    )

class TradingSignal(Base):
    """Generated trading signals."""
    __tablename__ = 'signals'
    __table_args__ = {'schema': 'data_engine'}
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    asset_symbol = Column(String(20), nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    signal_type = Column(String(20))  # BUY, SELL, HOLD
    confidence = Column(Numeric(5, 4))
    strategy = Column(String(50))
    signal_metadata = Column(JSON)  # CHANGED: 'metadata' -> 'signal_metadata'
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index('idx_signal_asset_time', 'asset_symbol', 'timestamp'),
        Index('idx_signal_type_time', 'signal_type', 'timestamp'),
    )

class AIInsight(Base):
    """AI-generated market insights."""
    __tablename__ = 'ai_insights'
    __table_args__ = {'schema': 'data_engine'}
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    asset_symbol = Column(String(20), nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    insight_type = Column(String(50))  # TREND, REVERSAL, BREAKOUT, VOLATILITY
    title = Column(String(200))
    description = Column(Text)
    confidence = Column(Numeric(5, 4))
    supporting_data = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index('idx_insight_asset_time', 'asset_symbol', 'timestamp'),
        Index('idx_insight_type', 'insight_type'),
    )