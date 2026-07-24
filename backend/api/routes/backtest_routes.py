"""
Backtest execution routes.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.backtesting.data_loader import load_backtest_data
from backend.backtesting.engine import BacktestEngine
from backend.strategies.simple_momentum import SimpleMomentumStrategy
from backend.strategies.ict_aggressive import ICTAggressiveStrategy
from backend.strategies.ict_correlation_combined import ICTCorrelationCombined
from backend.strategies.pairs_trading_v2 import PairsTradingStrategyV2

router = APIRouter(prefix="/api/v1/backtest", tags=["backtest"])

# Only the four strategies fixed/verified in earlier batches. No new
# strategies added here - out of scope for this batch.
STRATEGY_REGISTRY = {
    "simple_momentum": SimpleMomentumStrategy,
    "ict_aggressive": ICTAggressiveStrategy,
    "ict_correlation_combined": ICTCorrelationCombined,
    "pairs_trading_v2": PairsTradingStrategyV2,
}


class BacktestRequest(BaseModel):
    strategy: str
    assets: List[str]
    timeframe: str = "daily"
    start_date: Optional[str] = None  # ISO date, e.g. "2023-01-01"
    end_date: Optional[str] = None
    lookback: Optional[int] = None  # alternative to start_date: most-recent-N candles
    strategy_params: Dict[str, Any] = {}
    initial_capital: float = 100000
    commission: float = 0.001
    slippage: float = 0.001


def _serialize_trades(trades: List[Dict]) -> List[Dict]:
    """Trade entry_time/exit_time are pandas Timestamps (from the
    DatetimeIndex the data loader builds) - not JSON-serializable as-is."""
    out = []
    for t in trades:
        t = dict(t)
        for key in ("entry_time", "exit_time"):
            if key in t and t[key] is not None:
                t[key] = t[key].isoformat()
        out.append(t)
    return out


@router.get("/strategies")
async def list_strategies():
    """Available strategy names for POST /run."""
    return {"status": "success", "data": list(STRATEGY_REGISTRY.keys())}


@router.post("/run")
async def run_backtest(request: BacktestRequest):
    if request.strategy not in STRATEGY_REGISTRY:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown strategy '{request.strategy}'. Available: {list(STRATEGY_REGISTRY.keys())}",
        )
    if not request.assets:
        raise HTTPException(status_code=400, detail="At least one asset is required")
    if not request.start_date and not request.lookback:
        raise HTTPException(
            status_code=400, detail="Provide either start_date (with optional end_date) or lookback"
        )

    try:
        start_date = datetime.fromisoformat(request.start_date) if request.start_date else None
        end_date = datetime.fromisoformat(request.end_date) if request.end_date else None
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date: {e}")

    data = load_backtest_data(request.assets, request.timeframe, start_date, end_date, request.lookback)

    missing = [a for a in request.assets if a not in data]
    if missing:
        raise HTTPException(
            status_code=503,
            detail=f"No data available for: {missing}. A backtest cannot run on partial/missing data.",
        )

    strategy_class = STRATEGY_REGISTRY[request.strategy]
    try:
        strategy = strategy_class(**request.strategy_params)
    except TypeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid strategy_params for '{request.strategy}': {e}")

    engine = BacktestEngine(
        initial_capital=request.initial_capital,
        commission=request.commission,
        slippage=request.slippage,
    )
    result = engine.run(strategy.generate_signals, data)

    if "error" in result:
        raise HTTPException(status_code=422, detail=result["error"])

    result["trades"] = _serialize_trades(result.get("trades", []))
    result["assets_used"] = list(data.keys())

    return {"status": "success", "data": result}
