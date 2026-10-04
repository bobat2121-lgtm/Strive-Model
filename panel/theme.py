"""The "Mine" theme: a dwarven gold mine under the mountain, drawn as pixel art (tools/mine_art.py builds the images
into static/, served by Streamlit's static file serving).

The scene sits fixed behind the page and descends as you scroll: a CSS scroll timeline on Streamlit's main scroll
container drives it, so the throne hall (a dragon on its hoard, Michael Saylor riding it) is at the top and the deep
(where the lava runs round a glowing ring and through a bitcoin sigil) is at the bottom. Everything moves with CSS only: lava frames,
dwarves mining and pacing the walkways, sparkles in the gold, and the dragon, which flaps idly, breathes fire every
so often from the middle of its mouth (Saylor raises a fist and crackles with electricity) and now and then spins
round. prefers-reduced-motion stills it all.

Information panels stay distinct from the scene: opaque dark stone with a light lava border. Headings use the
Ringbearer font (static/fonts/ringbearer, freeware for non-commercial use, kept with its original archive files).
"""
from __future__ import annotations

import hashlib
import html
from pathlib import Path

import streamlit as st

from panel import mine_layout as L

ART = "/app/static/mine"
# a version stamp on every image URL, so browsers fetch new art when it changes (static files have no cache policy)
V = hashlib.md5(b"".join(f.read_bytes() for f in sorted(
    (Path(__file__).parents[1] / "static" / "mine").glob("*.png")))).hexdigest()[:8]
FONT = "/app/static/fonts/ringbearer/RingbearerMedium-51mgZ.ttf"
PAL = {"bg": "#07080d", "surface": "#15100d", "ink": "#f3e6cf", "ink2": "#cdb994", "muted": "#9a8a72",
       "gold": "#f2c14e", "lava": "#ff6a13", "grid": "#2a211b",
       "up": "#bb8118", "down": "#4f80b8", "total": "#7d838d", "s1": "#bb8118", "s2": "#4f80b8"}


def palette() -> dict:
    """Chart colors and fonts (validated with the dataviz palette checker)."""
    return {"up": PAL["up"], "down": PAL["down"], "total": PAL["total"], "s1": PAL["s1"], "s2": PAL["s2"],
            "ink": PAL["ink"], "ink2": PAL["ink2"], "muted": PAL["muted"], "rule": PAL["muted"], "grid": PAL["grid"],
            "font_body": "Inter", "font_num": "Inter"}


# ------------------------------------------------------------------ the scene

def _in_dragon(x, y, w, h) -> str:
    """Position in percent of the dragon sprite (its own 128 x 100 pixels), for what rides along with it."""
    d = L.DRAGON
    return (f"left: {x / d['w'] * 100:.4f}%; top: {y / d['h'] * 100:.4f}%; "
            f"width: {w / d['w'] * 100:.4f}%; height: {h / d['h'] * 100:.4f}%;")


FIRE_BOX = _in_dragon(L.MOUTH[0] - L.FIRE["w"] + 1, L.MOUTH[1] - L.FIRE["h"] / 2, L.FIRE["w"], L.FIRE["h"])
ZAP_BOX = _in_dragon(L.ZAP["x"], L.ZAP["y"], L.ZAP["w"], L.ZAP["h"])


def _box(x, y, w, h) -> str:
    """Position in percent of the world (the 480 x 1200 cavern), so everything scales with it."""
    return (f"left:{x / L.SCENE_W * 100:.4f}%;top:{y / L.SCENE_H * 100:.4f}%;"
            f"width:{w / L.SCENE_W * 100:.4f}%;height:{h / L.SCENE_H * 100:.4f}%")


