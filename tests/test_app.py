"""The model page renders end to end on the fixture snapshot (no network): the published target for every viewer,
each viewer's own scenario, and the password-locked owner panel."""
from dataclasses import replace

import pytest
from streamlit.testing.v1 import AppTest

from model import levers, published, state, valuation

OWNER_TEST_PASSWORD = "test-owner-pass"  # a test value; the real one is the OWNER_PASSWORD secret


@pytest.fixture
def snap(calc, base):
    return state.from_payloads(calc, base).with_prices(85224.79, 30.03)


@pytest.fixture
def pub(snap):
    lv = replace(levers.load(), k_start=round(valuation.implied_k(snap), 2))
    path, _, _ = valuation.solve_market(snap, lv, lv.base_cagr)
    return published.make(lv, snap, valuation.price_target(path, snap, lv.pt_date, lv)["price_target"], "@WallyXIX")


def _app(monkeypatch, snap, pub):
    monkeypatch.setattr(state, "load", lambda **_: snap)
    monkeypatch.setattr(published, "load", lambda *a, **k: pub)
    return AppTest.from_file("../panel/model_page.py", default_timeout=90)


def _hero(at) -> str:
    return next(h.proto.body for h in at.get("html") if "vg-hero" in h.proto.body)


def _lever(at, name: str):
    return next(w for w in at.sidebar.number_input if w.key and w.key.endswith("." + name))


def _button(at, label: str):
    return next(b for b in at.button if b.label == label)


def test_model_page_renders(monkeypatch, snap):
    """Nothing published: config/levers.yaml on the latest data."""
    at = _app(monkeypatch, snap, None).run()
    assert not at.exception
    bodies = [h.proto.body for h in at.get("html")]
    hero = _hero(at)
    assert "Price target" in hero and "Dec 31, 2028" in hero        # the target is the hero
    assert "Implied mNAV" not in hero                               # ...and only the target and the gain
    assert any("vg-facts" in b and "Implied mNAV" in b and "vg-tip" in b for b in bodies)  # explained, folded away
    assert any("strive today" in b.lower() for b in bodies)
    assert any("$14.09" in b and "2.13×" in b for b in bodies)      # today's cards match Strive's dashboard
    assert any("vg-ledger" in b and "Growth premium" in b for b in bodies)
    assert [e.label for e in at.main.expander][:2] == ["Key assumptions", "Full model detail"]  # both start folded
    assert "SATA issuance" in [t.label for t in at.tabs]           # the SATA schedule, year by year
    assert "PT history" in [t.label for t in at.tabs]              # every published target
    assert all(e.proto.expanded for e in at.sidebar.expander if e.label != "Owner")  # lever sections start open


def test_viewers_open_on_the_published_target(monkeypatch, snap, pub):
    at = _app(monkeypatch, snap, pub).run()
    assert not at.exception
    hero = _hero(at)
    assert f"${pub.price_target:,.2f}" in hero and "by @WallyXIX" in hero and "Your scenario" not in hero
    assert _lever(at, "k_start.published").value == pytest.approx(pub.levers.k_start)  # the k when it was set

    _lever(at, "common").set_value(0.75).run()                      # a viewer's edit is their own scenario
    hero = _hero(at)
    assert "Your scenario" in hero and f"The published target is ${pub.price_target:,.2f}" in hero

    _button(at, "Reset to the published target").click().run()     # ...until they reset
    assert "by @WallyXIX" in _hero(at) and _lever(at, "common").value == pytest.approx(0.5)


def test_owner_panel_needs_the_password(monkeypatch, snap, pub):
    monkeypatch.setenv("OWNER_PASSWORD", OWNER_TEST_PASSWORD)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    saved = []
    monkeypatch.setattr(published, "save_local", lambda p, *a, **k: saved.append(p))
    at = _app(monkeypatch, snap, pub).run()
    assert not [b for b in at.button if b.label == "Set as the live price target"]

    at.text_input(key="owner_pw").input("wrong guess")
    _button(at, "Unlock").click().run()
    assert any("Wrong password" in e.value for e in at.error)
    assert not [b for b in at.button if b.label == "Set as the live price target"]

    at.text_input(key="owner_pw").input(OWNER_TEST_PASSWORD)
    _button(at, "Unlock").click().run()
    _lever(at, "common").set_value(0.75).run()
    _button(at, "Set as the live price target").click().run()
    assert not at.exception
    assert saved and saved[0].levers.common_weekly_pct == pytest.approx(0.0075) and saved[0].set_by == "@WallyXIX"
    assert len(saved[0].history) == len(pub.history) + 1           # publishing adds a line to the PT history
    assert saved[0].history[-1]["price_target"] == pytest.approx(saved[0].price_target)
    assert any("not saved to GitHub" in w.value for w in at.warning)  # no token: this server only, and it says so


def test_pt_history_lists_the_official_target_first(monkeypatch, snap, pub):
    path, _, _ = valuation.solve_market(pub.state, pub.levers, pub.levers.base_cagr)
    v = valuation.price_target(path, pub.state, pub.levers.pt_date, pub.levers)
    pub = replace(pub, history=[published.entry(pub, v, 196000.0)])
    at = _app(monkeypatch, snap, pub).run()
    assert not at.exception
    frames = [d.value for d in at.dataframe]
    hist = next(f for f in frames if "Upside when set" in f.index)
    assert list(hist.columns)[0].endswith("(official)") and hist.iloc[0, 0].startswith(f"${pub.price_target:,.2f}")


def test_owner_lockout_and_auto_lock(monkeypatch, snap, pub):
    import time

    from panel import common
    monkeypatch.setenv("OWNER_PASSWORD", OWNER_TEST_PASSWORD)
    guard = common._unlock_guard()
    guard["locked_until"] = time.time() + 600          # as if someone had been guessing
    try:
        at = _app(monkeypatch, snap, pub).run()
        at.text_input(key="owner_pw").input(OWNER_TEST_PASSWORD)
        _button(at, "Unlock").click().run()
        assert any("Too many wrong passwords" in e.value for e in at.error)   # even the right password waits
        assert not [b for b in at.button if b.label == "Lock"]
    finally:
        guard["locked_until"], guard["fails"] = 0.0, []

    at = _app(monkeypatch, snap, pub).run()
    at.text_input(key="owner_pw").input(OWNER_TEST_PASSWORD)
    _button(at, "Unlock").click().run()
    assert [b for b in at.button if b.label == "Lock"]
    at.session_state[common.OWNER_KEY] = time.time() - common.OWNER_IDLE - 1   # left unlocked too long
    at.run()
    assert not [b for b in at.button if b.label == "Lock"] and [w for w in at.text_input if w.key == "owner_pw"]


def test_list_inputs_are_capped_and_bounded():
    from panel import common
    vals = common._floats(", ".join(str(x) for x in range(5, 500, 5)), [0.4], 0.01, lo=-0.5, hi=2.0, most=6)
    assert len(vals) == 6 and all(-0.5 <= v <= 2.0 for v in vals)


def test_publishing_without_a_password_secret_is_off(monkeypatch, snap, pub):
    monkeypatch.delenv("OWNER_PASSWORD", raising=False)
    at = _app(monkeypatch, snap, pub).run()
    assert not [w for w in at.text_input if w.key == "owner_pw"]
