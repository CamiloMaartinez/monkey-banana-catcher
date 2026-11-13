"""CSV layout for the raw dataset.

One CSV file per person and session: data/raw/<user>/<session>.csv
One row = one hand in one frame.
We store RAW landmarks (not normalized). Normalization happens when we
train, so we can change it later without recording again.
"""
from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

import numpy as np

from . import config

META_COLUMNS = [
    "timestamp", "user", "session", "take", "frame",
    "hand", "label", "hand_score", "img_w", "img_h",
]
LANDMARK_COLUMNS = [f"{axis}{i}" for i in range(config.NUM_LANDMARKS) for axis in ("x", "y", "z")]
COLUMNS = META_COLUMNS + LANDMARK_COLUMNS


class SessionWriter:
    """Appends rows to the CSV of one user + session."""

    def __init__(self, user: str, session: str, root: Path = config.RAW_DATA_DIR):
        self.path = root / user / f"{session}.csv"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        new_file = not self.path.exists()
        self._file = open(self.path, "a", newline="", encoding="utf-8")
        self._writer = csv.writer(self._file)
        if new_file:
            self._writer.writerow(COLUMNS)
        self.user = user
        self.session = session

    def write(self, take: int, frame: int, hand: str, label: str, hand_score: float,
              img_w: int, img_h: int, points: np.ndarray):
        row = [
            datetime.now().isoformat(timespec="milliseconds"),
            self.user, self.session, take, frame,
            hand, label, f"{hand_score:.4f}", img_w, img_h,
        ]
        row += [f"{v:.6f}" for v in points.reshape(-1)]
        self._writer.writerow(row)

    def flush(self):
        self._file.flush()

    def close(self):
        self._file.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def next_take_number(path: Path) -> int:
    """Continue take numbering if the session file already exists."""
    if not path.exists():
        return 1
    with open(path, newline="", encoding="utf-8") as f:
        takes = [int(r["take"]) for r in csv.DictReader(f)]
    return max(takes, default=0) + 1
