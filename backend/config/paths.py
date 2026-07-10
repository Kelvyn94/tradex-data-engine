from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

DATA = ROOT / "data"

RAW = DATA / "raw"

CLEANED = DATA / "cleaned"

PROCESSED = DATA / "processed"

FEATURES = DATA / "features"

LABELS = DATA / "labels"

REPORTS = ROOT / "reports"

LOGS = ROOT / "logs"