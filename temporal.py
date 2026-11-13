"""Temporal model experiment: does looking at the last 8 frames beat one frame + voting?

Compared on the same unseen person (leave-one-person-out):
    MLP (1 frame)        what the network sees, no smoothing
    MLP + vote 3 of 5    what the game uses today (gestures/controller.py Smoother)
    GRU (8 frames)       a small recurrent network that reads a window of 8 frames

To test like a real game, each test person's takes are joined one after another
into a long "stream", so the gesture changes from time to time. We measure:
    accuracy      % of frames with the right gesture
    flicker       wrong extra label changes per 100 frames (lower = steadier control)
    delay         frames after a real gesture change until the output follows it

Usage:
    python temporal.py            # writes reports/evaluation/temporal.md, .json and .png
"""
from __future__ import annotations

import argparse
import json
import time
from collections import Counter, deque

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import torch  # noqa: E402
from torch import nn  # noqa: E402

from gestures import config  # noqa: E402
from gestures.features import AUG_ROTATION, augment, load_hand, make_features  # noqa: E402
from train import train_mlp  # noqa: E402

OUT = config.ROOT / "reports" / "evaluation"
WINDOW = 8
SURE = 0.7
FPS = 30
IDLE = {"Left": "NEUTRAL", "Right": "OPEN"}   # same as gestures/controller.py


class GestureGRU(nn.Module):
    """features of 8 frames -> GRU(32) -> gesture."""

    def __init__(self, n_features, n_classes, hidden=32):
        super().__init__()
        self.gru = nn.GRU(n_features, hidden, batch_first=True)
        self.head = nn.Sequential(nn.Dropout(0.2), nn.Linear(hidden, n_classes))

    def forward(self, x):          # x: (batch, frames, features)
        _, h = self.gru(x)
        return self.head(h[-1])


def take_slices(d, idx):
    """Rows of each take, in recording order."""
    out = []
    for t in dict.fromkeys(d.takes[idx]):
        rows = idx[d.takes[idx] == t]
        out.append(rows)
    return out


def windows(rows_list):
    """All windows of WINDOW consecutive frames inside each take."""
    X, y_idx = [], []
    for rows in rows_list:
        for end in range(WINDOW, len(rows) + 1):
            X.append(rows[end - WINDOW:end])
            y_idx.append(rows[end - 1])
    return np.array(X), np.array(y_idx)


def train_gru(d, train_idx, epochs, seed):
    torch.manual_seed(seed)
    rng = np.random.default_rng(seed)
    hand, n = d.hand, len(d.classes)
    win, last = windows(take_slices(d, train_idx))
    model = GestureGRU(make_features(d.X[:1], hand).shape[1], n)
    opt = torch.optim.Adam(model.parameters(), lr=2e-3, weight_decay=1e-4)
    counts = np.bincount(d.y[train_idx], minlength=n).astype(np.float32)
    loss_fn = nn.CrossEntropyLoss(weight=torch.tensor(counts.sum() / np.maximum(counts, 1) / n))
    y = torch.as_tensor(d.y[last])
    for _ in range(epochs):
        # one random rotation/scale per frame, new every epoch (same augmentation as the MLP)
        Xa = make_features(augment(d.X, rng, max_rot_deg=AUG_ROTATION[hand]), hand)
        Xw = torch.as_tensor(Xa[win])
        order = rng.permutation(len(win))
        model.train()
        for i in range(0, len(order), 128):
            b = order[i:i + 128]
            opt.zero_grad()
            loss_fn(model(Xw[b]), y[b]).backward()
            opt.step()
    model.eval()
    return model


def stream(d, test_idx, rng):
    """Join the test person's takes in random order: one long 'game session'."""
    takes = take_slices(d, test_idx)
    order = rng.permutation(len(takes))
    return np.concatenate([takes[i] for i in order])


@torch.no_grad()
def run_gru(model, feats):
    """Sliding window over the stream; the first 7 frames repeat frame 0."""
    pad = np.concatenate([np.repeat(feats[:1], WINDOW - 1, 0), feats])
    Xw = np.stack([pad[i:i + WINDOW] for i in range(len(feats))])
    return model(torch.as_tensor(Xw)).argmax(1).numpy()


def vote(proba, classes, hand):
    """Same smoother as the game: majority of the last 5 confident predictions."""
    idle = classes.index(IDLE[hand])
    hist, out = deque([idle] * 5, maxlen=5), []
    for p in proba:
        hist.append(int(p.argmax()) if p.max() >= SURE else idle)
        out.append(Counter(hist).most_common(1)[0][0])
    return np.array(out)


