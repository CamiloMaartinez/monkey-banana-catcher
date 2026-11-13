"""Monkey Banana Catcher - retro edition.

Catch enough bananas before the time runs out. Coconuts, rocks and birds get in the way.
Tutorial, 5 levels, endless mode with a top 10, in-game calibration, settings.

Controls (keyboard and gestures work at the same time, also in the menus):
    Move / choose   A / D or arrows      left index finger tilt
    Jump / OK       SPACE / ENTER        right hand pinch
    Dash            SHIFT                right hand swipe
    Pause           P                    left fist held 0.6 s
    M sound   N music   L language   R network/rules   F11 full screen   ESC back

Usage:
    python game.py                    # neural network models (your calibrated ones if you calibrated)
    python game.py --player ana       # ana's calibrated models
    python game.py --rules            # backup: fixed rules instead of the network
    python game.py --no-camera        # keyboard only
"""
from __future__ import annotations

import argparse
import json
import math
import random
import time
from datetime import datetime

import pygame

from gestures import config
from retro import GROUND_Y, PANEL_W, SCALE, SCREEN_H, SCREEN_W, WORLD_H, WORLD_W, font, sfx, sprites
from retro.calibration import Calibration
from retro.effects import Effects
from retro.entities import SPEED, Banana, Bird, Monkey, PowerUp, Rock, Roller
from retro.i18n import Text
from retro.levels import ENDLESS_LEVEL, LEVELS, MENU_LEVELS, TUTORIAL_LEVEL, Level
from retro.panel import draw_panel
from retro.save import HighScores, Progress, Settings
from retro.scenery import Scenery, darker
from retro.stats import AIStats, ConfidenceHistory
from retro.tutorial import STEPS as TUT_STEPS
from retro.tutorial import Tutorial

# Difficulty: speed multiplier, warning-time multiplier, extra seconds, hearts
DIFFICULTY = {
    "easy": {"speed": 0.8, "warn": 1.5, "time": 15, "hearts": 7},
    "normal": {"speed": 1.0, "warn": 1.0, "time": 0, "hearts": 5},
    "hard": {"speed": 1.2, "warn": 0.75, "time": -10, "hearts": 4},
}
BASE_WARNING = 0.9          # seconds of "!" before a coconut or rock
GESTURE_BONUS = 0.4         # extra warning when playing with the camera (gestures react later than keys)
ENDLESS_THEME_EVERY = 15    # bananas before the endless scenery changes

WHITE, YELLOW, RED, GREEN = (255, 255, 255), (255, 214, 60), (255, 84, 84), (110, 230, 110)
INK, GREY, PANEL_BG = (24, 16, 30), (150, 140, 170), (34, 24, 52)
TITLE_MENU = ["play", "tutorial", "calibrate", "settings"]
SETTINGS_MENU = ["difficulty", "language", "sound", "music", "control", "back"]


def parse_args():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--player", help="use this player's calibrated models")
    p.add_argument("--rules", action="store_true", help="use fixed rules instead of the network")
    p.add_argument("--no-camera", action="store_true", help="keyboard only")
    p.add_argument("--camera", type=int, default=config.CAMERA_INDEX)
    p.add_argument("--mute", action="store_true", help="start with sound and music off")
    p.add_argument("--windowed", action="store_true", help="open in a window instead of full screen (F11 switches)")
    p.add_argument("--demo-seconds", type=float, default=0, help=argparse.SUPPRESS)  # auto-quit, for tests
    return p.parse_args()


class MenuNav:
    """Turns a held tilt into single menu steps (one step, then repeats slowly)."""

    def __init__(self):
        self.dir, self.timer = 0, 0.0

    def step(self, move, dt) -> int:
        if move != self.dir:
            self.dir, self.timer = move, 0.5
            return move
        if move:
            self.timer -= dt
            if self.timer <= 0:
                self.timer = 0.4
                return move
        return 0


