"""Create a FAKE dataset from the two hands in two_hands.jpg, only to test train.py.

Usage: python -m tests.make_fake_data <output_folder>
"""
import sys
from pathlib import Path

import cv2
import numpy as np

from gestures.dataset import SessionWriter
from gestures.landmarks import detect_image

HERE = Path(__file__).parent
W, H = 640, 480


def rotate(points, deg):
    px = points[:, :2] * [W, H]
    a = np.radians(deg)
    r = np.array([[np.cos(a), -np.sin(a)], [np.sin(a), np.cos(a)]])
    out = points.copy()
    out[:, :2] = ((px - px[0]) @ r.T + px[0]) / [W, H]
    return out


def upright(points):
    """Rotate so the index finger points straight up."""
    v = (points[8, :2] - points[5, :2]) * [W, H]
    return rotate(points, -np.degrees(np.arctan2(v[0], -v[1])))


def pinch(points):
    out = points.copy()
    out[8] = out[4] + (out[8] - out[4]) * 0.1
    out[7] = (out[6] + out[8]) / 2
    return out


def main(out_dir):
    img = cv2.cvtColor(cv2.imread(str(HERE / "two_hands.jpg")), cv2.COLOR_BGR2RGB)
    base = upright(detect_image(img)[0].points)
    rng = np.random.default_rng(0)
    makers = {
        ("Left", "TILT_LEFT"): lambda p: rotate(p, -rng.uniform(25, 45)),
        ("Left", "NEUTRAL"): lambda p: rotate(p, rng.uniform(-8, 8)),
        ("Left", "TILT_RIGHT"): lambda p: rotate(p, rng.uniform(25, 45)),
        ("Right", "OPEN"): lambda p: rotate(p, rng.uniform(-15, 15)),
        ("Right", "PINCH"): lambda p: rotate(pinch(p), rng.uniform(-15, 15)),
    }
    for user, size in (("ana", 1.0), ("beto", 0.8), ("caro", 1.2)):
        person = base.copy()
        person[:, :2] = person[0, :2] + (person[:, :2] - person[0, :2]) * size
        person[:, :2] += rng.normal(0, 0.004, person[:, :2].shape)  # each person's hand is a bit different
        for session in ("s1", "s2"):
            with SessionWriter(user, session, root=Path(out_dir)) as wr:
                for take, ((hand, label), make) in enumerate(makers.items(), start=1):
                    for frame in range(60):
                        p = make(person) + rng.normal(0, 0.002, person.shape)
                        p[:, :2] += rng.uniform(-0.1, 0.1, 2)
                        wr.write(take, frame, hand, label, 0.95, W, H, p.astype(np.float32))
    print(f"Fake dataset written to {out_dir}")


if __name__ == "__main__":
    main(sys.argv[1])
