"""
Data loading glue between db_service and BacktestEngine.

db_service.get_candles() returns candle data with 'timestamp' as a
regular column; BacktestEngine._build_unified_dataframe() reads
df['close'] off a DataFrame it expects to already be indexed by
timestamp. This bridges that gap - identified but not built in the
Batch 4 evaluation of the backtesting engine.
"""

from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd

from backend.services.database_service import db_service


def load_backtest_data(
    assets: List[str],
    timeframe: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    lookback: Optional[int] = None,
) -> Dict[str, pd.DataFrame]:
    """
    Fetch candles for each asset and index by timestamp - the shape
    BacktestEngine.run() expects.

    Args:
        assets: Asset symbols to fetch.
        timeframe: Candle timeframe (daily/4h/1h/30m/weekly).
        start_date/end_date: Explicit date range (ascending, unlimited).
        lookback: If given and start_date is None, fetch the most
            recent `lookback` candles instead of a date range (uses
            get_candles(limit=...), which correctly means "N periods"
            regardless of timeframe - see the CorrelationMatrix fix).

    Returns:
        {asset: DataFrame indexed by timestamp}. Assets with no data
        are simply omitted, not fabricated - callers must check which
        of the requested assets actually came back.
    """
    data: Dict[str, pd.DataFrame] = {}
    for asset in assets:
        if lookback and not start_date:
            df = db_service.get_candles(asset, timeframe, limit=lookback)
        else:
            df = db_service.get_candles(asset, timeframe, start_date, end_date)

        if df is not None and not df.empty:
            data[asset] = df.set_index("timestamp")

    return data
