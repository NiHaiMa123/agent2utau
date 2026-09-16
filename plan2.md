# agent2utau — Plan 2：GAME 主转谱 + 证据驱动校正 + 分阶段演唱建模

> 修订日期：2026-09-16
>
> 核心原则：**先把“唱对”解决，再把“唱得像泠鸢”解决。**
>
> 当前工程原则：**GAME 提供真实可渲染的乐谱候选；多次 GAME consensus 只作为 uncertainty / evidence graph。先把 residual errors 筛到很少并校准 precision，再允许自动 repair。**

---

## 1. 项目目标

输入一首原曲后，系统最终应自动完成：

```text
原曲
→ 人声 / 伴奏分离
→ GAME 多次转谱
→ 选择真实 GAME medoid run 作为 Candidate 0
→ 多 run consensus uncertainty graph
→ RMVPE + FCPE 双 F0 证据
→ stable plateau / changepoint / onset / energy / lyric evidence
→ residual-error triage
→ 只修强证据局部错误
→ lyrics ↔ melody mapping
→ OpenUtau / DiffSinger 基础渲染
→ constrained PITD / 演唱细节
→ 最后再做泠鸢风格迁移
```

旧主旋律生成方式：

```text
歌词字窗口
→ F0 中位数
→ heuristic split
→ MIDI note
```

已确认能力不足，只保留为显式 fallback，不再作为默认 melody transcription。

---

# Part A — 已确认的基础事实

## 2. 当前已完成基础设施

仓库已经真正接入：

- 官方 GAME 1.0.3-medium ONNX；
- 官方 RMVPE ONNX；
- FCPE；
- GAME `encoder → segmenter → bd2dur → estimator`；
- OpenUtau AudioSlicer 等价切片；
- GAME 同配置多次运行；
- `diagnose --repeats N`；
- order-preserving sequence alignment；
- `1↔1 / gap / 1↔2 / 2↔1` 显式关系；
- GAME stochastic consensus；
- voiced-island structural F0；
- RMVPE / FCPE evidence packets；
- lyric-boundary evidence；
- GAME USTX + DiffSinger render；
- medoid baseline selection；
- stable plateau detection；
- residual-error triage。

forced char `known_boundaries` 路径只保留实验用途，不进入默认主链。

---

## 3. GAME 是主转谱基座，不再用 F0 heuristic 重建整首 MIDI

早期 forced-boundary 实验曾出现：

```text
A raw ≈ 419 notes
B zh  ≈ 417 notes
C forced-char-boundary ≈ 760 notes
```

C 上的：

```text
76 suspicious
54 wrong_pitch
```

不能代表 GAME raw 错误率，因为强制字符边界本身改变了 segmentation 和 estimator。

因此固定原则：

- GAME raw 是主 melody transcription 来源；
- lyric char start 不是天然 note boundary；
- RMVPE / FCPE 是 evidence，不是全曲主转谱器；
- correction 的目标是修少量 GAME residual errors，而不是重写整首谱。

---

## 4. GAME 存在真实 stochasticity

《年轮》同输入、同参数多次 raw GAME：

```text
约 418–425 voiced notes / run
```

所以：

```text
single GAME run != deterministic truth
```

但 stochasticity 本身是有用 evidence：

- 多次都一致 → 更可信；
- split / merge / pitch 多解 → 局部不确定；
- 自动 repair 不能依赖单次 GAME。

---

## 5. M2.2A — Formal sequence alignment ✅

旧的 `150 ms onset greedy clustering` 已废弃为正式依据。

当前 `diagnostic/seqalign.py`：

```text
order-preserving DP
+ onset cost
+ IoU / overlap cost
+ duration cost
+ capped weak-pitch cost
+ gap
+ split
+ merge
```

显式表示：

```text
1 ↔ 1   same-note candidate
1 ↔ 0   missing
0 ↔ 1   extra
1 ↔ 2   split disagreement
2 ↔ 1   merge disagreement
```

最新 5+5 GAME runs 的 raw consensus evidence graph：

```text
397 events
348 GAME_STABLE
2   GAME_VARIABLE
47  GAME_UNSTABLE
43  events 有 split/merge structure variance
```

这说明 GAME 主体旋律稳定，真正需要关注的是局部区域。

