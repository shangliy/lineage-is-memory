"""Stage-10 sensitivity arm: cluster summaries that keep the expected answer.

    python analysis/sens_clustergold.py --runs runs/paper/gpt41mini \
        --gold runs/paper/gpt41mini_clustergold [--log]

Tests S1/S2 as pre-registered in 09-experiments.md.
"""

import argparse
import glob
import json
import random
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyze as Z  # noqa: E402


def heldout(runs):
    hb = {}
    for t in Z.PROMPT:
        rows = Z.load_prompt(runs, t)
        if rows:
            hb[t] = {k: [r["holdout_best"] for r in v] for k, v in Z.by_key(rows).items()}
    code = Z.load_code(runs)
    for t in Z.CODE:
        rows = [r for r in code if r["task"] == t]
        if rows:
            hb[t] = {k: [r["holdout_best"] for r in v] for k, v in Z.by_key(rows).items()}
    return hb


def retention(gold_runs, task):
    n = k = 0
    for f in glob.glob(str(gold_runs / task / "*-full-clustergold-*.jsonl")):
        for line in open(f):
            e = json.loads(line)
            fb = (e.get("evaluation") or {}).get("feedback") or ""
            if e.get("event") == "candidate" and fb:
                n += 1
                k += bool(re.search(r"expected", fb, re.I))
    return k, n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=Path, required=True)
    ap.add_argument("--gold", type=Path, required=True)
    ap.add_argument("--log", action="store_true")
    a = ap.parse_args()
    rng = random.Random(0)
    hb, gold = heldout(a.runs), heldout(a.gold)
    for t in gold:
        hb.setdefault(t, {}).update(gold[t])
    tasks = [t for t in hb if "parent-full-clustergold" in hb[t]]
    cells = {(t, k): v for t in tasks for k, v in hb[t].items()}

    def c(ts, x, y):
        return lambda m: Z.mean([m[(t, x)] - m[(t, y)] for t in ts])

    print("## held-out best, mean (n)")
    print("| task | seed-first | seed-cluster | seed-clustergold | parent-first | parent-cluster | parent-clustergold | gold kept |")
    print("|---|---|---|---|---|---|---|---|")
    for t in tasks:
        k, n = retention(a.gold, t) if t in Z.PROMPT else (None, None)
        print(f"| {t} | " + " | ".join(f"{Z.mean(hb[t][x]):.3f}" for x in (
            "seed-full-first", "seed-full-cluster", "seed-full-clustergold",
            "parent-full-first", "parent-full-cluster", "parent-full-clustergold"))
            + f" | {f'{k}/{n}' if n else '-'} |")
    print()
    rep = {k: v for k, v in cells.items() if k[0] == "replies"}
    s1 = Z.boot(rep, c(["replies"], "parent-full-clustergold", "parent-full-cluster"), rng)
    k, n = retention(a.gold, "replies")
    print(f"S1 replies parent clustergold - cluster = {Z.fmt(*s1)}; gold kept {k}/{n}")
    print(f"   supported={s1[1][0] > 0 and n and k / n >= 0.8}")
    s2 = Z.boot(cells, c(tasks, "parent-full-clustergold", "parent-full-first"), rng)
    verdict = "summary harmful" if s2[1][1] < 0 else "clustergold better" if s2[1][0] > 0 else "indistinguishable"
    print(f"S2 parent clustergold - first ({len(tasks)} tasks) = {Z.fmt(*s2)} -> {verdict}")
    for row in ("seed", "parent"):
        print(f"  {row}: clustergold - first = {Z.fmt(*Z.boot(cells, c(tasks, f'{row}-full-clustergold', f'{row}-full-first'), rng))}"
              f"; clustergold - cluster = {Z.fmt(*Z.boot(cells, c(tasks, f'{row}-full-clustergold', f'{row}-full-cluster'), rng))}")
    inter = lambda m: Z.mean([(m[(t, "seed-full-clustergold")] - m[(t, "seed-full-first")])
                              - (m[(t, "parent-full-clustergold")] - m[(t, "parent-full-first")]) for t in tasks])
    print(f"  I_clustergold = {Z.fmt(*Z.boot(cells, inter, rng))}")
    ts = [t for t in tasks if t != "replies"]
    sub = {k: v for k, v in cells.items() if k[0] in ts}
    print(f"  without replies: parent clustergold - first = {Z.fmt(*Z.boot(sub, c(ts, 'parent-full-clustergold', 'parent-full-first'), rng))}")
    print("\n## per task, parent clustergold - first")
    for t in tasks:
        sub = {k: v for k, v in cells.items() if k[0] == t}
        print(t, Z.fmt(*Z.boot(sub, c([t], "parent-full-clustergold", "parent-full-first"), rng)))
    if a.log:
        ex = ["python3", str(Path.home() / ".claude/skills/paper/scripts/exp.py"), "--workspace", str(Z.WS)]
        m = 0
        for t in tasks:
            for key in ("seed-full-clustergold", "parent-full-clustergold"):
                for i, v in enumerate(gold[t][key]):
                    subprocess.run(ex + ["log", "sens-clustergold", "--metric", f"holdout_best={v}", "--seed", str(i),
                                         "--split", "test", "--config", f"task={t}", "--config", f"cell={key}"],
                                   check=True, capture_output=True)
                    m += 1
        print(f"\nlogged {m} runs")


if __name__ == "__main__":
    main()
