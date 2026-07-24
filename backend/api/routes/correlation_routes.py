"""
Correlation matrix routes.
"""

from fastapi import APIRouter, HTTPException

from backend.correlation.matrix import CorrelationMatrix
from backend.config.settings import settings

router = APIRouter(prefix="/api/v1/correlation", tags=["correlation"])


@router.get("/matrix")
async def get_correlation_matrix(timeframe: str = "daily", lookback: int = 100):
    """
    Pearson correlation matrix of returns across this app's tracked
    assets, computed over the most recent `lookback` candles at the
    given timeframe (a real period count, not a calendar-day window -
    see CorrelationMatrix.calculate()).

    Only the numeric matrix and statistically-flagged strong pairs are
    exposed here - CorrelationMatrix/CorrelationService also generate
    "trading_recommendations" with hardcoded confidence scores (0.7,
    0.8) that aren't derived from any real statistical backing;
    deliberately not surfaced through this route.
    """
    cm = CorrelationMatrix()
    result = cm.calculate(settings.ASSETS, timeframe=timeframe, lookback=lookback)

    if "error" in result:
        raise HTTPException(status_code=503, detail=result["error"])

    corr_df = result["correlation_matrix"]
    return {
        "status": "success",
        "data": {
            "assets": list(corr_df.columns),
            "matrix": corr_df.values.tolist(),
            "strongCorrelations": cm.get_strong_correlations(),
            "timeframe": timeframe,
            "lookback": lookback,
            "lastUpdate": result["last_update"],
        },
    }
