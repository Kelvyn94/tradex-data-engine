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
from datetime import datetime, timedelta
from typing import Dict, Optional

import yfinance as yf

logger = logging.getLogger(__name__)

MACRO_SERIES = {
    "DXY": {"ticker": "DX-Y.NYB", "label": "US Dollar Index"},
    "US10Y": {"ticker": "^TNX", "label": "10-Year Treasury Yield"},
    "VIX": {"ticker": "^VIX", "label": "CBOE Volatility Index"},
}


class MacroRegimeService:
    """Fetches and caches DXY/10Y yield/VIX snapshots."""

    def __init__(self):
        self._cache: Optional[Dict] = None
        self._cache_time: Optional[datetime] = None
        self._cache_ttl = timedelta(minutes=30)

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
        prior_series = (self._cache or {}).get("series", {})

        for key, meta in MACRO_SERIES.items():
            try:
                data = yf.Ticker(meta["ticker"]).history(period="5d")
                if data.empty or len(data) < 2:
                    logger.warning(f"Macro: no/insufficient data for {meta['ticker']}")
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
            except Exception as e:
                logger.error(f"Macro fetch failed for {meta['ticker']}: {e}")
                if key in prior_series:
                    results[key] = prior_series[key]

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
        self._cache = payload
        self._cache_time = now
        logger.info(f"Macro regime refreshed: {list(results.keys())}, regime={risk_regime}")
        return payload


macro_regime_service = MacroRegimeService()
