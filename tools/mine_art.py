"""Pixel-art assets for the "Mine" theme: a dwarven gold mine under the mountain. Lava runs through irrigation canals
and pours into a half-hidden bitcoin sigil; dwarves work galleries and walkways; a dragon broods on a hoard at the top
with Matt Cole, Strive's CEO, riding it (navy suit, bitcoin-orange tie, a Strive S pin; he crackles with electricity
when it breathes fire). The STRIVE wordmark is carved into the dais under them, inlaid with gold.

Everything is drawn here, pixel by pixel, at low resolution and scaled up crisply in the browser
(image-rendering: pixelated). Deterministic: the same seed always draws the same mine.

    .venv\\Scripts\\python tools\\mine_art.py          writes static/mine/*.png and renderings/mine-preview.png
"""
from __future__ import annotations

import math
import random
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "static" / "mine"
sys.path.insert(0, str(ROOT))
from panel import mine_layout as L  # noqa: E402
W, H = 480, 1200  # the cavern, in art pixels (shown ~3x)


def C(h: str, a: int = 255) -> tuple:
    return int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16), a


# stone runs cool (slate); light runs warm (lava, gold)
STONE = [C("#0d0e14"), C("#161922"), C("#20242f"), C("#2b313e"), C("#38404f"), C("#4a5464"), C("#5f6a7a")]
WARM = [C("#1c1310"), C("#2a1d17"), C("#3b2a20"), C("#54392a")]
GOLD = [C("#4a2d0c"), C("#7a4c12"), C("#b07a1c"), C("#e0a72b"), C("#ffd24d"), C("#fff0a6")]
LAVA = [C("#3a0d06"), C("#6b1608"), C("#a8220b"), C("#d93d0e"), C("#ff6a13"), C("#ff9d2e"), C("#ffd27a"), C("#fff4c2")]
BTC = C("#f7931a")
OUTLINE = C("#0a0708")
CLEAR = (0, 0, 0, 0)
BAYER = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) / 16.0


class Cv:
    """An RGBA pixel canvas."""

    def __init__(self, w: int, h: int, fill=CLEAR):
        self.w, self.h = w, h
        self.a = np.zeros((h, w, 4), np.uint8)
        self.a[:, :] = fill

    def rect(self, x, y, w, h, c):
        x0, y0, x1, y1 = max(0, int(x)), max(0, int(y)), min(self.w, int(x + w)), min(self.h, int(y + h))
        if x1 > x0 and y1 > y0:
            self.a[y0:y1, x0:x1] = c

    def px(self, x, y, c):
        x, y = int(x), int(y)
        if 0 <= x < self.w and 0 <= y < self.h:
            self.a[y, x] = c

    def line(self, x0, y0, x1, y1, c):
        n = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
        for i in range(n):
            t = i / max(n - 1, 1)
            self.px(round(x0 + (x1 - x0) * t), round(y0 + (y1 - y0) * t), c)

    def mask_poly(self, pts) -> np.ndarray:
        im = Image.new("L", (self.w, self.h), 0)
        ImageDraw.Draw(im).polygon([(float(x), float(y)) for x, y in pts], fill=255)
        return np.array(im) > 0

    def mask_ellipse(self, cx, cy, rx, ry) -> np.ndarray:
        im = Image.new("L", (self.w, self.h), 0)
        ImageDraw.Draw(im).ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=255)
        return np.array(im) > 0

    def fill(self, mask, c):
        self.a[mask] = c

    def paste(self, other: "Cv", x: int, y: int):
        """Copy other's opaque pixels onto this canvas at (x, y)."""
        x, y = int(x), int(y)
        sx0, sy0 = max(0, -x), max(0, -y)
        dx0, dy0 = max(0, x), max(0, y)
        w, h = min(other.w - sx0, self.w - dx0), min(other.h - sy0, self.h - dy0)
        if w <= 0 or h <= 0:
            return
        src = other.a[sy0:sy0 + h, sx0:sx0 + w]
        m = src[:, :, 3] > 0
        self.a[dy0:dy0 + h, dx0:dx0 + w][m] = src[m]

    def outline(self, c=OUTLINE):
        """A 1px outline around every opaque shape (sprites)."""
        op = self.a[:, :, 3] > 0
        ring = np.zeros_like(op)
        ring[1:, :] |= op[:-1, :]
        ring[:-1, :] |= op[1:, :]
        ring[:, 1:] |= op[:, :-1]
        ring[:, :-1] |= op[:, 1:]
        self.a[ring & ~op] = c

    def image(self) -> Image.Image:
        return Image.fromarray(self.a, "RGBA")


def grid(rows: list[str], pal: dict) -> Cv:
    """A sprite from a text grid ('.' is transparent)."""
    cv = Cv(len(rows[0]), len(rows))
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch != ".":
                cv.px(x, y, pal[ch])
    return cv


def sheet(frames: list[Cv]) -> Image.Image:
    w, h = frames[0].w, frames[0].h
    out = Image.new("RGBA", (w * len(frames), h), CLEAR)
    for i, f in enumerate(frames):
        out.paste(f.image(), (i * w, 0))
    return out


# ------------------------------------------------------------------ sprites: dwarves

DWARF_PAL = {"k": OUTLINE, "H": C("#a3adb7"), "h": C("#5d6772"), "g": GOLD[3], "s": C("#eab38c"), "e": C("#24160f"),
             "B": C("#8a4a22"), "b": C("#5c2f15"), "t": C("#3f6b46"), "T": C("#294a30"), "l": C("#6b4a2a"),
             "L": C("#2a201b"), "n": C("#c98b67")}
BEARDS = [(C("#8a4a22"), C("#5c2f15")), (C("#b5482a"), C("#7a2c18")), (C("#d9d3c6"), C("#9c968a")),
          (C("#3a2a22"), C("#211712"))]
TUNICS = [(C("#3f6b46"), C("#294a30")), (C("#3a5585"), C("#263a5e")), (C("#8a3a2a"), C("#5e271c")),
          (C("#6a5a3a"), C("#46391f"))]

DWARF = [  # 12 x 14, facing right
    ".....kkk....",
    "....kHHHk...",
    "...kHHHHhk..",
    "..kgggggggk.",
    "..ksssssekk.",
    "..kBsnssBk..",
    ".kBBBBBBBBk.",
    ".kBBBbBBBBk.",
    ".ktBBBBBBtk.",
    ".kttBBBBttk.",
    ".kTllglllTk.",
    "..kttttTTk..",
]
LEGS = [["..kLLk.kLLk.", "..kkk...kkk."], ["..kLLkkLLk..", "...kkkkkk..."],
        [".kLLk..kLLk.", ".kkk....kkk."], ["...kLLLLk...", "...kkkkkk..."]]


def dwarf(frame_legs: int, beard: int, tunic: int, bob: int = 0) -> Cv:
    pal = dict(DWARF_PAL)
    pal["B"], pal["b"] = BEARDS[beard]
    pal["t"], pal["T"] = TUNICS[tunic]
    body = grid(DWARF + LEGS[frame_legs], pal)
    cv = Cv(18, 17)
    cv.paste(body, 3, 2 + bob)
    return cv


def dwarf_miner(beard: int, tunic: int) -> list[Cv]:
    """Pickaxe swing: raised, high, strike, recoil."""
    frames = []
    wood, steel, hi = C("#8a5a2e"), C("#b8c0c8"), C("#e8eef2")
    for i, (hx, hy, tx, ty) in enumerate([(9, 4, 4, -1), (12, 3, 13, -1), (14, 10, 17, 13), (12, 7, 16, 4)]):
        cv = dwarf(0, beard, tunic, bob=1 if i == 2 else 0)
        cv.line(hx, hy + 6, tx, ty + 6 if i < 2 else ty, wood)  # handle from the hands to the head
        px, py = (tx, ty + 6) if i < 2 else (tx, ty)
        for dx, dy in [(-2, -1), (-1, -1), (0, 0), (1, 1), (2, 1)] if i != 2 else [(-1, 2), (0, 1), (0, 0), (1, -1), (1, -2)]:
            cv.px(px + dx, py + dy, steel)
        cv.px(px, py, hi)
        if i == 2:  # sparks on the strike
            for sx, sy in [(17, 9), (16, 15), (15, 8)]:
                cv.px(sx, sy, GOLD[5])
        frames.append(cv)
    return frames


def dwarf_walker(beard: int, tunic: int) -> list[Cv]:
    return [dwarf(f, beard, tunic, bob=1 if f in (1, 3) else 0) for f in range(4)]


