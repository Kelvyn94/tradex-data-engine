"""
FastAPI application for TradeX Data Engine.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
from datetime import datetime

from backend.api.routes import data_routes, insight_routes, websocket_routes
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
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routers
    app.include_router(data_routes.router)
    app.include_router(insight_routes.router)
    app.include_router(websocket_routes.router)
    
    @app.get("/")
    async def root():
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
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat()
        }
    
    @app.on_event("startup")
    async def startup_event():
        logger.info("🚀 TradeX Data Engine starting...")
        logger.info("✅ TradeX Data Engine ready!")
    
    @app.on_event("shutdown")
    async def shutdown_event():
        logger.info("🛑 TradeX Data Engine shutting down...")
    
    return app

# Create app instance
app = create_app()
