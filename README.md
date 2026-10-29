# Lineage Is Memory

Code, run summaries and pre-registrations for **"Lineage Is Memory: Build on the Best
Parent and Let It Accumulate What Feedback Reveals"** ([paper/paper.pdf](paper/paper.pdf); arXiv link: TODO).

In LLM-guided prompt evolution, *building on the best parent* (lineage) is the main
lever, and it works as memory: facts the feedback reveals accumulate in the prompt
across generations, but only if the proposer is asked to write them in.

| result (gpt-4.1-mini, 10 seeds) | value |
|---|---|
| lineage main effect, 7 tasks | +0.238 [+0.224, +0.252] |
| same on claude-haiku-5-5, 5 tasks | +0.222 [+0.204, +0.239] |
| Banking77 held-out: parent + carry-facts vs GEPA 0.0.7 | 0.856 vs 0.664, 2.3x fewer tokens |
| stronger proposer (gpt-4.1) over gpt-4.1-mini, parent-first | -0.019 [-0.053, +0.014] |

Boundary conditions (all pre-registered, reported in Section 4.8): the carry-facts
sentence costs 0.061 on BBH salient-translation-error detection, and several
disclosure-interaction tests do not hold on public benchmarks.

## Use it

The method ships as the default of AdalFlow's `optimize_prompt`:

```python
from adalflow.optim.evolution import optimize_prompt

result = optimize_prompt("Classify the banking query.", examples, model="openai/gpt-4.1-mini")
print(result.report())  # carry_facts=True by default; pass carry_facts=False for fixed-option tasks
```

## Reproduce

```bash
pip install -r requirements.txt
bash data/fetch_data.sh                              # Banking77 + BBH, hash-checked
CHECK=1 bash benchmarks/evolution/reproduce_banking77.sh   # fake models, no API
OPENAI_API_KEY=... bash benchmarks/evolution/reproduce_banking77.sh   # about $1
```

Every table and figure in the paper comes from the run logs:

```bash
mkdir -p runs && tar -xzf results/runs.tar.gz -C runs   # runs/paper/...
python analysis/analyze.py --runs runs/paper/gpt41mini       # main grid (Section 4.1, 4.4-4.7)
python analysis/round4.py --root runs/paper                  # public benchmarks, GEPA, strong proposer
python analysis/round5.py --root runs/paper                  # carry-facts fix (Section 4.3)
python analysis/fig2.py runs/paper paper/figs/fig2-banking77-carry.png
```

The other scripts in `analysis/` cover the clustergold sensitivity arm, the Haiku
replication, and the robustness checks. Their `--log` flag writes to a private
tracker and is not needed.

## Layout

- `benchmarks/evolution/`: tasks, the lineage x disclosure grid (`prompt_anchoring.py`),
  the GEPA baseline (`gepa_baseline.py`), code tasks, LLM-judge task. Same as
  AdalFlow `benchmarks/evolution` at the commit pinned in `requirements.txt`.
- `analysis/`: the scripts that compute every number in the paper (task-stratified
  bootstrap, 10,000 resamples).
- `results/runs.tar.gz`: every reported run (summaries plus per-candidate logs with each prompt and its feedback);
  runs invalidated by API credit errors are left out, local paths replaced by `~`.
- `paper/`: PDF, LaTeX, figures, and the pre-registrations: Chinese original
  (`preregistration-zh.md`, timestamped, append-only; it governs) and English
  translation (`preregistration-en.md`).

## Cite

See [CITATION.cff](CITATION.cff), or:

```bibtex
@misc{lineage-is-memory-2026,
  title  = {Lineage Is Memory: Build on the Best Parent and Let It Accumulate What Feedback Reveals},
  author = {TODO},
  year   = {2026},
  eprint = {TODO},
  archivePrefix = {arXiv},
}
```

Data: Banking77 (Casanueva et al. 2020, CC BY 4.0), BIG-Bench Hard (Suzgun et al. 2023,
MIT), ScoNe (She et al. 2023, CC0); not redistributed here.
