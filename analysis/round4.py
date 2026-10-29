"""Stage-10 round 4: public benchmarks, GEPA on them, strong proposer, Haiku diverse arm.

    python analysis/round4.py --root runs/paper [--log]

Tests P1-P5 (public-bench), R4 (gepa-public), S1-S3 (strong-proposer) and
Hd (rep-haiku-diverse) exactly as pre-registered in 09-experiments.md.
"""

import argparse
import random
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyze as Z  # noqa: E402
from sens_clustergold import heldout  # noqa: E402

PUBLIC = ["banking77", "bbh_ste"]
COLS4 = ["first", "diverse", "minibatch", "clustergold"]


def cells_of(hb, tasks):
    return {(t, k): v for t in tasks for k, v in hb[t].items()}


def diff(ts, x, y):
    return lambda m: Z.mean([m[(t, x)] - m[(t, y)] for t in ts])


def lineage(ts, cols):
    return lambda m: Z.mean([Z.mean([m[(t, f"parent-full-{c}")] - m[(t, f"seed-full-{c}")] for c in cols]) for t in ts])


def inter(ts, x):
    return lambda m: Z.mean([(m[(t, f"seed-full-{x}")] - m[(t, "seed-full-first")])
                             - (m[(t, f"parent-full-{x}")] - m[(t, "parent-full-first")]) for t in ts])


def table(hb, tasks, keys):
    print("| cell | " + " | ".join(tasks) + " |")
    print("|---|" + "---|" * len(tasks))
    for k in keys:
        print(f"| {k} | " + " | ".join(f"{Z.mean(hb[t][k]):.3f} ({len(hb[t][k])})" if k in hb[t] else "-"
                                       for t in tasks) + " |")
    print()


def public(root, rng):
    Z.PROMPT[:] = PUBLIC
    hb = heldout(root / "gpt41mini_public")
    tasks = [t for t in PUBLIC if t in hb]
    print("# A+B public-bench (gpt-4.1-mini)\n")
    table(hb, tasks, ["seed-none"] + [f"{p}-full-{c}" for p in ("seed", "parent") for c in COLS4])
    ceil = [t for t in tasks if Z.mean(hb[t]["seed-none"]) >= 0.90]
    print(f"ceiling tasks (seed-none >= 0.90): {ceil or 'none'}\n")
    tests = [("P1 lineage (4 cols)", lambda ts: lineage(ts, COLS4), lambda p, c: c[0] > 0),
             ("P2 I_clustergold", lambda ts: inter(ts, "clustergold"), lambda p, c: c[0] > 0),
             ("P3 parent clustergold - first", lambda ts: diff(ts, "parent-full-clustergold", "parent-full-first"), lambda p, c: c[1] < 0.05),
             ("P4 I_diverse", lambda ts: inter(ts, "diverse"), lambda p, c: c[0] > 0),
             ("P5 parent minibatch - first", lambda ts: diff(ts, "parent-full-minibatch", "parent-full-first"), lambda p, c: c[1] < 0)]
    subsets = [("pooled", tasks)] + ([("without ceiling", [t for t in tasks if t not in ceil])] if ceil else [])
    for name, f, ok in tests:
        for label, ts in subsets:
            if not ts:
                continue
            p, c = Z.boot(cells_of(hb, ts), f(ts), rng)
            print(f"{name} [{label}] = {Z.fmt(p, c)} -> {'holds' if ok(p, c) else 'FAILS'}")
        for t in tasks:
            print(f"    {t}: {Z.fmt(*Z.boot(cells_of(hb, [t]), f([t]), rng))}")
    print("\nother contrasts (report only):")
    for row in ("seed", "parent"):
        for c in ("diverse", "minibatch", "clustergold"):
            print(f"  {row} {c} - first = {Z.fmt(*Z.boot(cells_of(hb, tasks), diff(tasks, f'{row}-full-{c}', f'{row}-full-first'), rng))}")
    return hb


def gepa(root, rng):
    Z.PROMPT[:] = PUBLIC
    runs = root / "gpt41mini_public"
    prompt_rows = {t: Z.load_prompt(runs, t) for t in PUBLIC}
    gepa_rows = {t: Z.load_gepa(runs, t) for t in PUBLIC}
    print("\n# C gepa-public\n")
    lines = Z.c3(prompt_rows, gepa_rows, rng)
    print("\n".join(lines[:-1]))  # last line is C3's own >=3/5 rule; R4 here is per task
    return prompt_rows, gepa_rows


