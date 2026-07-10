"""
Label Generation - Creates training labels.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class LabelGenerator:
    """
    Generate labels for ML training.
    """
    
    def __init__(self):
        logger.info("LabelGenerator initialized")
    
    def generate_labels(self, df: pd.DataFrame, 
                        horizon: int = 5,
                        method: str = 'direction') -> pd.Series:
        """
        Generate labels for training.
        
        Args:
            df: DataFrame with OHLCV data
            horizon: Prediction horizon (days ahead)
            method: 'direction' or 'return' or 'classification'
            
        Returns:
            Series with labels
        """
        if df is None or df.empty:
            return pd.Series()
        
        close = df['close']
        future_close = close.shift(-horizon)
        
        if method == 'direction':
            # Binary: 1 for up, 0 for down
            labels = (future_close > close).astype(int)
        elif method == 'return':
            # Continuous: percentage return
            labels = (future_close - close) / close
        elif method == 'classification':
            # Multi-class: Strong Up, Up, Neutral, Down, Strong Down
            returns = (future_close - close) / close
            labels = pd.cut(returns, 
                           bins=[-float('inf'), -0.02, -0.005, 0.005, 0.02, float('inf')],
                           labels=[-2, -1, 0, 1, 2])
        else:
            raise ValueError(f"Unknown method: {method}")
        
        # Drop NaN (last horizon rows)
        labels = labels.dropna()
        
        logger.info(f"Generated {len(labels)} labels using {method} method")
        
        return labels