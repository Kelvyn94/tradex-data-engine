"""
Inference Engine - Lightweight inference for real-time predictions.
"""

import pandas as pd
import numpy as np
import joblib
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import logging

from backend.services.database_service import db_service
from backend.ai.feature_engineering import FeatureEngineer

logger = logging.getLogger(__name__)


class InferenceEngine:
    """
    Lightweight inference for predictions.
    """
    
    def __init__(self):
        self.feature_engineer = FeatureEngineer()
        self.prediction_cache = {}
        self.cache_timeout = 300  # 5 minutes
        self.model_dir = Path('models')
        logger.info("InferenceEngine initialized")
    
    def get_prediction(self, asset: str, timeframe: str = 'daily') -> Dict:
        """
        Get prediction with caching.
        """
        cache_key = f"{asset}_{timeframe}"
        
        # Check cache
        if cache_key in self.prediction_cache:
            cached = self.prediction_cache[cache_key]
            if (datetime.now() - cached['timestamp']).seconds < self.cache_timeout:
                return cached['result']
        
        # Generate new prediction
        result = self._generate_prediction(asset, timeframe)
        
        # Cache result
        self.prediction_cache[cache_key] = {
            'timestamp': datetime.now(),
            'result': result
        }
        
        return result
    
    def _generate_prediction(self, asset: str, timeframe: str) -> Dict:
        """
        Generate prediction using trained model.
        """
        # Find the latest model for this asset
        model_files = list(self.model_dir.glob(f"{asset}_*.pkl"))
        if not model_files:
            return {
                'asset': asset,
                'prediction': None,
                'error': 'No model available',
                'status': 'TRAINING_NEEDED'
            }
        
        # Get the latest model
        model_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        model_path = model_files[0]
        
        try:
            model = joblib.load(model_path)
        except Exception as e:
            return {
                'asset': asset,
                'prediction': None,
                'error': f'Model load failed: {e}',
                'status': 'ERROR'
            }
        
        # Get features
        features = self.feature_engineer.generate_features(asset, timeframe, lookback=100)
        
        if features.empty:
            return {
                'asset': asset,
                'prediction': None,
                'error': 'No features',
                'status': 'NO_DATA'
            }
        
        latest = features.iloc[-1:].dropna()
        
        if latest.empty:
            return {
                'asset': asset,
                'prediction': None,
                'error': 'Invalid features',
                'status': 'NO_DATA'
            }
        
        try:
            # Get current price
            end_date = datetime.now()
            start_date = end_date - timedelta(days=10)
            df = db_service.get_candles(asset, timeframe, start_date, end_date)
            current_price = df['close'].iloc[-1] if df is not None and not df.empty else None
            
            # Make prediction
            pred = model.predict(latest)[0]
            
            # Get probability if available
            try:
                prob = model.predict_proba(latest)[0]
                confidence = float(max(prob))
            except:
                confidence = 0.5
            
            return {
                'asset': asset,
                'prediction': int(pred),
                'direction': 'UP' if pred == 1 else 'DOWN',
                'confidence': confidence,
                'current_price': float(current_price) if current_price else None,
                'status': 'SUCCESS',
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            return {
                'asset': asset,
                'prediction': None,
                'error': str(e),
                'status': 'ERROR'
            }
    
    def get_all_predictions(self) -> Dict:
        """Get predictions for all assets."""
        from backend.config.settings import settings
        
        results = {}
        for asset in settings.ASSETS:
            results[asset] = self.get_prediction(asset)
        
        return results