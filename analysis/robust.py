"""Stage-10 robustness (post hoc, labelled as such): leave-one-task-out and per-task contrasts.

    python analysis/robust.py --runs runs/paper/gpt41mini
"""

import argparse
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyze as Z  # noqa: E402


def contrast(tasks, a, b):
    return lambda m: Z.mean([m[(t, a)] - m[(t, b)] for t in tasks])


def interaction(tasks, x):
    return lambda m: Z.mean([
        (m[(t, f"seed-full-{x}")] - m[(t, "seed-full-first")])
        - (m[(t, f"parent-full-{x}")] - m[(t, "parent-full-first")]) for t in tasks])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=Path, required=True)
    a = ap.parse_args()
    rng = random.Random(0)
    hb = {}
    for t in Z.PROMPT:
        rows = Z.load_prompt(a.runs, t)
        if rows:
            hb[t] = {k: [r["holdout_best"] for r in v] for k, v in Z.by_key(rows).items()}
    for t in Z.CODE:
        rows = [r for r in Z.load_code(a.runs) if r["task"] == t]
        if rows:
            hb[t] = {k: [r["holdout_best"] for r in v] for k, v in Z.by_key(rows).items()}
    tasks = list(hb)
    cells = {(t, k): v for t in tasks for k, v in hb[t].items()}
    tests = {
        "I_diverse": lambda ts: interaction(ts, "diverse"),
        "I_cluster": lambda ts: interaction(ts, "cluster"),
        "parent cluster-first": lambda ts: contrast(ts, "parent-full-cluster", "parent-full-first"),
        "parent minibatch-first": lambda ts: contrast(ts, "parent-full-minibatch", "parent-full-first"),
        "parent diverse-first": lambda ts: contrast(ts, "parent-full-diverse", "parent-full-first"),
        "seed cluster-first": lambda ts: contrast(ts, "seed-full-cluster", "seed-full-first"),
    }
    print("## leave-one-task-out (95% CI)")
    print("| dropped | " + " | ".join(tests) + " |")
    print("|---|" + "---|" * len(tests))
    for drop in [None] + tasks:
        ts = [t for t in tasks if t != drop]
        sub = {k: v for k, v in cells.items() if k[0] in ts}
        print(f"| {drop or '(none)'} | " + " | ".join(Z.fmt(*Z.boot(sub, f(ts), rng)) for f in tests.values()) + " |")
    print("\n## per-task parent-row contrasts vs first")
    for t in tasks:
        sub = {k: v for k, v in cells.items() if k[0] == t}
        print(t, " ".join(f"{x}={Z.fmt(*Z.boot(sub, contrast([t], f'parent-full-{x}', 'parent-full-first'), rng))}"
                          for x in ("diverse", "minibatch", "cluster")))


if __name__ == "__main__":
    main()
