"""Shared pieces for the Streamlit pages: cached data and model runs, the lever sidebar, number formats, chart colors."""
from __future__ import annotations

import hmac
import math
import os
import time
from dataclasses import replace
from datetime import date

import httpx
import streamlit as st

from model import engine, levers, metrics, published, state, valuation

DATA_KEY = "data_mode"          # "published" (the owner's frozen snapshot), "latest" or "live"
OWNER_KEY, OWNER_MSG, OWNER_PW = "owner_unlocked", "owner_msg", "owner_pw"
OWNER_HANDLE = "@WallyXIX"
DATA_LABELS = {"latest": "Latest 8-K and close", "live": "Latest 8-K, live prices"}


@st.cache_data(ttl=600, show_spinner="Loading Strive's dashboard…")
def load_state(live_prices: bool) -> state.State:
    return state.load(live_prices=live_prices)


@st.cache_data(show_spinner=False)
def defaults() -> levers.Levers:
    return levers.load()


@st.cache_data(show_spinner="Running the model…", max_entries=64)
def compute(st_: state.State, lv: levers.Levers) -> dict:
    path, _, settled = valuation.solve_market(st_, lv, lv.base_cagr)
    return {"table": valuation.table(st_, lv), "attribution": valuation.attribution(st_, lv, lv.base_cagr),
            "path": path, "implied_k": valuation.implied_k(st_), "settled": settled,
            "values": {d: valuation.price_target(path, st_, d, lv) for d in valuation.valuation_dates(st_, lv)}}


def current_published() -> published.Published | None:
    return published.load()


def data_modes(pub: published.Published | None) -> list[str]:
    return (["published"] if pub else []) + ["latest", "live"]


def current_state(pub: published.Published | None) -> tuple[state.State, str]:
    """(the data this run uses, its mode). Everyone opens on the published snapshot; the sidebar can switch to the
    latest data, in this session only."""
    mode = st.session_state.get(DATA_KEY)
    if mode not in data_modes(pub):
        mode = data_modes(pub)[0]
        st.session_state.pop(DATA_KEY, None)
    return (pub.state if mode == "published" else load_state(mode == "live")), mode


def is_live(lv: levers.Levers, mode: str, pub: published.Published | None) -> bool:
    """Is this session showing the published price target (published data, published levers)?"""
    return pub is not None and mode == "published" and published.same_levers(lv, pub.levers)


def price_now(mode: str, st_: state.State) -> float:
    """ASST today: the published snapshot is frozen, so take the latest close for "vs today"."""
    if mode != "published":
        return st_.share_price
    try:
        return load_state(False).share_price
    except Exception:  # no data source reachable: the snapshot's price
        return st_.share_price


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
    if lv.market_mnav_mode == "model":
        return f"that follows the model's own valuation (from today's {m0:.2f}x)"
    if lv.mnav_target is None:
        return f"held at today's {m0:.2f}x"
    return f"{m0:.2f}x gliding to {lv.mnav_target:.2f}x by {lv.mnav_glide_to:%b %d, %Y}"


def k_label(lv: levers.Levers, k_today: float) -> str:
    if not lv.k_glide:
        return f"k = {lv.growth_multiple:g}x"
    k0 = lv.k_start if lv.k_start is not None else k_today
    return f"k gliding from {k0:.2f}x to {lv.growth_multiple:g}x by {lv.k_glide_to:%b %d, %Y}"


def rate_label(lv: levers.Levers, rate_now: float) -> str:
    if lv.sata_rate_target is None:
        return f"at a static {rate_now:.2%}"
    return f"at {rate_now:.2%} gliding to {lv.sata_rate_target:.2%} by {lv.sata_rate_glide_to:%b %d, %Y}"


# ------------------------------------------------------------------ chart colors (from the active theme)

def colors() -> dict:
    from panel import theme
    return theme.palette()


# ------------------------------------------------------------------ the lever sidebar

def _floats(text: str, fallback: list[float], scale: float = 1.0, lo: float = -1e9, hi: float = 1e9,
            most: int = 8) -> list[float]:
    """Comma-separated numbers, kept within [lo, hi] and to at most `most` of them (each one is a model run per row
    of the table, on a server every viewer shares)."""
    try:
        vals = sorted({min(max(float(x) * scale, lo), hi) for x in text.replace("%", "").replace("x", "").split(",")
                       if x.strip()})
    except ValueError:
        st.sidebar.error(f"Couldn't read “{text}”; using the defaults.")
        return fallback
    if len(vals) > most:
        st.sidebar.caption(f"Using the first {most} values.")
    return vals[:most] or fallback


def _date_in(lo: date, hi: date, d: date) -> date:
    return min(max(d, lo), hi)


