"""
Feature Engineering - Lightweight, Free Tier Optimized
Generates features without heavy memory usage.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import logging

from backend.services.database_service import db_service

logger = logging.getLogger(__name__)


class FeatureEngineer:
    """
    Lightweight feature engineering.
    Features are generated on-demand, not stored.
    """
    
    def __init__(self):
        self.feature_cache = {}
        logger.info("FeatureEngineer initialized (free tier optimized)")
    
    def generate_features(self, asset: str, timeframe: str = 'daily',
                         lookback: int = 200) -> pd.DataFrame:
        """
        Generate features for ML models.
        Memory efficient - processes in batches.
        """
        # Get data
        end_date = datetime.now()
        start_date = end_date - timedelta(days=lookback * 2)
        
        df = db_service.get_candles(asset, timeframe, start_date, end_date)
        
        if df is None or df.empty:
            return pd.DataFrame()
        
        # Process in batches to save memory
        batch_size = 100
        features_list = []
        
        for i in range(0, len(df), batch_size):
            batch_df = df.iloc[i:i+batch_size].copy()
            features = self._process_batch(batch_df, asset, timeframe)
            features_list.append(features)
        
        if features_list:
            result = pd.concat(features_list, ignore_index=True)
            logger.info(f"Generated {len(result.columns)} features for {asset}")
            return result
        
        return pd.DataFrame()
    
    def _process_batch(self, df: pd.DataFrame, asset: str, timeframe: str) -> pd.DataFrame:
        """Process a batch of data."""
        features = pd.DataFrame(index=df.index)
        
        # Price features (minimal memory)
        features['close'] = df['close']
        features['high'] = df['high']
        features['low'] = df['low']
        features['open'] = df['open']
        features['volume'] = df['volume']
        
        # Returns (vectorized)
        for period in [1, 2, 3, 5, 10, 20]:
            features[f'return_{period}'] = df['close'].pct_change(period)
        
        # Moving averages (efficient rolling)
        for period in [5, 10, 20, 50]:
            features[f'sma_{period}'] = df['close'].rolling(period).mean()
            features[f'ema_{period}'] = df['close'].ewm(span=period).mean()
        
        # Volatility
        for period in [5, 10, 20]:
            features[f'vol_{period}'] = df['close'].pct_change().rolling(period).std()
        
        # RSI (efficient)
        for period in [10, 14, 20]:
            features[f'rsi_{period}'] = self._calculate_rsi(df['close'], period)
        
        # Simple ICT features (no heavy computation)
        features['bos_signal'] = self._detect_bos(df['close'])
        features['momentum'] = df['close'].pct_change(10)
        features['price_position'] = self._price_position(df['close'])
        
        # Drop NaN rows
        features = features.dropna()
        
        return features
    
    def _calculate_rsi(self, prices: pd.Series, period: int) -> pd.Series:
        """Calculate RSI."""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    def _detect_bos(self, prices: pd.Series) -> pd.Series:
        """Simple BOS detection."""
        lookback = 20
        rolling_high = prices.rolling(window=lookback).max()
        rolling_low = prices.rolling(window=lookback).min()
        
        bos = pd.Series(index=prices.index, dtype=float)
        bos[:] = 0.0
        
        for i in range(lookback + 1, len(prices)):
            if prices.iloc[i] > rolling_high.iloc[i-1]:
                bos.iloc[i] = 1.0
            elif prices.iloc[i] < rolling_low.iloc[i-1]:
                bos.iloc[i] = -1.0
        
        return bos
    
    def _price_position(self, prices: pd.Series) -> pd.Series:
        """Price position in recent range."""
        lookback = 20
        high = prices.rolling(window=lookback).max()
        low = prices.rolling(window=lookback).min()
        range_size = high - low
        
        position = pd.Series(index=prices.index, dtype=float)
        position[:] = 0.5
        
        for i in range(lookback + 1, len(prices)):
            if range_size.iloc[i] > 0:
                position.iloc[i] = (prices.iloc[i] - low.iloc[i]) / range_size.iloc[i]
        
        return position