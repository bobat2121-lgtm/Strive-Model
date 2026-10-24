"""The model: the price target as a hero, Strive today (last 8-K), the path to the target, how the target is built,
and everything else folded into one collapsed section."""
from datetime import date, datetime

import pandas as pd
import streamlit as st

from model import engine, metrics, valuation
from model.state import SATS_PROSPECTUS
from panel import charts, common, detail, theme

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
updated_model = live and abs(pt - pub.price_target) >= 0.005
publication_note = (None if pub is None else
                    f"SATS included · settings set {pub.set_at:%b %d, %Y} by {pub.set_by}. "
                    f"Previously published: ${pub.price_target:,.2f}." if updated_model else
                    f"Set {pub.set_at:%b %d, %Y} by {pub.set_by}" if live else
                    f"The published target is ${pub.price_target:,.2f}; reset it from the levers panel.")
theme.hero(f"{'Your scenario' if pub and not live else 'Price target'} · {T:%b %d, %Y}", f"${pt:,.2f}",
           f"<b>{pt / p_now - 1:+.0%}</b> vs ${p_now:,.2f} today",
           publication_note)
if not res["settled"] or not res["table"]["settled"]:
    st.warning("The market mNAV couldn't be made consistent with the valuation for some settings (the multiple feeds on "
               "itself at a high k). Those table cells are blank; try a lower k or Manual market mNAV.")

# ------------------------------------------------------------------ Strive today
@st.fragment(run_every=common.TODAY_REFRESH_SECONDS)
def strive_today():
    today, warning = common.today_snapshot(stt)
    current = metrics.summary(today, today.share_price, today.sata_rate)
    theme.section("Strive today", f"Balance sheet as of {today.as_of:%b %d, %Y} (latest reported) · "
                  f"latest prices {today.price_date:%b %d, %Y} · refreshes every minute")
    if warning:
        st.warning(warning)
    theme.cards([
        ("ASST", f"${today.share_price:,.2f}", f"BTC ${today.btc_price:,.0f}"),
        ("mNAV", f"{current['mnav']:.2f}×", "price ÷ NTAV per share"),
        ("NTAV per share", f"${current['ntav_per_share']:,.2f}", "net treasury asset value"),
        ("Bitcoin held", f"{today.btc:,.0f}", f"{common.usd(current['btc_nav'])} at market"),
        ("Sats per share", f"{current['sats_per_share']:,.0f}", "per diluted share"),
        ("Amplification", f"{current['amplification']:.1%}", "preferred + debt ÷ BTC NAV"),
        ("SATA outstanding", common.usd(today.sata_notional), f"at {today.sata_rate:.2%}, paid daily"),
        ("SATS outstanding", common.usd(today.sats_notional), f"at {today.sats_rate:.2%}, nonconvertible"),
        ("Cash + STRC", common.usd(today.cash + today.securities),
         f"{current['dividend_coverage_years']:.1f} yrs dividend coverage"),
        ("Diluted shares", f"{today.fd_shares / 1e6:,.2f}M", f"+{today.warrants / 1e6:.2f}M warrants"),
        ("Enterprise value", common.usd(current['enterprise_value']), f"{current['ev_to_tav']:.2f}× treasury assets"),
    ])
    price_sources = [today.sources[k] for k in ("BTC price", "ASST price") if k in today.sources]
    if price_sources:
        st.caption(" · ".join(price_sources))
    if today.sources.get("SATS"):
        note = today.sources["SATS"].replace(SATS_PROSPECTUS, "SATS IPO")
        st.caption(note + " · Supplemental cash adjustments are pro forma estimates.")


strive_today()

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
         f"cash behind it, after preferred stock and debt. ASST traded at {m0:.2f}× on {stt.price_date:%b %d, %Y}."),
        ("Growth multiple k", f"{v['k']:.2f}×",
         f"How many years of {T.year} bitcoin earnings (BTC $ Gain) investors pay for on top of NTAV, like a P/E on "
         f"bitcoin earnings. {k_story}"),
        ("BTC at target", f"${r.btc_price:,.0f}",
         f"Bitcoin's assumed price on {T:%b %d, %Y}: ${lv.ye_btc_price:,.0f} at {lv.ye_anchor:%b %Y}, then growing "
         f"{lv.base_cagr:.0%} a year. Both are levers in the sidebar."),
        (f"{T.year} BTC Yield", f"{v['btc_yield']:.0%}",
         f"How much the bitcoin behind each diluted share grows during {T.year}: bitcoin bought with preferred and new-share "
         f"money, after the dilution from those new shares. Step II below turns it into dollars."),
        ("Base case", f"{lv.base_cagr * 100:g}% BTC CAGR",
         f"The yearly bitcoin growth rate behind the target and the chart. The sidebar sets the bands "
         f"({', '.join(f'{b:.0%}' for b in lv.cagr_bands)}); the forecast table runs each one."),
    ])

