"""Everything that moves in the world (world coordinates, 264 x 200)."""
from __future__ import annotations

import math
import random

import pygame

from . import GROUND_Y, WORLD_H, WORLD_W, font

SPEED, ACCEL = 120.0, 900.0        # world px/s, px/s^2
JUMP_V, GRAVITY = -235.0, 720.0
JUMP_BUFFER = 0.2                  # a jump pressed this long before landing still counts
DASH_SPEED, DASH_TIME = 330.0, 0.22   # swipe / SHIFT: short burst of speed
RED, WHITE = (255, 84, 84), (255, 255, 255)


def put(surf, x, y, color):
    if 0 <= x < WORLD_W and 0 <= y < WORLD_H:
        surf.set_at((x, y), color)


class Monkey:
    def __init__(self, x=WORLD_W / 2):
        self.x, self.y, self.vx, self.vy = x, float(GROUND_Y), 0.0, 0.0
        self.on_ground, self.invuln, self.anim, self.t = True, 0.0, 0.0, 0.0
        self.jump_buffer = 0.0
        self.shield = False
        self.dash_t, self.dash_dir = 0.0, 0

    def dash(self, direction: int) -> bool:
        if self.dash_t > 0 or not direction:
            return False
        self.dash_t, self.dash_dir = DASH_TIME, direction
        return True

    def update(self, dt, move, jump) -> bool:
        if self.dash_t > 0:
            self.dash_t -= dt
            self.vx = self.dash_dir * DASH_SPEED
        else:
            target = move * SPEED
            step = (ACCEL if move else ACCEL * 1.6) * dt
            self.vx += max(-step, min(step, target - self.vx))
        self.x += self.vx * dt
        if not 8 <= self.x <= WORLD_W - 8:
            self.x, self.vx = max(8, min(WORLD_W - 8, self.x)), 0.0
        # Gestures arrive a little late, so a jump asked for just before landing is kept.
        self.jump_buffer = JUMP_BUFFER if jump else max(0.0, self.jump_buffer - dt)
        jumped = False
        if self.jump_buffer > 0 and self.on_ground:
            self.vy, self.on_ground, jumped, self.jump_buffer = JUMP_V, False, True, 0.0
        self.vy += GRAVITY * dt
        self.y += self.vy * dt
        if self.y >= GROUND_Y:
            self.y, self.vy, self.on_ground = float(GROUND_Y), 0.0, True
        self.invuln = max(0.0, self.invuln - dt)
        self.anim += dt * abs(self.vx) / SPEED * 9
        self.t += dt
        return jumped

    @property
    def catch_rect(self):
        return pygame.Rect(int(self.x) - 8, int(self.y) - 17, 16, 12)

    @property
    def hurt_rect(self):
        return pygame.Rect(int(self.x) - 5, int(self.y) - 12, 10, 12)

    def frame(self):
        if not self.on_ground:
            return "monkey_jump"
        if abs(self.vx) > 25:
            return "monkey_runA" if int(self.anim) % 2 else "monkey_runB"
        return "monkey_blink" if self.t % 3.2 < 0.12 else "monkey_idle"

    def draw(self, surf, spr, ground_color):
        height = GROUND_Y - self.y
        w = max(6, 14 - int(height / 6))
        pygame.draw.ellipse(surf, ground_color, (int(self.x) - w // 2, GROUND_Y - 1, w, 3))
        frame = self.frame()
        img = spr["monkey_hit"] if self.invuln and int(self.invuln * 14) % 2 else spr[frame]
        bob = 1 if frame == "monkey_runA" else 0
        surf.blit(img, (int(self.x) - 8, int(self.y) - 16 - bob))
        if self.shield:
            r = 12 + int(math.sin(self.t * 6))
            pygame.draw.circle(surf, (120, 180, 255), (int(self.x), int(self.y) - 8), r, 1)


class Banana:
    def __init__(self, speed, golden, x=None, t=0.0):
        self.x = random.uniform(12, WORLD_W - 12) if x is None else x
        self.y, self.v = -8.0, speed
        self.golden, self.phase = golden, random.uniform(0, 6.28)
        self.born, self.reacted = t, False   # for the reaction-time stat
        self.carried = None                  # the bird holding it

    def update(self, dt):
        if self.carried:
            self.x, self.y = self.carried.x, self.carried.y + 8
            return
        self.y += self.v * dt
        self.phase += dt * 3

    @property
    def draw_x(self):
        return self.x + (0 if self.carried else math.sin(self.phase) * 2)

    @property
    def rect(self):
        return pygame.Rect(int(self.draw_x) - 5, int(self.y) - 4, 10, 8)

    def draw(self, surf, spr, t):
        surf.blit(spr["golden" if self.golden else "banana"], (int(self.draw_x) - 6, int(self.y) - 5))
        if self.golden and int(t * 8 + self.phase) % 3 == 0:
            put(surf, int(self.draw_x) + random.randint(-7, 7), int(self.y) + random.randint(-6, 6), WHITE)


class Roller:
    """Coconut rolling along the ground. Some bounce. A warning shows first."""

    def __init__(self, speed, warning=0.9, bounce=False):
        self.dir = random.choice((-1, 1))
        self.x, self.v = (-8.0 if self.dir == 1 else WORLD_W + 8.0), speed * self.dir
        self.delay, self.dist, self.cleared = warning, 0.0, False
        self.bounce = bounce

    def update(self, dt):
        if self.delay > 0:
            self.delay -= dt
            return
        self.x += self.v * dt
        self.dist += abs(self.v * dt)

    @property
    def lift(self):
        return int(abs(math.sin(self.dist / 14)) * 20) if self.bounce else 0

    @property
    def rect(self):
        return pygame.Rect(int(self.x) - 4, GROUND_Y - 9 - self.lift, 8, 8)

    def gone(self):
        return self.x < -20 or self.x > WORLD_W + 20

    def draw(self, surf, spr, t):
        if self.delay > 0:
            if int(t * 8) % 2:
                x = 3 if self.dir == 1 else WORLD_W - 12
                pygame.draw.rect(surf, (255, 150, 40) if self.bounce else RED, (x, GROUND_Y - 20, 9, 11))
                font.draw(surf, "!", x + 2, GROUND_Y - 18, WHITE, shadow=None)
            return
        frame = int(self.dist / 4) % 4
        if self.bounce:   # shadow so you can judge the bounce
            pygame.draw.ellipse(surf, (40, 30, 30), (int(self.x) - 4, GROUND_Y - 1, 8, 2))
        surf.blit(spr["coconut"][frame if self.dir == 1 else -frame], (int(self.x) - 5, GROUND_Y - 10 - self.lift))


class Rock:
    """Falls from the sky (volcano). A blinking mark on the ground shows where."""

    def __init__(self, warning=0.9):
        self.x, self.y, self.vy = random.uniform(14, WORLD_W - 14), -10.0, 30.0
        self.delay = warning

    def update(self, dt):
        if self.delay > 0:
            self.delay -= dt
            return
        self.vy += 260 * dt
        self.y += self.vy * dt

    @property
    def rect(self):
        return pygame.Rect(int(self.x) - 4, int(self.y) - 4, 8, 8)

    def draw(self, surf, spr, t):
        if int(t * 10) % 2 or self.delay <= 0:
            x = int(self.x)
            pygame.draw.line(surf, RED, (x - 3, GROUND_Y - 1), (x + 3, GROUND_Y + 1))
            pygame.draw.line(surf, RED, (x - 3, GROUND_Y + 1), (x + 3, GROUND_Y - 1))
        if self.delay <= 0:
            for i in range(1, 4):   # fire trail
                put(surf, int(self.x) + random.randint(-2, 2), int(self.y) - 5 - i * 3, (255, 160 - i * 30, 40))
            surf.blit(spr["rock"][int(t * 12) % 4], (int(self.x) - 5, int(self.y) - 5))


class Bird:
    """Flies across the sky and steals the first banana it touches."""

    def __init__(self, speed=48):
        self.dir = random.choice((-1, 1))
        self.x = -10.0 if self.dir == 1 else WORLD_W + 10.0
        self.base_y, self.t = random.uniform(34, 80), 0.0
        self.v = speed * self.dir
        self.loot = None

    @property
    def y(self):
        return self.base_y + math.sin(self.t * 3) * 4

    def update(self, dt):
        self.t += dt
        self.x += self.v * dt * (1.4 if self.loot else 1)

    @property
    def rect(self):
        return pygame.Rect(int(self.x) - 6, int(self.y) - 3, 12, 8)

    def gone(self):
        return self.x < -20 or self.x > WORLD_W + 20

    def draw(self, surf, spr, t):
        img = spr["bird"][int(self.t * 8) % 2]
        if self.dir < 0:
            img = pygame.transform.flip(img, True, False)
        surf.blit(img, (int(self.x) - 6, int(self.y) - 5))


class PowerUp:
    KINDS = ("magnet", "slow", "shield", "heart")
    DURATION = {"magnet": 7.0, "slow": 6.0}

    def __init__(self, kind=None, x=None):
        self.kind = kind or random.choice(self.KINDS)
        self.x = random.uniform(16, WORLD_W - 16) if x is None else x
        self.y, self.phase = -10.0, random.uniform(0, 6.28)

    def update(self, dt):
        self.y += 30 * dt
        self.phase += dt * 2.5

    @property
    def draw_x(self):
        return self.x + math.sin(self.phase) * 5

    @property
    def rect(self):
        return pygame.Rect(int(self.draw_x) - 7, int(self.y) - 7, 14, 14)

    def draw(self, surf, spr, t):
        surf.blit(spr["power"][self.kind], (int(self.draw_x) - 7, int(self.y) - 7 + int(math.sin(t * 4))))
