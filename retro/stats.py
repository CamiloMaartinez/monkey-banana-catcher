"""What the AI did during one level: shown on the end screen and saved in the play report."""
from __future__ import annotations

from collections import deque


class AIStats:
    SURE = 0.7   # same threshold the smoother uses

    def __init__(self):
        self.frames = 0
        self.seen = {"Left": 0, "Right": 0}
        self.sure = {"Left": 0, "Right": 0}
        self.conf_sum = {"Left": 0.0, "Right": 0.0}
        self.pinches = 0
        self.reactions: list[float] = []
        self.last_seq = -1

    def frame(self, cs):
        """Count one camera frame (the game runs faster than the camera, so skip repeats)."""
        if cs is None or cs.error or cs.seq == self.last_seq:
            return
        self.last_seq = cs.seq
        self.frames += 1
        for hand, (_, conf) in cs.raw.items():
            self.seen[hand] += 1
            self.conf_sum[hand] += conf
            self.sure[hand] += conf >= self.SURE

    def summary(self) -> dict | None:
        if self.frames == 0:
            return None
        seen = sum(self.seen.values())
        return {
            "camera_frames": self.frames,
            "hands_seen_pct": round(100 * seen / (2 * self.frames), 1),
            "sure_pct": round(100 * sum(self.sure.values()) / max(seen, 1), 1),
            "avg_conf": {h: round(self.conf_sum[h] / max(self.seen[h], 1), 3) for h in self.seen},
            "pinches": self.pinches,
            "reaction_s": round(sum(self.reactions) / len(self.reactions), 2) if self.reactions else None,
        }


class ConfidenceHistory:
    """Last few seconds of raw network confidence per hand, for the live graph."""

    def __init__(self, size=120):
        self.left = deque([0.0] * size, maxlen=size)
        self.right = deque([0.0] * size, maxlen=size)
        self.last_seq = -1

    def add(self, cs):
        if cs is None or cs.seq == self.last_seq:
            return
        self.last_seq = cs.seq
        self.left.append(cs.raw.get("Left", ("", 0.0))[1])
        self.right.append(cs.raw.get("Right", ("", 0.0))[1])
