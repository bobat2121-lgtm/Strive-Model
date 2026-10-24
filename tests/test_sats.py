"""SATS is a preferred claim, with separate net cash proceeds and a fixed stated-value coupon."""
from dataclasses import replace
from datetime import date

import pytest

from model import engine, metrics, state, valuation


def test_sats_reduces_ntav_and_increases_ev_and_dividend_cost(st):
    issued = replace(st, sats_notional=700e6, sats_rate=0.15)
    assert metrics.ntav(issued) == pytest.approx(metrics.ntav(st) - 700e6)
    assert metrics.enterprise_value(issued, st.share_price) == pytest.approx(
        metrics.enterprise_value(st, st.share_price) + 700e6)
    assert metrics.amplification(issued) == pytest.approx(metrics.amplification(st) + 700e6 / metrics.btc_nav(st))
    assert metrics.summary(issued, st.share_price, st.sata_rate)["annual_sats_dividends"] == 105e6
    assert metrics.annual_dividends(issued, st.sata_rate) == pytest.approx(st.sata_rate * st.sata_notional + 105e6)
    assert metrics.dividend_coverage_years(issued, st.sata_rate) < metrics.dividend_coverage_years(st, st.sata_rate)


def test_sats_liquidation_claim_has_par_floor_and_supports_higher_claim(st):
    issued = replace(st, sats_notional=700e6, sats_liquidation_preference=630e6)
    assert metrics.sats_claim(issued) == 700e6
    assert metrics.sats_claim(replace(issued, sats_liquidation_preference=735e6)) == 735e6


def test_ipo_supplement_preserves_btc_and_adds_net_cash_only_once(st):
    assert state.with_sats_ipo(st, date(2026, 10, 19)) == st
    issued = state.with_sats_ipo(st, date(2026, 10, 24))
    assert issued.btc == st.btc and issued.fd_shares == st.fd_shares
    assert issued.cash == st.cash + 608.15e6
    assert issued.sats_notional == 700e6 and issued.sats_rate == 0.15
    assert metrics.ntav(issued) == pytest.approx(metrics.ntav(st) - 91.85e6)
    assert state.with_sats_ipo(issued, date(2026, 11, 1)) == issued
    reported = replace(st, as_of=date(2026, 10, 23), cash_as_of=date(2026, 10, 23), cash=1e9)
    assert state.with_sats_ipo(reported, date(2026, 10, 24)).cash == reported.cash


def test_reported_sats_is_never_added_again(calc, base):
    row = max(calc["rows"], key=lambda r: r["date"])
    row.update(date="2026-10-24", cash=900e6, preferredStockMarketCap=1_919_318_000)
    calc["preferredStocks"].append({"ticker": "SATS", "date": "2026-10-20", "notional_value": 700e6,
                                     "dividend_rate": 0.15, "liquidation_preference": 735e6})
    st = state.from_payloads(calc, base)
    assert st.sata_notional == 1_219_318_000 and st.sats_notional == 700e6
    assert metrics.sats_claim(st) == 735e6
    assert state.with_sats_ipo(st, date(2026, 10, 24)) == st


def test_future_preferred_record_cannot_leak_into_historical_snapshot(calc, base):
    calc["preferredStocks"].append({"ticker": "SATS", "date": "2026-10-20", "notional_value": 700e6})
    assert state.from_payloads(calc, base).sats_notional == 0


def test_post_ipo_cash_with_stale_shares_does_not_add_proceeds_twice(calc, base):
    row = max(calc["rows"], key=lambda r: r["date"])
    row.update(date="2026-10-24", cash=900e6)
    base["cashDebt"].append({"date": "2026-10-23", "cash": 900e6, "debt": row["debt"],
                             "marketable_securities": row["marketableSecurities"]})
    st = state.from_payloads(calc, base)
    assert st.as_of < state.SATS_IPO_DATE and st.cash_as_of == date(2026, 10, 23)
    updated = state.with_sats_ipo(st, st.price_date)
    assert updated.cash == 900e6 and updated.sats_notional == 700e6


def test_new_shares_with_pre_ipo_cash_still_adds_proceeds(calc, base):
    row = max(calc["rows"], key=lambda r: r["date"])
    row["date"] = "2026-10-24"
    base["shares"].append({**base["shares"][0], "date": "2026-10-23"})
    st = state.from_payloads(calc, base)
    assert st.as_of > state.SATS_IPO_DATE and st.cash_as_of < state.SATS_IPO_DATE
    assert state.with_sats_ipo(st, st.price_date).cash == row["cash"] + 608.15e6


