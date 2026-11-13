"""Train one MLP per hand and compare it with the rule-based baseline.

Usage:
    python train.py                 # both hands
    python train.py --hand Left     # only the left hand

What it does, for each hand:
1. Evaluation: "leave one group out". The group is the person when there
   are 2+ people, otherwise the session. We never split
   frames randomly: frames of the same take are almost identical, so a
   random split would give a fake, too-high accuracy.
2. Prints accuracy and a confusion matrix for the MLP and for the rules.
3. Trains the final model on ALL the data and saves it to models/.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import torch
from torch import nn

from gestures import config
from gestures.features import AUG_ROTATION, HandData, augment, load_hand, make_features
from gestures.model import GestureMLP, save
from gestures.rules import RULES

REPORTS_DIR = config.ROOT / "reports"


def parse_args():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--hand", choices=["Left", "Right", "both"], default="both")
    p.add_argument("--epochs", type=int, default=40)
    p.add_argument("--batch", type=int, default=64)
    p.add_argument("--lr", type=float, default=1e-3)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--features", choices=["hand", "raw"], default="hand",
                   help="hand = index direction (left) / fingertip distances (right); raw = all 63 numbers")
    p.add_argument("--data", default=str(config.RAW_DATA_DIR), help="folder with <user>/<session>.csv files")
    return p.parse_args()


def train_mlp(X, y, num_classes, args, seed, kind, rotation, sample_weight=None, progress=None):
    """X = normalized landmarks (n, 63). kind = feature type ("raw", "Left", "Right")."""
    torch.manual_seed(seed)
    rng = np.random.default_rng(seed)
    model = GestureMLP(num_classes, make_features(X[:1], kind).shape[1])
    opt = torch.optim.Adam(model.parameters(), lr=args.lr, weight_decay=1e-4)
    # Class weights: a class with fewer rows counts more, so no class is ignored.
    counts = np.bincount(y, minlength=num_classes).astype(np.float32)
    weights = counts.sum() / np.maximum(counts, 1) / num_classes
    loss_fn = nn.CrossEntropyLoss(weight=torch.tensor(weights), reduction="none")
    sw = torch.as_tensor(np.ones(len(y)) if sample_weight is None else sample_weight, dtype=torch.float32)
    yt = torch.as_tensor(y)

    model.train()
    for epoch in range(args.epochs):
        if progress:
            progress(epoch / args.epochs)   # used by the in-game calibration bar
        Xa = torch.as_tensor(make_features(augment(X, rng, max_rot_deg=rotation), kind))  # new variation every epoch
        order = torch.as_tensor(rng.permutation(len(X)))
        for i in range(0, len(X), args.batch):
            idx = order[i:i + args.batch]
            if len(idx) < 2:  # BatchNorm needs at least 2 rows
                continue
            opt.zero_grad()
            loss = (loss_fn(model(Xa[idx]), yt[idx]) * sw[idx]).mean()
            loss.backward()
            opt.step()
    model.eval()
    return model


@torch.no_grad()
def predict(model, X, kind):
    return model(torch.as_tensor(make_features(X, kind))).argmax(1).numpy()


def confusion(y_true, y_pred, n):
    m = np.zeros((n, n), dtype=int)
    for t, p in zip(y_true, y_pred):
        m[t, p] += 1
    return m


def format_confusion(m, classes):
    w = max(len("true \\ pred"), *(len(c) for c in classes)) + 2
    lines = ["true \\ pred".ljust(w) + "".join(c[:10].rjust(12) for c in classes)]
    for c, row in zip(classes, m):
        lines.append(c.ljust(w) + "".join(str(v).rjust(12) for v in row))
    return "\n".join(lines)


def pick_groups(d: HandData):
    for name, groups in (("person", d.users), ("session", d.sessions)):
        if len(np.unique(groups)) >= 2:
            return name, groups
    return None, None


def evaluate_hand(d: HandData, args):
    n = len(d.classes)
    kind = d.hand if args.features == "hand" else "raw"
    rotation = AUG_ROTATION[d.hand]
    group_name, groups = pick_groups(d)
    rule = RULES[d.hand]
    rule_pred = np.array([d.classes.index(rule(p, w, h)) for p, (w, h) in zip(d.raw, d.sizes)])

    report = {"hand": d.hand, "features": kind, "rows": int(len(d.y)), "classes": d.classes,
              "rows_per_class": {c: int((d.y == i).sum()) for i, c in enumerate(d.classes)}}
    print(f"\n=== {d.hand} hand: {len(d.y)} rows, {report['rows_per_class']} ===")

    if group_name is None:
        print("Only one session: nothing unseen to test on. Record a 2nd session to get test numbers.")
    else:
        mlp_pred = np.empty_like(d.y)
        per_group = {}
        for g in np.unique(groups):
            test = groups == g
            if len(np.unique(d.y[~test])) < n:
                print(f"  skip {g}: training part is missing a class")
                mlp_pred[test] = -1
                continue
            model = train_mlp(d.X[~test], d.y[~test], n, args, args.seed, kind, rotation)
            mlp_pred[test] = predict(model, d.X[test], kind)
            per_group[g] = {
                "mlp": float((mlp_pred[test] == d.y[test]).mean()),
                "rules": float((rule_pred[test] == d.y[test]).mean()),
            }
            print(f"  test on {group_name} {g:<20} MLP {per_group[g]['mlp']:.3f}   rules {per_group[g]['rules']:.3f}")
        ok = mlp_pred >= 0
        mlp_acc = float((mlp_pred[ok] == d.y[ok]).mean()) if ok.any() else float("nan")
        rule_acc = float((rule_pred[ok] == d.y[ok]).mean()) if ok.any() else float("nan")
        cm_mlp = confusion(d.y[ok], mlp_pred[ok], n)
        cm_rules = confusion(d.y[ok], rule_pred[ok], n)
        print(f"\n  Leave-one-{group_name}-out accuracy:  MLP {mlp_acc:.3f}   rules {rule_acc:.3f}")
        print("\n  MLP confusion matrix:\n" + format_confusion(cm_mlp, d.classes))
        print("\n  Rules confusion matrix:\n" + format_confusion(cm_rules, d.classes))
        report.update({"eval_group": group_name, "per_group": per_group,
                       "mlp_accuracy": mlp_acc, "rules_accuracy": rule_acc,
                       "mlp_confusion": cm_mlp.tolist(), "rules_confusion": cm_rules.tolist()})

    final = train_mlp(d.X, d.y, n, args, args.seed, kind, rotation)
    path = save(final, d.hand, d.classes, kind, make_features(d.X[:1], kind).shape[1])
    print(f"\n  Final model trained on all rows -> {path}")
    return report


def main():
    args = parse_args()
    hands = ["Left", "Right"] if args.hand == "both" else [args.hand]
    REPORTS_DIR.mkdir(exist_ok=True)
    for hand in hands:
        report = evaluate_hand(load_hand(hand, Path(args.data)), args)
        out = REPORTS_DIR / f"{hand.lower()}_report.json"
        out.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"  Report -> {out}")


if __name__ == "__main__":
    main()
