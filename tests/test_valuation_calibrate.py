from dataclasses import replace
from datetime import date

import pytest

from model import calibrate, engine, metrics, valuation
from model.sources.filings import weeks_from_feed


def test_attribution_adds_up_to_the_price_target(st, lv):
    a = valuation.attribution(st, lv, 0.40)
    assert (a["start"] + a[valuation.PARTS].sum(axis=1) - a["end"]).abs().max() < 1e-9
    steps = ["btc_move", "amplification", "sata_dividends", "issuance", "op_costs"]
    assert (a["start"] + a[steps].sum(axis=1) - a["ntav_end"]).abs().max() < 1e-9
    assert list(a.index) == [date(y, 12, 31) for y in range(2026, 2031)]  # each needs a forward year inside the forecast
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


def test_price_target_by_hand(st, lv):
    df = engine.run(st, lv, 0.40)
    t, t1 = date(2028, 12, 31), date(2029, 12, 31)
    a, b = engine.at(df, t), engine.at(df, t1)
    net_y = (b.ntav_per_share / b.btc_price) / (a.ntav_per_share / a.btc_price) - 1
    v = valuation.price_target(df, t, lv)
    assert v["forward_yield"] == pytest.approx(net_y)
    assert v["price_target"] == pytest.approx(a.ntav_per_share * (1 + 3 * net_y))
    gross = valuation.price_target(df, t, replace(lv, gain_basis="gross"))
    gross_y = b.sats_per_share / a.sats_per_share - 1
    assert gross["price_target"] == pytest.approx(a.ntav_per_share + 3 * a.btc * gross_y * a.btc_price / a.fd_shares)


def test_implied_k_reprices_today(st, lv):
    df = engine.run(st, lv, 0.40)
    k = valuation.implied_k(df, lv)
    _, g = valuation.forward_gain(df, st.price_date)
    assert metrics.ntav_per_share(st) + k * g == pytest.approx(30.03)


def test_more_amplification_raises_the_target(st, lv):
    lo = valuation.price_target(engine.run(st, replace(lv, sata_pct_of_btc_nav=None), 0.4), lv.pt_date, lv)
    hi = valuation.price_target(engine.run(st, replace(lv, sata_pct_of_btc_nav=0.015), 0.4), lv.pt_date, lv)
    assert hi["amplification"] > lo["amplification"] and hi["price_target"] > lo["price_target"] * 1.3


def test_price_target_table_rises_with_k_and_cagr(st, lv):
    t = valuation.table(st, lv)
    body = t["price_target"].iloc[1:]  # skip the "today's price" row
    assert (body.diff().iloc[1:] > 0).all().all()       # higher k, higher target
    assert (body.T.diff().iloc[1:] > 0).all().all()     # higher CAGR, higher target
    assert t["price_target"].index[0] == f"{t['k_today']:.2f}x (today's price)"
    base = valuation.price_target(engine.run(st, lv, 0.40), lv.pt_date, lv)["price_target"]
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
