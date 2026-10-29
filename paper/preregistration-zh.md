# Experiments & results

## 预注册（2026-10-27，运行前写定；之后只追加，不改）
代码冻结：git d5ab8923 + `results/code/`（tracked.patch 与 benchmarks 脚本快照，SHA256SUMS）。
模型：gpt-4.1-mini（任务、提议、聚类同一模型；replies 的 judge 同为 gpt-4.1-mini，温度 0）。
种子：repeat 0–9（n=10）。预算：prompt 任务 budget 8，代码任务 budget 12（与 pilot 相同）。
主指标：held-out 最好分（`holdout_best`，search 上最优候选在 held-out 上的得分）。held-out 只用于报告，不参与任何选择。

### 网格
- 任务：labels、dates、routing、replies、scone（prompt）；duration、size（代码）。
- 格子（9）：`seed-none`，`{seed,parent}-full-{first,diverse,minibatch,cluster}`。
- C1 干预：duration `seed-full-random`、`seed-full-iso`（对照 `seed-none`）。
- C3：GEPA 0.0.7 minibatch 3，有/无 `--early-stop`，5 个 prompt 任务。

### 预注册检验
- **C2（主检验）**：对 X ∈ {diverse, cluster}，交互 I_X = 平均_任务[(X − first)_seed − (X − first)_parent]，7 个任务等权；95% CI 用任务内按运行分层 bootstrap（10,000 次）。
  - 支持 C2：I_diverse 的 CI 下界 > 0。
  - **R1（反驳）**：I_diverse 与 I_cluster 的 CI 都含 0。
  - **R2（反驳/塌缩）**：cluster − max(其余 reveal) 在 seed 行和 parent 行（各自按任务等权平均）的 CI 下界都 > 0。
  - 次要：parent 行内各 reveal 两两差（first/diverse/minibatch/cluster）的 CI；预期全部含 0。
- **C1（挤出）**：seed 行里，种子提示的失败所属类别分成"展示过"和"未展示"（seed 行每次改写看到的都是种子的错例，所以集合固定）。指标：提议级未展示类别覆盖 = 在 search 集上把该类别全部答对的提议比例，对未展示类别取平均。比较 `seed-full-first` 与 `seed-none`。
  - 支持 C1：labels、duration、size 中至少两个任务上，差（first − none）的 CI 上界 < 0。代码任务另报 `anchoring.py` 干预的同一指标。
  - 反驳：上述条件不成立。
  - **R3**：scone 上 seed 行所有 full-* 与 seed-none 的 held-out 差 CI 都含 0 → C1 的范围收窄为"规则只能从反馈学到"。**已知风险**：冒烟显示 scone 接近天花板（seed-none 0.903），R3 成立时不能区分"无效应"与"测不出"，按边界条件报告。
- **C3（GEPA token）**：tokens-to-solve（解出 search 集的运行取中位数，另报 solved 比例），GEPA + 早停 vs `parent-full-first`。
  - **R4**：在 ≥3/5 个任务上，GEPA + 早停与 evolve 的 tokens-to-solve 中位数之比的 bootstrap CI 含 1 → C3 改述为"差距来自没有早停"。
  - 同时报告 GEPA 原样（无早停）的调用类型分解。

### 不做 / 推迟
- IFBench：验证器需要执行外部仓库代码，未获许可，推迟（写入局限）。
- claude-sonnet-5-5、claude-haiku-5-5 的 n=10：开跑前单独报价、单独确认。

## 结果
（运行后追加）

### 中断记录（2026-10-27）
17:26–17:47 之间 OpenAI 账户额度耗尽（429 "no credits remaining"），后台任务已停。
- 干净：labels、dates、routing（9 格 × 10）；duration、size（9 格 × 10 + C1 干预 random/iso）；GEPA ± 早停 × labels/dates/routing。
- 污染：replies `parent-full-cluster` repeat 5–9（held-out 0，额度错误），需删除重跑；其余 85 次可用。
- 未跑：scone 全部；GEPA ± 早停 × replies/scone。补跑用同一冻结代码与种子。

