import pandas as pd

from backend.services.validation_service import ValidationService

df = pd.read_csv(
    "data/raw/EURUSD/daily.csv",
    index_col=0,
    parse_dates=True
)

validator = ValidationService()

report = validator.validate(df)

print()

print("=" * 50)

print("VALIDATION REPORT")

print("=" * 50)

for key, value in report.items():
    print(f"{key:<25} {value}")

print("=" * 50)