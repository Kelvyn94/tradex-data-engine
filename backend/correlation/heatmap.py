"""
Correlation Heatmap - Multi-Timeframe Visual Analysis
Generates visual correlation heatmaps for all timeframes.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import logging
import matplotlib.pyplot as plt
import seaborn as sns
from io import BytesIO
import base64

from backend.services.database_service import db_service
from backend.config.settings import settings

logger = logging.getLogger(__name__)


class CorrelationHeatmap:
    """
    Multi-timeframe correlation heatmap generator.
    """
    
    def __init__(self):
        self.last_heatmap = None
        self.timeframes = ['30m', '1h', '4h', 'daily', 'weekly']
        logger.info("CorrelationHeatmap initialized")
    
    def generate(self, assets: Optional[List[str]] = None,
                 timeframe: str = 'daily',
                 lookback: int = 252,
                 save_path: Optional[str] = None) -> Dict:
        """Generate correlation heatmap for a specific timeframe."""
        if assets is None:
            assets = settings.ASSETS
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=lookback * 2)
        
        data = {}
        for asset in assets:
            df = db_service.get_candles(asset, timeframe, start_date, end_date)
            if df is not None and not df.empty:
                data[asset] = df.set_index('timestamp')['close']
        
        if len(data) < 2:
            return {'error': 'Not enough assets'}
        
        aligned = pd.DataFrame(data).ffill().dropna()
        returns = aligned.pct_change().dropna()
        corr_matrix = returns.corr()
        
        # Create heatmap
        fig, ax = plt.subplots(figsize=(10, 8))
        mask = np.triu(np.ones_like(corr_matrix, dtype=bool))
        
        sns.heatmap(
            corr_matrix,
            mask=mask,
            annot=True,
            fmt='.2f',
            cmap='RdBu_r',
            vmin=-1,
            vmax=1,
            center=0,
            square=True,
            linewidths=0.5,
            cbar_kws={"shrink": 0.8},
            ax=ax
        )
        
        ax.set_title(f'Correlation Heatmap - {timeframe} (6 Assets)', fontsize=14)
        plt.tight_layout()
        
        # Convert to base64
        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        plt.close()
        
        return {
            'correlation_matrix': corr_matrix.to_dict(),
            'image_base64': image_base64,
            'timeframe': timeframe,
            'assets': assets,
            'lookback': lookback
        }
    
    def generate_all_timeframes(self, assets: Optional[List[str]] = None) -> Dict:
        """Generate heatmaps for ALL timeframes."""
        if assets is None:
            assets = settings.ASSETS
        
        results = {}
        
        for tf in self.timeframes:
            try:
                results[tf] = self.generate(assets, tf)
            except Exception as e:
                logger.error(f"Error generating heatmap for {tf}: {e}")
                results[tf] = {'error': str(e)}
        
        return results