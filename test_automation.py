
"""
Test Automation Service.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from backend.services.automation_service import AutomationService
import time

print("=" * 60)
print("🤖 STARTING AUTOMATION SERVICE")
print("=" * 60)

automation = AutomationService()
automation.start()

print("\n✅ Automation started!")
print("📊 Tasks running:")
print("  - Data updates (daily)")
print("  - Predictions (hourly)")
print("  - Model retraining (weekly)")
print("\n⏳ Press Ctrl+C to stop...")

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\n🛑 Stopping automation...")
    automation.stop()
    print("✅ Automation stopped")