"""The model: the price target as a hero, Strive today (last 8-K), the path to the target, how the target is built,
and everything else folded into one collapsed section."""
import pandas as pd
import streamlit as st

from model import engine, metrics, valuation
from panel import charts, common, theme

pub = common.current_published()
stt, mode = common.current_state(pub)
lv = common.sidebar(stt, pub, mode)
res = common.compute(stt, lv)
live = common.is_live(lv, mode, pub)
c = common.colors()
rate = lv.sata_rate if lv.sata_rate is not None else stt.sata_rate
s = metrics.summary(stt, stt.share_price, rate)
m0 = s["mnav"]
T = lv.pt_date
v, a, row = res["values"][T], res["attribution"], res["attribution"].loc[T]
r = engine.at(res["path"], T)
pt, p0 = v["price_target"], stt.share_price
p_now = common.price_now(mode, stt)

# ------------------------------------------------------------------ hero: the price target
theme.hero(f"{'Your scenario' if pub and not live else 'Price target'} · {T:%b %d, %Y}", f"${pt:,.2f}",
           f"<b>{pt / p_now - 1:+.0%}</b> vs ${p_now:,.2f} today",
           None if pub is None else f"Set {pub.set_at:%b %d, %Y} by {pub.set_by}" if live
           else f"The published target is ${pub.price_target:,.2f}; reset it from the levers panel.")
if not res["settled"] or not res["table"]["settled"]:
    st.warning("The market mNAV couldn't be made consistent with the valuation for some settings (the multiple feeds on "
               "itself at a high k). Those table cells are blank; try a lower k or Manual market mNAV.")

# ------------------------------------------------------------------ Strive today
theme.section("Strive today", f"Balance sheet as of {stt.as_of:%b %d, %Y} (weekly 8-K) · prices {stt.price_date:%b %d, %Y}")
theme.cards([
    ("ASST", f"${stt.share_price:,.2f}", f"BTC ${stt.btc_price:,.0f}"),
    ("mNAV", f"{m0:.2f}×", "price ÷ NTAV per share"),
    ("NTAV per share", f"${s['ntav_per_share']:,.2f}", "net treasury asset value"),
    ("Bitcoin held", f"{stt.btc:,.0f}", f"{common.usd(s['btc_nav'])} at market"),
    ("Sats per share", f"{s['sats_per_share']:,.0f}", "per diluted share"),
    ("Amplification", f"{s['amplification']:.1%}", "SATA ÷ BTC NAV"),
    ("SATA outstanding", common.usd(stt.sata_notional), f"at {rate:.2%}, paid daily"),
    ("Cash + STRC", common.usd(stt.cash + stt.securities), f"{s['dividend_coverage_years']:.1f} yrs dividend coverage"),
    ("Diluted shares", f"{stt.fd_shares / 1e6:,.2f}M", f"+{stt.warrants / 1e6:.2f}M warrants at ${lv.warrant_strike:g}"),
    ("Enterprise value", common.usd(s["enterprise_value"]), f"{s['ev_to_tav']:.2f}× treasury assets"),
])

# ------------------------------------------------------------------ the path to the target (fixed to the target date)
theme.section(f"The path to {T:%b %Y}",
              f"Net value per share today, what moves it, then the growth premium on top. $ per share; the dotted line "
              f"is ASST on {stt.price_date:%b %d, %Y} (${p0:,.2f}).")
with st.container(key="vg_chart"):
    st.altair_chart(charts.waterfall(row, f"{T:%b %Y}", c), width="stretch", theme=None)
k_implied = valuation.implied_k(stt)
k0 = lv.k_start if lv.k_start is not None else k_implied
k_from = (f"the k ASST's price implied on {stt.price_date:%b %d, %Y} (on Strive's actual last 12 months of bitcoin "
          f"earnings)" if abs(k0 - k_implied) < 0.005 else "your starting k")
k_story = (f"It starts at {k0:.2f}×, {k_from}, and glides to {lv.growth_multiple:.2f}× by {lv.k_glide_to:%b %Y}."
           if lv.k_glide else f"Held at {lv.growth_multiple:.2f}× throughout.")
with st.container(key="vg_facts"), st.expander("Key assumptions", expanded=False):
    theme.facts([
        ("Implied mNAV", f"{v['implied_mnav']:.2f}×",
         f"How richly the target values Strive against what it owns: the price target ÷ NTAV per share on "
         f"{T:%b %d, %Y}. At {v['implied_mnav']:.2f}×, a share is worth {v['implied_mnav']:.2f} times the bitcoin and "
         f"cash behind it, after SATA. ASST traded at {m0:.2f}× on {stt.price_date:%b %d, %Y}."),
        ("Growth multiple k", f"{v['k']:.2f}×",
         f"How many years of {T.year} bitcoin earnings (BTC $ Gain) investors pay for on top of NTAV, like a P/E on "
         f"bitcoin earnings. {k_story}"),
        ("BTC at target", f"${r.btc_price:,.0f}",
         f"Bitcoin's assumed price on {T:%b %d, %Y}: ${lv.ye_btc_price:,.0f} at {lv.ye_anchor:%b %Y}, then growing "
         f"{lv.base_cagr:.0%} a year. Both are levers in the sidebar."),
        (f"{T.year} BTC Yield", f"{v['btc_yield']:.0%}",
         f"How much the bitcoin behind each diluted share grows during {T.year}: bitcoin bought with SATA and new-share "
         f"money, after the dilution from those new shares. Step II below turns it into dollars."),
        ("Base case", f"{lv.base_cagr * 100:g}% BTC CAGR",
         f"The yearly bitcoin growth rate behind the target and the chart. The sidebar sets the bands "
         f"({', '.join(f'{b:.0%}' for b in lv.cagr_bands)}); the forecast table runs each one."),
    ])

