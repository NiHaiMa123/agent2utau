# agent2utau — Plan 2：GAME 主转谱 + 自动证据裁决 + Phrase-Level 审核

> 修订日期：2026-09-16
>
> 核心原则：**先把“唱对”解决，再把“唱得像泠鸢”解决。**
>
> 当前工程原则：**GAME 提供真实可渲染的 score candidate；多次 GAME consensus 只作为 uncertainty / evidence graph。能由程序测量的 pitch / octave 不交给人工猜；人工只处理机器仍无法唯一解释的音乐结构与听感，而且默认以完整乐句为审核单位。**

---

# 1. 最终目标流程

```text
原曲
→ decode / separation
→ GAME 多次同配置转谱
→ formal sequence alignment
→ 选择真实 GAME medoid run 作为 Candidate 0
→ multi-run uncertainty graph
→ RMVPE + FCPE + 第三独立 F0 / periodicity / harmonic evidence
→ orthogonal pitch / structure / identity / separation states
→ automatic adjudication
→ 只修高置信局部错误
→ unresolved structure 才进入 phrase-level A/B/C 人工审核
→ lyrics ↔ melody mapping
→ OpenUtau / DiffSinger 基础渲染
→ constrained PITD / 演唱细节
→ 最后做泠鸢 style profile
```

旧逻辑：

```text
歌词字符窗口 → F0 median → heuristic split → MIDI
```

已确认不足，只保留 fallback，不再作为默认 melody transcription。

---

# 2. 已确认的工程事实

## 2.1 GAME 是主转谱基座

forced-char-boundary 实验曾把约 419 notes 扩张到约 760 notes，并制造大量假 suspicious，因此：

- GAME raw 是主 melody transcription 来源；
- lyric char start 不是天然 note boundary；
- RMVPE / FCPE / 第三 F0 都是 evidence，不是从零重建全曲谱面的工具；
- correction 只修少量 residual errors。

## 2.2 GAME 有真实 stochasticity

《年轮》同输入、同配置，多次 GAME raw 大约：

```text
418–425 voiced notes / run
```

所以：

```text
single GAME run != deterministic truth
```

多 run 的价值是 uncertainty evidence：

- 多次一致 → 更可信；
- split / merge / pitch 多解 → 局部不确定；
- 不允许单次 GAME 直接驱动 repair。

## 2.3 Formal sequence alignment 已完成

使用 order-preserving DP：

```text
match 1↔1
gap 1↔0 / 0↔1
split 1↔2
merge 2↔1
```

cost 包含 onset / overlap / duration / capped weak pitch。

正式 consensus graph 曾得到约：

```text
397 events
348 GAME_STABLE
2   GAME_VARIABLE
47  GAME_UNSTABLE
43  events 有 split/merge structure variance
```

**397 events 不是最终 397 notes。**

Consensus / union-find component 只表示局部对应关系和 uncertainty，禁止把 `start_median / duration_median / tone_median` 拼成 synthetic final score。

## 2.4 Candidate 0 必须来自真实 GAME run

多次 raw GAME 中选择 medoid：

```text
sum(pairwise alignment cost) 最小的真实 run
```

它只是 concrete baseline，不是 ground truth，也不能作为独立 correctness evidence。

202s 案例证明 medoid selection 本身能消掉一部分 stochastic pitch error：GAME runs 对约 MIDI 65 / 72 存在多解；medoid 可以选择到更代表性的真实 run，但“medoid 选中了某个解”不等于这个解天然正确。

## 2.5 Dual-F0 已证明必要

189s 附近出现：

```text
RMVPE ≈ 高八度候选
FCPE  ≈ 低八度候选
GAME  ≈ 其中一个候选
```

单看 RMVPE 会有错误 octave repair 风险。

固定原则：

> **单一 F0 extractor 永远不能独自推翻 GAME。**

189s 永久保留为 extractor-conflict regression case。

---

# 3. F0 measurement 与 score interpretation 分离

## 3.1 F0 measurement