def test_unmatched_cash_provenance_cannot_double_count_proceeds(calc, base):
    row = max(calc["rows"], key=lambda r: r["date"])
    row.update(date="2026-10-24", cash=900e6)
    st = state.from_payloads(calc, base)
    assert st.cash_as_of is None
    updated = state.with_sats_ipo(st, st.price_date)
    assert updated.cash == 900e6 and updated.sats_notional == 700e6
    assert "unresolved" in updated.sources["SATS"]


def test_known_preferred_with_stale_cash_receives_cash_only_supplement(calc, base):
    row = max(calc["rows"], key=lambda r: r["date"])
    row["date"] = "2026-10-24"
    calc["preferredStocks"].append({"ticker": "SATS", "date": "2026-10-20", "notional_value": 700e6})
    st = state.from_payloads(calc, base)
    updated = state.with_sats_ipo(st, st.price_date)
    assert updated.sats_notional == 700e6 and updated.cash == st.cash + 608.15e6
    assert state.with_sats_ipo(updated, st.price_date) == updated


def test_ipo_projection_uses_net_proceeds_without_diluting_common(st, lv):
    before = replace(st, btc_price=100_000, share_price=10, cash=0, securities=0,
                     sata_notional=0, sata_rate=0, warrants=0)
    fixed = replace(lv, horizon_end=date(2026, 12, 31), ye_btc_price=100_000, sata_weekly_usd=0)
    df = engine.run(before, fixed, 0, common=False, warrants=False, burn=False)
    close = df.loc["2026-10-20"]
    assert close.raised_sats == 608.15e6 and close.sats_new_notional == 700e6
    assert close.sats_issuance_cost == 91.85e6 and close.sats_dividends == 0
    assert close.cash == 157.5e6  # 18 months of the $105m annual coupon, held as an asset
    assert close.fd_shares == st.fd_shares and close.sats_notional == 700e6
    assert close.btc - before.btc == pytest.approx((608.15e6 - 157.5e6) / 100_000)
    assert close.ntav_per_share * close.fd_shares == pytest.approx(metrics.ntav(before) - 91.85e6)
    assert df.sats_dividends.sum() == pytest.approx(105e6 * 70 / 360)
    assert df.raised_sats.sum() == 608.15e6 and df.sats_new_notional.sum() == 700e6
    assert df.sats_dividends.loc[:"2026-10-20"].sum() == 0


def test_current_sats_stays_outstanding_without_repeat_ipo(st, lv):
    current = state.with_sats_ipo(replace(st, price_date=date(2026, 10, 24)), date(2026, 10, 24))
    df = engine.run(current, replace(lv, horizon_end=date(2026, 12, 31)), 0.4)
    assert df.sats_notional.eq(700e6).all() and df.raised_sats.sum() == 0
    assert df.iloc[0].cash == current.cash


def test_sats_annual_coupon_uses_twelve_thirty_day_months():
    assert engine.sats_year_fraction(date(2026, 12, 31), date(2027, 12, 31)) == 1
    assert engine.sats_year_fraction(date(2027, 12, 31), date(2028, 12, 31)) == 1  # leap year too
    assert engine.sats_year_fraction(date(2027, 1, 31), date(2027, 2, 28)) == pytest.approx(28 / 360)


def test_sats_attribution_and_funding_premiums_reconcile(st, lv):
    lv = replace(lv, horizon_end=date(2028, 12, 31), market_mnav_mode="manual")
    a = valuation.attribution(st, lv, 0.4)
    assert (a["start"] + a[valuation.PARTS].sum(axis=1) - a["end"]).abs().max() < 1e-9
    assert a.sats_issuance_cost.iloc[0] == pytest.approx(-91.85e6 / st.fd_shares)
    assert (a.sats_dividends < 0).all()
    row = a.iloc[-1]
    assert row.premium_sata + row.premium_sats + row.premium_common == pytest.approx(row.growth_premium)


def test_legacy_post_ipo_state_is_normalized_before_valuation(st, lv):
    legacy = replace(st, price_date=date(2026, 10, 24))
    current = state.with_sats_ipo(legacy, legacy.price_date)
    lv = replace(lv, horizon_end=date(2028, 12, 31))
    assert valuation.implied_k(legacy) == pytest.approx(valuation.implied_k(current))
    df, _, settled = valuation.solve_market(legacy, lv, 0.4)
    assert settled
    assert df.mnav.iloc[0] == pytest.approx(metrics.mnav(current, current.share_price))
    assert df.ntav_per_share.iloc[0] == pytest.approx(metrics.ntav_per_share(current))
    a = valuation.attribution(legacy, lv, 0.4)
    assert a.start.iloc[0] == pytest.approx(metrics.ntav_per_share(current))
    assert (a.start + a[valuation.PARTS].sum(axis=1) - a.end).abs().max() < 1e-9
