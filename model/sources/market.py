"""BTC spot from Coinbase, timestamped stock quotes and daily bars from Yahoo."""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from datetime import date, datetime, time, timezone

import httpx
import pandas as pd

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Quote:
    price: float
    as_of: datetime
    source: str


def _positive_price(value) -> float:
    price = float(value)
    if not math.isfinite(price) or price <= 0:
        raise ValueError("price must be positive and finite")
    return price


def btc_quote() -> Quote | None:
    """Spot quote; Coinbase supplies no trade time, so label the retrieval time."""
    try:
        r = httpx.get("https://api.coinbase.com/v2/prices/BTC-USD/spot", timeout=15)
        r.raise_for_status()
        return Quote(_positive_price(r.json()["data"]["amount"]), datetime.now(timezone.utc),
                     "Coinbase BTC spot, checked")
    except (httpx.HTTPError, ValueError, TypeError, KeyError) as e:
        log.warning("Coinbase spot failed: %s", e)
        return None


def btc_spot() -> float | None:
    quote = btc_quote()
    return quote.price if quote else None


def stock_quote(ticker: str) -> Quote | None:
    """Latest regular-market quote with its actual timestamp, including closed markets.

    Yahoo's chart metadata is public but undocumented; retain the daily-bar
    fallback if its response changes or the quote endpoint is unavailable.
    """
    try:
        r = httpx.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}",
                      params={"range": "5d", "interval": "1d"},
                      headers={"User-Agent": "Mozilla/5.0 (compatible; StriveModel/1.0)"}, timeout=15)
        r.raise_for_status()
        meta = r.json()["chart"]["result"][0]["meta"]
        return Quote(_positive_price(meta["regularMarketPrice"]),
                     datetime.fromtimestamp(meta["regularMarketTime"], timezone.utc),
                     f"Yahoo {ticker} regular market")
    except (httpx.HTTPError, ValueError, TypeError, KeyError, IndexError, OverflowError) as e:
        log.warning("Yahoo quote for %s failed: %s", ticker, e)
    close = last_close(ticker)
    if close is None:
        return None
    # A daily bar only identifies the session date, not a quote timestamp.
    return Quote(close[0], datetime.combine(close[1], time.min, timezone.utc),
                 f"Yahoo {ticker} daily close (session date)")


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
    valid = bars.loc[bars["close"].notna() & (bars["close"] > 0)].sort_index()
    if valid.empty:
        return None
    return float(valid["close"].iloc[-1]), valid.index[-1].date()
