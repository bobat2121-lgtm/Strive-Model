"""Visual themes inspired by the Vault of Glass (Destiny, 2014): brutalist Vex stone, bronze machine detail, milky
radiolarian light, red Gorgon sightlines, circular time gates and floating Oracles, deep below Venus.

The looks share one set of HTML components (hero, section titles, metric cards, the price-target ledger) and differ
only in CSS and background art:
    vault     the chosen direction: Monolith's teal and gold, carved headings, stone slabs and Roman numerals over
              living Vex circuit traces, each firing a slow wave of light on its own paced timer
    monolith  flat 2D: layered stone silhouettes around a circular gate; square slabs with bronze inlay
    oracle    holographic glass: Vex circuit traces and floating rings; translucent panels with corner brackets
All art is original SVG and CSS; nothing from the game is used. Chart colors are validated (dataviz validator).
"""
from __future__ import annotations

import base64
import html
import math
import random

import streamlit as st

DEFAULT = "vault"
KEY = "vg_theme"

THEMES = {
    "vault": {
        "label": "Vault · Monolith with living circuits",
        "fonts": "family=Cinzel:wght@500;700&family=Inter:wght@400;500;600&family=Barlow+Condensed:wght@500;600;700",
        "head": "'Cinzel', serif", "body": "'Inter', sans-serif", "num": "'Barlow Condensed', sans-serif",
        "bg": "#0a0d0f", "surface": "#141a1e", "border": "#2b343a", "accent": "#b0894f", "glow": "#9fe7dc",
        "ink": "#ece6da", "ink2": "#bdb6a9", "muted": "#858a8f", "grid": "#242c32",
        "up": "#2ea596", "down": "#df5446", "total": "#8b9196", "s1": "#2ea596", "s2": "#b47a32",
    },
    "monolith": {
        "label": "Monolith · flat 2D",
        "fonts": "family=Cinzel:wght@500;700&family=Inter:wght@400;500;600&family=Barlow+Condensed:wght@500;600;700",
        "head": "'Cinzel', serif", "body": "'Inter', sans-serif", "num": "'Barlow Condensed', sans-serif",
        "bg": "#0b0e10", "surface": "#141a1e", "border": "#2b343a", "accent": "#b0894f", "glow": "#9fe7dc",
        "ink": "#ece6da", "ink2": "#bdb6a9", "muted": "#858a8f", "grid": "#242c32",
        "up": "#2ea596", "down": "#df5446", "total": "#8b9196", "s1": "#2ea596", "s2": "#b47a32",
    },
    "oracle": {
        "label": "Oracle · holographic glass",
        "fonts": ("family=Orbitron:wght@500;700&family=Exo+2:wght@400;500;600&family=Share+Tech+Mono"
                  "&family=Rajdhani:wght@600;700"),
        "head": "'Orbitron', sans-serif", "body": "'Exo 2', sans-serif", "num": "'Rajdhani', sans-serif",
        "bg": "#040607", "surface": "#0c1416", "border": "#24443f", "accent": "#d8c08a", "glow": "#9fe7dc",
        "ink": "#e9fffb", "ink2": "#a7cdc7", "muted": "#6e8f8a", "grid": "#15302c",
        "up": "#2ba79a", "down": "#ee5f4f", "total": "#8d9a98", "s1": "#2ba79a", "s2": "#b4813c",
    },
}


def current() -> str:
    return st.session_state.get(KEY, DEFAULT)


def palette(name: str | None = None) -> dict:
    """Chart colors and fonts for the active theme."""
    t = THEMES[name or current()]
    return {"up": t["up"], "down": t["down"], "total": t["total"], "s1": t["s1"], "s2": t["s2"],
            "ink": t["ink"], "ink2": t["ink2"], "muted": t["muted"], "rule": t["muted"], "grid": t["grid"],
            "font_body": t["body"].split(",")[0].strip("'"), "font_num": t["num"].split(",")[0].strip("'")}


