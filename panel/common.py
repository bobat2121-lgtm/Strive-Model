"""Shared pieces for the Streamlit pages: cached data and model runs, the lever sidebar, number formats, chart colors."""
from __future__ import annotations

from dataclasses import replace

import streamlit as st

from model import engine, levers, metrics, state, valuation

LIVE_KEY = "live_prices"


@st.cache_data(ttl=600, show_spinner="Loading Strive's dashboard…")
def load_state(live_prices: bool) -> state.State:
    return state.load(live_prices=live_prices)


@st.cache_data(show_spinner=False)
def defaults() -> levers.Levers:
    return levers.load()


@st.cache_data(show_spinner="Running the model…", max_entries=64)
def compute(st_: state.State, lv: levers.Levers) -> dict:
    path = engine.run(st_, lv, lv.base_cagr, lv.mnav_target)
    return {"table": valuation.table(st_, lv), "attribution": valuation.attribution(st_, lv, lv.base_cagr),
            "path": path, "implied_k": valuation.implied_k(st_),
            "values": {d: valuation.price_target(path, st_, d, lv) for d in valuation.valuation_dates(st_, lv)}}


def current_state() -> state.State:
    return load_state(st.session_state.get(LIVE_KEY, False))


# ------------------------------------------------------------------ formats

def usd(x: float) -> str:
    a = abs(x)
    s = f"${a / 1e9:.2f}B" if a >= 1e9 else f"${a / 1e6:.1f}M" if a >= 1e4 else f"${a:,.2f}"
    return "-" + s if x < 0 else s


def md(text: str) -> str:
    """Escape $ so Streamlit's markdown doesn't read a pair of dollar amounts as LaTeX."""
    return text.replace("$", r"\$")


def tiles(items: list[tuple]) -> None:
    """A row of metric tiles that wraps on narrow screens instead of truncating. Items: (label, value, help[, delta])."""
    with st.container(horizontal=True, gap="small"):
        for label, value, help_, *delta in items:
            st.metric(label, value, delta[0] if delta else None, help=help_, border=True, width=200 if delta else 150)


def signed(x: float) -> str:
    return f"{'+' if x >= 0 else '−'}${abs(x):,.2f}"


def mnav_label(lv: levers.Levers, m0: float) -> str:
    return f"held at today's {m0:.2f}x" if lv.mnav_target is None else \
        f"{m0:.2f}x gliding to {lv.mnav_target:.2f}x by {lv.mnav_glide_to:%b %d, %Y}"


def rate_label(lv: levers.Levers, rate_now: float) -> str:
    if lv.sata_rate_target is None:
        return f"at a static {rate_now:.2%}"
    return f"at {rate_now:.2%} gliding to {lv.sata_rate_target:.2%} by {lv.sata_rate_glide_to:%b %d, %Y}"


# ------------------------------------------------------------------ chart colors (validated: dataviz validate_palette.js)

_PALETTE = {
    "light": {"up": "#2a78d6", "down": "#e34948", "total": "#898781", "s1": "#2a78d6", "s2": "#eb6834",
              "ink2": "#52514e", "muted": "#898781", "rule": "#c3c2b7"},
    "dark": {"up": "#3987e5", "down": "#e66767", "total": "#898781", "s1": "#3987e5", "s2": "#d95926",
             "ink2": "#c3c2b7", "muted": "#898781", "rule": "#383835"},
}


def colors() -> dict:
    kind = getattr(getattr(st.context, "theme", None), "type", None)
    return _PALETTE["dark" if kind == "dark" else "light"]


# ------------------------------------------------------------------ the lever sidebar

def _floats(text: str, fallback: list[float], scale: float = 1.0) -> list[float]:
    try:
        vals = sorted({float(x) * scale for x in text.replace("%", "").replace("x", "").split(",") if x.strip()})
        return vals or fallback
    except ValueError:
        st.sidebar.error(f"Couldn't read “{text}”; using the defaults.")
        return fallback


