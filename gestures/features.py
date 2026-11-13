"""Load the raw CSVs and turn them into model inputs (X) and labels (y)."""
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from . import config
from .dataset import LANDMARK_COLUMNS
from .landmarks import normalize


@dataclass
class HandData:
    hand: str
    classes: list[str]
    X: np.ndarray        # (n, 63) normalized features
    y: np.ndarray        # (n,) class index
    users: np.ndarray    # (n,) user name of each row
    sessions: np.ndarray # (n,) "user/session" of each row
    takes: np.ndarray    # (n,) "user/session/take" of each row
    raw: np.ndarray      # (n, 21, 3) raw landmarks (for the rule baseline)
    sizes: np.ndarray    # (n, 2) image width, height


def load_hand(hand: str, root: Path = config.RAW_DATA_DIR) -> HandData:
    classes = config.CLASSES[hand]
    X, y, users, sessions, takes, raw, sizes = [], [], [], [], [], [], []
    for path in sorted(root.glob("*/*.csv")):
        with open(path, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if r["hand"] != hand or r["label"] not in classes:
                    continue
                pts = np.array([float(r[c]) for c in LANDMARK_COLUMNS], dtype=np.float32).reshape(21, 3)
                w, h = int(r["img_w"]), int(r["img_h"])
                X.append(normalize(pts, w, h))
                y.append(classes.index(r["label"]))
                users.append(r["user"])
                sessions.append(f"{r['user']}/{r['session']}")
                takes.append(f"{r['user']}/{r['session']}/{r['take']}")
                raw.append(pts)
                sizes.append((w, h))
    if not X:
        raise SystemExit(f"No rows for the {hand} hand in {root}")
    return HandData(
        hand=hand, classes=classes,
        X=np.stack(X), y=np.array(y), users=np.array(users),
        sessions=np.array(sessions), takes=np.array(takes),
        raw=np.stack(raw), sizes=np.array(sizes),
    )


def augment(X: np.ndarray, rng: np.random.Generator, max_rot_deg: float = 8.0,
            scale: float = 0.08, noise: float = 0.02) -> np.ndarray:
    """Create slightly different copies of normalized hands.

    Small rotation only (8 degrees): a big rotation would turn NEUTRAL into a TILT.
    """
    pts = X.reshape(-1, 21, 3).copy()
    n = len(pts)
    a = np.radians(rng.uniform(-max_rot_deg, max_rot_deg, n))
    cos, sin = np.cos(a), np.sin(a)
    x, yy = pts[:, :, 0].copy(), pts[:, :, 1].copy()
    pts[:, :, 0] = cos[:, None] * x - sin[:, None] * yy
    pts[:, :, 1] = sin[:, None] * x + cos[:, None] * yy
    pts *= rng.uniform(1 - scale, 1 + scale, (n, 1, 1))
    pts += rng.normal(0, noise, pts.shape)
    return pts.reshape(n, -1).astype(np.float32)


# ---------------------------------------------------------------------------
# Hand-specific features
#
# Experiment (reports/experiments-2026-11-04.md): with only 3 people, an MLP on
# the raw 63 numbers learns each person's hand shape and fails on a new person.
# Giving it only what matters for each gesture generalizes much better.
# ---------------------------------------------------------------------------

def _unit(v: np.ndarray) -> np.ndarray:
    return v / (np.linalg.norm(v, axis=-1, keepdims=True) + 1e-6)


def index_features(P: np.ndarray) -> np.ndarray:
    """Left hand: direction of the index finger segments (8 numbers)."""
    xy = P[:, :, :2]
    return np.concatenate([
        _unit(xy[:, 8] - xy[:, 5]), _unit(xy[:, 8] - xy[:, 6]),
        _unit(xy[:, 7] - xy[:, 5]), _unit(xy[:, 6] - xy[:, 5]),
    ], axis=1)


def pinch_features(P: np.ndarray) -> np.ndarray:
    """Right hand: fingertip distances divided by palm size (10 numbers)."""
    xy = P[:, :, :2]
    palm = np.linalg.norm(xy[:, 9] - xy[:, 0], axis=1, keepdims=True) + 1e-6
    pairs = [(4, 8), (4, 7), (3, 8), (4, 6), (4, 12), (8, 12), (4, 5), (8, 5), (12, 9)]
    f = [np.linalg.norm(xy[:, a] - xy[:, b], axis=1, keepdims=True) / palm for a, b in pairs]
    f.append(np.linalg.norm(P[:, 4] - P[:, 8], axis=1, keepdims=True) / palm)  # 3D thumb-index
    return np.concatenate(f, axis=1)


FEATURES = {
    "raw": lambda P: P.reshape(len(P), -1),
    "Left": index_features,
    "Right": pinch_features,
}
# Rotation used by augment(): small for the left hand (rotation changes the tilt
# label), large for the right hand (a pinch is a pinch at any angle).
AUG_ROTATION = {"Left": 8.0, "Right": 30.0}


def make_features(X63: np.ndarray, kind: str) -> np.ndarray:
    """kind = "raw", "Left" or "Right". X63 = normalized landmarks (n, 63)."""
    return FEATURES[kind](np.asarray(X63, dtype=np.float32).reshape(-1, 21, 3)).astype(np.float32)
