"""The model: today's snapshot, the price target and where it comes from, the k x CAGR table, and the forecast."""
import pandas as pd
import streamlit as st

from model import metrics
from panel import charts, common

stt = common.current_state()
lv = common.sidebar(stt)
res = common.compute(stt, lv)
c = common.colors()
rate = lv.sata_rate if lv.sata_rate is not None else stt.sata_rate
s = metrics.summary(stt, stt.share_price, rate)
m0 = s["mnav"]

st.title("Strive (ASST) model")
st.caption(common.md(f"Balance sheet as of {stt.as_of:%b %d, %Y} (weekly 8-K) · prices {stt.price_date:%b %d, %Y} · "
                     + " · ".join(f"{k}: {v}" for k, v in stt.sources.items())))
common.tiles([
    ("ASST", f"${stt.share_price:.2f}", None),
    ("mNAV", f"{m0:.2f}x", "ASST price ÷ net treasury asset value per diluted share (Strive's definition)"),
    ("NTAV per share", f"${s['ntav_per_share']:.2f}", "(BTC + cash + STRC − debt − SATA) ÷ diluted shares"),
    ("Amplification", f"{s['amplification']:.1%}", "(debt + SATA notional) ÷ BTC NAV"),
    ("Sats per share", f"{s['sats_per_share']:,.0f}", "BTC per assumed fully diluted share"),
    ("Coverage", f"{s['dividend_coverage_years']:.1f} yrs", "Treasury assets ÷ annual SATA dividends"),
])
st.caption(common.md(f"{stt.btc:,.0f} BTC at ${stt.btc_price:,.0f} · SATA {common.usd(stt.sata_notional)} at {rate:.2%} · "
                     f"cash + STRC {common.usd(stt.cash + stt.securities)} · {stt.fd_shares / 1e6:.2f}M diluted shares · "
                     f"{stt.warrants / 1e6:.2f}M PIPE warrants at ${lv.warrant_strike:g}"))

# ------------------------------------------------------------------ the price target and where it comes from
st.header("Where the price target comes from")
a = res["attribution"]
st.caption(common.md(
    f"Price target = NTAV per share at the date + {lv.growth_multiple:g}x the next year's {common.gain_label(lv)} "
    f"per share (TD Cowen's structure). Base case: {lv.base_cagr * 100:g}% BTC CAGR after {lv.ye_anchor:%b %Y}; "
    f"new common sells at a market mNAV {common.mnav_label(lv, m0)}; SATA dividends "
    f"{common.rate_label(lv, rate)}. $ per share."))
dates = list(a.index)
pick = st.segmented_control("Valuation date", dates, default=lv.pt_date if lv.pt_date in dates else dates[-1],
                            required=True, format_func=lambda d: f"{d:%b %Y}" + (" · target" if d == lv.pt_date else ""))
row, v = a.loc[pick], res["values"][pick]
title = "Price target" if pick == lv.pt_date else "Value"
common.tiles([
    (f"{title}, {pick:%b %Y}", f"${row['end']:,.2f}", None,
     f"{row['end'] / row['today_price'] - 1:+.0%} vs ${row['today_price']:,.2f} today"),
    ("NTAV per share", f"${v['ntav_per_share']:,.2f}", "What common owns per share at the date"),
    ("Next year's gain", f"{v['forward_yield']:.0%}", f"{common.signed(v['forward_gain'])} per share, at the date's "
                                                      f"BTC price"),
    ("k multiple", f"{lv.growth_multiple:g}x", f"Today's price implies {res['implied_k']:.2f}x"),
    ("Implied mNAV", f"{v['implied_mnav']:.2f}x", "Price target ÷ NTAV per share"),
])
st.caption(common.md(f"The grey line is today's price (${row['today_price']:,.2f}). Today's price implies k = "
                     f"{res['implied_k']:.2f}x on the next year's gain."))
st.altair_chart(charts.waterfall(row, f"{pick:%b %Y}", c), width="stretch")
with st.expander("What each step means"):
    st.markdown(common.md(
        "- **NTAV today**: what common owns per share now (BTC + cash + STRC − SATA, per diluted share).\n"
        "- **BTC move**: those net assets tracking BTC one-for-one.\n"
        "- **Amplification**: the extra from SATA leverage, existing and new, net of its dividends and the 18-month "
        "cash reserve. SATA sold at par adds nothing on the day; it pays off as BTC outruns the dividend.\n"
        "- **Issuance**: common (ATM) and warrant shares sold above NTAV per share, at the market mNAV. At mNAV *m*, "
        "each dollar raised adds 1 − 1/*m* of a dollar to NTAV.\n"
        "- **Op. costs**: the net cash burn.\n"
        "- **Growth premium**: k × the next year's gain per share, valued at the date's BTC price. With the net gain, "
        "higher amplification at the date means a bigger premium, because next year's leverage gain belongs to "
        "common.\n\n"
        "The steps are measured by switching the engine's pieces off one at a time, so they add up exactly."))
