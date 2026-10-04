"""The published price target: saved and loaded exactly, compared lever for lever, committed through the GitHub API."""
import base64
import json
from dataclasses import replace

import httpx
import pytest

from model import levers, published, state, valuation


@pytest.fixture
def pub(calc, base):
    snap = state.from_payloads(calc, base).with_prices(85224.79, 30.03)
    lv = replace(levers.load(), k_start=3.35)
    path, _, _ = valuation.solve_market(snap, lv, lv.base_cagr)
    return published.make(lv, snap, valuation.price_target(path, snap, lv.pt_date, lv)["price_target"], "@WallyXIX")


def test_round_trip_reproduces_the_target(pub, tmp_path):
    f = tmp_path / "published.json"
    published.save_local(pub, f)
    back = published.load(f)
    assert back.state == pub.state and back.levers == pub.levers and back.set_at == pub.set_at
    path, _, _ = valuation.solve_market(back.state, back.levers, back.levers.base_cagr)
    assert valuation.price_target(path, back.state, back.levers.pt_date, back.levers)["price_target"] == \
        pytest.approx(pub.price_target, rel=1e-12)


def test_history_entries_survive_the_round_trip(pub, tmp_path):
    path, _, _ = valuation.solve_market(pub.state, pub.levers, pub.levers.base_cagr)
    v = valuation.price_target(path, pub.state, pub.levers.pt_date, pub.levers)
    e = published.entry(pub, v, 196000.0)
    assert e["price_target"] == pytest.approx(pub.price_target) and e["k_start"] == pytest.approx(3.35)
    assert e["ntav_per_share"] + e["growth_premium"] == pytest.approx(e["price_target"])  # the breakdown adds up
    f = tmp_path / "published.json"
    published.save_local(replace(pub, history=[e]), f)
    back = published.load(f)
    assert back.history == [e]


def test_missing_file_means_nothing_published(tmp_path):
    assert published.load(tmp_path / "none.json") is None


def test_same_levers_ignores_round_off_but_not_changes(pub):
    lv = pub.levers
    assert published.same_levers(lv, replace(lv, common_weekly_pct=lv.common_weekly_pct * (1 + 1e-13)))
    assert not published.same_levers(lv, replace(lv, common_weekly_pct=0.006))
    assert not published.same_levers(lv, replace(lv, k_start=None))


def test_starting_k_drives_the_glide(pub):
    st_, lv = pub.state, pub.levers
    assert valuation.k_at(st_, lv, st_.price_date) == pytest.approx(3.35)
    assert valuation.k_at(st_, lv, lv.k_glide_to) == pytest.approx(lv.growth_multiple)
    assert valuation.k_at(st_, replace(lv, k_start=None), st_.price_date) == pytest.approx(valuation.implied_k(st_))


def test_commit_puts_the_file_with_the_current_sha(pub):
    seen = []

    def handler(req: httpx.Request) -> httpx.Response:
        seen.append(req)
        assert req.headers["Authorization"] == "Bearer test-token"
        if req.method == "GET":
            return httpx.Response(200, json={"sha": "abc123"})
        return httpx.Response(200, json={"commit": {"html_url": "https://github.com/x/commit/1"}})

    url = published.commit(pub, "test-token", client=httpx.Client(transport=httpx.MockTransport(handler)))
    assert url == "https://github.com/x/commit/1"
    body = json.loads(seen[1].content)
    assert seen[1].method == "PUT" and body["sha"] == "abc123" and body["branch"] == "main"
    assert published.loads(base64.b64decode(body["content"]).decode()).price_target == pub.price_target
