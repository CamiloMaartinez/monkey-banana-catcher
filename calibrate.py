"""Adapt the models to one player (calibration).

1. The player records ONE take of each gesture (about 30 s in total):
       python capture.py --user ana --session cal
   (press 1..5, SPACE for each)
2. Train personal models (all team data + the player's data counted 5x):
       python calibrate.py --user ana
3. Play with them:
       python game.py --player ana

Why: every hand is a bit different. In our tests, 1 take per gesture of the
new player raised right-hand accuracy from 93% to 97%.
"""
import argparse

import numpy as np

from gestures import config
from gestures.features import AUG_ROTATION, load_hand, make_features
from gestures.model import save
from train import train_mlp

PLAYER_WEIGHT = 5.0


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--user", required=True)
    p.add_argument("--epochs", type=int, default=40)
    args = p.parse_args()
    args.batch, args.lr, args.seed = 64, 1e-3, 42

    for hand in ("Left", "Right"):
        d = load_hand(hand)
        mine = d.users == args.user
        if not mine.any():
            raise SystemExit(f"No {hand}-hand data for '{args.user}'. Record first: "
                             f"python capture.py --user {args.user} --session cal")
        missing = set(d.classes) - {d.classes[i] for i in np.unique(d.y[mine])}
        if missing:
            print(f"  Warning: '{args.user}' has no takes for {sorted(missing)}; using team data for those.")
        weights = np.where(mine, PLAYER_WEIGHT, 1.0)
        model = train_mlp(d.X, d.y, len(d.classes), args, args.seed, hand, AUG_ROTATION[hand], weights)
        path = save(model, hand, d.classes, hand, make_features(d.X[:1], hand).shape[1],
                    config.MODELS_DIR / f"{args.user}_{hand.lower()}_mlp.pt")
        print(f"{hand}: {mine.sum()} rows of {args.user} + {(~mine).sum()} team rows -> {path}")
    print(f"Done. Play with: python game.py --player {args.user}")


if __name__ == "__main__":
    main()