# ------------------------------------------------------------------ background art (original SVG)

def _b64(svg: str) -> str:
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()


def _monolith_svg() -> str:
    """Flat, layered stone silhouettes in a cavern around a circular gate. No gradients: pure 2D."""
    rnd = random.Random(7)
    p = ['<rect width="1600" height="1000" fill="#0b0e10"/>',
         # cavern ceiling, two stepped slabs
         '<path d="M0 0H1600V130H1470V185H1300V150H1120V205H960V160H800V215H640V160H470V195H300V145H140V180H0Z" '
         'fill="#0f1417"/>',
         '<path d="M0 0H1600V64H1380V100H1180V74H900V112H620V76H360V104H160V72H0Z" fill="#12181b"/>']
    for x, w, top in [(30, 120, 420), (170, 90, 360), (280, 70, 450), (1170, 80, 455), (1280, 105, 365),
                      (1430, 130, 425)]:  # far monoliths
        p.append(f'<rect x="{x}" y="{top}" width="{w}" height="{800 - top}" fill="#11171a"/>')
    # the gate: ring, inner rings, faint radiolarian disk, a slit of light, bronze notches
    p += ['<circle cx="800" cy="500" r="255" fill="#0d1315" stroke="#2a2418" stroke-width="22"/>',
          '<circle cx="800" cy="500" r="208" fill="none" stroke="#3b3222" stroke-width="5"/>',
          '<circle cx="800" cy="500" r="172" fill="#0e1919"/>',
          '<circle cx="800" cy="500" r="120" fill="#cfeae4" opacity="0.05"/>',
          '<circle cx="800" cy="500" r="62" fill="#cfeae4" opacity="0.07"/>',
          '<rect x="793" y="318" width="14" height="364" fill="#9fe7dc" opacity="0.10"/>']
    p += [f'<rect x="795" y="236" width="10" height="26" fill="#4a3d27" transform="rotate({k * 30} 800 500)"/>'
          for k in range(12)]
    # mid monoliths, stepped, with bronze inlay lines
    p += ['<path d="M0 1000V430H120V380H235V455H335V520H440V1000Z" fill="#151c20"/>',
          '<path d="M1600 1000V430H1480V380H1365V455H1265V520H1160V1000Z" fill="#151c20"/>']
    for y in (470, 560, 650):
        p.append(f'<rect x="40" y="{y}" width="{260 - (y - 470) // 3}" height="3" fill="#5a4a30" opacity="0.55"/>')
        p.append(f'<rect x="{1560 - 260 + (y - 470) // 3}" y="{y}" width="{260 - (y - 470) // 3}" height="3" '
                 f'fill="#5a4a30" opacity="0.55"/>')
    # floor and flat steps up to the gate
    p.append('<rect y="780" width="1600" height="220" fill="#0d1113"/>')
    for i, (w, f) in enumerate([(700, "#12181b"), (840, "#101518"), (980, "#12181b")]):
        p.append(f'<rect x="{800 - w / 2}" y="{780 + i * 34}" width="{w}" height="34" fill="{f}"/>')
    p += ['<path d="M0 1000V820H190V900H270V1000Z" fill="#090c0e"/>',
          '<path d="M1600 1000V820H1410V900H1330V1000Z" fill="#090c0e"/>']
    for _ in range(46):  # faint geometric radiolarian cells
        x, y, r = rnd.uniform(0, 1600), rnd.uniform(0, 1000), rnd.uniform(4, 11)
        pts = " ".join(f"{x + r * math.cos(a):.1f},{y + r * math.sin(a):.1f}"
                       for a in [k * math.pi / 3 for k in range(6)])
        p.append(f'<polygon points="{pts}" fill="none" stroke="#9fe7dc" stroke-width="1" opacity="0.06"/>')
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 1000" preserveAspectRatio="xMidYMid slice">'
            + "".join(p) + "</svg>")