### 初步分析（5/7 任务：labels、dates、routing、duration、size；不是最终结论）
完整输出：`results/prelim-5tasks.txt`。检验定义按预注册，任务数少于预注册的 7 个。
- **C2**：I_diverse = +0.055 [+0.023, +0.087] → 方向支持；I_cluster = +0.092 [+0.047, +0.137]；R1 不成立。R2 不成立（cluster − 最好其他：seed 行 −0.017 [−0.055, +0.013]，parent 行 −0.042 [−0.068, −0.018]）。谱系主效应 +0.233 [+0.217, +0.248]。
  - **次要预期未达成**：parent 行两两差并非全部含 0——minibatch − first = −0.068 [−0.103, −0.034]，minibatch − diverse = −0.073，cluster − diverse = −0.028 [−0.056, −0.002]。即有谱系时 disclosure 仍有影响，主要是 GEPA 式随机 minibatch 更差。
  - dates 在 seed-none 已 1.000，属天花板，对交互贡献近 0。
- **C1**：2/3 构造任务支持挤出。duration first − none = −0.055 [−0.082, −0.033]，size −0.113 [−0.145, −0.082]；labels +0.018 [−0.031, +0.067]（不支持）。duration iso − none = −0.048 [−0.079, −0.021]，random − none = +0.061 [−0.003, +0.121]。
- **C3**：R4 不成立（0/3 个任务比值 CI 含 1）。GEPA+早停 / evolve tokens-to-solve：labels 3.34× [2.23, 4.49]，dates 2.59× [2.30, 4.82]，routing 解出太少（GEPA+早停 2/10 vs evolve 9/10）。早停不能解释差距；GEPA 原样 token 构成中 reflection 仅 2–15%。

### 补跑（2026-10-27 19:00–20:10，充值后）
同一冻结代码与种子。scone 9 格 × 10；GEPA ± 早停 × replies/scone；replies `parent-full-cluster` 整格重跑，取 repeat 5–9 替换污染运行（0–4 保留原值；原文件备份于 `runs/paper/gpt41mini/_failed_nocredit/`）。补跑日志无额度错误。
同种子重跑 repeat 0–4 的 held-out：原 0.875/0.438/0.750/0.188/1.000，重跑 0.625/0.188/0.750/0.000/1.000——replies cluster 格的运行内噪声很大，单次运行差 0.25 不罕见。
用量：全部 summary 合计约 31.6M tokens（含 held-out，不含 replies judge 缓存外调用的精确计数），按混合价 ≈$0.6/M 约 **$19**，高于预估 $12–18；准确花费以 OpenAI 账单为准。

## 结果（7 任务，n=10/格，750 次运行已写入 runs.jsonl）
完整输出：`results/final-7tasks.txt`。

| 检验 | 预注册阈值 | 结果 | 判定 |
|---|---|---|---|
| C2 | I_diverse CI 下界 > 0 | I_diverse = +0.068 [+0.043, +0.092]；I_cluster = +0.120 [+0.073, +0.167] | **支持** |
| R1 | I_diverse 与 I_cluster CI 都含 0 | 都不含 0 | 不成立 |
| R2 | cluster − 最好其他 两行 CI 下界都 > 0 | seed −0.044 [−0.078, −0.018]；parent −0.095 [−0.132, −0.063] | 不成立（cluster 两行都**更差**） |
| C2 次要 | parent 行两两差全部含 0 | minibatch − first −0.061 [−0.086, −0.035]；cluster − first −0.082 [−0.119, −0.045]；cluster − diverse −0.075；minibatch − diverse −0.054；diverse − first −0.007 [−0.025, +0.012] | **未达成**（first≈diverse > minibatch ≈ cluster） |
| C1 | labels/duration/size 中 ≥2 个 first − none CI 上界 < 0 | duration −0.055 [−0.082, −0.033]；size −0.113 [−0.144, −0.082]；labels +0.018 [−0.031, +0.067] | **支持（2/3）** |
| R3 | scone seed 行 full-* − none 全部含 0 | 四个差都在 ±0.01 内，CI 全含 0 | 成立 → C1 范围收窄为"规则只能从反馈学到"；scone 近天花板（0.89–0.92），按边界条件报告 |
| C3/R4 | ≥3/5 任务比值 CI 含 1 | labels 3.34× [2.23, 4.49]，dates 2.59× [2.30, 4.84]；routing/replies/scone 解出运行太少，比值不可估 | R4 不成立；但只有 2/5 任务可估比值 |

