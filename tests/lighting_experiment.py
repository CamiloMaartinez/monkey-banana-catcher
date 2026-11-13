# Run from the project folder: python -m tests.lighting_experiment
"""Does training with the new sessions help on unseen new-lighting sessions?
For each new session X: model A = old sessions only; model B = everything except X. Test both on X."""
import sys, argparse
sys.path.insert(0, ".")
import numpy as np
from pathlib import Path
from gestures import config
from gestures.features import AUG_ROTATION, load_hand
from gestures.rules import RULES
import train
args = argparse.Namespace(epochs=40, batch=64, lr=1e-3, seed=42)
OLD = {("camilo","s1"),("jehis","s1"),("jehis","s2"),("jehis","s3"),("maria","s1"),("maria","s2"),("maria","s3")}
NEW = [("jehis","s4"),("jehis","s5"),("jehis","s1luz"),("maria","s4"),("maria","s1luz")]
for hand in ("Left","Right"):
    d = load_hand(hand, config.RAW_DATA_DIR)
    n = len(d.classes); keys = [tuple(s.split("/")) for s in d.sessions]
    old = np.array([k in OLD for k in keys])
    mA = train.train_mlp(d.X[old], d.y[old], n, args, 42, hand, AUG_ROTATION[hand])
    print(f"\n{hand}: test session        old-data model   +new-data model   rules")
    for u, s in NEW:
        test = np.array([k == (u, s) for k in keys])
        mB = train.train_mlp(d.X[~test], d.y[~test], n, args, 42, hand, AUG_ROTATION[hand])
        a = (train.predict(mA, d.X[test], hand) == d.y[test]).mean()
        b = (train.predict(mB, d.X[test], hand) == d.y[test]).mean()
        r = np.mean([d.classes.index(RULES[hand](p, w, h)) == y for p, (w, h), y in zip(d.raw[test], d.sizes[test], d.y[test])])
        print(f"  {u}/{s:8s} ({test.sum():5d} rows)   {a:6.3f}           {b:6.3f}          {r:6.3f}")