问题：

```text
这一帧 / 稳定区间的 fundamental frequency 是多少？
```

程序处理，主要 evidence：

- RMVPE；
- FCPE；
- 第三独立 F0 estimator；
- waveform periodicity / autocorrelation；
- harmonic-series fit；
- subharmonic evidence。

人工不负责猜 MIDI / Hz / cents / octave number。

## 3.2 Score interpretation

问题：

```text
连续 F0 应记为一颗 note、两颗 note、slide、grace 还是 ornament？
```

由：

```text
GAME multi-run structure
+ plateau / changepoint
+ onset / energy
+ voiced transition
+ lyric articulation
+ local melodic context
```

共同判断。

只有程序仍保留多个合理 musical interpretations 时，才交给 phrase-level human review。

---

# 4. 当前阶段真实状态

## 4.1 M2.3 / M2.3.1 ✅

已经完成：

- medoid Candidate 0；
- stochastic consensus；
- RMVPE + FCPE dual-F0；
- structural F0；
- plateau / note-interior re-triage；
- structure-hard 降级为 `STRUCTURE_CANDIDATE`；
- SAFE gate 初版；
- regression packets；
- short listening-set demo。

旧 40 组 isolated short clips 只保留 debug/demo，不再作为正式人工审核方式。

## 4.2 M2.3.2A correctness cleanup ✅ 主体完成

最新 commit `44a488d...` 已完成：

- structure ambiguity 在 pitch-hard 前 gate；
- plateau duration 改为 frame-inclusive；
- SAFE gate 要求 RMVPE + FCPE 各自有 target plateau；
- cache manifest 加 source SHA256 + separator model + schema；
- raw-vs-zh 改为 formal DP alignment；
- full-cost medoid + structure-only medoid sensitivity；
- separation-sensitive spectral-comb diagnostic；
- 新增关键 regression tests。

最新《年轮》rerun：

```text
medoid = run 4
structure-only medoid = run 4
baseline_selection_uncertain = false

337 GAME_LIKELY_CORRECT
36  STRUCTURE_CANDIDATE
14  AMBIGUOUS_ORNAMENT
17  F0_EXTRACTOR_CONFLICT
8   NEEDS_LISTENING_REVIEW
1   PITCH_HARD_SUSPICIOUS
```

202.52s 的 `PITCH_HARD_SUSPICIOUS` 被 SAFE gate 正确拒绝：GAME 自己在约 65.3 / 72.4 之间 tone-unstable，`aligned_identity_clear` 不通过，因此它是 adjudication 问题，不是直接 retune 问题。

这说明 correctness gate 已开始真正阻止误修。

---

# 5. M2.3.2A2 — Final Correctness Cleanup ← 当前最高优先级

M2.3.2A 主体完成，但最新 code review 仍发现 4 类必须先清掉的问题。A2 完成前，不进入第三 F0 / harmonic auto-repair。

## 5.1 Plateau `end` 仍有一帧不一致

当前已修：

```text
dur = (j - i + 1) * frame_period
```

但保存的：

```text
end = ts[j]
```

仍使：

```text
end - start != dur
```

例如 8 × 10ms frame：

```text
start = 1.00
last sample = 1.07
dur = 0.08
真实区间应约为 [1.00, 1.08)
```

必须统一：

```text
end = start + dur
```

或等价的：

```text
end = ts[j] + frame_period
```

原因：后续 `plateau_overlap_ratio` 正依赖 `start/end`，当前实现会系统性少算约一帧 overlap。

必须补：

```text
assert abs((end - start) - dur) < tolerance
```

## 5.2 SAFE dual-plateau gate 还不够严格

当前已经要求：

```text
RMVPE target plateau exists
FCPE target plateau exists
plateau center delta <= threshold
```

但仍缺：

```text
FCPE plateau uniqueness / single-stable condition
plateau temporal-overlap hard gate
```

当前 `single_stable_plateau` 只检查 RMVPE：