def _reset_levers() -> None:
    """Back to the published price target: forget this session's lever edits and data choice."""
    for key in [k for k in st.session_state if str(k).startswith("lv.")]:
        del st.session_state[key]
    st.session_state.pop(DATA_KEY, None)


def sidebar(st_: state.State, pub: published.Published | None, mode: str) -> levers.Levers:
    """Every lever, opening on the published settings (config/levers.yaml if nothing is published). Edits stay in
    this session. Widget keys carry the publication's time, so a new publication resets everyone to it."""
    d = pub.levers if pub else defaults()
    v = f"lv.{pub.set_at.isoformat() if pub else 'cfg'}."
    m0 = metrics.mnav(st_, st_.share_price)
    with st.sidebar:
        st.header("Levers")
        top = st.container()

        with st.expander("1 · BTC price", expanded=True):
            ye = st.number_input(f"BTC on {d.ye_anchor:%b %d, %Y} ($)", min_value=1000.0, max_value=10_000_000.0,
                                 value=d.ye_btc_price,
                                 step=5000.0, format="%.0f", key=v + "ye")
            bands = _floats(st.text_input("CAGR bands after that (%)", ", ".join(f"{g * 100:g}" for g in d.cagr_bands),
                                          key=v + "bands",
                                          help="Comma-separated. The base case below drives the price target, the "
                                               "chart and the breakdown; every band gets a column in the price-target "
                                               "table (Full model detail)."),
                            d.cagr_bands, 0.01, lo=-0.5, hi=2.0, most=6)
            base_ix = bands.index(d.base_cagr) if d.base_cagr in bands else len(bands) // 2
            base = st.selectbox("Base case", bands, index=base_ix, format_func=lambda g: f"{g * 100:g}% CAGR",
                                key=v + "base")

        with st.expander("2 · SATA at $100 par", expanded=True):
            weekly = st.number_input(f"$M per week through {d.sata_switch:%b %d, %Y}", min_value=0.0, max_value=5000.0,
                                     value=d.sata_weekly_usd / 1e6, step=5.0, format="%.1f", key=v + "weekly",
                                     help="Recent run-rate: $72.7M/week (6 weeks to 9/25/26).")
            growth = st.number_input(f"Demand growth after {d.sata_switch:%b %d, %Y} (% a year)", min_value=-50.0,
                                     max_value=200.0, value=d.sata_growth * 100, step=5.0, format="%.0f",
                                     key=v + "growth",
                                     help="Weekly SATA issuance grows this much a year after the switch date. At 50%, "
                                          "SATA outstanding reaches about $13B by end-2028 (Strategy's whole preferred "
                                          "stack is ~$15B today).")
            rate_now = d.sata_rate if d.sata_rate is not None else st_.sata_rate
            glide_rate = st.toggle(f"Glide the dividend rate (now {rate_now:.2%})",
                                   value=d.sata_rate_target is not None, key=v + "glide_rate",
                                   help="Off: the rate holds at today's level. On: it moves in a straight line to the "
                                        "target by the date, then holds.")
            rate_target = st.number_input("Rate to glide to (%)", min_value=0.0, max_value=30.0,
                                          value=(d.sata_rate_target or 0.12) * 100, step=0.25, format="%.2f",
                                          disabled=not glide_rate, key=v + "rate_target")
            rate_by = st.date_input("Rate reaches it by", value=_date_in(st_.price_date, d.horizon_end, d.sata_rate_glide_to),
                                    min_value=st_.price_date, max_value=d.horizon_end, disabled=not glide_rate,
                                    key=v + "rate_by")

        with st.expander("3 · Common issuance", expanded=True):
            common = st.number_input("New shares per week (% of FD shares)", min_value=0.0, max_value=10.0,
                                     value=d.common_weekly_pct * 100, step=0.05, format="%.2f", key=v + "common",
                                     help="6-week average 1.86% (front-loaded); last 3 weeks 0.50%.")

        with st.expander("4 · Price target", expanded=True):
            dates = valuation.valuation_dates(st_, d)
            pt_date = st.selectbox("Target date", dates, index=dates.index(d.pt_date) if d.pt_date in dates else 0,
                                   format_func=lambda x: f"{x:%b %d, %Y}", key=v + "pt_date")
            k_now = valuation.implied_k(st_)
            k_glide = st.toggle("Glide k", value=d.k_glide, key=v + "k_glide",
                                help="On: k moves in a straight line from the starting k (on the data date) to the k "
                                     "it glides to, by the date, then holds. Off: one k throughout.")
            # the starting k is the k the price implied when the target was set; on fresh data, today's
            k0 = d.k_start if (mode == "published" and d.k_start is not None) else k_now
            k_start = st.number_input("Starting k", min_value=0.0, max_value=20.0, value=min(round(k0, 2), 20.0),
                                      step=0.05, format="%.2f",
                                      disabled=not k_glide, key=v + f"k_start.{mode}",
                                      help=f"Where the glide starts, on {st_.price_date:%b %d, %Y}. It opens at the k "
                                           f"the price implied when the target was set; that data's price implies "
                                           f"{k_now:.2f}x on Strive's trailing 12 months.")
            k = st.number_input("k it glides to" if k_glide else "k", min_value=0.0, max_value=20.0,
                                value=d.growth_multiple,
                                step=0.25, format="%.2f", key=v + "k",
                                help="Price target = (NTAV + k × the year's BTC $ Gain) ÷ diluted shares.")
            k_by = st.date_input("k reaches it by", value=_date_in(st_.price_date, d.horizon_end, d.k_glide_to),
                                 min_value=st_.price_date, max_value=d.horizon_end, disabled=not k_glide, key=v + "k_by")
            rows = _floats(st.text_input("Price-target table rows (k at the end of the glide)",
                                         ", ".join(f"{x:g}" for x in d.k_table), key=v + "rows"), d.k_table,
                          lo=0.0, hi=20.0, most=8)

        with st.expander("5 · Market mNAV", expanded=True):
            st.caption("The price new common sells at during the forecast (ASST ÷ NTAV per diluted share).")
            mnav_mode = st.radio("Market mNAV", ["model", "manual"], index=0 if d.market_mnav_mode == "model" else 1,
                                 label_visibility="collapsed", key=v + "mnav_mode",
                                 format_func=lambda x: {"model": "Follow the model's valuation",
                                                        "manual": "Manual (hold or glide)"}[x],
                                 help="Follow: at each year end the market multiple equals the price target's "
                                      "implied mNAV (solved), so shares sell at what the model says they're worth.")
            manual = mnav_mode == "manual"
            hold = st.toggle(f"Hold today's {m0:.2f}x", value=d.mnav_target is None, disabled=not manual,
                             key=v + "hold")
            target = st.number_input("Glide to (x)", min_value=0.1, max_value=20.0, value=d.mnav_target or 2.0,
                                     step=0.05,
                                     format="%.2f", disabled=not manual or hold, key=v + "mnav_target")
            glide_to = st.date_input("Reach it by", value=_date_in(st_.price_date, d.horizon_end, d.mnav_glide_to),
                                     min_value=st_.price_date, max_value=d.horizon_end, disabled=not manual or hold,
                                     key=v + "mnav_by")

        with st.expander("6 · Warrants and costs", expanded=True):
            wex = st.slider(f"PIPE warrants exercised on {d.warrant_date:%b %d} (%)", 0, 100,
                            int(round(d.warrant_exercise * 100)), key=v + "wex",
                            help=f"{st_.warrants / 1e6:.2f}M at ${d.warrant_strike:g}, only if ASST is above the strike "
                                 "that week. The date comes from a CEO post on X, not yet a filing.")
            burn = st.number_input("Net cash burn ($M per week)", min_value=0.0, max_value=100.0,
                                   value=d.net_cash_burn_weekly_usd / 1e6, step=0.1, format="%.1f", key=v + "burn")

        st.divider()
        modes = data_modes(pub)
        st.radio("Data", modes, key=DATA_KEY,
                 format_func=lambda m: (f"As published ({pub.state.price_date:%b %d, %Y})" if m == "published"
                                        else DATA_LABELS[m]),
                 help="As published: the 8-K and prices the price target was set on, frozen. Latest: today's "
                      "data from strive.com (and live prices if you pick them). Your choice stays in your session.")
        if mode != "published" and st.button("Refresh data", width="stretch"):
            load_state.clear()
            compute.clear()
            st.rerun()

    lv = replace(d, ye_btc_price=ye, cagr_bands=bands, base_cagr=base, sata_weekly_usd=weekly * 1e6,
                 sata_rate_target=rate_target / 100 if glide_rate else None, sata_rate_glide_to=rate_by,
                 sata_growth=growth / 100,
                 common_weekly_pct=common / 100, mnav_target=None if hold else target, mnav_glide_to=glide_to,
                 market_mnav_mode=mnav_mode, pt_date=pt_date, growth_multiple=k, k_glide=k_glide, k_start=k_start,
                 k_glide_to=k_by, k_table=rows,
                 warrant_exercise=wex / 100, net_cash_burn_weekly_usd=burn * 1e6)
    if pub is not None and not is_live(lv, mode, pub):
        with top:
            st.caption(f"You're exploring your own scenario; the published target is ${pub.price_target:,.2f}. "
                       "Changes stay on your screen.")
            st.button("Reset to the published target", on_click=_reset_levers, width="stretch")
    return lv


