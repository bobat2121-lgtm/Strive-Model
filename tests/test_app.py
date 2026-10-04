"""The model page renders end to end on the fixture snapshot (no network)."""
from streamlit.testing.v1 import AppTest

from model import state


def test_model_page_renders(monkeypatch, calc, base):
    snap = state.from_payloads(calc, base).with_prices(85224.79, 30.03)
    monkeypatch.setattr(state, "load", lambda **_: snap)
    at = AppTest.from_file("../panel/model_page.py", default_timeout=60).run()
    assert not at.exception
    assert [h.value for h in at.header][:3] == ["Where the price target comes from",
                                                 "Price target by growth multiple and BTC CAGR", "Forecast to 2031"]
    assert at.metric[1].value == "2.13x" and at.metric[2].value == "$14.09"
    assert at.metric[6].label == "Price target, Dec 2028"