```text
len(rmvpe_plateaus) == 1
```

必须升级为至少：

```text
RMVPE target hypothesis unique
AND FCPE target hypothesis unique
AND plateau_center_delta_cents <= calibrated threshold
AND plateau_overlap_ratio >= calibrated threshold
```

第一版建议从：

```text
plateau_overlap_ratio >= 0.5
```

开始，再由真实样本校准。

这种情况必须拒绝 SAFE：

```text
RMVPE: 72 ─────────
FCPE : 72 ─── / 65 ───
```

或者：

```text
RMVPE 72 plateau 与 FCPE 72 plateau 时间几乎不重叠
```

不能因为“都曾出现过 72”就通过。

## 5.3 Separation sensitivity 只能是 uncertainty flag

当前 mix-vs-separated spectral comb 是有价值的 diagnostic，但不能直接用于决定正确 pitch。

原因：

1. original mix 含伴奏，harmonic energy 可能来自乐器；
2. octave hypotheses `f` 与 `2f` 共享大量谐波；
3. 简单 `sum(max around k*f)` 对 octave ambiguity 有结构性偏差；
4. separated vocal 也可能受模型 artifact 影响。

因此当前字段只允许解释为：

```text
SEPARATION_SENSITIVE
→ confidence down
→ unresolved / further adjudication
```

禁止：

```text
mix prefers A → A is truth
```

同时修掉硬编码：

```text
("sep", wav, 44100)
```

必须使用实际 separated-vocal sample rate。

真正 M2.3.2B harmonic adjudicator 后续至少考虑：

```text
periodicity / autocorrelation
harmonic-to-noise ratio
weighted harmonic series
subharmonic support
odd/even harmonic relation
vocal-band weighting
mix-vs-separation sensitivity
```

## 5.4 单一 `triage` 标签开始不够表达状态

当前一个 region 可能同时存在：

```text
pitch extractor conflict
+
GAME structure instability
+
identity instability
+
separation sensitivity
```

但单一：

```text
triage = F0_EXTRACTOR_CONFLICT
```

会隐藏其他维度。

从 A2 开始逐步改成正交状态，旧 `triage` 可暂时保留兼容字段：

```text
pitch_state:
  stable
  suspicious
  extractor_conflict
  unresolved

structure_state:
  stable
  split_merge_variable
  candidate
  unresolved

identity_state:
  stable
  variable

separation_state:
  normal
  sensitive
  unknown

decision:
  keep_baseline
  auto_resolved
  needs_adjudication
  needs_phrase_review
  repair_candidate
```

要求：

- 一个 region 可以同时有多个非 stable 状态；
- `decision` 是最终 workflow routing，不等同于某一 evidence state；
- 旧 `triage` 只做兼容摘要，不再承载全部语义。

---

# 6. M2.3.2A2 测试与验收

至少新增 / 固化：

```text
1. plateau end-start == duration
2. 70/80/90ms plateau boundary
3. structure ambiguity blocks pitch-hard
4. SAFE requires RMVPE target plateau
5. SAFE requires FCPE target plateau
6. FCPE multiple/ambiguous plateau rejects SAFE
7. non-overlapping dual plateau rejects SAFE
8. plateau overlap threshold regression
9. separated vocal non-44.1k uses actual sr
10. separation-sensitive never directly resolves pitch
11. same-path source content change invalidates cache
12. separator model/config change invalidates dependent cache
13. raw-vs-zh uses formal alignment
14. full medoid vs structure-only medoid sensitivity
15. 189s remains NO-AUTO-REPAIR until adjudicator resolves it
16. 202s remains identity-variable / no direct retune
17. orthogonal states can represent simultaneous pitch+structure conflict
18. phrase A/B invariance outside target region
```

A2 验收：

```text
plateau geometry internally consistent
SAFE dual-plateau evidence has pitch + temporal agreement
separation check only lowers confidence / flags risk
all audio analysis uses actual sample rate
orthogonal state schema available
cache provenance regressions pass
189s / 202s regressions pass
```

