"""Summarize everything under data/raw/ and warn about problems.

Usage:
    python check_dataset.py
"""
import csv
from collections import Counter, defaultdict

import numpy as np

from gestures import config
from gestures.dataset import COLUMNS, LANDMARK_COLUMNS
from gestures.rules import RULES

TARGET_PER_USER_LABEL = 450  # 3 takes x 150 frames
# A take is suspicious when most of its frames look like a CONFLICTING gesture.
# A small tilt that looks NEUTRAL is fine (the model should learn it), a tilt in
# the wrong direction is not.
CONFLICTS = {
    "TILT_LEFT": {"TILT_RIGHT"}, "TILT_RIGHT": {"TILT_LEFT"},
    "NEUTRAL": {"TILT_LEFT", "TILT_RIGHT"}, "OPEN": {"PINCH"}, "PINCH": {"OPEN"},
}


def main():
    files = sorted(config.RAW_DATA_DIR.glob("*/*.csv"))
    if not files:
        print(f"No CSV files found in {config.RAW_DATA_DIR}")
        return

    per_user = defaultdict(Counter)
    sessions = defaultdict(set)
    take_checks = defaultdict(list)  # (user, session, take, label) -> [rule agrees?]
    problems = []
    for path in files:
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames != COLUMNS:
                problems.append(f"{path}: unexpected columns")
                continue
            for r in reader:
                per_user[r["user"]][r["label"]] += 1
                sessions[r["user"]].add(r["session"])
                expected = [h for h, labels in config.CLASSES.items() if r["label"] in labels]
                if expected != [r["hand"]]:
                    problems.append(f"{path}: label {r['label']} saved for hand {r['hand']}")
                    continue
                pts = np.array([float(r[c]) for c in LANDMARK_COLUMNS]).reshape(21, 3)
                guess = RULES[r["hand"]](pts, int(r["img_w"]), int(r["img_h"]))
                take_checks[(r["user"], r["session"], int(r["take"]), r["label"])].append(guess in CONFLICTS[r["label"]])

    labels = [lab for labs in config.CLASSES.values() for lab in labs]
    header = f"{'user':<12}{'sessions':>9}" + "".join(f"{lab:>12}" for lab in labels)
    print(header)
    print("-" * len(header))
    totals = Counter()
    for user in sorted(per_user):
        c = per_user[user]
        totals.update(c)
        print(f"{user:<12}{len(sessions[user]):>9}" + "".join(f"{c[lab]:>12}" for lab in labels))
        for lab in labels:
            if c[lab] < TARGET_PER_USER_LABEL:
                problems.append(f"{user}: {lab} has {c[lab]} rows (target {TARGET_PER_USER_LABEL})")
    print("-" * len(header))
    print(f"{'TOTAL':<12}{'':>9}" + "".join(f"{totals[lab]:>12}" for lab in labels))

    for (user, session, take, label), conflict in sorted(take_checks.items()):
        share = sum(conflict) / len(conflict)
        if share > 0.5:
            problems.append(
                f"{user}/{session} take {take} ({label}): {share:.0%} of frames look like a different gesture. "
                f"Wrong gesture? Delete it with: python delete_take.py --user {user} --session {session} --take {take}"
            )

    if len(per_user) < 3:
        problems.append(f"Only {len(per_user)} user(s). Need 3 to test on an unseen person.")
    print()
    if problems:
        print("To fix:")
        for p in sorted(set(problems)):
            print(f"  - {p}")
    else:
        print("Dataset looks complete.")


if __name__ == "__main__":
    main()
