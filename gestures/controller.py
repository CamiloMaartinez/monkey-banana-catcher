"""Real-time gesture control: camera -> MediaPipe -> model -> smoothed game commands.

Runs in a background thread so the game never waits for the camera.
The game only reads `controller.state()`.
"""
from __future__ import annotations

import threading
import time
from collections import Counter, deque
from dataclasses import dataclass, field

import cv2
import numpy as np

from datetime import datetime

from . import config
from .dataset import SessionWriter
from .extra import FistHold, Swipe, is_fist
from .landmarks import HandTracker, normalize
from .model import GesturePredictor, model_path
from .rules import RULES

MOVE = {"TILT_LEFT": -1, "NEUTRAL": 0, "TILT_RIGHT": 1}
SURE = 0.7
# When a hand is not visible we assume the "do nothing" gesture.
IDLE = {"Left": "NEUTRAL", "Right": "OPEN"}


@dataclass
class ControlState:
    move: int = 0                 # -1 left, 0 stop, +1 right
    jump: bool = False            # True once per new pinch (consumed by the game)
    labels: dict = field(default_factory=lambda: dict(IDLE))   # smoothed label per hand
    raw: dict = field(default_factory=dict)                    # last raw (label, confidence) per hand
    fps: float = 0.0
    latency_ms: float = 0.0       # camera frame -> command
    frame: np.ndarray | None = None  # small RGB preview for the game window
    error: str = ""
    points: dict = field(default_factory=dict)  # raw landmarks (21, 3) per visible hand (for calibration)
    size: tuple = (0, 0)          # camera frame width, height
    seq: int = 0                  # increases once per processed camera frame
    pause: bool = False           # True once per left fist held 0.6 s (consumed by the game)
    dash: int = 0                 # -1 / +1 once per right-hand swipe (consumed by the game)
    fist: bool = False            # left fist visible right now (for the panel)
    doubts: int = 0               # unsure frames saved this session


class DoubtLog:
    """Saves frames where the network was unsure (< 70%), to relabel them later with review_doubts.py.

    Goes to data/doubts/<player>/doubts_<date>.csv, NOT data/raw, so the guesses never reach
    training by accident. The label column holds the network's guess, hand_score its confidence.
    """
    EVERY = 0.3      # seconds between saved frames per hand
    MAX = 1500       # per session

    def __init__(self, player: str | None):
        self.player = player or "player"
        self.session = f"doubts_{datetime.now():%Y%m%d_%H%M}"
        self.writer, self.count, self.last = None, 0, {}

    def add(self, hand, label, conf, w, h, points, t):
        if conf >= SURE or self.count >= self.MAX or t - self.last.get(hand, -1) < self.EVERY:
            return
        if self.writer is None:
            self.writer = SessionWriter(self.player, self.session, config.ROOT / "data" / "doubts")
        self.last[hand] = t
        self.count += 1
        self.writer.write(0, self.count, hand, label, conf, w, h, points)
        if self.count % 20 == 0:
            self.writer.flush()

    def close(self):
        if self.writer:
            self.writer.close()


class Smoother:
    """Majority vote over the last `window` confident predictions.

    A single wrong frame cannot change the command: the new gesture must win
    the vote first. Low-confidence predictions count as the idle gesture.
    """

    def __init__(self, idle: str, window: int = 5, min_conf: float = SURE):
        self.idle, self.min_conf = idle, min_conf
        self.history: deque[str] = deque([idle] * window, maxlen=window)

    def update(self, label: str | None, conf: float) -> str:
        self.history.append(label if label is not None and conf >= self.min_conf else self.idle)
        return Counter(self.history).most_common(1)[0][0]


