"""Strive Model: the Streamlit app. Run: .venv\\Scripts\\python -m streamlit run streamlit_app.py"""
import os

import streamlit as st

from panel import theme

st.set_page_config(page_title="Strive Model", page_icon=":material/insights:", layout="wide")
try:  # secrets (local .streamlit/secrets.toml or Streamlit Cloud) -> environment, where model.sources reads them
    for key, value in st.secrets.items():
        if isinstance(value, str):
            os.environ.setdefault(key, value)
except Exception:  # no secrets file: the bundled snapshot covers the feed
    pass

names = list(theme.THEMES)  # theme preview: ?theme=monolith|spire|oracle, or the picker at the top of the sidebar
asked = st.query_params.get("theme", theme.DEFAULT)
pick = st.sidebar.selectbox("Theme (preview)", names, index=names.index(asked) if asked in names else 0,
                            format_func=lambda n: theme.THEMES[n]["label"])
if pick != asked:
    st.query_params["theme"] = pick
theme.apply(pick)

st.navigation([st.Page("panel/model_page.py", title="Model", icon=":material/insights:", default=True),
               st.Page("panel/history_page.py", title="Issuance history", icon=":material/history:")],
              position="top").run()