只有这些通过后，M2.3.2A 才正式冻结。

---

# 7. Evidence independence

禁止按 raw feature 数量简单投票。

Evidence family：

```text
GAME family
RMVPE family
FCPE family
third-F0 family
waveform-periodicity family
harmonic-spectrum family
musical-context family
```

注意：

```text
RMVPE raw center + RMVPE structural plateau
```

仍属于一个 RMVPE family。

同理 GAME 5 runs 是同模型 stochastic samples，不是 5 个独立模型。

confidence 应根据 family agreement / conflict / reliability 计算。

---

# 8. Cache / provenance contract

当前 A 已加入：

```text
source SHA256
separator model
analysis schema
GAME model hashes（report）
```

最终依赖 provenance 应逐步覆盖：

```text
source_audio_sha256
separator_model_name/hash/config
GAME model hashes/config
RMVPE model hash/config
FCPE model hash/config
third-F0 version/config
analysis/adjudicator schema version
```

规则：

```text
input/model/config changed
→ invalidate only affected dependent artifacts
```

不能仅靠 source path 判断缓存有效性。

---

# 9. M2.3.2B — Automatic Pitch / Octave Adjudication

A2 冻结后再开始。

## 9.1 第三独立 F0

第一版接一个即可，优先：

```text
pYIN / YIN
或 WORLD Harvest
```

CREPE 可作为额外 neural opinion，但不能因为模型数量更多就自动提升 confidence。

## 9.2 Octave adjudicator

对于：

```text
f vs 2f
```

不得只做多数投票。

至少使用：

```text
RMVPE family
FCPE family
third-F0 family
periodicity / autocorrelation
subharmonic support
weighted harmonic-series fit
GAME run pitch distribution
local melodic context
separation sensitivity
```

输出到正交状态与 decision：

```text
pitch_state = stable / suspicious / extractor_conflict / unresolved
identity_state = stable / variable
separation_state = normal / sensitive

decision = keep_baseline / auto_resolved / needs_adjudication
```

自动解决必须要求：

```text
identity clear
structure stable
多个独立 evidence families 支持同一 written-note hypothesis
periodicity/harmonic evidence 不反对
separation-sensitive 不构成强冲突
confidence > calibrated threshold
```

若冲突：

```text
保持 Candidate 0
NO AUTO REPAIR
```

---

# 10. M2.3.2C — Automatic Structure Adjudication

当前 structure candidates 先自动分析，不直接交给人工。

Evidence：

```text
GAME multi-run structure distribution
RMVPE plateau/changepoint
FCPE plateau/changepoint
third-F0 / periodicity（必要时）
onset strength
energy change
voiced/unvoiced transition
lyric articulation
note-duration plausibility
local melodic continuity
```

目标状态：

```text
ONE_NOTE_WITH_PORTAMENTO
TRUE_SPLIT_CANDIDATE
TRUE_MERGE_CANDIDATE
GRACE_OR_ORNAMENT
F0_ARTIFACT
ALIGNMENT_ARTIFACT
UNRESOLVED_STRUCTURE
```

只有 unresolved 或多个候选分数接近时才进入人工。

Structure repair 第一阶段仍不是 SAFE auto-fix；先积累 precision。

---

# 11. M2.3.2D — Phrase-Level Human Review

## 11.1 人工职责

人工不做：

```text
F0 measurement
MIDI identification
Hz / cents judgement
```

人工只回答：

```text
哪种完整唱法更像 source？
哪种 note structure 在上下文中更自然？
```

## 11.2 Review 单位必须是完整乐句

默认禁止 0.5–1.5s isolated clip 作为主入口。

phrase boundary 优先：

```text
LRC line / phrase
+ vocal silence / breath gap
+ GAME phrase context
```

建议：

```text
最低约 3s
常规 5–8s
最长约 12s
```

优先包含目标前后各 2–3 notes。

## 11.3 Phrase A/B/C 包