**C3 补充（如实报告）：** 解出率 evolve vs GEPA+早停：labels 7 vs 6，dates 10 vs 10，routing 9 vs 2，replies 10 vs 2，**scone 2 vs 4（GEPA 更好）**。held-out：routing 0.925 vs 0.842，replies 0.981 vs 0.850，scone 0.910 vs 0.899。GEPA 原样的 token 构成：reflection 只占 2–15%，全量重评 21–67%，minibatch 27–77%。早停只在 scone 上明显省 token（中位 tts 97.8k → 50.6k）。

**需要改写的论文表述：**
1. "有谱系时各 disclosure 打平"被否定：有谱系时 first/diverse 最好，随机 minibatch 和 cluster 显著更差（cluster 在 replies 上 0.519 vs first 0.981 是主要来源；在不含 replies、scone 的 5 任务初步分析中 cluster − first 为 −0.023 [−0.054, +0.008]，含 0）。
2. ESPO 式 cluster 摘要在本设置下不优于直接展示原样错例，两行都不优。
3. 挤出效应只在规则必须从反馈学的代码任务上出现（duration、size），labels 和 scone 上没有。
4. "GEPA 加早停能补上差距"被否定：差距不来自停止规则。

## 敏感性分析预注册：cluster-gold（stage 10 round 1，2026-10-27，运行前写定）
动机：round-1 发现 cluster 摘要在 replies 上只有 31/156 保留期望答案（其余任务 95–100%）。ESPO 的错例集为 (x, y, ŷ)。
改动：`factorial.CLUSTER_GOLD_PROMPT`，仅把"一条原样代表错误答案"改为"一条原样代表失败，附输入、错误答案与完整期望答案"。代码快照 `results/code_round1/`（SHA256SUMS）。其余与预注册网格完全相同（模型、种子 0–9、预算）。
格子：7 任务 × `{seed,parent}-full-clustergold` × 10。不覆盖、不替换预注册的 cluster 结果；论文中作为事后敏感性分析单独报告。
检验（任务等权，分层 bootstrap 10k）：
- **S1 信息丢失解释**：replies 上 parent 行 clustergold − cluster 的 CI 下界 > 0，且 replies 摘要保留期望答案的比例 ≥ 80%。
- **S2 "摘要本身有害"**：7 任务 parent 行 clustergold − first 的 CI 上界 < 0 → 支持"即使保留目标，摘要仍劣于原样错例"。CI 含 0 → 摘要与原样错例在有谱系时无法区分；CI 下界 > 0 → 保留目标的全量诊断优于 first（对 ESPO 有利，照实报告）。
- 次要：seed 行 clustergold − first；I_clustergold 交互。

### 敏感性分析结果：cluster-gold（2026-10-27，140 次运行，已写入 runs.jsonl 协议 `sens-clustergold`）
完整输出：`results/sens-clustergold.txt`（脚本 `results/sens_clustergold.py`）。日志无额度错误。用量约 4.5M tokens（≈$3，不含 judge 缓存外调用；以账单为准）。
摘要保留期望答案：labels 106/106、dates 25/25、routing 147/147、replies 65/65、scone 160/160。

| 检验 | 阈值 | 结果 | 判定 |
|---|---|---|---|
| S1 信息丢失 | replies parent clustergold − cluster CI 下界 > 0 且保留 ≥80% | +0.350 [+0.062, +0.612]；65/65 | **支持** |
| S2 摘要本身有害 | 7 任务 parent clustergold − first CI 上界 < 0 | −0.018 [−0.053, +0.010]（去掉 replies −0.002） | 不成立 → **无法区分** |
| 次要 seed 行 | clustergold − first | +0.156 [+0.122, +0.188]；对 diverse +0.095 [+0.058, +0.127] | seed 行最好的 reveal |
| 次要 交互 | I_clustergold | +0.174 [+0.127, +0.222] | 支持 C2 方向 |

