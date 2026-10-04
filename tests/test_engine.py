from dataclasses import replace
from datetime import date

import pandas as pd
import pytest

from model import engine, metrics


def test_btc_path_hits_the_anchor_then_compounds(st, lv):
    df = engine.run(st, lv, 0.40)
    assert engine.at(df, date(2026, 12, 31)).btc_price == pytest.approx(100_000)
    assert engine.at(df, date(2027, 12, 31)).btc_price == pytest.approx(140_000)
    assert engine.at(df, date(2028, 12, 31)).btc_price == pytest.approx(196_000)
    assert df["btc_price"].iloc[0] == st.btc_price


def test_schedule_is_weekly_plus_year_ends():
    s = engine.schedule(date(2026, 10, 4), date(2027, 1, 20))
    assert s[:3] == [date(2026, 10, 4), date(2026, 10, 11), date(2026, 10, 18)]
    assert date(2026, 12, 31) in s and s[-1] == date(2027, 1, 20)


def test_first_week_by_hand(st, lv):
    df = engine.run(st, lv, 0.40)
    p1 = df["btc_price"].iloc[1]
    m0 = metrics.mnav(st, st.share_price)
    px = metrics.price_at(metrics.Book(st.btc, p1, st.fd_shares, st.sata_notional, st.cash, st.securities), m0)
    new_sh = st.fd_shares * 0.005
    cash = st.cash + 70e6 + new_sh * px - 0.13 * st.sata_notional * 7 / 365 - 1.2e6
    reserve = 18 / 12 * 0.13 * (st.sata_notional + 70e6)
    r = df.iloc[1]
    assert r.cash == pytest.approx(reserve)
    assert r.btc == pytest.approx(st.btc + (cash - reserve) / p1)
    assert r.fd_shares == pytest.approx(st.fd_shares + new_sh)
    assert r.sata_notional == pytest.approx(st.sata_notional + 70e6)


def test_sata_demand_is_flat_then_grows(lv):
    assert engine.sata_per_week(lv, date(2026, 12, 31)) == 70e6                            # through the switch: flat
    assert engine.sata_per_week(lv, date(2027, 12, 31)) == pytest.approx(70e6 * 1.5)       # one year on: +50%
    assert engine.sata_per_week(lv, date(2028, 12, 31)) == pytest.approx(70e6 * 1.5 ** 2)
    assert engine.sata_per_week(replace(lv, sata_growth=0.0), date(2029, 6, 30)) == 70e6


def test_sata_rate_holds_or_glides(st, lv):
    static = engine.run(st, lv, 0.4)
    assert (static.sata_rate == 0.13).all()
    glide = engine.run(st, replace(lv, sata_rate_target=0.10, sata_rate_glide_to=date(2027, 12, 31)), 0.4)
    assert glide.sata_rate.iloc[0] == pytest.approx(0.13)
    assert 0.10 < engine.at(glide, date(2027, 6, 30)).sata_rate < 0.13
    w = glide.loc[:pd.Timestamp(date(2028, 6, 30))]
    r, prev, days = w.iloc[-1], w.iloc[-2], (w.index[-1] - w.index[-2]).days
    assert r.sata_rate == pytest.approx(0.10)
    assert r.dividends == pytest.approx(0.10 * prev.sata_notional * days / 365)


def test_cash_is_conserved(st, lv):
    df = engine.run(st, lv, 0.30, 1.6)
    inflow = (df.raised_sata + df.raised_common + df.raised_warrants - df.dividends - df.opex).sum()
    assert inflow == pytest.approx(df.cash.iloc[-1] - st.cash + df.btc_bought_usd.sum(), rel=1e-9)


def test_sata_at_par_leaves_ntav_per_share_unchanged_but_for_dividends(st, lv):
    # BTC flat, only SATA issuance: each week NTAV falls by exactly the dividends paid
    flat = replace(lv, ye_btc_price=st.btc_price)
    df = engine.run(st, flat, 0.0, common=False, warrants=False, burn=False)
    ntav = df.ntav_per_share * df.fd_shares
    assert (ntav.diff().iloc[1:] + df.dividends.iloc[1:]).abs().max() < 1e-3
    assert df.amplification.iloc[-1] > df.amplification.iloc[0]  # BTC flat: amplification climbs with SATA


def test_common_sold_above_ntav_is_accretive(st, lv):
    flat = replace(lv, ye_btc_price=st.btc_price, sata_rate=0.0)
    df = engine.run(st, flat, 0.0, 2.0, sata=False, warrants=False, burn=False)
    r0, r1 = df.iloc[0], df.iloc[1]
    n0, dn = r0.fd_shares, r1.new_shares
    px = r1.raised_common / dn
    assert r1.ntav_per_share == pytest.approx((r0.ntav_per_share * n0 + px * dn) / (n0 + dn))
    assert r1.ntav_per_share > r0.ntav_per_share


def test_warrants_exercise_only_in_the_money(st, lv):
    itm = engine.run(st, lv, 0.4, common=False)
    otm = engine.run(st, replace(lv, warrant_strike=1000.0), 0.4, common=False)
    assert itm.warrant_shares.sum() == pytest.approx(st.warrants)
    assert itm.raised_warrants.sum() == pytest.approx(st.warrants * 27)
    assert otm.warrant_shares.sum() == 0 and otm.fd_shares.iloc[-1] == st.fd_shares


def test_btc_is_sold_only_when_the_reserve_runs_dry(st, lv):
    df = engine.run(st, replace(lv, net_cash_burn_weekly_usd=50e6), 0.4, sata=False, common=False, warrants=False)
    assert (df.btc_bought_usd < 0).any() and (df.cash >= -1e-6).all()
