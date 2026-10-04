"""Strive Model: the Streamlit app. Run: .venv\\Scripts\\python -m streamlit run streamlit_app.py"""
import os

import streamlit as st

from panel import theme

st.set_page_config(page_title="Strive Model", page_icon=":material/insights:", layout="wide",
                   initial_sidebar_state="collapsed")  # the scene needs the room; levers are one click away
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