补充：parent clustergold − minibatch +0.043 [+0.005, +0.075]；− diverse −0.011 [−0.045, +0.015]；routing 上 parent clustergold − first −0.083 [−0.158, −0.008]。clustergold 内谱系效应 +0.139 [+0.096, +0.182]。
**需要改写的论文表述：** "cluster 摘要两行都不优于原样错例"只对丢掉期望答案的摘要成立。保留期望答案后：无谱系时全量诊断是最好的展示方式；有谱系时与原样错例打平。结论从"扩大反思范围不帮忙"收窄为"扩大反思范围只在没有谱系时帮忙"。已改 draft 摘要、贡献 (2)、§4.2、§4.4、§4.5、局限。

## 第二模型复现预注册：claude-haiku-5-5（stage 10 round 3，2026-10-27，运行前写定）

动机：round 2 的 Soundness/Eval-fit 卡在"单模型"。只复现结论，不做新探索。

- 模型：proposer 与被优化模型都换成 `claude-haiku-5-5`（默认 adaptive thinking，effort 默认 medium，不另调）。replies 的评判模型保持 gpt-4.1-mini 不变。
- 任务（5）：labels、routing、replies、duration、size。dates、scone 不跑（前者近天花板/后者是边界条件）。
- 格子（7）：seed-none，{seed, parent} × {first(=full-k4), minibatch, clustergold}。n=10/格，共 350 次运行。预算与 gpt-4.1-mini 主网格相同（代码任务 budget 12）。
- 统计：与主分析相同的任务分层 bootstrap（10k），指标为 held-out best。

预注册检验（H 表示 Haiku 复现）：
- **H1 谱系主效应**：parent 行均值 − seed 行均值（first/minibatch/clustergold 三列平均）的 95% CI 下界 > 0 → 复现。
- **H2 I_clustergold**：(seed clustergold − seed first) − (parent clustergold − parent first) 的 CI 下界 > 0 → 复现。
- **H3 有谱系时扩大范围无收益**：parent clustergold − parent first 的 CI 上界 < +0.05 → 复现。
- 次要（只报告不判定）：parent minibatch − parent first 的符号；seed 行 clustergold 是否为最好展示方式。
- 任一 H 不复现：照实写成"在 Haiku 上不成立"，并在摘要中标注模型依赖性；不改检验、不加格子补救。

## 第二模型复现结果：claude-haiku-5-5（2026-10-28，部分：4/5 个任务）

**数据状态。** replies 的 64 次运行全部作废：评判模型 gpt-4.1-mini 从第一次调用起返回 429（OpenAI 额度耗尽），分数全为 0。已移到 `runs/paper/haiku55/replies_INVALID_openai_credit/`，不进入分析。其余 4 个任务（labels、routing、duration、size）日志里没有额度错误，7 格 × n=10 完整，共 280 次运行，已记入 runs.jsonl（protocol `rep-haiku`）。replies 待 OpenAI 充值后重跑，在那之前本节结论只覆盖 4 个任务。

脚本：`results/rep_haiku.py`；完整输出：`results/rep_haiku.txt`。

| task | seed-none | seed first | seed minibatch | seed clustergold | parent first | parent minibatch | parent clustergold |
|---|---|---|---|---|---|---|---|
| labels | 0.671 | 0.725 | 0.775 | 0.904 | 0.958 | 0.950 | 0.992 |
| routing | 0.000 | 0.500 | 0.508 | 0.792 | 0.950 | 0.758 | 0.917 |
| duration | 0.954 | 0.863 | 0.942 | 0.942 | 1.000 | 0.988 | 1.000 |
| size | 0.650 | 0.817 | 0.863 | 0.838 | 1.000 | 0.971 | 1.000 |

**预注册检验（4 任务，分层 bootstrap 10k）。**
- H1 谱系主效应 = +0.168 [+0.151, +0.185] → **成立**（gpt-4.1-mini：+0.238）。
- H2 I_clustergold = +0.143 [+0.111, +0.174] → **成立**（gpt-4.1-mini：+0.174）。
- H3 parent clustergold − first = −0.000 [−0.009, +0.009]，上界 < +0.05 → **成立**。

**次要（只报告）。** parent minibatch − first = −0.060 [−0.089, −0.034]，与 gpt-4.1-mini 同号（−0.061）。seed 行 clustergold 是最好的展示方式：比 first 高 +0.143 [+0.112, +0.172]，比 minibatch 高 +0.097 [+0.056, +0.136]。

