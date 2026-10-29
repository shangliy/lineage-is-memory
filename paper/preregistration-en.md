## Appendix A. Pre-registered tests

The pre-registrations were written in Chinese in `09-experiments.md` before each batch of runs, timestamped, and only appended to afterwards; each protocol was also registered with its success threshold in `experiments.json`. Below is an English translation of the tests. Where the translation and the original differ, the original governs. All intervals are 95% task-stratified bootstrap intervals (10,000 resamples of runs within each cell), and tasks are weighted equally.

**A.1 Main grid (2026-10-27; code frozen at git d5ab8923 plus `results/code/`, SHA256SUMS).** Model gpt-4.1-mini for task, proposer and clusterer (and for the replies judge, temperature 0). Seeds 0–9. Budget 8 evaluations for prompt tasks and 12 for code tasks. Metric: held-out score of the best search-set candidate; held-out data is never used for selection. Cells: `seed-none` and {seed, parent} × {first, diverse, minibatch, cluster} on seven tasks.

- *C2 (primary).* For X = diverse and X = cluster, I_X = mean over tasks of (X − first)_seed − (X − first)_parent. Supported if the lower bound of I_diverse > 0. R1 refutes if both I_diverse and I_cluster contain 0. R2 (collapse) if cluster − max(other disclosures) has lower bound > 0 in both rows.
- *C1 (crowding out).* In the seed row, coverage of unshown failure kinds, `seed-full-first` vs `seed-none`. Supported if the upper bound of (first − none) < 0 on at least two of labels, duration and size. R3: if every seed-row full-* minus seed-none contains 0 on ScoNe, C1 is narrowed to rules that can only be learned from feedback (ScoNe was flagged as near ceiling before running).
- *C3 (GEPA tokens).* Median tokens-to-solve, GEPA with early stopping vs `parent-full-first`. R4: if the ratio CI contains 1 on at least 3 of 5 tasks, C3 is restated as "the gap comes from missing early stopping".

**A.2 Sensitivity arm `sens-clustergold` (2026-10-27, registered after round-1 review and before running; code in `results/code_round1/`).** Only the cluster prompt changes: the representative failure now carries input, wrong answer and full expected answer. The pre-registered cluster results are kept and not replaced.

- *S1 (information loss).* On replies, parent clustergold − cluster has lower bound > 0, and at least 80% of the summaries keep the expected answer.
- *S2.* Parent clustergold − first on seven tasks: upper bound < 0 means summaries are harmful even with the target kept; an interval containing 0 means indistinguishable; lower bound > 0 favours full-failure diagnosis.

**A.3 Second-model replication `rep-haiku` (2026-10-27).** claude-haiku-5-5 as proposer and task model (default adaptive thinking); replies judge unchanged. Tasks: labels, routing, replies, duration, size. Cells: `seed-none`, {seed, parent} × {first, minibatch, clustergold}; n = 10.

- *H1.* Lineage main effect (mean of the three columns), lower bound > 0.
- *H2.* I_clustergold, lower bound > 0.
- *H3.* Parent clustergold − first, upper bound < +0.05.
- Any H that fails is reported as "does not hold on Haiku", without added cells.

**A.4 Extension (2026-10-28T16:05 −07:00; code in `results/code_round4/`, data hashes in `DATA_SHA256SUMS`).** Design choices fixed after smoke runs and before registration, with smoke runs excluded from analysis: Banking77 reduced from 20 to 12 intents because 20 gave at most 0.15 within 8 evaluations; for BBH salient-translation-error detection, the shared instructions and options were moved into the seed prompt, inputs longer than the 300-character feedback limit were dropped (198 of 250 kept), and the search set was raised from 2 to 3 per class after the 2-per-class smoke run overfit (search 1.0, held-out 0.50). One smoke run showed Banking77 parent clustergold 0.22 vs parent first 0.72 (n = 1); the tests were not changed.

- *`public-bench`.* gpt-4.1-mini on banking77 and bbh_ste, nine cells (`seed-none` and {seed, parent} × {first, diverse, minibatch, clustergold}) run interleaved. P1 lineage (four-column mean), lower bound > 0. P2 I_clustergold, lower bound > 0. P3 parent clustergold − first, upper bound < +0.05. P4 I_diverse, lower bound > 0. P5 parent minibatch − first, upper bound < 0. A task with seed-none ≥ 0.90 is treated as at ceiling and every test is reported with and without it. A failed test is reported as "does not hold on public benchmarks".
- *`gepa-public`.* GEPA 0.0.7 (minibatch 3, with and without early stopping), 10 runs per task, against `parent-full-first`. R4 holds on a task if both arms solve at least 3/10 and the ratio CI contains 1.
- *`strong-proposer`.* gpt-4.1 as proposer and clusterer, gpt-4.1-mini as task model and judge; labels, routing, replies; cells `seed-none`, {seed, parent} × {first, clustergold}. S1 lineage (mean of the two columns), lower bound > 0; S2 I_clustergold, lower bound > 0; S3 parent clustergold − first, upper bound < +0.05.
- *`rep-haiku-diverse`.* claude-haiku-5-5, {seed, parent}-full-diverse on the five replication tasks. Hd: I_diverse, lower bound > 0, using the first-k cells from `rep-haiku` (not interleaved).

**A.5 Fix arm `fix-carryfacts` (2026-10-28, written in `09-experiments.md` after the diagnosis of §4.3 and before any fix run; code in `results/code_round5/`).** One sentence (`CARRY_FACTS`, quoted in §4.3) is appended to the proposer's objective; nothing else changes. gpt-4.1-mini in all roles; banking77 and bbh_ste; cells `seed-full-first` and `parent-full-first`; n = 10; compared against `parent-full-first` and GEPA mb3 from A.4 (not interleaved). Because the fix was designed after seeing where GEPA won, the paper labels it post hoc in design.

- *F1.* Banking77 parent-carry − parent-first, lower bound > 0.
- *F2.* Banking77 GEPA − parent-carry: an upper bound ≤ 0 means the gap is explained by the meta-prompt; otherwise not fully explained.
- *F3 (no harm).* BBH parent-carry − parent-first, lower bound > −0.05.
- *F4.* Lineage under carry-facts (parent-carry − seed-carry, mean of both tasks), lower bound > 0.
- Outcome: F1, F2 and F4 hold; F3 fails (−0.061 [−0.119, −0.006]) and is reported in §4.8.
