"""Pixel-art sprites drawn as text grids. One character = one pixel.

'.' is transparent. Each sprite has its own palette, so recolouring
(golden banana, empty heart) is just a palette swap.
"""
from __future__ import annotations

import pygame

MONKEY_PAL = {
    "k": (46, 24, 12), "b": (150, 92, 44), "B": (112, 66, 30), "f": (240, 200, 150),
    "F": (210, 165, 118), "w": (255, 255, 255), "e": (22, 16, 16), "m": (170, 60, 50),
}
_HEAD = [
    "....kkkkkkkk....",
    "...kbbbbbbbbk...",
    ".kkbbbbbbbbbbkk.",
    "kfkbbffffffbbkfk",
    "kfkbfwwffwwfbkfk",
    ".kkfwweffewwfkk.",
    "...kffffffffk...",
]
_HEAD_BLINK = _HEAD[:4] + [
    "kfkbffffffffbkfk",
    ".kkfkkkffkkkfkk.",
    "...kffffffffk...",
]
_BODY = [
    "...kfffmmfffk...",
    "....kFffffFk....",
    "...kkbbbbbbkk...",
    "..kbbbffffbbbk..",
    ".kbkbffffffbkbk.",
    ".kbkbFffffFbkbk.",
    "..k.kbbbbbbk.k..",
]
_LEGS = {
    "idle": ["....kbbkkbbk....", "....kkk..kkk...."],
    "runA": ["....kbbkkbbk....", "...kkk....kk...."],
    "runB": ["....kbbkkbbk....", "....kk....kkk..."],
}
_JUMP = _HEAD[:6] + [
    "kk.kffffffffk.kk",
    "kbk.kffmmffk.kbk",
    ".kbkkFffffFkkbk.",
    "..kbbbffffbbbk..",
    "...kbffffffbk...",
    "...kbFffffFbk...",
    "...kbbbbbbbbk...",
    "..kbbk....kbbk..",
    "..kkk......kkk..",
]
MONKEY = {
    "idle": _HEAD + _BODY + _LEGS["idle"],
    "blink": _HEAD_BLINK + _BODY + _LEGS["idle"],
    "runA": _HEAD + _BODY + _LEGS["runA"],
    "runB": _HEAD + _BODY + _LEGS["runB"],
    "jump": _JUMP,
}

BANANA_PAL = {"k": (96, 62, 8), "y": (255, 222, 64), "Y": (226, 166, 28), "h": (255, 250, 190), "g": (96, 120, 30)}
GOLD_PAL = {"k": (120, 60, 0), "y": (255, 186, 40), "Y": (226, 120, 10), "h": (255, 255, 255), "g": (180, 120, 20)}
BANANA = [
    "..........gk",
    ".........kyk",
    "........kyYk",
    "k......kyyYk",
    "kk....kyyyYk",
    "khk..kyyyYk.",
    ".khyyyyyyYk.",
    "..kkhyyyYk..",
    "....kkkkk...",
]

COCONUT_PAL = {"k": (40, 22, 10), "c": (126, 76, 36), "C": (90, 52, 24), "h": (176, 120, 64), "d": (34, 18, 8)}
COCONUT = [
    "...kkkk...",
    ".kkhhcckk.",
    ".khhcccCk.",
    "khccdccCCk",
    "kcccccdcCk",
    "kcdcccccCk",
    "kccccCcCCk",
    ".kcccCCCk.",
    ".kkCCCCkk.",
    "...kkkk...",
]
ROCK_PAL = {"k": (30, 22, 24), "c": (104, 92, 88), "C": (70, 60, 60), "h": (150, 136, 126), "d": (255, 120, 30)}

HEART_PAL = {"k": (70, 8, 18), "r": (232, 44, 66), "h": (255, 170, 180)}
HEART_EMPTY_PAL = {"k": (40, 20, 30), "r": (84, 54, 66), "h": (110, 80, 92)}
HEART = [
    ".kk.kk.",
    "khrkrrk",
    "krrrrrk",
    ".krrrk.",
    "..krk..",
    "...k...",
]
STAR_PAL = {"k": (110, 64, 0), "y": (255, 214, 60), "h": (255, 250, 200)}
STAR_EMPTY_PAL = {"k": (50, 40, 60), "y": (90, 80, 104), "h": (120, 110, 130)}
STAR = [
    "...k...",
    "..khk..",
    "kkkyykk",
    "kyyyyyk",
    ".kyyyk.",
    ".kykyk.",
    "kk...kk",
]