```text
SOURCE_PHRASE_original_mix.wav
SOURCE_PHRASE_separated_vocal.wav
BASELINE_PHRASE.wav
CANDIDATE_A_PHRASE.wav
CANDIDATE_B_PHRASE.wav
CANDIDATE_C_PHRASE.wav  # optional
```

要求：

- 所有 candidate 时间窗完全一致；
- singer / phonemizer / color / volume / PITD policy 一致；
- 除目标 region 外 score 与 render config 完全一致；
- 不允许 A/B 同时改变多个无关因素；
- source 与 candidates 使用同一 phrase boundary。

人工只需选：

```text
Baseline / A / B / C / 都差不多 / 都不对
```

zoom clip 只做二级辅助。

---

# 12. Repair Engine

## 12.1 M2.4 SAFE repair 进入条件

必须先满足：

```text
M2.3.2A2 correctness frozen
pitch/octave adjudicator 可用
189s regression 不会误修
202s identity-variable case 不会直接 retune
separation-sensitive gate 可用
phrase review workflow 可用
Candidate 0 / rollback contract 完整
```

第一版仍优先：

```text
single-note written-pitch retune
```

若最终 0 SAFE repairs，也是合法结果。

## 12.2 Candidate 0 与审计

永久保留真实 GAME medoid baseline。

每个 repair 记录：

```text
region
before / after
evidence families
orthogonal states
reason
confidence
gates passed
phrase A/B（若需要）
rollback data
```

禁止覆盖原 baseline。

## 12.3 Structure repair

split / merge / missing / false note / large boundary shift 默认仍为 PROBABLE / AMBIGUOUS。

只有 automatic adjudication + phrase calibration 证明 precision 足够高，才逐类升级。

---

# 13. Lyrics / USTX / PITD

melody 稳定后再映射 lyrics：

```text
1 char → 1 note
1 char → N notes (melisma)
N chars → N notes
```

OpenUtau：

```text
首 note：真实歌词
同字后续：+
换气：AP
静音：gap / SP
```

歌词冲突标 `lyric_alignment_conflict`，不得通过强移到最近 voiced block 伪修复。

基础 USTX 验收：

> **不做泠鸢 style 和复杂 PITD 时，是否已经唱对旋律和节奏？**

written score 通过后再加入 portamento / onset slide / ornament / vibrato / intonation deviation。

PITD 不得掩盖 written-note error。

---

# 14. Evaluation

## Diagnostic

至少记录：

```text
GAME run note counts
pairwise alignment costs
selected medoid + medoid sensitivity
match/gap/split/merge counts
consensus stability
pitch_state / structure_state / identity_state / separation_state
RMVPE / FCPE / third-F0 evidence families
periodicity/harmonic evidence
plateau center + temporal overlap
separation sensitivity
AUTO_RESOLVED / UNRESOLVED counts
phrase-review count
regression status
cache/provenance manifest
```

## Score

```text
Candidate 0
corrected score
retune count
split/merge/boundary-shift count
GAME preservation ratio
rollback coverage
```

## Render / Human

机器：reference F0 / score / render 三层比较。

人工：只比较 phrase-level source / baseline / candidates。

---

# 15. Milestones

### M2.0 — Foundation survey ✅

### M2.1 / M2.1.1 — Initial diagnostic + correctness ✅

### M2.1.2 — GAME stochastic baseline ✅

### M2.2A — Formal sequence alignment ✅

### M2.2B — Dual-F0 ✅

### M2.3 — Residual-error triage ✅

### M2.3.1 — Triage calibration ✅

### M2.3.2A — Correctness cleanup ✅ 主体完成

已完成 structure-first gate、frame-inclusive duration、dual extractor plateau、cache manifest、formal variant alignment、medoid sensitivity、separation diagnostic 与关键单测。

### M2.3.2A2 — Final correctness cleanup ← 当前最高优先级

必须完成：

