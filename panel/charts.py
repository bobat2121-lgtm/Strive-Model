"""Altair charts. Marks follow the dataviz spec: bars <= 24px with 4px rounded ends, 2px lines, a hover layer on every
chart, text in ink colors (never the series color), one y-axis per chart."""
from __future__ import annotations

import altair as alt
import pandas as pd

LABELS = {"btc_move": "BTC move", "amplification": "Amplification", "sata_dividends": "SATA dividends",
          "issuance": "Issuance", "op_costs": "Op. costs", "growth_premium": "Growth premium"}


def waterfall(row: pd.Series, when: str, c: dict) -> alt.LayerChart:
    """NTAV today -> BTC move, amplification, issuance, op costs -> NTAV at the date -> growth premium -> price target,
    with today's price as a reference line."""
    steps, cum = [], float(row["start"])

    def total(label, v):
        steps.append({"label": label, "y0": 0.0, "y1": v, "value": v, "kind": "Value"})

    def delta(key):
        nonlocal cum
        v = float(row[key])
        steps.append({"label": LABELS[key], "y0": cum, "y1": cum + v, "value": v,
                      "kind": "Adds" if v >= 0 else "Subtracts"})
        cum += v

    total("NTAV today", cum)
    for key in ("btc_move", "amplification", "sata_dividends", "issuance", "op_costs"):
        delta(key)
    total(f"NTAV {when}", float(row["ntav_end"]))
    delta("growth_premium")
    total("Price target", float(row["end"]))
    df = pd.DataFrame(steps)
    gain = row["end"] - row["start"]
    money = lambda v: f"${abs(v):,.0f}" if abs(v) >= 100 else f"${abs(v):,.2f}"  # whole dollars keep labels short
    df["text"] = [money(v) if k == "Value" else f"{'+' if v >= 0 else '−'}{money(v)}" for v, k in zip(df.value, df.kind)]
    df["exact"] = [f"${v:,.2f}" if k == "Value" else f"{'+' if v >= 0 else '−'}${abs(v):,.2f}"
                   for v, k in zip(df.value, df.kind)]
    df["share"] = [None if k == "Value" or not gain else v / gain for v, k in zip(df.value, df.kind)]
    df["top"] = df[["y0", "y1"]].max(axis=1)
    order = list(df.label)

    base = alt.Chart(df).encode(x=alt.X("label:N", sort=order, title=None, axis=alt.Axis(
        labelAngle=0, labelLimit=90, labelOverlap=False, labelFontSize=11,
        labelExpr="split(datum.label, ' ')")))  # two-word labels on two lines
    bars = base.mark_bar(size=24, cornerRadius=4).encode(
        y=alt.Y("y0:Q", title="$ per share", axis=alt.Axis(format="$,.0f")), y2="y1:Q",
        color=alt.Color("kind:N", title=None, scale=alt.Scale(domain=["Value", "Adds", "Subtracts"],
                                                              range=[c["total"], c["up"], c["down"]]),
                        legend=alt.Legend(orient="top", direction="horizontal")),
        tooltip=[alt.Tooltip("label:N", title="Step"), alt.Tooltip("exact:N", title="$ per share"),
                 alt.Tooltip("share:Q", title="Share of the climb from NTAV today", format=".0%")])
    labels = base.mark_text(dy=-9, fontSize=12, color=c["ink2"]).encode(y="top:Q", text="text:N")
    ref = pd.DataFrame({"y": [float(row["today_price"])], "label": [f"Today's price ${row['today_price']:,.2f}"]})
    rule = alt.Chart(ref).mark_rule(color=c["muted"], strokeWidth=1).encode(
        y="y:Q", tooltip=alt.Tooltip("label:N", title="Reference"))  # named in the caption above the chart
    return alt.layer(bars, labels, rule).properties(height=380)


def lines(df: pd.DataFrame, series: list[str], fmt: str, c: dict, height: int = 230,
          ref: tuple[float, str] | None = None, end_labels: bool = False, log: bool = False) -> alt.LayerChart:
    """One or two series over time on one axis, with a crosshair tooltip. df: a date column plus one per series."""
    palette = [c["s1"], c["s2"]][:len(series)]
    long = df.melt("date", series, var_name="series", value_name="value")
    sel = alt.selection_point(fields=["date"], nearest=True, on="pointerover", empty=False, clear="pointerout")
    color = alt.Color("series:N", title=None, scale=alt.Scale(domain=series, range=palette),
                      legend=alt.Legend(orient="top", direction="horizontal") if len(series) > 1 else None)
    x = alt.X("date:T", title=None, axis=alt.Axis(format="%b %Y", tickCount=6))
    axis = alt.Axis(format=fmt, labelExpr="replace(datum.label, 'G', 'B')") if fmt == "$~s" else alt.Axis(format=fmt)
    y = alt.Y("value:Q", title=None, axis=axis,
              scale=alt.Scale(type="log") if log else alt.Scale(zero=False))  # log: five years of compounding
    shown = alt.when(sel).then(alt.value(1)).otherwise(alt.value(0))
    layers = [
        alt.Chart(long).mark_line(strokeWidth=2).encode(x=x, y=y, color=color),
        alt.Chart(long).mark_point(size=70, filled=True, opacity=1).encode(x=x, y=y, color=color, opacity=shown),
        alt.Chart(df).mark_rule(color=c["muted"], strokeWidth=1).encode(
            x="date:T", opacity=shown,
            tooltip=[alt.Tooltip("date:T", title="Date", format="%b %d, %Y")]
                    + [alt.Tooltip(f"{s}:Q", format=fmt) for s in series]).add_params(sel),
    ]
    if ref is not None:
        rv, rl = ref
        rdf = pd.DataFrame({"y": [rv], "label": [rl]})
        layers.append(alt.Chart(rdf).mark_rule(color=c["muted"], strokeWidth=1).encode(y="y:Q"))
        layers.append(alt.Chart(rdf).mark_text(align="left", dx=4, dy=-7, fontSize=11, color=c["ink2"]).encode(
            y="y:Q", x=alt.value(0), text="label:N"))
    if end_labels:
        last = long[long["date"] == long["date"].max()]
        layers.append(alt.Chart(last).mark_text(align="left", dx=6, fontSize=11, color=c["ink2"]).encode(
            x="date:T", y="value:Q", text="series:N"))
    return alt.layer(*layers).properties(height=height)


def weekly_bars(df: pd.DataFrame, c: dict) -> alt.LayerChart:
    """SATA vs common dollars raised per week (grouped)."""
    long = df.melt("week", ["SATA", "Common"], var_name="series", value_name="usd")
    long["text"] = (long["usd"] / 1e6).map(lambda v: f"${v:,.1f}M")
    return alt.Chart(long).mark_bar(size=18, cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
        x=alt.X("week:N", title="Week ending", axis=alt.Axis(labelAngle=0)),
        xOffset=alt.XOffset("series:N", sort=["SATA", "Common"]),
        y=alt.Y("usd:Q", title="Raised", axis=alt.Axis(format="$~s")),
        color=alt.Color("series:N", title=None, sort=["SATA", "Common"],
                        scale=alt.Scale(domain=["SATA", "Common"], range=[c["s1"], c["s2"]]),
                        legend=alt.Legend(orient="top", direction="horizontal")),
        tooltip=[alt.Tooltip("week:N", title="Week ending"), alt.Tooltip("series:N", title="Security"),
                 alt.Tooltip("text:N", title="Raised")],
    ).properties(height=300)