# ------------------------------------------------------------------ how the price target is built
year, base_btc = T.year, (v["btc_gain"] / v["btc_yield"] if v["btc_yield"] else 0.0)
cash_sec, ntav_total = r.cash + stt.securities, r.ntav_per_share * r.fd_shares
split = ("" if v["premium_sata"] is None else
         f" · {common.signed(v['premium_sata'])} from SATA, {common.signed(v['premium_sats'])} from SATS, "
         f"{common.signed(v['premium_common'])} from common-funded bitcoin")
theme.section("How the price target is built", "(NTAV + k × the year's BTC $ Gain) ÷ diluted shares")
theme.ledger([
    {"n": "I", "title": f"What common owns · {T:%b %d, %Y}", "label": "NTAV per share",
     "math": f"{r.btc:,.0f} BTC × ${r.btc_price:,.0f} + {common.usd(cash_sec)} cash & STRC − "
             f"{common.usd(r.sata_notional)} SATA − {common.usd(r.sats_liquidation_preference)} SATS − "
             f"{common.usd(stt.debt)} debt = {common.usd(ntav_total)}, over {r.fd_shares / 1e6:,.1f}M diluted shares",
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
    tab_model, tab_dates, tab_table, tab_sata, tab_fcst, tab_hist = st.tabs(
        ["Model", "Attribution", "Price-target table", "SATA issuance", f"Forecast to {lv.horizon_end.year}",
         "PT history"])
    with tab_model:
        st.caption("Base case at the starting snapshot and each year end. BTC yield and BTC $ gain are for that "
                   "calendar year (year to date for the starting row). mNAV sets the common issuance price; "
                   "the price target uses the year's BTC earnings and k.")
        st.dataframe(detail.model_table(res["path"], res["values"], stt, lv), width="stretch")
        st.caption(common.md("SATS: 7M nonconvertible preferred shares, $700M stated amount, $608.15M estimated net "
                             "IPO proceeds, and a 15% annual dividend on stated value. It is included in preferred "
                             "claims and dividends; it does not add diluted common shares. The model uses its "
                             "$100 liquidation-preference floor. Future SATS issuance is not assumed."))
        st.markdown("[SATS final prospectus](https://www.sec.gov/Archives/edgar/data/1920406/000095010326015734/dp255138_424b5.htm)")
    with tab_dates:
        st.caption(common.md(
            f"Each year end valued the same way, {common.k_label(lv, res['implied_k'])}; new common sells at a market "
            f"mNAV {common.mnav_label(lv, m0)}; SATA dividends {common.rate_label(lv, rate)}."))
        labels = {**charts.LABELS, **charts.PREMIUM}
        table = a.rename(columns={"start": "NTAV today", "ntav_end": "NTAV at date", "end": "Price target", **labels})
        order = ["NTAV today", *[charts.LABELS[k] for k in valuation.PARTS if k != "growth_premium"],
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
            "- **NTAV**: what common owns per share (BTC + cash + STRC − preferred claims − debt, per diluted share).\n"
            "- **BTC move**: those net assets tracking BTC one-for-one. **Amplification**: what preferred-funded BTC gains, "
            "after the dividend reserve. **SATA / SATS dividends**: their separate costs. **SATS issuance cost**: "
            "the preferred claim less estimated net proceeds. **Common issuance**: common and "
            "warrant shares sold above NTAV per share. **Op. costs**: the net cash burn, not dividends.\n"
            "- **Growth premium**: k × the year's BTC $ Gain, split by who paid for the year's bitcoin. **Net-basis "
            "value** is a reference that credits preferred funding only with what its bitcoin earns above the dividend."))

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

    with tab_sata:
        sy = valuation.sata_by_year(res["path"], stt, lv)
        sy["period"] = [f"{r['from']:%b}–Dec {y}" if i == 0 and r["from"] != date(y - 1, 12, 31) else str(y)
                        for i, (y, r) in enumerate(sy.iterrows())]
        st.caption(common.md(
            f"Section 2 of the levers: ${lv.sata_weekly_usd / 1e6:,.1f}M of SATA a week through "
            f"{lv.sata_switch:%b %d, %Y}, then demand grows {lv.sata_growth:.0%} a year (compounding week by week), "
            f"always sold at $100 par. Dividends {common.rate_label(lv, rate)}. Strive keeps {lv.reserve_months:g} "
            f"months of dividends in cash and buys bitcoin with the rest."))
        last, at_t = sy.iloc[-1], sy.loc[T.year]
        end = lv.horizon_end
        theme.cards([
            (f"Weekly pace · {end:%b %Y}", common.usd(last["weekly_end"]), f"from ${lv.sata_weekly_usd / 1e6:,.0f}M a week now"),
            (f"Outstanding · {T:%b %Y}", common.usd(at_t["outstanding"]), f"from {common.usd(stt.sata_notional)} today"),
            (f"Outstanding · {end:%b %Y}", common.usd(last["outstanding"]), f"{last['amplification']:.0%} of the bitcoin"),
            (f"Dividends · {end.year}", common.usd(last["dividends"]), f"at {last['rate']:.2%}"),
        ])
        st.altair_chart(charts.sata_years(sy, c), width="stretch", theme=None)
        st.dataframe(pd.DataFrame({
            "Weekly pace": sy["weekly_end"].map(common.usd),
            "Sold": sy["sold"].map(common.usd),
            "Outstanding": sy["outstanding"].map(common.usd),
            "Dividends paid": sy["dividends"].map(common.usd),
            "Cash reserve": sy["reserve"].map(common.usd),
            "BTC bought": sy["btc_bought"].map(lambda v: f"{v:,.0f}"),
            "Amplification": sy["amplification"].map(lambda v: f"{v:.0%}"),
        }).set_axis(list(sy["period"])), width="stretch")
        st.caption("Weekly pace, outstanding, cash reserve and amplification are at year end. BTC bought = bitcoin "
                   "bought with SATA money: proceeds less the dividends paid and the cash reserve's top-up, at each "
                   "week's bitcoin price. Amplification = total preferred outstanding plus debt ÷ the bitcoin's value.")

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
        if (res["path"]["btc_bought_usd"] < 0).any():
            st.warning("The dividend reserve ran dry and BTC was sold in some weeks.")

    with tab_hist:
        hist = list(reversed(pub.history)) if pub else []
        if not hist:
            st.caption("No price target has been published yet.")
        else:
            st.caption(f"Every price target {pub.set_by} has published, newest first. Each is frozen as it was set: "
                       f"the target, its breakdown, and the levers and data behind it that day.")
            cols = [f"{datetime.fromisoformat(e['set_at']):%b %d, %Y · %H:%M} UTC" + (" (official)" if i == 0 else "")
                    for i, e in enumerate(hist)]

            def change(i):
                if i == len(hist) - 1:
                    return "—"
                d = hist[i]["price_target"] - hist[i + 1]["price_target"]
                return f"{common.signed(d)} ({d / hist[i + 1]['price_target']:+.0%})"

            target = pd.DataFrame({c: {
                "Price target": f"${e['price_target']:,.2f} at {date.fromisoformat(e['pt_date']):%b %d, %Y}",
                "Change vs the one before": change(i),
                "ASST when set": f"${e['asst_price']:,.2f}",
                "Upside when set": f"{e['price_target'] / e['asst_price'] - 1:+.0%}",
                "Data": f"8-K {date.fromisoformat(e['data_as_of']):%b %d} · prices {date.fromisoformat(e['prices_on']):%b %d, %Y}",
                "NTAV per share at the target": f"${e['ntav_per_share']:,.2f}",
                f"{date.fromisoformat(e['pt_date']).year} BTC Yield": f"{e['btc_yield']:.0%}",
                "Bitcoin earnings per share": f"${e['gain_per_share']:,.2f}",
                "Growth multiple k": f"{e['k_start']:.2f}x → {e['k']:.2f}x",
                "Growth premium": f"${e['growth_premium']:,.2f}",
                "Implied mNAV": f"{e['implied_mnav']:.2f}x",
            } for i, (c, e) in enumerate(zip(cols, hist))})
            st.subheader("The target and its breakdown")
            st.dataframe(target, width="stretch", height=(len(target) + 1) * 35 + 3)  # every row, no scroll

            def levers_row(e):
                x = e["levers"]
                return {
                    "BTC at the end of 2026": f"${x['ye_btc_price']:,.0f}",
                    "BTC growth after that": f"{x['base_cagr']:.0%} a year",
                    "BTC at the target date": f"${e['btc_price_at_target']:,.0f}",
                    "SATA per week now": f"${x['sata_weekly_usd'] / 1e6:,.1f}M",
                    "SATA demand growth": f"{x['sata_growth']:.0%} a year",
                    "SATA dividend rate": f"{e['sata_rate']:.2%}" + (
                        f" → {x['sata_rate_target']:.2%}" if x.get("sata_rate_target") is not None else ""),
                    "Common issuance": f"{x['common_weekly_pct']:.2%} of shares a week",
                    "Market mNAV": "follows the model" if x["market_mnav_mode"] == "model" else (
                        "held" if x.get("mnav_target") is None else f"glides to {x['mnav_target']:.2f}x"),
                    "Warrants exercised": f"{x['warrant_exercise']:.0%}",
                    "Net cash burn": f"${x['net_cash_burn_weekly_usd'] / 1e6:,.1f}M a week",
                }

            st.subheader("The levers behind it")
            behind = pd.DataFrame({c: levers_row(e) for c, e in zip(cols, hist)})
            st.dataframe(behind, width="stretch", height=(len(behind) + 1) * 35 + 3)

st.caption(common.md("Sources: " + " · ".join(f"{k}: {v}" for k, v in stt.sources.items())
                     + ". An independent modeling tool that applies your levers to Strive's published figures; not "
                     "affiliated with or endorsed by Strive, Inc. Not a recommendation."))

common.owner_panel(stt, lv, v, r.btc_price, pub, mode)
