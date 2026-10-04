"""Last-good copies of every remote pull, so the model still runs offline or when an endpoint breaks.

data/cache/ holds this machine's last good pulls (not in git). data/seed/ is a snapshot committed with the repo, the
last resort for a fresh install (e.g. Streamlit Cloud) whose first live pull fails."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

DIR = Path(__file__).resolve().parents[2] / "data" / "cache"
SEED = DIR.parent / "seed"


def save(name: str, payload) -> None:
    DIR.mkdir(parents=True, exist_ok=True)
    body = {"fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "payload": payload}
    (DIR / f"{name}.json").write_text(json.dumps(body), encoding="utf-8")


def load(name: str) -> tuple[object | None, str | None]:
    """(payload, label) from the last good pull, else the bundled snapshot, else (None, None)."""
    for folder, kind in ((DIR, "cached"), (SEED, "bundled snapshot")):
        p = folder / f"{name}.json"
        if p.exists():
            body = json.loads(p.read_text(encoding="utf-8"))
            return body.get("payload"), f"{kind} {body.get('fetched_at')}"
    return None, None