def stream_metrics(pred, truth):
    acc = float((pred == truth).mean())
    true_changes = int((np.diff(truth) != 0).sum())
    pred_changes = int((np.diff(pred) != 0).sum())
    flicker = max(0, pred_changes - true_changes) / len(truth) * 100
    delays = []
    for c in np.flatnonzero(np.diff(truth) != 0) + 1:
        end = c
        while end < len(truth) and truth[end] == truth[c]:
            end += 1
        hit = np.flatnonzero(pred[c:end] == truth[c])
        delays.append(int(hit[0]) if len(hit) else end - c)
    return {"accuracy": acc, "flicker_per_100": flicker,
            "delay_frames": float(np.mean(delays)) if delays else 0.0}


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--epochs", type=int, default=25)
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(args.seed)
    methods = ["MLP (1 frame)", "MLP + vote 3 of 5", "GRU (8 frames)"]
    results = {}
    example = None
    for hand in ("Left", "Right"):
        d = load_hand(hand)
        per = {m: [] for m in methods}
        for person in sorted(np.unique(d.users)):
            test = np.flatnonzero(d.users == person)
            train = np.flatnonzero(d.users != person)
            t = time.time()
            mlp = train_mlp(d.X[train], d.y[train], len(d.classes),
                            argparse.Namespace(epochs=args.epochs, batch=64, lr=1e-3, seed=args.seed),
                            args.seed, hand, AUG_ROTATION[hand])
            gru = train_gru(d, train, args.epochs, args.seed)
            s = stream(d, test, rng)
            feats = make_features(d.X[s], hand)
            with torch.no_grad():
                proba = torch.softmax(mlp(torch.as_tensor(feats)), 1).numpy()
            preds = {"MLP (1 frame)": proba.argmax(1), "MLP + vote 3 of 5": vote(proba, d.classes, hand),
                     "GRU (8 frames)": run_gru(gru, feats)}
            truth = d.y[s]
            for m in methods:
                per[m].append({"person": person, **stream_metrics(preds[m], truth)})
            print(f"  {hand:<5} test={person:<7} " + "  ".join(
                f"{m}: {per[m][-1]['accuracy']:.3f}/{per[m][-1]['flicker_per_100']:.1f}" for m in methods) +
                f"  ({time.time() - t:.0f}s)")
            if hand == "Left" and example is None:
                example = (truth[:600], {m: preds[m][:600] for m in methods}, d.classes, person)
            if hand == "Left":   # timing once, on CPU, one frame at a time like the game
                win = torch.as_tensor(np.repeat(feats[:1], WINDOW, 0)[None])
                one = torch.as_tensor(feats[:1])
                with torch.no_grad():
                    t0 = time.perf_counter()
                    for _ in range(200):
                        mlp(one)
                    t1 = time.perf_counter()
                    for _ in range(200):
                        gru(win)
                    t2 = time.perf_counter()
                results.setdefault("timing_ms", {"MLP": (t1 - t0) / 200 * 1000, "GRU": (t2 - t1) / 200 * 1000})
        results[hand] = {m: {"per_person": per[m],
                             **{k: float(np.mean([r[k] for r in per[m]]))
                                for k in ("accuracy", "flicker_per_100", "delay_frames")}} for m in methods}
    (OUT / "temporal.json").write_text(json.dumps(results, indent=2), encoding="utf-8")

    # chart: a slice of one stream, truth vs each method
    truth, preds, classes, person = example
    fig, axes = plt.subplots(len(methods) + 1, 1, figsize=(10, 4.6), sharex=True)
    for ax, (name, seq) in zip(axes, [("truth", truth), *preds.items()]):
        ax.step(np.arange(len(seq)) / FPS, seq, where="post", color="#333" if name == "truth" else "#d9534f", lw=1.2)
        ax.set_yticks(range(len(classes)), [c.replace("TILT_", "T_") for c in classes], fontsize=7)
        ax.set_ylabel(name, rotation=0, ha="right", fontsize=8)
        ax.grid(alpha=0.3)
    axes[-1].set_xlabel(f"seconds (left hand, unseen person: {person})")
    fig.suptitle("Gesture stream: steadiness of each method", fontsize=10)
    fig.tight_layout()
    fig.savefig(OUT / "temporal_stream.png", dpi=130)
    plt.close(fig)

    lines = ["# Temporal model vs one frame (generated by temporal.py)", "",
             "Leave-one-person-out; each test person's takes joined into one stream with gesture changes.", "",
             "| Hand | Method | Accuracy | Wrong changes / 100 frames | Delay after a change (frames) |",
             "|---|---|---|---|---|"]
    for hand in ("Left", "Right"):
        for m in methods:
            r = results[hand][m]
            lines.append(f"| {hand} | {m} | {r['accuracy'] * 100:.1f}% | {r['flicker_per_100']:.2f} | "
                         f"{r['delay_frames']:.1f} ({r['delay_frames'] / FPS * 1000:.0f} ms) |")
    tm = results["timing_ms"]
    lines += ["", f"Inference per frame on CPU: MLP {tm['MLP']:.3f} ms, GRU {tm['GRU']:.3f} ms.",
              "", "Chart: `temporal_stream.png`.", ""]
    (OUT / "temporal.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
