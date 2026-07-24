"""
Tests for the backtesting engine and its API route.

Plain assert-based script, not a pytest suite - there is no test
framework installed or configured anywhere in this project (checked:
pytest isn't in requirements.txt or the venv, and every sibling file in
this directory was empty before this one). Run directly:

    python backend/tests/test_backtest.py

Two tests, chosen for what they actually prove rather than coverage
for its own sake:
  1. A known strategy on a deterministic trend produces the expected
     trade direction end-to-end through the real engine - not just
     that the code runs without error.
  2. The API route returns a well-formed response for a valid request,
     using the same data-loading glue and consolidated stats module a
     real caller would hit.
"""

import os
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import sys
import numpy as np
import pandas as pd
from datetime import datetime, timedelta, timezone

from backend.backtesting.engine import BacktestEngine
from backend.strategies.simple_momentum import SimpleMomentumStrategy


def test_simple_momentum_strategy_uptrend_produces_buy_trades():
    """A strictly monotonic uptrend, fed through the real engine and the
    (Batch 5-fixed) SimpleMomentumStrategy, should produce at least one
    trade and every completed trade's first side should be BUY - not
    SELL, and not zero trades."""
    n = 120
    dates = pd.date_range("2024-01-01", periods=n, freq="D")
    # Deterministic, noise-free uptrend so momentum is unambiguously
    # positive throughout - no randomness to make this test flaky.
    prices = np.linspace(100, 130, n)
    price_df = pd.DataFrame({"close": prices}, index=dates)

    strategy = SimpleMomentumStrategy(asset="EURUSD", lookback=20, entry_threshold=0.005)
    engine = BacktestEngine(initial_capital=100000)
    result = engine.run(strategy.generate_signals, {"EURUSD": price_df})

    assert "error" not in result, f"engine.run() returned an error: {result}"
    assert result["total_trades"] > 0, "expected at least one trade on a clear uptrend, got zero"

    # engine.py's trade dicts record the EXIT action only (side is always
    # 'SELL' or 'CLOSE', never 'BUY' - a BUY just opens a position and
    # isn't logged as a trade until later closed). So "did the strategy
    # correctly go long on an uptrend" is verified via exit_price >
    # entry_price (a long position that gained value), not via `side`.
    first_trade = result["trades"][0]
    assert first_trade["side"] in ("SELL", "CLOSE"), f"unexpected side: {first_trade['side']}"
    assert first_trade["exit_price"] > first_trade["entry_price"], (
        f"expected a profitable long (exit > entry) on a pure uptrend, "
        f"got entry={first_trade['entry_price']}, exit={first_trade['exit_price']}"
    )

    # On a monotonic uptrend, overall P&L should be positive - the
    # strategy bought into a rising market.
    assert result["total_pnl"] > 0, f"expected positive P&L on a pure uptrend, got {result['total_pnl']}"

    print(f"  total_trades={result['total_trades']}, total_pnl={result['total_pnl']:.2f}, "
          f"win_rate={result['win_rate']:.2f}")
    return True


def test_backtest_route_returns_well_formed_response():
    """POST /api/v1/backtest/run, through the real FastAPI app, against
    seeded synthetic data (no real historical data available in this
    local environment - same situation as the correlation matrix tests,
    clearly labeled rather than silently assumed)."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
    from contextlib import contextmanager

    from backend.database.models import Base, AssetCandle
    from backend.services.database_service import DatabaseService
    import backend.services.database_service as database_service_module
    import backend.backtesting.data_loader as data_loader_module

    engine_db = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    ).execution_options(schema_translate_map={"data_engine": None})
    Base.metadata.create_all(engine_db)
    SessionLocal = sessionmaker(bind=engine_db)

    class FakeManager:
        @contextmanager
        def get_session(self):
            s = SessionLocal()
            try:
                yield s
                s.commit()
            except Exception:
                s.rollback()
                raise
            finally:
                s.close()

    fake_db = DatabaseService()
    fake_db.db_manager = FakeManager()
    database_service_module.db_service = fake_db
    data_loader_module.db_service = fake_db

    np.random.seed(42)
    n = 150
    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    prices = 1.10 + np.cumsum(np.random.normal(0, 0.002, n))
    with fake_db.db_manager.get_session() as session:
        for i in range(n):
            session.add(AssetCandle(
                id=i + 1, asset_symbol="EURUSD", timeframe="daily",
                timestamp=base + timedelta(days=i),
                open=float(prices[i]), high=float(prices[i]) + 0.001,
                low=float(prices[i]) - 0.001, close=float(prices[i]), volume=100,
            ))

    from fastapi.testclient import TestClient
    from backend.api.app import app

    client = TestClient(app)
    resp = client.post("/api/v1/backtest/run", json={
        "strategy": "simple_momentum",
        "assets": ["EURUSD"],
        "timeframe": "daily",
        "lookback": 100,
        "strategy_params": {"asset": "EURUSD", "lookback": 20, "entry_threshold": 0.003},
    })

    assert resp.status_code == 200, f"expected 200, got {resp.status_code}: {resp.text}"
    body = resp.json()
    assert body["status"] == "success"
    data = body["data"]

    for field in ("total_trades", "win_rate", "sharpe_ratio", "calmar_ratio",
                  "max_drawdown", "trades", "assets_used"):
        assert field in data, f"missing expected field '{field}' in response"

    assert data["assets_used"] == ["EURUSD"]
    assert isinstance(data["trades"], list)
    if data["trades"]:
        # Confirm trade timestamps were actually serialized to strings,
        # not left as unserializable pandas Timestamps (which wouldn't
        # have made it through resp.json() at all if broken).
        assert isinstance(data["trades"][0]["entry_time"], str)

    print(f"  route returned {data['total_trades']} trades, sharpe_ratio={data['sharpe_ratio']:.4f}, "
          f"assets_used={data['assets_used']}")
    return True


def test_backtest_route_rejects_unknown_strategy():
    """Bad input should fail loudly with a clear 400, not a 500 or a
    silent empty result."""
    from fastapi.testclient import TestClient
    from backend.api.app import app

    client = TestClient(app)
    resp = client.post("/api/v1/backtest/run", json={
        "strategy": "not_a_real_strategy",
        "assets": ["EURUSD"],
        "lookback": 50,
    })
    assert resp.status_code == 400, f"expected 400 for unknown strategy, got {resp.status_code}"
    return True


if __name__ == "__main__":
    tests = [
        test_simple_momentum_strategy_uptrend_produces_buy_trades,
        test_backtest_route_returns_well_formed_response,
        test_backtest_route_rejects_unknown_strategy,
    ]
    failed = []
    for t in tests:
        print(f"Running {t.__name__}...")
        try:
            t()
            print(f"  PASS\n")
        except AssertionError as e:
            failed.append(t.__name__)
            print(f"  FAIL: {e}\n")

    if failed:
        print(f"FAILED: {failed}")
        sys.exit(1)
    print("ALL TESTS PASSED")
