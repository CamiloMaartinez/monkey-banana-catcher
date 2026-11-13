"""The levels: look (Theme) + difficulty. Level 0 = tutorial, 6 = endless."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Theme:
    kind: str          # jungle / beach / canyon / night / volcano (decides the scenery shapes)
    sky: tuple         # gradient colours, top -> bottom
    sun: tuple | None  # (colour, x, y, radius)
    clouds: tuple | None  # (light, shade)
    far: tuple         # far hills colour
    near: tuple        # (main, dark) for trees / rocks in front
    ground: tuple      # (top, top_dark, dirt, dirt_dark, speck)
    ambient: str | None  # leaves / gulls / birds / fireflies / embers
    text: tuple = (255, 255, 255)


@dataclass(frozen=True)
class Level:
    number: int
    name: str
    theme: Theme
    goal: int                  # bananas to catch to clear the level
    banana_every: float        # seconds between bananas
    banana_speed: float        # fall speed, world px / s
    coconut_every: float | None
    coconut_speed: float
    rock_every: float | None   # falling rocks (volcano only)
    golden_chance: float       # golden banana = 5 points
    time_limit: float = 60.0   # seconds to reach the goal
    powerups: bool = False     # falling power-up bubbles
    birds: float | None = None  # seconds between banana-stealing birds
    bounce_chance: float = 0.0  # share of coconuts that bounce
    key: str = ""              # i18n key of the name

    @property
    def endless(self) -> bool:
        return self.number == ENDLESS

    @property
    def tutorial(self) -> bool:
        return self.number == TUTORIAL


TUTORIAL, ENDLESS = 0, 6


JUNGLE = Theme(
    "jungle",
    sky=((84, 160, 236), (120, 190, 244), (168, 216, 246), (214, 238, 240)),
    sun=((255, 242, 170), 214, 38, 12), clouds=((255, 255, 255), (204, 224, 240)),
    far=(76, 150, 112), near=((44, 124, 70), (26, 86, 50)),
    ground=((116, 192, 64), (72, 140, 42), (132, 86, 46), (98, 60, 30), (162, 112, 62)),
    ambient="leaves",
)
BEACH = Theme(
    "beach",
    sky=((56, 150, 232), (104, 194, 244), (164, 226, 250), (228, 244, 240)),
    sun=((255, 250, 204), 54, 34, 14), clouds=((255, 255, 255), (210, 232, 246)),
    far=(40, 136, 206), near=((62, 128, 52), (36, 84, 36)),
    ground=((246, 222, 152), (224, 190, 120), (236, 206, 136), (212, 176, 110), (252, 238, 196)),
    ambient="gulls",
)
CANYON = Theme(
    "canyon",
    sky=((64, 36, 104), (164, 68, 112), (238, 118, 82), (255, 190, 104)),
    sun=((255, 232, 150), 132, 86, 20), clouds=((255, 170, 140), (200, 104, 112)),
    far=(156, 72, 82), near=((112, 46, 52), (80, 30, 40)),
    ground=((204, 112, 62), (162, 80, 46), (150, 82, 52), (114, 56, 36), (192, 122, 82)),
    ambient="birds",
)
NIGHT = Theme(
    "night",
    sky=((8, 10, 36), (18, 28, 66), (32, 48, 96), (52, 70, 120)),
    sun=((240, 240, 216), 204, 36, 10), clouds=((64, 74, 116), (44, 54, 92)),
    far=(26, 52, 72), near=((16, 42, 44), (8, 26, 30)),
    ground=((44, 96, 64), (26, 66, 46), (46, 36, 42), (30, 22, 28), (64, 52, 58)),
    ambient="fireflies",
)
VOLCANO = Theme(
    "volcano",
    sky=((38, 10, 22), (88, 20, 26), (160, 50, 30), (222, 102, 42)),
    sun=None, clouds=((92, 72, 72), (62, 46, 52)),
    far=(62, 30, 36), near=((42, 26, 30), (26, 16, 20)),
    ground=((76, 58, 58), (52, 38, 42), (46, 30, 32), (30, 20, 22), (255, 112, 32)),
    ambient="embers",
)

LEVELS = [
    Level(1, "Jungle Morning", JUNGLE, goal=12, banana_every=1.6, banana_speed=44,
          coconut_every=None, coconut_speed=0, rock_every=None, golden_chance=0.06, key="lv1"),
    Level(2, "Sunny Beach", BEACH, goal=18, banana_every=1.4, banana_speed=52,
          coconut_every=5.0, coconut_speed=64, rock_every=None, golden_chance=0.08,
          powerups=True, key="lv2"),
    Level(3, "Sunset Canyon", CANYON, goal=24, banana_every=1.2, banana_speed=62,
          coconut_every=4.0, coconut_speed=80, rock_every=None, golden_chance=0.10,
          powerups=True, birds=9.0, key="lv3"),
    Level(4, "Moonlit Jungle", NIGHT, goal=30, banana_every=1.05, banana_speed=72,
          coconut_every=3.4, coconut_speed=92, rock_every=None, golden_chance=0.12,
          powerups=True, birds=8.0, bounce_chance=0.4, key="lv4"),
    Level(5, "Volcano Peak", VOLCANO, goal=36, banana_every=0.95, banana_speed=80,
          coconut_every=3.8, coconut_speed=98, rock_every=2.6, golden_chance=0.15,
          powerups=True, birds=10.0, bounce_chance=0.5, key="lv5"),
]
TUTORIAL_LEVEL = Level(TUTORIAL, "Tutorial", JUNGLE, goal=0, banana_every=99, banana_speed=30,
                       coconut_every=None, coconut_speed=55, rock_every=None, golden_chance=0,
                       time_limit=0, key="lv_tutorial")
# Endless: starts like level 2 and keeps speeding up; the scenery changes every 15 bananas.
ENDLESS_LEVEL = Level(ENDLESS, "Endless", JUNGLE, goal=0, banana_every=1.5, banana_speed=50,
                      coconut_every=4.5, coconut_speed=70, rock_every=None, golden_chance=0.10,
                      time_limit=0, powerups=True, birds=10.0, bounce_chance=0.3, key="lv_endless")
MENU_LEVELS = [TUTORIAL_LEVEL, *LEVELS, ENDLESS_LEVEL]   # cards in the level menu