# ------------------------------------------------------------------ how the price target is built
year, base_btc = T.year, (v["btc_gain"] / v["btc_yield"] if v["btc_yield"] else 0.0)
cash_sec, ntav_total = r.cash + stt.securities, r.ntav_per_share * r.fd_shares
split = ("" if v["premium_sata"] is None else
         f" · ${v['premium_sata']:,.2f} from SATA-funded bitcoin, ${v['premium_common']:,.2f} from common-funded")
theme.section("How the price target is built", "(NTAV + k × the year's BTC $ Gain) ÷ diluted shares")
theme.ledger([
    {"n": "I", "title": f"What common owns · {T:%b %d, %Y}", "label": "NTAV per share",
     "math": f"{r.btc:,.0f} BTC × ${r.btc_price:,.0f} + {common.usd(cash_sec)} cash & STRC − "
             f"{common.usd(r.sata_notional)} SATA = {common.usd(ntav_total)}, over {r.fd_shares / 1e6:,.1f}M diluted shares",
     "value": f"${r.ntav_per_share:,.2f}"},
    {"n": "II", "title": f"{year} bitcoin earnings · BTC $ Gain", "label": "per share",
     "math": f"{base_btc:,.0f} BTC at the start of {year} × {v['btc_yield']:.0%} BTC Yield = {v['btc_gain']:,.0f} BTC "
             f"gained × ${r.btc_price:,.0f} = {common.usd(v['btc_gain'] * r.btc_price)}, over {r.fd_shares / 1e6:,.1f}M shares",
     "value": f"${v['gain_per_share']:,.2f}"},
    {"n": "III", "title": "Growth premium", "label": "per share",
     "math": f"k {v['k']:.2f}× × ${v['gain_per_share']:,.2f}{split}", "value": f"+${v['growth_premium']:,.2f}"},
    {"n": "IV", "title": f"Price target · {T:%b %d, %Y}", "label": "per share", "total": True,
     "math": f"${r.ntav_per_share:,.2f} + ${v['growth_premium']:,.2f} · implied mNAV {v['implied_mnav']:.2f}× · "
             f"{pt / p0 - 1:+.0%} vs ${p0:,.2f} on {stt.price_date:%b %d, %Y}",
     "value": f"${pt:,.2f}"},
])

