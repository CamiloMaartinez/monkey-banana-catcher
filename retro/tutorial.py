"""Tutorial: one gesture at a time, the next step only starts when the current one is done."""
from __future__ import annotations

import random

from . import WORLD_W
from .entities import Banana, PowerUp, Roller

STEPS = ["tut_1", "tut_2", "tut_3", "tut_4", "tut_5", "tut_6", "tut_7"]
HOLD = 1.0       # seconds to hold a tilt
JUMPS = 3
BANANAS = 3


class Tutorial:
    def __init__(self):
        self.step = 0
        self.hold = 0.0
        self.count = 0
        self.spawn_t = 0.0

    @property
    def finished(self):
        return self.step >= len(STEPS)

    def progress(self) -> float:
        if self.step in (0, 1):
            return self.hold / HOLD
        if self.step == 2:
            return self.count / JUMPS
        if self.step == 3:
            return self.count / BANANAS
        return 0.0

    def next(self, game):
        self.step += 1
        self.hold = self.count = 0
        self.spawn_t = 0.0
        game.fx.text("OK!", game.monkey.x, game.monkey.y - 28, (110, 230, 110))
        game.sound("step")

    def update(self, game, dt, move, jumped, caught, cleared, powered, dashed=0):
        """Called every frame by the game with what just happened."""
        if self.finished:
            return
        m = game.monkey
        if self.step == 0 or self.step == 1:
            want = -1 if self.step == 0 else 1
            self.hold = self.hold + dt if move == want else max(0.0, self.hold - dt)
            if self.hold >= HOLD:
                self.next(game)
        elif self.step == 2:
            self.count += jumped
            if self.count >= JUMPS:
                self.next(game)
        elif self.step == 3:
            self.count += caught
            self.spawn_t -= dt
            if not game.bananas and self.spawn_t <= 0:
                x = max(14, min(WORLD_W - 14, m.x + random.choice((-1, 1)) * random.uniform(30, 70)))
                game.bananas.append(Banana(30, False, x=x, t=game.level_time))
                self.spawn_t = 0.5
            if self.count >= BANANAS:
                self.next(game)
        elif self.step == 4:
            if cleared:
                self.next(game)
            elif not game.rollers:
                game.rollers.append(Roller(45, warning=2.0))
        elif self.step == 5:
            if powered:
                self.next(game)
            elif not game.powerups:
                game.powerups.append(PowerUp("shield", x=max(16, min(WORLD_W - 16, m.x + random.uniform(-50, 50)))))
        elif self.step == 6:
            if dashed:
                self.next(game)
