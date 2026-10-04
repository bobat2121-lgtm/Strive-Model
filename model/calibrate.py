"""Weekly issuance backed out of public data, which is what the lever defaults rest on.

8-Ks report share counts every week but stopped reporting ATM dollars after 8/7/26, so:
  common ATM shares = change in issued shares - traditional-warrant exercises (Class B -> A conversions net out)
  common ATM $      = ATM shares x that week's ASST VWAP (typical price x volume over the week's sessions)
  SATA $            = change in SATA shares x max(SATA VWAP, $100)   (Strive doesn't sell SATA below par)
Check: sources (ATM + warrants at the strike + SATA) vs uses (BTC bought + change in cash + SATA dividends + burn).
Through 9/25/26 the two agree within $2M every week.
"""
from __future__ import annotations

import pandas as pd

WARRANT_STRIKE = 27.0
DAILY_DIVIDEND = 0.0516  # $ per SATA share per business day, Aug-Oct 2026 (13% / ~252 days on $100)
WEEKLY_BURN = 1.4e6


def _vwap(bars: pd.DataFrame, after: str, through: str) -> float:
    w = bars.loc[(bars.index > after) & (bars.index <= through)]
    tp = (w["high"] + w["low"] + w["close"]) / 3
    return float((tp * w["volume"]).sum() / w["volume"].sum())


def weekly(base: dict, weeks: dict[str, dict], bars: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """One row per week between consecutive 8-K balance dates that have both share counts and SATA counts.
    base = strive.com base-data; weeks = {balance_date: 8-K facts}; bars = {"ASST": df, "SATA": df}."""
    shares = {s["date"]: s for s in base["shares"]}
    cash = {c["date"]: c for c in base["cashDebt"]}
    bought: dict[str, float] = {}
    for t in base["transactions"]:
        bought[t["transaction_date"]] = bought.get(t["transaction_date"], 0.0) + t["cost"]
    sata = {d: f["sata_shares"] for d, f in weeks.items() if f.get("sata_shares") is not None}
    dates = sorted(d for d in shares if d in sata and d in cash)
    rows = []
    for prev, cur in zip(dates, dates[1:]):
        s0, s1 = shares[prev], shares[cur]
        warr = s0["traditional_warrants"] - s1["traditional_warrants"]
        atm = s1["issued_shares"] - s0["issued_shares"] - warr
        vw_a, vw_s = _vwap(bars["ASST"], prev, cur), _vwap(bars["SATA"], prev, cur)
        d_sata = sata[cur] - sata[prev]
        sata_usd, atm_usd, warr_usd = d_sata * max(vw_s, 100.0), atm * vw_a, warr * WARRANT_STRIKE
        uses = (bought.get(cur, 0.0) + cash[cur]["cash"] - cash[prev]["cash"]
                + sata[prev] * DAILY_DIVIDEND * 5 + WEEKLY_BURN)
        rows.append({"week": cur, "asst_vwap": vw_a, "sata_vwap": vw_s, "sata_usd": sata_usd,
                     "common_shares": atm, "common_pct": atm / s0["fully_diluted_shares"], "common_usd": atm_usd,
                     "warrant_shares": warr, "warrant_usd": warr_usd, "sources": sata_usd + atm_usd + warr_usd,
                     "uses": uses, "btc_bought": bought.get(cur, 0.0)})
    df = pd.DataFrame(rows).set_index("week")
    df["gap"] = df["sources"] - df["uses"]
    return df


def summary(df: pd.DataFrame, since: str = "2026-08-21", recent: int = 3) -> dict:
    """Averages since SATA issuance resumed at par (week ending 8/21/26), and over the last few weeks."""
    w, r = df.loc[since:], df.tail(recent)
    new = w["sata_usd"].sum() + w["common_usd"].sum()
    return {"weeks": len(w), "sata_usd_avg": w["sata_usd"].mean(), "common_usd_avg": w["common_usd"].mean(),
            "common_pct_avg": w["common_pct"].mean(), "common_pct_recent": r["common_pct"].mean(),
            "sata_share_of_new_capital": w["sata_usd"].sum() / new if new else float("nan"),
            "max_abs_gap": df["gap"].abs().max()}
