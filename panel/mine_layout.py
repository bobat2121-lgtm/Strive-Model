"""Where everything sits in the Mine scene, in art pixels on the 480 x 1200 cavern (shown about 3x). Shared by the art
builder (tools/mine_art.py) and the page (panel/theme.py), so sprites land on the walkways the art draws.

The page's content column covers roughly x 80-400, and the hero covers x 80-266 for y 27-137; the scene is composed
so the life of it (dragon, dwarves, lava falls, the sigil) sits in what stays visible: both margins, the dragon's
throne beside the hero, and the gaps between sections.
"""
SCENE_W, SCENE_H = 480, 1200

RUNE_BANDS, RUNE_H = (44, 176), 7   # the carved bands across the throne hall wall; the price target sits between them
# walkways: (x0, x1, y_top); every walkway carries a lava canal in a groove along its top
WALKWAYS = [
    (0, 480, 192),                      # the throne hall floor
    (0, 112, 300), (356, 480, 300),     # first gallery
    (0, 150, 440), (330, 480, 440),     # second gallery
    (0, 480, 600),                      # the great bridge
    (0, 132, 800), (378, 480, 752),     # the forge level
    (0, 480, 930),                      # the deep bridge
    (0, 480, 1160),                     # the floor of the deep
]
# lava falls: (x, y_top, y_bottom, width)
FALLS = [(52, 66, 190, 4), (74, 302, 438, 3), (404, 442, 598, 3), (70, 602, 798, 3), (404, 754, 928, 3),
         (468, 932, 1028, 4)]
COLUMNS = [(6, 40, 300, 22), (452, 140, 300, 22), (58, 300, 600, 14), (408, 300, 600, 14), (8, 600, 930, 18),
           (440, 600, 752, 16), (90, 930, 1160, 16), (382, 930, 1160, 14)]
DRAGON = {"x": 330, "y": 34, "w": 128, "h": 100}
# inside the dragon sprite (its own 128 x 100 pixels, facing left)
RIDER = (55, 21)                              # top-left of the rider (Matt Cole); his hips on the dragon's back
MOUTH = (11, 35)                              # the root of the fire, inside the open jaws
FIRE = {"w": 76, "h": 30}                     # the flame sprite; its root is the middle of its right edge
ZAP = {"x": 36, "y": 4, "w": 56, "h": 50}     # the box his electricity crackles in
DAIS_LOGO = {"cx": 394, "y": 180}           # the STRIVE wordmark carved into the dais's lowest step, under the dragon
BRAZIERS = [(312, 112), (470, 112)]          # bowl centers
HOARD = [(352, 132, 30, 10), (396, 136, 34, 9), (440, 132, 30, 11), (470, 138, 18, 7), (322, 138, 18, 6)]
SIGIL = {"cx": 440, "cy": 1062, "r": 34}
STATUE = {"x": 6, "y": 964}
FORGE = {"x": 446, "y": 712}
ANVIL = {"x": 426, "y": 744}
VEINS = [(30, 262, 26, 18), (420, 404, 26, 18), (6, 768, 30, 16)]   # (x, y, w, h) gold in the rock

# sprites: miners face the vein; walkers pace a walkway; times in seconds
MINERS = [
    {"sheet": "miner_a", "x": 12, "y": 284, "flip": False, "dur": 1.0, "delay": 0.0},
    {"sheet": "miner_b", "x": 446, "y": 424, "flip": True, "dur": 1.1, "delay": 0.4},
    {"sheet": "miner_c", "x": 30, "y": 784, "flip": True, "dur": 0.9, "delay": 0.2},
]
WALKERS = [
    {"sheet": "walker_a", "y": 284, "x0": 362, "x1": 462, "dur": 22, "delay": -4},
    {"sheet": "walker_b", "y": 424, "x0": 4, "x1": 120, "dur": 26, "delay": -13},
    {"sheet": "walker_c", "y": 914, "x0": 404, "x1": 466, "dur": 18, "delay": -7},
]
CARTS = [{"sheet": "cart", "y": 584, "x0": 2, "x1": 60, "dur": 20, "delay": -6}]
SMITH = {"sheet": "smith", "x": 406, "y": 736, "dur": 1.2}
SPARKLES = [(40, 270, 0.0), (52, 282, 2.3), (428, 412, 1.1), (440, 426, 3.4), (16, 776, 0.7), (360, 124, 1.9),
            (410, 128, 3.1), (452, 126, 0.4), (430, 1056, 2.6)]
