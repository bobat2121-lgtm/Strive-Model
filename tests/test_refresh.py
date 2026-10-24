"""Refresh regression tests: today's cards, date provenance, and last-good feeds."""
from datetime import datetime, timezone

import httpx
import pytest

from model import state
from model.sources import cache, market, strive
from panel import common


@pytest.fixture(autouse=True)
def clear_today_cache():
    common.load_today_state.clear()
    yield
    common.load_today_state.clear()


def test_today_loads_independently_of_published_snapshot(monkeypatch, st):
    latest = st.with_prices(btc_price=92000, share_price=42)
    calls = []

    def load(**kwargs):
        calls.append(kwargs)
        return latest

    monkeypatch.setattr(state, "load", load)
    current, warning = common.today_snapshot(st)
    assert current == latest and warning is None
    assert st.share_price != current.share_price
    assert calls == [{"live_prices": True}]
    assert common.price_now("published", st) == 42
    assert len(calls) == 1  # hero and cards share one short-lived live cache


def test_failed_today_refresh_keeps_dated_snapshot_visible(monkeypatch, st):
    def unavailable(**kwargs):
        raise RuntimeError("no source or cache")

    monkeypatch.setattr(state, "load", unavailable)
    current, warning = common.today_snapshot(st)
    assert current == st
    assert "dated snapshot" in warning
    assert "Retrying" in warning


def test_cached_company_data_has_visible_warning(monkeypatch, st):
    from dataclasses import replace

    cached = replace(st, sources={"balance sheet": "strive.com (cached 2026-10-23T10:00:00+00:00)"})
    monkeypatch.setattr(state, "load", lambda **_: cached)
    current, warning = common.today_snapshot(st)
    assert current == cached
    assert "last saved company figures" in warning


def test_unavailable_market_quote_warning_includes_original_date(monkeypatch, st):
    from dataclasses import replace

    cached = replace(st, sources={"ASST price": "Strive dashboard · Oct 04, 2026 (quote unavailable)"})
    monkeypatch.setattr(state, "load", lambda **_: cached)
    _, warning = common.today_snapshot(st)
    assert "ASST price" in warning and "Oct 04, 2026" in warning


def test_strive_orders_rows_and_rejects_empty_response(calc):
    raw = {"data": {"btcHoldings": list(reversed(calc["rows"]))}, "preferredStocks": calc["preferredStocks"]}
    trimmed = strive._trim_calculated(raw)
    assert trimmed["rows"][-1]["date"] == max(r["date"] for r in calc["rows"])
    with pytest.raises(ValueError, match="no usable"):
        strive._trim_calculated({"data": {"btcHoldings": []}})


def test_bad_live_payload_does_not_replace_good_cache(monkeypatch, calc):
    request = httpx.Request("GET", "https://strive.com/test")
    response = httpx.Response(200, request=request, json={"data": {"btcHoldings": []}})
    saved = []
    monkeypatch.setattr(strive.httpx, "get", lambda *a, **k: response)
    monkeypatch.setattr(cache, "save", lambda *args: saved.append(args))
    monkeypatch.setattr(cache, "load", lambda name: (calc, "cached yesterday"))
    data, source = strive.calculated()
    assert data == calc and "cached yesterday" in source
    assert not saved


def test_corrupt_cache_falls_back_to_seed(monkeypatch, tmp_path):
    import json

    cached, seed = tmp_path / "cache", tmp_path / "seed"
    cached.mkdir()
    seed.mkdir()
    (cached / "test.json").write_text("{unfinished", encoding="utf-8")
    (seed / "test.json").write_text(json.dumps({"fetched_at": "yesterday", "payload": {"ok": True}}), encoding="utf-8")
    monkeypatch.setattr(cache, "DIR", cached)
    monkeypatch.setattr(cache, "SEED", seed)
    data, source = cache.load("test")
    assert data == {"ok": True} and "bundled snapshot" in source
    cache.save("test", {"new": True})
    assert cache.load("test")[0] == {"new": True}
    assert not list(cached.glob("*.tmp"))


def test_stock_quote_retains_market_timestamp(monkeypatch):
    quote_time = datetime(2026, 10, 23, 20, 0, 1, tzinfo=timezone.utc)
    response = httpx.Response(200, request=httpx.Request("GET", "https://example.com"),
                              json={"chart": {"result": [{"meta": {
                                  "regularMarketPrice": 28.97,
                                  "regularMarketTime": quote_time.timestamp(),
                              }}]}})
    monkeypatch.setattr(market.httpx, "get", lambda *a, **k: response)
    quote = market.stock_quote("ASST")
    assert quote.price == 28.97 and quote.as_of == quote_time
    assert "regular market" in quote.source


@pytest.mark.parametrize("btc_available", [True, False])
def test_live_quotes_refresh_independently(monkeypatch, calc, base, btc_available):
    quote_time = datetime(2026, 10, 23, 20, tzinfo=timezone.utc)
    monkeypatch.setattr(strive, "calculated", lambda *args: (calc, "dashboard"))
    monkeypatch.setattr(strive, "base_data", lambda *args: (base, "dashboard"))
    monkeypatch.setattr(market, "btc_quote", lambda: market.Quote(99000, quote_time, "BTC") if btc_available else None)
    monkeypatch.setattr(market, "stock_quote", lambda _: None if btc_available else market.Quote(50, quote_time, "ASST"))
    current = state.load(live_prices=True)
    assert current.btc_price == (99000 if btc_available else calc["rows"][-1]["btcPrice"])
    assert current.share_price == (calc["rows"][-1]["sharePrice"] if btc_available else 50)
    key = "BTC price" if btc_available else "ASST price"
    assert "Oct 23, 2026" in current.sources[key]
