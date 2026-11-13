"""Shared settings for the whole project (capture, training, game)."""
import sys
from pathlib import Path

# Project folder. In the Windows .exe (build_exe.ps1) it is the folder of the .exe,
# so models/, data/ and the save files sit next to it.
ROOT = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent.parent
MODELS_DIR = ROOT / "models"
RAW_DATA_DIR = ROOT / "data" / "raw"

HAND_MODEL_PATH = MODELS_DIR / "hand_landmarker.task"
HAND_MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
    "hand_landmarker/float16/latest/hand_landmarker.task"
)

# Which gestures each hand can make. The game reads them like this:
#   Left hand  -> movement (TILT_LEFT = A, TILT_RIGHT = D, NEUTRAL = stop)
#   Right hand -> jump     (PINCH = Space, OPEN = nothing)
CLASSES = {
    "Left": ["TILT_LEFT", "NEUTRAL", "TILT_RIGHT"],
    "Right": ["OPEN", "PINCH"],
}

# Keyboard key -> (hand, label) used by the capture tool.
CAPTURE_KEYS = {
    "1": ("Left", "TILT_LEFT"),
    "2": ("Left", "NEUTRAL"),
    "3": ("Left", "TILT_RIGHT"),
    "4": ("Right", "OPEN"),
    "5": ("Right", "PINCH"),
}

NUM_LANDMARKS = 21

# Capture defaults
CAMERA_INDEX = 0
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
COUNTDOWN_SECONDS = 2.0    # time to get the hand in position before recording
FRAMES_PER_TAKE = 150      # about 5 seconds at 30 FPS
MIN_HAND_SCORE = 0.8       # ignore detections where MediaPipe is unsure of the hand side
