"""Checks that work without a webcam.  Run: python -m tests.test_pipeline"""
import csv
import tempfile
from pathlib import Path

import cv2
import numpy as np

from gestures import config
from gestures.dataset import COLUMNS, SessionWriter
from gestures.landmarks import detect_image, normalize

HERE = Path(__file__).parent


def test_detects_two_hands():
    img = cv2.cvtColor(cv2.imread(str(HERE / "two_hands.jpg")), cv2.COLOR_BGR2RGB)
    hands = detect_image(img)
    assert len(hands) == 2, f"expected 2 hands, got {len(hands)}"
    assert {h.side for h in hands} == {"Left", "Right"}
    assert all(h.points.shape == (21, 3) for h in hands)
    return img, hands


def test_normalize_ignores_position_and_size(points):
    base = normalize(points, 640, 480)
    moved = points.copy()
    moved[:, 0] += 0.1
    moved[:, 1] -= 0.05
    assert np.allclose(normalize(moved, 640, 480), base, atol=1e-4)
    # zoom around the wrist (hand closer to the camera)
    bigger = points.copy()
    bigger[:, :2] = points[0, :2] + (points[:, :2] - points[0, :2]) * 1.5
    bigger[:, 2] *= 1.5
    assert np.allclose(normalize(bigger, 640, 480), base, atol=1e-4)
    assert base.shape == (63,) and np.allclose(base[:3], 0)


def test_normalize_keeps_tilt(points):
    """Rotating the hand must change the features (tilt is the signal)."""
    w, h = 640, 480
    px = points[:, :2] * [w, h]
    a = np.radians(30)
    rot = np.array([[np.cos(a), -np.sin(a)], [np.sin(a), np.cos(a)]])
    rotated = points.copy()
    rotated[:, :2] = ((px - px[0]) @ rot.T + px[0]) / [w, h]
    assert not np.allclose(normalize(rotated, w, h), normalize(points, w, h), atol=1e-2)


def test_writer_roundtrip(obs):
    with tempfile.TemporaryDirectory() as tmp:
        with SessionWriter("tester", "s1", root=Path(tmp)) as wr:
            wr.write(1, 0, obs.side, config.CLASSES[obs.side][0], obs.score, 640, 480, obs.points)
        with open(Path(tmp) / "tester" / "s1.csv", newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 1 and list(rows[0].keys()) == COLUMNS
        back = np.array([float(rows[0][c]) for c in COLUMNS[len(COLUMNS) - 63:]]).reshape(21, 3)
        assert np.allclose(back, obs.points, atol=1e-5)


def test_smoother_ignores_single_wrong_frames():
    from gestures.controller import Smoother
    sm = Smoother("NEUTRAL", window=5, min_conf=0.7)
    out = [sm.update(l, c) for l, c in [("TILT_LEFT", 0.9), ("NEUTRAL", 0.9), ("TILT_LEFT", 0.9),
                                         ("TILT_LEFT", 0.95), ("TILT_LEFT", 0.4)]]
    assert out[0] == "NEUTRAL"          # one frame is not enough
    assert out[3] == "TILT_LEFT"        # 3 of the last 5 frames agree


if __name__ == "__main__":
    _, hands = test_detects_two_hands()
    test_normalize_ignores_position_and_size(hands[0].points)
    test_normalize_keeps_tilt(hands[0].points)
    test_writer_roundtrip(hands[0])
    test_smoother_ignores_single_wrong_frames()
    print("All checks passed.")
