"""Full evaluation for the report: compares 5 methods per hand, with charts.

Methods (all on the same hand-specific features, except the rules):
    Rules           fixed thresholds (no learning, the original TikTok idea)
    kNN             k-nearest neighbours (k=5)
    SVM             support vector machine, RBF kernel
    Random Forest   200 decision trees
    MLP             our neural network (gestures/model.py)

Test protocol: leave-one-person-out. Train on 2 people, test on the 3rd, repeat
for each person. The test person is never seen in training, like a new player.

Also measures:
    - learning curve: accuracy vs amount of training data
    - false triggers: how often a model is "sure" (>= 70%) about a pose that is
      not one of its gestures (we show it the other hand's poses)
    - inference time per frame of each method

Usage:
    pip install -r requirements-eval.txt     # scikit-learn + matplotlib (only for this script)
    python evaluate.py                       # writes reports/evaluation/
    python evaluate.py --quick               # fewer epochs, for a fast check
"""
from __future__ import annotations

import argparse
import json
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import torch  # noqa: E402
from sklearn.calibration import CalibratedClassifierCV  # noqa: E402
from sklearn.ensemble import RandomForestClassifier  # noqa: E402
from sklearn.metrics import f1_score  # noqa: E402
from sklearn.neighbors import KNeighborsClassifier  # noqa: E402
from sklearn.pipeline import make_pipeline  # noqa: E402
from sklearn.preprocessing import StandardScaler  # noqa: E402
from sklearn.svm import SVC  # noqa: E402

from gestures import config  # noqa: E402
from gestures.features import AUG_ROTATION, load_hand, make_features  # noqa: E402
from gestures.rules import RULES  # noqa: E402
from train import confusion, train_mlp  # noqa: E402

OUT = config.ROOT / "reports" / "evaluation"
METHODS = ["Rules", "kNN", "SVM", "Random Forest", "MLP"]
COLORS = {"Rules": "#9a8fb0", "kNN": "#5b9bd5", "SVM": "#e0a030", "Random Forest": "#58a868", "MLP": "#d9534f"}
SURE = 0.7


def parse_args():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--epochs", type=int, default=40)
    p.add_argument("--quick", action="store_true", help="10 epochs, 2 learning-curve points")
    p.add_argument("--seed", type=int, default=42)
    return p.parse_args()


# --- the learned models, behind one small interface: fit(X63, y) / proba(X63) ---------
class SkModel:
    def __init__(self, name, hand, seed):
        self.name, self.hand = name, hand
        self.clf = {
            "kNN": lambda: make_pipeline(StandardScaler(), KNeighborsClassifier(5)),
            "SVM": lambda: make_pipeline(StandardScaler(), CalibratedClassifierCV(SVC(C=3), ensemble=False, cv=3)),
            "Random Forest": lambda: RandomForestClassifier(200, min_samples_leaf=3, n_jobs=-1, random_state=seed),
        }[name]()

    def fit(self, X, y):
        if self.name == "SVM" and len(y) > 6000:
            idx = np.random.default_rng(0).choice(len(y), 6000, replace=False)   # SVM is O(n^2): subsample
            X, y = X[idx], y[idx]
        self.clf.fit(make_features(X, self.hand), y)
        return self

    def proba(self, X):
        return self.clf.predict_proba(make_features(X, self.hand))


class MLPModel:
    def __init__(self, hand, epochs, seed):
        self.hand, self.seed = hand, seed
        self.args = argparse.Namespace(epochs=epochs, batch=64, lr=1e-3, seed=seed)

    def fit(self, X, y):
        n = len(config.CLASSES[self.hand])
        self.model = train_mlp(X, y, n, self.args, self.seed, self.hand, AUG_ROTATION[self.hand])
        return self

    @torch.no_grad()
    def proba(self, X):
        logits = self.model(torch.as_tensor(make_features(X, self.hand)))
        return torch.softmax(logits, 1).numpy()


