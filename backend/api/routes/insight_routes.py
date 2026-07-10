"""
Insight API routes for TradeX Data Engine.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from datetime import datetime

from backend.services.database_service import db_service
from backend.services.ai_insight_service import AIInsightService

router = APIRouter(prefix="/api/v1/insights", tags=["insights"])

@router.get("/latest")
async def get_latest_insights(
    asset: Optional[str] = None,
    limit: int = 10
):
    """
    Get latest AI insights.
    """
    try:
        insights = db_service.get_latest_insights(asset, limit)
        
        return {
            "status": "success",
            "count": len(insights),
            "data": insights
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/generate")
async def generate_insights(
    asset: Optional[str] = None
):
    """
    Manually generate AI insights.
    """
    try:
        ai_service = AIInsightService()
        insights = ai_service.generate_insights(asset)
        
        # Store in database
        stored_count = 0
        for insight in insights:
            db_service.store_insight(insight)
            stored_count += 1
        
        return {
            "status": "success",
            "message": f"Generated {stored_count} insights",
            "count": stored_count,
            "data": insights
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/signals/latest")
async def get_latest_signals(
    asset: Optional[str] = None,
    limit: int = 10
):
    """
    Get latest trading signals.
    """
    try:
        signals = db_service.get_latest_signals(asset, limit)
        
        return {
            "status": "success",
            "count": len(signals),
            "data": signals
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/summary")
async def get_insight_summary():
    """
    Get summary of all insights.
    """
    try:
        insights = db_service.get_latest_insights(limit=50)
        
        # Summarize by type
        summary = {}
        for insight in insights:
            insight_type = insight['insight_type']
            if insight_type not in summary:
                summary[insight_type] = 0
            summary[insight_type] += 1
        
        return {
            "status": "success",
            "summary": summary,
            "total": len(insights)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))