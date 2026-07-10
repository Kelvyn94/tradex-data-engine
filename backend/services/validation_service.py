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

    REQUIRED_COLUMNS = [
        "Open",
        "High",
        "Low",
        "Close"
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

        passed = True

        if not df.index.is_monotonic_increasing:
            passed = False

        if df.index.has_duplicates:
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

            if row["High"] < row["Low"]:
                bad += 1

            if row["High"] < row["Open"]:
                bad += 1

            if row["High"] < row["Close"]:
                bad += 1

            if row["Low"] > row["Open"]:
                bad += 1

            if row["Low"] > row["Close"]:
                bad += 1

        self.report["bad_ohlc_rows"] = bad

        return bad == 0

    #####################################################

    def validate_volume(
        self,
        df: pd.DataFrame
    ) -> bool:

        if "Volume" not in df.columns:

            self.report["volume"] = "Missing"

            return True

        negatives = int((df["Volume"] < 0).sum())

        self.report["negative_volume"] = negatives

        return negatives == 0

    #####################################################

    def calculate_quality_score(self) -> float:

        score = 100.0

        score -= self.report.get("duplicates", 0) * 0.10

        score -= self.report.get("missing_values", 0) * 0.05

        score -= self.report.get("bad_ohlc_rows", 0) * 0.50

        if not self.report.get("date_validation", True):
            score -= 5

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

        self.validate_columns(df)

        self.validate_duplicates(df)

        self.validate_missing(df)

        self.validate_dates(df)

        self.validate_ohlc(df)

        self.validate_volume(df)

        return self.validation_summary()