# ------------------------------------------------------------------ the owner panel

MAX_FAILS, FAIL_WINDOW, LOCKOUT, OWNER_IDLE = 10, 15 * 60, 15 * 60, 30 * 60  # seconds


@st.cache_resource
def _unlock_guard() -> dict:
    """Wrong owner passwords across every session on this server (a restart clears it): guessing at scale locks
    the panel for a while, whichever browser the guesses come from."""
    return {"fails": [], "locked_until": 0.0}


def _owner_unlocked() -> bool:
    """Unlocked in this session, and not idle past OWNER_IDLE (it re-locks itself)."""
    t = st.session_state.get(OWNER_KEY)
    return isinstance(t, float) and time.time() - t < OWNER_IDLE


def _unlock() -> None:
    secret = os.environ.get("OWNER_PASSWORD", "")
    typed = st.session_state.get(OWNER_PW, "")
    st.session_state[OWNER_PW] = ""
    g, now = _unlock_guard(), time.time()
    if now < g["locked_until"]:
        st.session_state[OWNER_MSG] = ("error", f"Too many wrong passwords. Try again in "
                                                f"{math.ceil((g['locked_until'] - now) / 60)} min.")
        return
    if secret and hmac.compare_digest(typed.encode("utf-8"), secret.encode("utf-8")):
        st.session_state[OWNER_KEY] = now
        st.session_state.pop(OWNER_MSG, None)
        return
    g["fails"] = [t for t in g["fails"] if now - t < FAIL_WINDOW] + [now]
    if len(g["fails"]) >= MAX_FAILS:
        g["locked_until"], g["fails"] = now + LOCKOUT, []
    time.sleep(1.5)  # slow down guessing
    st.session_state[OWNER_MSG] = ("error", "Wrong password.")


