"""
Configuration settings for the TradeX Data Engine.
"""

from pathlib import Path
from typing import List, Optional, Dict
from dataclasses import dataclass, field
import os
from datetime import datetime

@dataclass
class Settings:
    """Application settings."""
    
    # Assets
    ASSETS: List[str] = field(default_factory=lambda: [
        'EURUSD', 'GBPUSD', 'XAUUSD', 'XAGUSD', 'XAUEUR', 'XAUGBP'
    ])
    
    # Timeframes
    TIMEFRAMES: List[str] = field(default_factory=lambda: [
        'weekly', 'daily', '4h', '1h', '30m'
    ])
    
    # Historical data targets (in years)
    HISTORICAL_TARGETS: Dict[str, int] = field(default_factory=lambda: {
        'weekly': 15,
        'daily': 10,
        '4h': 10,
        '1h': 5,
        '30m': 5,
    })
    
    # Data paths
    DATA_DIR: Path = Path('data')
    RAW_DATA_DIR: Path = Path('data/raw')
    CLEANED_DATA_DIR: Path = Path('data/cleaned')
    METADATA_DIR: Path = Path('data/metadata')
    REPORTS_DIR: Path = Path('reports')
    LOGS_DIR: Path = Path('logs')
    
    # Database Configuration
    DATABASE_URL: str = os.getenv('DATABASE_URL', "postgresql://neondb_owner:npg_faNmnb8q5Wds@ep-twilight-brook-adbmb6hq-pooler.c-2.us-east-1.aws.neon.tech/neondb?sslmode=require")
    
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    
    # API Keys
    NEWS_API_KEY: str = os.getenv('NEWS_API_KEY', "06a2e8449d244722a2e432039dc0c46b")
    FRED_API_KEY: str = os.getenv('FRED_API_KEY', "d5dc8c57d9922d0f2b3d04c64b2f7520")
    
    # Scheduler Settings
    SCHEDULER_ENABLED: bool = False  # DISABLED to prevent openbb errors
    
    # AI Settings
    AI_ENABLED: bool = True
    AI_MODEL_PATH: Path = Path('models')
    AI_UPDATE_INTERVAL: int = 3600
    
    # Provider settings - Use Yahoo only (no openbb)
    DEFAULT_PROVIDER: str = 'yahoo'
    
    # Download batch size
    DOWNLOAD_BATCH_SIZE: int = 2
    
    def __post_init__(self):
        """Create directories if they don't exist."""
        for dir_path in [
            self.DATA_DIR, self.RAW_DATA_DIR, self.CLEANED_DATA_DIR,
            self.METADATA_DIR, self.REPORTS_DIR, self.LOGS_DIR,
            self.AI_MODEL_PATH
        ]:
            dir_path.mkdir(parents=True, exist_ok=True)

# Create global settings instance
settings = Settings()