def dwarf_smith(beard: int, tunic: int) -> list[Cv]:
    """Hammer at the anvil: raised, high, strike (sparks), rest."""
    frames = []
    wood, steel = C("#7a4f2a"), C("#9aa4ae")
    for i, (ex, ey) in enumerate([(9, 0), (13, 1), (16, 9), (14, 6)]):
        cv = dwarf(0, beard, tunic, bob=1 if i == 2 else 0)
        cv.line(11, 9, ex, ey + (0 if i == 2 else 2), wood)
        cv.rect(ex - 1, ey - 1 + (0 if i == 2 else 2), 3, 2, steel)
        if i == 2:
            for sx, sy in [(17, 7), (17, 12), (15, 6), (16, 13)]:
                cv.px(sx, sy, GOLD[5] if sx % 2 else LAVA[6])
        frames.append(cv)
    return frames


def cart_pusher(beard: int, tunic: int) -> list[Cv]:
    """A dwarf pushing an ore cart heaped with gold and (look closely) bitcoin-orange coins."""
    frames = []
    for f in range(4):
        cv = Cv(34, 17)
        cv.paste(dwarf(f, beard, tunic, bob=1 if f in (1, 3) else 0), 0, 0)
        cart = Cv(16, 12)
        cart.rect(1, 4, 14, 6, C("#4a3020"))
        cart.rect(1, 4, 14, 1, C("#6b4630"))
        cart.rect(0, 3, 16, 1, C("#7d8792"))
        for x in range(2, 14):  # the heap
            top = 1 + abs(x - 8) // 3
            for y in range(top, 4):
                c = BTC if (x * 7 + y * 3) % 5 == 0 else GOLD[3 if (x + y) % 2 else 4]
                cart.px(x, y, c)
        cart.px(5, 2, GOLD[5])
        cart.px(10, 2, C("#ffc26b"))
        for wx in (3, 11):
            cart.rect(wx, 10, 2, 2, C("#2a2a30"))
        cart.outline()
        cv.paste(cart, 17, 4 + (1 if f in (1, 3) else 0))
        frames.append(cv)
    return frames


def sparkle() -> list[Cv]:
    shapes = [[(2, 2)], [(2, 1), (1, 2), (2, 2), (3, 2), (2, 3)], [(2, 0), (2, 1), (0, 2), (1, 2), (2, 2), (3, 2),
              (4, 2), (2, 3), (2, 4)], [(2, 1), (1, 2), (3, 2), (2, 3)]]
    out = []
    for i, pts in enumerate(shapes):
        cv = Cv(5, 5)
        for x, y in pts:
            cv.px(x, y, GOLD[5] if (x, y) != (2, 2) else C("#ffffff"))
        out.append(cv)
    return out


# ------------------------------------------------------------------ sprite: Matt Cole (Strive's CEO) on the dragon

COLE_PAL = {"k": OUTLINE, "h": C("#3a3431"), "H": C("#6b635e"),                          # dark hair, combed back
            "G": C("#a7a39f"), "g": C("#76716d"),                                        # gray at the sides
            "S": C("#f1c4a6"), "s": C("#d89c80"), "d": C("#ad7158"),                     # skin
            "b": C("#3b2f29"), "e": C("#6a8fb3"), "w": C("#f4f1ea"),                     # dark brows, blue eyes
            "c": C("#a8968b"), "C": C("#7a6e66"), "B": C("#cac2bb"),                     # short salt-and-pepper beard
            "m": C("#b0605a"), "t": C("#fbf8f2")}                                        # lips, the smile
COLE_HEAD = [  # 12 x 17, three-quarter view facing left: a long face, dark hair slicked back over gray sides, a short
    "...kkkkk....",   # salt-and-pepper beard, and a smile
    ".kkhhHhhkk..",
    "khhHhhhhHhk.",
    "khhhhHhhhhgk",
    "khhhhhhhhggk",
    "kShhhhhhgGgk",
    "kSSShhhhgGgk",
    "kbbbSbbbSGgk",
    "kSSSSSSSsGgk",
    "kewSSewSsdGk",
    "kSSSsSSSssdk",
    "kSSSssSSsdsk",
    "kcmCCCmSsck.",
    "kcctttccsck.",
    "kccCmCccBk..",
    ".kcBccBck...",
    "..kkkkkk....",
]
STRIVE_S = [".XX", "X..", ".X.", "..X", "XX."]   # the Strive S, worn as a lapel pin
SUIT, SUIT_HI, SUIT_LO = C("#1b2236"), C("#34405f"), C("#10141f")
SHIRT, SHIRT_LO, TIE, TIE_LO = C("#f4f4ef"), C("#c6cad1"), BTC, C("#c46a08")
SHOE, SHOE_HI = C("#121212"), C("#3c3c3c")
RIDER_W, RIDER_H = 26, 44
FIST = (3, 7)        # where the raised fist is in the breath pose (rider pixels): the electricity starts here


def cole(summoning: bool) -> Cv:
    """Matt Cole astride the dragon, facing left, 26 x 44: navy suit with a Strive S pin, white shirt, bitcoin-orange
    tie, the near leg down the dragon's shoulder like a rider's. summoning raises his fist (electricity crackles from
    it)."""
    assert all(len(r) == 12 for r in COLE_HEAD)
    cv = Cv(RIDER_W, RIDER_H)
    ox = 2
    # near leg: thigh angled down the dragon's shoulder, knee forward, shin raked back, shoe pointing ahead
    cv.fill(cv.mask_poly([(ox + 6, 26), (ox + 19, 26), (ox + 19, 31), (ox + 11, 33), (ox + 6, 37), (ox + 1, 36),
                          (ox + 1, 32)]), SUIT)
    cv.fill(cv.mask_poly([(ox + 1, 35), (ox + 6, 35), (ox + 8, 41), (ox + 3, 41)]), SUIT)
    cv.line(ox + 1, 32, ox + 1, 35, SUIT_HI)
    cv.line(ox + 2, 36, ox + 3, 40, SUIT_HI)
    cv.line(ox + 11, 32, ox + 18, 30, SUIT_LO)
    cv.fill(cv.mask_poly([(ox, 43), (ox, 42), (ox + 2, 40), (ox + 8, 40), (ox + 9, 43)]), SHOE)
    cv.rect(ox + 1, 41, 3, 1, SHOE_HI)
    # jacket, shirt, tie
    cv.fill(cv.mask_poly([(ox + 6, 17), (ox + 9, 15), (ox + 18, 15), (ox + 21, 18), (ox + 21, 29), (ox + 5, 29),
                          (ox + 4, 19)]), SUIT)
    cv.rect(ox + 19, 18, 2, 11, SUIT_LO)
    cv.rect(ox + 5, 20, 1, 9, SUIT_HI)
    cv.fill(cv.mask_poly([(ox + 9, 14), (ox + 16, 14), (ox + 12.5, 23)]), SHIRT)
    cv.line(ox + 15, 15, ox + 13, 21, SHIRT_LO)
    cv.rect(ox + 12, 15, 2, 2, TIE)
    cv.fill(cv.mask_poly([(ox + 11.5, 17), (ox + 14, 17), (ox + 14.5, 23), (ox + 12.7, 25.5), (ox + 11, 23)]), TIE)
    cv.line(ox + 14, 18, ox + 14, 23, TIE_LO)
    cv.line(ox + 9, 15, ox + 12, 23, SUIT_HI)      # lapels
    cv.line(ox + 17, 15, ox + 14, 24, SUIT_HI)
    for y, row in enumerate(STRIVE_S):                 # the pin, on his chest beside the lapel
        for x, ch in enumerate(row):
            if ch == "X":
                cv.px(ox + 17 + x, 19 + y, C("#eef1f4"))
    cv.paste(grid(COLE_HEAD, COLE_PAL), ox + 6, 0)
    # near arm
    if summoning:   # fist raised high, ready to crackle
        cv.fill(cv.mask_poly([(ox + 4, 19), (ox + 9, 18), (ox + 5, 9), (ox + 1, 10)]), SUIT)
        cv.line(ox + 1, 11, ox + 4, 19, SUIT_HI)
        cv.rect(FIST[0] - 1, FIST[1] - 1, 4, 4, COLE_PAL["S"])
        cv.rect(FIST[0] - 1, FIST[1] + 2, 4, 1, COLE_PAL["s"])
    else:           # hand forward on the reins
        cv.fill(cv.mask_poly([(ox + 5, 18), (ox + 10, 19), (ox + 7, 25), (ox + 1, 27), (ox, 25), (ox + 4, 22)]),
                SUIT)
        cv.line(ox + 1, 25, ox + 5, 19, SUIT_HI)
        cv.rect(ox - 2, 25, 3, 3, COLE_PAL["S"])
        cv.rect(ox - 2, 27, 3, 1, COLE_PAL["s"])
    cv.outline()
    return cv


def far_foot() -> Cv:
    """The rider's other foot: the leg is behind the dragon, and the shoe peeks out below its neck."""
    cv = Cv(10, 7)
    cv.rect(4, 0, 4, 4, SUIT_LO)
    cv.fill(cv.mask_poly([(0, 6), (0, 5), (2, 3), (8, 3), (9, 6)]), SHOE)
    cv.rect(1, 4, 3, 1, SHOE_HI)
    cv.outline()
    return cv


