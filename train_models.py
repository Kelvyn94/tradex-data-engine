"""
Train AI Models for All Assets.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from backend.ai.training import ModelTrainer
from backend.ai.feature_engineering import FeatureEngineer
from backend.ai.labeling import LabelGenerator
from backend.config.settings import settings

print("=" * 60)
print("🤖 TRAINING AI MODELS")
print("=" * 60)

trainer = ModelTrainer()
fe = FeatureEngineer()
lg = LabelGenerator()

results = {}

for asset in settings.ASSETS:
    print(f"\n📊 Training model for {asset}...")
    print("-" * 40)
    
    try:
        # Generate features
        features = fe.generate_features(asset, lookback=500)
        if features.empty:
            print(f"  ❌ No features for {asset}")
            continue
        
        # Generate labels
        labels = lg.generate_labels(features, horizon=5, method='direction')
        if labels.empty:
            print(f"  ❌ No labels for {asset}")
            continue
        
        # Train model
        result = trainer.train(asset, features, labels)
        
        if 'error' in result:
            print(f"  ❌ Error: {result['error']}")
        else:
            print(f"  ✅ Accuracy: {result.get('accuracy', 0):.4f}")
            print(f"  📊 Samples: {result.get('samples', 0)}")
            results[asset] = result
            
    except Exception as e:
        print(f"  ❌ Error: {e}")

print("\n" + "=" * 60)
print("✅ TRAINING COMPLETE")
print("=" * 60)

if results:
    print(f"\n📊 Summary:")
    for asset, result in results.items():
        print(f"  {asset}: {result.get('accuracy', 0):.4f} ({result.get('samples', 0)} samples)")