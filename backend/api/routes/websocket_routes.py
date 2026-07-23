"""
WebSocket routes for real-time data.
"""

from fastapi import WebSocket, WebSocketDisconnect, APIRouter
from typing import Dict, Set, List
import json
import asyncio
import logging
from datetime import datetime

from backend.services.database_service import db_service
from backend.services.ai_insight_service import AIInsightService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])

class ConnectionManager:
    """Manages WebSocket connections."""
    
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self.connection_details: Dict[WebSocket, Dict] = {}
    
    async def connect(self, websocket: WebSocket, asset: str = None):
        """Connect a websocket."""
        await websocket.accept()
        
        if asset not in self.active_connections:
            self.active_connections[asset] = set()
        self.active_connections[asset].add(websocket)
        
        self.connection_details[websocket] = {
            'asset': asset,
            'connected_at': datetime.now()
        }
        
        logger.info(f"WebSocket connected: {asset}")
    
    async def disconnect(self, websocket: WebSocket):
        """Disconnect a websocket."""
        details = self.connection_details.get(websocket, {})
        asset = details.get('asset')
        
        if asset and asset in self.active_connections:
            self.active_connections[asset].discard(websocket)
            if not self.active_connections[asset]:
                del self.active_connections[asset]
        
        self.connection_details.pop(websocket, None)
        logger.info(f"WebSocket disconnected: {asset}")
    
    async def broadcast(self, message: Dict, asset: str = None):
        """Broadcast a message to connected clients."""
        if asset and asset in self.active_connections:
            for connection in self.active_connections[asset]:
                try:
                    await connection.send_json(message)
                except:
                    pass
        
        # Also broadcast to general channel if specified
        if asset is None and "general" in self.active_connections:
            for connection in self.active_connections["general"]:
                try:
                    await connection.send_json(message)
                except:
                    pass
    
    async def send_to_asset(self, asset: str, message: Dict):
        """Send message to a specific asset's subscribers."""
        if asset in self.active_connections:
            for connection in self.active_connections[asset]:
                try:
                    await connection.send_json(message)
                except:
                    pass

manager = ConnectionManager()

@router.websocket("/ws/{asset}")
async def websocket_endpoint(websocket: WebSocket, asset: str):
    """WebSocket endpoint for real-time data."""
    await manager.connect(websocket, asset)
    
    try:
        # Send initial data
        latest = db_service.get_latest_candle(asset, 'daily')
        if latest:
            await websocket.send_json({
                "type": "initial_data",
                "asset": asset,
                "timestamp": datetime.now().isoformat(),
                "price": latest["close"],
                "data": {
                    "open": latest["open"],
                    "high": latest["high"],
                    "low": latest["low"],
                    "close": latest["close"],
                    "volume": latest["volume"]
                }
            })
        
        # Keep connection alive and listen for messages
        while True:
            # Receive messages from client
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                
                # Handle different message types
                if message.get('type') == 'ping':
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": datetime.now().isoformat()
                    })
                elif message.get('type') == 'get_insights':
                    # Send latest insights
                    insights = db_service.get_latest_insights(asset, limit=5)
                    await websocket.send_json({
                        "type": "insights",
                        "asset": asset,
                        "data": insights
                    })
                elif message.get('type') == 'subscribe_signals':
                    # Subscribe to signal updates
                    await websocket.send_json({
                        "type": "subscribed",
                        "topic": "signals",
                        "asset": asset
                    })
                    
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON"
                })
            
            # Small delay to prevent CPU spinning
            await asyncio.sleep(0.1)
            
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await manager.disconnect(websocket)

@router.websocket("/ws/insights")
async def insights_websocket(websocket: WebSocket):
    """WebSocket endpoint for insights updates."""
    await manager.connect(websocket, "general")
    
    try:
        while True:
            # Send periodic updates
            insights = db_service.get_latest_insights(limit=5)
            await websocket.send_json({
                "type": "insights_update",
                "timestamp": datetime.now().isoformat(),
                "data": insights
            })
            
            await asyncio.sleep(30)  # Update every 30 seconds
            
    except WebSocketDisconnect:
        await manager.disconnect(websocket)