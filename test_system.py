"""
Complete System Test.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from datetime import datetime, timedelta
from backend.config.settings import settings
from backend.services.database_service import db_service
from backend.ict import ICTService
from backend.correlation import CorrelationMatrix
from backend.backtesting.engine import BacktestEngine
from backend.strategies.simple_momentum import SimpleMomentumStrategy
from backend.ai.inference import InferenceEngine

print("=" * 60)
print("🚀 TRADEX SYSTEM TEST")
print("=" * 60)

# 1. Database
print("\n📊 1. Database Status:")
print("-" * 40)
try:
    with db_service.db_manager.get_session() as session:
        # Use raw SQL to count candles
        result = session.execute("SELECT COUNT(*) FROM data_engine.asset_candles")
        total = result.fetchone()[0]
        print(f"  Total Candles: {total:,}")
except Exception as e:
    print(f"  Error: {e}")

# 2. ICT Service
print("\n🧠 2. ICT Service:")
print("-" * 40)
ict = ICTService()
try:
    result = ict.analyze_asset('EURUSD')
    if 'signal' in result:
        print(f"  Signal: {result['signal'].get('action', 'N/A')}")
        print(f"  Confidence: {result['signal'].get('confidence', 0):.2f}")
except Exception as e:
    print(f"  Error: {e}")

# 3. Correlation
print("\n📈 3. Correlation:")
print("-" * 40)
corr = CorrelationMatrix()
try:
    result = corr.calculate()
    if result and 'correlation_matrix' in result:
        print(f"  Matrix calculated: {len(result['correlation_matrix'].columns)} assets")
except Exception as e:
    print(f"  Error: {e}")

# 4. Backtest
print("\n📊 4. Backtest:")
print("-" * 40)
try:
    # Get data
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    data = {}
    for asset in ['XAUUSD']:
        df = db_service.get_candles(asset, 'daily', start_date, end_date)
        if df is not None and not df.empty:
            df = df.set_index('timestamp')
            data[asset] = df
    
    if data:
        strategy = SimpleMomentumStrategy(asset='XAUUSD', lookback=20, entry_threshold=0.005)
        engine = BacktestEngine(initial_capital=100000)
        result = engine.run(strategy.generate_signals, data)
        print(f"  Trades: {result.get('total_trades', 0)}")
        print(f"  Return: {result.get('total_return', 0)*100:.2f}%")
    else:
        print("  No data for backtest")
except Exception as e:
    print(f"  Error: {e}")

# 5. AI Predictions
print("\n🤖 5. AI Predictions:")
print("-" * 40)
inference = InferenceEngine()
for asset in ['EURUSD', 'GBPUSD', 'XAUUSD']:
    result = inference.get_prediction(asset)
    if result.get('status') == 'SUCCESS':
        print(f"  {asset}: {result.get('direction')} ({result.get('confidence', 0):.2f})")
    elif result.get('status') == 'TRAINING_NEEDED':
        print(f"  {asset}: ⚠️ Training needed - run train_models.py first")
    else:
        print(f"  {asset}: {result.get('status', 'N/A')} - {result.get('error', '')}")

print("\n" + "=" * 60)
print("✅ SYSTEM TEST COMPLETE")
print("=" * 60)