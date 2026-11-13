"""Side panel (full resolution): camera, gesture lamps, raw network output and a live confidence graph."""
from __future__ import annotations

import pygame

from . import PANEL_W, SCREEN_H, font

WHITE, YELLOW, RED, GREEN = (255, 255, 255), (255, 214, 60), (255, 84, 84), (110, 230, 110)
INK, GREY, OFF, LINE = (24, 16, 30), (150, 140, 170), (52, 42, 72), (90, 70, 130)
LEFT_C, RIGHT_C = (110, 230, 110), (255, 214, 60)


def draw_panel(s, x0, cs, t, mode_key, history):
    pygame.draw.rect(s, (22, 16, 34), (x0, 0, PANEL_W, SCREEN_H))
    pygame.draw.line(s, LINE, (x0, 0), (x0, SCREEN_H), 2)
    font.draw(s, t("gesture_control"), x0 + PANEL_W // 2, 10, YELLOW, 2, "center")
    y = 34
    if cs is None:
        font.draw(s, t("keyboard_mode"), x0 + PANEL_W // 2, y, GREY, 2, "center")
        y += 34
        for k, v in (("A / D", "left_move"), ("SPACE", "right_jump"), ("SHIFT", "dash_key"), ("P", "paused"), ("M", "sound"),
                     ("L", "language"), ("ESC", "back")):
            font.draw(s, k, x0 + 10, y, WHITE, 2)
            font.draw(s, t(v).split("  ")[-1], x0 + 96, y, GREY, 2)
            y += 24
        return
    if cs.error:
        line = ""
        for wd in cs.error.split():
            if len(line) + len(wd) > 18:
                font.draw(s, line, x0 + 8, y, RED, 2)
                y, line = y + 20, ""
            line = (line + " " + wd).strip()
        font.draw(s, line, x0 + 8, y, RED, 2)
        return
    if cs.frame is not None:
        fh, fw = cs.frame.shape[:2]
        pygame.draw.rect(s, LINE, (x0 + 3, y - 1, fw + 2, fh + 2), 1)
        s.blit(pygame.image.frombuffer(cs.frame.tobytes(), (fw, fh), "RGB"), (x0 + 4, y))
        y += fh + 8
    # left hand: three direction lamps
    font.draw(s, t("left_move"), x0 + 8, y, WHITE, 2)
    y += 20
    for i, (label, mv) in enumerate((("<", -1), (t("stop"), 0), (">", 1))):
        bx = x0 + 8 + i * 78
        on = cs.move == mv
        pygame.draw.rect(s, GREEN if on else OFF, (bx, y, 72, 22))
        font.draw(s, label, bx + 36, y + 4, INK if on else GREY, 2, "center", shadow=None)
    y = raw_line(s, x0, y + 26, cs, "Left", t)
    # right hand: jump lamp
    font.draw(s, t("right_jump"), x0 + 8, y, WHITE, 2)
    y += 20
    on = cs.labels.get("Right") == "PINCH"
    pygame.draw.rect(s, YELLOW if on else OFF, (x0 + 8, y, 232, 22))
    font.draw(s, t("pinch_jump") if on else t("OPEN"), x0 + 124, y + 4, INK if on else GREY, 2, "center", shadow=None)
    y = raw_line(s, x0, y + 26, cs, "Right", t)
    # live confidence graph
    font.draw(s, t("confidence"), x0 + 8, y + 2, GREY)
    gy, gh, gw = y + 12, 46, 232
    pygame.draw.rect(s, (14, 10, 22), (x0 + 8, gy, gw, gh))
    ty = gy + gh - int(gh * 0.7)
    for x in range(x0 + 8, x0 + 8 + gw, 6):   # 70% threshold, dashed
        pygame.draw.line(s, (90, 60, 60), (x, ty), (x + 2, ty))
    for series, color in ((history.left, LEFT_C), (history.right, RIGHT_C)):
        n = len(series)
        pts = [(x0 + 8 + int(i * (gw - 1) / (n - 1)), gy + gh - 1 - int(v * (gh - 2))) for i, v in enumerate(series)]
        pygame.draw.lines(s, color, False, pts, 2)
    # extra gestures (rules, gestures/extra.py)
    y = gy + gh + 10
    font.draw(s, t("panel_fist"), x0 + 8, y, YELLOW if cs.fist else GREY, 2)
    font.draw(s, t("panel_swipe"), x0 + 8, y + 20, GREY, 2)
    if cs.doubts:
        font.draw(s, t("doubts_n", n=cs.doubts), x0 + 8, y + 42, GREY)
    font.draw(s, f"{cs.fps:4.1f} FPS  {cs.latency_ms:3.0f} MS", x0 + 8, SCREEN_H - 38, GREY, 2)
    font.draw(s, t("model", m=t(mode_key)), x0 + 8, SCREEN_H - 18, GREY, 2)


def raw_line(s, x0, y, cs, hand, t):
    """Raw network output (before smoothing): label + confidence bar."""
    label, conf = cs.raw.get(hand, ("NO HAND", 0.0))
    font.draw(s, t(label), x0 + 8, y, (200, 190, 220), 2)
    pygame.draw.rect(s, OFF, (x0 + 150, y + 2, 90, 10))
    pygame.draw.rect(s, GREEN if conf >= 0.7 else (230, 150, 60), (x0 + 150, y + 2, int(90 * conf), 10))
    return y + 22
