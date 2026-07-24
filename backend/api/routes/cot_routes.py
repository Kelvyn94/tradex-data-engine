"""
CFTC Commitment of Traders (COT) positioning routes.
"""

from fastapi import APIRouter, HTTPException

from backend.services.cot_service import cot_service

router = APIRouter(prefix="/api/v1/cot", tags=["cot"])


@router.get("/positioning")
async def get_positioning():
    """
    Commercial (hedgers) vs Non-Commercial (large speculators) vs
    Non-Reportable (small traders) positioning for Gold, Silver, EUR,
    and GBP futures, from CFTC's weekly Commitment of Traders report.
    """
    data = cot_service.get_positioning()
    if data is None:
        raise HTTPException(status_code=503, detail="COT positioning data unavailable")
    return {"status": "success", "data": data}