def _oracle_svg() -> str:
    """Obsidian with Vex circuit traces (right angles that bend like roots) and floating Oracle rings."""
    rnd = random.Random(11)
    p = ['<rect width="1600" height="1000" fill="#040607"/>']
    for _ in range(44):
        edge = rnd.choice("lrtb")
        x = {"l": 0, "r": 1600}.get(edge, rnd.uniform(0, 1600))
        y = {"t": 0, "b": 1000}.get(edge, rnd.uniform(0, 1000))
        dx, dy = {"l": (1, 0), "r": (-1, 0), "t": (0, 1), "b": (0, -1)}[edge]
        d = f"M{x:.0f} {y:.0f}"
        for _ in range(rnd.randint(3, 7)):
            step = rnd.uniform(40, 170)
            x, y = x + dx * step, y + dy * step
            d += f" L{x:.0f} {y:.0f}"
            if rnd.random() < 0.35:  # a 45-degree bend, then turn
                x, y = x + dx * 26 + dy * 26, y + dy * 26 + dx * 26
                d += f" L{x:.0f} {y:.0f}"
            dx, dy = (dy, dx) if rnd.random() < 0.5 else (-dy, -dx)
        p.append(f'<path d="{d}" fill="none" stroke="#5ee0cf" stroke-width="1.2" opacity="0.15"/>')
        p.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="2.6" fill="#9fe7dc" opacity="0.35"/>')
    for cx, cy, r in [(240, 210, 64), (1380, 280, 52), (1270, 830, 74), (300, 800, 46)]:  # Oracles
        p += [f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#9fe7dc" stroke-width="1.4" opacity="0.20"/>',
              f'<circle cx="{cx}" cy="{cy}" r="{r * 0.7:.0f}" fill="none" stroke="#9fe7dc" stroke-width="1" '
              f'stroke-dasharray="6 8" opacity="0.18"/>',
              f'<circle cx="{cx}" cy="{cy}" r="{r * 0.28:.0f}" fill="#cfeae4" opacity="0.08"/>']
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 1000" preserveAspectRatio="xMidYMid slice">'
            + "".join(p) + "</svg>")


def _trace_paths(seed: int = 23, n: int = 42) -> list[list[tuple[float, float]]]:
    """Vex circuit traces: walks in from the edges with right-angle turns and the odd 45-degree bend."""
    rnd, out = random.Random(seed), []
    for _ in range(n):
        edge = rnd.choice("lrtb")
        x = {"l": 0, "r": 1600}.get(edge, rnd.uniform(0, 1600))
        y = {"t": 0, "b": 1000}.get(edge, rnd.uniform(0, 1000))
        dx, dy = {"l": (1, 0), "r": (-1, 0), "t": (0, 1), "b": (0, -1)}[edge]
        pts = [(x, y)]
        for _ in range(rnd.randint(3, 7)):
            step = rnd.uniform(50, 180)
            x, y = x + dx * step, y + dy * step
            pts.append((x, y))
            if rnd.random() < 0.35:
                x, y = x + dx * 26 + dy * 26, y + dy * 26 + dx * 26
                pts.append((x, y))
            dx, dy = (dy, dx) if rnd.random() < 0.5 else (-dy, -dx)
        out.append(pts)
    return out


def _d(pts) -> str:
    return "M" + " L".join(f"{x:.0f} {y:.0f}" for x, y in pts)


def _svg(body: str) -> str:
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 1000" preserveAspectRatio="xMidYMid slice">'
            + body + "</svg>")