---

## 6. Consensus 只是 evidence graph，不是最终谱面

必须长期保持：

```text
397 consensus events != 最终 397 notes
```

包含 split / merge 的 component 表示：

> 多次 GAME 对这一局部 musical region 的结构解释不同。

它不是一颗最终 MIDI note。

禁止把：

```text
start_median
duration_median
tone_median
```

直接拼成 synthetic USTX。

`event_as_note()` 只能用于 diagnostic / cross-consensus comparison。

union-find component 也只表示 uncertainty region；由于存在 transitive bridging 风险，不负责决定唯一结构。

---

## 7. 最终 Candidate 0 必须来自真实 GAME run

正式策略：从多次 raw GAME 中选 **medoid run**：

```text
对其他 runs 的总 pairwise alignment cost 最小
```

当前《年轮》M2.3 run 已选出：

```text
Candidate 0 = raw GAME run 3
voiced notes = 416
```

这样：

- 每颗 baseline note 都来自真实 GAME 推理；
- 不会产生不存在于任何 run 的 synthetic structure；
- repair 可以逐项 audit / rollback；
- corrected score 永远能和 Candidate 0 做 A/B。

---

# Part B — F0 / Structural Evidence

## 8. M2.2B — Dual-F0 ✅

RMVPE + FCPE 必须共同参与 hard-pitch judgement。

189.84s 已成为关键 regression case：

```text
GAME   ≈ MIDI 58.1
FCPE   ≈ MIDI 58.03
RMVPE  ≈ MIDI 69.96
```

RMVPE 与 FCPE 相差约一个 octave。

工程结论：

> **F0_EXTRACTOR_CONFLICT；没有足够证据修改 GAME。**

这证明：任何单一 F0 extractor 都不能独自推翻 GAME。

189.84s 必须永久保留为 regression case，确保未来规则不会重新把它误修成 octave correction。

---

## 9. Structural F0

当前处理：

```text
raw F0
→ 仅填 <=40 ms 短 unvoiced gap
→ 按连续 voiced island 独立 filtering
→ structural F0
```

职责：

- structural F0：note / plateau / boundary / changepoint evidence；
- raw F0：PITD / vibrato / portamento / intonation。

所有 pitch error / dispersion 对外统一 cents。

`high_dispersion` 只保留为 feature，不单独触发 suspicious。

---

## 10. Full-window median 只适用于结构稳定区域

对稳定 note，GAME note window 内的 F0 median 有用。

但对：

- split；
- merge；
- missed split；
- portamento；
- 快速转音；
- grace / ornament；

必须优先看 plateau / changepoint，而不是整段 median。

结构 evidence 应尽量独立计算：

```text
RMVPE raw / structural F0
→ RMVPE plateaus + changepoints

FCPE raw / structural F0
→ FCPE plateaus + changepoints
```

不能只用 RMVPE structural plateau，再把“FCPE 有 F0”当成双结构确认。

---

# Part C — Lyrics Evidence

## 11. Lyric timestamp 永远不是默认 note boundary

必须区分：

```text
Whisper char start
辅音起点
元音起点
F0 voiced onset
GAME note onset
```

歌词只用于：

```text
matching
articulation evidence
weak boundary-snap evidence
missing-boundary evidence
lyrics ↔ notes mapping
```

禁止：

```text
char start → 强制新增 GAME boundary
```

只有：

```text
GAME boundary / structure 不稳定
+
RMVPE / FCPE changepoint 支持
+
energy / onset 支持
+
lyric articulation 支持
```

才允许生成 boundary repair candidate。

---

# Part D — M2.3 Residual-Error Triage ✅ 初版完成

## 12. 当前《年轮》真实 triage 结果

Candidate 0：

```text
GAME medoid run 3
416 voiced notes
```

当前 triage：

```text
312 GAME_LIKELY_CORRECT
47  STRUCTURE_HARD_SUSPICIOUS
37  NEEDS_LISTENING_REVIEW
16  F0_EXTRACTOR_CONFLICT
3   AMBIGUOUS_ORNAMENT
1   PITCH_HARD_SUSPICIOUS
```

这说明系统已经把原先几百个粗糙 feature flag 压缩成较小的 review set。

但：

