"""Hand detection (MediaPipe Tasks API) and landmark normalization.

The same `normalize` function is used for training and for the game,
so the model always sees data prepared in the same way.
"""
from __future__ import annotations

import time
from dataclasses import dataclass

import numpy as np
import mediapipe as mp
from mediapipe.tasks.python import BaseOptions, vision

from . import config

WRIST = 0
MIDDLE_MCP = 9  # base of the middle finger

# Pairs of landmark indices, used only to draw the hand skeleton.
CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),          # thumb
    (0, 5), (5, 6), (6, 7), (7, 8),          # index
    (5, 9), (9, 10), (10, 11), (11, 12),     # middle
    (9, 13), (13, 14), (14, 15), (15, 16),   # ring
    (13, 17), (17, 18), (18, 19), (19, 20),  # pinky
    (0, 17),
]


@dataclass
class HandObservation:
    side: str            # "Left" or "Right" (the person's real hand)
    score: float         # how sure MediaPipe is about the side
    points: np.ndarray   # shape (21, 3): x, y in [0, 1] of the image, z relative depth


class HandTracker:
    """Small wrapper around MediaPipe HandLandmarker for video frames.

    Frames must already be mirrored (selfie view). MediaPipe assumes a
    mirrored image when it decides "Left" or "Right", so after the flip the
    label matches the person's real hand.
    """

    def __init__(self, num_hands: int = 2, model_path=config.HAND_MODEL_PATH):
        if not model_path.exists():
            raise FileNotFoundError(
                f"Hand model not found at {model_path}. Run: python download_model.py"
            )
        options = vision.HandLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=str(model_path)),
            running_mode=vision.RunningMode.VIDEO,
            num_hands=num_hands,
            min_hand_detection_confidence=0.5,
            min_hand_presence_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self._landmarker = vision.HandLandmarker.create_from_options(options)
        self._last_ts = -1

    def detect(self, frame_rgb: np.ndarray) -> list[HandObservation]:
        # VIDEO mode needs strictly increasing timestamps in milliseconds.
        ts = int(time.monotonic() * 1000)
        if ts <= self._last_ts:
            ts = self._last_ts + 1
        self._last_ts = ts

        image = mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(frame_rgb))
        result = self._landmarker.detect_for_video(image, ts)
        return _to_observations(result)

    def close(self):
        self._landmarker.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def detect_image(frame_rgb: np.ndarray, num_hands: int = 2) -> list[HandObservation]:
    """One-off detection on a still image (used by tests)."""
    options = vision.HandLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=str(config.HAND_MODEL_PATH)),
        running_mode=vision.RunningMode.IMAGE,
        num_hands=num_hands,
    )
    with vision.HandLandmarker.create_from_options(options) as landmarker:
        image = mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(frame_rgb))
        return _to_observations(landmarker.detect(image))


def _to_observations(result) -> list[HandObservation]:
    hands = []
    for lms, handedness in zip(result.hand_landmarks, result.handedness):
        best = handedness[0]
        points = np.array([[p.x, p.y, p.z] for p in lms], dtype=np.float32)
        hands.append(HandObservation(side=best.category_name, score=float(best.score), points=points))
    return hands


def normalize(points: np.ndarray, width: int, height: int) -> np.ndarray:
    """Turn raw landmarks into model features (63 numbers).

    1. Use pixel proportions, so a 45 degree tilt stays 45 degrees on any
       camera aspect ratio.
    2. Move the wrist to (0, 0, 0): position in the image does not matter.
    3. Divide by the wrist -> middle-finger-base distance: hand size and
       distance to the camera do not matter.

    We do NOT rotate the hand. The tilt of the index finger IS the signal
    for TILT_LEFT / TILT_RIGHT, so removing rotation would erase it.
    """
    pts = points.astype(np.float32).copy()
    pts[:, 0] *= width
    pts[:, 1] *= height
    pts[:, 2] *= width  # MediaPipe z uses roughly the same scale as x

    pts -= pts[WRIST]
    scale = np.linalg.norm(pts[MIDDLE_MCP, :2])
    if scale < 1e-6:
        scale = 1.0
    pts /= scale
    return pts.reshape(-1)
