"""Command line: `python -m model` prints today's snapshot, the levers, the price tables and the attribution.

    python -m model                 live strive.com data (falls back to the cache)
    python -m model --offline       cached data only
    python -m model --live-prices   Coinbase BTC spot + latest Yahoo ASST close instead of the dashboard's prices
    python -m model calibrate       weekly SATA / common issuance from 8-K share counts and VWAP
"""
from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta

import pandas as pd

from model import calibrate, engine, levers, metrics, state, valuation


def usd(x: float) -> str:
    a = abs(x)
    s = f"${a / 1e9:.2f}B" if a >= 1e9 else f"${a / 1e6:.1f}M" if a >= 1e4 else f"${a:,.0f}"
    return "-" + s if x < 0 else s


def show_today(st: state.State, rate: float) -> None:
    s = metrics.summary(st, st.share_price, rate)
    print(f"STRIVE (ASST) — balance sheet as of {st.as_of} (weekly 8-K), prices {st.price_date}")
    for k, v in st.sources.items():
        print(f"  source · {k}: {v}")
    print()
    lines = [
        ("BTC held", f"{st.btc:,.0f}", "BTC price", f"${st.btc_price:,.0f}"),
        ("ASST", f"${st.share_price:.2f}", "FD shares", f"{st.fd_shares / 1e6:.2f}M"),
        ("SATA notional", f"{usd(st.sata_notional)} @ {rate:.2%}", "Cash + STRC", usd(st.cash + st.securities)),
        ("NTAV / share", f"${s['ntav_per_share']:.2f}", "mNAV", f"{s['mnav']:.2f}x"),
        ("Amplification", f"{s['amplification']:.1%}", "Sats / share", f"{s['sats_per_share']:,.0f}"),
        ("Accretion premium", f"{s['accretion_premium']:.1%}", "Dividend coverage", f"{s['dividend_coverage_years']:.1f} yrs"),
    ]
    for a, b, c, d in lines:
        print(f"  {a:<18}{b:<22}{c:<18}{d}")
    api = f"; strive.com API {st.strive_ev_mnav:.2f}x" if st.strive_ev_mnav else ""
    print(f"  (EV {usd(s['enterprise_value'])} · EV/TAV {s['ev_to_tav']:.2f}x · EV/BTC NAV {s['ev_to_btc_nav']:.2f}x{api})")


def show_levers(st: state.State, lv: levers.Levers, rate: float) -> None:
    m0 = metrics.mnav(st, st.share_price)
    bands = " / ".join(f"{g:.0%}" for g in lv.cagr_bands)
    mn = f"hold today's {m0:.2f}x" if lv.mnav_target is None else f"{m0:.2f}x -> {lv.mnav_target:.2f}x by {lv.mnav_glide_to}"
    print("\nLEVERS")
    print(f"  1 BTC        ${lv.ye_btc_price:,.0f} at {lv.ye_anchor}, then {bands} CAGR (base {lv.base_cagr:.0%})")
    later = f", then growing {lv.sata_growth:.0%} a year"
    rt = (f"{rate:.2%} static" if lv.sata_rate_target is None
          else f"{rate:.2%} -> {lv.sata_rate_target:.2%} by {lv.sata_rate_glide_to}")
    print(f"  2 SATA       {usd(lv.sata_weekly_usd)} / week through {lv.sata_switch}{later} · at $100 par · {rt} · "
          f"{lv.reserve_months:g}-month cash reserve")
    print(f"  3 Common     {lv.common_weekly_pct:.2%} of FD shares / week, sold at the market mNAV ({mn})")
    print(f"  4 Valuation  price target {lv.pt_date} = (NTAV + {lv.growth_multiple:g}x the year's BTC $ Gain) / FD shares "
          f"(TD Cowen) · table k {lv.k_table[0]:g}x-{lv.k_table[-1]:g}x · today's price implies "
          f"{valuation.implied_k(st):.2f}x")
    print(f"  Warrants     {lv.warrant_exercise:.0%} of {st.warrants / 1e6:.2f}M at ${lv.warrant_strike:g} on "
          f"{lv.warrant_date} if ASST > strike · burn {usd(lv.net_cash_burn_weekly_usd)}/week · forecast to {lv.horizon_end}")


def show_tables(st: state.State, lv: levers.Levers) -> None:
    t = valuation.table(st, lv)
    print(f"\nPRICE TARGET AT {lv.pt_date}  (rows: k on the year's BTC $ Gain; columns: BTC CAGR after {lv.ye_anchor})")
    print(t["price_target"].map(lambda v: f"${v:,.2f}").to_string())
    print("\nIMPLIED mNAV AT THE TARGET (price target / NTAV per share)")
    print(t["implied_mnav"].map(lambda v: f"{v:.2f}x").to_string())


