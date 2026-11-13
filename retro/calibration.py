"""In-game calibration: record each gesture for a few seconds, train a personal model, show before/after."""
from __future__ import annotations

import math
import threading
from datetime import datetime

import pygame

from gestures import config
from gestures.dataset import SessionWriter
from gestures.personal import Sample, train_player

from . import WORLD_W, font
from .scenery import darker

STEPS = [("Left", "TILT_LEFT"), ("Left", "NEUTRAL"), ("Left", "TILT_RIGHT"), ("Right", "OPEN"), ("Right", "PINCH")]
SYMBOL = {"TILT_LEFT": "<", "NEUTRAL": "!", "TILT_RIGHT": ">", "OPEN": "O", "PINCH": "."}
FRAMES = 90          # frames per gesture (about 3 s at 30 FPS)
READY_TIME = 2.0
WHITE, YELLOW, GREY, RED, GREEN = (255, 255, 255), (255, 214, 60), (150, 140, 170), (255, 84, 84), (110, 230, 110)


class Calibration:
    def __init__(self, text, controller, name: str):
        self.t, self.controller = text, controller
        self.name = (name or "")[:10].lower()
        self.stage = "NAME" if controller else "NOCAM"
        self.step, self.timer, self.last_seq = 0, 0.0, -1
        self.samples: list[Sample] = []
        self.count = 0
        self.progress, self.results, self.error = 0.0, None, ""
        self.session = f"cal_{datetime.now():%Y%m%d_%H%M}"
        self.done = False      # True when the player leaves the screen

    # --- input + logic -------------------------------------------------------
    def update(self, dt, events, cs, confirm, back) -> str | None:
        """Returns "trained" once a new model is ready, "exit" to leave, else None."""
        if back and self.stage != "TRAIN":
            return "exit"
        if self.stage == "NOCAM":
            return "exit" if confirm else None
        if self.stage == "NAME":
            for e in events:
                if e.type == pygame.KEYDOWN:
                    if e.key == pygame.K_BACKSPACE:
                        self.name = self.name[:-1]
                    elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        confirm = True
                    elif e.unicode and (e.unicode.isalnum()) and len(self.name) < 10:
                        self.name += e.unicode.lower()
            if confirm:   # ENTER, SPACE or a pinch
                self.name = self.name or "player"
                self.stage, self.timer = "READY", READY_TIME
            return None
        if self.stage == "READY":
            self.timer -= dt
            if self.timer <= 0:
                self.stage, self.count = "RECORD", 0
            return None
        if self.stage == "RECORD":
            hand, label = STEPS[self.step]
            if cs and cs.seq != self.last_seq and hand in cs.points:
                self.last_seq = cs.seq
                w, h = cs.size
                self.samples.append(Sample(hand, label, cs.points[hand], w, h))
                self.count += 1
            if self.count >= FRAMES:
                self.step += 1
                if self.step < len(STEPS):
                    self.stage, self.timer = "READY", READY_TIME
                else:
                    self.save_csv()
                    self.start_training()
            return None
        if self.stage == "TRAIN":
            if self.results is not None:
                self.stage = "DONE"
                return "trained"
            if self.error:
                self.stage = "ERROR"
            return None
        if self.stage in ("DONE", "ERROR") and confirm:
            return "exit"
        return None

    def save_csv(self):
        """Keep the frames in the dataset (data/raw/<name>/cal_<date>.csv) so train.py can use them too."""
        with SessionWriter(self.name, self.session) as w:
            frame = {}
            for s in self.samples:
                take = STEPS.index((s.hand, s.label)) + 1
                frame[take] = frame.get(take, 0) + 1
                w.write(take, frame[take], s.hand, s.label, 1.0, s.width, s.height, s.points)

    def start_training(self):
        self.stage = "TRAIN"

        def work():
            try:
                self.results = train_player(self.name, self.session, self.samples, progress=self.set_progress)
            except Exception as exc:   # show it on screen instead of crashing the game
                self.error = str(exc)[:60]
        threading.Thread(target=work, daemon=True).start()

    def set_progress(self, f):
        self.progress = f

    # --- drawing -----------------------------------------------------------------
    def draw(self, w, time, box):
        t = self.t
        box(w, 14, 14, WORLD_W - 28, 172)
        font.draw(w, t("cal_title"), WORLD_W // 2, 22, YELLOW, 2, "center", shadow=(120, 60, 0))
        cx = WORLD_W // 2
        if self.stage == "NOCAM":
            font.draw(w, t("cal_need_camera"), cx, 90, RED, align="center")
            font.draw(w, t("cal_continue"), cx, 150, GREY, align="center")
            return
        if self.stage == "NAME":
            font.draw(w, t("cal_name"), cx, 50, WHITE, align="center")
            name = self.name.upper() + ("_" if int(time * 2) % 2 else " ")
            pygame.draw.rect(w, (20, 14, 30), (cx - 70, 68, 140, 24))
            font.draw(w, name, cx, 73, YELLOW, 2, "center")
            font.draw(w, t("cal_intro"), cx, 110, GREY, align="center")
            return
        if self.stage in ("READY", "RECORD"):
            hand, label = STEPS[self.step]
            font.draw(w, f"{self.step + 1}/{len(STEPS)}", cx, 44, GREY, align="center")
            font.draw(w, t(f"cal_{label}"), cx, 56, WHITE, align="center")
            self.draw_gesture(w, label, cx, 100, time)
            if self.stage == "READY":
                font.draw(w, t("cal_get_ready"), cx, 140, YELLOW, align="center")
                font.draw(w, str(math.ceil(self.timer)), cx, 152, YELLOW, 2, "center")
            else:
                cs_hint = t("cal_hold") if self.count else t("cal_show_hand", hand=t(hand.lower()))
                font.draw(w, cs_hint, cx, 140, GREEN if self.count else RED, align="center")
                self.bar(w, cx - 80, 156, 160, self.count / FRAMES, GREEN)
            return
        if self.stage == "TRAIN":
            font.draw(w, t("cal_training"), cx, 70, WHITE, align="center")
            font.draw(w, t("cal_training2"), cx, 84, GREY, align="center")
            self.bar(w, cx - 80, 110, 160, self.progress, YELLOW)
            for i in range(8):   # spinner
                a = time * 4 + i * math.pi / 4
                c = YELLOW if i == 7 else darker(YELLOW, 160 - i * 20)
                pygame.draw.rect(w, c, (cx + int(math.cos(a) * 10) - 1, 140 + int(math.sin(a) * 10) - 1, 3, 3))
            return
        if self.stage == "ERROR":
            font.draw(w, t("cal_failed", e=""), cx, 70, RED, align="center")
            font.draw(w, self.error.upper()[:40], cx, 84, RED, align="center")
            font.draw(w, t("cal_continue"), cx, 160, GREY, align="center")
            return
        # DONE
        font.draw(w, t("cal_done"), cx, 46, GREEN, align="center")
        font.draw(w, t("cal_before_after"), cx + 30, 66, GREY, align="center")
        for i, hand in enumerate(("Left", "Right")):
            r = self.results[hand]
            y = 78 + i * 26
            font.draw(w, t("cal_hand_l" if hand == "Left" else "cal_hand_r"), 40, y + 3, WHITE)
            for j, key in enumerate(("before", "after")):
                v = r[key]
                txt = "--" if v != v else f"{v * 100:.0f}%"
                color = WHITE if key == "before" else GREY if r.get("kept_old") else GREEN
                font.draw(w, txt, cx - 6 + j * 72, y, color, 2, "center")
            if r.get("kept_old"):
                font.draw(w, t("cal_kept"), cx + 66, y + 16, GREY, align="center")
        font.draw(w, t("cal_note"), cx, 134, GREY, align="center")
        font.draw(w, t("player", name=self.name.upper()), cx, 146, YELLOW, align="center")
        if int(time * 2) % 2:
            font.draw(w, t("cal_continue"), cx, 162, WHITE, align="center")

    @staticmethod
    def bar(w, x, y, width, f, color):
        pygame.draw.rect(w, (20, 14, 30), (x, y, width, 8))
        pygame.draw.rect(w, color, (x + 1, y + 1, int((width - 2) * max(0, min(1, f))), 6))

    @staticmethod
    def draw_gesture(w, label, cx, cy, time):
        """Simple pixel picture of the gesture: a finger for the left hand, two fingertips for the right."""
        col, dark = (240, 200, 150), (150, 100, 60)
        if label in ("TILT_LEFT", "NEUTRAL", "TILT_RIGHT"):
            ang = {"TILT_LEFT": -35, "NEUTRAL": 0, "TILT_RIGHT": 35}[label] + math.sin(time * 3) * 3
            pygame.draw.rect(w, dark, (cx - 11, cy + 6, 22, 14))          # fist
            pygame.draw.rect(w, col, (cx - 10, cy + 7, 20, 12))
            a = math.radians(ang)
            for k in range(22):                                           # index finger
                x, y = cx + math.sin(a) * k, cy + 6 - math.cos(a) * k
                pygame.draw.rect(w, dark, (int(x) - 3, int(y) - 1, 6, 3))
                pygame.draw.rect(w, col, (int(x) - 2, int(y) - 1, 4, 2))
        else:
            gap = 10 if label == "OPEN" else max(0, int(2 + math.sin(time * 6) * 1))
            for dx, length in ((-gap // 2 - 3, 18), (gap // 2 + 3, 14)):   # index and thumb tips
                pygame.draw.rect(w, dark, (cx + dx - 3, cy - length + 10, 6, length))
                pygame.draw.rect(w, col, (cx + dx - 2, cy - length + 11, 4, length - 2))
            pygame.draw.rect(w, dark, (cx - 14, cy + 8, 28, 12))
            pygame.draw.rect(w, col, (cx - 13, cy + 9, 26, 10))
