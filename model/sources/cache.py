"""Last-good copies of every remote pull, so the model still runs offline or when an endpoint breaks.

data/cache/ holds this machine's last good pulls (not in git). data/seed/ is a snapshot committed with the repo, the
last resort for a fresh install (e.g. Streamlit Cloud) whose first live pull fails."""
from __future__ import annotations

import json
import logging
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

DIR = Path(__file__).resolve().parents[2] / "data" / "cache"
SEED = DIR.parent / "seed"
log = logging.getLogger(__name__)


def save(name: str, payload) -> None:
    DIR.mkdir(parents=True, exist_ok=True)
    body = {"fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "payload": payload}
    # Readers must never see a half-written refresh, including across sessions.
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=DIR, suffix=".tmp", delete=False) as out:
            temporary = out.name
            json.dump(body, out)
        os.replace(temporary, DIR / f"{name}.json")
    finally:
        if temporary is not None and os.path.exists(temporary):
            os.unlink(temporary)


def load(name: str) -> tuple[object | None, str | None]:
    """(payload, label) from the last good pull, else the bundled snapshot, else (None, None)."""
    for folder, kind in ((DIR, "cached"), (SEED, "bundled snapshot")):
        p = folder / f"{name}.json"
        if p.exists():
            try:
                body = json.loads(p.read_text(encoding="utf-8"))
                if not isinstance(body, dict) or body.get("payload") is None:
                    raise ValueError("cache has no payload")
                return body["payload"], f"{kind} {body.get('fetched_at')}"
            except (OSError, ValueError) as e:
                log.warning("Could not read %s cache %s: %s", kind, p, e)
    return None, None
