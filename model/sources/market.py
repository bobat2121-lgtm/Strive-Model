"""Prices: BTC spot from Coinbase; ASST, SATA and BTC daily bars from Yahoo (yfinance)."""
from __future__ import annotations

import logging
from datetime import date

import httpx
import pandas as pd

log = logging.getLogger(__name__)


def btc_spot() -> float | None:
    try:
        r = httpx.get("https://api.coinbase.com/v2/prices/BTC-USD/spot", timeout=15)
        r.raise_for_status()
        return float(r.json()["data"]["amount"])
    except (httpx.HTTPError, ValueError, KeyError) as e:
        log.warning("Coinbase spot failed: %s", e)
        return None


def daily_bars(ticker: str, start: date, end: date) -> pd.DataFrame:
    """open/high/low/close/volume by trading day (tz-naive dates). Empty frame on failure."""
    import yfinance as yf  # slow import; only the calibration and live prices need it

    try:
        h = yf.Ticker(ticker).history(start=start.isoformat(), end=end.isoformat(), interval="1d", auto_adjust=False)
    except Exception as e:  # yfinance raises a zoo of exception types
        log.warning("Yahoo bars for %s failed: %s", ticker, e)
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
    h.index = h.index.tz_localize(None).normalize()
    return h.rename(columns=str.lower)[["open", "high", "low", "close", "volume"]]


def last_close(ticker: str) -> tuple[float, date] | None:
    bars = daily_bars(ticker, date.today() - pd.Timedelta(days=10), date.today() + pd.Timedelta(days=1))
    if bars.empty:
        return None
    return float(bars["close"].iloc[-1]), bars.index[-1].date()
