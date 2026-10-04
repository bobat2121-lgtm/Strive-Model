"""The model page renders end to end on the fixture snapshot (no network)."""
from streamlit.testing.v1 import AppTest

from model import state


def test_model_page_renders(monkeypatch, calc, base):
    snap = state.from_payloads(calc, base).with_prices(85224.79, 30.03)
    monkeypatch.setattr(state, "load", lambda **_: snap)
    at = AppTest.from_file("../panel/model_page.py", default_timeout=90).run()
    assert not at.exception
    bodies = [h.proto.body for h in at.get("html")]
    hero = next(b for b in bodies if "vg-hero" in b)
    assert "Price target" in hero and "Dec 31, 2028" in hero        # the target is the hero
    assert any("strive today" in b.lower() for b in bodies)
    assert any("$14.09" in b and "2.13×" in b for b in bodies)      # today's cards match Strive's dashboard
    assert any("vg-ledger" in b and "Growth premium" in b for b in bodies)
    assert [e.label for e in at.expander][0] == "Full model detail"  # everything else is folded away
