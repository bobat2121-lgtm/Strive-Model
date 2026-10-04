"""The four levers, plus the fixed assumptions around them. Defaults live in config/levers.yaml (percents written as
percents there, fractions here)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import yaml

DEFAULT_PATH = Path(__file__).resolve().parents[1] / "config" / "levers.yaml"


@dataclass
class Levers:
    # 1) BTC: log-linear from today's price to the YE anchor, then a normalized CAGR (one run per band)
    ye_btc_price: float = 100_000.0
    ye_anchor: date = date(2026, 12, 31)
    cagr_bands: list[float] = field(default_factory=lambda: [0.30, 0.40, 0.50])
    base_cagr: float = 0.40                  # the band used for single-run outputs and the attribution
    # 2) SATA at $100 par: a fixed $ per week through sata_switch, then a % of the BTC stack (BTC NAV) per week,
    #    blended from one to the other over sata_glide_weeks so there's no cliff at the switch
    sata_weekly_usd: float = 70_000_000.0
    sata_switch: date = date(2026, 12, 31)
    sata_pct_of_btc_nav: float | None = 0.01  # weekly fraction; None keeps the fixed $ forever
    sata_glide_weeks: float = 13.0
    sata_rate: float | None = None           # None = Strive's current rate (13%), the starting point
    sata_rate_target: float | None = None    # None holds the rate static; a number glides to it by sata_rate_glide_to
    sata_rate_glide_to: date = date(2027, 12, 31)
    reserve_months: float = 18.0             # months of SATA dividends Strive keeps in cash
    # 3) Common: new shares each week as a fraction of FD shares, sold at the modeled price
    common_weekly_pct: float = 0.005
    # 4) Valuation, TD Cowen's structure: price target = NTAV per share + k x the next year's gain per share
    pt_date: date = date(2028, 12, 31)
    growth_multiple: float = 3.0             # k
    gain_basis: str = "net"                  # "net": growth in net BTC per share; "gross": Strive's BTC Yield
    k_table: list[float] = field(default_factory=lambda: [1.0, 2.0, 3.0, 4.0, 5.0])
    # Market mNAV (price / NTAV per share) during the forecast: the price new common sells at. None holds today's;
    # a target glides today's multiple to it by mnav_glide_to. It doesn't enter the price target directly.
    mnav_target: float | None = None
    mnav_glide_to: date = date(2026, 12, 31)
    # Fixed assumptions
    warrant_date: date = date(2026, 10, 13)
    warrant_exercise: float = 1.0            # fraction exercised if ASST is above the strike that week; the rest lapse
    warrant_strike: float = 27.0
    net_cash_burn_weekly_usd: float = 1_200_000.0
    horizon_end: date = date(2031, 12, 31)    # the forecast runs past the price target so its forward year exists


def _pct(x):
    return None if x is None else float(x) / 100


def load(path: Path | str = DEFAULT_PATH) -> Levers:
    c = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    btc, sata, common = c.get("btc") or {}, c.get("sata") or {}, c.get("common") or {}
    m, w, costs = c.get("mnav") or {}, c.get("warrants") or {}, c.get("costs") or {}
    val = c.get("valuation") or {}
    d = Levers()
    bands = [_pct(x) for x in btc.get("cagr_bands_pct") or []] or d.cagr_bands
    return Levers(
        ye_btc_price=float(btc.get("ye_price", d.ye_btc_price)),
        ye_anchor=btc.get("ye_anchor", d.ye_anchor),
        cagr_bands=bands,
        base_cagr=_pct(btc["base_cagr_pct"]) if btc.get("base_cagr_pct") is not None else bands[len(bands) // 2],
        sata_weekly_usd=float(sata.get("weekly_usd", d.sata_weekly_usd)),
        sata_switch=sata.get("switch_date", d.sata_switch),
        sata_pct_of_btc_nav=_pct(sata.get("pct_of_btc_stack_weekly", d.sata_pct_of_btc_nav * 100)),
        sata_glide_weeks=float(sata.get("glide_weeks", d.sata_glide_weeks)),
        sata_rate=_pct(sata.get("rate_pct")),
        sata_rate_target=_pct(sata.get("rate_target_pct")),
        sata_rate_glide_to=sata.get("rate_glide_to", d.sata_rate_glide_to),
        reserve_months=float(sata.get("reserve_months", d.reserve_months)),
        common_weekly_pct=_pct(common.get("weekly_pct", d.common_weekly_pct * 100)),
        mnav_target=float(m["target"]) if m.get("target") is not None else None,
        mnav_glide_to=m.get("glide_to", d.mnav_glide_to),
        pt_date=val.get("price_target_date", d.pt_date),
        growth_multiple=float(val.get("growth_multiple", d.growth_multiple)),
        gain_basis=str(val.get("gain_basis", d.gain_basis)),
        k_table=[float(x) for x in val.get("table") or d.k_table],
        warrant_date=w.get("exercise_date", d.warrant_date),
        warrant_exercise=_pct(w.get("exercise_pct", d.warrant_exercise * 100)),
        warrant_strike=float(w.get("strike", d.warrant_strike)),
        net_cash_burn_weekly_usd=float(costs.get("net_cash_burn_weekly_usd", d.net_cash_burn_weekly_usd)),
        horizon_end=c.get("horizon_end", d.horizon_end),
    )
