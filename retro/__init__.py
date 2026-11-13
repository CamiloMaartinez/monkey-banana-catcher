"""Retro pixel-art look for the game.

The world is drawn on a small 264 x 200 surface and scaled x3 with
nearest-neighbour, so every pixel stays sharp (the classic 16-bit look).
"""

WORLD_W, WORLD_H = 264, 200   # logical pixels
GROUND_Y = 176                # y of the ground surface
SCALE = 3                     # 264 x 200 -> 792 x 600 on screen
PANEL_W = 248                 # gesture panel on the right, full resolution
SCREEN_W, SCREEN_H = WORLD_W * SCALE + PANEL_W, WORLD_H * SCALE
