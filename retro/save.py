"""Small JSON files the game keeps between runs: settings, stars and the top 10."""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path


def _load(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def _save(path: Path, data):
    try:
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except OSError:
        pass  # never crash the game because a file could not be written


class Settings:
    DEFAULTS = {"difficulty": "normal", "lang": "en", "sound": True, "music": True,
                "control": "network", "player": ""}

    def __init__(self, path: Path):
        self.path = path
        self.data = {**self.DEFAULTS, **_load(path, {})}

    def __getitem__(self, key):
        return self.data[key]

    def __setitem__(self, key, value):
        self.data[key] = value
        _save(self.path, self.data)


class Progress:
    """Best stars and score per level (progress.json)."""

    def __init__(self, path: Path):
        self.path = path
        self.data = _load(path, {})

    def stars(self, level: int) -> int:
        return self.data.get(str(level), {}).get("stars", 0)

    def best(self, level: int) -> int:
        return self.data.get(str(level), {}).get("best", 0)

    def record(self, level: int, stars: int, score: int):
        old = self.data.get(str(level), {})
        self.data[str(level)] = {"stars": max(stars, old.get("stars", 0)), "best": max(score, old.get("best", 0))}
        _save(self.path, self.data)


class HighScores:
    """Top 10 of endless mode (highscores.json)."""

    def __init__(self, path: Path):
        self.path = path
        self.rows = _load(path, [])

    def add(self, name: str, score: int) -> int | None:
        """Returns the rank (1-10) if the score got in, else None."""
        if score <= 0:
            return None
        row = {"name": (name or "PLAYER")[:10].upper(), "score": score, "date": date.today().isoformat()}
        self.rows.append(row)
        self.rows.sort(key=lambda r: -r["score"])
        self.rows = self.rows[:10]
        _save(self.path, self.rows)
        return self.rows.index(row) + 1 if row in self.rows else None