**稳健性（事后）。** 去掉任一任务后，H1、H2 的 CI 都在 0 以上；H3 的上界都 < +0.02。按任务看，size 上 H2 的 CI 含 0（+0.021 [−0.058, +0.104]），labels 上 parent clustergold 比 first 高 +0.033（显著但小于 +0.05 的界限）。

### 补跑 replies 后的最终结果（2026-10-28，5/5 个任务）

OpenAI 充值后单独补跑了 replies（70 次，评判调用全部正常，看门狗未触发），已记入 runs.jsonl。`rep-haiku` 共 350 次有效运行，与预注册一致。

| task | seed-none | seed first | seed minibatch | seed clustergold | parent first | parent minibatch | parent clustergold |
|---|---|---|---|---|---|---|---|
| replies | 0.044 | 0.312 | 0.444 | 0.637 | 0.988 | 0.762 | 0.950 |

**预注册检验（5 任务）。**
- H1 = +0.222 [+0.204, +0.239] → **成立**（gpt-4.1-mini 主网格 +0.238）。
- H2 I_clustergold = +0.187 [+0.152, +0.221] → **成立**（gpt-4.1-mini +0.174）。
- H3 parent clustergold − first = −0.008 [−0.017, +0.002] → **成立**。

**次要。** parent minibatch − first = −0.093 [−0.123, −0.067]；seed 行 clustergold 比 first 高 +0.179，比 minibatch 高 +0.116。replies 上 parent clustergold 比 first 低 −0.038 [−0.062, −0.012]（与 gpt-4.1-mini 的 routing 同向）。去掉任一任务，H1、H2 的 CI 都大于 0，H3 的上界都 ≤ +0.009。以上一节（4 任务）的结论保留作为记录，本节取代它作为最终结果。

## 扩展实验预注册（stage 10 round 4，2026-10-28，运行前写定；之后只追加，不改）

用户批准 A–D 四组，上限从 $40 提到 $50。四组都用 n=10，分层 bootstrap 10k，所有 CI 为 95%。

**设计在冒烟测试后、注册前定下（冒烟运行不进入分析）：**
- banking77：用 20 个意图时，8 次评估内最好只到 0.15（有地板效应），所以改为 12 个意图。每个意图 2 条搜索、3 条 held-out（共 24/36）。
- bbh_ste：
  - 每条输入共享的任务说明和选项表挪进种子提示，输入只保留源句和译句。
  - 超过反馈显示上限 300 字的输入不用（250 条剩 198 条）。
  - 每类 2 条搜索时，parent 行搜索集到 1.0，但 held-out 只有 0.50，过拟合明显，所以改为每类 3 条搜索、6 条 held-out（共 18/36）。
- 冒烟测试里看到一次 banking77 parent clustergold = 0.22，低于 parent first 的 0.72。这是 n=1 的结果，下面的检验没有因此改动。

### A+B `public-bench`：两个公开基准，gpt-4.1-mini，9 个格子交错运行
- 任务：banking77（Casanueva et al. 2020）、bbh_ste（BBH salient_translation_error_detection）。
- 格子：seed-none 加 {seed, parent} × {first, diverse, minibatch, clustergold}，共 9 格 × 10 = 180 次运行。四种展示方式同批交错，用来回应"clustergold 是事后单独跑的"这一质疑。
- 检验（两个任务合并，任务分层）：
  - P1 谱系主效应：四列平均的 parent − seed，CI 下界 > 0。
  - P2 I_clustergold：CI 下界 > 0。
  - P3 parent clustergold − first：CI 上界 < +0.05。
  - P4 I_diverse：CI 下界 > 0。
  - P5 parent minibatch − first：CI 上界 < 0。
- 天花板规则：某任务 seed-none 的 held-out 均值 ≥ 0.90 时，该任务按天花板处理，检验同时报告含它和不含它两个版本。
- 任一检验不成立：照实写成"在公开基准上不成立"，不加格子补救。按任务的结果也一并报告。

