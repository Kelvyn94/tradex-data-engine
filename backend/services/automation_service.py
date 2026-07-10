"""
Automation Service - Free Tier Optimized.
Runs scheduled tasks using lightweight checks.
"""

import time
from datetime import datetime, timedelta
import logging
import threading
from typing import Dict, List, Optional

from backend.services.download_service import DownloadService
from backend.services.database_service import db_service
from backend.services.scheduler_service import scheduler
from backend.ai.inference import InferenceEngine
from backend.ai.training import ModelTrainer
from backend.ai.feature_engineering import FeatureEngineer
from backend.ai.labeling import LabelGenerator

logger = logging.getLogger(__name__)


class AutomationService:
    """
    Automated service with minimal resource usage.
    """
    
    def __init__(self):
        self.is_running = False
        self.thread = None
        self.interval = 3600  # 1 hour
        self.inference = InferenceEngine()
        self.trainer = ModelTrainer()
        self.feature_engineer = FeatureEngineer()
        self.label_generator = LabelGenerator()
        
        logger.info("AutomationService initialized")
    
    def start(self):
        """Start automation service."""
        if self.is_running:
            return
        
        self.is_running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        logger.info("AutomationService started")
    
    def stop(self):
        """Stop automation service."""
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("AutomationService stopped")
    
    def _run_loop(self):
        """Main loop for automation."""
        while self.is_running:
            try:
                self._run_tasks()
                time.sleep(self.interval)
            except Exception as e:
                logger.error(f"Automation error: {e}")
                time.sleep(60)
    
    def _run_tasks(self):
        """Run all automation tasks."""
        from backend.config.settings import settings
        
        logger.info("Running automation tasks...")
        
        # 1. Check if data needs updating
        self._check_data_updates()
        
        # 2. Generate predictions
        self._generate_predictions(settings.ASSETS)
        
        # 3. Check if models need retraining
        self._check_model_retraining(settings.ASSETS)
    
    def _check_data_updates(self):
        """Check and update data if needed."""
        from backend.config.settings import settings
        
        for asset in settings.ASSETS:
            latest = db_service.get_latest_candle(asset, 'daily')
            if latest:
                age = (datetime.now() - latest.timestamp).days
                if age > 1:
                    logger.info(f"Updating data for {asset} (last: {age} days ago)")
                    # Trigger update
                    download_service = DownloadService()
                    end_date = datetime.now()
                    start_date = end_date - timedelta(days=age + 1)
                    download_service.download_asset_data(asset, 'daily', start_date, end_date)
    
    def _generate_predictions(self, assets: List[str]):
        """Generate predictions for all assets."""
        for asset in assets:
            try:
                prediction = self.inference.get_prediction(asset)
                if prediction.get('status') == 'SUCCESS':
                    logger.debug(f"Prediction for {asset}: {prediction.get('direction')} ({prediction.get('confidence'):.2f})")
            except Exception as e:
                logger.error(f"Prediction error for {asset}: {e}")
    
    def _check_model_retraining(self, assets: List[str]):
        """Check and retrain models if needed."""
        for asset in assets:
            try:
                # Check if model needs retraining
                model_path = Path('models') / f"{asset}_latest.pkl"
                need_retrain = False
                
                if not model_path.exists():
                    need_retrain = True
                else:
                    # Check model age
                    age = (datetime.now() - datetime.fromtimestamp(model_path.stat().st_mtime)).days
                    if age > 7:  # Retrain weekly
                        need_retrain = True
                
                if need_retrain:
                    logger.info(f"Retraining model for {asset}")
                    self._retrain_model(asset)
            except Exception as e:
                logger.error(f"Retraining error for {asset}: {e}")
    
    def _retrain_model(self, asset: str):
        """Retrain model for an asset."""
        # Generate features and labels
        features = self.feature_engineer.generate_features(asset, lookback=500)
        if features.empty:
            return
        
        labels = self.label_generator.generate_labels(features, horizon=5, method='direction')
        if labels.empty:
            return
        
        # Train model
        result = self.trainer.train(asset, features, labels, f"{asset}_latest")
        
        if result.get('accuracy'):
            logger.info(f"Model retrained for {asset} (accuracy: {result['accuracy']:.4f})")