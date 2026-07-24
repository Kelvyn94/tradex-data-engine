"""
CFTC Commitment of Traders (COT) service.

Institutional/commercial positioning data from CFTC's official public
reporting API (publicreporting.cftc.gov, Socrata-based) - free, no key
required. This is the "smart money" positioning layer: Commercial
(hedgers) vs Non-Commercial (large speculators) vs Non-Reportable
(small traders), for the assets this app tracks.

Verified empirically against the real API before building this:
- Market names are CFTC's own naming, not this app's symbols - and a
  plausible-looking name can be wrong: "BRITISH POUND STERLING -
  CHICAGO MERCANTILE EXCHANGE" is a stale, renamed entry whose last
  data is from 2022-02-01. The actually-current market is
  "BRITISH POUND - CHICAGO MERCANTILE EXCHANGE" (verified live-updating
  through the current week).
- Report cadence is weekly, snapshotted every Tuesday, published the
  following Friday - confirmed via 6 consecutive real report dates
  exactly 7 days apart. Publish timing/Socrata sync can lag the
  documented ~3:30pm ET Friday target, so this checks daily rather than
  trying to time a precise weekly cron.
- Verified the long-side and short-side position breakdowns both sum
  exactly to reported open interest for a real, current Gold report
  (Non-Commercial + Commercial + Non-Reportable, per CFTC's own
  documented Legacy report methodology) - not just "the API returned
  something that looks plausible."
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

CFTC_DATASET_URL = "https://publicreporting.cftc.gov/resource/6dca-aqww.json"

# CFTC's own market_and_exchange_names for the Legacy Futures Only
# report, confirmed live-updating (see module docstring) - these are
# the actual COMEX/CME contracts underlying this app's XAUUSD/XAGUSD/
# EURUSD/GBPUSD price data (GC=F, SI=F, EURUSD=X, GBPUSD=X via Yahoo),
# so positioning and price data are sourced consistently.
ASSET_MARKET_NAMES = {
    "XAUUSD": "GOLD - COMMODITY EXCHANGE INC.",
    "XAGUSD": "SILVER - COMMODITY EXCHANGE INC.",
    "EURUSD": "EURO FX - CHICAGO MERCANTILE EXCHANGE",
    "GBPUSD": "BRITISH POUND - CHICAGO MERCANTILE EXCHANGE",
}


class COTService:
    """Fetches and caches weekly CFTC COT positioning for tracked assets."""

    def __init__(self):
        self._cache: Dict[str, dict] = {}
        self._cache_time: Optional[datetime] = None
        # Real cadence is weekly (confirmed empirically) - a 24h cache is
        # generous, not aggressive, and avoids depending on precise
        # Friday-afternoon publish timing.
        self._cache_ttl = timedelta(hours=24)

    def _fetch_latest_for_market(self, market_name: str) -> Optional[dict]:
        try:
            resp = requests.get(
                CFTC_DATASET_URL,
                params={
                    "$where": f"market_and_exchange_names='{market_name}'",
                    "$order": "report_date_as_yyyy_mm_dd DESC",
                    "$limit": 1,
                },
                timeout=15,
            )
            resp.raise_for_status()
            rows = resp.json()
            if not rows:
                logger.warning(f"CFTC COT: no data returned for market '{market_name}'")
                return None
            return rows[0]
        except Exception as e:
            logger.error(f"CFTC COT fetch failed for '{market_name}': {e}")
            return None

    def get_positioning(self, force_refresh: bool = False) -> Optional[List[dict]]:
        """
        Returns positioning for every tracked asset, or None only if
        there is no data at all (no cache, and every live fetch failed).
        Per-asset failures fall back to that asset's last cached value
        (explicitly stale, still labeled with its real reportDate) rather
        than being dropped or replaced with a fabricated placeholder.
        """
        now = datetime.utcnow()
        if (
            not force_refresh
            and self._cache
            and self._cache_time
            and now - self._cache_time < self._cache_ttl
        ):
            return list(self._cache.values())

        results: Dict[str, dict] = {}
        for asset, market_name in ASSET_MARKET_NAMES.items():
            row = self._fetch_latest_for_market(market_name)
            if row is None:
                if asset in self._cache:
                    results[asset] = self._cache[asset]
                continue

            try:
                noncomm_long = int(row["noncomm_positions_long_all"])
                noncomm_short = int(row["noncomm_positions_short_all"])
                # CFTC's own field name has a typo ("postions", not
                # "positions") - matched exactly since it's their column
                # name, confirmed from the raw API response. This is the
                # Legacy report's only spread bucket - Commercial and
                # Non-Reportable traders have no separate spread category.
                # Included so the four numbers reconcile exactly to open
                # interest (verified), but deliberately excluded from
                # "net" below: a spread position is simultaneously long
                # and short in different contract months, so it has no
                # net directional bias - folding it into net would misstate
                # sentiment, and that's also the standard convention for
                # how COT "net positioning" is read.
                noncomm_spread = int(row["noncomm_postions_spread_all"])
                comm_long = int(row["comm_positions_long_all"])
                comm_short = int(row["comm_positions_short_all"])
                nonrept_long = int(row["nonrept_positions_long_all"])
                nonrept_short = int(row["nonrept_positions_short_all"])
                open_interest = int(row["open_interest_all"])
                report_date = row["report_date_as_yyyy_mm_dd"][:10]
            except (KeyError, ValueError) as e:
                logger.error(f"CFTC COT: unexpected row shape for {asset}: {e}")
                if asset in self._cache:
                    results[asset] = self._cache[asset]
                continue

            results[asset] = {
                "asset": asset,
                "marketName": market_name,
                "reportDate": report_date,
                "openInterest": open_interest,
                "commercial": {
                    "long": comm_long,
                    "short": comm_short,
                    "net": comm_long - comm_short,
                },
                "nonCommercial": {
                    "long": noncomm_long,
                    "short": noncomm_short,
                    "spread": noncomm_spread,
                    "net": noncomm_long - noncomm_short,
                },
                "nonReportable": {
                    "long": nonrept_long,
                    "short": nonrept_short,
                    "net": nonrept_long - nonrept_short,
                },
                "source": "CFTC",
            }

        if not results:
            logger.warning("CFTC COT: no positioning data available for any tracked asset")
            return None

        self._cache = results
        self._cache_time = now
        logger.info(f"CFTC COT positioning refreshed for {len(results)} assets")
        return list(results.values())


cot_service = COTService()
