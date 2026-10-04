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
    # 2) SATA at $100 par, demand-led: a fixed $ per week through sata_switch, then growing at sata_growth a year
    sata_weekly_usd: float = 70_000_000.0
    sata_switch: date = date(2026, 12, 31)
    sata_growth: float = 0.50                # annual growth in weekly SATA demand after the switch
    sata_rate: float | None = None           # None = Strive's current rate (13%), the starting point
    sata_rate_target: float | None = None    # None holds the rate static; a number glides to it by sata_rate_glide_to
    sata_rate_glide_to: date = date(2027, 12, 31)
    reserve_months: float = 18.0             # months of SATA dividends Strive keeps in cash
    # 3) Common: new shares each week as a fraction of FD shares, sold at the modeled price
    common_weekly_pct: float = 0.005
    # 4) Valuation, TD Cowen's method: price target = (NTAV + k x the year's BTC $ Gain) / FD shares
    pt_date: date = date(2028, 12, 31)
    growth_multiple: float = 3.0             # k at the end of the glide (TD Cowen: 3x on ASST)
    k_glide: bool = True                     # start k at what today's price implies and glide to growth_multiple
    k_glide_to: date = date(2028, 12, 31)
    k_table: list[float] = field(default_factory=lambda: [1.0, 2.0, 3.0, 4.0, 5.0])
    # Market mNAV (price / NTAV per share) during the forecast: the price new common sells at. "model" makes it equal
    # the model's own valuation at each year end (solved); "manual" holds today's (mnav_target None) or glides to it.
    market_mnav_mode: str = "model"
    mnav_target: float | None = None
    mnav_glide_to: date = date(2026, 12, 31)
    # Fixed assumptions
    warrant_date: date = date(2026, 10, 13)
    warrant_exercise: float = 1.0            # fraction exercised if ASST is above the strike that week; the rest lapse
    warrant_strike: float = 27.0
    net_cash_burn_weekly_usd: float = 1_200_000.0
    horizon_end: date = date(2031, 12, 31)    # the forecast runs past the price target


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
        sata_growth=_pct(sata.get("growth_pct", d.sata_growth * 100)),
        sata_rate=_pct(sata.get("rate_pct")),
        sata_rate_target=_pct(sata.get("rate_target_pct")),
        sata_rate_glide_to=sata.get("rate_glide_to", d.sata_rate_glide_to),
        reserve_months=float(sata.get("reserve_months", d.reserve_months)),
        common_weekly_pct=_pct(common.get("weekly_pct", d.common_weekly_pct * 100)),
        mnav_target=float(m["target"]) if m.get("target") is not None else None,
        mnav_glide_to=m.get("glide_to", d.mnav_glide_to),
        pt_date=val.get("price_target_date", d.pt_date),
        growth_multiple=float(val.get("growth_multiple", d.growth_multiple)),
        k_glide=bool(val.get("glide_from_today", d.k_glide)),
        k_glide_to=val.get("glide_to", d.k_glide_to),
        market_mnav_mode=str(m.get("mode", d.market_mnav_mode)),
        k_table=[float(x) for x in val.get("table") or d.k_table],
        warrant_date=w.get("exercise_date", d.warrant_date),
        warrant_exercise=_pct(w.get("exercise_pct", d.warrant_exercise * 100)),
        warrant_strike=float(w.get("strike", d.warrant_strike)),
        net_cash_burn_weekly_usd=float(costs.get("net_cash_burn_weekly_usd", d.net_cash_burn_weekly_usd)),
        horizon_end=c.get("horizon_end", d.horizon_end),
    )