class Game:
    def __init__(self, args):
        pygame.init()
        self.args = args
        self.settings = Settings(config.ROOT / "settings.json")
        self.t = Text(self.settings["lang"])
        if args.mute:
            sfx.enabled = sfx.music_on = False
        else:
            sfx.init()
            sfx.enabled = sfx.enabled and self.settings["sound"]
            sfx.music_on = self.settings["music"]
            sfx.preload()
        pygame.display.set_caption("Monkey Banana Catcher")
        # Full screen by default: SCALED keeps the pixel art sharp and adds black bars if the
        # monitor has another shape. F11 switches between full screen and a window.
        flags = pygame.SCALED if args.windowed else pygame.SCALED | pygame.FULLSCREEN
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H), flags)
        self.world = pygame.Surface((WORLD_W, WORLD_H))
        self.spr = sprites.load()
        pygame.display.set_icon(pygame.transform.scale(self.spr["banana"], (36, 27)))
        self.clock = pygame.time.Clock()

        self.player = (args.player or self.settings["player"] or "").lower()
        self.controller = None
        if not args.no_camera:
            self.loading_screen()   # torch + mediapipe take a few seconds to load on Windows
            from gestures.controller import GestureController  # loads torch + mediapipe only if needed
            use_rules = args.rules or self.settings["control"] == "rules"
            self.controller = GestureController(args.camera, use_rules, self.player or None,
                                                preview_width=PANEL_W - 8).start()
        self.progress = Progress(config.ROOT / "progress.json")
        self.highscores = HighScores(config.ROOT / "highscores.json")
        self.scenes = [Scenery(lv.theme, seed=lv.number) for lv in LEVELS]
        thumbs = [s.thumbnail(34, 26) for s in self.scenes]
        endless_thumb = pygame.Surface((34, 26))
        for i, th in enumerate(thumbs):   # endless = a slice of every scenery
            endless_thumb.blit(th, (i * 7, 0), (i * 7, 0, 7, 26))
        self.thumbs = [thumbs[0], *thumbs, endless_thumb]
        self.fx = Effects()
        self.nav = MenuNav()
        self.history = ConfidenceHistory()
        self.time = 0.0
        self.results = []
        self.title_choice, self.level_sel, self.settings_sel = 0, 1, 0
        self.choice, self.menu_delay, self.end_time = 0, 0.0, 0.0
        self.title_monkey, self.title_dir = Monkey(40), 1
        self.cal = None
        self.start_level(LEVELS[0])
        self.state = "TITLE"
        sfx.music("menu")

    # --- helpers ------------------------------------------------------------
    def loading_screen(self):
        self.screen.fill(INK)
        cx, cy = SCREEN_W // 2, SCREEN_H // 2
        self.screen.blit(pygame.transform.scale(self.spr["banana"], (72, 54)), (cx - 36, cy - 90))
        font.draw(self.screen, self.t("loading"), cx, cy, YELLOW, 3, "center")
        font.draw(self.screen, self.t("loading2"), cx, cy + 40, GREY, 2, "center")
        pygame.display.flip()
        pygame.event.pump()

    @property
    def diff(self):
        return DIFFICULTY[self.settings["difficulty"]]

    @property
    def mode_key(self):
        if not self.controller:
            return "mode_keyboard"
        return "mode_rules" if self.controller.use_rules else "mode_network"

    def warning(self):
        return BASE_WARNING * self.diff["warn"] + (GESTURE_BONUS if self.controller else 0)

    @staticmethod
    def sound(name):
        sfx.play(name)

    def level_name(self, lv: Level):
        return self.t(lv.key)

    # --- flow ---------------------------------------------------------------
    def start_level(self, level: Level):
        self.level = level
        self.scene = self.scenes[0] if level.number in (0, 6) else self.scenes[level.number - 1]
        self.monkey = Monkey()
        self.bananas, self.rollers, self.rocks, self.birds, self.powerups = [], [], [], [], []
        self.caught = self.score = self.combo = 0
        self.max_lives = self.diff["hearts"]
        self.lives = self.max_lives
        self.t_banana, self.t_roller, self.t_rock, self.t_bird = 0.6, 0.0, 0.0, 0.0
        self.t_power = random.uniform(6, 10)
        self.magnet = self.slow = 0.0
        self.countdown = 0.8 if level.tutorial else 2.2
        self.level_time = 0.0
        self.time_left = level.time_limit + self.diff["time"] if level.time_limit else 0.0
        self.end_reason, self.rank, self.stars_won, self.summary = "", None, 0, None
        self.last_x = self.monkey.x
        self.pending_dash = 0
        self.stats = AIStats()
        self.tutorial = Tutorial() if level.tutorial else None
        self.fx.clear()
        self.state = "PLAY"
        sfx.music("tutorial" if level.tutorial else "endless" if level.endless else f"lv{level.number}")

    def finish(self, cleared, reason=""):
        lv = self.level
        self.end_reason = reason
        self.summary = self.stats.summary()
        stars = 0
        if lv.endless:
            self.rank = self.highscores.add(self.player or "player", self.score)
            self.progress.record(lv.number, 0, self.score)
        elif cleared:
            self.score += int(self.time_left)   # time bonus
            lost = self.max_lives - self.lives
            stars = 3 if lost == 0 else 2 if lost <= 2 else 1
            self.progress.record(lv.number, stars, self.score)
        self.stars_won = stars
        self.results.append({"level": lv.number, "difficulty": self.settings["difficulty"], "cleared": cleared,
                             "stars": stars, "bananas": self.caught, "score": self.score,
                             "seconds": round(self.level_time, 1), "ai": self.summary})
        self.state, self.choice, self.menu_delay, self.end_time = ("CLEAR" if cleared else "OVER"), 0, 0.9, 0.0
        self.sound("clear" if cleared else "over")
        sfx.music(None)

    def hurt(self):
        m = self.monkey
        if m.shield:
            m.shield, m.invuln = False, 1.0
            self.fx.text(self.t("blocked"), m.x, m.y - 30, (120, 180, 255))
            self.sound("shield")
            return
        if not self.tutorial:
            self.lives -= 1
        self.combo = 0
        m.invuln = 1.5
        self.fx.shake(0.3, 3)
        self.fx.burst(m.x, m.y - 8, [RED, (255, 160, 160)], n=14)
        self.sound("hit")

    def power(self, p: PowerUp):
        m = self.monkey
        if p.kind == "magnet":
            self.magnet = PowerUp.DURATION["magnet"]
        elif p.kind == "slow":
            self.slow = PowerUp.DURATION["slow"]
        elif p.kind == "shield":
            m.shield = True
        else:
            self.lives = min(self.max_lives, self.lives + 1)
        self.fx.text(self.t(f"pu_{p.kind}"), m.x, m.y - 30, sprites.POWER_COLORS[p.kind])
        self.fx.burst(p.x, p.y, [sprites.POWER_COLORS[p.kind], WHITE], n=12)
        self.sound("power")

    # --- main loop ------------------------------------------------------------
    def run(self):
        start = time.time()
        running = True
        while running:
            dt = min(self.clock.tick(60) / 1000, 1 / 20)
            running = self.tick(dt, pygame.event.get())
            pygame.display.flip()
            if self.args.demo_seconds and time.time() - start > self.args.demo_seconds:
                running = False
        self.quit(time.time() - start)

    def tick(self, dt, events) -> bool:
        """One frame: read input, update the current screen, draw. False = quit."""
        self.time += dt
        running = True
        typing = self.state == "CAL" and self.cal.stage == "NAME"
        key_step, confirm, back, pause, key_jump, key_dash = 0, False, False, False, False, False
        for e in events:
            if e.type == pygame.QUIT:
                running = False
            elif e.type == pygame.KEYDOWN:
                k = e.key
                if k == pygame.K_ESCAPE:
                    back = True
                elif k in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    confirm = True
                elif k == pygame.K_F11:
                    pygame.display.toggle_fullscreen()
                elif typing:
                    continue                      # letters are the player's name here
                elif k in (pygame.K_a, pygame.K_LEFT):
                    key_step = -1
                elif k in (pygame.K_d, pygame.K_RIGHT):
                    key_step = 1
                elif k in (pygame.K_SPACE, pygame.K_w, pygame.K_UP):
                    key_jump = confirm = True
                elif k == pygame.K_p:
                    pause = True
                elif k in (pygame.K_LSHIFT, pygame.K_RSHIFT):
                    key_dash = True
                elif k == pygame.K_m:
                    self.toggle("sound")
                elif k == pygame.K_n:
                    self.toggle("music")
                elif k == pygame.K_l:
                    self.toggle("language")
                elif k == pygame.K_r:
                    self.toggle("control")

        keys = pygame.key.get_pressed()
        move = 0 if typing else (keys[pygame.K_d] or keys[pygame.K_RIGHT]) - (keys[pygame.K_a] or keys[pygame.K_LEFT])
        cs = self.controller.state() if self.controller else None
        self.history.add(cs)
        gesture_move = cs.move if cs else 0
        pinch = bool(cs and cs.jump)
        move = move or gesture_move
        step = key_step or self.nav.step(gesture_move, dt)
        confirm = confirm or pinch
        pause = pause or bool(cs and cs.pause)          # left fist held
        if key_dash:                                     # SHIFT: dash where you are going
            self.pending_dash = move or (1 if self.monkey.vx >= 0 else -1)
        elif cs and cs.dash:                             # right-hand swipe
            self.pending_dash = cs.dash

        if self.state == "TITLE":
            running = self.update_title(dt, step, confirm, back) and running
        elif self.state == "LEVELS":
            self.update_levels(dt, step, confirm, back)
        elif self.state == "SETTINGS":
            self.update_settings(dt, step, confirm, back)
        elif self.state == "CAL":
            self.scenes[0].update(dt)
            result = self.cal.update(dt, events, cs, confirm, back)
            if result == "trained":
                self.player = self.cal.name
                self.settings["player"] = self.player
                self.controller.load_models(self.player)
                self.sound("clear")
            elif result == "exit":
                self.state = "TITLE"
                sfx.music("menu")
        elif self.state == "PLAY":
            if pause or back:
                self.state = "PAUSE"
            elif self.tutorial and self.tutorial.finished and confirm:
                self.progress.record(0, 3, 0)
                self.state, self.level_sel = "LEVELS", 1
                sfx.music("menu")
            else:
                if pinch:
                    self.stats.pinches += 1
                self.update_play(dt, move, key_jump or pinch, cs)
        elif self.state == "PAUSE":
            if pause or confirm:
                self.state = "PLAY"
            elif back:
                self.state = "LEVELS"
                sfx.music("menu")
        else:
            self.update_end(dt, step, confirm, back)
        self.draw(cs)
        return running

    def toggle(self, what):
        s = self.settings
        if what == "sound":
            s["sound"] = sfx.toggle()
        elif what == "music":
            s["music"] = not s["music"]
            sfx.set_music(s["music"])
        elif what == "language":
            self.t.toggle()
            s["lang"] = self.t.lang
        elif what == "control" and self.controller:
            rules = not self.controller.use_rules
            self.controller.set_rules(rules)
            s["control"] = "rules" if rules else "network"
        elif what == "difficulty":
            order = list(DIFFICULTY)
            s["difficulty"] = order[(order.index(s["difficulty"]) + 1) % len(order)]
        self.sound("select")

    def update_title(self, dt, step, confirm, back) -> bool:
        self.scenes[0].update(dt)
        m = self.title_monkey
        if m.x > WORLD_W - 30:
            self.title_dir = -1
        elif m.x < 30:
            self.title_dir = 1
        m.update(dt, self.title_dir, m.on_ground and random.random() < 0.01)
        if step:
            self.title_choice = (self.title_choice + step) % len(TITLE_MENU)
            self.sound("select")
        if confirm:
            self.sound("confirm")
            pick = TITLE_MENU[self.title_choice]
            if pick == "play":
                self.state = "LEVELS"
            elif pick == "tutorial":
                self.start_level(TUTORIAL_LEVEL)
            elif pick == "calibrate":
                self.cal = Calibration(self.t, self.controller, self.player)
                self.state = "CAL"
                sfx.music("tutorial")
            else:
                self.state, self.settings_sel = "SETTINGS", 0
        return not back

    def update_levels(self, dt, step, confirm, back):
        lv = MENU_LEVELS[self.level_sel]
        self.scene_for(lv).update(dt)
        if step:
            self.level_sel = (self.level_sel + step) % len(MENU_LEVELS)
            self.sound("select")
        if confirm:
            self.sound("confirm")
            self.start_level(lv)
        elif back:
            self.state = "TITLE"

    def update_settings(self, dt, step, confirm, back):
        self.scenes[1].update(dt)
        if step:
            self.settings_sel = (self.settings_sel + step) % len(SETTINGS_MENU)
            self.sound("select")
        item = SETTINGS_MENU[self.settings_sel]
        if back or (confirm and item == "back"):
            self.state = "TITLE"
            self.sound("confirm")
        elif confirm:
            self.toggle(item)

    def update_end(self, dt, step, confirm, back):
        self.scene.update(dt)
        self.fx.update(dt)
        self.menu_delay -= dt
        self.end_time += dt
        if step:
            self.choice = 1 - self.choice
            self.sound("select")
        if back:
            self.state = "LEVELS"
            sfx.music("menu")
        elif confirm and self.menu_delay <= 0:
            self.sound("confirm")
            lv = self.level
            if self.choice == 1:
                self.level_sel = MENU_LEVELS.index(lv)
                self.state = "LEVELS"
                sfx.music("menu")
            elif self.state == "CLEAR" and 1 <= lv.number < len(LEVELS):
                self.level_sel = lv.number + 1
                self.start_level(LEVELS[lv.number])
            else:
                self.start_level(lv)

    def scene_for(self, lv: Level):
        if lv.endless:
            return self.scenes[(self.caught // ENDLESS_THEME_EVERY) % len(self.scenes)] if self.state != "LEVELS" \
                else self.scenes[int(self.time / 2) % len(self.scenes)]
        return self.scenes[0] if lv.tutorial else self.scenes[lv.number - 1]

    # --- gameplay ---------------------------------------------------------------
    def update_play(self, dt, move, jump, cs):
        lv, m = self.level, self.monkey
        self.stats.frame(cs)
        if lv.endless:
            new_scene = self.scene_for(lv)
            if new_scene is not self.scene:
                self.scene = new_scene
                self.fx.burst(WORLD_W / 2, 60, [YELLOW, WHITE], n=20, speed=90)
        self.scene.update(dt)
        self.fx.update(dt)
        if self.countdown > 0:
            self.countdown -= dt
            self.pending_dash = 0
            m.update(dt, move, False)
            return
        self.level_time += dt
        if lv.time_limit:
            self.time_left -= dt
            if self.time_left <= 0:
                self.time_left = 0
                self.finish(False, "time_up")
                return
        dashed = 0
        if self.pending_dash and m.dash(self.pending_dash):
            dashed = 1
            self.fx.text(self.t("dash"), m.x, m.y - 30, (120, 220, 255))
            self.fx.burst(m.x, m.y - 6, [(120, 220, 255), WHITE], n=10, speed=50, life=0.3)
            self.sound("step")
        self.pending_dash = 0
        jumped = m.update(dt, move, jump)
        if jumped:
            self.sound("jump")
            self.fx.burst(m.x, GROUND_Y, [darker(self.scene.t.ground[0], 10)], n=5, speed=25, life=0.3)
        wdt = dt * (0.5 if self.slow > 0 else 1.0)    # slow-mo slows the world, not the monkey
        self.slow = max(0.0, self.slow - dt)
        self.magnet = max(0.0, self.magnet - dt)
        if self.tutorial is None:
            self.spawn(dt)

        caught = cleared = powered = 0
        lowest = max((b for b in self.bananas if not b.carried), key=lambda b: b.y, default=None)
        for b in self.bananas[:]:
            b.update(wdt)
            if b.carried:
                if b.carried.gone():
                    self.bananas.remove(b)
                continue
            if self.magnet > 0 and abs(b.x - m.x) < 90 and b.y > 30:
                b.x += max(-70 * dt, min(70 * dt, m.x - b.x))
            if b is lowest and not b.reacted:   # reaction time: until the monkey heads to the banana
                dx = b.x - m.x
                if abs(dx) < 12:
                    b.reacted = True
                elif abs(m.vx) > 30 and (m.vx > 0) == (dx > 0):
                    b.reacted = True
                    self.stats.reactions.append(self.level_time - b.born)
            if b.rect.colliderect(m.catch_rect):
                self.bananas.remove(b)
                caught += 1
                self.catch(b)
                if lv.goal and self.caught >= lv.goal:
                    self.finish(True)
                    return
            elif b.y >= GROUND_Y - 2:
                self.bananas.remove(b)
                self.combo = 0
                self.fx.burst(b.x, GROUND_Y - 1, [YELLOW, (200, 160, 40)], n=8, speed=40)
                self.fx.text(self.t("miss"), b.x, GROUND_Y - 14, GREY)
                self.sound("miss")
                if lv.endless:          # endless has no timer: a miss costs a heart
                    self.lives -= 1
        for c in self.rollers[:]:
            c.update(wdt)
            if c.delay > 0:
                continue
            if c.rect.colliderect(m.hurt_rect) and not m.invuln:
                self.rollers.remove(c)
                self.hurt()
            elif c.gone():
                self.rollers.remove(c)
            elif not c.cleared and not m.on_ground and abs(c.x - m.x) < 5:
                c.cleared = True
                cleared += 1
                self.score += 2
                self.fx.text(self.t("nice"), m.x, m.y - 30, GREEN)
                self.sound("nice")
        for r in self.rocks[:]:
            r.update(wdt)
            if r.delay > 0:
                continue
            if r.rect.colliderect(m.hurt_rect) and not m.invuln:
                self.rocks.remove(r)
                self.hurt()
            elif r.y >= GROUND_Y - 3:
                self.rocks.remove(r)
                self.fx.burst(r.x, GROUND_Y - 2, [(120, 100, 96), (255, 120, 30)], n=10, speed=45)
                self.fx.shake(0.12, 1)
        for bird in self.birds[:]:
            bird.update(wdt)
            if bird.loot is None:
                for b in self.bananas:
                    if not b.carried and b.rect.colliderect(bird.rect):
                        b.carried, bird.loot = bird, b
                        self.fx.text(self.t("stolen"), bird.x, bird.y - 12, (200, 160, 255))
                        self.sound("steal")
                        break
            if bird.gone():
                self.birds.remove(bird)
        for p in self.powerups[:]:
            p.update(wdt)
            if p.rect.colliderect(m.catch_rect):
                self.powerups.remove(p)
                powered += 1
                self.power(p)
            elif p.y > GROUND_Y:
                self.powerups.remove(p)
        if self.tutorial:
            self.tutorial.update(self, dt, move, int(jumped), caught, cleared, powered, dashed)
        if self.lives <= 0:
            self.finish(False, "no_hearts")

    def catch(self, b: Banana):
        self.caught += 1
        self.combo += 1
        mult = min(1 + self.combo // 5, 4)
        pts = (5 if b.golden else 1) * mult
        self.score += pts
        self.fx.text(f"+{pts}", b.x, b.y - 10, (255, 160, 40) if b.golden else YELLOW)
        self.fx.burst(b.x, b.y, [YELLOW, WHITE, (255, 240, 150)], n=12 if b.golden else 7)
        self.sound("gold" if b.golden else "catch")

    def spawn(self, dt):
        lv = self.level
        if lv.endless:
            k = min(2.4, 1 + self.caught / 40)
        else:
            k = 1 + 0.25 * self.caught / lv.goal     # a bit faster as you progress
        k *= self.diff["speed"]
        self.t_banana += dt
        interval = lv.banana_every / k
        if self.t_banana > interval:
            self.t_banana = 0
            x = None
            if lv.endless:   # misses cost hearts here, so every banana must be reachable
                reach = SPEED * interval * 0.8 + 30
                x = max(12, min(WORLD_W - 12, self.last_x + random.uniform(-reach, reach)))
                self.last_x = x
            self.bananas.append(Banana(lv.banana_speed * k * random.uniform(0.9, 1.1),
                                       random.random() < lv.golden_chance, x=x, t=self.level_time))
        if lv.coconut_every:
            self.t_roller += dt
            if self.t_roller > lv.coconut_every / k:
                self.t_roller = random.uniform(-1.0, 0)
                bounce = random.random() < lv.bounce_chance
                self.rollers.append(Roller(lv.coconut_speed * k * (0.8 if bounce else 1), self.warning(), bounce))
                self.sound("warn")
        if lv.rock_every or (lv.endless and self.caught > 45):
            self.t_rock += dt
            if self.t_rock > (lv.rock_every or 3.0) / k:
                self.t_rock = random.uniform(-0.8, 0)
                self.rocks.append(Rock(self.warning()))
        if lv.birds:
            self.t_bird += dt
            if self.t_bird > lv.birds:
                self.t_bird = random.uniform(-3, 0)
                self.birds.append(Bird())
        if lv.powerups:
            self.t_power -= dt
            if self.t_power <= 0:
                self.t_power = random.uniform(12, 18)
                kinds = [k for k in PowerUp.KINDS if k != "heart" or self.lives < self.max_lives]
                self.powerups.append(PowerUp(random.choice(kinds)))

    # --- drawing ------------------------------------------------------------------
    def draw(self, cs):
        w = self.world
        if self.state == "TITLE":
            self.draw_title(w)
        elif self.state == "LEVELS":
            self.draw_levels(w)
        elif self.state == "SETTINGS":
            self.draw_settings(w)
        elif self.state == "CAL":
            self.scenes[0].draw_back(w, WORLD_W / 2)
            self.scenes[0].draw_ground(w)
            self.dim(w, 100)
            self.cal.draw(w, self.time, self.box)
        else:
            self.draw_play(w, cs)
            if self.state == "PAUSE":
                self.dim(w)
                self.box(w, 62, 70, 140, 52)
                font.draw(w, self.t("paused"), WORLD_W // 2, 80, YELLOW, 2, "center")
                font.draw(w, self.t("resume"), WORLD_W // 2, 100, WHITE, align="center")
                font.draw(w, self.t("esc_levels"), WORLD_W // 2, 110, GREY, align="center")
            elif self.state in ("CLEAR", "OVER"):
                self.draw_end(w)
        dx, dy = self.fx.offset()
        self.screen.fill(INK)
        self.screen.blit(pygame.transform.scale(w, (WORLD_W * SCALE, WORLD_H * SCALE)), (dx * SCALE, dy * SCALE))
        draw_panel(self.screen, WORLD_W * SCALE, cs, self.t, self.mode_key, self.history)

    @staticmethod
    def dim(w, alpha=120):
        shade = pygame.Surface((WORLD_W, WORLD_H), pygame.SRCALPHA)
        shade.fill((10, 6, 20, alpha))
        w.blit(shade, (0, 0))

    @staticmethod
    def box(w, x, y, bw, bh, fill=PANEL_BG, border=(250, 214, 120)):
        pygame.draw.rect(w, INK, (x - 1, y - 1, bw + 2, bh + 2))
        pygame.draw.rect(w, fill, (x, y, bw, bh))
        pygame.draw.rect(w, border, (x, y, bw, bh), 1)
        pygame.draw.line(w, darker(border, 80), (x + 1, y + bh - 2), (x + bw - 2, y + bh - 2))

    def buttons(self, w, labels, selected, y, width):
        gap = 4
        x = (WORLD_W - (len(labels) * width + (len(labels) - 1) * gap)) // 2
        for i, label in enumerate(labels):
            sel = i == selected
            bx = x + i * (width + gap)
            pygame.draw.rect(w, INK, (bx - 1, y - 1, width + 2, 18))
            pygame.draw.rect(w, YELLOW if sel else (60, 48, 84), (bx, y, width, 16))
            font.draw(w, label, bx + width // 2, y + 5, INK if sel else WHITE, align="center", shadow=None)

    def draw_title(self, w):
        scene = self.scenes[0]
        scene.draw_back(w, self.title_monkey.x)
        scene.draw_ground(w)
        self.title_monkey.draw(w, self.spr, darker(scene.t.ground[0], 40))
        bob = int(math.sin(self.time * 2) * 2)
        self.box(w, 40, 18 + bob, 184, 66)
        font.draw(w, "MONKEY", WORLD_W // 2, 26 + bob, YELLOW, 3, "center", shadow=(120, 60, 0))
        font.draw(w, "BANANA CATCHER", WORLD_W // 2, 54 + bob, WHITE, 2, "center", shadow=(120, 60, 0))
        w.blit(self.spr["banana"], (48, 32 + bob))
        w.blit(pygame.transform.flip(self.spr["banana"], True, False), (204, 32 + bob))
        self.buttons(w, [self.t(k) for k in TITLE_MENU], self.title_choice, 98, 60)
        font.draw(w, self.t("menu_hint"), WORLD_W // 2, 120, WHITE, align="center")
        if self.player:
            font.draw(w, self.t("player", name=self.player.upper()), WORLD_W // 2, 132, YELLOW, align="center")
        font.draw(w, self.t("subtitle"), WORLD_W // 2, 190, (230, 245, 210), align="center", shadow=(40, 60, 30))

    def draw_levels(self, w):
        lv = MENU_LEVELS[self.level_sel]
        scene = self.scene_for(lv)
        scene.draw_back(w, WORLD_W / 2)
        scene.draw_ground(w)
        self.dim(w, 90)
        font.draw(w, self.t("select_level"), WORLD_W // 2, 8, YELLOW, 2, "center", shadow=(120, 60, 0))
        cw, gap = 34, 3
        x0 = (WORLD_W - (len(MENU_LEVELS) * cw + (len(MENU_LEVELS) - 1) * gap)) // 2
        for i, (item, thumb) in enumerate(zip(MENU_LEVELS, self.thumbs)):
            sel = i == self.level_sel
            x, y = x0 + i * (cw + gap), 30 - (3 if sel else 0)
            border = YELLOW if sel and int(self.time * 4) % 2 else (WHITE if sel else GREY)
            pygame.draw.rect(w, INK, (x - 2, y - 2, cw + 4, 41))
            w.blit(thumb, (x, y))
            pygame.draw.rect(w, border, (x - 1, y - 1, cw + 2, 39), 1)
            pygame.draw.rect(w, PANEL_BG, (x, y + 26, cw, 11))
            tag = "T" if item.tutorial else "∞" if item.endless else str(item.number)
            font.draw(w, tag, x + 2, y + 28, WHITE if sel else GREY, shadow=None)
            if item.tutorial:
                if self.progress.stars(0):
                    w.blit(self.spr["star"], (x + 20, y + 28))
            elif not item.endless:
                for s in range(3):
                    img = self.spr["star" if s < self.progress.stars(item.number) else "star_empty"]
                    w.blit(img, (x + 9 + s * 8, y + 28))
        self.box(w, 20, 76, 224, 100)
        font.draw(w, self.level_name(lv), WORLD_W // 2, 82, WHITE, 2, "center")
        cx = WORLD_W // 2
        if lv.tutorial:
            font.draw(w, self.t("tutorial_goal"), cx, 104, YELLOW, align="center")
            font.draw(w, self.t("tut_summary"), cx, 120, (200, 190, 220), align="center")
            font.draw(w, self.t("tut_info"), cx, 134, GREY, align="center")
        elif lv.endless:
            font.draw(w, self.t("endless_goal"), cx, 100, YELLOW, align="center")
            rows = self.highscores.rows
            if not rows:
                font.draw(w, self.t("no_scores"), cx, 130, GREY, align="center")
            for i, r in enumerate(rows):
                col, row = divmod(i, 5)
                font.draw(w, f"{i + 1:>2} {r['name'][:7]:<7} {r['score']:>4}", 30 + col * 106, 114 + row * 11,
                          YELLOW if i == 0 else WHITE)
        else:
            font.draw(w, self.t("catch_goal", n=lv.goal), cx, 102, YELLOW, align="center")
            hz = [self.t("bananas")]
            if lv.coconut_every:
                hz.append(self.t("coconuts"))
            if lv.rock_every:
                hz.append(self.t("rocks"))
            if lv.birds:
                hz.append(self.t("birds"))
            if lv.powerups:
                hz.append(self.t("powerups"))
            line, lines = "", []
            for h in hz:   # wrap the hazard list over two lines if needed
                cand = f"{line} + {h}" if line else h
                if font.width(cand) > 210:
                    lines.append(line)
                    cand = h
                line = cand
            lines.append(line)
            for i, ln in enumerate(lines):
                font.draw(w, ln, cx, 116 + i * 11, (200, 190, 220), align="center")
            best = self.progress.best(lv.number)
            font.draw(w, self.t("best", n=best) if best else self.t("not_played"), cx, 146, GREY, align="center")
        font.draw(w, f"{self.t('difficulty')}: {self.t(self.settings['difficulty'])}", cx, 162, GREY, align="center")
        if int(self.time * 2) % 2:
            font.draw(w, self.t("levels_hint"), cx, 186, WHITE, align="center")

    def draw_settings(self, w):
        scene = self.scenes[1]
        scene.draw_back(w, WORLD_W / 2)
        scene.draw_ground(w)
        self.dim(w, 100)
        self.box(w, 24, 12, 216, 172)
        font.draw(w, self.t("settings"), WORLD_W // 2, 20, YELLOW, 2, "center", shadow=(120, 60, 0))
        s = self.settings
        values = {
            "difficulty": self.t(s["difficulty"]),
            "language": self.t("lang_name"),
            "sound": self.t("on" if sfx.enabled else "off"),
            "music": self.t("on" if s["music"] else "off"),
            "control": self.t(self.mode_key),
            "back": "",
        }
        for i, item in enumerate(SETTINGS_MENU):
            y = 44 + i * 18
            sel = i == self.settings_sel
            if sel:
                pygame.draw.rect(w, (70, 56, 100), (32, y - 4, 200, 15))
                font.draw(w, ">", 36, y, YELLOW)
            font.draw(w, self.t(item), 46, y, YELLOW if sel else WHITE)
            font.draw(w, values[item], 226, y, YELLOW if sel else GREY, align="right")
        note = {"easy": "easy_note", "normal": "normal_note", "hard": "hard_note"}[s["difficulty"]]
        font.draw(w, self.t(note), WORLD_W // 2, 152, GREY, align="center")
        font.draw(w, self.t("settings_hint"), WORLD_W // 2, 166, WHITE, align="center")

    def draw_play(self, w, cs):
        lv, m, t = self.level, self.monkey, self.time
        self.scene.draw_back(w, m.x)
        self.scene.draw_ground(w)
        shadow = darker(self.scene.t.ground[0], 40)
        for b in self.bananas:   # landing shadows grow as the banana gets closer
            if not b.carried:
                sw = 3 + int(7 * max(0, b.y) / GROUND_Y)
                pygame.draw.ellipse(w, shadow, (int(b.draw_x) - sw // 2, GROUND_Y - 1, sw, 2))
        for group in (self.rocks, self.bananas, self.powerups, self.birds, self.rollers):
            for obj in group:
                obj.draw(w, self.spr, t)
        m.draw(w, self.spr, shadow)
        if self.slow > 0:   # slow-mo tint
            tint = pygame.Surface((WORLD_W, WORLD_H), pygame.SRCALPHA)
            tint.fill((80, 220, 230, 28))
            w.blit(tint, (0, 0))
        self.fx.draw(w)
        self.draw_hud(w, cs)
        if self.tutorial:
            self.draw_tutorial(w)
        elif self.countdown > 0 and self.state == "PLAY":
            font.draw(w, self.t("level_n", n=lv.number) if not lv.endless else "∞", WORLD_W // 2, 58, WHITE, 1, "center")
            font.draw(w, self.level_name(lv), WORLD_W // 2, 68, YELLOW, 2, "center", shadow=(120, 60, 0))
            msg = self.t("ready") if self.countdown > 0.7 else self.t("go")
            font.draw(w, msg, WORLD_W // 2, 90, WHITE, 3, "center", shadow=(120, 60, 0))

    def draw_hud(self, w, cs):
        bar = pygame.Surface((WORLD_W, 13), pygame.SRCALPHA)
        bar.fill((14, 8, 24, 150))
        w.blit(bar, (0, 0))
        for i in range(self.max_lives):
            w.blit(self.spr["heart" if i < self.lives else "heart_empty"], (4 + i * 8, 3))
        x = 8 + self.max_lives * 8
        w.blit(self.spr["banana"], (x, 2))
        lv = self.level
        if lv.goal:
            font.draw(w, f"{self.caught}/{lv.goal}", x + 15, 3, WHITE)
            bx = x + 50
            pygame.draw.rect(w, INK, (bx, 4, 40, 5))
            pygame.draw.rect(w, YELLOW, (bx + 1, 5, int(38 * min(1, self.caught / lv.goal)), 3))
        else:
            font.draw(w, str(self.caught), x + 15, 3, WHITE)
        mult = min(1 + self.combo // 5, 4)
        if mult > 1:
            font.draw(w, f"X{mult}", x + 95, 3, (255, 150, 60))
        if lv.time_limit:
            secs = math.ceil(self.time_left)
            hurry = secs <= 10 and int(self.time * 4) % 2
            font.draw(w, f"{secs // 60}:{secs % 60:02d}", WORLD_W - 40, 3, RED if hurry else WHITE, align="right")
        font.draw(w, f"{self.score:05d}", WORLD_W - 4, 3, YELLOW, align="right")
        # active power-ups
        y = 16
        for kind, left in (("magnet", self.magnet), ("slow", self.slow)):
            if left > 0:
                w.blit(self.spr["icon"][kind], (4, y))
                pygame.draw.rect(w, INK, (13, y + 2, 26, 4))
                pygame.draw.rect(w, sprites.POWER_COLORS[kind], (14, y + 3, int(24 * left / PowerUp.DURATION[kind]), 2))
                y += 10
        if self.monkey.shield:
            w.blit(self.spr["icon"]["shield"], (4, y))
        # gesture lamps: what the camera sees right now
        if cs is not None and not cs.error:
            lx = WORLD_W - 30
            for i, (txt, on) in enumerate((("<", cs.move == -1), (">", cs.move == 1),
                                            ("J", cs.labels.get("Right") == "PINCH"))):
                pygame.draw.rect(w, (GREEN if i < 2 else YELLOW) if on else (50, 40, 70), (lx + i * 9, 16, 8, 9))
                font.draw(w, txt, lx + i * 9 + 1, 17, INK if on else GREY, shadow=None)

    def draw_tutorial(self, w):
        tut = self.tutorial
        self.box(w, 10, 30, WORLD_W - 20, 40)
        if tut.finished:
            font.draw(w, self.t("tut_done"), WORLD_W // 2, 40, GREEN, align="center")
            if int(self.time * 2) % 2:
                font.draw(w, "OK!", WORLD_W // 2, 52, YELLOW, 2, "center")
            return
        font.draw(w, f"{tut.step + 1}/{len(TUT_STEPS)}", 16, 35, GREY)
        for i in range(len(TUT_STEPS)):   # step dots
            pygame.draw.rect(w, GREEN if i < tut.step else YELLOW if i == tut.step else (60, 48, 84),
                             (WORLD_W - 14 - (len(TUT_STEPS) - i) * 9, 36, 6, 4))
        font.draw(w, self.t(TUT_STEPS[tut.step]), WORLD_W // 2, 46, WHITE, align="center")
        f = tut.progress()
        if f > 0:
            pygame.draw.rect(w, INK, (WORLD_W // 2 - 50, 57, 100, 5))
            pygame.draw.rect(w, GREEN, (WORLD_W // 2 - 49, 58, int(98 * min(1, f)), 3))
        else:
            font.draw(w, self.t("tut_keys"), WORLD_W // 2, 57, GREY, align="center")

    def draw_end(self, w):
        self.dim(w, 110)
        cleared = self.state == "CLEAR"
        lv, cx = self.level, WORLD_W // 2
        self.box(w, 24, 8, 216, 184)
        title = self.t("clear") if cleared else self.t("game_over")
        font.draw(w, title, cx, 15, YELLOW if cleared else RED, 2, "center", shadow=(60, 20, 0))
        if cleared:
            for s in range(3):   # stars pop in one by one
                show = self.end_time > 0.4 + s * 0.35
                img = self.spr["star" if show and s < self.stars_won else "star_empty"]
                w.blit(pygame.transform.scale(img, (14, 14)), (cx - 26 + s * 19, 32))
        else:
            font.draw(w, self.t(self.end_reason), cx, 33, RED, align="center")
            txt = self.t("bananas_n", a=self.caught, b=lv.goal) if lv.goal else self.t("bananas_only", a=self.caught)
            font.draw(w, txt, cx, 43, WHITE, align="center")
        font.draw(w, self.t("score", n=self.score), cx - 4, 54, WHITE, align="right")
        font.draw(w, self.t("best", n=self.progress.best(lv.number)), cx + 4, 54, GREY)
        if self.rank:
            font.draw(w, self.t("new_record", n=self.rank), cx, 65, YELLOW if int(self.time * 3) % 2 else WHITE,
                      align="center")
        # what the AI did during this level
        pygame.draw.line(w, (90, 70, 130), (34, 76), (230, 76))
        font.draw(w, self.t("ai_stats"), cx, 81, YELLOW, align="center")
        s = self.summary
        if s is None:
            font.draw(w, self.t("no_camera_stats"), cx, 100, GREY, align="center")
        else:
            react = f"{s['reaction_s']:.2f}" if s["reaction_s"] is not None else "--"
            lines = [self.t("hand_seen", n=f"{s['hands_seen_pct']:.0f}"), self.t("confident", n=f"{s['sure_pct']:.0f}"),
                     self.t("reaction", n=react), self.t("pinches", n=s["pinches"])]
            for i, ln in enumerate(lines):
                font.draw(w, ln, 34 + (i % 2) * 104, 94 + (i // 2) * 11, WHITE)
            conf = s["avg_conf"]
            font.draw(w, f"CONF L {conf['Left'] * 100:.0f}%  R {conf['Right'] * 100:.0f}%", cx, 118, GREY, align="center")
        pygame.draw.line(w, (90, 70, 130), (34, 130), (230, 130))
        last = cleared and lv.number >= len(LEVELS)
        first = self.t("replay") if last else self.t("next") if cleared else self.t("retry")
        self.buttons(w, [first, self.t("levels")], self.choice, 140, 76)
        font.draw(w, self.t("menu_hint"), cx, 166, GREY, align="center")

    def quit(self, seconds):
        if self.controller:
            self.controller.stop()
            st = self.controller.stats
            n = max(st["frames"], 1)
            report = {
                "date": datetime.now().isoformat(timespec="seconds"),
                "mode": self.t(self.mode_key).lower(), "player": self.player or None,
                "difficulty": self.settings["difficulty"], "seconds": round(seconds, 1),
                "camera_frames": st["frames"], "camera_fps": round(st["frames"] / max(seconds, 1e-6), 1),
                "avg_latency_ms": round(st["latency_sum"] / n, 1),
                "gesture_frames": dict(st["gestures"]), "levels": self.results,
            }
            out = config.ROOT / "reports" / f"play_{datetime.now():%Y%m%d_%H%M%S}.json"
            out.parent.mkdir(exist_ok=True)
            out.write_text(json.dumps(report, indent=2), encoding="utf-8")
            print(json.dumps(report, indent=2))
            print(f"Saved {out}")
        pygame.quit()


if __name__ == "__main__":
    Game(parse_args()).run()