def _vault_static_svg() -> str:
    """The traces at rest: dim teal and gold lines with solder pads and end nodes, over near-black stone."""
    p = ['<defs><radialGradient id="v" cx="0.5" cy="0.42" r="0.75"><stop offset="0" stop-color="#11181b"/>'
         '<stop offset="1" stop-color="#07090b"/></radialGradient></defs>',
         '<rect width="1600" height="1000" fill="url(#v)"/>']
    for i, pts in enumerate(_trace_paths()):
        col, op = ("#b0894f", 0.22) if i % 3 == 0 else ("#2ea596", 0.20)
        p.append(f'<path d="{_d(pts)}" fill="none" stroke="{col}" stroke-width="1.3" opacity="{op}"/>')
        for x, y in pts[1:-1:2]:  # solder pads at some turns
            p.append(f'<rect x="{x - 2:.0f}" y="{y - 2:.0f}" width="4" height="4" fill="{col}" opacity="{op}"/>')
        x, y = pts[-1]
        p.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="3" fill="{col}" opacity="0.5"/>')
    return _svg("".join(p))


WAVE_PACE = {"a": 0.10, "b": 0.13, "c": 0.17}  # share of each cycle a wave spends crossing its trace (one keyframe set each)


def _vault_waves_html() -> str:
    """The light, as an inline SVG layer fixed behind the page (an SVG used as a background image doesn't animate
    reliably). On each lit trace a soft glow with a bright core travels the whole path, then waits. Every trace has
    its own paced timer: 5-11s to cross, 30-110s between waves, already mid-schedule at load, so about three are
    moving at any moment. CSS animation, so prefers-reduced-motion turns it off."""
    rnd = random.Random(9)
    head = 130  # the glow's length; both layers' heads move together from the start of the path to past its end
    p = []
    for i, pts in enumerate(_trace_paths()):
        if rnd.random() > 0.5:  # about half the traces carry light
            continue
        col = "#f2cf8e" if i % 3 == 0 else "#c4fbf3"
        length = sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))
        travel = min(max(length / 95, 5.0), 11.0)
        pace = rnd.choice(list(WAVE_PACE))
        cycle = travel / WAVE_PACE[pace]
        delay = -rnd.uniform(0, cycle)
        for cls, dash in (("glow", head), ("core", 46)):
            p.append(f'<path class="{cls}" d="{_d(pts)}" stroke="{col}" style="--dash:{dash};'
                     f'--gap:{length + head + dash + 20:.0f};--o0:{dash};--o1:{dash - length - head:.0f};'
                     f'animation-name:vg-wave-{pace};animation-duration:{cycle:.1f}s;animation-delay:{delay:.1f}s"/>')
    return ('<div class="vg-waves" aria-hidden="true"><svg viewBox="0 0 1600 1000" preserveAspectRatio="xMidYMid slice">'
            + "".join(p) + "</svg></div>")


WAVES_CSS = """
.stApp { isolation: isolate; }
[data-testid="stElementContainer"]:has(.vg-waves) { position: absolute; }
.vg-waves { position: fixed; inset: 0; z-index: -1; pointer-events: none; }
.vg-waves svg { width: 100%; height: 100%; display: block; }
.vg-waves path { fill: none; stroke-linecap: round; stroke-dasharray: var(--dash) var(--gap);
  stroke-dashoffset: var(--o0); animation-timing-function: linear; animation-iteration-count: infinite; }
.vg-waves .glow { stroke-width: 5; opacity: .09; }
.vg-waves .core { stroke-width: 1.6; opacity: .55; }
""" + "".join(
    f"@keyframes vg-wave-{k} {{ 0% {{ stroke-dashoffset: var(--o0); animation-timing-function: cubic-bezier(.45,0,.55,1); }}"
    f" {v * 100:g}% {{ stroke-dashoffset: var(--o1); }} 100% {{ stroke-dashoffset: var(--o1); }} }}\n"
    for k, v in WAVE_PACE.items()) + """
@media (prefers-reduced-motion: reduce) { .vg-waves { display: none; } }
"""


_ART = {"vault": [_vault_static_svg], "monolith": [_monolith_svg], "oracle": [_oracle_svg]}


# ------------------------------------------------------------------ CSS

