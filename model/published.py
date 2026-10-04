"""The published price target: the owner's levers and the data they were set on, frozen together, so every viewer
opens on the same target and it doesn't drift with prices. It lives in config/published.json, committed to the repo
(by the owner panel, through the GitHub API) so it survives app restarts and redeploys."""
from __future__ import annotations

import base64
import json
import math
from dataclasses import asdict, dataclass, field, fields
from datetime import date, datetime, timezone
from pathlib import Path

import httpx

from model.levers import Levers
from model.state import State

PATH = Path(__file__).resolve().parents[1] / "config" / "published.json"
REPO, BRANCH, REPO_PATH = "bobat2121-lgtm/Strive-Model", "main", "config/published.json"
COMMITTER = {"name": "Strive Model", "email": "312642099+bobat2121-lgtm@users.noreply.github.com"}


@dataclass(frozen=True)
class Published:
    set_at: datetime          # UTC
    set_by: str
    price_target: float       # at levers.pt_date, as computed when it was set
    levers: Levers
    state: State
    history: list = field(default_factory=list)  # every published target, oldest first (see entry())


def _plain(obj):
    return obj.isoformat() if isinstance(obj, (date, datetime)) else obj


def _dated(cls, raw: dict):
    """A dataclass from JSON, turning ISO strings back into dates where the field is a date."""
    out = {}
    for f in fields(cls):
        if f.name not in raw:
            continue
        v = raw[f.name]
        out[f.name] = date.fromisoformat(v) if f.type == "date" and isinstance(v, str) else v
    return cls(**out)


def dumps(p: Published) -> str:
    return json.dumps({"set_at": p.set_at, "set_by": p.set_by, "price_target": p.price_target,
                       "levers": asdict(p.levers), "state": asdict(p.state), "history": p.history},
                      default=_plain, indent=2) + "\n"


def loads(text: str) -> Published:
    raw = json.loads(text)
    st = raw["state"]
    st["history"] = {k: {**v, "date": date.fromisoformat(v["date"])} for k, v in (st.get("history") or {}).items()}
    return Published(set_at=datetime.fromisoformat(raw["set_at"]), set_by=raw["set_by"],
                     price_target=float(raw["price_target"]), levers=_dated(Levers, raw["levers"]),
                     state=_dated(State, st), history=raw.get("history") or [])


def load(path: Path = PATH) -> Published | None:
    try:
        return loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None


def make(levers: Levers, state: State, price_target: float, set_by: str) -> Published:
    return Published(set_at=datetime.now(timezone.utc).replace(microsecond=0), set_by=set_by,
                     price_target=float(price_target), levers=levers, state=state)


def entry(p: Published, value: dict, btc_price_at_target: float) -> dict:
    """One line of the price-target history, frozen as published: the target, its breakdown and the levers and data
    behind it (JSON-ready). value is valuation.price_target at the target date."""
    from model import valuation  # here, not at the top: valuation is heavier and published is loaded on every run
    lv, st = p.levers, p.state
    k0 = lv.k_start if lv.k_start is not None else valuation.implied_k(st)
    return {"set_at": p.set_at.isoformat(), "set_by": p.set_by, "price_target": float(p.price_target),
            "pt_date": lv.pt_date.isoformat(), "asst_price": float(st.share_price), "data_as_of": st.as_of.isoformat(),
            "prices_on": st.price_date.isoformat(), "ntav_per_share": float(value["ntav_per_share"]),
            "btc_yield": float(value["btc_yield"]), "gain_per_share": float(value["gain_per_share"]),
            "k": float(value["k"]), "k_start": float(k0) if lv.k_glide else float(value["k"]),
            "growth_premium": float(value["growth_premium"]), "implied_mnav": float(value["implied_mnav"]),
            "btc_price_at_target": float(btc_price_at_target),
            "sata_rate": float(lv.sata_rate if lv.sata_rate is not None else st.sata_rate),
            "levers": json.loads(json.dumps(asdict(lv), default=_plain))}


def save_local(p: Published, path: Path = PATH) -> None:
    Path(path).write_text(dumps(p), encoding="utf-8")


def commit(p: Published, token: str, client: httpx.Client | None = None) -> str:
    """Commit config/published.json to the repo; returns the commit's URL. Needs a token that can write contents."""
    url = f"https://api.github.com/repos/{REPO}/contents/{REPO_PATH}"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
               "X-GitHub-Api-Version": "2022-11-28"}
    c = client or httpx.Client(timeout=20)
    try:
        cur = c.get(url, headers=headers, params={"ref": BRANCH})
        body = {"message": f"Publish price target: ${p.price_target:,.2f} at {p.levers.pt_date:%b %d, %Y} "
                           f"(set by {p.set_by})",
                "content": base64.b64encode(dumps(p).encode("utf-8")).decode("ascii"),
                "branch": BRANCH, "committer": COMMITTER}
        if cur.status_code == 200:
            body["sha"] = cur.json()["sha"]
        r = c.put(url, headers=headers, json=body)
        r.raise_for_status()
        return r.json()["commit"]["html_url"]
    finally:
        if client is None:
            c.close()


def same_levers(a: Levers, b: Levers) -> bool:
    """Equal lever for lever, allowing for float round-trips through the input widgets."""
    def eq(x, y):
        if isinstance(x, float) and isinstance(y, float):
            return math.isclose(x, y, rel_tol=1e-9, abs_tol=1e-12)
        if isinstance(x, list) and isinstance(y, list):
            return len(x) == len(y) and all(eq(i, j) for i, j in zip(x, y))
        return x == y
    return all(eq(getattr(a, f.name), getattr(b, f.name)) for f in fields(Levers))
