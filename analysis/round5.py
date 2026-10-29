"""Stage-10 round 5: does the carry-facts objective close GEPA's Banking77 gap?

    python analysis/round5.py --root runs/paper

Tests F1-F4 exactly as pre-registered in 09-experiments.md (round 5).
"""

import argparse
import glob
import json
import random
import re
import statistics
from pathlib import Path


def holdout(path, key):
    return [r["holdout_best"] for r in json.loads(Path(path).read_text()) if r["key"] == key]


def boot(groups, f, rng, n=10000):
    """Resample runs within each group; ``f`` maps the resampled means to a contrast."""
    point = f({k: statistics.mean(v) for k, v in groups.items()})
    bs = sorted(f({k: statistics.mean(rng.choices(v, k=len(v))) for k, v in groups.items()})
                for _ in range(n))
    return point, (bs[int(0.025 * n)], bs[int(0.975 * n) - 1])


def fmt(p, c):
    return f"{p:+.3f} [{c[0]:+.3f}, {c[1]:+.3f}]"


def labels_named(run_dir, cell):
    labels = set()
    for f in glob.glob(f"{run_dir}/*.jsonl"):
        labels |= {x.strip("?") for x in re.findall(r"expected '([a-z_?]+)'", open(f).read())}
    out = []
    for f in sorted(glob.glob(f"{run_dir}/{cell}-*.jsonl"), key=lambda s: int(s.rsplit("-", 1)[1][:-6])):
        best = None
        for line in open(f):
            e = json.loads(line)
            if e.get("event") == "candidate":
                ev = e["evaluation"]
                s = (eval(ev) if isinstance(ev, str) else ev)["score"]  # noqa: S307 (own log)
                if best is None or s > best[0]:
                    best = (s, e.get("text") or "")
        out.append(sum(x in best[1] for x in labels))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    a = ap.parse_args()
    rng = random.Random(0)
    pub, fix = a.root / "gpt41mini_public", a.root / "gpt41mini_carryfacts"
    g = {}
    for t in ("banking77", "bbh_ste"):
        g[t, "first"] = holdout(pub / t / "summary.json", "parent-full-first")
        g[t, "carry"] = holdout(fix / t / "summary.json", "parent-full-first")
        g[t, "seedcarry"] = holdout(fix / t / "summary.json", "seed-full-first")
        g[t, "gepa"] = [r["holdout_best"] for r in json.loads((pub / f"gepa_{t}" / "summary-mb3.json").read_text())]
    print("| task | parent-first (r4) | seed-carry | parent-carry | GEPA mb3 |\n|---|---|---|---|---|")
    for t in ("banking77", "bbh_ste"):
        print(f"| {t} | " + " | ".join(f"{statistics.mean(g[t, k]):.3f} ({len(g[t, k])})"
                                      for k in ("first", "seedcarry", "carry", "gepa")) + " |")
    print()
    sub = lambda t, x, y: ({k: v for k, v in g.items() if k in ((t, x), (t, y))}, lambda m: m[t, x] - m[t, y])
    p, c = boot(*sub("banking77", "carry", "first"), rng)
    print(f"F1 banking77 parent-carry - parent-first = {fmt(p, c)} -> {'holds' if c[0] > 0 else 'FAILS'}")
    p, c = boot(*sub("banking77", "gepa", "carry"), rng)
    verdict = "gap explained by the meta-prompt" if c[0] <= 0 else "gap NOT fully explained"
    print(f"F2 banking77 GEPA - parent-carry = {fmt(p, c)} -> {verdict}")
    p, c = boot(*sub("bbh_ste", "carry", "first"), rng)
    print(f"F3 bbh_ste parent-carry - parent-first = {fmt(p, c)} -> {'holds' if c[0] > -0.05 else 'FAILS'}")
    both = {k: v for k, v in g.items() if k[1] in ("carry", "seedcarry")}
    p, c = boot(both, lambda m: statistics.mean([m[t, "carry"] - m[t, "seedcarry"] for t in ("banking77", "bbh_ste")]), rng)
    print(f"F4 lineage under carry-facts (pooled) = {fmt(p, c)} -> {'holds' if c[0] > 0 else 'FAILS'}")
    for t in ("banking77", "bbh_ste"):
        print(f"    {t}: {fmt(*boot(*sub(t, 'carry', 'seedcarry'), rng))}")
    p, c = boot(*sub("bbh_ste", "gepa", "carry"), rng)
    print(f"\nreport only: bbh_ste GEPA - parent-carry = {fmt(p, c)}")
    print("\nmechanism (labels named in best prompt, banking77):")
    print(f"  parent-first (r4): {labels_named(pub / 'banking77', 'parent-full-first')}")
    print(f"  parent-carry:      {labels_named(fix / 'banking77', 'parent-full-first')}")
    print(f"  seed-carry:        {labels_named(fix / 'banking77', 'seed-full-first')}")
    print(f"zero-held-out runs: parent-first {g['banking77', 'first'].count(0)}, parent-carry {g['banking77', 'carry'].count(0)}")
    for t in ("banking77", "bbh_ste"):
        s = json.loads((fix / t / "summary.json").read_text())
        tok = statistics.median(r["proposer_tokens"] + r["task_tokens"] for r in s if r["key"] == "parent-full-first")
        gt = statistics.median(r["proposer_tokens"] + r["task_tokens"]
                               for r in json.loads((pub / f"gepa_{t}" / "summary-mb3.json").read_text()))
        print(f"tokens/run {t}: parent-carry {tok:.0f}, GEPA mb3 {gt:.0f} (ratio {gt / tok:.1f}x)")


if __name__ == "__main__":
    main()