def _base_css(t: dict, layers: list[str]) -> str:
    art = ", ".join(f'url("{u}")' for u in layers)  # the first layer sits on top
    return f"""
@import url('https://fonts.googleapis.com/css2?{t['fonts']}&display=swap');
:root {{ --vg-bg:{t['bg']}; --vg-surface:{t['surface']}; --vg-border:{t['border']}; --vg-accent:{t['accent']};
  --vg-glow:{t['glow']}; --vg-ink:{t['ink']}; --vg-ink2:{t['ink2']}; --vg-muted:{t['muted']};
  --vg-up:{t['up']}; --vg-down:{t['down']}; --vg-head:{t['head']}; --vg-body:{t['body']}; --vg-num:{t['num']}; }}
.stApp {{ background-color: var(--vg-bg); background-image: {art}; background-size: cover; background-position: center;
  background-attachment: fixed; background-repeat: no-repeat; color: var(--vg-ink); font-family: var(--vg-body); }}
[data-testid="stAppViewContainer"], [data-testid="stMain"], [data-testid="stBottom"] > div {{ background: transparent; }}
[data-testid="stHeader"] {{ background: color-mix(in srgb, var(--vg-bg) 82%, transparent);
  backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px); border-bottom: 1px solid var(--vg-border); }}
[data-testid="stSidebar"] {{ background: color-mix(in srgb, var(--vg-surface) 92%, transparent);
  border-right: 1px solid var(--vg-border); }}
[data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {{ font-family: var(--vg-head); letter-spacing: .04em; }}
.block-container {{ max-width: 1240px; padding-top: 3.2rem; }}
.stApp p, .stApp label, .stApp li {{ font-family: var(--vg-body); }}

.vg-hero {{ position: relative; overflow: hidden; padding: 38px 44px 34px; margin-bottom: 30px; }}
.vg-eyebrow {{ font-family: var(--vg-head); text-transform: uppercase; letter-spacing: .22em; font-size: 13px;
  color: var(--vg-accent); }}
.vg-hero-value {{ font-family: var(--vg-num); font-weight: 700; font-size: 96px; line-height: 1.02;
  color: var(--vg-ink); margin: 10px 0 6px; font-variant-numeric: lining-nums; }}
.vg-hero-delta {{ font-family: var(--vg-body); font-size: 17px; color: var(--vg-ink2); }}
.vg-hero-delta b {{ color: var(--vg-up); font-weight: 600; }}
.vg-chips {{ display: flex; flex-wrap: wrap; gap: 10px; margin-top: 22px; }}
.vg-chip {{ font-size: 13px; color: var(--vg-ink2); padding: 7px 12px; border: 1px solid var(--vg-border); }}
.vg-chip b {{ color: var(--vg-ink); font-weight: 600; margin-left: 6px; font-family: var(--vg-num); font-size: 15px; }}

.vg-section {{ margin: 34px 0 14px; }}
.vg-section-title {{ font-family: var(--vg-head); font-size: 22px; font-weight: 700; color: var(--vg-ink);
  letter-spacing: .06em; text-transform: uppercase; }}
.vg-section-sub {{ font-size: 13.5px; color: var(--vg-muted); margin-top: 4px; }}

.vg-cards {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(190px, 1fr)); gap: 12px; }}
.vg-card {{ padding: 15px 16px 14px; }}
.vg-card-label {{ font-size: 11.5px; text-transform: uppercase; letter-spacing: .14em; color: var(--vg-muted); }}
.vg-card-value {{ font-family: var(--vg-num); font-size: 30px; font-weight: 600; color: var(--vg-ink); margin-top: 4px; }}
.vg-card-sub {{ font-size: 12.5px; color: var(--vg-ink2); margin-top: 2px; }}

.st-key-vg_chart {{ padding: 18px 18px 8px; }}

.vg-ledger {{ display: flex; flex-direction: column; gap: 10px; }}
.vg-step {{ display: grid; grid-template-columns: 54px 1fr auto; align-items: center; gap: 18px; padding: 16px 20px; }}
.vg-step-n {{ font-family: var(--vg-head); font-size: 20px; color: var(--vg-accent); text-align: center; }}
.vg-step-title {{ font-family: var(--vg-head); font-size: 15px; letter-spacing: .05em; color: var(--vg-ink);
  text-transform: uppercase; }}
.vg-step-math {{ font-size: 13.5px; color: var(--vg-ink2); margin-top: 5px; line-height: 1.5; }}
.vg-step-value {{ font-family: var(--vg-num); font-size: 30px; font-weight: 700; color: var(--vg-ink); text-align: right;
  white-space: nowrap; }}
.vg-step-value small {{ display: block; font-family: var(--vg-body); font-size: 11.5px; font-weight: 500;
  letter-spacing: .12em; text-transform: uppercase; color: var(--vg-muted); }}
.vg-total .vg-step-value {{ font-size: 40px; color: var(--vg-up); }}

[data-testid="stExpander"] details {{ background: color-mix(in srgb, var(--vg-surface) 88%, transparent);
  border: 1px solid var(--vg-border); }}
[data-testid="stExpander"] summary p {{ font-family: var(--vg-head); letter-spacing: .08em; text-transform: uppercase; }}
"""


