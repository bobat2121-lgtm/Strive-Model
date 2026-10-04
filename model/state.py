"""The company today: one dated snapshot of Strive's balance sheet and prices that the engine starts from.

Holdings and share counts are as of the latest weekly 8-K (strive.com mirrors each one the Monday it's filed).
Prices are the latest day on Strive's dashboard, or live Coinbase / Yahoo prices with live_prices=True.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date, timedelta

from model.sources import market, strive


@dataclass(frozen=True)
class State:
    as_of: date               # balance date of the latest weekly 8-K
    price_date: date          # date of btc_price / share_price
    btc: float
    btc_price: float
    share_price: float        # ASST
    fd_shares: float          # Strive's "assumed fully diluted" count (excludes the traditional warrants)
    sata_notional: float      # $100 stated amount x SATA shares
    sata_rate: float          # annual dividend rate, 0.13 = 13%
    cash: float
    securities: float         # STRC held, at fair value
    debt: float
    warrants: float           # traditional (PIPE) warrants outstanding
    strive_ev_mnav: float | None = None  # the API's evMnav for price_date (EV / BTC NAV), a cross-check
    sources: dict = field(default_factory=dict)
    history: dict = field(default_factory=dict)  # actual {fy_start, year_ago}: {date, btc, fd_shares}, for TD Cowen's
                                                 # BTC Yield (FY2026 starts before the forecast) and the implied k

    def with_prices(self, btc_price: float | None = None, share_price: float | None = None,
                    price_date: date | None = None) -> State:
        return replace(self, btc_price=btc_price or self.btc_price, share_price=share_price or self.share_price,
                       price_date=price_date or self.price_date, strive_ev_mnav=None)


def _history(base: dict | None, as_of: date) -> dict:
    """BTC held and FD shares on the share-history date nearest each target, from strive.com's ledger."""
    rows = sorted((base or {}).get("shares") or [], key=lambda s: s["date"])
    tx = (base or {}).get("transactions") or []
    if not rows:
        return {}

    def point(target: date) -> dict:
        r = min(rows, key=lambda s: abs((date.fromisoformat(s["date"]) - target).days))
        btc = sum(t["btc_amount"] for t in tx if t["transaction_date"] <= r["date"])
        return {"date": date.fromisoformat(r["date"]), "btc": btc, "fd_shares": float(r["fully_diluted_shares"])}

    return {"fy_start": point(date(as_of.year - 1, 12, 31)), "year_ago": point(as_of - timedelta(days=365))}


def from_payloads(calc: dict, base: dict | None, sources: dict | None = None) -> State:
    """Build the snapshot from strive.com's calculated rows (trimmed) and base-data."""
    rows = [r for r in calc.get("rows") or [] if r.get("sharePrice") and r.get("btcPrice") and r.get("btcHoldings")]
    if not rows:
        raise ValueError("strive.com returned no priced rows")
    r = rows[-1]
    sata = next((p for p in calc.get("preferredStocks") or [] if p.get("ticker") == "SATA"), {})
    shares = max((base or {}).get("shares") or [], key=lambda s: s["date"], default={})
    as_of = date.fromisoformat(shares.get("date") or sata.get("date") or r["date"])
    return State(
        as_of=as_of,
        price_date=date.fromisoformat(r["date"]),
        btc=float(r["btcHoldings"]), btc_price=float(r["btcPrice"]), share_price=float(r["sharePrice"]),
        fd_shares=float(r["sharesOutstanding"]),
        sata_notional=float(sata.get("notional_value") or r.get("preferredStockMarketCap") or 0.0),
        sata_rate=float(sata.get("dividend_rate") or 0.0),
        cash=float(r.get("cash") or 0.0), securities=float(r.get("marketableSecurities") or 0.0),
        debt=float(r.get("debt") or 0.0), warrants=float(shares.get("traditional_warrants") or 0.0),
        strive_ev_mnav=r.get("evMnav"), sources=sources or {}, history=_history(base, as_of))


def load(offline: bool = False, live_prices: bool = False) -> State:
    calc, calc_src = strive.calculated(offline)
    base, base_src = strive.base_data(offline)
    if calc is None:
        raise RuntimeError("No strive.com data, live or cached. Run once online first.")
    st = from_payloads(calc, base, {"balance sheet, SATA, prices": calc_src, "warrants": base_src})
    if live_prices and not offline:
        btc, asst = market.btc_spot(), market.last_close("ASST")
        if btc and asst:
            st = st.with_prices(btc, asst[0], date.today())
            st.sources["prices"] = f"Coinbase BTC spot, Yahoo ASST close {asst[1]}"
    return st