def make_model(name, hand, args):
    return MLPModel(hand, args.epochs, args.seed) if name == "MLP" else SkModel(name, hand, args.seed)


def rule_predict(d, idx):
    rule = RULES[d.hand]
    return np.array([d.classes.index(rule(d.raw[i], *d.sizes[i])) for i in idx])


# --- experiments ------------------------------------------------------------------------
def leave_one_person_out(d, other, args):
    people = sorted(np.unique(d.users))
    n = len(d.classes)
    res = {m: {"per_person": {}, "pred": np.full(len(d.y), -1)} for m in METHODS}
    false_trig = {m: [] for m in METHODS if m != "Rules"}
    for person in people:
        test = np.flatnonzero(d.users == person)
        train = np.flatnonzero(d.users != person)
        res["Rules"]["pred"][test] = rule_predict(d, test)
        other_test = other.X[other.users == person]
        for m in METHODS[1:]:
            t = time.time()
            model = make_model(m, d.hand, args).fit(d.X[train], d.y[train])
            p = model.proba(d.X[test])
            res[m]["pred"][test] = p.argmax(1)
            # false triggers: the other hand's poses are not gestures of this hand
            false_trig[m].append(float((model.proba(other_test).max(1) >= SURE).mean()))
            print(f"  {d.hand:<5} test={person:<7} {m:<14} acc {(p.argmax(1) == d.y[test]).mean():.3f}"
                  f"  ({time.time() - t:.1f}s)")
        for m in METHODS:
            res[m]["per_person"][person] = float((res[m]["pred"][test] == d.y[test]).mean())
    out = {}
    for m in METHODS:
        pred = res[m]["pred"]
        out[m] = {
            "accuracy": float((pred == d.y).mean()),
            "macro_f1": float(f1_score(d.y, pred, average="macro")),
            "per_person": res[m]["per_person"],
            "confusion": confusion(d.y, pred, n).tolist(),
            "false_trigger": float(np.mean(false_trig[m])) if m in false_trig else None,
        }
    return out


def learning_curve(d, args, fractions):
    """Mean leave-one-person-out accuracy when training on only part of the other people's data."""
    rng = np.random.default_rng(args.seed)
    curve = {m: [] for m in ("Random Forest", "MLP")}
    for f in fractions:
        accs = {m: [] for m in curve}
        for person in np.unique(d.users):
            test = d.users == person
            train = np.flatnonzero(~test)
            # whole takes, not random frames, so the smaller set is really less varied
            takes = np.unique(d.takes[train])
            keep = rng.choice(takes, max(len(d.classes), int(len(takes) * f)), replace=False)
            sub = train[np.isin(d.takes[train], keep)]
            if len(np.unique(d.y[sub])) < len(d.classes):
                continue
            for m in curve:
                model = make_model(m, d.hand, args).fit(d.X[sub], d.y[sub])
                accs[m].append(float((model.proba(d.X[test]).argmax(1) == d.y[test]).mean()))
        for m in curve:
            curve[m].append(float(np.mean(accs[m])) if accs[m] else float("nan"))
        print(f"  {d.hand} learning curve {int(f * 100):>3}%: " + "  ".join(f"{m} {curve[m][-1]:.3f}" for m in curve))
    return curve


def timing(d, args):
    """Milliseconds to classify ONE frame (the game classifies one frame at a time)."""
    X1 = d.X[:1]
    out = {}
    t = time.perf_counter()
    for _ in range(200):
        rule_predict(d, [0])
    out["Rules"] = (time.perf_counter() - t) / 200 * 1000
    sub = np.random.default_rng(0).choice(len(d.y), min(3000, len(d.y)), replace=False)
    for m in METHODS[1:]:
        model = make_model(m, d.hand, argparse.Namespace(epochs=3, seed=args.seed)).fit(d.X[sub], d.y[sub])
        if m == "MLP":
            model.model.eval()
        model.proba(X1)
        t = time.perf_counter()
        for _ in range(100):
            model.proba(X1)
        out[m] = (time.perf_counter() - t) / 100 * 1000
    return out


