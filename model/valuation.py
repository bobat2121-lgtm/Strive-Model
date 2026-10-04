"""Valuation on top of the engine: the price target, the k x BTC CAGR table, and the attribution.

Price target (the BTC-earnings method; it reproduces a published $44 sell-side target on ASST from its inputs):

    PT_T = [ NTAV_T + k x BTC $ Gain over the fiscal year ending at T ] / FD shares_T
    BTC $ Gain = BTC Gain x BTC price_T;  BTC Gain = BTC held at the start of the year x BTC Yield for the year
    BTC Yield  = growth in BTC per assumed diluted share over the year (Strive's KPI)

In plain terms: what common owns at T, plus k years' worth of the bitcoin the company added per share that year.
k starts at what today's price implies and glides to the chosen k by a date (or holds the chosen k).

The market mNAV (the price new common sells at) can follow the model's own valuation: solve_market() iterates until
the market multiple at every year end equals the price target's implied mNAV at that date, with straight lines in
between, starting from today's actual multiple. Because selling shares at a higher multiple raises BTC per share,
which raises the value, the solution is a fixed point; it's damped and capped, and reports when it doesn't settle.
BTC Yield counts every bitcoin bought, including those bought with SATA money (SATA holders are owed $100 a share,
which NTAV deducts at T). The premium is split into the part from SATA-funded and from common-funded bitcoin so
that's visible, and a net-basis value (gain measured on NTAV / BTC price, the part that belongs to common) is
reported alongside as a reference.

FY2026 starts before the forecast, so it's stitched from Strive's actual history: the yield is measured from the
actual 12/31/25 BTC per share (Strive's own convention), and the BTC Gain base includes the 5,048.1 BTC from the
Semler merger (1/16/26), which is how the published FY26 figure reconciles.

Attribution ($ per share, adds up exactly):
    NTAV today -> BTC move -> amplification -> SATA dividends -> issuance -> op costs -> NTAV at T
               -> growth premium (SATA-funded + common-funded) -> price target
  BTC move       NTAV today x (BTC_T / BTC_0 - 1): common's net assets tracking BTC one-for-one
  Amplification  what the SATA-funded BTC (existing + new) gains, after the cash-reserve drag
  SATA dividends the dividends paid on that SATA
  Issuance       common ATM + warrants sold above NTAV per share (at the market mNAV path)
  Op. costs      the net cash burn (opex less fee revenue), not dividends
  Growth premium k x the year's BTC $ Gain per share
"""
from __future__ import annotations

from datetime import date

from dataclasses import replace

import pandas as pd

from model import engine, metrics
from model.levers import Levers
from model.state import State

PARTS = ["btc_move", "amplification", "sata_dividends", "issuance", "op_costs", "growth_premium"]
SEMLER_BTC = 5048.1               # strive.com ledger, 1/16/26: the bitcoin that came with Semler Scientific
SEMLER_CLOSE = date(2026, 1, 16)


def value_per_share(ntav_total: float, btc_gain: float, btc_price: float, fd_shares: float, k: float) -> float:
    """Equity value per share: (NTAV + k x BTC Gain x BTC price) / FD shares."""
    return (ntav_total + k * btc_gain * btc_price) / fd_shares


def valuation_dates(state: State, lv: Levers) -> list[date]:
    return [date(y, 12, 31) for y in range(state.price_date.year, lv.horizon_end.year + 1)
            if state.price_date < date(y, 12, 31) <= lv.horizon_end]


def _year_start(df: pd.DataFrame, state: State, t: date) -> tuple[float, float, bool]:
    """(BTC Gain base, BTC per share in sats, inside the forecast?) at the start of the fiscal year ending t."""
    start = date(t.year - 1, 12, 31)
    if start >= state.price_date:
        r = engine.at(df, start)
        return r.btc, r.sats_per_share, True
    h = state.history["fy_start"]  # stitched from Strive's actual history
    base = h["btc"] + (SEMLER_BTC if start < SEMLER_CLOSE <= t else 0.0)
    return base, h["btc"] / h["fd_shares"] * 1e8, False


