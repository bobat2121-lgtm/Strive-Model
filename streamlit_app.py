"""Strive Model: the Streamlit app. Run: .venv\\Scripts\\python -m streamlit run streamlit_app.py"""
import os
import sys
from pathlib import Path

import streamlit as st

st.set_page_config(page_title="Strive Model", page_icon=":material/insights:", layout="wide",
                   initial_sidebar_state="collapsed")  # the scene needs the room; levers are one click away

ROOT = Path(__file__).parent
APP_PACKAGES = ("panel", "model")


@st.cache_resource
def _loaded_code() -> dict:
    return {}


def load_fresh_code() -> None:
    """Load the app's code as it is on disk, all of it together.

    Streamlit Cloud updates the files on a git push, but only a browser session open at that moment notices, and
    modules already imported stay in memory for every new session. A new page could then run against an old module
    (a TypeError on a changed signature). So each run compares the app's files with what this process last loaded;
    when they differ it drops the app's modules, the compiled page scripts and the data caches, and this run imports
    everything fresh."""
    now = {str(p): p.stat().st_mtime for d in (*APP_PACKAGES, "config") for p in (ROOT / d).rglob("*")
           if p.suffix in (".py", ".yaml")}
    seen = _loaded_code()
    if seen == now:
        return
    for name in [m for m in sys.modules if m.split(".")[0] in APP_PACKAGES]:
        del sys.modules[name]
    try:  # the compiled page scripts, shared by every session (Streamlit internals, pinned in requirements.txt)
        from streamlit.runtime import Runtime
        Runtime.instance()._script_cache.clear()
    except Exception:
        pass
    if seen:  # not on a fresh start
        st.cache_data.clear()
    seen.clear()
    seen.update(now)


load_fresh_code()

from panel import theme  # noqa: E402  (after the code check, so it's the current theme)

try:  # secrets (local .streamlit/secrets.toml or Streamlit Cloud) -> environment, where model.sources reads them
    for key, value in st.secrets.items():
        if isinstance(value, str):
            os.environ.setdefault(key, value)
except Exception:  # no secrets file: the bundled snapshot covers the feed
    pass

theme.apply()

st.navigation([st.Page("panel/model_page.py", title="Model", icon=":material/insights:", default=True),
               st.Page("panel/history_page.py", title="Issuance history", icon=":material/history:")],
              position="top").run()
