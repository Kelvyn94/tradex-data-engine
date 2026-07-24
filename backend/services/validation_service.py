"""
validation_service.py

Validates downloaded market data before cleaning
or storing it.

TradeX Data Engine
"""

from __future__ import annotations

import pandas as pd
from typing import Dict, Any


class ValidationService:

    # The pipeline's DataFrames use lowercase columns throughout (see
    # YahooProvider._clean_dataframe: 'timestamp', 'open', 'high', 'low',
    # 'close', 'volume') - this validator originally checked capitalized
    # names that never matched, so validate_columns() always reported every
    # column missing had it ever actually been called against real pipeline
    # data.
    REQUIRED_COLUMNS = [
        "open",
        "high",
        "low",
        "close"
    ]

    def __init__(self):

        self.report = {}

    #####################################################

    def validate_columns(
        self,
        df: pd.DataFrame
    ) -> bool:

        missing = []

        for col in self.REQUIRED_COLUMNS:

            if col not in df.columns:
                missing.append(col)

        self.report["missing_columns"] = missing

        return len(missing) == 0

    #####################################################

    def validate_duplicates(
        self,
        df: pd.DataFrame
    ) -> bool:

        duplicates = int(df.duplicated().sum())

        self.report["duplicates"] = duplicates

        return duplicates == 0

    #####################################################

    def validate_missing(
        self,
        df: pd.DataFrame
    ) -> bool:

        missing = int(df.isna().sum().sum())

        self.report["missing_values"] = missing

        return missing == 0

    #####################################################

    def validate_dates(
        self,
        df: pd.DataFrame
    ) -> bool:
        # Pipeline DataFrames carry timestamps in a 'timestamp' column, not
        # as the DataFrame index (df.reset_index() in _clean_dataframe puts
        # a plain 0..n RangeIndex in place) - checking df.index here always
        # passed regardless of the actual data, since a RangeIndex is
        # trivially monotonic and never has duplicates.
        passed = True

        if "timestamp" not in df.columns:
            self.report["date_validation"] = False
            return False

        timestamps = df["timestamp"]

        if not timestamps.is_monotonic_increasing:
            passed = False

        if timestamps.duplicated().any():
            passed = False

        self.report["date_validation"] = passed

        return passed

    #####################################################

    def validate_ohlc(
        self,
        df: pd.DataFrame
    ) -> bool:

        bad = 0

        for _, row in df.iterrows():

            if row["high"] < row["low"]:
                bad += 1

            if row["high"] < row["open"]:
                bad += 1

            if row["high"] < row["close"]:
                bad += 1

            if row["low"] > row["open"]:
                bad += 1

            if row["low"] > row["close"]:
                bad += 1

        self.report["bad_ohlc_rows"] = bad

        return bad == 0

    #####################################################

    def validate_volume(
        self,
        df: pd.DataFrame
    ) -> bool:

        if "volume" not in df.columns:

            self.report["volume"] = "Missing"

            return True

        negatives = int((df["volume"] < 0).sum())

        self.report["negative_volume"] = negatives

        return negatives == 0

    #####################################################

    def calculate_quality_score(self) -> float:
        # Weighted by the FRACTION of rows affected, not a flat per-row
        # deduction. A flat deduction is negligible on any dataset above a
        # handful of rows - e.g. 4 physically-impossible OHLC rows out of
        # 12 (a third of the data) only cost 2.0 points at the old
        # -0.50/row weight, nowhere near enough to fail a 90-point
        # threshold. Bad OHLC in particular is a severe integrity
        # violation (the data describes a candle that cannot exist) and is
        # weighted accordingly.
        score = 100.0
        total_rows = max(self.report.get("total_rows", 0), 1)

        dup_fraction = self.report.get("duplicates", 0) / total_rows
        bad_ohlc_fraction = self.report.get("bad_ohlc_rows", 0) / total_rows
        missing_fraction = self.report.get("missing_values", 0) / total_rows

        score -= dup_fraction * 50
        score -= bad_ohlc_fraction * 100
        score -= missing_fraction * 20

        if not self.report.get("date_validation", True):
            score -= 10

        if score < 0:
            score = 0

        return round(score, 2)

    #####################################################

    def validation_summary(
        self
    ) -> Dict[str, Any]:

        self.report["quality_score"] = self.calculate_quality_score()

        self.report["status"] = (
            "PASS"
            if self.report["quality_score"] >= 90
            else "FAIL"
        )

        return self.report

    #####################################################

    def validate(
        self,
        df: pd.DataFrame
    ) -> Dict[str, Any]:

        self.report = {}
        self.report["total_rows"] = len(df)

        self.validate_columns(df)

        self.validate_duplicates(df)

        self.validate_missing(df)

        self.validate_dates(df)

        self.validate_ohlc(df)

        self.validate_volume(df)

        return self.validation_summary()