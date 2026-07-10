"""
Abstract base class for all data providers.
"""

from abc import ABC, abstractmethod
from typing import Optional, List
from datetime import datetime
import pandas as pd

class BaseProvider(ABC):
    """Abstract base class for all data providers."""
    
    @abstractmethod
    def download_asset(self, symbol: str, timeframe: str, 
                      start_date: datetime, end_date: datetime) -> Optional[pd.DataFrame]:
        """Download asset data."""
        pass
    
    @abstractmethod
    def get_supported_assets(self) -> List[str]:
        """Get list of supported assets."""
        pass
    
    @abstractmethod
    def get_timeframes(self) -> List[str]:
        """Get list of supported timeframes."""
        pass
    
    @abstractmethod
    def validate_symbol(self, symbol: str) -> bool:
        """Validate if symbol is supported."""
        pass