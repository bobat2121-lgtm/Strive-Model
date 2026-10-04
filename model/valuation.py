"""Valuation on top of the engine: the price target, the k x BTC CAGR table, and the attribution.

Price target, TD Cowen's structure: what common owns at the target date, plus a multiple of the growth it's expected
to add over the following year (the forecast runs past the target date so that year exists):

    PT_T = NTAV per share_T + k x forward gain per share (T -> T + 1 year), valued at T's BTC price

    net gain   = NTAV per share_T x growth in net BTC per share (NTAV / BTC price). This is the accretion that belongs
                 to common: shares sold above NTAV, and SATA leverage once BTC outruns the dividend.
    gross gain = BTC held_T x Strive's BTC Yield x BTC price_T / FD shares. TD Cowen's literal input; it counts BTC
                 bought with SATA money as gain even though SATA holders are owed it.

The engine's mNAV path only sets the price new common sells at during the forecast. k changes the valuation, not
the forecast, so the k table needs one run per BTC band.

Attribution ($ per share, adds up exactly):
    NTAV today -> BTC move -> amplification -> SATA dividends -> issuance -> op costs -> NTAV at T
               -> growth premium -> price target
  BTC move       NTAV today x (BTC_T / BTC_0 - 1): common's net assets tracking BTC one-for-one
  Amplification  what the SATA-funded BTC (existing + new) gains, after the cash-reserve drag
  SATA dividends the dividends paid on that SATA (rate x notional, every week)
  Issuance       common ATM + warrants sold above NTAV per share (at the market mNAV path); also the extra SATA, and
                 its dividends, that a bigger BTC stack brings when SATA scales with the stack
  Op. costs      the net cash burn (opex less fee revenue), not dividends
  Growth premium k x the next year's gain per share
"""
from __future__ import annotations

import calendar
from datetime import date

import pandas as pd

from model import engine
from model.levers import Levers
from model.state import State

PARTS = ["btc_move", "amplification", "sata_dividends", "issuance", "op_costs", "growth_premium"]


def plus_year(d: date) -> date:
    return date(d.year + 1, d.month, 28 if (d.month, d.day) == (2, 29) and not calendar.isleap(d.year + 1) else d.day)


def valuation_dates(state: State, lv: Levers) -> list[date]:
    """Year ends that have a full forward year inside the forecast."""
    return [date(y, 12, 31) for y in range(state.price_date.year, lv.horizon_end.year + 1)
            if state.price_date < date(y, 12, 31) and plus_year(date(y, 12, 31)) <= lv.horizon_end]


def forward_gain(df: pd.DataFrame, t: date, basis: str = "net") -> tuple[float, float]:
    """(yield, $ gain per share) over the year after t, valued at t's BTC price."""
    a, b = engine.at(df, t), engine.at(df, plus_year(t))
    if basis == "gross":
        y = b.sats_per_share / a.sats_per_share - 1
        return y, a.btc * y * a.btc_price / a.fd_shares
    y = (b.ntav_per_share / b.btc_price) / (a.ntav_per_share / a.btc_price) - 1
    return y, a.ntav_per_share * y


def price_target(df: pd.DataFrame, t: date, lv: Levers, k: float | None = None) -> dict:
    k = lv.growth_multiple if k is None else k
    r = engine.at(df, t)
    y, g = forward_gain(df, t, lv.gain_basis)
    pt = r.ntav_per_share + k * g
    return {"date": t, "ntav_per_share": r.ntav_per_share, "forward_yield": y, "forward_gain": g, "k": k,
            "growth_premium": k * g, "price_target": pt, "implied_mnav": pt / r.ntav_per_share,
            "market_price": r.share_price, "amplification": r.amplification}


def implied_k(df: pd.DataFrame, lv: Levers) -> float:
    """The k that today's price implies: (price - NTAV per share) / next year's gain per share."""
    t0 = df.index[0].date()
    _, g = forward_gain(df, t0, lv.gain_basis)
    return (df["share_price"].iloc[0] - df["ntav_per_share"].iloc[0]) / g


def _band(g: float) -> str:
    return f"{g * 100:g}% CAGR"


def table(state: State, lv: Levers) -> dict[str, pd.DataFrame]:
    """Price target at lv.pt_date: rows = k (with the k today's price implies first), columns = BTC CAGR bands."""
    runs = {g: engine.run(state, lv, g, lv.mnav_target) for g in lv.cagr_bands}
    k_today = implied_k(runs[lv.base_cagr] if lv.base_cagr in runs else next(iter(runs.values())), lv)
    rows = [(f"{k_today:.2f}x (today's price)", k_today)] + [(f"{k:g}x", k) for k in lv.k_table]
    pt, mn = {}, {}
    for g, df in runs.items():
        for label, k in rows:
            v = price_target(df, lv.pt_date, lv, k)
            pt.setdefault(_band(g), {})[label] = v["price_target"]
            mn.setdefault(_band(g), {})[label] = v["implied_mnav"]
    order = [r[0] for r in rows]
    return {"price_target": pd.DataFrame(pt).reindex(order), "implied_mnav": pd.DataFrame(mn).reindex(order),
            "k_today": k_today}


def attribution(state: State, lv: Levers, cagr: float) -> pd.DataFrame:
    """Rows = valuation dates; columns = start (NTAV today), the parts, ntav_end, end (price target), today_price."""
    full = engine.run(state, lv, cagr, lv.mnav_target)
    no_common = engine.run(state, lv, cagr, lv.mnav_target, common=False, warrants=False)
    no_costs = engine.run(state, lv, cagr, lv.mnav_target, common=False, warrants=False, burn=False)
    n0, b0, p0 = full["ntav_per_share"].iloc[0], full["btc_price"].iloc[0], full["share_price"].iloc[0]
    out = {}
    for t in valuation_dates(state, lv):
        f, nc, nk = (engine.at(df, t) for df in (full, no_common, no_costs))
        tracker = n0 * f["btc_price"] / b0
        divs = no_costs.loc[:pd.Timestamp(t), "dividends"].sum() / state.fd_shares  # share count is fixed in this run
        v = price_target(full, t, lv)
        out[t] = {"start": n0, "btc_move": tracker - n0, "amplification": nk["ntav_per_share"] - tracker + divs,
                  "sata_dividends": -divs,
                  "issuance": f["ntav_per_share"] - nc["ntav_per_share"],
                  "op_costs": nc["ntav_per_share"] - nk["ntav_per_share"], "ntav_end": f["ntav_per_share"],
                  "growth_premium": v["growth_premium"], "end": v["price_target"], "today_price": p0,
                  "implied_mnav": v["implied_mnav"], "forward_yield": v["forward_yield"]}
    return pd.DataFrame(out).T
