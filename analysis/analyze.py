"""Stage-09 analysis: log runs to exp.py and compute the pre-registered tests.

    python analysis/analyze.py --runs runs/paper/gpt41mini [--log]

Definitions are the ones written in 09-experiments.md before the runs.
"""

from __future__ import annotations

import argparse
import ast
import json
import random
import re
import statistics
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "benchmarks" / "evolution"))

import anchoring as A  # noqa: E402
import prompt_anchoring as P  # noqa: E402
from tasks import DURATION_SEARCH, SIZE_SEARCH  # noqa: E402

WS = Path(__file__).resolve().parents[1]
PROMPT = ["labels", "dates", "routing", "replies", "scone"]
CODE = ["duration", "size"]
REVEALS = ["first", "diverse", "minibatch", "cluster"]
B = 10_000


def load_prompt(runs: Path, task: str):
    f = runs / task / "summary.json"
    return json.loads(f.read_text()) if f.exists() else []


def load_code(runs: Path):
    rows = []
    for d in ("code", "code_c1"):
        f = runs / d / "summary.json"
        if f.exists():
            for r in json.loads(f.read_text()):
                r = dict(r, task=r["task"].split("@")[0].split("+")[0])
                r["key"] = A.key_of(r["lineage"], r["feedback"], r["reveal"])
                r["tokens_to_solve"] = A.tokens_to_solve(r)
                rows.append(r)
    return rows


def load_gepa(runs: Path, task: str):
    out = []
    for suffix in ("", "-stop"):
        f = runs / f"gepa_{task}" / f"summary-mb3{suffix}.json"
        if f.exists():
            out += json.loads(f.read_text())
    return out


def by_key(rows):
    out = {}
    for r in rows:
        out.setdefault(r["key"], []).append(r)
    return out


def mean(xs):
    return sum(xs) / len(xs) if xs else float("nan")


def ci(samples):
    s = sorted(samples)
    return s[int(0.025 * len(s))], s[int(0.975 * len(s)) - 1]


def boot(cells, stat, rng):
    """cells: {name: [values]}; resample each cell's runs; stat(dict of means)."""
    point = stat({k: mean(v) for k, v in cells.items()})
    draws = []
    for _ in range(B):
        m = {k: mean([rng.choice(v) for _ in v]) for k, v in cells.items()}
        draws.append(stat(m))
    return point, ci(draws)


def fmt(p, c):
    return f"{p:+.3f} [{c[0]:+.3f}, {c[1]:+.3f}]"


# ------------------------------------------------------------------ C2
def c2(hb, rng):
    """hb: {task: {key: [holdout_best]}}"""
    tasks = [t for t in hb if all(f"{p}-full-{x}" in hb[t] for p in ("seed", "parent") for x in REVEALS)]
    cells = {(t, k): v for t in tasks for k, v in hb[t].items()}
    lines = [f"tasks: {tasks}"]

    def inter(x):
        def s(m):
            return mean([
                (m[(t, f"seed-full-{x}")] - m[(t, "seed-full-first")])
                - (m[(t, f"parent-full-{x}")] - m[(t, "parent-full-first")])
                for t in tasks
            ])
        return s

    res = {}
    for x in ("diverse", "cluster", "minibatch"):
        res[x] = boot(cells, inter(x), rng)
        lines.append(f"I_{x} = {fmt(*res[x])}")
    for row in ("seed", "parent"):
        def s(m, row=row):
            return mean([
                m[(t, f"{row}-full-cluster")]
                - max(m[(t, f"{row}-full-{x}")] for x in REVEALS if x != "cluster")
                for t in tasks
            ])
        res[f"cluster_{row}"] = boot(cells, s, rng)
        lines.append(f"cluster - best other ({row} row) = {fmt(*res[f'cluster_{row}'])}")
        for i, x in enumerate(REVEALS):
            for y in REVEALS[i + 1:]:
                def d(m, x=x, y=y, row=row):
                    return mean([m[(t, f"{row}-full-{y}")] - m[(t, f"{row}-full-{x}")] for t in tasks])
                lines.append(f"  {row}: {y} - {x} = {fmt(*boot(cells, d, rng))}")
    def lin(m):
        return mean([
            mean([m[(t, f"parent-full-{x}")] for x in REVEALS])
            - mean([m[(t, f"seed-full-{x}")] for x in REVEALS])
            for t in tasks
        ])
    lines.append(f"lineage main effect (parent - seed, mean over reveals) = {fmt(*boot(cells, lin, rng))}")
    supported = res["diverse"][1][0] > 0
    r1 = res["diverse"][1][0] <= 0 <= res["diverse"][1][1] and res["cluster"][1][0] <= 0 <= res["cluster"][1][1]
    r2 = res["cluster_seed"][1][0] > 0 and res["cluster_parent"][1][0] > 0
    lines.append(f"VERDICT C2: supported={supported}  R1={r1}  R2={r2}")
    return lines


