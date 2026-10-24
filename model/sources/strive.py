"""Strive's public treasury dashboard (strive.com/treasury). The endpoints are undocumented, so every pull is cached and
the last good copy is used when a call fails.

| Endpoint | What the model takes |
|---|---|
| /treasury/api/dashboard/calculated?stockSymbol=ASST | daily rows: BTC held, BTC + ASST price, assumed FD shares, SATA notional, cash, securities, debt, Strive's own evMnav; the SATA series (shares, rate) |
| /treasury/api/dashboard/base-data | weekly share-count history (Class A/B, traditional warrants), cash history, the BTC purchase ledger |
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone

import httpx

from model.sources import cache

log = logging.getLogger(__name__)
BASE = "https://strive.com"
UA = {"User-Agent": "Mozilla/5.0 (compatible; StriveModel/1.0)", "Accept": "application/json"}


def _pull(name: str, path: str, params: dict | None, offline: bool, shape=lambda d: d) -> tuple[dict | None, str]:
    """(payload, provenance): live from strive.com, else the cached copy."""
    if not offline:
        try:
            r = httpx.get(BASE + path, params=params, headers=UA, timeout=30)
            r.raise_for_status()
            data = shape(r.json())
            try:
                cache.save(name, data)
            except OSError as e:
                log.warning("Could not save %s cache: %s", name, e)
            return data, f"strive.com (live; checked {datetime.now(timezone.utc):%Y-%m-%d %H:%M UTC})"
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as e:  # network, bad JSON, or a changed shape
            log.warning("strive.com %s failed, using the cached copy: %s", path, e)
    data, label = cache.load(name)
    return data, (f"strive.com ({label})" if data is not None else "unavailable")


def _trim_calculated(d: dict) -> dict:
    # The endpoint returns every day since May 2025 (~1.5 MB) whatever the date range; keep what the model reads.
    data = d["data"]
    rows = data["btcHoldings"]
    if not isinstance(rows, list) or not all(isinstance(r, dict) and r.get("date") for r in rows) or not any(
        r.get("date") and r.get("sharePrice") and r.get("btcPrice") and r.get("btcHoldings")
        for r in rows
    ):
        raise ValueError("no usable priced dashboard rows")
    # Do not rely on an undocumented API's ordering or replace a working cache
    # with an empty but successful HTTP response.
    rows = sorted(rows, key=lambda r: r["date"])
    return {"rows": rows[-30:], "preferredStocks": d.get("preferredStocks") or [],
            "stockVolume": data.get("stockVolume") or {}}


def _base_data(d: dict) -> dict:
    data = d["data"]
    if not isinstance(data, dict) or not isinstance(data.get("shares"), list) or not data["shares"]:
        raise ValueError("no usable company share history")
    return data


def calculated(offline: bool = False, today: date | None = None) -> tuple[dict | None, str]:
    """Latest daily rows (with Strive's own mNAV) and the SATA series."""
    to = today or date.today()
    params = {"fromDate": (to - timedelta(days=10)).isoformat(), "toDate": to.isoformat(), "currency": "USD",
              "stockSymbol": "ASST"}  # without stockSymbol the rows come back with no ASST price or evMnav
    return _pull("strive_calculated", "/treasury/api/dashboard/calculated", params, offline, _trim_calculated)


def base_data(offline: bool = False) -> tuple[dict | None, str]:
    """Share-count history, cash history and the BTC ledger."""
    return _pull("strive_base", "/treasury/api/dashboard/base-data", None, offline, _base_data)