# --- charts -------------------------------------------------------------------------------
def chart_accuracy(results):
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), sharey=True)
    for ax, hand in zip(axes, ("Left", "Right")):
        r = results[hand]["lopo"]
        people = list(r["MLP"]["per_person"])
        w = 0.8 / len(METHODS)
        x = np.arange(len(people) + 1)
        for i, m in enumerate(METHODS):
            vals = [r[m]["per_person"][p] for p in people] + [r[m]["accuracy"]]
            ax.bar(x + (i - 2) * w, np.array(vals) * 100, w, label=m, color=COLORS[m])
        ax.set_xticks(x, [p.capitalize() for p in people] + ["ALL"])
        ax.set_title(f"{hand} hand ({'move' if hand == 'Left' else 'jump'})")
        ax.set_ylim(40, 100)
        ax.grid(axis="y", alpha=0.3)
    axes[0].set_ylabel("accuracy on the unseen person (%)")
    axes[1].legend(loc="lower right", fontsize=8)
    fig.suptitle("Leave-one-person-out accuracy")
    fig.tight_layout()
    fig.savefig(OUT / "accuracy_by_person.png", dpi=130)
    plt.close(fig)


def chart_confusions(results):
    for hand in ("Left", "Right"):
        classes = config.CLASSES[hand]
        fig, axes = plt.subplots(1, len(METHODS), figsize=(3.1 * len(METHODS), 3.2))
        for ax, m in zip(axes, METHODS):
            cm = np.array(results[hand]["lopo"][m]["confusion"], dtype=float)
            cmn = cm / cm.sum(1, keepdims=True)
            ax.imshow(cmn, cmap="Blues", vmin=0, vmax=1)
            for i in range(len(classes)):
                for j in range(len(classes)):
                    ax.text(j, i, f"{cmn[i, j] * 100:.0f}", ha="center", va="center",
                            color="white" if cmn[i, j] > 0.6 else "black", fontsize=9)
            short = [c.replace("TILT_", "T_")[:7] for c in classes]
            ax.set_xticks(range(len(classes)), short, fontsize=7, rotation=30)
            ax.set_yticks(range(len(classes)), short if m == METHODS[0] else [], fontsize=7)
            ax.set_title(f"{m}\n{results[hand]['lopo'][m]['accuracy'] * 100:.1f}%", fontsize=9)
        axes[0].set_ylabel("true")
        fig.suptitle(f"{hand} hand: confusion matrices (% of each true class, rows)", fontsize=10)
        fig.tight_layout()
        fig.savefig(OUT / f"confusion_{hand.lower()}.png", dpi=130)
        plt.close(fig)


def chart_learning_curve(results, fractions):
    fig, ax = plt.subplots(figsize=(6, 3.8))
    for hand, style in (("Left", "-"), ("Right", "--")):
        for m in ("Random Forest", "MLP"):
            ax.plot(np.array(fractions) * 100, np.array(results[hand]["learning_curve"][m]) * 100,
                    style, marker="o", color=COLORS[m], label=f"{m} ({hand})")
    ax.set_xlabel("% of the training takes used")
    ax.set_ylabel("accuracy on the unseen person (%)")
    ax.set_title("Learning curve")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT / "learning_curve.png", dpi=130)
    plt.close(fig)