def _theme_css(name: str, t: dict) -> str:
    if name in ("monolith", "vault"):
        return """
.vg-hero, .vg-card, .st-key-vg_chart, .vg-step { background: #141a1ef2; border: 1px solid #2b343a;
  border-top: 2px solid #b0894f; border-radius: 0; }
.vg-hero { border-top-width: 3px; }
.vg-hero::after { content: ""; position: absolute; right: 44px; top: 34px; width: 140px; height: 140px;
  border: 10px solid #2a2418; border-radius: 50%; box-shadow: inset 0 0 0 4px #3b3222; opacity: .9; }
.vg-hero::before { content: ""; position: absolute; right: 108px; top: 54px; width: 12px; height: 100px;
  background: #9fe7dc22; }
.vg-chip { border-color: #5a4a30; background: #11171a; }
.vg-section-title::before { content: "◆"; color: #b0894f; font-size: 13px; margin-right: 10px; vertical-align: 3px; }
.vg-step-n { border-right: 1px solid #2b343a; }
.vg-total { border-top-color: #9fe7dc; }
"""
    return """
.vg-hero, .vg-card, .st-key-vg_chart, .vg-step { position: relative; background: rgba(10,20,22,.58);
  backdrop-filter: blur(9px); -webkit-backdrop-filter: blur(9px); border: 1px solid rgba(159,231,220,.24);
  border-radius: 2px; box-shadow: 0 0 0 1px rgba(0,0,0,.4), 0 0 26px rgba(94,224,207,.05) inset; }
.vg-card::before, .vg-step::before, .vg-hero::before, .st-key-vg_chart::before { content: ""; position: absolute;
  inset: -1px; pointer-events: none; background:
    linear-gradient(#9fe7dc,#9fe7dc) top left / 14px 2px no-repeat, linear-gradient(#9fe7dc,#9fe7dc) top left / 2px 14px no-repeat,
    linear-gradient(#9fe7dc,#9fe7dc) bottom right / 14px 2px no-repeat, linear-gradient(#9fe7dc,#9fe7dc) bottom right / 2px 14px no-repeat;
  opacity: .7; }
.vg-hero { text-align: center; padding: 48px 44px 40px; }
.vg-hero::after { content: ""; position: absolute; left: 50%; top: 50%; width: 520px; height: 520px;
  transform: translate(-50%, -50%); border-radius: 50%; pointer-events: none;
  background: radial-gradient(circle, rgba(159,231,220,.16) 0%, rgba(159,231,220,.05) 35%, transparent 62%),
    repeating-radial-gradient(circle, transparent 0 58px, rgba(159,231,220,.10) 58px 59px);
  animation: vg-pulse 6s ease-in-out infinite; }
@keyframes vg-pulse { 50% { opacity: .55; } }
@media (prefers-reduced-motion: reduce) { .vg-hero::after { animation: none; } }
.vg-hero-value { text-shadow: 0 0 22px rgba(94,224,207,.45), 0 0 2px rgba(233,255,251,.8); position: relative; z-index: 1; }
.vg-eyebrow, .vg-hero-delta, .vg-chips { position: relative; z-index: 1; }
.vg-chips { justify-content: center; }
.vg-chip { background: rgba(4,10,11,.6); border-color: rgba(159,231,220,.3); font-family: 'Share Tech Mono', monospace; }
.vg-card-label, .vg-section-sub, .vg-step-math { font-family: 'Share Tech Mono', monospace; }
.vg-section-title { font-size: 18px; letter-spacing: .18em; color: #c9f5ee; text-shadow: 0 0 12px rgba(94,224,207,.35); }
.vg-section-title::after { content: ""; display: block; height: 1px; margin-top: 8px;
  background: linear-gradient(90deg, rgba(159,231,220,.6), transparent 70%); }
.vg-card-value, .vg-step-value { text-shadow: 0 0 12px rgba(94,224,207,.25); }
.vg-total { border-color: rgba(159,231,220,.55); box-shadow: 0 0 30px rgba(94,224,207,.12) inset; }
.stApp::after { content: ""; position: fixed; inset: 0; pointer-events: none; z-index: 0;
  background: repeating-linear-gradient(0deg, rgba(255,255,255,.018) 0 1px, transparent 1px 3px); }
"""


