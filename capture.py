"""Record labeled hand landmarks from the webcam.

Usage:
    python capture.py --user camilo --session s1

Keys (in the camera window):
    1..5   choose the gesture to record (shown on screen)
    SPACE  start a take: short countdown, then records FRAMES_PER_TAKE frames
    X      cancel the take that is running (nothing is saved)
    Z      delete the last saved take of this session
    Q/ESC  quit
"""
from __future__ import annotations

import argparse
import csv
import re
import time
from collections import Counter

import cv2

from gestures import config
from gestures.dataset import COLUMNS, SessionWriter, next_take_number
from gestures.landmarks import CONNECTIONS, HandTracker

GREEN, RED, YELLOW, WHITE, GRAY = (80, 200, 80), (60, 60, 230), (0, 220, 255), (255, 255, 255), (150, 150, 150)


def parse_args():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--user", required=True, help="person name, lowercase, no spaces (e.g. camilo)")
    p.add_argument("--session", required=True, help="session id (e.g. s1). Use a new one per lighting/place")
    p.add_argument("--camera", type=int, default=config.CAMERA_INDEX)
    p.add_argument("--frames", type=int, default=config.FRAMES_PER_TAKE)
    args = p.parse_args()
    for name in ("user", "session"):
        if not re.fullmatch(r"[a-z0-9_-]+", getattr(args, name)):
            p.error(f"--{name} must use only lowercase letters, numbers, - or _")
    return args


def draw_hand(frame, points, color):
    h, w = frame.shape[:2]
    xy = [(int(x * w), int(y * h)) for x, y, _ in points]
    for a, b in CONNECTIONS:
        cv2.line(frame, xy[a], xy[b], color, 2)
    for p in xy:
        cv2.circle(frame, p, 3, WHITE, -1)
    return xy[0]


def put(frame, text, org, color=WHITE, scale=0.6):
    """Text on a dark box, so it stays readable on any background."""
    font, thick = cv2.FONT_HERSHEY_SIMPLEX, 1
    (tw, th), base = cv2.getTextSize(text, font, scale, thick)
    x, y = org
    cv2.rectangle(frame, (x - 3, y - th - 4), (x + tw + 3, y + base + 2), (0, 0, 0), -1)
    cv2.putText(frame, text, org, font, scale, color, thick, cv2.LINE_AA)


def count_labels(path):
    if not path.exists():
        return Counter()
    with open(path, newline="", encoding="utf-8") as f:
        return Counter(r["label"] for r in csv.DictReader(f))


def delete_last_take(path):
    """Rewrite the CSV without its highest take number. Returns the removed take or None."""
    if not path.exists():
        return None
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        return None
    last = max(int(r["take"]) for r in rows)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(r for r in rows if int(r["take"]) != last)
    return last


def main():
    args = parse_args()
    cap = cv2.VideoCapture(args.camera)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.FRAME_HEIGHT)
    if not cap.isOpened():
        raise SystemExit(f"Could not open camera {args.camera}. Try --camera 1")

    writer = SessionWriter(args.user, args.session)
    take = next_take_number(writer.path)
    counts = count_labels(writer.path)
    hand, label = config.CAPTURE_KEYS["1"]
    state, state_start, buffer = "IDLE", 0.0, []
    message, message_until = "", 0.0
    fps, last_t = 0.0, time.monotonic()

    print(f"Saving to {writer.path}")
    with HandTracker() as tracker:
        while True:
            ok, frame = cap.read()
            if not ok:
                print("Camera frame not received, stopping.")
                break
            frame = cv2.flip(frame, 1)  # selfie view: MediaPipe "Left" = your real left hand
            img_h, img_w = frame.shape[:2]
            hands = tracker.detect(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

            now = time.monotonic()
            fps = 0.9 * fps + 0.1 * (1.0 / max(now - last_t, 1e-6))
            last_t = now

            target = None
            for obs in hands:
                is_target = obs.side == hand and obs.score >= config.MIN_HAND_SCORE
                wrist = draw_hand(frame, obs.points, GREEN if is_target else GRAY)
                put(frame, f"{obs.side} {obs.score:.2f}", (wrist[0] - 30, wrist[1] + 25), WHITE, 0.5)
                if is_target and target is None:
                    target = obs

            # --- state machine: IDLE -> COUNTDOWN -> RECORDING -> IDLE ---
            if state == "COUNTDOWN" and now - state_start >= config.COUNTDOWN_SECONDS:
                state, buffer = "RECORDING", []
            if state == "RECORDING":
                if target is not None:
                    buffer.append((len(buffer), target))
                if len(buffer) >= args.frames:
                    for i, obs in buffer:
                        writer.write(take, i, hand, label, obs.score, img_w, img_h, obs.points)
                    writer.flush()
                    counts[label] += len(buffer)
                    message, message_until = f"Saved take {take}: {len(buffer)} frames of {label}", now + 2.5
                    take += 1
                    state = "IDLE"

            # --- overlay ---
            put(frame, f"user={args.user} session={args.session}  FPS {fps:4.1f}", (10, 22))
            put(frame, f"Gesture: {label} ({hand} hand)", (10, 50), YELLOW, 0.75)
            if state == "IDLE":
                put(frame, "SPACE record | 1-5 gesture | Z undo take | Q quit", (10, 78), WHITE, 0.5)
            elif state == "COUNTDOWN":
                left = config.COUNTDOWN_SECONDS - (now - state_start)
                put(frame, f"Get ready... {left:.1f}", (10, 85), YELLOW, 0.9)
            else:
                put(frame, f"REC {len(buffer)}/{args.frames}  (X cancel)", (10, 85), RED, 0.9)
                if target is None:
                    put(frame, f"{hand} hand not visible: frame skipped", (10, 115), RED, 0.6)
                cv2.circle(frame, (img_w - 25, 25), 10, RED, -1)
            y = img_h - 15
            for key, (h_, lab) in reversed(list(config.CAPTURE_KEYS.items())):
                put(frame, f"[{key}] {lab:<10} {counts[lab]:5d}", (10, y), YELLOW if lab == label else WHITE, 0.5)
                y -= 20
            if now < message_until:
                put(frame, message, (10, 140), GREEN, 0.6)

            cv2.imshow("Gesture capture", frame)
            key = cv2.waitKey(1) & 0xFF
            ch = chr(key) if key < 128 else ""

            if key in (27, ord("q")):
                break
            if state == "IDLE":
                if ch in config.CAPTURE_KEYS:
                    hand, label = config.CAPTURE_KEYS[ch]
                elif key == ord(" "):
                    state, state_start = "COUNTDOWN", now
                elif ch == "z":
                    writer.close()  # close before rewriting the file, then reopen
                    removed = delete_last_take(writer.path)
                    writer = SessionWriter(args.user, args.session)
                    counts = count_labels(writer.path)
                    if removed is not None:
                        take = removed
                    message = f"Deleted take {removed}" if removed else "Nothing to delete"
                    message_until = now + 2.5
            elif ch == "x":
                state = "IDLE"
                message, message_until = "Take cancelled", now + 2.0

    writer.close()
    cap.release()
    cv2.destroyAllWindows()
    print(f"Done. Rows per label in this session: {dict(counts)}")


if __name__ == "__main__":
    main()