# ------------------------------------------------------------------ C1
def shown_inputs(text):
    out = []
    for m in re.finditer(r"""^input ('(?:[^'\\]|\\.)*'|"(?:[^"\\]|\\.)*")""", text or "", re.M):
        try:
            out.append(ast.literal_eval(m.group(1)))
        except (ValueError, SyntaxError):
            pass
    return out


def unshown_groups(rows, pt):
    """Fixed per task, as pre-registered: groups the seed fails in most seed-row runs,
    minus groups shown to the seed's rewrite in most seed-full-first runs."""
    seed_rows = [r for r in rows if r["key"].startswith("seed-")]
    first = [r for r in rows if r["key"] == "seed-full-first"]
    groups = list(dict.fromkeys(pt.search_groups))
    failing = {
        g for g in groups
        if mean([g not in P.labels_covered(r["candidates"][0]["instance_scores"] or {}, pt.search_groups) for r in seed_rows]) > 0.5
    }
    index = {x: pt.search_groups[i] for i, (x, _) in enumerate(pt.search)}
    shown = {
        g for g in groups
        if mean([g in {index[x] for x in shown_inputs(r.get("shown")) if x in index} for r in first]) > 0.5
    }
    return failing - shown, shown


def unshown_prompt(rows, pt, unshown):
    """Per run: share of proposals covering (on search) the fixed unshown groups."""
    out = []
    for r in rows:
        props = [c for c in r["candidates"][1:] if c["score"] is not None]
        if not unshown or not props:
            continue
        cov = [
            mean([g in P.labels_covered(c["instance_scores"] or {}, pt.search_groups) for g in unshown])
            for c in props
        ]
        out.append(mean(cov))
    return out


def unshown_code(rows, task):
    """Per run: share of proposals passing every held-out case of each held-out
    category not represented among the failures shown to the seed's rewrite."""
    search = {"duration": DURATION_SEARCH, "size": SIZE_SEARCH}[task]
    want = dict(search)
    cases = A.HOLDOUT[task]
    cats = sorted({A.category(task, t, w) for t, w in cases})
    holdout = A.PythonEvaluator(A.TASKS[task].holdout_evaluator, timeout=60)
    cache = {}

    def covers(text):
        if text not in cache:
            s = A.to_evaluation(holdout(text)).instance_scores or {}
            cache[text] = {
                c for c in cats
                if all(s.get(f"case-{i:02d}") == 1.0 for i, (t, w) in enumerate(cases) if A.category(task, t, w) == c)
            }
        return cache[text]

    out = []
    for r in rows:
        seed = r["candidates"][0]["text"]
        failing = set(cats) - covers(seed)
        shown_inputs = re.findall(r"parse_\w+\('((?:[^'\\]|\\.)*)'\)", r.get("shown") or "")
        shown = {A.category(task, s, want.get(s)) for s in shown_inputs if s in want}
        unshown = failing - shown if r["feedback"] != "none" else None
        out.append((r, unshown))
    # seed-none has no display: use the unshown set of the first-k display of the same seed
    ref = next((u for r, u in out if r["key"] == "seed-full-first" and u is not None), None)
    res = {}
    for r, u in out:
        u = ref if u is None else u
        props = [c for c in r["candidates"][1:] if c["score"] is not None]
        if not u or not props:
            continue
        res.setdefault(r["key"], []).append(mean([mean([g in covers(c["text"]) for g in u]) for c in props]))
    return res, ref