> **这些分类仍是 validator 输出，不等于 confirmed error 数量。**

特别是 47 个 `STRUCTURE_HARD_SUSPICIOUS` 当前不能解释成 47 个确定的 split / merge 错误。

---

## 13. 202.52s — 首个强 pitch-error 候选

当前 evidence：

```text
GAME ≈ 65.3
RMVPE ≈ 72.30
FCPE ≈ 72.31
RMVPE / FCPE IQR ≈ 低且稳定
structural plateau ≈ 72.28
GAME 多次运行高度一致
```

差约：

```text
+700 cents
```

它是目前最强的 GAME wrong-pitch candidate。

但是正式表述应是：

> **first SAFE-retune benchmark candidate**

而不是在 A/B audition 之前直接写成“confirmed error”。

M2.3.1 必须用它校准完整 SAFE gate。

---

# Part E — 当前最高优先级：M2.3.1 Triage Calibration

## 14. 为什么不能直接进入 M2.4

当前 `PITCH_HARD_SUSPICIOUS` 规则主要依赖：

```text
RMVPE + FCPE agree
AND both oppose GAME
AND 两个 extractor IQR 足够低
```

但正式 SAFE repair 还缺少：

- GAME presence / tone consensus gate；
- `structure_varies = false` gate；
- single stable plateau gate；
- plateau center 与双 F0 center 的一致性；
- 局部 A/B render；
- human listening benchmark。

另外当前 structure triage 仍主要使用 RMVPE structural plateau，47 个 structure-hard 的 precision 尚未校准。

因此：

> **M2.3.1 未完成前，禁止进入自动 SAFE repair。**

---

## 15. 收紧 PITCH SAFE gate

`PITCH_HARD_SUSPICIOUS` 和 `SAFE_RETUNE_CANDIDATE` 必须拆开。

### PITCH_HARD_SUSPICIOUS

程序发现：

```text
RMVPE + FCPE agree
AND 两者共同反对 GAME > calibrated threshold
AND voiced evidence 充分
```

只表示“值得重点验证”。

### SAFE_RETUNE_CANDIDATE

至少同时满足：

```text
1. GAME presence_rate 高，优先 5/5
2. GAME tone agreement 高
3. consensus structure 不存在 split / merge ambiguity
4. structure_varies = false
5. aligned note identity 清楚
6. RMVPE 与 FCPE center 接近
7. RMVPE IQR 低
8. FCPE IQR 低
9. 两者共同反对 GAME，差值足够大
10. stable plateau 数 = 1
11. plateau center 与双 F0 center 一致
12. 前后相邻 note 不支持另一种合理解释
13. repair 仅修改当前 note pitch
14. before / after render 可生成
15. 首批 benchmark 经人工听感确认
```

缺任一关键证据 → `NEEDS_LISTENING_REVIEW` 或 `AMBIGUOUS`，不得 SAFE auto-fix。

---

## 16. 202.52s benchmark 验收

必须输出局部完整包：

```text
202.52s 附近原唱混音片段
separated vocal 片段
GAME Candidate 0 render
retune candidate render
GAME 5 runs note evidence
consensus evidence
RMVPE raw / structural F0
FCPE raw / structural F0
plateau evidence
local neighbours
repair diff
```

用户试听后：

- 若原唱与 retune candidate 明显一致 → 标记首个 confirmed SAFE-retune case；
- 若存在音乐语义歧义 → 降级 AMBIGUOUS；
- 不允许仅因数值好看自动通过。

该案例通过后，才能把同一 gate 推广到全曲其他 pitch-hard regions。

---

## 17. Structure-hard 必须降级为 structure candidates

当前 47 个 `STRUCTURE_HARD_SUSPICIOUS` 在校准完成前统一解释为：

```text
STRUCTURE_CANDIDATE
```

不是 confirmed structure error。

正式 hard structure evidence 要求：

```text
GAME runs 有明确 1↔2 / 2↔1 / missing / extra disagreement
AND RMVPE structural F0 支持特定 plateau / changepoint
AND FCPE structural F0 独立支持相近 plateau / changepoint
AND 两个 extractor 的 transition timing 足够接近
AND onset / energy 支持该 boundary
AND 新结构 duration 合理
```

