"""The annual model table, shared by the page and its presentation checks."""
from __future__ import annotations

import pandas as pd

from model import engine, valuation
from panel.common import usd


MODEL_COLUMNS = [
    "BTC Price", "BTC held", "SATA", "SATS", "SATA per week", "Amplification",
    "Diluted shares", "NTAV per share", "mNAV", "BTC yield",
    "BTC $ gain for that year", "k multiple", "Price target",
]


def model_table(path, values, state, levers) -> pd.DataFrame:
    """Current snapshot and each forecast year end, with annual (not cumulative) BTC earnings."""
    dates = [state.price_date, *values]
    rows = []
    for day in dates:
        row = engine.at(path, day)
        value = values.get(day) or valuation.price_target(path, state, day, levers)
        rows.append({
            "BTC Price": f"${row.btc_price:,.0f}",
            "BTC held": f"{row.btc:,.0f}",
            "SATA": usd(row.sata_notional),
            "SATS": usd(row.get("sats_notional", 0.0)),
            "SATA per week": usd(engine.sata_per_week(levers, day)),
            "Amplification": f"{row.amplification:.1%}",
            "Diluted shares": f"{row.fd_shares / 1e6:,.2f}M",
            "NTAV per share": f"${row.ntav_per_share:,.2f}",
            "mNAV": f"{row.mnav:.2f}×",
            "BTC yield": f"{value['btc_yield']:.1%}",
            "BTC $ gain for that year": usd(value["btc_gain"] * row.btc_price),
            "k multiple": f"{value['k']:.2f}×",
            "Price target": f"${value['price_target']:,.2f}",
        })
    labels = [f"{day:%b %d, %Y}" + (" (start)" if i == 0 else " (target)" if day == levers.pt_date else "")
              for i, day in enumerate(dates)]
    return pd.DataFrame(rows, index=pd.Index(labels, name="Date"), columns=MODEL_COLUMNS)