def c1(runs, prompt_rows, code_rows, rng):
    lines, verdict = [], {}
    for t in ["labels", "scone"]:
        rows = by_key(prompt_rows.get(t, []))
        if "seed-full-first" not in rows or "seed-none" not in rows:
            continue
        pt = P.make_task(t)
        unshown, shown = unshown_groups([r for v in rows.values() for r in v], pt)
        lines.append(f"{t}: shown groups {sorted(shown)}, unshown failing groups {sorted(unshown)}")
        cells = {key: unshown_prompt(rows[key], pt, unshown) for key in ("seed-none", "seed-full-first", "seed-full-diverse", "seed-full-cluster") if key in rows}
        lines.append(f"{t}: unshown-group proposal coverage " + ", ".join(f"{a}={mean(v):.3f}(n={len(v)})" for a, v in cells.items()))
        p, c = boot({a: cells[a] for a in ("seed-none", "seed-full-first")}, lambda m: m["seed-full-first"] - m["seed-none"], rng)
        lines.append(f"  first - none = {fmt(p, c)}")
        verdict[t] = c[1] < 0
    for t in CODE:
        rows = [r for r in code_rows if r["task"] == t and r["lineage"] == "seed"]
        if not rows:
            continue
        cells, ref = unshown_code(rows, t)
        lines.append(f"{t}: unshown categories {sorted(ref or [])}; coverage " + ", ".join(f"{a}={mean(v):.3f}(n={len(v)})" for a, v in sorted(cells.items())))
        if "seed-full-first" in cells and "seed-none" in cells:
            p, c = boot({a: cells[a] for a in ("seed-none", "seed-full-first")}, lambda m: m["seed-full-first"] - m["seed-none"], rng)
            lines.append(f"  first - none = {fmt(p, c)}")
            verdict[t] = c[1] < 0
        for x in ("random", "iso"):
            if f"seed-full-{x}" in cells and "seed-none" in cells:
                p, c = boot({a: cells[a] for a in ("seed-none", f"seed-full-{x}")}, lambda m, x=x: m[f"seed-full-{x}"] - m["seed-none"], rng)
                lines.append(f"  {x} - none = {fmt(p, c)}")
    n = sum(verdict.get(t, False) for t in ("labels", "duration", "size"))
    lines.append(f"VERDICT C1: crowding-out on {n}/3 constructed tasks -> supported={n >= 2}; per task {verdict}")
    # R3: scone seed row held-out vs seed-none
    sc = by_key(prompt_rows.get("scone", []))
    if "seed-none" in sc:
        within = []
        for x in REVEALS:
            key = f"seed-full-{x}"
            if key in sc:
                cells = {"n": [r["holdout_best"] for r in sc["seed-none"]], "x": [r["holdout_best"] for r in sc[key]]}
                p, c = boot(cells, lambda m: m["x"] - m["n"], rng)
                lines.append(f"scone held-out {key} - seed-none = {fmt(p, c)}")
                within.append(c[0] <= 0 <= c[1])
        lines.append(f"R3 (scone seed row shows no effect) = {all(within)}")
    return lines


# ------------------------------------------------------------------ C3
def c3(prompt_rows, gepa_rows, rng):
    lines, ties = [], 0
    for t in PROMPT:
        ev = [r for r in prompt_rows.get(t, []) if r["key"] == "parent-full-first"]
        g = by_key(gepa_rows.get(t, []))
        stop = g.get("gepa-mb3-stop", [])
        full = g.get("gepa-mb3", [])
        if not ev or not stop:
            continue

        def solved(rows):
            return [r["tokens_to_solve"] for r in rows if r.get("tokens_to_solve")]

        se, ss = solved(ev), solved(stop)
        line = (f"{t}: solved evolve {len(se)}/{len(ev)}, gepa+stop {len(ss)}/{len(stop)}, gepa {len(solved(full))}/{len(full)}; "
                f"median tts evolve {statistics.median(se) if se else '-'}, gepa+stop {statistics.median(ss) if ss else '-'}, "
                f"gepa {statistics.median(solved(full)) if solved(full) else '-'}; held-out evolve {mean([r['holdout_best'] for r in ev]):.3f}, "
                f"gepa+stop {mean([r['holdout_best'] for r in stop]):.3f}, gepa {mean([r['holdout_best'] for r in full]) if full else float('nan'):.3f}")
        if len(se) >= 3 and len(ss) >= 3:
            draws = []
            for _ in range(B):
                a = statistics.median([rng.choice(ss) for _ in ss])
                b = statistics.median([rng.choice(se) for _ in se])
                draws.append(a / b)
            lo, hi = ci(draws)
            ratio = statistics.median(ss) / statistics.median(se)
            line += f"; ratio gepa+stop/evolve {ratio:.2f} [{lo:.2f}, {hi:.2f}]"
            ties += lo <= 1 <= hi
        else:
            line += "; ratio: too few solved runs"
        lines.append(line)
        # GEPA (no stop) call-type decomposition
        if full:
            kinds = {"full": 0, "minibatch": 0}
            for r in full:
                for e in r["trace"]:
                    kinds[e["kind"]] += e["tokens"]
            refl = sum(r["proposer_tokens"] for r in full)
            tot = sum(kinds.values()) + refl
            lines.append(f"  gepa tokens: full re-eval {kinds['full'] / tot:.0%}, minibatch {kinds['minibatch'] / tot:.0%}, reflection {refl / tot:.0%}, total/run {tot / len(full):.0f}")
    lines.append(f"R4 (ratio CI contains 1 on >=3/5 tasks) = {ties >= 3} ({ties} ties)")
    return lines


