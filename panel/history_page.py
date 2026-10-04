"""Weekly issuance history: SATA and common dollars backed out of 8-K share counts and ASST VWAP. This is what the
SATA and common lever defaults rest on."""
from datetime import date, timedelta

import pandas as pd
import streamlit as st

from model import calibrate
from model.sources import filings, market, strive
from panel import charts, common


@st.cache_data(ttl=3600, show_spinner="Pulling share counts, the 8-K feed and prices…")
def history() -> pd.DataFrame:
    base, _ = strive.base_data()
    weeks, _ = filings.strive_weeks()
    end = date.today() + timedelta(days=1)
    bars = {t: market.daily_bars(t, date(2026, 7, 1), end) for t in ("ASST", "SATA")}
    return calibrate.weekly(base, weeks, bars)


c = common.colors()
st.title("Issuance history")
st.caption(common.md("8-Ks report share counts every week but stopped reporting ATM dollars after Aug 7, 2026. Common dollars = "
           "(change in issued shares − warrant exercises) × the week's ASST VWAP; SATA dollars = change in SATA "
           "shares × $100. Check: money raised vs. money used (BTC bought + change in cash + dividends + burn)."))
df = history()
s = calibrate.summary(df)
tiles = [("SATA per week", common.usd(s["sata_usd_avg"])), ("Common per week", common.usd(s["common_usd_avg"])),
         ("Common, % of shares / wk", f"{s['common_pct_avg']:.2%}"),
         ("Last 3 weeks", f"{s['common_pct_recent']:.2%}"),
         ("SATA share of new capital", f"{s['sata_share_of_new_capital']:.0%}"),
         ("Largest raised-vs-used gap", common.usd(s["max_abs_gap"]))]
st.caption(f"Averages over the {s['weeks']} weeks since SATA reached par (week ending Aug 21, 2026).")
common.tiles([(label, value, None) for label, value in tiles])

view = df.reset_index()
view["week"] = pd.to_datetime(view["week"]).dt.strftime("%b %d")
st.altair_chart(charts.weekly_bars(view.rename(columns={"sata_usd": "SATA", "common_usd": "Common"}), c),
                width="stretch")
table = pd.DataFrame({
    "ASST VWAP": df["asst_vwap"].map(lambda v: f"${v:.2f}"),
    "SATA": df["sata_usd"].map(common.usd), "Common": df["common_usd"].map(common.usd),
    "Common, % of shares": df["common_pct"].map(lambda v: f"{v:.2%}"),
    "Warrants": df["warrant_usd"].map(common.usd), "Raised": df["sources"].map(common.usd),
    "Used": df["uses"].map(common.usd), "Gap": df["gap"].map(common.usd),
})
table.index = [f"{pd.Timestamp(d):%b %d, %Y}" for d in table.index]
st.dataframe(table, width="stretch")
