"""
Prediction Engine - Generates predictions from trained models.
"""

import pandas as pd
import numpy as np
import joblib
from pathlib import Path
from typing import Dict, Optional, List
from datetime import datetime
import logging

from backend.services.database_service import db_service
from backend.ai.feature_engineering import FeatureEngineer

logger = logging.getLogger(__name__)


class PredictionEngine:
    """
    Generate predictions using trained models.
    """
    
    def __init__(self, model_dir: Path = Path('models')):
        self.model_dir = model_dir
        self.feature_engineer = FeatureEngineer()
        logger.info("PredictionEngine initialized")
    
    def predict(self, asset: str, timeframe: str = 'daily') -> Dict:
        """
        Generate prediction for an asset.
        
        Args:
            asset: Asset symbol
            timeframe: Timeframe to use
            
        Returns:
            Prediction result
        """
        # Get latest model
        model_path = self._get_latest_model(asset)
        if model_path is None:
            return {'error': f'No model found for {asset}'}
        
        # Load model
        model = joblib.load(model_path)
        
        # Get latest features
        features = self.feature_engineer.generate_features(asset, timeframe, lookback=100)
        
        if features.empty:
            return {'error': 'No features generated'}
        
        # Get latest row
        latest_features = features.iloc[-1:].dropna()
        
        if latest_features.empty:
            return {'error': 'No valid features'}
        
        # Make prediction
        prediction = model.predict(latest_features)[0]
        
        # Get probability
        try:
            probability = model.predict_proba(latest_features)[0]
            confidence = float(max(probability))
        except:
            confidence = 0.5
        
        # Get latest price
        end_date = datetime.now()
        start_date = end_date - timedelta(days=10)
        df = db_service.get_candles(asset, timeframe, start_date, end_date)
        current_price = df['close'].iloc[-1] if df is not None and not df.empty else None
        
        return {
            'asset': asset,
            'timeframe': timeframe,
            'prediction': int(prediction),
            'direction': 'UP' if prediction == 1 else 'DOWN',
            'confidence': confidence,
            'current_price': float(current_price) if current_price else None,
            'timestamp': datetime.now().isoformat()
        }
    
    def _get_latest_model(self, asset: str) -> Optional[Path]:
        """Get the latest model for an asset."""
        models = list(self.model_dir.glob(f"{asset}_*.pkl"))
        if not models:
            return None
        
        # Sort by modification time
        models.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        return models[0]