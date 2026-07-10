"""
Model Manager - Manage model versions.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class ModelManager:
    """
    Manage model versions and metadata.
    """
    
    def __init__(self, model_dir: Path = Path('models')):
        self.model_dir = model_dir
        self.model_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"ModelManager initialized")
    
    def list_models(self, asset: Optional[str] = None) -> List[Dict]:
        """List all models."""
        models = []
        for metadata_file in self.model_dir.glob("*_metadata.json"):
            with open(metadata_file, 'r') as f:
                data = json.load(f)
                if asset is None or data.get('asset') == asset:
                    models.append(data)
        return sorted(models, key=lambda x: x.get('created_at', ''), reverse=True)
    
    def get_latest(self, asset: str) -> Optional[Dict]:
        """Get latest model for asset."""
        models = self.list_models(asset)
        return models[0] if models else None