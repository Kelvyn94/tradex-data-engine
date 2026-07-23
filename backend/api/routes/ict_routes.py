"""
ICT (Inner Circle Trader) analysis routes for TradeX Data Engine.

Exposes ICTService, which was fully implemented (market structure, BOS,
CHOCH, order blocks, FVGs, liquidity, killzones, premium/discount,
mitigation, dealing range, quarterly theory, SMT divergence) but never
wired to an HTTP route — every request TRADEX made to
/api/v1/ict/analyze/{asset} was a structural 404 until this file existed.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from backend.services.ict_service import ICTService
from backend.config.settings import settings

router = APIRouter(prefix="/api/v1/ict", tags=["ict"])

_ict_service = ICTService()

# Correlated pairs SMT divergence is actually checked across — mirrors the
# groupings TRADEX's own smtDetection.service.js uses, so a signal raised
# on either side of the stack means the same thing.
SMT_PAIRS = [
    ("XAUUSD", "XAGUSD"),
    ("EURUSD", "GBPUSD"),
]


@router.get("/analyze/{asset}")
async def analyze_asset(asset: str, timeframe: str = "daily", lookback: int = 200):
    """
    Complete ICT analysis for a single asset: market structure, BOS/CHOCH,
    order blocks, FVGs, liquidity zones, killzones, premium/discount,
    mitigation, dealing range, quarterly theory, and a combined signal.
    """
    if asset not in settings.ASSETS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown asset '{asset}'. Expected one of {settings.ASSETS}",
        )

    try:
        result = _ict_service.analyze_asset(asset, timeframe, lookback)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if "error" in result:
        return {"status": "success", "asset": asset, "data": None, "message": result["error"]}

    return {"status": "success", "asset": asset, "data": result}


@router.get("/smt")
async def smt_divergence(timeframe: str = "daily", pair: Optional[str] = Query(default=None)):
    """
    SMT divergence across correlated asset pairs (XAUUSD/XAGUSD,
    EURUSD/GBPUSD by default). Pass pair=XAUUSD,XAGUSD to check a specific
    pair instead of every default pair.
    """
    pairs_to_check = SMT_PAIRS
    if pair:
        parts = [p.strip() for p in pair.split(",")]
        if len(parts) != 2:
            raise HTTPException(status_code=400, detail="pair must be 'ASSET1,ASSET2'")
        pairs_to_check = [tuple(parts)]

    from backend.services.database_service import db_service

    results = []
    for asset1, asset2 in pairs_to_check:
        df1 = db_service.get_candles(asset1, timeframe, limit=100)
        df2 = db_service.get_candles(asset2, timeframe, limit=100)

        if df1 is None or df1.empty or df2 is None or df2.empty:
            results.append({
                "asset1": asset1,
                "asset2": asset2,
                "error": "Insufficient candle data",
            })
            continue

        try:
            analysis = _ict_service.smt_analyzer.analyze(df1, df2, asset1, asset2)
            results.append(analysis)
        except Exception as e:
            results.append({"asset1": asset1, "asset2": asset2, "error": str(e)})

    return {"status": "success", "timeframe": timeframe, "data": results}
