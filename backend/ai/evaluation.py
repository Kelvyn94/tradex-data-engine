"""
Model Evaluation - Lightweight metrics.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
import logging

logger = logging.getLogger(__name__)


class ModelEvaluator:
    """
    Evaluate model performance with lightweight metrics.
    """
    
    def __init__(self):
        logger.info("ModelEvaluator initialized")
    
    def evaluate(self, y_true, y_pred) -> Dict:
        """
        Calculate evaluation metrics.
        """
        try:
            accuracy = accuracy_score(y_true, y_pred)
            precision = precision_score(y_true, y_pred, average='weighted', zero_division=0)
            recall = recall_score(y_true, y_pred, average='weighted', zero_division=0)
            f1 = f1_score(y_true, y_pred, average='weighted', zero_division=0)
            
            return {
                'accuracy': accuracy,
                'precision': precision,
                'recall': recall,
                'f1_score': f1
            }
        except Exception as e:
            logger.error(f"Evaluation error: {e}")
            return {'error': str(e)}