def btc_gain(df: pd.DataFrame, state: State, t: date) -> dict:
    base, sats0, in_forecast = _year_start(df, state, t)
    r = engine.at(df, t)
    y = r.sats_per_share / sats0 - 1
    return {"btc_yield": y, "btc_gain": base * y, "gain_per_share": base * y * r.btc_price / r.fd_shares,
            "in_forecast": in_forecast}


def premium_split(df: pd.DataFrame, t: date, k: float) -> tuple[float, float]:
    """(SATA-funded, common-funded) parts of the growth premium per share, for a year inside the forecast.

    BTC Gain = d x BTC bought with SATA money + (d x BTC bought with common money - BTC_start x (1 - d)), where
    d = shares at the start / shares at T. Each week's purchase is split by the cash each side brought in: SATA
    proceeds less its dividends and reserve top-up, and common + warrant proceeds less the burn."""
    start = date(t.year - 1, 12, 31)
    w = df.loc[pd.Timestamp(start):pd.Timestamp(t)]
    a, b, rows = w.iloc[0], w.iloc[-1], w.iloc[1:]
    d_cash = w["cash"].diff().iloc[1:]
    sata_btc = ((rows.raised_sata - rows.dividends - d_cash) / rows.btc_price).sum()
    common_btc = ((rows.raised_common + rows.raised_warrants - rows.opex) / rows.btc_price).sum()
    d = a.fd_shares / b.fd_shares
    scale = k * b.btc_price / b.fd_shares
    return scale * d * sata_btc, scale * (d * common_btc - a.btc * (1 - d))


def net_value(df: pd.DataFrame, t: date, k: float) -> float | None:
    """Reference: the same formula with the gain measured on net BTC (NTAV / BTC price), the part that belongs to
    common. Only for years inside the forecast."""
    start = date(t.year - 1, 12, 31)
    if pd.Timestamp(start) < df.index[0]:
        return None
    a, b = engine.at(df, start), engine.at(df, t)
    net_btc_a = a.ntav_per_share * a.fd_shares / a.btc_price
    y = (b.ntav_per_share / b.btc_price) / (a.ntav_per_share / a.btc_price) - 1
    return value_per_share(b.ntav_per_share * b.fd_shares, net_btc_a * y, b.btc_price, b.fd_shares, k)


def k_at(state: State, lv: Levers, t: date) -> float:
    """The growth multiple at date t: today's implied k gliding to lv.growth_multiple by lv.k_glide_to, then held."""
    if not lv.k_glide:
        return lv.growth_multiple
    k0, t0 = implied_k(state), state.price_date
    span = (lv.k_glide_to - t0).days
    w = 1.0 if span <= 0 else min(max((t - t0).days / span, 0.0), 1.0)
    return k0 + (lv.growth_multiple - k0) * w


def price_target(df: pd.DataFrame, state: State, t: date, lv: Levers, k: float | None = None) -> dict:
    k = k_at(state, lv, t) if k is None else k
    r, g = engine.at(df, t), btc_gain(df, state, t)
    pt = value_per_share(r.ntav_per_share * r.fd_shares, g["btc_gain"], r.btc_price, r.fd_shares, k)
    sata_p, common_p = premium_split(df, t, k) if g["in_forecast"] else (None, None)
    return {"date": t, "ntav_per_share": r.ntav_per_share, **g, "k": k, "growth_premium": pt - r.ntav_per_share,
            "premium_sata": sata_p, "premium_common": common_p, "price_target": pt,
            "implied_mnav": pt / r.ntav_per_share, "market_price": r.share_price, "amplification": r.amplification,
            "net_target": net_value(df, t, k)}


def implied_k(state: State) -> float:
    """The k today's price implies on Strive's actual trailing-12-month BTC $ Gain (same definition)."""
    h = state.history["year_ago"]
    y = metrics.sats_per_share(state) / (h["btc"] / h["fd_shares"] * 1e8) - 1
    gain_ps = h["btc"] * y * state.btc_price / state.fd_shares
    return (state.share_price - metrics.ntav_per_share(state)) / gain_ps