### C `gepa-public`：GEPA 0.0.7 在 A、B 上的对照
- GEPA mb3、mb3 加 early-stop，各 10 次，任务调用预算 8 × 搜索集大小，与已有 C3 相同。
- 对照组是 `public-bench` 的 parent-full-first。
- 检验（沿用 C3 的 R4）：
  - 在双方都至少 3/10 解出的任务上，GEPA+stop 与 evolve 的 tokens-to-solve 比值的 CI 含 1，算作 R4 在该任务上成立。
  - 解出次数和 held-out 只报告。

### D1 `strong-proposer`：gpt-4.1 当提议者和聚类者，gpt-4.1-mini 当任务模型
- 这是 GEPA 常见的"强反思模型 + 小任务模型"配置。
- 任务：labels、routing、replies。replies 的评判模型仍是 gpt-4.1-mini。
- 格子：seed-none、seed-first、seed-clustergold、parent-first、parent-clustergold，共 5 格 × 3 任务 × 10 = 150 次运行。
- 检验沿用 Haiku 复现的 H1–H3，阈值不变：
  - S1：first 与 clustergold 两列平均的谱系主效应，CI 下界 > 0。
  - S2：I_clustergold，CI 下界 > 0。
  - S3：parent clustergold − first，CI 上界 < +0.05。
- 次要（只报告）：
  - 对比 gpt-4.1-mini 提议者在同任务、同格子上的 held-out，也就是强提议者带来的增益。
  - seed 行的差距是否缩小。

### D2 `rep-haiku-diverse`：给 Haiku 补上 diverse 臂
- claude-haiku-5-5，seed-full-diverse 和 parent-full-diverse，跑 Haiku 复现的 5 个任务，共 2 格 × 5 × 10 = 100 次运行。
- 检验 Hd：I_diverse = (seed diverse − seed first) − (parent diverse − parent first)，CI 下界 > 0。
- first 列取自 `rep-haiku`，两批不是交错运行的，这一点写入局限。
- 次要：parent diverse − first。

### 第 4 轮中断记录（2026-10-28T16:29:57-07:00；在看任何 BBH 结果之前写定）
- 16:28 OpenAI 额度耗尽（429 insufficient_quota），看门狗停掉了所有任务（exit 3）。
- 有效且完整（额度耗尽前跑完，日志无报错）：banking77 9 格 × 10；strong-proposer labels、routing；rep-haiku-diverse labels、routing、replies。
- 作废：
  - bbh_ste 已完成的 90 个运行文件里，最后几个运行时碰上了 429，而且进程在写 summary.json 之前就被停了（token 记录丢失）。
  - 规则：**bbh_ste 整个 9 格 × 10 全部重跑**，不按单个运行挑选。被打断的 parent-full-clustergold 格已移到 `runs/paper/_failed_nocredit_r4/`；其余 80 个文件不进入分析，只作为存档。
  - strong-proposer replies（10/50，评判调用报错）：整组重跑。
  - rep-haiku-diverse 代码任务（被看门狗连带停掉，没有额度问题）：整组重跑，已用 Anthropic 重新开始。
  - gepa-public：还没有开始。
- 预注册检验不变。

补记（2026-10-28 晚，补跑启动前）：run13 的看门狗退出后，`gepa_baseline.py --task banking77` 进程没有被 pkill 杀掉，在无额度状态下又空转约 3.5 小时（日志中约 5000 次 429 `credit_balance_exhausted`），没有产出任何结果文件。该日志已归档到 `runs/paper/_failed_nocredit_r4/gepa/`，不参与分析。充值后用两次极小请求（gpt-4.1-mini、gpt-4.1）确认额度可用，然后启动补跑 run14（bbh_ste 9×10 整格、强提议者 replies 5×10、两个公开任务上的 GEPA mb3 与 mb3-stop 各 10 次）。检验与规则不变。

## 第 5 轮：Banking77 上 GEPA 胜出的诊断与修复（预注册于 2026-10-28T21:03:49-07:00，在看任何修复结果之前写定）

### 第 4 轮结果（已记录于 results/round4.txt，原样保留）
P1 合并成立（+0.088 [+0.045, +0.130]），P2–P5 在公开基准上不成立；S1–S3、Hd 成立。
GEPA（mb3）− parent-full-first 留出：Banking77 +0.292 [+0.111, +0.464]；BBH −0.019 [−0.050, +0.014]。两任务均 0/10 解决，R4 无法判定。

