"""Golden numbers: every metric must match what Strive itself publishes."""
import pytest

from model import metrics
from model.metrics import Book


def test_matches_the_strive_dashboard_on_oct_4(st):
    # strive.com/treasury, 10/4/26, ASST $30.03: the panel the model's mNAV definition comes from
    s = metrics.summary(st, st.share_price, st.sata_rate)
    assert round(s["btc_nav"] / 1e9, 2) == 2.34
    assert round(s["tav"] / 1e9, 2) == 2.64
    assert round(s["ntav"] / 1e9, 2) == 1.42
    assert round(s["ntav_per_share"], 2) == 14.09
    assert round(s["mnav"], 2) == 2.13                    # "Multiple to Net Treasury Asset Value"
    assert round(s["enterprise_value"] / 1e9, 2) == 3.95
    assert round(s["ev_to_tav"], 2) == 1.50
    assert round(s["accretion_premium"], 3) == 0.293      # "Common Equity Accretion Premium"
    assert round(s["dividend_coverage_years"], 1) == 16.6  # /api/treasury "totalDividendCoverage"


def test_ev_to_btc_nav_matches_the_api_field(st):
    # the API's evMnav at the same prices
    assert metrics.ev_to_btc_nav(st, 30.03) == pytest.approx(1.686480915448094, rel=1e-9)


def test_x_agent_fixture_sep_27():
    # X Agent's golden test: 9/18 balance sheet, ASST $29.44, BTC $84,670.07, evMnav 1.6972
    b = Book(btc=26355.180562789996, btc_price=84670.07, fd_shares=100144713, sata_notional=1118416000,
             cash=229600000, securities=49748000)
    assert metrics.ev_to_btc_nav(b, 29.44) == pytest.approx(1.6972, abs=5e-5)


def test_amplification_at_june_30():
    # Q2-26 release: 67.2% with 19,864 BTC at $58,631 and $783.0M of SATA, no debt
    b = Book(btc=19864, btc_price=58631, fd_shares=84653128, sata_notional=783.0e6, cash=145.5e6, securities=42.9e6)
    assert round(metrics.amplification(b), 3) == 0.672


def test_sats_per_share_and_inverse_price(st):
    assert round(metrics.sats_per_share(st)) == 27250  # strive.com, 9/25
    assert metrics.mnav(st, metrics.price_at(st, 1.75)) == pytest.approx(1.75)
