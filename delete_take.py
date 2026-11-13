"""Delete one take from a session CSV (for example a take recorded with the wrong gesture).

Usage:
    python delete_take.py --user camilo --session s1 --take 1
"""
import argparse
import csv

from gestures import config
from gestures.dataset import COLUMNS


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--user", required=True)
    p.add_argument("--session", required=True)
    p.add_argument("--take", required=True, type=int)
    args = p.parse_args()

    path = config.RAW_DATA_DIR / args.user / f"{args.session}.csv"
    if not path.exists():
        raise SystemExit(f"Not found: {path}")
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    keep = [r for r in rows if int(r["take"]) != args.take]
    if len(keep) == len(rows):
        raise SystemExit(f"Take {args.take} not found in {path}")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(keep)
    print(f"Deleted take {args.take} ({len(rows) - len(keep)} rows) from {path}")


if __name__ == "__main__":
    main()
