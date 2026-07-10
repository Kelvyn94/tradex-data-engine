"""
Data API routes for TradeX Data Engine.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from datetime import datetime, timedelta
import pandas as pd

from backend.services.database_service import db_service
from backend.services.download_service import DownloadService

router = APIRouter(prefix="/api/v1/data", tags=["data"])

@router.get("/candles/{asset}")
async def get_candles(
    asset: str,
    timeframe: str = "daily",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: Optional[int] = 100
):
    """
    Get candle data for an asset.
    """
    try:
        # Parse dates
        if start_date:
            start = datetime.fromisoformat(start_date)
        else:
            start = datetime.now() - timedelta(days=30)
        
        if end_date:
            end = datetime.fromisoformat(end_date)
        else:
            end = datetime.now()
        
        # Get data
        df = db_service.get_candles(asset, timeframe, start, end, limit)
        
        if df.empty:
            return {
                "status": "success",
                "data": [],
                "message": "No data found"
            }
        
        # Convert to records
        records = df.to_dict(orient='records')
        
        return {
            "status": "success",
            "asset": asset,
            "timeframe": timeframe,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "count": len(records),
            "data": records
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/indicators/{asset}")
async def get_indicators(
    asset: str,
    timeframe: str = "daily",
    indicator: str = "sma_20",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """
    Get technical indicator values.
    """
    try:
        # Parse dates
        if start_date:
            start = datetime.fromisoformat(start_date)
        else:
            start = datetime.now() - timedelta(days=30)
        
        if end_date:
            end = datetime.fromisoformat(end_date)
        else:
            end = datetime.now()
        
        # Get data
        df = db_service.get_indicators(asset, timeframe, indicator, start, end)
        
        if df.empty:
            return {
                "status": "success",
                "data": [],
                "message": "No data found"
            }
        
        records = df.to_dict(orient='records')
        
        return {
            "status": "success",
            "asset": asset,
            "indicator": indicator,
            "count": len(records),
            "data": records
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/latest/{asset}")
async def get_latest(
    asset: str,
    timeframe: str = "daily"
):
    """
    Get latest candle for an asset.
    """
    try:
        candle = db_service.get_latest_candle(asset, timeframe)
        
        if not candle:
            return {
                "status": "success",
                "data": None,
                "message": "No data found"
            }
        
        return {
            "status": "success",
            "asset": asset,
            "timeframe": timeframe,
            "data": {
                "timestamp": candle.timestamp.isoformat(),
                "open": float(candle.open),
                "high": float(candle.high),
                "low": float(candle.low),
                "close": float(candle.close),
                "volume": candle.volume
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/macro/{indicator}")
async def get_macro(
    indicator: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """
    Get macro indicator data.
    """
    try:
        if start_date:
            start = datetime.fromisoformat(start_date)
        else:
            start = datetime.now() - timedelta(days=365)
        
        if end_date:
            end = datetime.fromisoformat(end_date)
        else:
            end = datetime.now()
        
        df = db_service.get_macro(indicator, start, end)
        
        if df.empty:
            return {
                "status": "success",
                "data": [],
                "message": "No data found"
            }
        
        records = df.to_dict(orient='records')
        
        return {
            "status": "success",
            "indicator": indicator,
            "count": len(records),
            "data": records
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/update")
async def trigger_update(
    assets: Optional[List[str]] = None,
    timeframes: Optional[List[str]] = None,
    days: int = 5
):
    """
    Manually trigger a data update.
    """
    try:
        from backend.config.settings import settings
        
        if not assets:
            assets = settings.ASSETS
        
        if not timeframes:
            timeframes = settings.TIMEFRAMES
        
        download_service = DownloadService()
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        result = download_service.run_download_pipeline(
            start_date=start_date,
            end_date=end_date,
            assets=assets,
            timeframes=timeframes
        )
        
        # Store in database
        for asset, timeframes_data in result.get('results', {}).items():
            for tf, data in timeframes_data.items():
                if data.get('success') and data.get('rows', 0) > 0:
                    import pandas as pd
                    from pathlib import Path
                    
                    raw_path = Path(data.get('raw_path', ''))
                    if raw_path and raw_path.exists():
                        df = pd.read_csv(raw_path)
                        if not df.empty:
                            df['timestamp'] = pd.to_datetime(df['timestamp'])
                            db_service.store_candles(df, asset, tf)
        
        return {
            "status": "success",
            "message": "Update triggered successfully",
            "result": result
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))