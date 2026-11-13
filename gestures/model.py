"""The neural network (a small MLP) and helpers to save, load and predict."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import torch
from torch import nn

from . import config
from .features import make_features



class GestureMLP(nn.Module):
    """input_size -> 128 -> 64 -> classes.

    BatchNorm keeps training stable, Dropout reduces overfitting to the
    few people in the dataset.
    """

    def __init__(self, num_classes: int, input_size: int, hidden=(128, 64), dropout: float = 0.3):
        super().__init__()
        layers, size = [], input_size
        for h in hidden:
            layers += [nn.Linear(size, h), nn.BatchNorm1d(h), nn.ReLU(), nn.Dropout(dropout)]
            size = h
        layers.append(nn.Linear(size, num_classes))
        self.net = nn.Sequential(*layers)

    def forward(self, x):
        return self.net(x)


def model_path(hand: str, player: str | None = None) -> Path:
    """Generic model, or the calibrated model of one player if it exists."""
    if player:
        personal = config.MODELS_DIR / f"{player}_{hand.lower()}_mlp.pt"
        if personal.exists():
            return personal
        print(f"No calibrated {hand} model for '{player}', using the generic one.")
    return config.MODELS_DIR / f"{hand.lower()}_mlp.pt"


def save(model: GestureMLP, hand: str, classes: list[str], features: str, input_size: int,
         path: Path | None = None):
    path = path or model_path(hand)
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save({"state_dict": model.state_dict(), "hand": hand, "classes": classes,
                "features": features, "input_size": input_size}, path)
    return path


class GesturePredictor:
    """Loads a trained model and returns (label, confidence) for one hand."""

    def __init__(self, hand: str, path: Path | None = None):
        ckpt = torch.load(path or model_path(hand), map_location="cpu", weights_only=True)
        self.classes = ckpt["classes"]
        self.features = ckpt["features"]
        self.model = GestureMLP(len(self.classes), ckpt["input_size"])
        self.model.load_state_dict(ckpt["state_dict"])
        self.model.eval()

    @torch.no_grad()
    def predict_proba(self, normalized_landmarks: np.ndarray) -> np.ndarray:
        """normalized_landmarks: output of landmarks.normalize(), shape (63,) or (n, 63)."""
        x = torch.as_tensor(make_features(np.atleast_2d(normalized_landmarks), self.features))
        return torch.softmax(self.model(x), dim=1).numpy()

    def predict(self, normalized_landmarks: np.ndarray) -> tuple[str, float]:
        p = self.predict_proba(normalized_landmarks)[0]
        i = int(p.argmax())
        return self.classes[i], float(p[i])
