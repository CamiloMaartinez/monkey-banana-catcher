"""Extra gestures detected with simple geometry (no training data needed yet).

    Left fist, held 0.6 s   -> pause / resume
    Right hand swipe        -> dash (quick move) to the swipe side

They are rules, like gestures/rules.py. With recorded examples they could be
learned like the other gestures (record them with capture.py and add a class).
"""
from __future__ import annotations

from collections import deque

import numpy as np

# finger: (tip, middle joint, base joint)
FINGERS = {"index": (8, 6, 5), "middle": (12, 10, 9), "ring": (16, 14, 13), "pinky": (20, 18, 17)}
FIST_HOLD = 0.6          # seconds
SWIPE_DIST = 0.30        # wrist movement, as a fraction of the image width ...
SWIPE_TIME = 0.30        # ... within this many seconds (0.22 gave ~3 false swipes/min on recorded data)
SWIPE_COOLDOWN = 0.8


def is_fist(points: np.ndarray, w: int, h: int) -> bool:
    """All four fingers folded: each fingertip is closer to the wrist than its middle joint."""
    p = points[:, :2] * [w, h]
    wrist = p[0]
    return all(np.linalg.norm(p[tip] - wrist) < np.linalg.norm(p[mid] - wrist)
               for tip, mid, _ in FINGERS.values())


class FistHold:
    """Fires once when a fist has been held FIST_HOLD seconds; needs a release before firing again."""

    def __init__(self):
        self.since, self.fired = None, False

    def update(self, fist: bool, t: float) -> bool:
        if not fist:
            self.since, self.fired = None, False
            return False
        if self.since is None:
            self.since = t
        if not self.fired and t - self.since >= FIST_HOLD:
            self.fired = True
            return True
        return False


class Swipe:
    """A fast sideways move of the right wrist. Returns -1 (left), +1 (right) or 0."""

    def __init__(self):
        self.track: deque[tuple[float, float]] = deque()
        self.cooldown_until = 0.0

    def update(self, wrist_x: float | None, t: float) -> int:
        if wrist_x is None:
            self.track.clear()
            return 0
        self.track.append((t, wrist_x))
        while self.track and t - self.track[0][0] > SWIPE_TIME:
            self.track.popleft()
        if t < self.cooldown_until or len(self.track) < 3:
            return 0
        dx = wrist_x - self.track[0][1]
        if abs(dx) >= SWIPE_DIST:
            self.track.clear()
            self.cooldown_until = t + SWIPE_COOLDOWN
            return 1 if dx > 0 else -1
        return 0
