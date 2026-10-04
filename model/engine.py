"""The weekly projection. One run = one BTC CAGR band and one mNAV path.

Each week, in order:
  1. BTC moves along its path; ASST is priced at that week's mNAV x NTAV per share (before the week's issuance).
  2. Capital comes in: SATA at $100 par (demand-led: a fixed $ per week through the switch date, then growing at a
     set rate a year), common (% of FD shares, sold at that price),
     and the PIPE warrants on their exercise date (at the strike, only if ASST is above it).
  3. Cash goes out: SATA dividends (that week's rate x notional, accrued daily; the rate holds at 13% or glides to a
     target) and the net operating burn.
  4. Cash is kept at the dividend reserve (reserve_months of SATA dividends); everything above it buys BTC.
     If the reserve runs dry, BTC is sold to pay (Strive never has; the btc_bought column turns negative).

At a constant mNAV, SATA sold at par leaves NTAV per share unchanged (cash in = new claim), so SATA adds value only
when BTC outruns the dividend. Common sold above NTAV per share (mNAV > 1) adds to it: 1 - 1/mNAV per dollar raised.
"""
from __future__ import annotations

import calendar
from datetime import date, timedelta

import numpy as np
import pandas as pd

from model import metrics
from model.levers import Levers
from model.state import State


def schedule(start: date, end: date) -> list[date]:
    """Weekly steps from start, plus every Dec 31 and the horizon end, so year-end values are exact."""
    days = {start + timedelta(weeks=k) for k in range(0, (end - start).days // 7 + 1)}
    days |= {date(y, 12, 31) for y in range(start.year, end.year + 1) if start < date(y, 12, 31) <= end}
    return sorted(days | {end})


def _years_after(anchor: date, d: date) -> float:
    # Actual/actual year fraction from a Dec 31 anchor: exactly 1.0 at each later Dec 31, so YE prices are round.
    days_in_year = 366 if calendar.isleap(d.year) else 365
    return (d.year - anchor.year - 1) + (d - date(d.year - 1, 12, 31)).days / days_in_year


def btc_path(dates: list[date], p0: float, ye_anchor: date, ye_price: float, cagr: float) -> np.ndarray:
    t0 = dates[0]
    span = max((ye_anchor - t0).days, 1)
    return np.array([p0 * (ye_price / p0) ** ((d - t0).days / span) if d <= ye_anchor
                     else ye_price * (1 + cagr) ** _years_after(ye_anchor, d) for d in dates])


def glide_path(dates: list[date], v0: float, target: float | None, glide_to: date) -> np.ndarray:
    """Today's value, moving linearly to target by glide_to, then held (used for mNAV and the SATA rate)."""
    if target is None:
        return np.full(len(dates), v0)
    t0 = dates[0]
    span = (glide_to - t0).days
    if span <= 0:
        return np.full(len(dates), target)
    return np.array([v0 + (target - v0) * min((d - t0).days / span, 1.0) for d in dates])


def sata_per_week(lv: Levers, d: date) -> float:
    """Weekly SATA $ (demand-led): flat through the switch date, then growing at sata_growth a year."""
    if d <= lv.sata_switch:
        return lv.sata_weekly_usd
    return lv.sata_weekly_usd * (1 + lv.sata_growth) ** _years_after(lv.sata_switch, d)


def run(state: State, lv: Levers, cagr: float, mnav: float | None = None, *, sata: bool = True,
        common: bool = True, warrants: bool = True, burn: bool = True) -> pd.DataFrame:
    """Weekly rows from today to the horizon. mnav=None holds today's multiple; a number glides to it.
    The switches turn pieces off for the attribution."""
    dates = schedule(state.price_date, lv.horizon_end)
    m0 = metrics.mnav(state, state.share_price)
    P = btc_path(dates, state.btc_price, lv.ye_anchor, lv.ye_btc_price, cagr)
    M = glide_path(dates, m0, mnav, lv.mnav_glide_to)
    R = glide_path(dates, lv.sata_rate if lv.sata_rate is not None else state.sata_rate, lv.sata_rate_target,
                   lv.sata_rate_glide_to)

    btc, n, sata_n, cash = state.btc, state.fd_shares, state.sata_notional, state.cash
    sec, debt, w_left = state.securities, state.debt, state.warrants
    flows0 = dict(raised_sata=0.0, raised_common=0.0, new_shares=0.0, warrant_shares=0.0, raised_warrants=0.0,
                  dividends=0.0, opex=0.0, btc_bought_usd=0.0)
    rows = [_row(dates[0], metrics.Book(btc, P[0], n, sata_n, cash, sec, debt), M[0], R[0], flows0)]
    for i in range(1, len(dates)):
        days = (dates[i] - dates[i - 1]).days
        wk, p, m, rate = days / 7, P[i], M[i], R[i]
        px = metrics.price_at(metrics.Book(btc, p, n, sata_n, cash, sec, debt), m)  # this week's ASST price
        f = dict(flows0)
        f["raised_sata"] = sata_per_week(lv, dates[i]) * wk if sata else 0.0
        f["new_shares"] = n * ((1 + lv.common_weekly_pct) ** wk - 1) if common else 0.0
        f["raised_common"] = f["new_shares"] * px
        if warrants and w_left and dates[i - 1] < lv.warrant_date <= dates[i]:
            f["warrant_shares"] = w_left * lv.warrant_exercise if px > lv.warrant_strike else 0.0
            f["raised_warrants"] = f["warrant_shares"] * lv.warrant_strike
            w_left = 0.0  # whatever isn't exercised lapses
        f["dividends"] = rate * sata_n * days / 365  # SATA pays every business day on the notional
        f["opex"] = lv.net_cash_burn_weekly_usd * wk if burn else 0.0

        sata_n += f["raised_sata"]
        n += f["new_shares"] + f["warrant_shares"]
        cash += f["raised_sata"] + f["raised_common"] + f["raised_warrants"] - f["dividends"] - f["opex"]
        reserve = lv.reserve_months / 12 * rate * sata_n
        if cash > reserve:            # everything above the dividend reserve buys BTC
            f["btc_bought_usd"], cash = cash - reserve, reserve
        elif cash < 0:                # reserve exhausted: sell BTC to pay
            f["btc_bought_usd"], cash = cash, 0.0
        btc += f["btc_bought_usd"] / p
        rows.append(_row(dates[i], metrics.Book(btc, p, n, sata_n, cash, sec, debt), m, rate, f))

    out = pd.DataFrame(rows).set_index("date")
    out.index = pd.to_datetime(out.index)
    out["btc_yield"] = out["sats_per_share"] / out["sats_per_share"].iloc[0] - 1  # cumulative, Strive's FD basis
    return out


def _row(d: date, b: metrics.Book, m: float, rate: float, flows: dict) -> dict:
    nps = metrics.ntav_per_share(b)
    return {"date": d, "btc_price": b.btc_price, "mnav": m, "share_price": m * nps, "ntav_per_share": nps,
            "btc": b.btc, "fd_shares": b.fd_shares, "sata_notional": b.sata_notional, "cash": b.cash,
            "btc_nav": metrics.btc_nav(b), "amplification": metrics.amplification(b),
            "sats_per_share": metrics.sats_per_share(b), "coverage_years": metrics.dividend_coverage_years(b, rate),
            "sata_rate": rate, **flows}


def at(df: pd.DataFrame, d: date) -> pd.Series:
    """The row on (or the last one before) a date."""
    return df.loc[:pd.Timestamp(d)].iloc[-1]