table = a.rename(columns={"start": "NTAV today", "ntav_end": "NTAV at date", "end": "Value", **charts.LABELS})
table = table[["NTAV today", *charts.LABELS.values(), "NTAV at date", "Value", "implied_mnav", "forward_yield"]]
shown = table.drop(columns=["implied_mnav", "forward_yield"]).map(common.signed)
for col in ("NTAV today", "NTAV at date", "Value"):
    shown[col] = table[col].map(lambda x: f"${x:,.2f}")
shown["Implied mNAV"] = table["implied_mnav"].map(lambda x: f"{x:.2f}x")
shown["Next year's gain"] = table["forward_yield"].map(lambda x: f"{x:.0%}")
shown.index = [f"{d:%b %Y}" + (" (target)" if d == lv.pt_date else "") for d in shown.index]
st.dataframe(shown, width="stretch")

# ------------------------------------------------------------------ k x CAGR table
st.header("Price target by growth multiple and BTC CAGR")
st.caption(f"Price target at {lv.pt_date:%b %d, %Y}. Rows: k on the next year's {common.gain_label(lv)}; the first "
           f"row is the k today's price implies. Columns: BTC CAGR after {lv.ye_anchor:%b %Y}. Base case highlighted.")
t = res["table"]
hl = f"background-color: {c['s1']}26; font-weight: 600"
base_row, base_col = f"{lv.growth_multiple:g}x", f"{lv.base_cagr * 100:g}% CAGR"
for tab, (key, fmt) in zip(st.tabs(["Price target", "Implied mNAV"]),
                           [("price_target", "${:,.2f}"), ("implied_mnav", "{:.2f}x")]):
    df = t[key]
    css = pd.DataFrame("", index=df.index, columns=df.columns)
    if base_row in css.index and base_col in css.columns:
        css.loc[base_row, base_col] = hl
    tab.dataframe(df.style.format(fmt).apply(lambda _, css=css: css, axis=None), width="stretch")

# ------------------------------------------------------------------ the forecast
st.header(f"Forecast to {lv.horizon_end.year}")
st.caption(f"Base case, week by week. The market price is the mNAV path × NTAV per share; it sets the price new common "
           f"sells at. Price and SATA charts use a log scale.")
p = res["path"].reset_index()
p["sata_week"] = p["raised_sata"] / (p["date"].diff().dt.days / 7)
p = p.rename(columns={"share_price": "Market price", "ntav_per_share": "NTAV per share",
                      "amplification": "Amplification", "sata_week": "SATA per week",
                      "sats_per_share": "Sats per share"})
g1, g2 = st.columns(2, gap="large")
with g1:
    st.subheader("Market price and NTAV per share")
    st.altair_chart(charts.lines(p, ["Market price", "NTAV per share"], "$,.0f", c, end_labels=True, log=True),
                    width="stretch")
    st.subheader("SATA issued per week")
    st.altair_chart(charts.lines(p.iloc[1:], ["SATA per week"], "$~s", c, ref=(72.7e6, "Recent average $72.7M"),
                                 log=True), width="stretch")
with g2:
    st.subheader("Amplification")
    st.altair_chart(charts.lines(p, ["Amplification"], ".0%", c), width="stretch")
    st.subheader("Sats per diluted share")
    st.altair_chart(charts.lines(p, ["Sats per share"], ",.0f", c), width="stretch")

ye = [p.iloc[0]] + [p[p["date"] <= pd.Timestamp(f"{y}-12-31")].iloc[-1]
                    for y in range(stt.price_date.year, lv.horizon_end.year + 1)]
vals = {pd.Timestamp(d): x for d, x in res["values"].items()}
st.dataframe(pd.DataFrame({
    "BTC price": [f"${r['btc_price']:,.0f}" for r in ye],
    "BTC held": [f"{r['btc']:,.0f}" for r in ye],
    "SATA": [common.usd(r["sata_notional"]) for r in ye],
    "SATA per week": ["—" if pd.isna(r["SATA per week"]) else common.usd(r["SATA per week"]) for r in ye],
    "Amplification": [f"{r['Amplification']:.1%}" for r in ye],
    "SATA rate": [f"{r['sata_rate']:.2%}" for r in ye],
    "Dividends / yr": [common.usd(r["sata_rate"] * r["sata_notional"]) for r in ye],
    "Diluted shares": [f"{r['fd_shares'] / 1e6:,.1f}M" for r in ye],
    "NTAV per share": [f"${r['NTAV per share']:,.2f}" for r in ye],
    "Market price": [f"${r['Market price']:,.2f}" for r in ye],
    "Next year's gain": [f"{vals[r['date']]['forward_yield']:.0%}" if r["date"] in vals else "—" for r in ye],
    "Value": [f"${vals[r['date']]['price_target']:,.2f}" if r["date"] in vals else "—" for r in ye],
    "Coverage": [f"{r['coverage_years']:.1f} yrs" for r in ye],
}, index=[f"{r['date']:%b %d, %Y}" for r in ye]), width="stretch")
if (res["path"]["btc_bought_usd"] < 0).any():
    st.warning("The dividend reserve ran dry and BTC was sold in some weeks.")
st.caption("A modeling tool that applies your levers to Strive's published figures. It is not a recommendation.")
