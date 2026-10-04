"""Weekly 8-K facts for Strive from the capital-report feed (your Cloudflare Worker that parses Strategy and Strive
8-Ks; X Agent reads it too). It carries the weekly SATA share count, which strive.com only shows for the latest week.

The feed's address is a secret (FILINGS_FEED_URL in the environment or .streamlit/secrets.toml) so it stays out of
the public repo. Without it the model uses the last cached pull, then the bundled snapshot.
"""
from __future__ import annotations

import logging
import os
import tomllib
from pathlib import Path

import httpx

from model.sources import cache

log = logging.getLogger(__name__)
SECRETS = Path(__file__).resolve().parents[2] / ".streamlit" / "secrets.toml"


def feed_url() -> str | None:
    if url := os.environ.get("FILINGS_FEED_URL"):
        return url
    if SECRETS.exists():  # the CLI reads the same secrets file the app does
        return tomllib.loads(SECRETS.read_text(encoding="utf-8")).get("FILINGS_FEED_URL")
    return None


def strive_weeks(offline: bool = False) -> tuple[dict[str, dict], str]:
    """({balance_date: facts}, provenance) for every parsed ASST weekly 8-K."""
    feed, source, url = None, "unavailable", feed_url()
    if not offline and url:
        try:
            r = httpx.get(url, timeout=30)
            r.raise_for_status()
            feed = r.json()
            cache.save("filings_feed", feed)
            source = "capital-report feed (live)"
        except (httpx.HTTPError, ValueError) as e:
            log.warning("filings feed failed, using the cached copy: %s", e)
    if feed is None:
        feed, label = cache.load("filings_feed")
        source = f"capital-report feed ({label})" if feed is not None else source
    return weeks_from_feed(feed or {}), source


def weeks_from_feed(feed: dict) -> dict[str, dict]:
    out = {}
    for f in feed.get("filings") or []:
        ex = f.get("extracted") or {}
        if f.get("ticker") == "ASST" and ex.get("balanceDate") and ex.get("facts"):
            out[ex["balanceDate"]] = ex["facts"]
    return dict(sorted(out.items()))
