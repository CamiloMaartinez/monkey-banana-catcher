"""Procedural pixel-art backgrounds: dithered sky, parallax layers, ground, ambient life.

Everything is generated once per level from the Theme (no image files),
then only the clouds and small particles move.
"""
from __future__ import annotations

import math
import random

import numpy as np
import pygame

from . import GROUND_Y, WORLD_H, WORLD_W
from .levels import Theme

PAD = 24                      # extra width on each side for parallax
LAYER_W = WORLD_W + 2 * PAD
BAYER = np.array([[0, 2], [3, 1]]) / 4 + 1 / 8   # 2x2 ordered dither


def mix(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def lighter(c, k=40):
    return tuple(min(255, v + k) for v in c)


def darker(c, k=30):
    return tuple(max(0, v - k) for v in c)


def dither_gradient(w: int, h: int, stops) -> pygame.Surface:
    """Vertical gradient using only the stop colours plus a 2x2 dither (retro banding)."""
    stops = np.array(stops, dtype=np.float32)
    n = len(stops)
    arr = np.zeros((w, h, 3), dtype=np.uint8)
    xs = np.arange(w)
    for y in range(h):
        pos = y / max(h - 1, 1) * (n - 1)
        base = min(int(pos), n - 2)
        frac = pos - base
        # 4 dither steps between two stops: mix pairs of the two colours
        a, b = stops[base], stops[base + 1]
        mid = (a + b) / 2
        if frac < 0.5:
            lo, hi, f = a, mid, frac * 2
        else:
            lo, hi, f = mid, b, frac * 2 - 1
        pick = f > BAYER[y % 2, xs % 2]
        arr[:, y] = np.where(pick[:, None], hi, lo)
    surf = pygame.Surface((w, h))
    pygame.surfarray.blit_array(surf, arr)
    return surf


def dither_disc(surf, color, cx, cy, r, ring=5):
    """Disc with a checkerboard halo (sun / moon glow)."""
    for y in range(cy - r - ring, cy + r + ring + 1):
        for x in range(cx - r - ring, cx + r + ring + 1):
            if not (0 <= x < surf.get_width() and 0 <= y < surf.get_height()):
                continue
            d = math.hypot(x - cx, y - cy)
            if r < d <= r + ring and (x + y) % 2 == 0 and d < r + ring * (0.5 + 0.5 * ((x * 7 + y * 3) % 2)):
                surf.set_at((x, y), mix(surf.get_at((x, y))[:3], color, 0.45))
    pygame.draw.circle(surf, color, (cx, cy), r)


def make_cloud(rng, light, shade) -> pygame.Surface:
    w, h = rng.randint(28, 46), 16
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    puffs = [(rng.randint(6, w - 6), rng.randint(6, 9), rng.randint(4, 7)) for _ in range(5)]
    for x, y, r in puffs:
        pygame.draw.circle(surf, shade, (x, y + 2), r)
    for x, y, r in puffs:
        pygame.draw.circle(surf, light, (x, y), r - 1)
    pygame.draw.rect(surf, shade, (4, h - 5, w - 8, 3))
    return surf


class Scenery:
    def __init__(self, theme: Theme, seed: int = 1):
        self.t = theme
        self.rng = random.Random(seed)
        self.time = 0.0
        self.sky = self._build_sky()
        self.far = self._build_far()
        self.near = self._build_near()
        self.ground = self._build_ground()
        self.clouds = []
        if theme.clouds:
            for i in range(4):
                c = make_cloud(self.rng, *theme.clouds)
                self.clouds.append([self.rng.uniform(0, WORLD_W), self.rng.randint(14, 70),
                                    self.rng.uniform(3, 8), c])
        self.ambient = []
        self.stars = [(self.rng.randrange(WORLD_W), self.rng.randrange(110), self.rng.random() * 6)
                      for _ in range(60)] if theme.kind == "night" else []

    # --- building (once) --------------------------------------------------
    def _build_sky(self):
        t = self.t
        sky = dither_gradient(WORLD_W, WORLD_H, t.sky)
        if t.sun:
            color, x, y, r = t.sun
            dither_disc(sky, color, x, y, r)
            if t.kind == "night":   # moon craters
                for dx, dy, cr in ((-3, -2, 2), (3, 3, 2), (2, -4, 1)):
                    pygame.draw.circle(sky, darker(color, 30), (x + dx, y + dy), cr)
            if t.kind == "canyon":  # sun stripes like a synthwave sunset
                for i, yy in enumerate(range(y + 4, y + r, 4)):
                    pygame.draw.line(sky, t.sky[2], (x - r, yy), (x + r, yy), 1 + i // 2)
        return sky

    def _hills(self, base, amps, color, rng, top=None):
        surf = pygame.Surface((LAYER_W, WORLD_H), pygame.SRCALPHA)
        phases = [rng.uniform(0, 6.28) for _ in amps]
        for x in range(LAYER_W):
            h = base + sum(a * math.sin(x * f + p) for (a, f), p in zip(amps, phases))
            h = int(h)
            pygame.draw.line(surf, color, (x, h), (x, WORLD_H))
            if top:
                surf.set_at((x, h), top)
        return surf

    def _build_far(self):
        t, rng = self.t, self.rng
        if t.kind == "beach":
            surf = pygame.Surface((LAYER_W, WORLD_H), pygame.SRCALPHA)
            for x in range(20, 110):                      # distant island
                h = 132 - int(18 * math.sin(math.pi * (x - 20) / 90) ** 0.7 + 2 * math.sin(x * 0.4))
                pygame.draw.line(surf, darker(t.near[0], 10), (x, h), (x, 132))
                surf.set_at((x, h), lighter(t.near[0], 10))
            pygame.draw.rect(surf, t.far, (0, 132, LAYER_W, WORLD_H))
            for y in range(134, GROUND_Y, 5):           # sea sparkle lines
                for x in range(rng.randrange(8), LAYER_W, rng.randint(14, 26)):
                    pygame.draw.line(surf, lighter(t.far, 50), (x, y), (x + rng.randint(2, 6), y))
            pygame.draw.line(surf, lighter(t.far, 80), (0, 132), (LAYER_W, 132))
            return surf
        if t.kind == "canyon":
            surf = pygame.Surface((LAYER_W, WORLD_H), pygame.SRCALPHA)
            x = 0
            while x < LAYER_W:
                w, top = rng.randint(26, 54), rng.randint(96, 128)
                pygame.draw.rect(surf, t.far, (x, top, w, WORLD_H))
                pygame.draw.rect(surf, lighter(t.far, 26), (x, top, w, 2))
                for yy in range(top + 8, WORLD_H, 9):   # rock strata
                    pygame.draw.line(surf, darker(t.far, 14), (x, yy), (x + w - 1, yy))
                x += w + rng.randint(-6, 14)
            return surf
        if t.kind == "volcano":
            surf = pygame.Surface((LAYER_W, WORLD_H), pygame.SRCALPHA)
            cx = LAYER_W // 2 + 30
            for x in range(LAYER_W):
                h = 54 + abs(x - cx) * 0.9 + 3 * math.sin(x * 0.3)
                if abs(x - cx) < 9:
                    h = 60 + (9 - abs(x - cx)) * 0.5   # crater
                pygame.draw.line(surf, t.far, (x, int(h)), (x, WORLD_H))
            lava = (255, 120, 30)
            pygame.draw.line(surf, (255, 200, 60), (cx - 8, 60), (cx + 8, 60), 2)
            for dx, length in ((-4, 40), (3, 62), (7, 30)):  # lava streams
                x, y = cx + dx, 61
                for i in range(length):
                    surf.set_at((x, y + i), lava if i % 7 else (255, 200, 60))
                    if i % 6 == 5:
                        x += 1 if dx > 0 else -1
            return surf
        top = lighter(t.far, 18)
        return self._hills(118, [(9, 0.03), (5, 0.08), (2, 0.21)], t.far, rng, top)

    def _build_near(self):
        t, rng = self.t, self.rng
        surf = pygame.Surface((LAYER_W, WORLD_H), pygame.SRCALPHA)
        main, dark = t.near
        if t.kind in ("jungle", "night"):
            for _ in range(14):     # tree canopies
                cx, cy, r = rng.randrange(LAYER_W), rng.randint(128, 150), rng.randint(9, 16)
                pygame.draw.rect(surf, darker(dark, 6), (cx - 2, cy, 4, GROUND_Y - cy))
                pygame.draw.circle(surf, dark, (cx, cy + 2), r)
                pygame.draw.circle(surf, main, (cx - 1, cy), r - 2)
                for _ in range(6):  # light leaf pixels
                    a, d = rng.uniform(3.4, 5.2), rng.uniform(0, r - 3)
                    surf.set_at((int(cx - 1 + math.cos(a) * d), int(cy + math.sin(a) * d)), lighter(main, 28))
            for _ in range(5):      # hanging vines
                x, y0 = rng.randrange(LAYER_W), rng.randint(130, 140)
                for y in range(y0, y0 + rng.randint(10, 22)):
                    surf.set_at((x + int(math.sin(y * 0.4)), y), darker(main, 10))
            for x in range(0, LAYER_W, 9):   # bushes along the ground
                r = rng.randint(5, 9)
                pygame.draw.circle(surf, dark, (x, GROUND_Y + 1), r)
                pygame.draw.circle(surf, main, (x - 1, GROUND_Y), r - 2)
        elif t.kind == "beach":
            for bx in (30, LAYER_W - 46, LAYER_W // 2 + 40):
                self._palm(surf, bx, rng)
        elif t.kind == "canyon":
            for _ in range(5):
                self._cactus(surf, rng.randrange(10, LAYER_W - 10), rng, main, dark)
            for _ in range(8):
                x, r = rng.randrange(LAYER_W), rng.randint(3, 7)
                pygame.draw.circle(surf, dark, (x, GROUND_Y), r)
                pygame.draw.circle(surf, main, (x - 1, GROUND_Y - 1), r - 1)
        elif t.kind == "volcano":
            for _ in range(9):     # sharp rocks
                x, h, w = rng.randrange(LAYER_W), rng.randint(14, 34), rng.randint(8, 18)
                pygame.draw.polygon(surf, dark, [(x - w, GROUND_Y), (x, GROUND_Y - h), (x + w, GROUND_Y)])
                pygame.draw.polygon(surf, main, [(x - w + 3, GROUND_Y), (x - 1, GROUND_Y - h + 4), (x, GROUND_Y)])
        return surf

    def _palm(self, surf, bx, rng):
        lean = rng.choice((-1, 1)) * rng.randint(6, 12)
        trunk_h = rng.randint(44, 58)
        x = y = 0
        for i in range(0, trunk_h, 3):
            k = i / trunk_h
            x = bx + int(lean * k * k)
            y = GROUND_Y - i
            pygame.draw.rect(surf, (128, 88, 48) if (i // 3) % 2 else (100, 66, 36), (x - 2, y - 3, 5, 3))
        main, dark = self.t.near
        for ang in (-2.6, -2.0, -1.2, -0.5, 0.2, 0.9):
            for j in range(18):
                px = x + math.cos(ang) * j * 1.2
                py = y - 2 + math.sin(ang) * j * 0.6 + (j * j) * 0.035
                pygame.draw.rect(surf, dark, (int(px), int(py) + 1, 2, 2))
                pygame.draw.rect(surf, main, (int(px), int(py), 2, 1))
        pygame.draw.circle(surf, (90, 56, 26), (x - 1, y + 1), 2)
        pygame.draw.circle(surf, (90, 56, 26), (x + 2, y + 2), 2)

    @staticmethod
    def _cactus(surf, x, rng, main, dark):
        h = rng.randint(14, 26)
        pygame.draw.rect(surf, dark, (x - 2, GROUND_Y - h, 5, h))
        pygame.draw.rect(surf, main, (x - 2, GROUND_Y - h, 3, h))
        for side in (-1, 1):
            if rng.random() < 0.8:
                ay = GROUND_Y - rng.randint(6, h - 4)
                ax = x + side * 5
                pygame.draw.rect(surf, dark, (min(x, ax), ay, 6, 3))
                pygame.draw.rect(surf, dark, (ax - 1, ay - 6, 3, 9))
                pygame.draw.rect(surf, main, (ax - 1, ay - 6, 2, 8))

    def _build_ground(self):
        t, rng = self.t, self.rng
        top, top_dark, dirt, dirt_dark, speck = t.ground
        surf = pygame.Surface((WORLD_W, WORLD_H), pygame.SRCALPHA)
        pygame.draw.rect(surf, dirt, (0, GROUND_Y, WORLD_W, WORLD_H - GROUND_Y))
        for y in range(GROUND_Y + 6, WORLD_H, 7):            # soil layers
            for x in range(WORLD_W):
                if (x // 3 + y) % 5 == 0:
                    surf.set_at((x, y), dirt_dark)
        for _ in range(160):
            surf.set_at((rng.randrange(WORLD_W), rng.randint(GROUND_Y + 5, WORLD_H - 1)),
                        speck if rng.random() < 0.6 else dirt_dark)
        pygame.draw.rect(surf, top, (0, GROUND_Y, WORLD_W, 3))
        pygame.draw.rect(surf, top_dark, (0, GROUND_Y + 3, WORLD_W, 2))
        for x in range(0, WORLD_W, 2):                         # wavy edge
            if (x * 13) % 7 < 3:
                surf.set_at((x, GROUND_Y + 5), top_dark)
        if t.kind in ("jungle", "night"):
            for _ in range(70):                                # grass blades
                x = rng.randrange(WORLD_W)
                h = rng.randint(1, 3)
                pygame.draw.line(surf, top, (x, GROUND_Y - h), (x, GROUND_Y))
        if t.kind == "volcano":
            for _ in range(10):                                # lava cracks
                x, y = rng.randrange(WORLD_W), rng.randint(GROUND_Y + 6, WORLD_H - 4)
                for i in range(rng.randint(4, 10)):
                    surf.set_at((x + i, y + (i % 3 == 0)), speck)
        if t.kind == "beach":
            for _ in range(10):                                # shells
                x, y = rng.randrange(WORLD_W), rng.randint(GROUND_Y + 8, WORLD_H - 3)
                pygame.draw.rect(surf, (250, 160, 150), (x, y, 2, 1))
        return surf

    # --- every frame --------------------------------------------------------
    def update(self, dt: float):
        self.time += dt
        for c in self.clouds:
            c[0] += c[2] * dt
            if c[0] > WORLD_W + 10:
                c[0] = -c[3].get_width() - 10
        self._update_ambient(dt)

    def _update_ambient(self, dt):
        kind, rng = self.t.ambient, self.rng
        spawn = {"leaves": 0.6, "gulls": 0.15, "birds": 0.2, "fireflies": 2.0, "embers": 6.0}.get(kind, 0)
        if rng.random() < spawn * dt and len(self.ambient) < 40:
            if kind == "leaves":
                self.ambient.append([rng.uniform(0, WORLD_W), -4, rng.uniform(-6, 6), rng.uniform(10, 18), 0])
            elif kind in ("gulls", "birds"):
                d = rng.choice((-1, 1))
                self.ambient.append([-8 if d > 0 else WORLD_W + 8, rng.randint(20, 70), d * rng.uniform(16, 26), 0, 0])
            elif kind == "fireflies":
                self.ambient.append([rng.uniform(0, WORLD_W), rng.uniform(110, GROUND_Y - 4),
                                     rng.uniform(-4, 4), rng.uniform(-4, 4), rng.uniform(4, 8)])
            elif kind == "embers":
                self.ambient.append([rng.uniform(0, WORLD_W), GROUND_Y, rng.uniform(-4, 4), rng.uniform(-30, -14), 0])
        alive = []
        for p in self.ambient:
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            p[4] += dt
            if kind == "leaves":
                p[2] = 8 * math.sin(p[4] * 2)
            if kind == "fireflies" and p[4] > 8:
                continue
            if -12 < p[0] < WORLD_W + 12 and -10 < p[1] < WORLD_H:
                alive.append(p)
        self.ambient = alive

    def draw_back(self, surf: pygame.Surface, focus_x: float):
        """Sky, clouds, far and near layers. focus_x = player x, for a small parallax."""
        surf.blit(self.sky, (0, 0))
        for x, y, phase in self.stars:
            if math.sin(self.time * 2 + phase) > -0.3:
                surf.set_at((x, y), (220, 220, 255) if math.sin(self.time * 3 + phase) > 0.6 else (130, 140, 190))
        for x, y, _, c in self.clouds:
            surf.blit(c, (int(x), y))
        shift = (focus_x / WORLD_W - 0.5)
        surf.blit(self.far, (-PAD - int(shift * 8), 0))
        surf.blit(self.near, (-PAD - int(shift * 20), 0))
        self._draw_ambient(surf)

    def _draw_ambient(self, surf):
        kind = self.t.ambient
        for p in self.ambient:
            x, y = int(p[0]), int(p[1])
            if kind == "leaves":
                c = (96, 170, 60) if int(p[4] * 4) % 2 else (60, 130, 50)
                pygame.draw.rect(surf, c, (x, y, 2, 1 + int(p[4] * 4) % 2))
            elif kind in ("gulls", "birds"):
                c = (250, 250, 250) if kind == "gulls" else (60, 24, 40)
                up = int(p[4] * 6) % 2
                surf.set_at((x, y), c)
                surf.set_at((x - 1, y - up), c)
                surf.set_at((x + 1, y - up), c)
                surf.set_at((x - 2, y - 1 + up), c)
                surf.set_at((x + 2, y - 1 + up), c)
            elif kind == "fireflies":
                if math.sin(p[4] * 4 + p[0]) > 0:
                    surf.set_at((x, y), (230, 255, 120))
                    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        if 0 <= x + dx < WORLD_W and 0 <= y + dy < WORLD_H:
                            surf.set_at((x + dx, y + dy), mix(surf.get_at((x + dx, y + dy))[:3], (200, 255, 80), 0.5))
            elif kind == "embers":
                surf.set_at((x, y), (255, 200, 60) if int(p[4] * 8) % 2 else (255, 110, 30))

    def draw_ground(self, surf: pygame.Surface):
        surf.blit(self.ground, (0, 0))

    def thumbnail(self, w: int, h: int) -> pygame.Surface:
        full = pygame.Surface((WORLD_W, WORLD_H))
        self.draw_back(full, WORLD_W / 2)
        self.draw_ground(full)
        return pygame.transform.scale(full, (w, h))
