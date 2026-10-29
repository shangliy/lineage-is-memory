"""Fig. 1: held-out best by disclosure, seed vs parent lineage, one panel per task (mean, 95% CI)."""

import random
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyze as Z  # noqa: E402

RUNS = Path(sys.argv[1]); OUT = Path(sys.argv[2])
REV = ["none", "first", "diverse", "minibatch", "cluster"]
COL = {"seed": "#eb6834", "parent": "#2a78d6"}
rng = random.Random(0)


def ci(v):
    bs = sorted(Z.mean([rng.choice(v) for _ in v]) for _ in range(2000))
    return bs[50], bs[1949]


hb = {}
for t in Z.PROMPT:
    hb[t] = {k: [r["holdout_best"] for r in v] for k, v in Z.by_key(Z.load_prompt(RUNS, t)).items()}
code = Z.load_code(RUNS)
for t in Z.CODE:
    hb[t] = {k: [r["holdout_best"] for r in v] for k, v in Z.by_key([r for r in code if r["task"] == t]).items()}

fig, axes = plt.subplots(1, 7, figsize=(14, 2.8), sharey=True)
for ax, t in zip(axes, hb):
    for row in ("seed", "parent"):
        keys = ["seed-none"] + [f"{row}-full-{x}" for x in REV[1:]]
        ys = [Z.mean(hb[t][k]) for k in keys]
        lo, hi = zip(*(ci(hb[t][k]) for k in keys))
        xs = range(len(REV))
        ax.fill_between(xs, lo, hi, color=COL[row], alpha=0.15, linewidth=0)
        ax.plot(xs, ys, color=COL[row], linewidth=2, marker="o", markersize=4, label=row)
    ax.set_title(t, fontsize=10, color="#0b0b0b")
    ax.set_xticks(range(len(REV)), REV, rotation=60, fontsize=8, color="#52514e")
    ax.grid(axis="y", color="#e5e4e0", linewidth=0.6); ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color("#c3c2b7")
axes[0].set_ylabel("held-out best", fontsize=9, color="#52514e")
axes[0].set_ylim(-0.02, 1.04)
axes[-1].legend(frameon=False, fontsize=8, loc="lower right", title="lineage", title_fontsize=8)
fig.tight_layout()
fig.savefig(OUT, dpi=200)
print(OUT)