def chart_false_and_time(results):
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.6))
    learned = METHODS[1:]
    x = np.arange(len(learned))
    for i, hand in enumerate(("Left", "Right")):
        vals = [results[hand]["lopo"][m]["false_trigger"] * 100 for m in learned]
        axes[0].bar(x + (i - 0.5) * 0.38, vals, 0.38, label=f"{hand} model", color=["#5b9bd5", "#e0a030"][i])
        vals = [results[hand]["timing_ms"][m] for m in METHODS]
        axes[1].bar(np.arange(len(METHODS)) + (i - 0.5) * 0.38, vals, 0.38, label=hand, color=["#5b9bd5", "#e0a030"][i])
    axes[0].set_xticks(x, learned)
    axes[0].set_ylabel("% of non-gesture poses\nclassified with >= 70%")
    axes[0].set_title("False triggers (lower is better)")
    axes[0].legend(fontsize=8)
    axes[1].set_xticks(range(len(METHODS)), METHODS)
    axes[1].set_ylabel("ms per frame")
    axes[1].set_yscale("log")
    axes[1].set_title("Inference time per frame (log scale)")
    axes[1].legend(fontsize=8)
    for ax in axes:
        ax.grid(axis="y", alpha=0.3)
        ax.tick_params(axis="x", labelsize=8)
    fig.tight_layout()
    fig.savefig(OUT / "false_triggers_and_time.png", dpi=130)
    plt.close(fig)


def write_markdown(results, fractions):
    lines = ["# Model comparison (generated by evaluate.py)", "",
             "Leave-one-person-out: train on 2 people, test on the 3rd. Same features for all learned models.", ""]
    for hand in ("Left", "Right"):
        r = results[hand]
        people = list(r["lopo"]["MLP"]["per_person"])
        lines += [f"## {hand} hand ({r['rows']} frames)", "",
                  "| Method | " + " | ".join(p.capitalize() for p in people) +
                  " | All | Macro-F1 | False triggers | ms/frame |",
                  "|---|" + "---|" * (len(people) + 4)]
        for m in METHODS:
            x = r["lopo"][m]
            ft = "-" if x["false_trigger"] is None else f"{x['false_trigger'] * 100:.1f}%"
            lines.append(f"| {m} | " + " | ".join(f"{x['per_person'][p] * 100:.1f}" for p in people) +
                         f" | **{x['accuracy'] * 100:.1f}** | {x['macro_f1']:.3f} | {ft} | {r['timing_ms'][m]:.3f} |")
        lines += ["", "Learning curve (mean accuracy): " + ", ".join(
            f"{int(f * 100)}% data: RF {r['learning_curve']['Random Forest'][i] * 100:.1f} / "
            f"MLP {r['learning_curve']['MLP'][i] * 100:.1f}" for i, f in enumerate(fractions)), ""]
    lines += ["Charts: `accuracy_by_person.png`, `confusion_left.png`, `confusion_right.png`, "
              "`learning_curve.png`, `false_triggers_and_time.png`.", ""]
    (OUT / "evaluation.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    args = parse_args()
    if args.quick:
        args.epochs = 10
    fractions = [0.25, 1.0] if args.quick else [0.1, 0.25, 0.5, 1.0]
    OUT.mkdir(parents=True, exist_ok=True)
    data = {h: load_hand(h) for h in ("Left", "Right")}
    results = {}
    for hand, other in (("Left", "Right"), ("Right", "Left")):
        d = data[hand]
        print(f"\n=== {hand} hand: {len(d.y)} frames, people {sorted(set(d.users))} ===")
        results[hand] = {"rows": int(len(d.y)), "lopo": leave_one_person_out(d, data[other], args),
                         "learning_curve": learning_curve(d, args, fractions), "timing_ms": timing(d, args)}
    for hand in results:
        for m in METHODS:
            results[hand]["lopo"][m].pop("pred", None)
    (OUT / "evaluation.json").write_text(json.dumps({"fractions": fractions, "results": results}, indent=2),
                                         encoding="utf-8")
    chart_accuracy(results)
    chart_confusions(results)
    chart_learning_curve(results, fractions)
    chart_false_and_time(results)
    write_markdown(results, fractions)
    print(f"\nDone -> {OUT}")


if __name__ == "__main__":
    main()
