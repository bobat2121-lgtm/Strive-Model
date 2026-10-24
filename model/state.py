"""The company today: one dated snapshot of Strive's balance sheet and prices that the engine starts from.

Holdings and share counts are as of the latest weekly 8-K (strive.com mirrors each one the Monday it's filed).
Prices are the latest day on Strive's dashboard, or live Coinbase / Yahoo prices with live_prices=True.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date, timedelta
import math

from model.sources import market, strive


# Final prospectus (424B5, filed October 19, 2026), offering expected to close October 20.
# 7m shares at $90, $100 stated amount; proceeds are net of fees and expenses.
SATS_IPO_DATE = date(2026, 10, 20)
SATS_IPO_NOTIONAL = 700_000_000.0
SATS_IPO_NET_PROCEEDS = 608_150_000.0
SATS_RATE = 0.15
SATS_PROSPECTUS = "https://www.sec.gov/Archives/edgar/data/1920406/000095010326015734/dp255138_424b5.htm"


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
    history: dict = field(default_factory=dict)  # actual {fy_start, year_ago}: {date, btc, fd_shares}, for the year's
                                                 # BTC Yield (FY2026 starts before the forecast) and the implied k
    sats_notional: float = 0.0
    sats_rate: float = SATS_RATE
    sats_liquidation_preference: float | None = None
    sats_ipo_applied: bool = False
    cash_as_of: date | None = None  # independent of the share-count date; None means unresolved cash provenance

    def with_prices(self, btc_price: float | None = None, share_price: float | None = None,
                    price_date: date | None = None) -> State:
        return replace(self, btc_price=btc_price or self.btc_price, share_price=share_price or self.share_price,
                       price_date=price_date or self.price_date, strive_ev_mnav=None)


def with_sats_ipo(st: State, through: date) -> State:
    """Supplement a pre-IPO balance sheet once the known transaction has closed.

    Cash and the preferred claim refresh independently. Add proceeds only to cash confirmed to predate the IPO,
    even if SATS already appears in the preferred table. Post-IPO or unresolved cash gets no extra proceeds.
    The dated source balance and BTC holdings stay intact; the supplemental transaction is identified separately.
    """
    if through < SATS_IPO_DATE or st.sats_ipo_applied:
        return st
    add_cash = st.cash_as_of is not None and st.cash_as_of < SATS_IPO_DATE
    detail = ("net proceeds added to pre-IPO cash" if add_cash else
              "proceeds already in post-IPO cash balance" if st.cash_as_of is not None else
              "cash timing unresolved; net proceeds not added")
    sources = {**st.sources, "SATS": f"{SATS_PROSPECTUS} (October 20 IPO; "
               + detail + ")"}
    notional = st.sats_notional or SATS_IPO_NOTIONAL
    return replace(st, sats_notional=notional, sats_rate=st.sats_rate,
                   sats_liquidation_preference=max(notional, st.sats_liquidation_preference or notional),
                   sats_ipo_applied=True,
                   cash=st.cash + (SATS_IPO_NET_PROCEEDS if add_cash else 0.0), sources=sources,
                   strive_ev_mnav=None)


def _preferred(calc: dict, ticker: str, through: date) -> dict:
    rows = [p for p in calc.get("preferredStocks") or [] if p.get("ticker", "").upper() == ticker
            and (not p.get("date") or p["date"][:10] <= through.isoformat())]
    return max(rows, key=lambda p: p.get("date") or "", default={})


def _number(record: dict, *keys: str, default=0.0) -> float:
    for key in keys:
        if record.get(key) is not None:
            return float(record[key])
    return default


def _cash_date(row: dict, base: dict | None, through: date) -> date | None:
    """Date the selected calculated cash actually describes, never inferred from a share count.

    If the endpoints refreshed at different times, only matching cash/debt/securities records may supply a date.
    With no match or explicit date, leave it unknown so the IPO cannot add proceeds a second time.
    """
    explicit = next((row[k] for k in ("cashAsOf", "cashDate", "cash_as_of") if row.get(k)), None)
    if explicit:
        return date.fromisoformat(str(explicit)[:10])
    matching = []
    for record in (base or {}).get("cashDebt") or []:
        if not record.get("date") or record["date"][:10] > through.isoformat():
            continue
        if all(math.isclose(float(record.get(base_key) or 0), float(row.get(calc_key) or 0),
                            rel_tol=1e-9, abs_tol=0.01)
               for base_key, calc_key in (("cash", "cash"), ("debt", "debt"),
                                         ("marketable_securities", "marketableSecurities"))):
            matching.append(date.fromisoformat(record["date"][:10]))
    return max(matching, default=None)


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
    r = max(rows, key=lambda row: row["date"])
    price_date = date.fromisoformat(r["date"][:10])
    sata, sats = _preferred(calc, "SATA", price_date), _preferred(calc, "SATS", price_date)
    shares = max((s for s in (base or {}).get("shares") or [] if s["date"][:10] <= price_date.isoformat()),
                 key=lambda s: s["date"], default={})
    as_of = date.fromisoformat((shares.get("date") or sata.get("date") or r["date"])[:10])
    sats_n = _number(r, "satsNotional", default=_number(sats, "notional_value", "stated_value"))
    sats_claim = _number(r, "satsLiquidationPreference",
                         default=_number(sats, "liquidation_preference", default=sats_n))
    # preferredStockMarketCap is an aggregate. Use it only if an instrument-specific SATA record is absent.
    sata_n = _number(r, "sataNotional", default=_number(sata, "notional_value",
                     default=max(0.0, _number(r, "preferredStockMarketCap") - sats_claim)))
    cash_as_of = _cash_date(r, base, price_date)
    return State(
        as_of=as_of,
        price_date=price_date,
        btc=float(r["btcHoldings"]), btc_price=float(r["btcPrice"]), share_price=float(r["sharePrice"]),
        fd_shares=float(r["sharesOutstanding"]),
        sata_notional=sata_n,
        sata_rate=float(sata.get("dividend_rate") or 0.0),
        cash=float(r.get("cash") or 0.0), securities=float(r.get("marketableSecurities") or 0.0),
        debt=float(r.get("debt") or 0.0), warrants=float(shares.get("traditional_warrants") or 0.0),
        strive_ev_mnav=r.get("evMnav"), sources=sources or {}, history=_history(base, as_of),
        sats_notional=sats_n, sats_rate=_number(sats, "dividend_rate", default=SATS_RATE),
        sats_liquidation_preference=max(sats_n, sats_claim),
        sats_ipo_applied=bool(sats_n) and not (cash_as_of and cash_as_of < SATS_IPO_DATE),
        cash_as_of=cash_as_of)


def load(offline: bool = False, live_prices: bool = False) -> State:
    calc, calc_src = strive.calculated(offline)
    base, base_src = strive.base_data(offline)
    if calc is None:
        raise RuntimeError("No strive.com data, live or cached. Run once online first.")
    st = from_payloads(calc, base, {"balance sheet, SATA, prices": calc_src, "warrants": base_src})
    if live_prices and not offline:
        btc, asst = market.btc_quote(), market.stock_quote("ASST")
        fallback = f"Strive dashboard · {st.price_date:%b %d, %Y} (quote unavailable)"
        sources = {**st.sources,
                   "BTC price": f"{btc.source} · {btc.as_of:%b %d, %Y %H:%M UTC}" if btc else fallback,
                   "ASST price": f"{asst.source} · {asst.as_of:%b %d, %Y %H:%M UTC}" if asst else fallback}
        st = st.with_prices(btc_price=btc.price if btc else None, share_price=asst.price if asst else None,
                            price_date=btc.as_of.date() if btc else (asst.as_of.date() if asst else None))
        st = replace(st, sources=sources)
    return with_sats_ipo(st, st.price_date)
