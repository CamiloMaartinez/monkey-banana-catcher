"""Rule-based baseline (the approach of the original TikTok project).

No learning: fixed thresholds on the landmarks. We compare the neural
network against this, and keep it as a backup for the demo.
"""
from __future__ import annotations

import numpy as np

TILT_DEG = 20.0      # index tilt beyond this angle = TILT
PINCH_RATIO = 0.35   # thumb-index distance / palm size below this = PINCH


def _px(points: np.ndarray, w: int, h: int) -> np.ndarray:
    return points[:, :2] * [w, h]


def index_angle(points: np.ndarray, w: int, h: int) -> float:
    """Angle of the index finger (base -> tip) from vertical, in degrees.

    Negative = tilted to the person's left (in the mirrored image), positive = right.
    """
    p = _px(points, w, h)
    v = p[8] - p[5]
    return float(np.degrees(np.arctan2(v[0], -v[1])))


def left_hand_rule(points: np.ndarray, w: int, h: int) -> str:
    a = index_angle(points, w, h)
    if a < -TILT_DEG:
        return "TILT_LEFT"
    if a > TILT_DEG:
        return "TILT_RIGHT"
    return "NEUTRAL"


def right_hand_rule(points: np.ndarray, w: int, h: int) -> str:
    p = _px(points, w, h)
    palm = np.linalg.norm(p[9] - p[0]) + 1e-6
    return "PINCH" if np.linalg.norm(p[4] - p[8]) / palm < PINCH_RATIO else "OPEN"


RULES = {"Left": left_hand_rule, "Right": right_hand_rule}