# ------------------------------------------------------------------ everything else, folded away
with st.expander("Full model detail", expanded=False):
    tab_dates, tab_table, tab_fcst = st.tabs(["All valuation dates", "Price-target table",
                                              f"Forecast to {lv.horizon_end.year}"])
    with tab_dates:
        st.caption(common.md(
            f"Each year end valued the same way, {common.k_label(lv, res['implied_k'])}; new common sells at a market "
            f"mNAV {common.mnav_label(lv, m0)}; SATA dividends {common.rate_label(lv, rate)}."))
        labels = {**charts.LABELS, **charts.PREMIUM}
        table = a.rename(columns={"start": "NTAV today", "ntav_end": "NTAV at date", "end": "Price target", **labels})
        order = ["NTAV today", *[charts.LABELS[k] for k in ("btc_move", "amplification", "sata_dividends", "issuance",
                                                             "op_costs")],
                 "NTAV at date", *charts.PREMIUM.values(), charts.LABELS["growth_premium"], "Price target"]
        shown = table[order].map(lambda x: "—" if pd.isna(x) else common.signed(x))
        for col in ("NTAV today", "NTAV at date", "Price target"):
            shown[col] = table[col].map(lambda x: f"${x:,.2f}")
        shown["BTC Yield"] = table["btc_yield"].map(lambda x: f"{x:.0%}")
        shown["k"] = table["k"].map(lambda x: f"{x:.2f}x")
        shown["Implied mNAV"] = table["implied_mnav"].map(lambda x: f"{x:.2f}x")
        shown["Net-basis value"] = table["net_target"].map(lambda x: "—" if pd.isna(x) else f"${x:,.2f}")
        shown.index = [f"{d:%b %Y}" + (" (target)" if d == T else "") for d in shown.index]
        st.dataframe(shown, width="stretch")
        st.markdown(common.md(
            "- **NTAV**: what common owns per share (BTC + cash + STRC − SATA, per diluted share).\n"
            "- **BTC move**: those net assets tracking BTC one-for-one. **Amplification**: what SATA-funded BTC gains, "
            "after the 18-month cash-reserve drag. **SATA dividends**: what that SATA costs. **Issuance**: common and "
            "warrant shares sold above NTAV per share. **Op. costs**: the net cash burn, not dividends.\n"
            "- **Growth premium**: k × the year's BTC $ Gain, split by who paid for the year's bitcoin. **Net-basis "
            "value** is a reference that credits SATA only with what its bitcoin earns above the dividend."))

    with tab_table:
        st.caption(f"Price target at {T:%b %d, %Y}. Rows: the k the glide ends at; the first row holds the k today's "
                   f"price implies. Columns: BTC CAGR after {lv.ye_anchor:%b %Y}. Each cell is its own run"
                   f"{', with its own consistent market mNAV' if lv.market_mnav_mode == 'model' else ''}. "
                   f"Base case highlighted.")
        t = res["table"]
        hl = f"background-color: {c['up']}33; font-weight: 600"
        base_row, base_col = f"{lv.growth_multiple:g}x", f"{lv.base_cagr * 100:g}% CAGR"
        for tab, (key, fmt) in zip(st.tabs(["Price target", "Implied mNAV"]),
                                   [("price_target", "${:,.2f}"), ("implied_mnav", "{:.2f}x")]):
            df = t[key]
            css = pd.DataFrame("", index=df.index, columns=df.columns)
            if base_row in css.index and base_col in css.columns:
                css.loc[base_row, base_col] = hl
            tab.dataframe(df.style.format(fmt).apply(lambda _, css=css: css, axis=None), width="stretch")

    with tab_fcst:
        st.caption("Base case, week by week. The market price is the market mNAV × NTAV per share; it sets the price "
                   "new common sells at. Price and SATA charts use a log scale.")
        p = res["path"].reset_index()
        p["sata_week"] = p["raised_sata"] / (p["date"].diff().dt.days / 7)
        p = p.rename(columns={"share_price": "Market price", "ntav_per_share": "NTAV per share",
                              "amplification": "Amplification", "sata_week": "SATA per week",
                              "sats_per_share": "Sats per share"})
        g1, g2 = st.columns(2, gap="large")
        with g1:
            st.subheader("Market price and NTAV per share")
            st.altair_chart(charts.lines(p, ["Market price", "NTAV per share"], "$,.0f", c, end_labels=True, log=True),
                            width="stretch", theme=None)
            st.subheader("SATA issued per week")
            st.altair_chart(charts.lines(p.iloc[1:], ["SATA per week"], "$~s", c,
                                         ref=(72.7e6, "Recent average $72.7M"), log=True), width="stretch", theme=None)
        with g2:
            st.subheader("Amplification")
            st.altair_chart(charts.lines(p, ["Amplification"], ".0%", c), width="stretch", theme=None)
            st.subheader("Sats per diluted share")
            st.altair_chart(charts.lines(p, ["Sats per share"], ",.0f", c), width="stretch", theme=None)
        ye = [p.iloc[0]] + [p[p["date"] <= pd.Timestamp(f"{y}-12-31")].iloc[-1]
                            for y in range(stt.price_date.year, lv.horizon_end.year + 1)]
        vals = {pd.Timestamp(d): x for d, x in res["values"].items()}
        st.dataframe(pd.DataFrame({
            "BTC price": [f"${x['btc_price']:,.0f}" for x in ye],
            "BTC held": [f"{x['btc']:,.0f}" for x in ye],
            "SATA": [common.usd(x["sata_notional"]) for x in ye],
            "SATA per week": ["—" if pd.isna(x["SATA per week"]) else common.usd(x["SATA per week"]) for x in ye],
            "Amplification": [f"{x['Amplification']:.1%}" for x in ye],
            "SATA rate": [f"{x['sata_rate']:.2%}" for x in ye],
            "Dividends / yr": [common.usd(x["sata_rate"] * x["sata_notional"]) for x in ye],
            "Diluted shares": [f"{x['fd_shares'] / 1e6:,.1f}M" for x in ye],
            "NTAV per share": [f"${x['NTAV per share']:,.2f}" for x in ye],
            "Market mNAV": [f"{x['mnav']:.2f}x" for x in ye],
            "Market price": [f"${x['Market price']:,.2f}" for x in ye],
            "k": [f"{vals[x['date']]['k']:.2f}x" if x["date"] in vals else "—" for x in ye],
            "BTC Yield": [f"{vals[x['date']]['btc_yield']:.0%}" if x["date"] in vals else "—" for x in ye],
            "Value": [f"${vals[x['date']]['price_target']:,.2f}" if x["date"] in vals else "—" for x in ye],
            "Coverage": [f"{x['coverage_years']:.1f} yrs" for x in ye],
        }, index=[f"{x['date']:%b %d, %Y}" for x in ye]), width="stretch")
        if (res["path"]["btc_bought_usd"] < 0).any():
            st.warning("The dividend reserve ran dry and BTC was sold in some weeks.")

st.caption(common.md("Sources: " + " · ".join(f"{k}: {v}" for k, v in stt.sources.items())
                     + ". An independent modeling tool that applies your levers to Strive's published figures; not "
                     "affiliated with or endorsed by Strive, Inc. Not a recommendation."))

common.owner_panel(stt, lv, v, pub, mode)
