"""Visual themes inspired by the Vault of Glass (Destiny, 2014): brutalist Vex stone, bronze machine detail, milky
radiolarian light, red Gorgon sightlines, circular time gates and floating Oracles, deep below Venus.

Three looks share one set of HTML components (hero, section titles, metric cards, the price-target ledger) and differ
only in CSS and background art:
    monolith  flat 2D: layered stone silhouettes around a circular gate; square slabs with bronze inlay
    spire     2D drawn to look 3D: a perspective colonnade receding to a lit gate; extruded stone blocks
    oracle    holographic glass: Vex circuit traces and floating rings; translucent panels with corner brackets
All art is original SVG and CSS; nothing from the game is used. Chart colors are validated (dataviz validator).
"""
from __future__ import annotations

import base64
import html
import math
import random

import streamlit as st

DEFAULT = "monolith"
KEY = "vg_theme"

THEMES = {
    "monolith": {
        "label": "Monolith · flat 2D",
        "fonts": "family=Cinzel:wght@500;700&family=Inter:wght@400;500;600&family=Barlow+Condensed:wght@500;600;700",
        "head": "'Cinzel', serif", "body": "'Inter', sans-serif", "num": "'Barlow Condensed', sans-serif",
        "bg": "#0b0e10", "surface": "#141a1e", "border": "#2b343a", "accent": "#b0894f", "glow": "#9fe7dc",
        "ink": "#ece6da", "ink2": "#bdb6a9", "muted": "#858a8f", "grid": "#242c32",
        "up": "#2ea596", "down": "#df5446", "total": "#8b9196", "s1": "#2ea596", "s2": "#b47a32",
    },
    "spire": {
        "label": "Spire · 3D-look",
        "fonts": "family=Rajdhani:wght@500;600;700&family=Inter:wght@400;500;600",
        "head": "'Rajdhani', sans-serif", "body": "'Inter', sans-serif", "num": "'Rajdhani', sans-serif",
        "bg": "#06080b", "surface": "#151d22", "border": "#2c3940", "accent": "#c9a46a", "glow": "#bff3ec",
        "ink": "#eef3f1", "ink2": "#b8c4c2", "muted": "#7d8a8a", "grid": "#1e282e",
        "up": "#28a397", "down": "#e5574a", "total": "#7f8a90", "s1": "#28a397", "s2": "#b47d38",
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


def _spire_svg() -> str:
    """A colonnade receding to a lit time gate: perspective floor, shaded pillar faces, mist. Looks 3D; it's 2D."""
    vx, vy = 800, 500
    p = ['<defs>'
         '<linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#04060a"/>'
         '<stop offset="1" stop-color="#0d1a1d"/></linearGradient>'
         '<linearGradient id="floor" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#0c1416"/>'
         '<stop offset="1" stop-color="#040607"/></linearGradient>'
         '<linearGradient id="face" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#2b373d"/>'
         '<stop offset="1" stop-color="#182025"/></linearGradient>'
         '<linearGradient id="side" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#0e1418"/>'
         '<stop offset="1" stop-color="#090d10"/></linearGradient>'
         '<radialGradient id="gate"><stop offset="0" stop-color="#f2fffc" stop-opacity="0.95"/>'
         '<stop offset="0.35" stop-color="#9fe7dc" stop-opacity="0.45"/>'
         '<stop offset="1" stop-color="#9fe7dc" stop-opacity="0"/></radialGradient>'
         '<linearGradient id="mist" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#9fe7dc" stop-opacity="0"/>'
         '<stop offset="0.5" stop-color="#9fe7dc" stop-opacity="0.07"/>'
         '<stop offset="1" stop-color="#9fe7dc" stop-opacity="0"/></linearGradient>'
         '</defs>',
         '<rect width="1600" height="1000" fill="url(#sky)"/>',
         f'<rect y="{vy}" width="1600" height="{1000 - vy}" fill="url(#floor)"/>']
    for x in range(-1600, 3300, 150):  # floor rays to the vanishing point
        p.append(f'<line x1="{vx}" y1="{vy}" x2="{x}" y2="1000" stroke="#1a272b" stroke-width="1.2"/>')
    for i in range(1, 14):  # floor rows, closer together toward the horizon
        y = vy + (1000 - vy) * (1 - 0.74 ** i)
        p.append(f'<line x1="0" y1="{y:.1f}" x2="1600" y2="{y:.1f}" stroke="#152024" stroke-width="1"/>')
    for x in range(-800, 2500, 200):  # ceiling beams
        p.append(f'<line x1="{vx}" y1="{vy}" x2="{x}" y2="0" stroke="#0f171a" stroke-width="2"/>')
    p += [f'<circle cx="{vx}" cy="{vy}" r="190" fill="url(#gate)"/>',
          f'<circle cx="{vx}" cy="{vy}" r="118" fill="none" stroke="#c9a46a" stroke-opacity="0.45" stroke-width="3"/>',
          f'<circle cx="{vx}" cy="{vy}" r="160" fill="none" stroke="#9fe7dc" stroke-opacity="0.18" stroke-width="2"/>',
          f'<rect y="{vy - 90}" width="1600" height="180" fill="url(#mist)"/>']
    for i in range(6, -1, -1):  # pillars, far to near, both sides
        s = 0.78 ** i
        w, top, bot = 150 * s, vy - 440 * s, vy + 480 * s
        for side in (-1, 1):
            cx = vx + side * 660 * s
            inner = cx - side * w / 2
            d = side * w * 0.38
            p.append(f'<polygon points="{inner:.1f},{top:.1f} {inner - d:.1f},{top + (bot - top) * 0.05:.1f} '
                     f'{inner - d:.1f},{bot - (bot - top) * 0.05:.1f} {inner:.1f},{bot:.1f}" fill="url(#side)"/>')
            p.append(f'<rect x="{cx - w / 2:.1f}" y="{top:.1f}" width="{w:.1f}" height="{bot - top:.1f}" fill="url(#face)"/>')
            p.append(f'<rect x="{cx - w * 0.66:.1f}" y="{top - w * 0.32:.1f}" width="{w * 1.32:.1f}" '
                     f'height="{w * 0.32:.1f}" fill="#222c32"/>')
            p.append(f'<rect x="{cx - w * 0.66:.1f}" y="{top - w * 0.32:.1f}" width="{w * 1.32:.1f}" '
                     f'height="{max(1.0, w * 0.03):.1f}" fill="#3a474e"/>')
            p.append(f'<rect x="{cx - w * 0.6:.1f}" y="{bot - w * 0.12:.1f}" width="{w * 1.2:.1f}" '
                     f'height="{w * 0.24:.1f}" fill="#11181c"/>')
            p.append(f'<rect x="{cx - w * 0.06:.1f}" y="{top + (bot - top) * 0.3:.1f}" width="{w * 0.12:.1f}" '
                     f'height="{(bot - top) * 0.25:.1f}" fill="#9fe7dc" opacity="{0.10 + 0.05 * s:.2f}"/>')
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


_ART = {"monolith": _monolith_svg, "spire": _spire_svg, "oracle": _oracle_svg}


# ------------------------------------------------------------------ CSS

def _base_css(t: dict, art: str) -> str:
    return f"""
@import url('https://fonts.googleapis.com/css2?{t['fonts']}&display=swap');
:root {{ --vg-bg:{t['bg']}; --vg-surface:{t['surface']}; --vg-border:{t['border']}; --vg-accent:{t['accent']};
  --vg-glow:{t['glow']}; --vg-ink:{t['ink']}; --vg-ink2:{t['ink2']}; --vg-muted:{t['muted']};
  --vg-up:{t['up']}; --vg-down:{t['down']}; --vg-head:{t['head']}; --vg-body:{t['body']}; --vg-num:{t['num']}; }}
.stApp {{ background: var(--vg-bg) url("{art}") center / cover fixed no-repeat; color: var(--vg-ink);
  font-family: var(--vg-body); }}
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
    if name == "monolith":
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
    if name == "spire":
        return """
.vg-hero, .vg-card, .st-key-vg_chart, .vg-step {
  background: linear-gradient(180deg, #1d272d 0%, #131a1f 100%); border: 1px solid #2c3940; border-radius: 4px;
  box-shadow: inset 0 1px 0 rgba(255,255,255,.07), inset 0 -1px 0 rgba(0,0,0,.6), 0 7px 0 -1px #0b1013,
    0 7px 0 0 #2c3940, 0 22px 34px rgba(0,0,0,.6); }
.vg-hero { background: linear-gradient(180deg, #222e35 0%, #121a1f 70%); border-radius: 6px;
  box-shadow: inset 0 1px 0 rgba(255,255,255,.10), 0 12px 0 -1px #0a0e11, 0 12px 0 0 #34434a,
    0 34px 60px rgba(0,0,0,.7), 0 0 80px rgba(159,231,220,.06); }
.vg-hero::after { content: ""; position: absolute; left: 0; right: 0; top: 0; height: 45%;
  background: linear-gradient(180deg, rgba(191,243,236,.07), transparent); pointer-events: none; }
.vg-hero-value { text-shadow: 0 2px 0 #0a0e11, 0 4px 0 #0a0e11, 0 18px 30px rgba(0,0,0,.6); }
.vg-chip { background: linear-gradient(180deg, #243038, #182126); border-color: #34434a; border-radius: 3px;
  box-shadow: 0 3px 0 #0a0e11; }
.vg-section-title { text-shadow: 0 2px 0 #000, 0 0 18px rgba(159,231,220,.12); }
.vg-card { transition: transform .15s; }
.vg-step-n { width: 40px; height: 40px; line-height: 40px; margin: 0 auto; border-radius: 3px;
  background: linear-gradient(180deg, #2a363d, #172025); box-shadow: 0 3px 0 #0a0e11; }
.vg-total { background: linear-gradient(180deg, #213036 0%, #12201f 100%); }
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
    st.html(f"<style>{_base_css(t, _b64(_ART[name]()))}{_theme_css(name, t)}</style>")


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
