"""
FastAPI application for TradeX Data Engine.
"""

from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from backend.api.routes import data_routes, insight_routes, websocket_routes
from backend.services.scheduler_service import scheduler
from backend.config.settings import settings

logger = logging.getLogger(__name__)

def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    
    app = FastAPI(
        title="TradeX Data Engine API",
        description="Institutional-grade market data and insights API",
        version="1.0.0"
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure properly for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routers
    app.include_router(data_routes.router)
    app.include_router(insight_routes.router)
    
    # Include WebSocket routes
    app.include_router(websocket_routes.router)
    
    @app.on_event("startup")
    async def startup_event():
        """Startup tasks."""
        logger.info("🚀 TradeX Data Engine starting...")
        
        # Start scheduler
        if settings.SCHEDULER_ENABLED:
            scheduler.start()
            logger.info("✅ Scheduler started")
        
        # Generate initial insights
        if settings.AI_ENABLED:
            from backend.services.ai_insight_service import AIInsightService
            ai_service = AIInsightService()
            insights = ai_service.generate_insights()
            logger.info(f"✅ Generated {len(insights)} initial insights")
        
        logger.info("✅ TradeX Data Engine ready!")
    
    @app.on_event("shutdown")
    async def shutdown_event():
        """Shutdown tasks."""
        logger.info("🛑 TradeX Data Engine shutting down...")
        if scheduler.is_running:
            scheduler.stop()
            logger.info("✅ Scheduler stopped")
        logger.info("🛑 TradeX Data Engine shutdown complete")
    
    @app.get("/")
    async def root():
        """Root endpoint."""
        return {
            "name": "TradeX Data Engine",
            "version": "1.0.0",
            "status": "running",
            "endpoints": {
                "docs": "/docs",
                "redoc": "/redoc",
                "api_v1": "/api/v1"
            }
        }
    
    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "scheduler_running": scheduler.is_running,
            "market_open": scheduler.is_market_open() if scheduler.is_running else False
        }
    
    return app

# Create app instance
app = create_app()