歌词 evidence 可辅助，但不能单独决定 split / merge。

---

## 18. 双结构证据

新增每个 structure candidate 的字段：

```text
rmvpe_plateaus
fcpe_plateaus
rmvpe_changepoints
fcpe_changepoints
plateau_count_agreement
plateau_pitch_agreement
changepoint_time_delta_ms
boundary_onset_support
energy_support
lyric_support
```

建议第一版硬 gate：

```text
plateau count 一致
AND 对应 plateau pitch 接近
AND changepoint timing 在 calibrated tolerance 内
```

如果 RMVPE / FCPE 对结构本身不一致：

```text
F0_STRUCTURE_CONFLICT / AMBIGUOUS
```

禁止自动 split / merge。

---

## 19. Structure triage precision calibration

不要一次处理 47 个。

先从 47 个 structure candidates 中抽取至少 10 个，尽量覆盖：

```text
1↔2 split
2↔1 merge
多 plateau
single plateau but GAME splits
快速转音
portamento
vibrato
短 note
```

每个样本输出：

```text
GAME 5-run local piano roll / JSON
medoid baseline
RMVPE plateau / changepoint
FCPE plateau / changepoint
onset / energy
source vocal clip
baseline render clip
候选结构 render（仅用于人工比较，不自动采用）
```

人工确认：

```text
true structure error
GAME acceptable representation
ornament ambiguity
F0 extractor artifact
alignment artifact
```

统计 precision：

```text
confirmed structure errors / reviewed structure candidates
```

若 precision 偏低，继续校准 validator，不进入 split / merge auto-repair。

---

## 20. 37 个 NEEDS_LISTENING_REVIEW

当前其中很多是：

```text
双 F0 center 大致一致
但 vibrato / transition 导致 full-window IQR 高
GAME vs median 偏约 100–190 cents
```

这些不能因为“双 F0 agree”就自动 retune。

优先用：

- stable plateau center；
- note interior center；
- local melodic context；
- neighbouring GAME notes；

重新筛选。

大部分预计会回落到：

```text
GAME_LIKELY_CORRECT
```

或：

```text
AMBIGUOUS_ORNAMENT
```

而不是 repair candidate。

---

## 21. 16 个 F0_EXTRACTOR_CONFLICT

默认：

```text
NO AUTO REPAIR
```

保留到：

- 第三 evidence source；
- source listening；
- 或后续更强局部模型；

再处理。

当前不需要为了消灭这些 conflict 立即接 ROSVOT。

如果 conflict 数量和实际影响很小，保持 unresolved 更安全。

---

## 22. M2.3.1 输出

新增：

```text
runs/<id>/diagnostic/
  baseline_game.json
  residual_triage.json
  residual_triage_summary.json
  pitch_safe_candidates.json
  structure_candidates.json
  structure_dual_f0_evidence.json
  calibration_review_set.json
  calibration_results.json
  regression_cases/
    189.84_f0_conflict.json
    202.52_pitch_candidate.json
```

summary 必须严格区分：

```text
feature
candidate
hard suspicious
human confirmed error
safe repair candidate
```

禁止把 candidate count 当 confirmed error count。

---

# Part F — Repair Engine

## 23. M2.4 — SAFE repair 的进入条件

只有 M2.3.1 完成后才允许开始。

进入条件：

```text
202.52s benchmark 已人工确认
PITCH SAFE gate 固化并有 regression test
structure-candidate precision 已知
189.84s regression 不会被误修
```

第一版 repair 只实现已经真实确认且规则简单的类型。

如果最终只有少量 pitch errors，就只做轻量 retune，不为了“完整性”开发重型 repair engine。

---

## 24. Candidate 0 与修复审计

永久保留：

```text
Candidate 0 = selected real GAME medoid run
```

每个 repair 必须记录：

```text
region
before
candidate after
evidence
reason
confidence
which gate passed
A/B render
rollback information
```

不能直接覆盖原 GAME baseline。

---

## 25. SAFE retune

只允许：

```text
single-note pitch retune
```

并满足 §15 SAFE gate。

目标 pitch 优先来自：

```text
RMVPE / FCPE agreed stable plateau center
→ 映射到合理 written-note semitone
```

不能把任意 raw F0 deviation 直接写成 MIDI note。