def solve_market(state: State, lv: Levers, cagr: float, tol: float = 0.005, max_iter: int = 60,
                 damp: float = 0.6) -> tuple[pd.DataFrame, dict | float | None, bool]:
    """(weekly run, market mNAV path, settled?). In "model" mode the path makes the market multiple equal the
    model's implied mNAV at each year end; in "manual" mode it's lv.mnav_target (hold or glide)."""
    if lv.market_mnav_mode != "model":
        return engine.run(state, lv, cagr, lv.mnav_target), lv.mnav_target, True
    dates = valuation_dates(state, lv)
    path = {d: metrics.mnav(state, state.share_price) for d in dates}
    for _ in range(max_iter):
        df = engine.run(state, lv, cagr, path)
        implied = {d: price_target(df, state, d, lv)["implied_mnav"] for d in dates}
        gap = max(abs(implied[d] - path[d]) for d in dates)
        if gap < tol:
            return df, path, True
        path = {d: min(max(path[d] + damp * (implied[d] - path[d]), 0.5), 10.0) for d in dates}  # damped, capped
    return engine.run(state, lv, cagr, path), path, False


def _band(g: float) -> str:
    return f"{g * 100:g}% CAGR"


def table(state: State, lv: Levers) -> dict:
    """Price target at lv.pt_date: rows = the k the glide ends at (today's implied k, held, first), columns = BTC
    CAGR bands. Each cell is its own run with its own k path and, in "model" mode, its own consistent market path."""
    k_today = implied_k(state)
    rows = [(f"{k_today:.2f}x (today's price)", k_today)] + [(f"{k:g}x", k) for k in lv.k_table]
    pt, mn, settled = {}, {}, True
    for g in lv.cagr_bands:
        for label, k in rows:
            cell = replace(lv, growth_multiple=k)
            df, _, ok = solve_market(state, cell, g)
            v = price_target(df, state, lv.pt_date, cell)
            settled &= ok
            pt.setdefault(_band(g), {})[label] = v["price_target"] if ok else float("nan")
            mn.setdefault(_band(g), {})[label] = v["implied_mnav"] if ok else float("nan")
    order = [r[0] for r in rows]
    return {"price_target": pd.DataFrame(pt).reindex(order), "implied_mnav": pd.DataFrame(mn).reindex(order),
            "k_today": k_today, "settled": settled}


def attribution(state: State, lv: Levers, cagr: float) -> pd.DataFrame:
    """Rows = valuation dates; columns = start (NTAV today), the parts, ntav_end, end (price target), today_price,
    and the premium split (NaN where the year starts before the forecast)."""
    full, path, _ = solve_market(state, lv, cagr)
    no_common = engine.run(state, lv, cagr, path, common=False, warrants=False)
    no_costs = engine.run(state, lv, cagr, path, common=False, warrants=False, burn=False)
    n0, b0, p0 = full["ntav_per_share"].iloc[0], full["btc_price"].iloc[0], full["share_price"].iloc[0]
    out = {}
    for t in valuation_dates(state, lv):
        f, nc, nk = (engine.at(df, t) for df in (full, no_common, no_costs))
        tracker = n0 * f["btc_price"] / b0
        divs = no_costs.loc[:pd.Timestamp(t), "dividends"].sum() / state.fd_shares  # share count is fixed in this run
        v = price_target(full, state, t, lv)
        out[t] = {"start": n0, "btc_move": tracker - n0, "amplification": nk["ntav_per_share"] - tracker + divs,
                  "sata_dividends": -divs, "issuance": f["ntav_per_share"] - nc["ntav_per_share"],
                  "op_costs": nc["ntav_per_share"] - nk["ntav_per_share"], "ntav_end": f["ntav_per_share"],
                  "growth_premium": v["growth_premium"], "premium_sata": v["premium_sata"],
                  "premium_common": v["premium_common"], "end": v["price_target"], "today_price": p0,
                  "implied_mnav": v["implied_mnav"], "btc_yield": v["btc_yield"], "net_target": v["net_target"],
                  "k": v["k"], "market_mnav": f["mnav"]}
    return pd.DataFrame(out).T.astype(float)
