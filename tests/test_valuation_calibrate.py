from dataclasses import replace
from datetime import date

import pytest

from model import calibrate, engine, metrics, valuation
from model.sources.filings import weeks_from_feed


def test_reproduces_td_cowens_44():
    # TD Cowen, Sep 21 2026: 32,105 BTC at YE26 x $97.5k, less ~$1.64B SATA plus ~$0.30B cash, plus 3x the FY26
    # BTC $ Gain (70.1% BTC Yield on the ~12,675 BTC start incl. Semler's), over today's 100.78M FD shares -> $44
    v = valuation.value_per_share(32105 * 97500 - 1.64e9 + 0.30e9, 12675 * 0.701, 97500, 100776795, 3)
    assert round(v, 2) == 43.55


def test_implied_k_on_the_actual_trailing_twelve_months(st):
    # 9/30/25 -> 9/25/26: 5,886 BTC, sats per share 13,945 -> 27,250 (95% BTC Yield), ~$4.75 a share at $85,225
    assert round(valuation.implied_k(st), 2) == 3.36


def test_price_target_by_hand(st, lv):
    df = engine.run(st, lv, 0.40)
    a, b = engine.at(df, date(2027, 12, 31)), engine.at(df, date(2028, 12, 31))
    y = b.sats_per_share / a.sats_per_share - 1
    v = valuation.price_target(df, st, date(2028, 12, 31), lv)
    assert v["btc_yield"] == pytest.approx(y)
    assert v["price_target"] == pytest.approx(b.ntav_per_share + 3 * a.btc * y * b.btc_price / b.fd_shares)
    assert v["premium_sata"] + v["premium_common"] == pytest.approx(v["growth_premium"])


def test_fy2026_is_stitched_from_history_with_semler(st, lv):
    df = engine.run(st, lv, 0.40)
    v = valuation.price_target(df, st, date(2026, 12, 31), lv)
    h = st.history["fy_start"]
    sats0 = h["btc"] / h["fd_shares"] * 1e8                       # 17,037 sats: Strive's own Q1-26 starting point
    y = engine.at(df, date(2026, 12, 31)).sats_per_share / sats0 - 1
    assert round(sats0) == 17037 and v["btc_yield"] == pytest.approx(y)
    assert v["btc_gain"] == pytest.approx((h["btc"] + valuation.SEMLER_BTC) * y)
    assert v["premium_sata"] is None and v["net_target"] is None  # the year starts before the forecast


def test_attribution_adds_up_to_the_price_target(st, lv):
    a = valuation.attribution(st, lv, 0.40)
    assert (a["start"] + a[valuation.PARTS].sum(axis=1) - a["end"]).abs().max() < 1e-9
    steps = ["btc_move", "amplification", "sata_dividends", "issuance", "op_costs"]
    assert (a["start"] + a[steps].sum(axis=1) - a["ntav_end"]).abs().max() < 1e-9
    split = a.dropna(subset=["premium_sata"])
    assert (split["premium_sata"] + split["premium_common"] - split["growth_premium"]).abs().max() < 1e-9
    assert list(a.index) == [date(y, 12, 31) for y in range(2026, 2032)]
    assert a["start"].iloc[0] == pytest.approx(metrics.ntav_per_share(st))
    assert a["today_price"].iloc[0] == pytest.approx(30.03)


def test_sata_dividends_are_their_own_step(st, lv):
    a = valuation.attribution(st, lv, 0.40)
    t = date(2028, 12, 31)
    run = engine.run(st, lv, 0.40, common=False, warrants=False, burn=False)
    paid = run.loc[:"2028-12-31", "dividends"].sum() / st.fd_shares
    assert a.loc[t, "sata_dividends"] == pytest.approx(-paid) and paid > 0
    assert a.loc[t, "op_costs"] > a.loc[t, "sata_dividends"]  # the burn is far smaller than the dividends


def test_btc_move_is_net_assets_tracking_btc(st, lv):
    a = valuation.attribution(st, lv, 0.40)
    n0 = metrics.ntav_per_share(st)
    assert a.loc[date(2027, 12, 31), "btc_move"] == pytest.approx(n0 * (140_000 / st.btc_price - 1))


def test_more_sata_raises_the_target_and_its_sata_premium(st, lv):
    lo = valuation.price_target(engine.run(st, replace(lv, sata_growth=0.0), 0.4), st, lv.pt_date, lv)
    hi = valuation.price_target(engine.run(st, replace(lv, sata_growth=1.0), 0.4), st, lv.pt_date, lv)
    assert hi["price_target"] > lo["price_target"] and hi["premium_sata"] > lo["premium_sata"]


def test_price_target_table_rises_with_k_and_cagr(st, lv):
    t = valuation.table(st, lv)
    body = t["price_target"].iloc[1:]  # skip the "today's price" row
    assert (body.diff().iloc[1:] > 0).all().all()       # higher k, higher target
    assert (body.T.diff().iloc[1:] > 0).all().all()     # higher CAGR, higher target
    assert t["price_target"].index[0] == f"{t['k_today']:.2f}x (today's price)"
    base = valuation.price_target(engine.run(st, lv, 0.40), st, lv.pt_date, lv)["price_target"]
    assert t["price_target"].loc["3x", "40% CAGR"] == pytest.approx(base)


def test_calibration_reproduces_the_six_week_averages(base, feed, bars):
    df = calibrate.weekly(base, weeks_from_feed(feed), bars)
    s = calibrate.summary(df)
    assert s["weeks"] == 6
    assert round(s["sata_usd_avg"] / 1e6, 1) == 72.7
    assert round(s["common_usd_avg"] / 1e6, 1) == 36.4
    assert round(s["common_pct_avg"], 4) == 0.0186
    assert round(s["common_pct_recent"], 4) == 0.0050
    assert round(s["sata_share_of_new_capital"], 2) == 0.67
    assert s["max_abs_gap"] < 2e6  # sources and uses agree every week