---

## 26. Structure repair 暂不进入 SAFE

第一阶段的：

```text
split
merge
missing note
false note
large boundary shift
```

默认仍属于 PROBABLE / AMBIGUOUS。

只有 structure calibration 证明某类规则 precision 足够高，才逐类升级。

修改 boundary 后优先让 GAME estimator 重新估局部 pitch，而不是重新退回 `median F0 → note`。

---

## 27. Candidate scoring

候选：

```text
C0 real GAME baseline
C1 retune
C2 boundary shift
C3 split
C4 merge
C5 local combined repair
```

证据包括：

```text
GAME presence consensus
GAME tone consensus
GAME structural stability
sequence-alignment relation
RMVPE pitch evidence
FCPE pitch evidence
RMVPE plateau / changepoint
FCPE plateau / changepoint
voiced consistency
energy / onset
lyric compatibility
duration plausibility
local melodic continuity
complexity penalty
unsupported-edit penalty
```

必须设置 minimum improvement。

原则：

> **宁可保留 GAME 的小错误，也不要让 correction 制造新错误。**

---

# Part G — Lyrics / USTX / PITD

## 28. Lyrics ↔ corrected melody

melody 稳定后再映射：

```text
1 char → 1 note
1 char → N notes（melisma）
N chars → N notes
```

OpenUtau：

```text
首 note：真实歌词
同字后续：+
换气：AP
静音：gap / SP
```

若 lyrics 和 melody 冲突，标 `lyric_alignment_conflict`；不得通过把歌词强移到最近 voiced block 来伪修复。

---

## 29. 基础 USTX 验收

第一阶段只含：

- corrected score；
- lyrics；
- timing；
- singer / renderer；
- 必要 phonemizer 设置。

核心验收：

> **不做泠鸢 style 和复杂 PITD 时，是否已经唱对《年轮》的旋律和节奏？**

未通过不得进入 style 阶段。

---

## 30. raw F0 → constrained PITD

written score 通过后才加入：

- portamento；
- 音头滑入；
- ornament；
- vibrato；
- intonation deviation。

PITD 不得掩盖 written-note 错误。

---

# Part H — Evaluation

## 31. Diagnostic level

至少记录：

- 每次 GAME run note count；
- pairwise alignment cost；
- medoid baseline run；
- `1↔1 / gap / split / merge` 数；
- consensus stability；
- residual triage 分类；
- RMVPE / FCPE pitch agreement；
- RMVPE / FCPE structure agreement；
- plateau / changepoint evidence；
- candidate count；
- human-confirmed error count；
- validator precision / false-positive；
- regression-case status。

---

## 32. Score level

记录：

```text
real GAME Candidate 0
corrected score
retune count
split / merge count
boundary-shift count
GAME preservation ratio
rollback coverage
```

GAME preservation ratio 应尽量高。

---

## 33. Render level

比较：

```text
source / separated vocal F0
real GAME baseline score
candidate corrected score
DiffSinger baseline render
DiffSinger corrected render
```

区分：

- GAME transcription error；
- F0 extractor error；
- structure representation ambiguity；
- lyric alignment error；
- PITD error；
- DiffSinger render deviation。

旧 per-note median cents 只能作为辅助指标，不能单独证明旋律正确。

---

# Part I — Milestones

## 34. 当前实施顺序

### M2.0 — Foundation survey ✅

GAME / RMVPE / dataset-tools / SlurCutter 等基础调研完成。

### M2.1 — Initial diagnostic ✅

完成并纠正 forced-boundary 误读。

### M2.1.1 — Diagnostic correctness ✅

完成 cents、raw-first、time alignment、lyric evidence-only、voiced-island structural F0 等修复。

### M2.1.2 — GAME stochastic baseline ✅

完成多次 GAME、stochasticity 测量和初版 consensus。

### M2.2A — Formal sequence alignment ✅

完成 DP `match/gap/split/merge` 与 run-order-independent consensus evidence。

### M2.2B — Dual-F0 evidence ✅

完成 RMVPE + FCPE；189.84s 已成为 extractor-conflict regression case。

### M2.3 — Residual-error triage ✅ 初版完成

完成：

