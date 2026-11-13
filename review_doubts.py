"""Relabel the frames where the network was unsure during play (active learning).

While you play with the camera, the game saves every frame where the network
was below 70% sure in data/doubts/<player>/doubts_<date>.csv. This tool shows
those hands one by one as a skeleton; you press the right gesture key and the
frame goes into the training data. Then retrain: python train.py

Keys (same as capture.py):
    1 TILT_LEFT   2 NEUTRAL   3 TILT_RIGHT     (left hand frames)
    4 OPEN        5 PINCH                      (right hand frames)
    X  not a gesture / bad frame (skip)        BACKSPACE  undo      ESC  save and quit

Usage:
    python review_doubts.py --player camilo
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime

import numpy as np
import pygame

from gestures import config
from gestures.dataset import LANDMARK_COLUMNS, SessionWriter

BONES = [(0, 1), (1, 2), (2, 3), (3, 4), (0, 5), (5, 6), (6, 7), (7, 8), (5, 9), (9, 10), (10, 11), (11, 12),
         (9, 13), (13, 14), (14, 15), (15, 16), (13, 17), (0, 17), (17, 18), (18, 19), (19, 20)]
W, H = 760, 560


def load(player):
    rows = []
    for path in sorted((config.ROOT / "data" / "doubts" / player).glob("doubts_*.csv")):
        with open(path, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                pts = np.array([float(r[c]) for c in LANDMARK_COLUMNS], dtype=np.float32).reshape(21, 3)
                rows.append({"hand": r["hand"], "guess": r["label"], "conf": float(r["hand_score"]),
                             "w": int(r["img_w"]), "h": int(r["img_h"]), "points": pts, "file": path.name})
    return rows


def draw_hand(screen, pts, w, h, box):
    """Skeleton scaled to fit the box, keeping the camera's aspect ratio (image is already mirrored)."""
    x0, y0, bw, bh = box
    p = pts[:, :2] * [w, h]
    lo, hi = p.min(0), p.max(0)
    scale = 0.8 * min(bw / max(hi[0] - lo[0], 1), bh / max(hi[1] - lo[1], 1))
    c = (lo + hi) / 2
    q = [(x0 + bw / 2 + (x - c[0]) * scale, y0 + bh / 2 + (y - c[1]) * scale) for x, y in p]
    for a, b in BONES:
        pygame.draw.line(screen, (200, 190, 220), q[a], q[b], 4)
    for i, (x, y) in enumerate(q):
        color = (255, 214, 60) if i in (4, 8) else (110, 230, 110)
        pygame.draw.circle(screen, color, (int(x), int(y)), 7 if i in (4, 8) else 5)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--player", default="player")
    args = p.parse_args()
    rows = load(args.player)
    if not rows:
        raise SystemExit(f"No unsure frames for '{args.player}' in data/doubts/. Play with the camera first.")
    keys = {getattr(pygame, f"K_{k}"): v for k, v in config.CAPTURE_KEYS.items()}
    pygame.init()
    screen = pygame.display.set_mode((W, H))
    pygame.display.set_caption("Review unsure frames")
    big, small = pygame.font.SysFont("consolas", 28, bold=True), pygame.font.SysFont("consolas", 18)
    answers: list[str | None] = []
    total, i, msg = len(rows), 0, ""
    while i < len(rows):
        r = rows[i]
        for e in pygame.event.get():
            if e.type == pygame.QUIT or (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE):
                rows = rows[:i]
                break
            if e.type != pygame.KEYDOWN:
                continue
            if e.key == pygame.K_BACKSPACE and i > 0:
                i -= 1
                answers.pop()
            elif e.key == pygame.K_x:
                answers.append(None)
                i += 1
            elif e.key in keys:
                hand, label = keys[e.key]
                if hand != r["hand"]:
                    msg = f"This is a {r['hand'].upper()} hand frame: use keys " + ("1-3" if r["hand"] == "Left" else "4-5")
                else:
                    answers.append(label)
                    i += 1
                    msg = ""
        if i >= len(rows):
            break
        r = rows[i]
        screen.fill((22, 16, 34))
        draw_hand(screen, r["points"], r["w"], r["h"], (40, 90, W - 80, H - 200))
        screen.blit(big.render(f"{r['hand'].upper()} HAND   {i + 1} / {len(rows)}", True, (255, 214, 60)), (20, 16))
        screen.blit(small.render(f"Network guessed {r['guess']} ({r['conf'] * 100:.0f}% sure)", True,
                                 (200, 190, 220)), (20, 54))
        hint = "1 TILT_LEFT  2 NEUTRAL  3 TILT_RIGHT" if r["hand"] == "Left" else "4 OPEN  5 PINCH"
        screen.blit(big.render(hint, True, (255, 255, 255)), (20, H - 96))
        screen.blit(small.render("X skip   BACKSPACE undo   ESC save and quit", True, (150, 140, 170)), (20, H - 52))
        if msg:
            screen.blit(small.render(msg, True, (255, 84, 84)), (20, H - 126))
        pygame.display.flip()
        pygame.time.wait(15)
    pygame.quit()

    session = f"review_{datetime.now():%Y%m%d_%H%M}"
    kept = 0
    with SessionWriter(args.player, session) as w:
        for n, (r, label) in enumerate(zip(rows, answers)):
            if label:
                kept += 1
                take = list(config.CAPTURE_KEYS.values()).index((r["hand"], label)) + 1
                w.write(take, n, r["hand"], label, 1.0, r["w"], r["h"], r["points"])
    print(f"Saved {kept} relabelled frames -> data/raw/{args.player}/{session}.csv")
    print("Retrain to use them:  python train.py   (or CALIBRATE in the game)")
    if len(answers) == total:   # everything reviewed: move the doubt files away so they are not shown again
        done = config.ROOT / "data" / "doubts" / args.player / "reviewed"
        done.mkdir(exist_ok=True)
        for name in {r["file"] for r in rows}:
            src = config.ROOT / "data" / "doubts" / args.player / name
            if src.exists():
                src.rename(done / name)


if __name__ == "__main__":
    main()
