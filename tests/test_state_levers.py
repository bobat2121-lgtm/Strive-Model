from datetime import date

import pytest

from model import levers, state


def test_snapshot_from_strive_payloads(calc, base):
    s = state.from_payloads(calc, base)
    assert s.as_of == date(2026, 9, 25)                    # the 9/28 8-K's balance date
    assert s.price_date == date(2026, 10, 4)
    assert s.btc == pytest.approx(27461.787, abs=1e-3)
    assert s.fd_shares == 100776795
    assert s.sata_notional == 1219318000 and s.sata_rate == 0.13
    assert (s.cash, s.securities, s.debt) == (248800000, 49763000, 0)
    assert s.warrants == 25349806
    fy, ya = s.history["fy_start"], s.history["year_ago"]
    assert (fy["date"], round(fy["btc"], 2), fy["fd_shares"]) == (date(2025, 12, 31), 7626.81, 44766899)
    assert (ya["date"], round(ya["btc"])) == (date(2025, 9, 30), 5886)


def test_snapshot_needs_priced_rows(calc, base):
    calc["rows"] = [dict(r, sharePrice=None) for r in calc["rows"]]
    with pytest.raises(ValueError):
        state.from_payloads(calc, base)


def test_config_defaults_match_code_defaults():
    assert levers.load() == levers.Levers()


def test_percents_become_fractions(tmp_path):
    p = tmp_path / "l.yaml"
    p.write_text("btc: {cagr_bands_pct: [25, 60]}\nsata: {rate_pct: 12.5}\ncommon: {weekly_pct: 1}\n"
                 "mnav: {target: 1.8}\n")
    lv = levers.load(p)
    assert lv.cagr_bands == [0.25, 0.60] and lv.base_cagr == 0.60  # no base given: the middle band
    assert (lv.sata_rate, lv.common_weekly_pct, lv.mnav_target) == (0.125, 0.01, 1.8)
