"""Game feel: particles, floating score text and screen shake."""
from __future__ import annotations

import random

import pygame

from . import font


class Effects:
    def __init__(self):
        self.parts = []   # [x, y, vx, vy, life, max_life, color, gravity]
        self.texts = []   # [text, x, y, life, color]
        self.shake_t = 0.0
        self.shake_mag = 0

    def burst(self, x, y, colors, n=10, speed=60, gravity=140, life=0.6):
        for _ in range(n):
            vx, vy = random.uniform(-speed, speed), random.uniform(-speed * 1.3, -speed * 0.2)
            lf = random.uniform(life * 0.6, life)
            self.parts.append([x, y, vx, vy, lf, lf, random.choice(colors), gravity])

    def text(self, msg, x, y, color=(255, 255, 255)):
        self.texts.append([msg, x, y, 0.9, color])

    def shake(self, t=0.25, mag=3):
        self.shake_t, self.shake_mag = t, mag

    def offset(self):
        if self.shake_t <= 0:
            return 0, 0
        return random.randint(-self.shake_mag, self.shake_mag), random.randint(-self.shake_mag, self.shake_mag)

    def clear(self):
        self.parts.clear()
        self.texts.clear()
        self.shake_t = 0

    def update(self, dt):
        self.shake_t -= dt
        for p in self.parts:
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            p[3] += p[7] * dt
            p[4] -= dt
        self.parts = [p for p in self.parts if p[4] > 0]
        for t in self.texts:
            t[2] -= 18 * dt
            t[3] -= dt
        self.texts = [t for t in self.texts if t[3] > 0]

    def draw(self, surf):
        for x, y, _, _, life, max_life, color, _ in self.parts:
            size = 2 if life > max_life * 0.5 else 1
            pygame.draw.rect(surf, color, (int(x), int(y), size, size))
        for msg, x, y, life, color in self.texts:
            if life > 0.25 or int(life * 20) % 2:
                font.draw(surf, msg, int(x), int(y), color, align="center")
