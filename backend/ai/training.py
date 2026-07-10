"""
Model Training - Lightweight XGBoost Models.
Free tier optimized - no GPU needed.
"""

import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, mean_squared_error
import joblib
from pathlib import Path
from datetime import datetime
import logging
import json
from typing import Dict, Optional, List, Any

logger = logging.getLogger(__name__)


class ModelTrainer:
    """
    Lightweight model training for free tier.
    Uses XGBoost - efficient and fast.
    """
    
    def __init__(self, model_dir: Path = Path('models')):
        self.model_dir = model_dir
        self.model_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"ModelTrainer initialized (models saved to {model_dir})")
    
    def train(self, asset: str, 
              features: pd.DataFrame,
              labels: pd.Series,
              model_name: str = None) -> Dict[str, Any]:
        """
        Train XGBoost model.
        
        Args:
            asset: Asset symbol
            features: Feature DataFrame
            labels: Label Series
            model_name: Custom model name
            
        Returns:
            Training results
        """
        if features.empty or labels.empty:
            return {'error': 'No data'}
        
        # Align features and labels
        common_idx = features.index.intersection(labels.index)
        X = features.loc[common_idx]
        y = labels.loc[common_idx]
        
        if len(X) < 50:
            return {'error': 'Not enough data'}
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, shuffle=False
        )
        
        # Train XGBoost (lightweight)
        model = xgb.XGBClassifier(
            n_estimators=100,
            max_depth=5,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            use_label_encoder=False,
            eval_metric='logloss'
        )
        
        model.fit(X_train, y_train)
        
        # Evaluate
        y_pred = model.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)
        
        # Feature importance
        importance = pd.DataFrame({
            'feature': X.columns,
            'importance': model.feature_importances_
        }).sort_values('importance', ascending=False)
        
        # Save model
        model_name = model_name or f"{asset}_{datetime.now().strftime('%Y%m%d')}"
        model_path = self.model_dir / f"{model_name}.pkl"
        joblib.dump(model, model_path)
        
        # Save metadata
        metadata = {
            'asset': asset,
            'model_name': model_name,
            'accuracy': float(accuracy),
            'features': len(X.columns),
            'samples': len(X),
            'top_features': importance.head(10).to_dict('records'),
            'created_at': datetime.now().isoformat()
        }
        
        with open(self.model_dir / f"{model_name}_metadata.json", 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Model trained: {model_name} (accuracy: {accuracy:.4f})")
        
        return {
            'model_name': model_name,
            'accuracy': accuracy,
            'feature_importance': importance.head(10).to_dict('records'),
            'samples': len(X)
        }