def strong(root, rng):
    Z.PROMPT[:] = ["labels", "routing", "replies"]
    hb = heldout(root / "gpt41_proposer")
    mini = heldout(root / "gpt41mini")
    gold = heldout(root / "gpt41mini_clustergold")
    for t in gold:
        mini.setdefault(t, {}).update(gold[t])
    tasks = [t for t in Z.PROMPT if t in hb]
    keys = ["seed-none", "seed-full-first", "seed-full-clustergold", "parent-full-first", "parent-full-clustergold"]
    print("\n# D1 strong-proposer (gpt-4.1 proposer + clusterer, gpt-4.1-mini task model)\n")
    table(hb, tasks, keys)
    cells = cells_of(hb, tasks)
    for name, f, ok in [("S1 lineage (first, clustergold)", lineage(tasks, ["first", "clustergold"]), lambda p, c: c[0] > 0),
                        ("S2 I_clustergold", inter(tasks, "clustergold"), lambda p, c: c[0] > 0),
                        ("S3 parent clustergold - first", diff(tasks, "parent-full-clustergold", "parent-full-first"), lambda p, c: c[1] < 0.05)]:
        p, c = Z.boot(cells, f, rng)
        print(f"{name} = {Z.fmt(p, c)} -> {'holds' if ok(p, c) else 'FAILS'}")
    print("\nsecondary: gpt-4.1 proposer - gpt-4.1-mini proposer, same task and cell")
    for k in keys:
        both = {}
        for t in tasks:
            if k in hb[t] and k in mini.get(t, {}):
                both[(t, "strong")], both[(t, "mini")] = hb[t][k], mini[t][k]
        ts = sorted({t for t, _ in both})
        if ts:
            print(f"  {k}: {Z.fmt(*Z.boot(both, diff(ts, 'strong', 'mini'), rng))} over {ts}")
    for label, src in (("mini", mini), ("strong", hb)):
        sub = cells_of(src, tasks)
        gap = lambda m: Z.mean([Z.mean([m[(t, f"parent-full-{c}")] - m[(t, f"seed-full-{c}")] for c in ("first", "clustergold")]) for t in tasks])
        print(f"  lineage gap with {label} proposer = {Z.fmt(*Z.boot(sub, gap, rng))}")
    return hb


def haiku_diverse(root, rng):
    Z.PROMPT[:] = ["labels", "routing", "replies"]
    div = heldout(root / "haiku55_diverse")
    base = heldout(root / "haiku55")
    for t in div:
        base.setdefault(t, {}).update(div[t])
    tasks = [t for t in ["labels", "routing", "replies", "duration", "size"] if "parent-full-diverse" in base.get(t, {})]
    print("\n# D2 rep-haiku-diverse (claude-haiku-5-5; first cells from rep-haiku, not interleaved)\n")
    table(base, tasks, ["seed-full-first", "seed-full-diverse", "parent-full-first", "parent-full-diverse"])
    cells = cells_of(base, tasks)
    p, c = Z.boot(cells, inter(tasks, "diverse"), rng)
    print(f"Hd I_diverse = {Z.fmt(p, c)} -> {'holds' if c[0] > 0 else 'FAILS'}")
    for t in tasks:
        print(f"    {t}: {Z.fmt(*Z.boot(cells_of(base, [t]), inter([t], 'diverse'), rng))}")
    for row in ("seed", "parent"):
        print(f"{row} diverse - first = {Z.fmt(*Z.boot(cells, diff(tasks, f'{row}-full-diverse', f'{row}-full-first'), rng))}")
    return div


def log_all(pub, gp, st, hd):
    ex = [sys.executable, str(Path.home() / ".claude/skills/paper/scripts/exp.py"), "--workspace", str(Z.WS)]
    n = 0

    def log(proto, v, seed, model, **cfg):
        nonlocal n
        cmd = ex + ["log", proto, *sum((["--metric", f"{k}={x}"] for k, x in v.items()), []), "--seed", str(seed),
                    "--split", "test", "--config", f"model={model}"]
        for k, x in cfg.items():
            cmd += ["--config", f"{k}={x}"]
        subprocess.run(cmd, check=True, capture_output=True)
        n += 1

    for proto, hb, model in (("public-bench", pub, "gpt-4.1-mini"), ("strong-proposer", st, "gpt-4.1-mini+gpt-4.1"),
                             ("rep-haiku-diverse", hd, "claude-haiku-5-5")):
        for t, cells in hb.items():
            for k, vs in cells.items():
                for i, v in enumerate(vs):
                    log(proto, {"holdout_best": v}, i, model, task=t, cell=k)
    for t, rows in gp[1].items():
        for r in rows:
            m = {"holdout_best": r["holdout_best"]}
            if r.get("tokens_to_solve"):
                m["tokens_to_solve"] = r["tokens_to_solve"]
            log("gepa-public", m, r["repeat"], "gpt-4.1-mini", task=t, cell=r["key"])
    print(f"\nlogged {n} runs")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--log", action="store_true")
    a = ap.parse_args()
    rng = random.Random(0)
    pub = public(a.root, rng)
    gp = gepa(a.root, rng)
    st = strong(a.root, rng)
    hd = haiku_diverse(a.root, rng)
    if a.log:
        log_all(pub, gp, st, hd)


if __name__ == "__main__":
    main()
