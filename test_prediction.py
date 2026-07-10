"""
Test AI Predictions.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from backend.ai.inference import InferenceEngine
from backend.config.settings import settings

print("=" * 60)
print("🔮 AI PREDICTIONS")
print("=" * 60)

inference = InferenceEngine()

for asset in settings.ASSETS[:3]:  # Test first 3 assets
    print(f"\n📊 {asset}:")
    print("-" * 40)
    
    result = inference.get_prediction(asset)
    
    if result.get('status') == 'SUCCESS':
        print(f"  Direction: {result.get('direction')}")
        print(f"  Confidence: {result.get('confidence', 0):.2%}")
    else:
        print(f"  Status: {result.get('status', 'UNKNOWN')}")
        if 'error' in result:
            print(f"  Error: {result['error']}")

print("\n" + "=" * 60)
print("✅ PREDICTIONS COMPLETE")
print("=" * 60)