def sidebar(st_: state.State) -> levers.Levers:
    """Every lever, defaulting to config/levers.yaml. Returns the Levers for this run."""
    d = defaults()
    m0 = metrics.mnav(st_, st_.share_price)
    with st.sidebar:
        st.header("Levers")

        st.subheader("1 · BTC price")
        ye = st.number_input(f"BTC on {d.ye_anchor:%b %d, %Y} ($)", min_value=1000.0, value=d.ye_btc_price,
                             step=5000.0, format="%.0f")
        bands = _floats(st.text_input("CAGR bands after that (%)", ", ".join(f"{g * 100:g}" for g in d.cagr_bands),
                                      help="Comma-separated. Each band is a column of the price table."),
                        d.cagr_bands, 0.01)
        base_ix = bands.index(d.base_cagr) if d.base_cagr in bands else len(bands) // 2
        base = st.selectbox("Base case", bands, index=base_ix, format_func=lambda g: f"{g * 100:g}% CAGR")

        st.subheader("2 · SATA at $100 par")
        weekly = st.number_input(f"$M per week through {d.sata_switch:%b %d, %Y}", min_value=0.0,
                                 value=d.sata_weekly_usd / 1e6, step=5.0, format="%.1f",
                                 help="Recent run-rate: $72.7M/week (6 weeks to 9/25/26).")
        growth = st.number_input(f"Demand growth after {d.sata_switch:%b %d, %Y} (% a year)", min_value=-50.0,
                                 max_value=200.0, value=d.sata_growth * 100, step=5.0, format="%.0f",
                                 help="Weekly SATA issuance grows this much a year after the switch date. At 50%, "
                                      "SATA outstanding reaches about $13B by end-2028 (Strategy's whole preferred stack is ~$15B today).")
        rate_now = d.sata_rate if d.sata_rate is not None else st_.sata_rate
        glide_rate = st.toggle(f"Glide the dividend rate (now {rate_now:.2%})", value=d.sata_rate_target is not None,
                               help="Off: the rate holds at today's level. On: it moves in a straight line to the "
                                    "target by the date, then holds.")
        rate_target = st.number_input("Rate to glide to (%)", min_value=0.0, max_value=30.0,
                                      value=(d.sata_rate_target or 0.12) * 100, step=0.25, format="%.2f",
                                      disabled=not glide_rate)
        rate_by = st.date_input("Rate reaches it by", value=d.sata_rate_glide_to, disabled=not glide_rate)

        st.subheader("3 · Common issuance")
        common = st.number_input("New shares per week (% of FD shares)", min_value=0.0,
                                 value=d.common_weekly_pct * 100, step=0.05, format="%.2f",
                                 help="6-week average 1.86% (front-loaded); last 3 weeks 0.50%.")

        st.subheader("4 · Price target")
        dates = valuation.valuation_dates(st_, d)
        pt_date = st.selectbox("Target date", dates, index=dates.index(d.pt_date) if d.pt_date in dates else 0,
                               format_func=lambda x: f"{x:%b %d, %Y}")
        k = st.number_input("Growth multiple k (× the year's BTC $ Gain)", min_value=0.0, value=d.growth_multiple,
                            step=0.25, format="%.2f",
                            help="TD Cowen's method: price target = (NTAV + k × the year's BTC $ Gain) ÷ diluted "
                                 "shares. TD Cowen uses 3x; the page shows the k today's price implies.")
        rows = _floats(st.text_input("Price-target table rows (k)", ", ".join(f"{x:g}" for x in d.k_table)),
                       d.k_table)

        st.subheader("5 · Market mNAV")
        st.caption("The price new common sells at during the forecast (ASST ÷ NTAV per diluted share).")
        hold = st.toggle(f"Hold today's {m0:.2f}x", value=d.mnav_target is None)
        target = st.number_input("Glide to (x)", min_value=0.1, value=d.mnav_target or 2.0, step=0.05,
                                 format="%.2f", disabled=hold)
        glide_to = st.date_input("Reach it by", value=d.mnav_glide_to, disabled=hold)

        with st.expander("Warrants and costs"):
            wex = st.slider(f"PIPE warrants exercised on {d.warrant_date:%b %d} (%)", 0, 100,
                            int(d.warrant_exercise * 100),
                            help=f"{st_.warrants / 1e6:.2f}M at ${d.warrant_strike:g}, only if ASST is above the strike "
                                 "that week. The date comes from a CEO post on X, not yet a filing.")
            burn = st.number_input("Net cash burn ($M per week)", min_value=0.0,
                                   value=d.net_cash_burn_weekly_usd / 1e6, step=0.1, format="%.1f")

        st.divider()
        st.toggle("Live prices (Coinbase BTC, Yahoo ASST)", key=LIVE_KEY)
        if st.button("Refresh data", width="stretch"):
            load_state.clear()
            compute.clear()
            st.rerun()

    return replace(d, ye_btc_price=ye, cagr_bands=bands, base_cagr=base, sata_weekly_usd=weekly * 1e6,
                   sata_rate_target=rate_target / 100 if glide_rate else None, sata_rate_glide_to=rate_by,
                   sata_growth=growth / 100,
                   common_weekly_pct=common / 100, mnav_target=None if hold else target, mnav_glide_to=glide_to,
                   pt_date=pt_date, growth_multiple=k, k_table=rows,
                   warrant_exercise=wex / 100, net_cash_burn_weekly_usd=burn * 1e6)