def log_runs(prompt_rows, code_rows, gepa_rows, model):
    ex = [sys.executable, str(Path.home() / ".claude/skills/paper/scripts/exp.py"), "--workspace", str(WS)]
    existing = json.loads(subprocess.run(ex + ["runs", "--json"], capture_output=True, text=True).stdout or "[]")
    seen = {(r["name"], r.get("seed"), (r.get("config") or {}).get("model")) for r in existing}
    todo = []
    for t, rows in list(prompt_rows.items()) + [(t, [r for r in code_rows if r["task"] == t]) for t in CODE] + list(gepa_rows.items()):
        for r in rows:
            name = f"{t}/{r['key']}"
            if (name, r["repeat"], model) in seen:
                continue
            tok = r.get("tokens") or (r.get("proposer_tokens", 0) + r.get("task_tokens", 0))
            m = ["--metric", f"holdout_best={r['holdout_best']}", "--metric", f"tokens={tok}"]
            if r.get("tokens_to_solve"):
                m += ["--metric", f"tokens_to_solve={r['tokens_to_solve']}"]
            todo.append(ex + ["log", name, *m, "--seed", str(r["repeat"]), "--split", "test", "--config", f"model={model}"])
    for cmd in todo:
        subprocess.run(cmd, capture_output=True, check=True)
    return len(todo)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=Path, required=True)
    ap.add_argument("--model", default="gpt-4.1-mini")
    ap.add_argument("--log", action="store_true")
    a = ap.parse_args()
    rng = random.Random(0)
    prompt_rows = {t: load_prompt(a.runs, t) for t in PROMPT}
    code_rows = load_code(a.runs)
    gepa_rows = {t: load_gepa(a.runs, t) for t in PROMPT}
    hb = {t: {k: [r["holdout_best"] for r in v] for k, v in by_key(rows).items()} for t, rows in prompt_rows.items() if rows}
    for t in CODE:
        rows = [r for r in code_rows if r["task"] == t]
        if rows:
            hb[t] = {k: [r["holdout_best"] for r in v] for k, v in by_key(rows).items()}
    print("## held-out best, mean (n)")
    keys = ["seed-none"] + [f"{p}-full-{x}" for p in ("seed", "parent") for x in REVEALS]
    print("| cell | " + " | ".join(hb) + " |")
    print("|---|" + "---|" * len(hb))
    for k in keys:
        print(f"| {k} | " + " | ".join(f"{mean(hb[t][k]):.3f} ({len(hb[t][k])})" if k in hb[t] else "-" for t in hb) + " |")
    print("\n## C2"); print("\n".join(c2(hb, rng)))
    print("\n## C1"); print("\n".join(c1(a.runs, prompt_rows, code_rows, rng)))
    print("\n## C3"); print("\n".join(c3(prompt_rows, gepa_rows, rng)))
    if a.log:
        print(f"\nlogged {log_runs(prompt_rows, code_rows, gepa_rows, a.model)} runs")


if __name__ == "__main__":
    main()