BIRD_PAL = {"k": (40, 20, 44), "b": (110, 70, 170), "w": (255, 255, 255), "e": (20, 10, 20), "o": (255, 160, 40)}
BIRD = {
    "up": [
        "..kk........",
        ".kbbk.......",
        "..kbbk......",
        "kkkkbbkkkk..",
        "kbbbbbbbwek.",
        ".kbbbbbbbbok",
        "..kkkkkkkk..",
        "............",
        "............",
    ],
    "down": [
        "............",
        "............",
        "............",
        "kkkkkkkkkk..",
        "kbbbbbbbwek.",
        ".kbbbbbbbbok",
        "..kbbkkkkk..",
        "...kbbk.....",
        "....kk......",
    ],
}
ICON_PAL = {"r": (230, 50, 60), "w": (240, 240, 250), "k": (40, 30, 50), "b": (70, 150, 255), "h": (200, 230, 255)}
ICONS = {
    "magnet": ["ww...ww", "rr...rr", "rr...rr", "rr...rr", "rrr.rrr", ".rrrrr.", "..rrr.."],
    "slow": ["..kkk..", ".kwwwk.", "kwwkwwk", "kwwkkwk", "kwwwwwk", ".kwwwk.", "..kkk.."],
    "shield": ["bbbbbbb", "bhhbbbb", "bhbbbbb", "bbbbbbb", ".bbbbb.", "..bbb..", "...b..."],
}
POWER_COLORS = {"magnet": (220, 90, 230), "slow": (80, 220, 230), "shield": (90, 150, 255), "heart": (255, 90, 110)}


def bubble(kind: str, icon: pygame.Surface) -> pygame.Surface:
    """Power-up: a see-through bubble with the icon inside."""
    c = POWER_COLORS[kind]
    surf = pygame.Surface((15, 15), pygame.SRCALPHA)
    pygame.draw.circle(surf, (*c, 110), (7, 7), 7)
    pygame.draw.circle(surf, (255, 255, 255, 230), (7, 7), 7, 1)
    surf.set_at((4, 3), (255, 255, 255, 255))
    surf.set_at((3, 4), (255, 255, 255, 255))
    surf.blit(icon, (7 - icon.get_width() // 2, 7 - icon.get_height() // 2 + 1))
    return surf


def make(grid: list[str], palette: dict) -> pygame.Surface:
    w = len(grid[0])
    assert all(len(r) == w for r in grid), f"ragged sprite: {[len(r) for r in grid]}"
    surf = pygame.Surface((w, len(grid)), pygame.SRCALPHA)
    for y, row in enumerate(grid):
        for x, ch in enumerate(row):
            if ch != ".":
                surf.set_at((x, y), palette[ch])
    return surf


def flash(surf: pygame.Surface, color=(255, 255, 255)) -> pygame.Surface:
    """Same shape, one solid colour (used for the hit flash)."""
    out = surf.copy()
    out.fill((*color, 0), special_flags=pygame.BLEND_RGBA_MAX)
    out.fill((*color, 255), special_flags=pygame.BLEND_RGB_MAX)
    return out


def load() -> dict[str, pygame.Surface | list]:
    s: dict = {f"monkey_{k}": make(g, MONKEY_PAL) for k, g in MONKEY.items()}
    s["monkey_hit"] = flash(s["monkey_idle"], (255, 90, 90))
    s["banana"] = make(BANANA, BANANA_PAL)
    s["golden"] = make(BANANA, GOLD_PAL)
    coco = make(COCONUT, COCONUT_PAL)
    s["coconut"] = [pygame.transform.rotate(coco, -90 * i) for i in range(4)]
    rock = make(COCONUT, ROCK_PAL)
    s["rock"] = [pygame.transform.rotate(rock, -90 * i) for i in range(4)]
    s["heart"] = make(HEART, HEART_PAL)
    s["heart_empty"] = make(HEART, HEART_EMPTY_PAL)
    s["star"] = make(STAR, STAR_PAL)
    s["star_empty"] = make(STAR, STAR_EMPTY_PAL)
    s["bird"] = [make(BIRD["up"], BIRD_PAL), make(BIRD["down"], BIRD_PAL)]
    icons = {k: make(g, ICON_PAL) for k, g in ICONS.items()}
    icons["heart"] = s["heart"]
    s["icon"] = icons
    s["power"] = {k: bubble(k, icon) for k, icon in icons.items()}
    return s