def zap() -> list[Cv]:
    """The rider's electricity, 8 frames in the ZAP box: small forked bolts that crackle from his raised fist, his
    shoulders and his head in changing formations (and some frames dark, so it flickers). Short: none reach far."""
    z = L.ZAP
    rx, ry = L.RIDER
    fist = (rx + FIST[0] - z["x"], ry + FIST[1] - z["y"])
    head = (rx + 14 - z["x"], ry - z["y"])
    back = (rx + 22 - z["x"], ry + 18 - z["y"])
    chest = (rx + 8 - z["x"], ry + 20 - z["y"])
    core, inner, halo = (255, 255, 255, 255), (190, 236, 255, 255), (100, 185, 255, 170)

    def bolt(cv, start, ang, length, rnd, branch=True):
        a = math.radians(ang + rnd.uniform(-12, 12))
        ux, uy, sign = math.cos(a), math.sin(a), rnd.choice((-1, 1))
        pts = [start]
        for i in range(1, int(length / 2.5) + 1):   # step along the bolt, kicking out left and right in turn
            d, kick = i * 2.5, sign * rnd.uniform(1.0, 2.2) * (1 if i % 2 else -1)
            pts.append((start[0] + ux * d - uy * kick, start[1] + uy * d + ux * kick))
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            for dx, dy in ((1, 0), (0, 1)):
                cv.line(x0 + dx, y0 + dy, x1 + dx, y1 + dy, halo)
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            cv.line(x0, y0, x1, y1, inner)
        for (px_, py_) in pts[1::2]:
            cv.px(px_, py_, core)
        if branch and len(pts) > 3:
            bolt(cv, pts[len(pts) // 2], ang + rnd.choice((-55, 55)), length * 0.45, rnd, branch=False)

    def arc(cv, p, q, rnd):  # a crackle jumping between two points on him
        n = 5
        pts = [p] + [(p[0] + (q[0] - p[0]) * i / n + rnd.uniform(-2, 2), p[1] + (q[1] - p[1]) * i / n
                      + rnd.uniform(-2, 2)) for i in range(1, n)] + [q]
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            for dx, dy in ((1, 0), (0, 1)):
                cv.line(x0 + dx, y0 + dy, x1 + dx, y1 + dy, halo)
            cv.line(x0, y0, x1, y1, inner)

    def sparks(cv, at, rnd, n=4):
        for _ in range(n):
            cv.px(at[0] + rnd.randint(-4, 4), at[1] + rnd.randint(-4, 4), core if rnd.random() < 0.5 else inner)

    plan = [  # bolts per frame as (source, angle, length); None is a dark frame
        [(fist, -120, 10), (fist, 200, 8)],
        None,
        [(head, -80, 7), (back, -20, 7), ("sparks", fist)],
        [(fist, -150, 9), (fist, -95, 8), (fist, 160, 6)],
        None,
        [("sparks", fist), ("sparks", head)],
        [("arc", fist, head), (back, 30, 7)],
        [(chest, 150, 6), (head, -110, 6)],
    ]
    frames = []
    for i, bolts in enumerate(plan):
        cv = Cv(z["w"], z["h"])
        rnd = random.Random(500 + i)
        for b in bolts or []:
            if b[0] == "sparks":
                sparks(cv, b[1], rnd)
            elif b[0] == "arc":
                arc(cv, b[1], b[2], rnd)
            else:
                bolt(cv, *b, rnd)
        frames.append(cv)
    return frames


def _bezier(p0, p1, p2, n):
    return [((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0],
             (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]) for t in [i / (n - 1) for i in range(n)]]


def dragon_frame(wing: int, breath: bool) -> Cv:
    """128 x 100, facing left, crouched on the hoard. wing 0-3 is the flap phase; breath opens the jaw."""
    cv = Cv(128, 100)
    red, red_hi, red_dk, red_dd = C("#a3241a"), C("#d2492c"), C("#6a1515"), C("#3e0b0e")
    belly, belly_dk = C("#dcaa48"), C("#9a6a22")
    membrane, membrane_dk, membrane_dd = C("#8a2420"), C("#5e1616"), C("#3e0e10")
    bone, bone_hi = C("#b8935c"), C("#e6c98c")

    def shade(mask, top, mid, low, split=(0.36, 0.72)):
        ys, xs = np.nonzero(mask)
        if len(ys) == 0:
            return
        y0, y1 = ys.min(), ys.max() + 1
        t = (ys - y0) / max(y1 - y0, 1) + BAYER[ys % 4, xs % 4] * 0.12
        cv.a[ys, xs] = np.where((t < split[0])[:, None], top, np.where((t < split[1])[:, None], mid, low))

    def wing_shape(shoulder, elbow, wrist, tips, back, dark=False):
        layer = Cv(128, 100)
        pts = [shoulder, elbow, wrist, *tips, back]
        mem = layer.mask_poly(pts)
        for (a, b) in zip(tips, tips[1:]):  # scallops between finger tips
            mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
            inward = ((mid[0] * 3 + wrist[0]) / 4, (mid[1] * 3 + wrist[1]) / 4)
            mem &= ~layer.mask_poly([a, inward, b])
        ys, xs = np.nonzero(mem)
        hi, lo = (membrane_dk, membrane_dd) if dark else (membrane, membrane_dk)
        for y, x in zip(ys, xs):
            near_arm = abs((y - wrist[1]) - (x - wrist[0]) * 0.2) < 6
            layer.a[y, x] = hi if near_arm or BAYER[y % 4, x % 4] > 0.45 else lo
        for t in tips:
            layer.line(*wrist, *t, bone)
        layer.line(*shoulder, *elbow, bone_hi)
        layer.line(*elbow, *wrist, bone_hi)
        layer.line(shoulder[0], shoulder[1] + 1, elbow[0], elbow[1] + 1, bone)
        layer.outline()
        return layer

    bob = 1 if wing in (1, 3) else 0
    poses = [  # (elbow, wrist, tips) for the near wing, per flap phase
        ((92, 30), (104, 6), [(126, 12), (126, 30), (118, 46), (104, 52)]),
        ((96, 34), (112, 16), [(127, 26), (124, 42), (114, 54), (100, 56)]),
        ((98, 44), (116, 38), [(127, 52), (120, 64), (108, 66), (96, 62)]),
        ((96, 36), (112, 20), [(127, 30), (124, 46), (114, 56), (100, 58)]),
    ]
    elbow, wrist, tips = poses[wing]
    # far wing: the near wing's twin, set back and darker, mostly hidden behind it
    off = (-16, -5)
    sh = lambda p: (p[0] + off[0], p[1] + off[1])
    cv.paste(wing_shape(sh((78, 54 + bob)), sh(elbow), sh(wrist), [sh(t) for t in tips], sh((92, 60 + bob)), dark=True),
             0, 0)
    rx, ry = L.RIDER
    cv.paste(far_foot(), rx - 11, ry + 37 + bob)
    # tail: rests on the hoard, curling forward under the dragon
    tail_pts = _bezier((104, 74 + bob), (128, 98), (78, 97), 16)
    for i, (x, y) in enumerate(tail_pts):
        r = max(1.5, 7 - i * 0.42)
        shade(cv.mask_ellipse(x, y, r, r), red_hi, red, red_dk)
    tx, ty = tail_pts[-1]
    cv.fill(cv.mask_poly([(tx, ty - 3), (tx - 8, ty + 2), (tx + 1, ty + 6)]), red_dk)
    # haunch, body, front leg
    shade(cv.mask_poly([(92, 66), (106, 66), (110, 82), (104, 92), (94, 92), (98, 82)]), red, red_dk, red_dd)
    body = cv.mask_ellipse(84, 66 + bob, 26, 15)
    shade(body, red_hi, red, red_dk)
    cv.fill(cv.mask_ellipse(82, 74 + bob, 20, 7) & body, belly)
    for x in range(66, 100, 5):
        cv.line(x, 69 + bob, x + 1, 80 + bob, belly_dk)
    shade(cv.mask_poly([(60, 68), (72, 70), (70, 84), (66, 94), (56, 94), (60, 84)]), red, red_dk, red_dd)
    for cx, cy in [(56, 94), (60, 95), (64, 94), (95, 92), (99, 93), (103, 92)]:
        cv.px(cx, cy, C("#efe6d2"))
    # neck: an S-curve up from the chest, then forward to the head
    neck = _bezier((66, 60 + bob), (44, 52), (36, 26 + bob), 14)
    for i, (x, y) in enumerate(neck):
        r = 9.5 - i * 0.32
        shade(cv.mask_ellipse(x, y, r, r), red_hi, red, red_dk)
    for (x0, y0), (x1, y1) in zip(neck[::2], neck[2::2]):  # throat plates
        cv.line(x0 - 5, y0 + 4, x1 - 5, y1 + 4, belly)
    # head: brow, snout, jaw (opens to breathe), horns swept back
    hb = bob
    jaw_drop = 7 if breath else 0
    head = cv.mask_poly([(40, 18 + hb), (44, 24 + hb), (42, 32 + hb), (30, 34 + hb), (16, 32 + hb), (8, 30 + hb),
                         (8, 25 + hb), (18, 21 + hb), (28, 17 + hb)])
    shade(head, red_hi, red, red_dk)
    cv.fill(cv.mask_poly([(28, 17 + hb), (40, 18 + hb), (36, 21 + hb), (24, 21 + hb)]), red_dk)  # brow ridge
    jaw = cv.mask_poly([(34, 33 + hb), (18, 33 + hb + jaw_drop // 2), (9, 32 + hb + jaw_drop),
                        (10, 35 + hb + jaw_drop), (22, 37 + hb + jaw_drop), (36, 36 + hb)])
    shade(jaw, red, red_dk, red_dd)
    if breath:
        cv.fill(cv.mask_poly([(9, 31 + hb), (20, 33 + hb), (10, 33 + hb + jaw_drop)]), LAVA[6])
        for tx_ in (11, 14, 17):
            cv.px(tx_, 31 + hb, C("#f2ead8"))
    for base, ctrl, tip_ in [((38, 18), (50, 12), (60, 15)), ((33, 17), (42, 8), (52, 4))]:  # two horns, swept back
        pts = _bezier((base[0], base[1] + hb), (ctrl[0], ctrl[1] + hb), (tip_[0], tip_[1] + hb), 9)
        for i, (x, y) in enumerate(pts):
            r = max(0.6, 2.2 - i * 0.22)
            cv.fill(cv.mask_ellipse(x, y, r, r), C("#e8dbbb") if i < 6 else C("#fff6dc"))
            cv.px(x, y + r, C("#a8946a"))
    cv.px(24, 24 + hb, C("#ffe14a"))
    cv.px(25, 24 + hb, C("#ffe14a"))
    cv.px(24, 25 + hb, OUTLINE)
    cv.px(10, 27 + hb, OUTLINE)
    for (x, y) in [(46, 44), (52, 50), (60, 52), (68, 52), (76, 51), (84, 51), (92, 52), (100, 55)]:  # spine ridges
        cv.fill(cv.mask_poly([(x, y + bob), (x + 2, y - 4 + bob), (x + 4, y + bob)]), red_dk)
    cv.outline()
    cv.paste(cole(breath), rx, ry + bob)
    cv.paste(wing_shape((78, 54 + bob), elbow, wrist, tips, (92, 60 + bob)), 0, 0)
    return cv


def fire() -> list[Cv]:
    """A cone of dragon fire, 76 x 30, pointing left (its root, the middle of the right edge, sits at the dragon's
    MOUTH): banded core, flicker, embers."""
    out = []
    for f in range(4):
        rnd = random.Random(40 + f)
        cv = Cv(76, 30)
        for x in range(76):
            reach = (75 - x) / 75  # 0 at the mouth (right edge), 1 at the tip
            wob = math.sin(x * 0.45 + f * 1.7) * 1.2
            half = 2.5 + reach * (10 + f * 0.6)
            for y in range(30):
                d = abs(y - 15 - wob * reach) / half
                if d > 1:
                    continue
                band = d + reach * 0.55
                c = LAVA[7] if band < 0.35 else LAVA[6] if band < 0.6 else LAVA[5] if band < 0.85 else \
                    LAVA[4] if band < 1.1 else LAVA[3]
                if reach > 0.75 and rnd.random() < (reach - 0.75) * 2.5:
                    continue
                cv.px(x, y, c)
        for _ in range(10):  # embers
            cv.px(rnd.randint(0, 30), rnd.randint(3, 26), LAVA[5])
        out.append(cv)
    return out


def build_sprites() -> dict[str, Image.Image]:
    s = {}
    s["miner_a"] = sheet(dwarf_miner(0, 0))
    s["miner_b"] = sheet(dwarf_miner(1, 1))
    s["miner_c"] = sheet(dwarf_miner(2, 3))
    s["walker_a"] = sheet(dwarf_walker(3, 1))
    s["walker_b"] = sheet(dwarf_walker(1, 2))
    s["walker_c"] = sheet(dwarf_walker(2, 0))
    s["smith"] = sheet(dwarf_smith(1, 2))
    s["cart"] = sheet(cart_pusher(0, 3))
    s["sparkle"] = sheet(sparkle())
    s["dragon"] = sheet([dragon_frame(w, False) for w in range(4)])
    s["dragon_breath"] = sheet([dragon_frame(w, True) for w in (0, 2)])  # head held level: fire stays in the mouth
    s["fire"] = sheet(fire())
    s["zap"] = sheet(zap())
    return s


# ------------------------------------------------------------------ the cavern

BTC_GLYPH = [  # the bitcoin B, carved into the sigil (scaled 2x)
    "..#.#......",
    "..#.#......",
    "#######....",
    ".##...##...",
    ".##....##..",
    ".##...##...",
    ".######....",
    ".##....##..",
    ".##.....##.",
    ".##.....##.",
    ".##....##..",
    "########...",
    "..#.#......",
    "..#.#......",
]


def prect(cv: Cv, region, x, y, w, h, c):
    """Paint a rect, but only where region (a full-canvas bool mask, or None) allows."""
    x0, y0, x1, y1 = max(0, int(x)), max(0, int(y)), min(cv.w, int(x + w)), min(cv.h, int(y + h))
    if x1 <= x0 or y1 <= y0:
        return
    if region is None:
        cv.a[y0:y1, x0:x1] = c
    else:
        sub = cv.a[y0:y1, x0:x1]
        sub[region[y0:y1, x0:x1]] = c


def slabs(cv, x0, y0, x1, y1, rng, tones, region=None, h_rng=(5, 11), w_rng=(16, 52)):
    """Stacked rock slabs: body, lit top edge, shadowed underside, a dark seam on the left, speckle."""
    top_i = len(tones) - 1
    y = y0
    while y < y1:
        h = rng.randint(*h_rng)
        x = x0 - rng.randint(0, 30)
        while x < x1:
            w = rng.randint(*w_rng)
            k = rng.random()
            i = 2 if k < 0.55 else 1 if k < 0.8 else 3
            prect(cv, region, x, y, w, h, tones[i])
            prect(cv, region, x, y, w, 1, tones[min(i + 1, top_i)])
            prect(cv, region, x + 1, y, min(6, w), 1, tones[min(i + 2, top_i)])
            prect(cv, region, x, y + h - 1, w, 1, tones[0])
            prect(cv, region, x, y, 1, h, tones[max(i - 1, 0)])
            for _ in range(w * h // 18):
                px, py = x + rng.randint(1, w - 1), y + rng.randint(1, max(1, h - 2))
                c = tones[max(i - 1, 0)] if rng.random() < 0.6 else tones[min(i + 1, top_i)]
                prect(cv, region, px, py, 1, 1, c)
            x += w
        y += h


def masonry(cv, x0, y0, x1, y1, rng, tones, bw=20, bh=9):
    """Dwarven ashlar: regular courses, offset joints, each block lit on top."""
    for row, y in enumerate(range(y0, y1, bh)):
        off = (bw // 2) * (row % 2)
        for x in range(x0 - off, x1, bw):
            i = rng.choice([2, 2, 3, 2, 1])
            xs = max(x, x0)
            ww = min(bw, x1 - xs)
            prect(cv, None, xs, y, ww, bh, tones[i])
            prect(cv, None, xs, y, ww, 1, tones[i + 1])
            prect(cv, None, xs, y + bh - 1, ww, 1, tones[0])
            if x >= x0:
                prect(cv, None, x, y, 1, bh, tones[0])


def rune_band(cv, x0, x1, y, tones):
    """A carved band of angular dwarven knotwork with gold inlay."""
    prect(cv, None, x0, y, x1 - x0, L.RUNE_H, tones[1])
    prect(cv, None, x0, y, x1 - x0, 1, tones[4])
    prect(cv, None, x0, y + L.RUNE_H - 1, x1 - x0, 1, tones[0])
    for x in range(x0, x1, 8):
        for d in range(4):
            cv.px(x + d, y + 1 + d, tones[4])
            cv.px(x + 7 - d, y + 1 + d, tones[4])
        cv.px(x + 3, y + 3, GOLD[3])
        cv.px(x + 4, y + 3, GOLD[2])


def column(cv, x, y0, y1, w, tones):
    """A dwarven pillar: stepped capital and base, fluted shaft, gold bands."""
    cap, base = 9, 9
    for i in range(w):
        c = tones[4] if i == 0 else tones[0] if i >= w - 2 else tones[3] if (i % 4) in (1, 2) else tones[2]
        prect(cv, None, x + i, y0 + cap, 1, y1 - y0 - cap - base, c)
    for y in range(y0 + cap + 30, y1 - base - 10, 46):
        prect(cv, None, x, y, w, 2, GOLD[2])
        prect(cv, None, x, y, w, 1, GOLD[4])
        prect(cv, None, x + w - 2, y, 2, 2, GOLD[1])
    for k, dx in enumerate([4, 2, 0]):  # capital, widening upward
        yy = y0 + cap - (k + 1) * 3
        prect(cv, None, x - dx, yy, w + 2 * dx, 3, tones[3])
        prect(cv, None, x - dx, yy, w + 2 * dx, 1, tones[5])
        prect(cv, None, x - dx, yy + 2, w + 2 * dx, 1, tones[0])
    for k, dx in enumerate([1, 3, 5]):  # base, widening downward
        yy = y1 - base + k * 3
        prect(cv, None, x - dx, yy, w + 2 * dx, 3, tones[3])
        prect(cv, None, x - dx, yy, w + 2 * dx, 1, tones[5])


def walkway(cv, x0, x1, y, tones, rail=True):
    """A stone walkway: thick slab with joints, a canal groove along the top, corbels below, a railing."""
    th = 8
    prect(cv, None, x0, y, x1 - x0, th, tones[3])
    prect(cv, None, x0, y, x1 - x0, 1, tones[5])
    prect(cv, None, x0, y + 1, x1 - x0, 3, C("#120a08"))   # the canal (the lava layer fills it)
    prect(cv, None, x0, y + 4, x1 - x0, 1, tones[4])
    prect(cv, None, x0, y + th - 1, x1 - x0, 1, tones[0])
    prect(cv, None, x0, y + th, x1 - x0, 2, tones[1])      # shadow under the lip
    for x in range(x0 + 7, x1, 15):
        prect(cv, None, x, y + 4, 1, th - 4, tones[1])
    for x in range(x0 + 12, x1 - 4, 34):                   # corbels
        for k in range(5):
            prect(cv, None, x + k, y + th + k, 6 - k, 1, tones[2] if k else tones[3])
    if rail:
        for x in range(x0 + 2, x1, 10):
            prect(cv, None, x, y - 7, 2, 7, tones[3])
            prect(cv, None, x, y - 7, 1, 7, tones[5])
        prect(cv, None, x0, y - 8, x1 - x0, 2, tones[3])
        prect(cv, None, x0, y - 8, x1 - x0, 1, tones[5])


def doorway(cv, x, y, w, h, tones):
    """A dwarven door: dark opening under a stepped lintel."""
    prect(cv, None, x, y, w, h, C("#07060a"))
    for k in range(3):
        prect(cv, None, x - 2 - k * 2, y - 3 - k * 3, w + 4 + k * 4, 3, tones[3 if k % 2 else 4])
    prect(cv, None, x - 2, y, 2, h, tones[3])
    prect(cv, None, x + w, y, 2, h, tones[1])
    prect(cv, None, x + w // 2 - 1, y - 9, 2, 2, GOLD[3])


def vein(cv, rng, x, y, w, h):
    """Gold showing through the rock, with a few bitcoin-orange flecks."""
    for _ in range(14):
        cx, cy, r = x + rng.uniform(0, w), y + rng.uniform(0, h), rng.uniform(2, 5)
        m = cv.mask_ellipse(cx, cy, r, r * 0.7)
        cv.fill(m, GOLD[1])
        cv.fill(m & cv.mask_ellipse(cx - 0.5, cy - 0.5, r - 1, r * 0.7 - 1), GOLD[3])
        cv.px(cx - 1, cy - 1, GOLD[5])
        if rng.random() < 0.3:
            cv.px(cx + 1, cy, BTC)


STRIVE_WORD = {  # the wordmark in its bold geometric style (the E is three bars), 8 px tall
    "S": [".######", "#######", "##.....", "######.", ".######", ".....##", "#######", "######."],
    "T": ["########", "########", "...##...", "...##...", "...##...", "...##...", "...##...", "...##..."],
    "R": ["######.", "#######", "##...##", "#######", "######.", "##.##..", "##..##.", "##...##"],
    "I": ["##"] * 8,
    "V": ["##....##", "##....##", ".##..##.", ".##..##.", ".##..##.", "..####..", "..####..", "...##..."],
    "E": ["#######", "#######", ".......", "#######", "#######", ".......", "#######", "#######"],
}


def engrave(cv, word, cx, y, tones):
    """Carve a word into stone, centered on cx: a shadowed groove (top and left), a lit lip (bottom and right), and
    gold inlay in the cut."""
    gap = 2
    width = sum(len(STRIVE_WORD[ch][0]) for ch in word) + gap * (len(word) - 1)
    x = cx - width // 2
    cut = np.zeros((cv.h, cv.w), bool)
    for ch in word:
        for dy, row in enumerate(STRIVE_WORD[ch]):
            for dx, v in enumerate(row):
                if v == "#":
                    cut[y + dy, x + dx] = True
        x += len(STRIVE_WORD[ch][0]) + gap
    shadow = np.zeros_like(cut)
    shadow[:-1, :] |= cut[1:, :]
    shadow[:, :-1] |= cut[:, 1:]
    lip = np.zeros_like(cut)
    lip[1:, :] |= cut[:-1, :]
    lip[:, 1:] |= cut[:, :-1]
    cv.fill(shadow & ~cut, tones[0])
    cv.fill(lip & ~cut & ~shadow, tones[5])
    ys, xs = np.nonzero(cut)
    for yy, xx in zip(ys, xs):                                        # inlay: brighter where the light catches
        cv.a[yy, xx] = GOLD[4] if not cut[yy - 1, xx] else GOLD[3] if BAYER[yy % 4, xx % 4] > 0.3 else GOLD[2]


def hoard(cv, rng, cx, base, rx, ry):
    """A heap of gold coins (and, if you look, bitcoins)."""
    m = cv.mask_ellipse(cx, base, rx, ry * 2) & (np.arange(cv.h)[:, None] <= base)
    ys, xs = np.nonzero(m)
    for y, x in zip(ys, xs):
        t = (y - (base - ry * 2)) / (ry * 2 + 1)
        c = GOLD[4] if t < 0.3 else GOLD[3] if t < 0.65 else GOLD[2]
        if (x * 3 + y * 5) % 7 == 0:
            c = GOLD[5] if t < 0.5 else GOLD[3]
        cv.a[y, x] = c
    for _ in range(rx):
        x, y = cx + rng.randint(-rx, rx), base - rng.randint(0, max(1, ry))
        if 0 <= x < cv.w and 0 <= y < cv.h and m[y, x]:
            cv.px(x, y, BTC if rng.random() < 0.25 else GOLD[5])
            cv.px(x + 1, y, GOLD[1])


def brazier(cv, cx, cy, tones):
    prect(cv, None, cx - 1, cy + 4, 2, 150 - cy - 4, tones[2])
    prect(cv, None, cx - 4, 146, 8, 4, tones[3])
    cv.fill(cv.mask_poly([(cx - 7, cy), (cx + 7, cy), (cx + 4, cy + 5), (cx - 4, cy + 5)]), C("#2a2a30"))
    prect(cv, None, cx - 7, cy, 14, 1, GOLD[3])


def banner(cv, x, y, w, h):
    red, red_dk = C("#7a1a18"), C("#4e1012")
    prect(cv, None, x, y, w, h + 4, red)
    prect(cv, None, x + w - 2, y, 2, h + 4, red_dk)
    notch = cv.mask_poly([(x, y + h + 5), (x + w / 2, y + h - 1), (x + w, y + h + 5)])
    cv.a[notch] = cv.a[min(cv.h - 1, y + h + 8), min(cv.w - 1, x + w + 3)]
    cx, cy = x + w // 2, y + h // 2 - 2
    cv.fill(cv.mask_poly([(cx, cy - 4), (cx + 3, cy), (cx, cy + 4), (cx - 3, cy)]), GOLD[3])
    cv.px(cx, cy, BTC)
    prect(cv, None, x - 1, y, w + 2, 1, GOLD[2])


def chain(cv, x, y0, y1):
    for y in range(y0, y1, 3):
        cv.px(x, y, C("#6a7480"))
        cv.px(x, y + 1, C("#3a414b"))
        cv.px(x + (1 if (y // 3) % 2 else -1), y + 1, C("#4a525e"))


def statue(cv, x, y, tones):
    """A dwarf king carved into the deep: helm, braided beard, hands on an axe."""
    t = tones
    prect(cv, None, x, y + 156, 84, 40, t[3])          # pedestal
    prect(cv, None, x, y + 156, 84, 1, t[5])
    prect(cv, None, x + 4, y + 152, 76, 4, t[4])
    cv.fill(cv.mask_poly([(x + 14, y + 66), (x + 64, y + 66), (x + 74, y + 152), (x + 6, y + 152)]), t[2])
    cv.fill(cv.mask_poly([(x + 22, y + 44), (x + 54, y + 44), (x + 48, y + 120), (x + 38, y + 132), (x + 28, y + 120)]),
            t[3])
    for k in range(4):  # braids
        bx = x + 28 + k * 6
        for yy in range(y + 50, y + 118, 4):
            cv.px(bx, yy, t[4])
            cv.px(bx + 1, yy + 2, t[1])
    helm = cv.mask_ellipse(x + 38, y + 30, 18, 14) & (np.arange(cv.h)[:, None] <= y + 30)
    cv.fill(helm, t[4])
    prect(cv, None, x + 20, y + 30, 37, 4, GOLD[2])
    prect(cv, None, x + 26, y + 34, 25, 10, t[3])     # face
    prect(cv, None, x + 30, y + 38, 5, 1, t[0])
    prect(cv, None, x + 41, y + 38, 5, 1, t[0])
    prect(cv, None, x + 66, y + 20, 3, 132, t[2])     # axe haft
    cv.fill(cv.mask_poly([(x + 67, y + 18), (x + 80, y + 10), (x + 82, y + 34), (x + 67, y + 28)]), t[4])
    prect(cv, None, x + 58, y + 74, 12, 7, t[4])      # hands on the haft
    for yy in range(y + 66, y + 152, 2):              # lit edge on the right
        cv.px(x + 64 + (yy - y - 66) // 9, yy, t[5])


def sigil(cv, cx, cy, r, tones):
    """A carved stone seal: a ring channel inside the rim and grooves in the shape of the bitcoin B, with channels in
    from the fall and out to the floor. The lava layer fills them all (sigil_flow)."""
    groove = C("#120a08")
    flow = sigil_flow()
    cv.fill(cv.mask_ellipse(cx, cy, r, r), tones[4])
    cv.fill(cv.mask_ellipse(cx, cy, r - 2, r - 2), groove)            # the ring channel
    cv.fill(cv.mask_ellipse(cx, cy, r - 7, r - 7), tones[3])          # the inner disc
    cv.fill(cv.mask_ellipse(cx, cy, r - 7, r - 7) & ~cv.mask_ellipse(cx, cy, r - 8, r - 8), tones[4])
    for k in range(16):
        a = k * math.pi / 8
        cv.px(cx + (r - 1) * math.cos(a), cy + (r - 1) * math.sin(a), GOLD[2])
    for part in ("inflow", "feeders", "outflow"):                     # each channel in a groove a pixel wider
        for x, y in flow[part]:
            cv.rect(x - 1, y - 1, 3, 3, groove)
    for gx, gy in glyph_cells(cx, cy):
        cv.px(gx, gy, groove)


def _channel(points, half_w, s0=0.0):
    """Pixels within half_w of a polyline, each with s = s0 + the distance along the line to its nearest point."""
    pts = np.array(points, float)
    seg = np.r_[0, np.cumsum(np.hypot(*np.diff(pts, axis=0).T))]
    dense = np.linspace(0, seg[-1], max(int(seg[-1] * 4), 2))
    px_ = np.interp(dense, seg, pts[:, 0])
    py_ = np.interp(dense, seg, pts[:, 1])
    out = {}
    for y in range(int(py_.min() - half_w - 1), int(py_.max() + half_w + 2)):
        for x in range(int(px_.min() - half_w - 1), int(px_.max() + half_w + 2)):
            d = np.hypot(px_ - x, py_ - y)
            i = int(d.argmin())
            if d[i] <= half_w:
                out[(x, y)] = s0 + dense[i]
    return out


def sigil_flow() -> dict[str, dict]:
    """Where the lava runs through the seal, as {part: {(x, y): s}} with s the distance along the flow in pixels: in
    from the last fall to the ring; both ways round the ring to its foot; down two feeders into the top of the B,
    through it and out its bottom back to the ring; and out of the ring's foot to the floor canal."""
    cx, cy, r = L.SIGIL["cx"], L.SIGIL["cy"], L.SIGIL["r"]
    rr = r - 4.5                                                      # the ring channel's middle radius
    th_in, th_out = math.radians(-50), math.radians(90)
    fx, _, fy1, fw = L.FALLS[-1]
    inlet = (cx + rr * math.cos(th_in), cy + rr * math.sin(th_in))
    path = _bezier((fx + fw / 2 - 0.5, fy1 - 2), (fx + fw / 2, fy1 + 10), inlet, 24)
    inflow = _channel(path, 1.2)
    lead = max(inflow.values())
    inflow = {k: v - lead for k, v in inflow.items()}                 # s is 0 where the lava meets the ring

    def ring_s(x, y):                                                 # both streams run from the inlet to the foot
        th = math.atan2(y - cy, x - cx)
        cw = (th - th_in) % (2 * math.pi)
        return rr * (cw if cw <= (th_out - th_in) % (2 * math.pi) else (th_in - th) % (2 * math.pi))

    ring = {}
    for y in range(int(cy - r), int(cy + r) + 1):
        for x in range(int(cx - r), int(cx + r) + 1):
            if abs(math.hypot(x - cx, y - cy) - rr) <= 1.5:
                ring[(x, y)] = ring_s(x, y)
    top_y, bot_y = int(cy - rr + 1), int(cy + rr - 1)
    feeders, glyph = {}, {}
    for x in (cx - 7, cx - 6, cx - 3, cx - 2):                        # the B's top and bottom ticks
        s_top = ring_s(x, top_y)
        for y in range(top_y, cy - 14):
            feeders[(x, y)] = s_top + (y - top_y)
        for y in range(cy + 14, bot_y + 1):
            feeders[(x, y)] = s_top + (y - top_y)
    s_glyph = ring_s(cx - 5, top_y) - top_y
    for x, y in glyph_cells(cx, cy):
        glyph[(x, y)] = s_glyph + y
    foot = ring_s(cx, cy + rr)
    outflow = {(x, y): foot + (y - cy - rr) for x in (cx - 1, cx, cx + 1)
               for y in range(int(cy + rr), L.WALKWAYS[-1][2] + 2)}
    return {"inflow": inflow, "ring": ring, "feeders": feeders, "glyph": glyph, "outflow": outflow}


def glyph_cells(cx, cy):
    return [(cx - 11 + gx * 2 + dx, cy - 14 + gy * 2 + dy) for gy, row in enumerate(BTC_GLYPH)
            for gx, ch in enumerate(row) if ch == "#" for dx in (0, 1) for dy in (0, 1)]


def box_blur(a: np.ndarray, r: int) -> np.ndarray:
    k = 2 * r + 1
    for axis in (0, 1):
        pad = [(0, 0), (0, 0)]
        pad[axis] = (r + 1, r)
        c = np.cumsum(np.pad(a, pad), axis=axis)
        n = c.shape[axis]
        a = (np.take(c, np.arange(k, n), axis=axis) - np.take(c, np.arange(0, n - k), axis=axis)) / k
    return a


def light_sources():
    src = []
    for x0, x1, y in L.WALKWAYS:
        src += [(x, y + 2, 9, 0.22) for x in range(x0, x1, 10)]
    for x, y0, y1, w in L.FALLS:
        src += [(x, y, 13, 0.3) for y in range(y0, y1, 9)]
    src += [(x, y - 6, 26, 0.9) for x, y in L.BRAZIERS]
    src += [(L.FORGE["x"] + 15, L.FORGE["y"] + 28, 30, 1.0), (L.SIGIL["cx"], L.SIGIL["cy"], 34, 0.5)]
    src += [(cx, b - ry, 36, 0.3) for cx, b, rx, ry in L.HOARD]
    return src


LIGHT_REACH = 8  # a light fades out smoothly by this many radii (a hard square cutoff left visible seams)


def apply_light(cv: Cv, sources):
    yy, xx = np.mgrid[0:cv.h, 0:cv.w]
    lum = np.zeros((cv.h, cv.w))
    for x, y, r, k in sources:
        reach = r * LIGHT_REACH
        x0, x1 = max(0, int(x - reach)), min(cv.w, int(x + reach) + 1)
        y0, y1 = max(0, int(y - reach)), min(cv.h, int(y + reach) + 1)
        d2 = (xx[y0:y1, x0:x1] - x) ** 2 + (yy[y0:y1, x0:x1] - y) ** 2
        lum[y0:y1, x0:x1] += k / (1 + d2 / r ** 2) * np.clip(1 - d2 / reach ** 2, 0, 1) ** 2
    bay = np.tile(BAYER, (cv.h // 4 + 1, cv.w // 4 + 1))[:cv.h, :cv.w]
    level = np.clip(np.floor(np.clip(lum, 0, 1.1) * 4 + bay) / 4, 0, 1.25)  # posterized, ordered dither
    rgb = cv.a[:, :, :3].astype(float)
    rgb = rgb * (1 + 0.55 * level[..., None]) + level[..., None] * np.array([78, 30, 4])
    cv.a[:, :, :3] = np.clip(rgb, 0, 255).astype(np.uint8)


# ------------------------------------------------------------------ v2: a vast cavern, not a dungeon

def _noise(rng, n_terms=4, base=0.012):
    terms = [(rng.uniform(0.5, 1.0) / (k + 1), base * (k + 1) * rng.uniform(0.8, 1.3), rng.uniform(0, 6.28))
             for k in range(n_terms)]
    return lambda t: sum(a * math.sin(t * f + p) for a, f, p in terms)


def deep_space(cv: Cv, rng):
    """The open heart of the mountain: a dark gradient, distant colonnades and arches, far lava glows, mist."""
    bay = np.tile(BAYER, (cv.h // 4 + 1, cv.w // 4 + 1))[:cv.h, :cv.w]
    top, bot = np.array([7, 8, 13]), np.array([12, 14, 22])
    t = np.linspace(0, 1, cv.h)[:, None, None]
    cv.a[:, :, :3] = (top * (1 - t) + bot * t).astype(np.uint8)
    cv.a[:, :, 3] = 255
    far_col, far_edge, far_cap = C("#10131c"), C("#181d2a"), C("#151a26")
    for depth, (x_step, w, shade) in enumerate([(58, 9, 0.75), (84, 14, 1.0)]):  # two depths of distant columns
        x = rng.randint(70, 70 + x_step)
        while x < 420:
            col = tuple(int(v * shade) for v in far_col[:3]) + (255,)
            edge = tuple(int(v * shade) for v in far_edge[:3]) + (255,)
            for y in range(196, 1160):
                fade = min(1.0, (y - 196) / 120, (1160 - y) / 160)  # dissolve into the dark at both ends
                if fade < 1 and BAYER[y % 4, x % 4] > fade:
                    continue
                prect(cv, None, x, y, w, 1, col)
                cv.px(x, y, edge)
            for cap_y in (330, 520, 860):  # capitals where distant galleries cross
                prect(cv, None, x - 2, cap_y, w + 4, 3, far_cap)
            if rng.random() < 0.5:  # a far brazier
                ly = rng.choice([330, 520, 860]) - 4
                cv.px(x + w // 2, ly, C("#7a2a10"))
                cv.px(x + w // 2, ly - 1, C("#b4441a"))
            x += x_step + rng.randint(-8, 8)
    for ay in (520, 860):  # distant arcades
        for cx in range(60, 440, 64):
            for k in range(0, 181, 3):
                a = math.radians(k)
                cv.px(cx + 32 * math.cos(a), ay - 22 * math.sin(a), far_cap)
    for gy in (586, 916, 1146):  # far lava rivers on the cavern floors, seen through the gaps
        for x in range(70, 420):
            if (x * 13 + gy) % 7:
                cv.px(x, gy, C("#4a160b"))
            for d in range(1, 9):
                if BAYER[(gy - d) % 4, x % 4] < 0.5 - d * 0.05:
                    cv.px(x, gy - d, C("#22100c"))
    for my, mh in [(250, 60), (650, 70), (990, 80)]:  # mist bands
        for y in range(my, my + mh):
            k = 1 - abs((y - my) / mh * 2 - 1)
            for x in range(cv.w):
                if bay[y, x] < k * 0.35:
                    r, g, b, a = cv.a[y, x]
                    cv.a[y, x] = (min(255, r + 8), min(255, g + 10), min(255, b + 16), a)


def cave_walls(cv: Cv, rng, y0: int, y1: int):
    """Natural cliff faces down both sides, where the galleries are cut. Irregular edges, lit rims."""
    left, right = _noise(rng), _noise(rng)
    ys = np.arange(cv.h)[:, None]
    xs = np.arange(cv.w)[None, :]
    xl = np.array([86 + 22 * left(y) for y in range(cv.h)])[:, None]
    xr = np.array([396 + 22 * right(y) for y in range(cv.h)])[:, None]
    region = ((xs < xl) | (xs > xr)) & (ys >= y0) & (ys < y1)
    tones = [STONE[0], STONE[1], STONE[2], STONE[3], STONE[4], STONE[5]]
    slabs(cv, 0, y0, cv.w, y1, rng, tones, region=region, h_rng=(4, 10), w_rng=(10, 40))
    for y in range(y0, y1):  # rims facing the cavern: a lit edge and a dark lip
        a, b = int(xl[y, 0]), int(xr[y, 0])
        cv.px(a - 1, y, STONE[5])
        cv.px(a - 2, y, STONE[4])
        cv.px(a, y, STONE[0])
        cv.px(b + 1, y, STONE[5])
        cv.px(b, y, STONE[0])
    for _ in range(26):  # ledges and outcrops sticking out of the walls
        side = rng.random() < 0.5
        y = rng.randint(y0 + 20, y1 - 20)
        edge = int(xl[y, 0]) if side else int(xr[y, 0])
        w = rng.randint(6, 18)
        x = edge - 2 if side else edge - w + 2
        prect(cv, None, x, y, w, 3, STONE[3])
        prect(cv, None, x, y, w, 1, STONE[5])
        prect(cv, None, x, y + 3, w, 1, STONE[0])
    return region


def drips(cv: Cv, rng, y_top: int, y_floor: int):
    """Stalactites under a level's ceiling and stalagmites on its floor, out in the open cavern."""
    for x in range(96, 390, rng.randint(9, 13)):
        d = rng.randint(4, 22)
        cv.fill(cv.mask_poly([(x, y_top), (x + 5, y_top), (x + 2, y_top + d)]), STONE[1])
        cv.px(x + 1, y_top + 1, STONE[3])
        if rng.random() < 0.35:
            g = rng.randint(4, 14)
            cv.fill(cv.mask_poly([(x - 2, y_floor), (x + 4, y_floor), (x + 1, y_floor - g)]), STONE[1])
            cv.px(x, y_floor - 2, STONE[3])


def build_cavern() -> Cv:
    rng = random.Random(1909)
    cv = Cv(W, H, STONE[0])
    deep_space(cv, rng)                                               # the open cavern behind everything
    masonry(cv, 0, 28, W, 192, rng, STONE, bw=22, bh=10)              # the hall's built wall
    for y in L.RUNE_BANDS:
        rune_band(cv, 0, W, y, STONE)
    prect(cv, None, 0, 0, W, 30, STONE[1])                            # ceiling and stalactites
    slabs(cv, 0, 0, W, 30, rng, STONE[:5], h_rng=(4, 7))
    for x in range(0, W, 7):
        d = rng.randint(3, 16)
        cv.fill(cv.mask_poly([(x, 30), (x + 6, 30), (x + 3, 30 + d)]), STONE[2])
        cv.px(x + 1, 31, STONE[4])
    # the throne niche: a great arch behind the dragon, then the stepped dais
    niche = cv.mask_ellipse(392, 104, 90, 66) | cv.mask_poly([(302, 104), (482, 104), (482, 192), (302, 192)])
    cv.fill(niche, STONE[1])
    slabs(cv, 302, 38, W, 192, rng, [STONE[0], STONE[0], STONE[1], STONE[2], STONE[3]], region=niche)
    rim = niche & ~cv.mask_ellipse(392, 104, 87, 63) & ~cv.mask_poly([(305, 104), (482, 104), (482, 192),
                                                                       (305, 192)])
    cv.fill(rim, GOLD[2])
    prect(cv, None, 300, 104, 3, 88, GOLD[2])
    prect(cv, None, 388, 36, 9, 7, GOLD[3])                           # keystone
    for k, (x0, top) in enumerate([(300, 150), (290, 162), (280, 174)]):
        prect(cv, None, x0, top, W - x0, 12 + (6 if k == 2 else 0), STONE[3 + (k % 2)])
        prect(cv, None, x0, top, W - x0, 1, STONE[5])
        prect(cv, None, x0, top + 1, W - x0, 1, GOLD[2])
    engrave(cv, "STRIVE", L.DAIS_LOGO["cx"], L.DAIS_LOGO["y"], STONE)  # under the dragon, on the dais
    for cx, base, rx, ry in L.HOARD:
        hoard(cv, rng, cx, base, rx, ry)
    for cx, cy in L.BRAZIERS:
        brazier(cv, cx, cy, STONE)
    # galleries: cliff faces down both sides with walkways, pillars and doors; open cavern between
    cave_walls(cv, rng, 192, H)
    for y_top, y_floor in [(200, 598), (610, 928), (940, 1158)]:
        drips(cv, rng, y_top, y_floor)
    for x, y, w, h in [(12, 262, 18, 38), (446, 398, 18, 42), (100, 764, 18, 36), (300, 890, 18, 40)]:
        doorway(cv, x, y, w, h, STONE)
    for vx, vy, vw, vh in L.VEINS:
        vein(cv, rng, vx, vy, vw, vh)
    for x, y0, y1, w in L.FALLS:                                      # wet rock behind each fall
        prect(cv, None, x - 2, y0, w + 4, y1 - y0, STONE[0])
    for args in L.COLUMNS:
        column(cv, *args, STONE)
    for x0, x1, y in L.WALKWAYS:
        walkway(cv, x0, x1, y, STONE, rail=y not in (192, 1160))
    banner(cv, 418, 310, 12, 26)
    banner(cv, 30, 450, 12, 26)
    banner(cv, 330, 610, 12, 28)
    chain(cv, 30, 610, 700)
    prect(cv, None, 25, 700, 11, 8, C("#4a3020"))                       # the hoist bucket, full of coins
    for x in range(26, 35):
        cv.px(x, 699, GOLD[4] if x % 3 else BTC)
    chain(cv, 470, 154, 192)
    fx, fy = L.FORGE["x"], L.FORGE["y"]                               # the forge and its chimney
    prect(cv, None, fx, fy, 30, 40, STONE[3])
    prect(cv, None, fx, fy, 30, 1, STONE[5])
    prect(cv, None, fx + 8, fy - 70, 14, 70, STONE[2])
    prect(cv, None, fx + 8, fy - 70, 1, 70, STONE[4])
    cv.fill(cv.mask_ellipse(fx + 15, fy + 22, 9, 9) | cv.mask_poly([(fx + 6, fy + 22), (fx + 24, fy + 22),
                                                                   (fx + 24, fy + 38), (fx + 6, fy + 38)]),
            C("#120a08"))
    ax, ay = L.ANVIL["x"], L.ANVIL["y"]
    prect(cv, None, ax - 4, ay, 14, 3, C("#5d6772"))
    prect(cv, None, ax - 4, ay, 14, 1, C("#9aa4ae"))
    prect(cv, None, ax - 7, ay + 1, 3, 1, C("#5d6772"))
    prect(cv, None, ax, ay + 3, 6, 5, C("#3a414b"))
    statue(cv, L.STATUE["x"], L.STATUE["y"], STONE)
    sigil(cv, L.SIGIL["cx"], L.SIGIL["cy"], L.SIGIL["r"], STONE)
    apply_light(cv, light_sources())
    return cv


def build_lava(n: int = 4) -> list[Cv]:
    """The moving light: canals, falls, braziers, the forge mouth and the sigil's grooves, with dithered glow."""
    frames = []
    flow = sigil_flow()
    sx, sy, rr = L.SIGIL["cx"], L.SIGIL["cy"], L.SIGIL["r"] - 4.5
    bay = np.tile(BAYER, (H // 4 + 1, W // 4 + 1))[:H, :W]
    for f in range(n):
        cv = Cv(W, H)
        hot = np.zeros((H, W))
        for x0, x1, y in L.WALKWAYS:                                  # canals flow toward the middle of each walkway
            mid = (x0 + x1) / 2
            for x in range(x0, x1):
                phase = int((x if x < mid else -x) + f * 3) % 11
                c = LAVA[6] if phase in (0, 1) else LAVA[5] if phase in (2, 6) else LAVA[4]
                if (x * 7 + f * 5) % 23 == 0:
                    c = LAVA[2]
                cv.px(x, y + 1, c)
                cv.px(x, y + 2, LAVA[4] if phase % 3 else LAVA[3])
                cv.px(x, y + 3, LAVA[3])
            hot[y + 1:y + 4, x0:x1] = 1
        for x, y0, y1, w in L.FALLS:                                  # falls run downward
            for y in range(y0, y1):
                for dx in range(w):
                    phase = (y - f * 4 + dx * 3) % 9
                    c = LAVA[7] if phase == 0 else LAVA[6] if phase in (1, 5) else LAVA[5] if phase in (2, 6) \
                        else LAVA[4]
                    cv.px(x + dx, y, c)
            hot[y0:y1, x:x + w] = 1
            for k in range(6):                                        # splash
                cv.px(x - 3 + (k * 5 + f * 3) % (w + 6), y1 - 1 - (k + f) % 3, LAVA[6])
        for i, (cx, cy) in enumerate(L.BRAZIERS):
            rnd = random.Random(f * 10 + i)
            for c, hgt, wid in [(LAVA[4], 14, 6), (LAVA[5], 10, 4), (LAVA[7], 5, 2)]:
                pts = [(cx - wid, cy), (cx - wid // 2 + rnd.randint(-1, 1), cy - hgt // 2),
                       (cx + rnd.randint(-2, 2), cy - hgt - rnd.randint(0, 3)),
                       (cx + wid // 2 + rnd.randint(-1, 1), cy - hgt // 2), (cx + wid, cy)]
                m = cv.mask_poly(pts)
                cv.fill(m, c)
                hot[m] = 1
        fx, fy = L.FORGE["x"], L.FORGE["y"]                           # the forge mouth flickers
        mouth = cv.mask_ellipse(fx + 15, fy + 23, 7, 7) | cv.mask_poly([(fx + 8, fy + 23), (fx + 22, fy + 23),
                                                                       (fx + 22, fy + 37), (fx + 8, fy + 37)])
        ys, xs = np.nonzero(mouth)
        for y, x in zip(ys, xs):
            v = (y * 3 + x + f * 5) % 7
            cv.a[y, x] = LAVA[6] if v < 2 else LAVA[5] if v < 4 else LAVA[4]
        hot[mouth] = 1
        # the sigil: bright bands travel with the flow (2px a frame on an 8px beat, so the loop is seamless)
        hot_bands = [LAVA[6], LAVA[6], LAVA[5], LAVA[4], LAVA[4], LAVA[4], LAVA[4], LAVA[5]]
        edge_bands = [LAVA[5], LAVA[5], LAVA[4], LAVA[3], LAVA[3], LAVA[3], LAVA[3], LAVA[4]]
        glyph_bands = [LAVA[6], LAVA[5], LAVA[4], LAVA[3], LAVA[3], LAVA[3], LAVA[3], LAVA[4]]
        for part, heat in (("inflow", 1.0), ("ring", 1.0), ("feeders", 0.7), ("outflow", 1.0), ("glyph", 0.5)):
            for (x, y), dist in flow[part].items():
                phase = int(dist - f * 2) % 8
                if part == "glyph":
                    c = glyph_bands[phase]
                elif (part == "ring" and abs(math.hypot(x - sx, y - sy) - rr) > 0.8) or (part == "outflow"
                                                                                    and x != sx):
                    c = edge_bands[phase]                             # channel edges run a shade cooler
                else:
                    c = hot_bands[phase]
                cv.px(x, y, c)
                if 0 <= y < H and 0 <= x < W:
                    hot[y, x] = heat
        glow = np.clip(box_blur(hot, 4) * 2.4 + box_blur(hot, 10) * 1.2, 0, 1) * (1 + 0.07 * math.sin(f * 1.6))
        level = np.floor(glow * 3 + bay) / 3                          # three dithered glow bands
        g = (level > 0) & (cv.a[:, :, 3] == 0)
        cv.a[g, 0], cv.a[g, 1], cv.a[g, 2] = 255, 106, 19
        cv.a[g, 3] = np.clip(level[g] * 58, 0, 70).astype(np.uint8)
        frames.append(cv)
    return frames


def place(canvas: Cv, sprite_sheet: Image.Image, frames: int, x: int, y: int, flip: bool = False, frame: int = 0):
    w = sprite_sheet.width // frames
    im = sprite_sheet.crop((frame * w, 0, (frame + 1) * w, sprite_sheet.height))
    if flip:
        im = im.transpose(Image.FLIP_LEFT_RIGHT)
    s = Cv(im.width, im.height)
    s.a = np.array(im.convert("RGBA"))
    canvas.paste(s, x, y)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    cav = build_cavern()
    cav.image().save(OUT / "cavern.png")
    lava = build_lava()
    sheet(lava).save(OUT / "lava.png")
    sprites = build_sprites()
    for name, im in sprites.items():
        im.save(OUT / f"{name}.png")
    base = cav.image()                                                # a still preview, every sprite at its spot
    base.alpha_composite(lava[0].image())
    prev = Cv(W, H)
    prev.a = np.array(base)
    d = L.DRAGON
    place(prev, sprites["dragon"], 4, d["x"], d["y"])
    for m in L.MINERS:
        place(prev, sprites[m["sheet"]], 4, m["x"], m["y"], m["flip"], 2)
    for wk in L.WALKERS:
        place(prev, sprites[wk["sheet"]], 4, (wk["x0"] + wk["x1"]) // 2, wk["y"])
    for c in L.CARTS:
        place(prev, sprites[c["sheet"]], 4, c["x0"], c["y"])
    place(prev, sprites["smith"], 4, L.SMITH["x"], L.SMITH["y"], False, 2)
    (ROOT / "renderings").mkdir(exist_ok=True)
    big = prev.image().resize((W * 2, H * 2), Image.NEAREST)
    big.save(ROOT / "renderings" / "mine-preview.png")
    big.crop((0, 0, W * 2, 700)).resize((W * 3, 1050), Image.NEAREST).save(ROOT / "renderings" / "mine-top.png")
    print("wrote", sorted(p.name for p in OUT.iterdir()))


if __name__ == "__main__":
    main()