class GestureController:
    def __init__(self, camera: int = config.CAMERA_INDEX, use_rules: bool = False,
                 player: str | None = None, preview_width: int = 240, log_doubts: bool = True):
        self.camera, self.use_rules, self.preview_width = camera, use_rules, preview_width
        self.player = player
        self.predictors = {}
        if not use_rules:
            self.load_models(player)
        self.smoothers = {h: Smoother(IDLE[h]) for h in ("Left", "Right")}
        self.fist_hold, self.swipe = FistHold(), Swipe()
        self.doubts = DoubtLog(player) if log_doubts else None
        self._state = ControlState()
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self.stats = {"frames": 0, "latency_sum": 0.0, "gestures": Counter()}

    # --- public API used by the game -------------------------------------
    def load_models(self, player: str | None = None):
        """(Re)load the networks: the player's calibrated ones if they exist, else the generic ones."""
        self.player = player
        self.predictors = {hand: GesturePredictor(hand, model_path(hand, player)) for hand in ("Left", "Right")}

    def set_rules(self, use_rules: bool):
        if not use_rules and not self.predictors:
            self.load_models(self.player)
        self.use_rules = use_rules

    def start(self):
        self._thread.start()
        return self

    def stop(self):
        self._stop.set()
        self._thread.join(timeout=2)

    def state(self) -> ControlState:
        """Copy of the latest state. Reading it consumes the jump event."""
        with self._lock:
            s = ControlState(**vars(self._state))
            self._state.jump, self._state.pause, self._state.dash = False, False, 0
        return s

    # --- worker thread ----------------------------------------------------
    def classify(self, hand: str, points: np.ndarray, w: int, h: int) -> tuple[str, float]:
        if self.use_rules:
            return RULES[hand](points, w, h), 1.0
        return self.predictors[hand].predict(normalize(points, w, h))

    def _run(self):
        cap = cv2.VideoCapture(self.camera)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.FRAME_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.FRAME_HEIGHT)
        if not cap.isOpened():
            with self._lock:
                self._state.error = f"Camera {self.camera} not available"
            return
        fps, last = 0.0, time.perf_counter()
        prev_right = IDLE["Right"]
        seq = 0
        with HandTracker() as tracker:
            while not self._stop.is_set():
                ok, frame = cap.read()
                if not ok:
                    continue
                t0 = time.perf_counter()
                frame = cv2.flip(frame, 1)
                h, w = frame.shape[:2]
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                seen = {}
                for obs in tracker.detect(rgb):
                    if obs.score >= config.MIN_HAND_SCORE and obs.side not in seen:
                        seen[obs.side] = obs
                raw, labels = {}, {}
                for hand in ("Left", "Right"):
                    if hand in seen:
                        label, conf = self.classify(hand, seen[hand].points, w, h)
                        raw[hand] = (label, conf)
                        if self.doubts and not self.use_rules:
                            self.doubts.add(hand, label, conf, w, h, seen[hand].points, t0)
                        labels[hand] = self.smoothers[hand].update(label, conf)
                        _draw(rgb, seen[hand].points)
                    else:
                        labels[hand] = self.smoothers[hand].update(None, 0.0)

                jump_now = labels["Right"] == "PINCH" and prev_right != "PINCH"  # only on a NEW pinch
                fist = "Left" in seen and is_fist(seen["Left"].points, w, h)
                pause_now = self.fist_hold.update(fist, t0)
                open_right = "Right" in seen and raw["Right"][0] != "PINCH"
                dash_now = self.swipe.update(float(seen["Right"].points[0, 0]) if open_right else None, t0)
                prev_right = labels["Right"]
                now = time.perf_counter()
                latency = (now - t0) * 1000
                fps = 0.9 * fps + 0.1 / max(now - last, 1e-6)
                last = now
                scale = self.preview_width / w
                preview = cv2.resize(rgb, (self.preview_width, int(h * scale)))

                seq += 1
                self.stats["frames"] += 1
                self.stats["latency_sum"] += latency
                self.stats["gestures"].update(labels.values())
                with self._lock:
                    s = self._state
                    s.move = MOVE[labels["Left"]]
                    s.jump = s.jump or jump_now
                    s.labels, s.raw = labels, raw
                    s.fps, s.latency_ms, s.frame = fps, latency, preview
                    s.points = {hand: obs.points.copy() for hand, obs in seen.items()}
                    s.size, s.seq = (w, h), seq
                    s.pause = s.pause or pause_now
                    s.dash = dash_now or s.dash
                    s.fist = fist
                    s.doubts = self.doubts.count if self.doubts else 0
        cap.release()
        if self.doubts:
            self.doubts.close()


def _draw(rgb, points):
    h, w = rgb.shape[:2]
    for x, y, _ in points:
        cv2.circle(rgb, (int(x * w), int(y * h)), 3, (80, 220, 80), -1)