def apply(name: str) -> None:
    """Inject the theme (fonts, background, component styles) for this run."""
    st.session_state[KEY] = name
    t = THEMES[name]
    st.html(f"<style>{_base_css(t, [_b64(make()) for make in _ART[name]])}{_theme_css(name, t)}"
            f"{WAVES_CSS if name == 'vault' else ''}</style>")
    if name == "vault":  # the living circuits: an inline layer behind the page (st.html strips inline SVG)
        st.markdown(_vault_waves_html(), unsafe_allow_html=True)


# ------------------------------------------------------------------ components

def _e(s: str) -> str:
    return html.escape(str(s), quote=False)


def hero(eyebrow: str, value: str, delta_html: str, chips: list[tuple[str, str]]) -> None:
    chips_html = "".join(f'<span class="vg-chip">{_e(k)}<b>{_e(v)}</b></span>' for k, v in chips)
    st.html(f'<div class="vg-hero"><div class="vg-eyebrow">{_e(eyebrow)}</div>'
            f'<div class="vg-hero-value">{_e(value)}</div><div class="vg-hero-delta">{delta_html}</div>'
            f'<div class="vg-chips">{chips_html}</div></div>')


def section(title: str, sub: str | None = None) -> None:
    st.html(f'<div class="vg-section"><div class="vg-section-title">{_e(title)}</div>'
            + (f'<div class="vg-section-sub">{_e(sub)}</div>' if sub else "") + "</div>")


def cards(items: list[tuple[str, str, str]]) -> None:
    st.html('<div class="vg-cards">' + "".join(
        f'<div class="vg-card"><div class="vg-card-label">{_e(a)}</div><div class="vg-card-value">{_e(b)}</div>'
        f'<div class="vg-card-sub">{_e(c)}</div></div>' for a, b, c in items) + "</div>")


def ledger(steps: list[dict]) -> None:
    """steps: {n, title, math, value, label, total?}"""
    st.html('<div class="vg-ledger">' + "".join(
        f'<div class="vg-step{" vg-total" if s.get("total") else ""}"><div class="vg-step-n">{_e(s["n"])}</div>'
        f'<div><div class="vg-step-title">{_e(s["title"])}</div><div class="vg-step-math">{_e(s["math"])}</div></div>'
        f'<div class="vg-step-value"><small>{_e(s["label"])}</small>{_e(s["value"])}</div></div>'
        for s in steps) + "</div>")
