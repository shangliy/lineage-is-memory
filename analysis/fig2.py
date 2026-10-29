"""Fig. 2: Banking77 held-out best and intents named in the best prompt, per arm (mean, 95% CI)."""

import json
import random
import re
import statistics
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from round5 import holdout, labels_named  # noqa: E402

ROOT = Path(sys.argv[1]); OUT = Path(sys.argv[2])
pub, fix = ROOT / "gpt41mini_public" / "banking77", ROOT / "gpt41mini_carryfacts" / "banking77"
gepa = json.loads((ROOT / "gpt41mini_public" / "gepa_banking77" / "summary-mb3.json").read_text())
labels = {x.strip("?") for f in pub.glob("*.jsonl") for x in re.findall(r"expected '([a-z_?]+)'", f.read_text())}
best_text = lambda r: r["best"] if isinstance(r["best"], str) else json.dumps(r["best"])
ARMS = [  # (label, held-out, intents named, colour)
    ("seed\nfirst", holdout(pub / "summary.json", "seed-full-first"), labels_named(pub, "seed-full-first"), "#eb6834"),
    ("parent\nfirst", holdout(pub / "summary.json", "parent-full-first"), labels_named(pub, "parent-full-first"), "#2a78d6"),
    ("GEPA\nmb3", [r["holdout_best"] for r in gepa], [sum(x in best_text(r) for x in labels) for r in gepa], "#8a8984"),
    ("seed\n+carry", holdout(fix / "summary.json", "seed-full-first"), labels_named(fix, "seed-full-first"), "#eb6834"),
    ("parent\n+carry", holdout(fix / "summary.json", "parent-full-first"), labels_named(fix, "parent-full-first"), "#2a78d6"),
]
rng = random.Random(0)


def ci(v):
    bs = sorted(statistics.mean(rng.choices(v, k=len(v))) for _ in range(2000))
    return bs[50], bs[1949]


fig, axes = plt.subplots(1, 2, figsize=(8, 2.9))
for ax, j, ylab, top in ((axes[0], 1, "held-out best", 1.0), (axes[1], 2, f"intents named (of {len(labels)})", len(labels))):
    for i, arm in enumerate(ARMS):
        m = statistics.mean(arm[j]); lo, hi = ci(arm[j])
        ax.bar(i, m, width=0.6, color=arm[3], alpha=0.85 if i == 4 else 0.45, edgecolor=arm[3], linewidth=1.2)
        ax.errorbar(i, m, yerr=[[m - lo], [hi - m]], color="#0b0b0b", capsize=3, linewidth=1)
        ax.text(i, hi + top * 0.03, f"{m:.2f}" if j == 1 else f"{m:.1f}", ha="center", fontsize=8, color="#0b0b0b")
    ax.set_xticks(range(len(ARMS)), [a[0] for a in ARMS], fontsize=8, color="#52514e")
    ax.set_ylim(0, top * 1.15); ax.set_ylabel(ylab, fontsize=9, color="#52514e")
    ax.grid(axis="y", color="#e5e4e0", linewidth=0.6); ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color("#c3c2b7")
fig.tight_layout()
fig.savefig(OUT, dpi=200)
print(OUT, {a[0].replace("\n", " "): (round(statistics.mean(a[1]), 3), a[2]) for a in ARMS})