- real GAME medoid baseline；
- baseline note → consensus evidence mapping；
- stable plateau 初版；
- 全曲 triage。

当前结果：

```text
416 baseline notes
312 likely-correct
47 structure candidates
37 listening-review
16 F0 conflicts
3 ambiguous
1 pitch-hard candidate
```

### M2.3.1 — Triage calibration ← 当前最高优先级

必须完成：

1. `PITCH_HARD_SUSPICIOUS` 与 `SAFE_RETUNE_CANDIDATE` 分层；
2. SAFE gate 加入 GAME consensus / structure stability / single plateau；
3. 202.52s 生成完整 local A/B benchmark；
4. 用户人工听感确认 202.52s；
5. RMVPE 与 FCPE 独立生成 structural plateau / changepoint；
6. 47 个 structure-hard 统一降为 structure candidates；
7. 抽至少 10 个 structure candidates 做人工 precision calibration；
8. 189.84s regression 必须保持 NO-REPAIR；
9. 输出 confirmed-error 与 candidate 的严格分离统计。

**M2.3.1 未完成前，不进入自动 M2.4。**

### M2.4 — SAFE repair

第一版只实现 M2.3.1 已人工确认并能稳定通过 gate 的简单错误类型。

优先：

```text
single-note pitch retune
```

### M2.5 — PROBABLE structure candidates

只有 structure calibration precision 足够高时才逐步实现：

- split；
- merge；
- missing / false note；
- boundary shift；
- scorer / minimum improvement gate。

### M2.6 — Optional second opinion

只有 GAME + formal alignment + RMVPE + FCPE + lyric / onset evidence 仍留下大量关键 unresolved regions 时才考虑 ROSVOT。

### M2.7 — Lyrics mapping + base USTX

corrected real score → lyrics / melisma → 可编辑工程。

### M2.8 — PITD + render loop

raw F0 → constrained PITD → DiffSinger → reference / score / render 三层评价。

### M2.9 — 《年轮》M2 验收

主要 A/B：

```text
selected real GAME medoid baseline
vs
corrected score
```

人工听感是最终 gate 之一。

通过后冻结 melody score。

### M3 — 泠鸢 style profile

只有 M2.9 通过后开始。

分析：

- vibrato rate / depth；
- portamento；
- 音头；
- 句尾；
- breath placement；
- dynamics；
- tension / breathiness；
- voice color；
- 音区差异。

原则：

> **原唱决定“唱什么”；泠鸢参考决定“怎么唱”。**

---

# 35. 最终原则

1. **GAME 是默认 melody transcription 基座。**
2. **最终可渲染 baseline 必须来自真实 GAME run，不是 synthetic consensus。**
3. **Candidate 0 使用 real GAME medoid run。**
4. **Consensus 是 uncertainty / evidence graph，不是 note skeleton。**
5. **split / merge component 只表示局部结构不确定，不等于 repair 指令。**
6. **RMVPE + FCPE 是 evidence，不是主转谱器。**
7. **单 F0 extractor 永远不能独自推翻 GAME。**
8. **双 F0 pitch agreement 也不等于自动 SAFE；还必须通过 GAME stability + structure + plateau gate。**
9. **structure repair 必须要求 RMVPE + FCPE 双结构证据，而不是单 RMVPE plateau。**
10. **189.84s 永久作为 extractor-conflict NO-REPAIR regression case。**
11. **202.52s 当前是 SAFE-retune benchmark candidate，人工 A/B 前不写成 confirmed error。**
12. **47 个 structure-hard 当前只是 candidates，不是 47 个 confirmed errors。**
13. **37 个 listening-review 优先用 plateau / note-interior evidence 消除 vibrato median 假阳性。**
14. **high dispersion 是 feature，不是错误。**
15. **lyric char timestamp 不是 note onset。**
16. **candidate / hard suspicious / confirmed error / SAFE repair 必须分层统计。**
17. **如果真实 residual errors 很少，就保持 correction layer 轻量。**
18. **Candidate 0 永远可 rollback。**
19. **所有修改必须局部、可解释、可审计、可 A/B。**
20. **复杂区域宁可 needs_review，不强行自动修。**
21. **先把 written score 唱对，再生成 PITD。**
22. **先“唱对”，再做泠鸢风格。**
