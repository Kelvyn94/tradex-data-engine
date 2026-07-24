"""
Macro regime routes: DXY / 10-Year Treasury Yield / VIX snapshot.
"""

from fastapi import APIRouter, HTTPException

from backend.services.macro_regime_service import macro_regime_service

router = APIRouter(prefix="/api/v1/macro", tags=["macro"])


@router.get("/regime")
async def get_macro_regime():
    """
    US Dollar Index (DXY), 10-Year Treasury Yield, and VIX snapshot,
    plus a simple risk-on/elevated/risk-off regime label derived from
    VIX level.
    """
    data = macro_regime_service.get_macro_context()
    if data is None:
        raise HTTPException(status_code=503, detail="Macro regime data unavailable")
    return {"status": "success", "data": data}