1. plateau `end = start + dur`；
2. RMVPE / FCPE target plateau 都要求 unique / stable；
3. `plateau_overlap_ratio` 真正进入 SAFE gate；
4. non-overlap dual plateau 必须 reject；
5. separation diagnostic 使用实际 vocal sample rate；
6. separation-sensitive 只能降低 confidence，不能直接裁决；
7. 引入 orthogonal state schema；
8. 补 cache/config/sample-rate/189s/202s/state regressions；
9. 所有相关 tests 通过后冻结 A 阶段。

### M2.3.2B — Automatic pitch/octave adjudication

第三 F0 + periodicity + harmonic/subharmonic + evidence-family confidence。

### M2.3.2C — Automatic structure adjudication

先自动筛 structure candidates，只把真正 unresolved 的音乐语义交给人工。

### M2.3.2D — Phrase-level human review

正式生成 3–12s、常规 5–8s 的 source / baseline / A/B/C phrase 包；short clip 只保留 zoom/debug。

### M2.4 — SAFE repair

只实现 adjudicator 已高置信确认的简单局部错误。

### M2.5 — PROBABLE structure repair

按实际 precision 决定是否实现 split / merge / missing / false note / boundary shift。

### M2.6 — Optional second opinion

只有 GAME + formal alignment + multi-F0 + periodicity/harmonic + onset/lyric 后仍留下大量关键 unresolved region 时，再考虑 ROSVOT 等额外模型。

### M2.7 — Lyrics mapping + base USTX

### M2.8 — PITD + render loop

### M2.9 — 《年轮》M2 验收

主要比较：

```text
selected real GAME baseline
vs
corrected score
```

人工验收以完整乐句/段落为主。

### M3 — 泠鸢 style profile

> **原唱决定“唱什么”；泠鸢参考决定“怎么唱”。**

---

# 16. 最终原则

1. **GAME 是默认 melody transcription 基座。**
2. **最终 baseline 必须来自真实 GAME run，不是 synthetic consensus。**
3. **Medoid 是 baseline selection，不是 correctness proof。**
4. **Consensus 是 uncertainty graph，不是最终 note skeleton。**
5. **F0 measurement 与 score interpretation 分开。**
6. **能程序测量的 pitch / octave 不交给人工猜。**
7. **单 F0 extractor 不能独自推翻 GAME。**
8. **同一 extractor 的 raw / structural features 不是独立票。**
9. **GAME 多 runs 是 stochastic samples，不是多个独立模型。**
10. **Pitch-hard 前必须先排除 structure / identity ambiguity。**
11. **SAFE pitch 必须有 RMVPE + FCPE 独立且时间一致的 plateau 支持。**
12. **Plateau 的 start/end/duration 必须几何一致。**
13. **Octave conflict 要看 periodicity / harmonic / subharmonic，不做简单多数投票。**
14. **Separation artifact 只作为 uncertainty / confidence evidence，不能直接当真值。**
15. **所有音频分析必须使用实际 sample rate，不写死 44.1k。**
16. **Cache 必须绑定音频内容与模型/配置 provenance。**
17. **正式 variant comparison 使用 formal sequence alignment。**
18. **Evidence confidence 按 family 计算，禁止重复计票。**
19. **Pitch / structure / identity / separation 使用正交状态，不把全部语义塞进单一 triage enum。**
20. **Structure candidate 先自动 adjudicate，再决定是否人工。**
21. **人工默认审核完整乐句，不审核 isolated note。**
22. **Phrase A/B/C 除目标局部外必须完全一致。**
23. **Zoom clip 只是辅助。**
24. **189s 永久作为 extractor-conflict regression。**
25. **202s 永久作为 stochastic pitch / identity-variable regression。**
26. **candidate / auto-resolved / unresolved / confirmed repair 分层统计。**
27. **0 automatic repairs 是合法结果。**
28. **Candidate 0 永远可 rollback。**
29. **所有修改必须局部、可解释、可审计、可 A/B。**
30. **先把 written score 唱对，再生成 PITD。**
31. **先“唱对”，再做泠鸢风格。**