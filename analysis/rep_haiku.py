"""Stage-10 round 3: second-model replication on claude-haiku-5-5.

    python analysis/rep_haiku.py --runs runs/paper/haiku55 [--log]

Tests H1-H3 as pre-registered in 09-experiments.md.
"""

import argparse
import random
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyze as Z  # noqa: E402
from sens_clustergold import heldout  # noqa: E402

COLS = ("first", "minibatch", "clustergold")
CELLS = ["seed-none"] + [f"{r}-full-{c}" for r in ("seed", "parent") for c in COLS]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=Path, required=True)
    ap.add_argument("--log", action="store_true")
    a = ap.parse_args()
    rng = random.Random(0)
    hb = heldout(a.runs)
    tasks = [t for t in hb if all(len(hb[t].get(k, [])) == 10 for k in CELLS)]
    cells = {(t, k): hb[t][k] for t in tasks for k in CELLS}
    print(f"tasks with all 7 cells at n=10: {tasks}; incomplete: {[t for t in hb if t not in tasks]}")
    print("\n## held-out best, mean")
    print("| task | " + " | ".join(CELLS) + " |")
    print("|---" * (len(CELLS) + 1) + "|")
    for t in tasks:
        print(f"| {t} | " + " | ".join(f"{Z.mean(hb[t][k]):.3f}" for k in CELLS) + " |")
    d = lambda ts, x, y: lambda m: Z.mean([m[(t, x)] - m[(t, y)] for t in ts])
    h1 = lambda ts: lambda m: Z.mean([Z.mean([m[(t, f"parent-full-{c}")] for c in COLS])
                                      - Z.mean([m[(t, f"seed-full-{c}")] for c in COLS]) for t in ts])
    h2 = lambda ts: lambda m: Z.mean([(m[(t, "seed-full-clustergold")] - m[(t, "seed-full-first")])
                                      - (m[(t, "parent-full-clustergold")] - m[(t, "parent-full-first")]) for t in ts])
    r1 = Z.boot(cells, h1(tasks), rng)
    r2 = Z.boot(cells, h2(tasks), rng)
    r3 = Z.boot(cells, d(tasks, "parent-full-clustergold", "parent-full-first"), rng)
    print(f"\nH1 lineage main effect = {Z.fmt(*r1)} -> {'holds' if r1[1][0] > 0 else 'does not hold'}")
    print(f"H2 I_clustergold = {Z.fmt(*r2)} -> {'holds' if r2[1][0] > 0 else 'does not hold'}")
    print(f"H3 parent clustergold - first = {Z.fmt(*r3)} -> {'holds' if r3[1][1] < 0.05 else 'does not hold'}")
    print("\n## secondary (reported only)")
    print("parent minibatch - first =", Z.fmt(*Z.boot(cells, d(tasks, "parent-full-minibatch", "parent-full-first"), rng)))
    for x in ("first", "minibatch"):
        print(f"seed clustergold - {x} =", Z.fmt(*Z.boot(cells, d(tasks, "seed-full-clustergold", f"seed-full-{x}"), rng)))
    print("seed first - seed-none =", Z.fmt(*Z.boot(cells, d(tasks, "seed-full-first", "seed-none"), rng)))
    print("\n## per task: H1 / H2 / H3")
    for t in tasks:
        sub = {k: v for k, v in cells.items() if k[0] == t}
        print(t, Z.fmt(*Z.boot(sub, h1([t]), rng)), "/", Z.fmt(*Z.boot(sub, h2([t]), rng)), "/",
              Z.fmt(*Z.boot(sub, d([t], "parent-full-clustergold", "parent-full-first"), rng)))
    print("\n## leave-one-task-out: H1 / H2 / H3")
    for t in tasks:
        ts = [u for u in tasks if u != t]
        sub = {k: v for k, v in cells.items() if k[0] in ts}
        print(f"-{t}", Z.fmt(*Z.boot(sub, h1(ts), rng)), "/", Z.fmt(*Z.boot(sub, h2(ts), rng)), "/",
              Z.fmt(*Z.boot(sub, d(ts, "parent-full-clustergold", "parent-full-first"), rng)))
    if a.log:
        ex = ["python3", str(Path.home() / ".claude/skills/paper/scripts/exp.py"), "--workspace", str(Z.WS)]
        m = 0
        for (t, k), vs in cells.items():
            for i, v in enumerate(vs):
                subprocess.run(ex + ["log", "rep-haiku", "--metric", f"holdout_best={v}", "--seed", str(i), "--split", "test",
                                     "--config", f"task={t}", "--config", f"cell={k}", "--config", "model=claude-haiku-5-5"],
                               check=True, capture_output=True)
                m += 1
        print(f"\nlogged {m} runs")


if __name__ == "__main__":
    main()