def _scene_html() -> tuple[str, str]:
    """(markup, per-sprite CSS) for the scene."""
    parts, css = ['<div class="mx-scene" aria-hidden="true"><div class="mx-world">',
                  '<div class="mx-layer mx-cavern"></div><div class="mx-layer mx-lava"></div>'], []
    for i, m in enumerate(L.MINERS):
        parts.append(f'<div class="mx-sprite mx-loop{" mx-flip" if m["flip"] else ""}" style="{_box(m["x"], m["y"], 18, 17)};'
                     f'background-image:url({ART}/{m["sheet"]}.png?v={V});animation-duration:{m["dur"]}s;'
                     f'animation-delay:{m["delay"]}s"></div>')
    for i, wk in enumerate(L.WALKERS + L.CARTS):
        is_cart = wk in L.CARTS
        w = 34 if is_cart else 18
        parts.append(f'<div class="mx-pace" style="{_box(wk["x0"], wk["y"], w, 17)};animation-name:mx-pace-{i};'
                     f'animation-duration:{wk["dur"]}s;animation-delay:{wk["delay"]}s"><div class="mx-sprite mx-loop '
                     f'mx-turn" style="left:0;top:0;width:100%;height:100%;background-image:url({ART}/{wk["sheet"]}.png?v={V});'
                     f'animation-duration:0.7s,{wk["dur"]}s;animation-delay:0s,{wk["delay"]}s"></div></div>')
        css.append(f"@keyframes mx-pace-{i} {{ 0%, 100% {{ left: {wk['x0'] / L.SCENE_W * 100:.4f}%; }} "
                   f"50% {{ left: {wk['x1'] / L.SCENE_W * 100:.4f}%; }} }}")
    s = L.SMITH
    parts.append(f'<div class="mx-sprite mx-loop" style="{_box(s["x"], s["y"], 18, 17)};'
                 f'background-image:url({ART}/{s["sheet"]}.png?v={V});animation-duration:{s["dur"]}s"></div>')
    for x, y, delay in L.SPARKLES:
        parts.append(f'<div class="mx-sparkle" style="{_box(x - 2, y - 2, 5, 5)};animation-delay:{delay}s"></div>')
    d = L.DRAGON
    parts.append(
        f'<div class="mx-dragon" style="{_box(d["x"], d["y"], d["w"], d["h"])}"><div class="mx-spin">'
        f'<div class="mx-sprite mx-dragon-idle"></div><div class="mx-sprite mx-dragon-breath"></div>'
        f'<div class="mx-sprite mx-fire"></div><div class="mx-sprite mx-zap"></div>'
        f'<div class="mx-sprite mx-zap mx-zap-b"></div></div></div>')
    parts.append("</div></div>")
    return "".join(parts), "\n".join(css)


SCENE_CSS = f"""
[data-testid="stMain"] {{ scroll-timeline: --mx block; }}
.stApp {{ isolation: isolate; background: {PAL['bg']}; }}
[data-testid="stElementContainer"]:has(.mx-scene) {{ position: absolute; }}
.mx-scene {{ position: fixed; inset: 0; z-index: -1; overflow: hidden; pointer-events: none; }}
.mx-world {{ position: absolute; left: 0; top: 0; width: 100vw; aspect-ratio: {L.SCENE_W} / {L.SCENE_H};
  animation: mx-descend linear both; animation-timeline: --mx; }}
@keyframes mx-descend {{ from {{ transform: translateY(0); }} to {{ transform: translateY(calc(-100% + 100vh)); }} }}
.mx-layer, .mx-sprite, .mx-sparkle {{ position: absolute; image-rendering: pixelated;
  background-repeat: no-repeat; }}
.mx-layer {{ inset: 0; }}
.mx-cavern {{ background: url({ART}/cavern.png?v={V}) 0 0 / 100% 100%; }}
.mx-lava {{ background-image: url({ART}/lava.png?v={V}); background-size: 400% 100%;
  animation: mx-frames-4 .9s steps(4) infinite; }}
@keyframes mx-frames-4 {{ to {{ background-position-x: 133.333%; }} }}
@keyframes mx-frames-2 {{ to {{ background-position-x: 200%; }} }}
@keyframes mx-frames-8 {{ to {{ background-position-x: 114.2857%; }} }}
.mx-loop {{ background-size: 400% 100%; animation-name: mx-frames-4; animation-timing-function: steps(4);
  animation-iteration-count: infinite; }}
.mx-flip {{ transform: scaleX(-1); }}
.mx-pace {{ position: absolute; animation-timing-function: linear; animation-iteration-count: infinite; }}
.mx-turn {{ animation-name: mx-frames-4, mx-turn; animation-timing-function: steps(4), step-end;
  animation-iteration-count: infinite; }}
@keyframes mx-turn {{ 0% {{ transform: scaleX(1); }} 50% {{ transform: scaleX(-1); }} }}
.mx-sparkle {{ background: url({ART}/sparkle.png?v={V}) 0 0 / 400% 100%; opacity: 0;
  animation: mx-twinkle 4.2s steps(1) infinite; }}
@keyframes mx-twinkle {{ 0%, 70% {{ opacity: 0; background-position-x: 0%; }} 74% {{ opacity: 1; background-position-x: 33.333%; }}
  78% {{ opacity: 1; background-position-x: 66.667%; }} 82% {{ opacity: 1; background-position-x: 100%; }}
  86%, 100% {{ opacity: 0; }} }}
.mx-dragon {{ position: absolute; perspective: 700px; }}
.mx-spin {{ position: absolute; inset: 0; animation: mx-spin 41s ease-in-out infinite; transform-style: preserve-3d; }}
@keyframes mx-spin {{ 0%, 66% {{ transform: rotateY(0deg); }} 70% {{ transform: rotateY(360deg); }} 100% {{ transform: rotateY(360deg); }} }}
.mx-dragon-idle, .mx-dragon-breath {{ inset: 0; }}
.mx-dragon-idle {{ background-image: url({ART}/dragon.png?v={V}); background-size: 400% 100%;
  animation: mx-frames-4 .9s steps(4) infinite, mx-idle-show 23s steps(1) infinite, mx-bob 3s ease-in-out infinite; }}
.mx-dragon-breath {{ background-image: url({ART}/dragon_breath.png?v={V}); background-size: 200% 100%; opacity: 0;
  animation: mx-frames-2 .5s steps(2) infinite, mx-breath-show 23s steps(1) infinite; }}
.mx-fire {{ {FIRE_BOX} background-image: url({ART}/fire.png?v={V});
  background-size: 400% 100%; opacity: 0; transform-origin: right center;
  animation: mx-frames-4 .36s steps(4) infinite, mx-breath-show 23s steps(1) infinite; }}
.mx-zap {{ {ZAP_BOX} background-image: url({ART}/zap.png?v={V}); background-size: 800% 100%; opacity: 0;
  animation: mx-frames-8 1.2s steps(8) infinite, mx-breath-show 23s steps(1) infinite;
  filter: drop-shadow(0 0 1px rgba(170, 225, 255, .95)) drop-shadow(0 0 5px rgba(80, 160, 255, .7)); }}
.mx-zap-b {{ animation-duration: 1.7s, 23s; animation-delay: -.7s, 0s; }}  /* out of step: the formations vary */
@keyframes mx-idle-show {{ 0%, 82% {{ opacity: 1; }} 83%, 94% {{ opacity: 0; }} 95%, 100% {{ opacity: 1; }} }}
@keyframes mx-breath-show {{ 0%, 82% {{ opacity: 0; }} 83%, 94% {{ opacity: 1; }} 95%, 100% {{ opacity: 0; }} }}
@keyframes mx-bob {{ 50% {{ translate: 0 -1.2%; }} }}
@media (prefers-reduced-motion: reduce) {{
  .mx-scene * {{ animation-play-state: paused !important; }}
  .mx-world {{ animation-play-state: running !important; }}
}}
"""

