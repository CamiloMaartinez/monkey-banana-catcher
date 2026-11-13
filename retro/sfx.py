"""Chiptune sound effects and background music, synthesised with numpy (no audio files).

If the computer has no audio device the game just runs silent.
"""
from __future__ import annotations

import numpy as np
import pygame

RATE = 22050
_sounds: dict[str, pygame.mixer.Sound] = {}
_tracks: dict[str, pygame.mixer.Sound] = {}
_waves: dict[str, np.ndarray] = {}   # filled by a background thread at start
_channels = 1
_music_channel = None
_current = None
enabled = True        # sound effects on/off
music_on = True       # music on/off


def _wave(freqs, dur, kind="square", vol=0.35):
    n = int(RATE * dur)
    f = np.interp(np.linspace(0, 1, n), np.linspace(0, 1, len(freqs)), freqs)
    phase = 2 * np.pi * np.cumsum(f) / RATE
    if kind == "square":
        s = np.sign(np.sin(phase))
    elif kind == "triangle":
        s = 2 / np.pi * np.arcsin(np.sin(phase))
    else:  # noise
        s = np.random.default_rng(0).uniform(-1, 1, n)
    env = np.minimum(1, np.linspace(8, 0, n))   # quick attack, linear fade
    return s * env * vol


def _notes(freqs, step, kind="square"):
    return np.concatenate([_wave([f, f], step, kind) for f in freqs])


def _to_sound(wave):
    data = (np.clip(wave, -1, 1) * 32767).astype(np.int16)
    if _channels > 1:
        data = np.repeat(data[:, None], _channels, axis=1)
    return pygame.sndarray.make_sound(np.ascontiguousarray(data))


def init():
    global enabled, _channels, _music_channel
    try:
        pygame.mixer.init(RATE, -16, 1, 512)
    except pygame.error:
        enabled = False
        return
    _channels = pygame.mixer.get_init()[2]
    pygame.mixer.set_num_channels(16)
    pygame.mixer.set_reserved(1)
    _music_channel = pygame.mixer.Channel(0)
    raw = {
        "catch": _wave([700, 1400], 0.08),
        "gold": _notes([988, 1319, 1976], 0.06),
        "jump": _wave([260, 620], 0.12, "triangle", 0.5),
        "hit": _wave([200, 60], 0.25, "square", 0.3) + _wave([0, 0], 0.25, "noise", 0.25),
        "miss": _wave([420, 150], 0.2, "triangle", 0.45),
        "select": _wave([880, 880], 0.04),
        "confirm": _notes([660, 990], 0.07),
        "clear": _notes([523, 659, 784, 1047, 784, 1047], 0.09),
        "over": _notes([392, 330, 262, 196], 0.14, "triangle"),
        "warn": _notes([1200, 0, 1200], 0.04),
        "nice": _notes([784, 1175], 0.06),
        "power": _notes([523, 784, 1047, 1568], 0.05),
        "shield": _wave([300, 900], 0.15, "triangle", 0.4),
        "steal": _notes([1500, 1200, 900], 0.05, "triangle"),
        "step": _notes([784, 988, 1175], 0.06),
    }
    for name, wave in raw.items():
        _sounds[name] = _to_sound(wave)


def play(name: str):
    if enabled and name in _sounds:
        _sounds[name].play()


def toggle() -> bool:
    global enabled
    enabled = not enabled and bool(_sounds)
    return enabled


# --- music -----------------------------------------------------------------------
# name -> (seed, key in semitones from C4, minor?)
TRACKS = {"menu": (11, 0, False), "lv1": (1, 2, False), "lv2": (2, 5, False), "lv3": (3, -3, False),
          "lv4": (4, -3, True), "lv5": (5, -5, True), "endless": (6, 0, True), "tutorial": (7, 7, False)}
BPM = 140


def _hz(semi):
    return 261.63 * 2 ** (semi / 12)


def _pulse(freq, n, duty=0.25):
    phase = (np.arange(n) * freq / RATE) % 1.0
    return np.where(phase < duty, 1.0, -1.0)


def _tri(freq, n):
    phase = (np.arange(n) * freq / RATE) % 1.0
    return 4 * np.abs(phase - 0.5) - 1


def make_track(seed, key, minor):
    """8 bars: lead (pulse), bass (triangle), drums (noise). Loops seamlessly."""
    rng = np.random.default_rng(seed)
    step = int(RATE * 60 / BPM / 2)               # an eighth note
    chords = [0, 8, 3, 10] if minor else [0, 7, 9, 5]
    scale = [0, 3, 5, 7, 10, 12, 15] if minor else [0, 2, 4, 7, 9, 12, 14]
    out = np.zeros(step * 64)
    env = np.minimum(1, np.linspace(6, 0, step)) * (np.arange(step) < step * 0.85)
    deg = 2
    for i in range(64):
        a = i * step
        chord = chords[(i // 8) % 4]
        # lead: random walk on the scale, 1 bar in 4 repeats bar 1 so it sounds like a song
        src = i if (i // 8) % 4 != 2 else i - 16
        r = np.random.default_rng(seed * 100 + src % 32)
        if r.random() > 0.25:
            deg = int(np.clip(deg + r.integers(-2, 3), 0, len(scale) - 1))
            f = _hz(key + scale[deg] + (0 if r.random() > 0.2 else 12))
            out[a:a + step] += 0.10 * _pulse(f, step) * env
        # bass
        if i % 8 in (0, 3, 4, 6):
            out[a:a + step] += 0.16 * _tri(_hz(key + chord - 24), step) * env
        # drums
        if i % 4 == 0:   # kick
            n = int(RATE * 0.08)
            f = np.linspace(140, 40, n)
            out[a:a + n] += 0.35 * np.sin(2 * np.pi * np.cumsum(f) / RATE) * np.linspace(1, 0, n)
        if i % 4 == 2:   # snare
            n = int(RATE * 0.06)
            out[a:a + n] += 0.10 * rng.uniform(-1, 1, n) * np.linspace(1, 0, n)
        if i % 2 == 1:   # hi-hat
            n = int(RATE * 0.015)
            out[a:a + n] += 0.04 * np.diff(rng.uniform(-1, 1, n + 1)) * np.linspace(1, 0, n)
    return out / max(1.0, np.abs(out).max() / 0.8)


def preload():
    """Compose all tracks in a background thread so starting a level never stutters."""
    import threading

    def work():
        for name, spec in TRACKS.items():
            _waves.setdefault(name, make_track(*spec))
    if _music_channel is not None:
        threading.Thread(target=work, daemon=True).start()


def music(name: str | None):
    """Start a looping track (None = stop). Calling with the current track does nothing."""
    global _current
    if _music_channel is None or name == _current:
        return
    _current = name
    _music_channel.stop()
    if name is None or not music_on:
        return
    if name not in _tracks:
        wave = _waves.get(name)
        _tracks[name] = _to_sound(wave if wave is not None else make_track(*TRACKS[name]))
    _music_channel.set_volume(0.45)
    _music_channel.play(_tracks[name], loops=-1)


def set_music(on: bool):
    global music_on, _current
    music_on = on
    track, _current = _current, None
    music(track if on else None)
    if not on:
        _current = track   # remember it, so switching back on resumes the right track
        if _music_channel:
            _music_channel.stop()