### 免费诊断（只读日志，未花钱）
1. **零平台停滞**：Banking77 种子提示 0.00（标签词表未知，精确匹配）。第 1 代候选多只改输出格式（snake_case），仍为 0，最佳父代始终是种子；2/10 次运行（重复 8、9）8 个候选全为 0，最终提示即 36 字符种子。谱系在全 0 平台上不起作用。
2. **事实转写**：反馈中出现 12 个标签名。evolve parent-full-first 最佳提示中写入的标签数 [6,11,4,11,7,9,4,4,0,0]，与留出分数 [.47,.69,.31,.75,.39,.58,.22,.31,0,0] 同步；GEPA mb3 最佳提示写入 [6,8,11,9,6,9,9,9,10,7]（中位 9）。GEPA 0.0.7 反思提示明确要求"Identify all niche and domain specific factual information about the task and include it in the instruction"；AdalFlow 的 LLMProposer 目标里没有这句。BBH 没有需要转写的词表，两者打平，与此解释一致。
结论（假设）：差距来自提议者元提示是否要求把反馈中的事实写进提示，而非 GEPA 的搜索结构（小批量、Pareto）。

### 修复臂 fix-carryfacts（预注册）
- 改动只有一处：`prompt_anchoring.py --carry-facts` 在目标后追加一句 CARRY_FACTS（要求把反馈中暴露的任务事实，如精确标签，写进提示）。其余设置与第 4 轮相同。代码冻结于 results/code_round5/（SHA256SUMS）。
- 运行：gpt-4.1-mini；banking77、bbh_ste；单元 seed-full-first、parent-full-first（均加 --carry-facts）；各 10 次，交错运行。估计 ~$1.5–2.5。
- 检验（自助法同前，按次重抽 10k）：
  - **F1**（修复有效）：Banking77 parent-carry − parent-full-first（第 4 轮），下界 > 0。
  - **F2**（差距被解释）：Banking77 GEPA mb3 − parent-carry 的区间包含 0 或上界 < 0 → "差距由元提示解释"；下界 > 0 → "差距未被完全解释"，如实报告。
  - **F3**（无害）：BBH parent-carry − parent-full-first，下界 > −0.05。
  - **F4**（主结论在修复后仍在）：两任务合并，parent-carry − seed-carry，下界 > 0。
  - 机制检查（只报告）：最佳提示中写入的标签数。
- 第 4 轮所有结果保留不替换；修复臂是新增臂，不回改 P1–P5 的判定。

### 第 5 轮结果（results/round5.txt；40 次运行已记入 runs.jsonl，协议 fix-carryfacts）
| 任务 | parent-first（第 4 轮） | seed-carry | parent-carry | GEPA mb3 |
|---|---|---|---|---|
| banking77 | 0.372 | 0.317 | 0.856 | 0.664 |
| bbh_ste | 0.653 | 0.614 | 0.592 | 0.633 |

- F1 成立：+0.483 [+0.328, +0.644]。
- F2：GEPA − parent-carry = −0.192 [−0.289, −0.097]，差距由元提示解释（且修复后反超 GEPA）。
- **F3 不成立**：BBH parent-carry − parent-first = −0.061 [−0.119, −0.006]，修复在 BBH 上有小幅损害。
- F4 成立（合并）：+0.258 [+0.221, +0.296]；banking77 +0.539，bbh_ste −0.022 [−0.086, +0.039]（区间含 0）。
- 机制：最佳提示写入的标签数，parent-carry [11,12,12,11,12,11,12,12,12,12]，seed-carry 全为 4（每代只看到同样的前 k 个错例），parent-first（第 4 轮）[6,11,4,11,7,9,4,4,0,0]。谱系让写进提示的事实跨代累积；没有谱系时每代从种子重来，只能写进当代看到的那几个。
- 零分运行：parent-first 2/10 → parent-carry 0/10。token/次：parent-carry 约 46k / 55k，GEPA 107k / 122k（约 2.2–2.3×）。
- 说明：carry-facts 是看到第 4 轮 GEPA 结果之后才设计的（事后诊断 + 预注册确认），只在两个任务上测过，论文中须如实标明。
- 分析脚本小修：labels_named 读错字段（prompt→text），只影响机制计数，不影响 F1–F4。