PAGE_CSS = f"""
@import url('https://fonts.googleapis.com/css2?family=Silkscreen&family=Inter:wght@400;500;600;700&display=swap');
@font-face {{ font-family: 'Ringbearer'; src: url('{FONT}') format('truetype'); font-display: swap; }}
:root {{ --mx-surface: {PAL['surface']}; --mx-ink: {PAL['ink']}; --mx-ink2: {PAL['ink2']}; --mx-muted: {PAL['muted']};
  --mx-gold: {PAL['gold']}; --mx-lava: {PAL['lava']}; }}
.stApp, .stApp p, .stApp label, .stApp li {{ color: var(--mx-ink); font-family: 'Inter', sans-serif; }}
[data-testid="stAppViewContainer"], [data-testid="stMain"], [data-testid="stBottom"] > div {{ background: transparent; }}
[data-testid="stHeader"] {{ background: rgba(7, 8, 13, .72); backdrop-filter: blur(6px); border-bottom: 1px solid #3a1c0e; }}
.block-container {{ max-width: 960px; padding-top: 4.6rem; padding-bottom: 6rem; }}
[data-testid="stSidebar"] {{ background: rgba(18, 13, 11, .97); border-right: 2px solid #b4501c;
  box-shadow: 0 0 18px rgba(255, 106, 19, .25); }}
[data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {{ font-family: 'Ringbearer', serif; color: var(--mx-gold);
  font-weight: 400; text-transform: lowercase; letter-spacing: .02em; }}

.mx-panel, .vg-hero, .vg-card, .st-key-vg_chart, .vg-step, [data-testid="stExpander"] details {{
  background: rgba(21, 16, 13, .96); border: 2px solid #c8561c; border-radius: 0;
  box-shadow: 0 0 0 1px #2a0e06, 0 0 14px rgba(255, 106, 19, .28), inset 0 0 0 1px rgba(255, 176, 96, .10);
  animation: mx-ember 7s ease-in-out infinite; }}
@keyframes mx-ember {{ 50% {{ box-shadow: 0 0 0 1px #2a0e06, 0 0 20px rgba(255, 120, 30, .40),
  inset 0 0 0 1px rgba(255, 176, 96, .14); }} }}

.vg-hero {{ position: relative; max-width: 58%; padding: 30px 32px 26px; margin-bottom: 64px; }}
.vg-eyebrow {{ font-family: 'Silkscreen', monospace; font-size: 12px; letter-spacing: .14em; color: var(--mx-lava);
  text-transform: uppercase; }}
.vg-hero-value {{ font-family: 'Ringbearer', serif; font-size: 88px; line-height: 1.05; color: var(--mx-gold);
  margin: 10px 0 4px; text-shadow: 0 3px 0 #4a2a08, 0 0 24px rgba(255, 170, 40, .35); }}
.vg-hero-delta {{ font-size: 16px; color: var(--mx-ink2); }}
.vg-hero-delta b {{ color: var(--mx-gold); }}
.vg-chips {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 18px; }}
.vg-chip {{ font-size: 12.5px; color: var(--mx-ink2); padding: 6px 10px; border: 1px solid #6a3a1a; background: #0f0b09; }}
.vg-chip b {{ color: var(--mx-ink); margin-left: 6px; font-weight: 600; }}

.vg-section {{ margin: 70px 0 14px; }}
.vg-section-title {{ font-family: 'Ringbearer', serif; font-size: 34px; color: var(--mx-gold); text-transform: lowercase;
  letter-spacing: .02em; text-shadow: 0 2px 0 #000, 0 0 16px rgba(255, 140, 30, .35); }}
.vg-section-sub {{ display: inline-block; margin-top: 6px; padding: 4px 10px; font-size: 13px; color: var(--mx-ink2);
  background: rgba(10, 8, 7, .82); border-left: 2px solid var(--mx-lava); }}

.vg-cards {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(170px, 1fr)); gap: 12px; }}
.vg-card {{ padding: 13px 14px 12px; }}
.vg-card-label {{ font-family: 'Silkscreen', monospace; font-size: 10.5px; letter-spacing: .1em; color: var(--mx-lava);
  text-transform: uppercase; }}
.vg-card-value {{ font-size: 26px; font-weight: 700; color: var(--mx-ink); margin-top: 4px; }}
.vg-card-sub {{ font-size: 12px; color: var(--mx-muted); margin-top: 2px; }}

.st-key-vg_chart {{ padding: 16px 16px 6px; }}

.vg-ledger {{ display: flex; flex-direction: column; gap: 10px; }}
.vg-step {{ display: grid; grid-template-columns: 58px 1fr auto; align-items: center; gap: 16px; padding: 14px 18px; }}
.vg-step-n {{ font-family: 'Ringbearer', serif; font-size: 30px; color: var(--mx-gold); text-align: center;
  border-right: 1px solid #4a2410; }}
.vg-step-title {{ font-family: 'Silkscreen', monospace; font-size: 12.5px; letter-spacing: .08em; color: var(--mx-ink);
  text-transform: uppercase; }}
.vg-step-math {{ font-size: 13.5px; color: var(--mx-ink2); margin-top: 6px; line-height: 1.5; }}
.vg-step-value {{ font-size: 28px; font-weight: 700; color: var(--mx-ink); text-align: right; white-space: nowrap; }}
.vg-step-value small {{ display: block; font-family: 'Silkscreen', monospace; font-size: 10px; letter-spacing: .1em;
  color: var(--mx-muted); font-weight: 400; text-transform: uppercase; }}
.vg-total {{ border-color: #ff8a2a; }}
.vg-total .vg-step-value {{ font-family: 'Ringbearer', serif; font-weight: 400; font-size: 44px; color: var(--mx-gold); }}

[data-testid="stExpander"] summary p {{ font-family: 'Ringbearer', serif; font-size: 22px; color: var(--mx-gold);
  text-transform: lowercase; }}
.stApp [data-testid="stCaptionContainer"] {{ background: rgba(10, 8, 7, .8); padding: 6px 10px; }}
"""


def apply(name: str | None = None) -> None:
    """Inject the theme (fonts, panels, the scene) for this run."""
    markup, sprite_css = _scene_html()
    st.html(f"<style>{PAGE_CSS}{SCENE_CSS}{sprite_css}</style>")
    st.html(markup)


# ------------------------------------------------------------------ components

def _e(s: str) -> str:
    return html.escape(str(s), quote=False)


def hero(eyebrow: str, value: str, delta_html: str, chips: list[tuple[str, str]]) -> None:
    chips_html = "".join(f'<span class="vg-chip">{_e(k)}<b>{_e(v)}</b></span>' for k, v in chips)
    st.html(f'<div class="vg-hero"><div class="vg-eyebrow">{_e(eyebrow)}</div>'
            f'<div class="vg-hero-value">{_e(value)}</div><div class="vg-hero-delta">{delta_html}</div>'
            f'<div class="vg-chips">{chips_html}</div></div>')


def section(title: str, sub: str | None = None) -> None:
    st.html(f'<div class="vg-section"><div class="vg-section-title">{_e(title.lower())}</div>'
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
