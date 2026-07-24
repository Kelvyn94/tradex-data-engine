"""
Macro regime service: US Dollar Index (DXY), 10-Year Treasury Yield,
and VIX - via the existing yfinance dependency already used by
YahooProvider. No new provider or signup.

Named MacroRegimeService (not MacroService) deliberately - a
MacroService already exists in this file's sibling
(backend/services/macro_service.py), wired to the real
POST /api/v1/insights/generate route via ai_insight_service.py, using
FRED for a different set of indicators (FEDFUNDS, UNRATE, DGS10). This
is a separate, Yahoo-based snapshot service for DXY/yield/VIX
specifically, not a replacement or extension of that one.

Verified live before building this (don't assume other Yahoo tickers
working means these do too):
- DX-Y.NYB (US Dollar Index): confirmed real data.
- ^TNX (10-Year Treasury Yield): confirmed this returns the DIRECT
  yield percentage (e.g. 4.70 = 4.70%) against the actual current
  value, not assumed from the ticker's historical CBOE x10-index
  naming convention.
- ^VIX (CBOE Volatility Index): confirmed real data.

This is a lightweight snapshot service (latest value + change), not
routed through YahooProvider/DownloadService/the candles DB table -
these series don't need historical OHLCV storage for a simple macro-
context display, so the heavier download pipeline is deliberately not
used here.
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

import yfinance as yf

logger = logging.getLogger(__name__)

MACRO_SERIES = {
    "DXY": {"ticker": "DX-Y.NYB", "label": "US Dollar Index"},
    "US10Y": {"ticker": "^TNX", "label": "10-Year Treasury Yield"},
    "VIX": {"ticker": "^VIX", "label": "CBOE Volatility Index"},
}

# Diagnosed in production (see _fetchErrors): DXY intermittently fails
# with yfinance's YFRateLimitError from Render's IP while the other two
# series succeed in the same run. Retrying with backoff is the correct
# fix for genuine rate-limiting (as opposed to a permanent block, which
# would fail identically on every retry too).
MAX_FETCH_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = (2, 5)


class MacroRegimeService:
    """Fetches and caches DXY/10Y yield/VIX snapshots."""

    def __init__(self):
        self._cache: Optional[Dict] = None
        self._cache_time: Optional[datetime] = None
        self._cache_ttl = timedelta(minutes=30)

    def _fetch_one(self, ticker: str) -> Tuple[Optional[dict], Optional[str]]:
        """
        Fetches a single ticker's 5d history, retrying with backoff since
        the diagnosed failure mode (YFRateLimitError from Render's IP) is
        transient. Returns (raw_data_dict, error_message); error_message
        is set only if every attempt failed.
        """
        last_error: Optional[str] = None
        for attempt in range(1, MAX_FETCH_ATTEMPTS + 1):
            try:
                data = yf.Ticker(ticker).history(period="5d")
                if data.empty or len(data) < 2:
                    last_error = f"empty/insufficient history ({len(data)} rows)"
                else:
                    return data, None
            except Exception as e:
                last_error = f"{type(e).__name__}: {e}"

            if attempt < MAX_FETCH_ATTEMPTS:
                logger.warning(
                    f"Macro fetch attempt {attempt}/{MAX_FETCH_ATTEMPTS} failed for "
                    f"{ticker}: {last_error} - retrying in {RETRY_BACKOFF_SECONDS[attempt - 1]}s"
                )
                time.sleep(RETRY_BACKOFF_SECONDS[attempt - 1])

        return None, last_error

    def get_macro_context(self, force_refresh: bool = False) -> Optional[Dict]:
        """
        Returns {"series": {...}, "riskRegime": "..."} or None only if
        every tracked series has neither fresh data nor a prior cache.
        Per-series failures fall back to that series' last cached value
        (explicitly stale, not fabricated) rather than being dropped.
        """
        now = datetime.utcnow()
        if (
            not force_refresh
            and self._cache
            and self._cache_time
            and now - self._cache_time < self._cache_ttl
        ):
            return self._cache

        results: Dict[str, dict] = {}
        # TEMPORARY DIAGNOSTIC (see D:\Development\Data Engine handoff notes):
        # DXY is silently missing from the live Render deployment while
        # US10Y/VIX succeed and DXY works locally. No access to Render's
        # server logs, so capture the real exception here and surface it
        # in the API response until the actual cause is identified, then
        # remove/quiet this.
        errors: Dict[str, str] = {}
        prior_series = (self._cache or {}).get("series", {})

        for key, meta in MACRO_SERIES.items():
            data, error = self._fetch_one(meta["ticker"])
            if data is None:
                logger.error(
                    f"Macro fetch exhausted {MAX_FETCH_ATTEMPTS} attempts for {meta['ticker']}: {error}"
                )
                errors[key] = error or "unknown error"
                if key in prior_series:
                    results[key] = prior_series[key]
                continue

            latest = float(data["Close"].iloc[-1])
            previous = float(data["Close"].iloc[-2])
            change = latest - previous
            change_pct = (change / previous * 100) if previous else 0.0

            results[key] = {
                "label": meta["label"],
                "ticker": meta["ticker"],
                "value": latest,
                "change": change,
                "changePercent": change_pct,
                "direction": "up" if change > 0 else "down" if change < 0 else "flat",
                "asOf": data.index[-1].isoformat(),
            }

        if not results:
            logger.warning("Macro: no data available for any tracked series")
            return None

        # Risk regime from VIX level - standard convention: <20 calm/
        # risk-on, 20-25 elevated, >=25 risk-off/fear.
        risk_regime = None
        if "VIX" in results:
            vix_val = results["VIX"]["value"]
            if vix_val < 20:
                risk_regime = "RISK_ON"
            elif vix_val < 25:
                risk_regime = "ELEVATED"
            else:
                risk_regime = "RISK_OFF"

        payload = {"series": results, "riskRegime": risk_regime}
        if errors:
            # TEMPORARY DIAGNOSTIC field - remove once DXY root cause is fixed.
            payload["_fetchErrors"] = errors
        self._cache = payload
        self._cache_time = now
        logger.info(f"Macro regime refreshed: {list(results.keys())}, regime={risk_regime}")
        return payload


macro_regime_service = MacroRegimeService()