def show_base(st: state.State, lv: levers.Levers) -> None:
    df = engine.run(st, lv, lv.base_cagr, lv.mnav_target)
    vals = {v: valuation.price_target(df, st, v, lv) for v in valuation.valuation_dates(st, lv)}
    yes = [st.price_date] + [date(y, 12, 31) for y in range(st.price_date.year, lv.horizon_end.year + 1)
                             if st.price_date < date(y, 12, 31) <= lv.horizon_end]
    print(f"\nBASE CASE ({lv.base_cagr:.0%} CAGR), YEAR BY YEAR")
    rows = []
    for d in yes:
        r, v = engine.at(df, d), vals.get(d)
        rows.append({"date": d, "BTC price": f"${r.btc_price:,.0f}", "BTC held": f"{r.btc:,.0f}",
                     "SATA": usd(r.sata_notional), "Amplif.": f"{r.amplification:.1%}",
                     "FD shares": f"{r.fd_shares / 1e6:.1f}M", "Sats/sh": f"{r.sats_per_share:,.0f}",
                     "NTAV/sh": f"${r.ntav_per_share:,.2f}", "Mkt price": f"${r.share_price:,.2f}",
                     "BTC Yield": f"{v['btc_yield']:.0%}" if v else "—",
                     "Value": f"${v['price_target']:,.2f}" if v else "—",
                     "Impl. mNAV": f"{v['implied_mnav']:.2f}x" if v else "—"})
    print(pd.DataFrame(rows).set_index("date").to_string())
    print("  Mkt price = market mNAV x NTAV/share (sets the price new common sells at); Value = (NTAV + k x the year's "
          "BTC $ Gain) / FD shares")
    if (df["btc_bought_usd"] < 0).any():
        print("  ! the dividend reserve ran dry and BTC was sold in some weeks")

    a = valuation.attribution(st, lv, lv.base_cagr)
    print(f"\nWHERE THE PRICE TARGET COMES FROM (base case, $ per share; today's price ${a['today_price'].iloc[0]:.2f})")
    cols = ["start", "btc_move", "amplification", "sata_dividends", "issuance", "op_costs", "ntav_end",
            "premium_sata", "premium_common", "growth_premium", "end"]
    out = a[cols].rename(columns={"start": "NTAV today", "btc_move": "BTC move", "amplification": "Amplification",
                                  "sata_dividends": "SATA divs", "issuance": "Issuance", "op_costs": "Op. costs",
                                  "ntav_end": "NTAV at T", "premium_sata": "SATA prem.",
                                  "premium_common": "Common prem.", "growth_premium": "Growth prem.", "end": "Value"})
    print(out.map(lambda v: "—" if pd.isna(v) else f"{v:+,.2f}").to_string())


def show_calibration(offline: bool) -> None:
    from model.sources import filings, market, strive

    base, _ = strive.base_data(offline)
    weeks, _ = filings.strive_weeks(offline)
    start, end = date(2026, 7, 1), date.today() + timedelta(days=1)
    bars = {t: market.daily_bars(t, start, end) for t in ("ASST", "SATA")}
    df = calibrate.weekly(base, weeks, bars)
    view = pd.DataFrame({"ASST VWAP": df.asst_vwap.map(lambda v: f"${v:.2f}"), "SATA": df.sata_usd.map(usd),
                         "Common": df.common_usd.map(usd), "% FD sh": df.common_pct.map(lambda v: f"{v:.2%}"),
                         "Warrants": df.warrant_usd.map(usd), "Sources": df.sources.map(usd),
                         "Uses": df.uses.map(usd), "Gap": df.gap.map(usd)})
    print("WEEKLY ISSUANCE (8-K share counts x VWAP)\n" + view.to_string())
    s = calibrate.summary(df)
    print(f"\nSince SATA reached par ({s['weeks']} weeks): SATA {usd(s['sata_usd_avg'])}/wk · common "
          f"{usd(s['common_usd_avg'])}/wk = {s['common_pct_avg']:.2%} of FD shares/wk (last 3 weeks "
          f"{s['common_pct_recent']:.2%}) · SATA {s['sata_share_of_new_capital']:.0%} of new capital · "
          f"largest sources-vs-uses gap {usd(s['max_abs_gap'])}")


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="python -m model")
    ap.add_argument("command", nargs="?", default="run", choices=["run", "calibrate"])
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--live-prices", action="store_true")
    ap.add_argument("--levers", default=str(levers.DEFAULT_PATH))
    args = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")  # Windows consoles default to cp1252
    pd.set_option("display.width", 200)
    if args.command == "calibrate":
        return show_calibration(args.offline)
    st = state.load(offline=args.offline, live_prices=args.live_prices)
    lv = levers.load(args.levers)
    rate = lv.sata_rate if lv.sata_rate is not None else st.sata_rate
    show_today(st, rate)
    show_levers(st, lv, rate)
    show_tables(st, lv)
    show_base(st, lv)


if __name__ == "__main__":
    main()
