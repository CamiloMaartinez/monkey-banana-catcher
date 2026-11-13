"""Personal models from a short calibration recorded inside the game.

Same idea as calibrate.py: all team data + the player's frames counted 5x.
Difference: we keep the last 30% of each recorded gesture out of training and
use it to show an honest "before / after" accuracy.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass

import numpy as np

from . import config

# torch and mediapipe are imported inside the functions: the game imports this file
# at startup and should not wait for them.

PLAYER_WEIGHT = 5.0
TEST_SHARE = 0.3
TEAM_ROWS = 8000     # random team rows used per hand: keeps training to a few seconds


@dataclass
class Sample:
    hand: str
    label: str
    points: np.ndarray   # raw (21, 3)
    width: int
    height: int


def split(samples: list[Sample], hand: str):
    """Per label: first 70% of frames -> train, last 30% -> test (frames in a row are alike)."""
    from .landmarks import normalize

    classes = config.CLASSES[hand]
    tr_X, tr_y, te_X, te_y = [], [], [], []
    for label in classes:
        rows = [normalize(s.points, s.width, s.height) for s in samples if s.hand == hand and s.label == label]
        cut = int(len(rows) * (1 - TEST_SHARE))
        tr_X += rows[:cut]
        tr_y += [classes.index(label)] * cut
        te_X += rows[cut:]
        te_y += [classes.index(label)] * (len(rows) - cut)
    as_x = lambda v: np.array(v, dtype=np.float32).reshape(-1, 63)
    return as_x(tr_X), np.array(tr_y, dtype=int), as_x(te_X), np.array(te_y, dtype=int)


def accuracy(predictor, X, y) -> float:
    if len(X) == 0:
        return float("nan")
    p = predictor.predict_proba(X).argmax(1)
    return float((p == y).mean())


def train_player(player: str, session: str, samples: list[Sample], epochs: int = 15, progress=None) -> dict:
    """Train both hands. progress(f) gets 0..1. Returns accuracy before/after per hand."""
    from train import train_mlp   # imported here: train.py lives in the project root

    from .features import AUG_ROTATION, load_hand, make_features
    from .model import GesturePredictor, model_path, save

    args = argparse.Namespace(epochs=epochs, batch=64, lr=1e-3, seed=42)
    results = {}
    for i, hand in enumerate(("Left", "Right")):
        tr_X, tr_y, te_X, te_y = split(samples, hand)
        before = accuracy(GesturePredictor(hand, model_path(hand, player)), te_X, te_y)
        team = load_hand(hand)
        # this calibration is already saved as a CSV inside `team`: drop it and use the split instead
        keep = team.sessions != f"{player}/{session}"
        rng = np.random.default_rng(42)
        others = np.flatnonzero(keep & (team.users != player))
        if len(others) > TEAM_ROWS:   # all of the player's old rows + a random part of the team
            keep = keep & (team.users == player)
            keep[rng.choice(others, TEAM_ROWS, replace=False)] = True
        X = np.concatenate([team.X[keep], tr_X])
        y = np.concatenate([team.y[keep], tr_y])
        w = np.concatenate([np.where(team.users[keep] == player, PLAYER_WEIGHT, 1.0),
                            np.full(len(tr_y), PLAYER_WEIGHT)])
        step = (lambda f, i=i: progress((i + f) / 2)) if progress else None
        model = train_mlp(X, y, len(team.classes), args, 42, hand, AUG_ROTATION[hand], w, progress=step)
        final = config.MODELS_DIR / f"{player}_{hand.lower()}_mlp.pt"
        tmp = save(model, hand, team.classes, hand, make_features(X[:1], hand).shape[1],
                   final.with_suffix(".new.pt"))
        after = accuracy(GesturePredictor(hand, tmp), te_X, te_y)
        kept = after < before   # never replace a model with a worse one
        if kept:
            tmp.unlink()
        else:
            tmp.replace(final)
        results[hand] = {"before": before, "after": after, "kept_old": kept, "test_frames": int(len(te_y))}
    if progress:
        progress(1.0)
    return results