def _lock() -> None:
    st.session_state[OWNER_KEY] = None
    st.session_state.pop(OWNER_MSG, None)


def _publish(lv: levers.Levers, st_: state.State, value: dict, btc_at_target: float) -> None:
    if not _owner_unlocked():
        return
    prev = current_published()
    p = published.make(lv, st_, value["price_target"], OWNER_HANDLE)
    p = replace(p, history=[*(prev.history if prev else []), published.entry(p, value, btc_at_target)])
    published.save_local(p)
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        msg = ("warning", "Live for every viewer on this server, but not saved to GitHub, so it resets when the app "
                          "restarts. Add a GITHUB_TOKEN secret to make it permanent.")
    else:
        try:
            url = published.commit(p, token)
            msg = ("success", f"Live for every viewer, and saved to GitHub ({url}).")
        except httpx.HTTPStatusError as e:
            msg = ("error", f"Live on this server, but GitHub refused the save (HTTP {e.response.status_code}), so "
                            "it resets on the next restart. Check that GITHUB_TOKEN can write this repo's contents.")
        except httpx.HTTPError:
            msg = ("error", "Live on this server, but GitHub couldn't be reached, so it resets on the next restart. "
                            "Try publishing again.")
    st.session_state[OWNER_MSG] = msg
    _reset_levers()  # the owner now sees the new live target too


def owner_panel(st_: state.State, lv: levers.Levers, value: dict, btc_at_target: float,
                pub: published.Published | None, mode: str) -> None:
    """Password-locked: set this session's levers and data as the live price target for every viewer."""
    with st.sidebar, st.expander("Owner", expanded=bool(st.session_state.get(OWNER_MSG) or _owner_unlocked())):
        kind, text = st.session_state.get(OWNER_MSG, (None, None))
        if not os.environ.get("OWNER_PASSWORD"):
            st.caption("Publishing is off: set an OWNER_PASSWORD secret to turn it on.")
            return
        if not _owner_unlocked():
            st.text_input("Password", type="password", key=OWNER_PW)
            st.button("Unlock", on_click=_unlock, width="stretch")
            if kind == "error":
                st.error(text)
            return
        if kind:
            getattr(st, kind)(text)
        T = lv.pt_date
        if is_live(lv, mode, pub):
            st.caption(f"Viewers see these settings: ${value['price_target']:,.2f} at {T:%b %d, %Y}, set "
                       f"{pub.set_at:%b %d, %Y}. Change levers or the data to publish a new target.")
        else:
            st.markdown(md(f"Set **${value['price_target']:,.2f}** at {T:%b %d, %Y} as the live price target, on these "
                           f"levers and the data as of {st_.as_of:%b %d} (prices {st_.price_date:%b %d, %Y})."))
            st.button("Set as the live price target", type="primary", width="stretch", on_click=_publish,
                      args=(lv, st_, value, btc_at_target))
        st.button("Lock", on_click=_lock, width="stretch")
