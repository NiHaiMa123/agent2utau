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

历史 consensus graph 曾得到约：

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

202s 案例证明 GAME 本身可能对同一区域给出约 MIDI 65 / 72 两套 stochastic 解；medoid 可以选择更代表性的真实 run，但“medoid 选中了某个解”不等于这个解天然正确。

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

## 4.2 M2.3.2A correctness cleanup ✅

commit `44a488d...` 已完成：

- structure ambiguity 在 pitch-hard 前 gate；
- plateau duration 改为 frame-inclusive；
- SAFE gate 要求 RMVPE + FCPE 各自有 target plateau；
- cache manifest 加 source SHA256 + separator model + schema；
- raw-vs-zh 改为 formal DP alignment；
- full-cost medoid + structure-only medoid sensitivity；
- separation-sensitive spectral-comb diagnostic；
- 新增关键 regression tests。

## 4.3 M2.3.2A2 final correctness cleanup ✅

commit `6937ce8...` 已完成：

- plateau `end = start + dur`，保证 frame-inclusive geometry 一致；
- RMVPE / FCPE 都要求 unique single plateau；
- `plateau_overlap_ratio >= 0.5` 进入 SAFE hard gate；
- multi-plateau / non-overlap dual plateau 会 reject；
- separation check 使用实际 separated-vocal sample rate；
- separation spectral comb 明确只作为 uncertainty flag；
- 每个 packet 新增 `pitch / structure / identity / separation` 正交状态；
- legacy `triage` 暂时保留为 compatibility summary；
- 新增对应 unit regressions。

最新《年轮》rerun：

```text
333 GAME_LIKELY_CORRECT
45  STRUCTURE_CANDIDATE
18  F0_EXTRACTOR_CONFLICT
8   NEEDS_LISTENING_REVIEW
1   PITCH_HARD_SUSPICIOUS

routing decisions:
314 keep_baseline
65  needs_adjudication
39  needs_phrase_review
0   repair_candidate
```

202.52s 的 pitch-hard 仍被 identity gate 拒绝：GAME 自己在约 65.3 / 72.4 之间不稳定，因此不能直接 retune。

A2 说明底层 correctness gate 已基本稳定，但最新 review 发现正交状态层还有一小轮语义清理要做。

---

# 5. M2.3.2A3 — State / Routing Cleanup ← 当前最高优先级

A3 是小型 state-machine cleanup，不再扩展底层 F0 算法。完成后即可进入第三 F0 与 octave adjudication。

## 5.1 Raw pitch flags 不能重新覆盖 calibrated judgement

当前 `orthogonal_states()` 仍可能直接使用：

```text
wrong_pitch
possible_octave_error
```

这些 raw/full-window flags 来设置：

```text
pitch_state = suspicious
```

问题是 M2.3.1 已经通过 plateau / interior center 把大量 full-window median 假阳性重新判为：

```text
GAME_LIKELY_CORRECT
```

如果 orthogonal state 再直接读取旧 raw flag，就会把已经被 calibrated triage 清掉的 note 重新送回 `needs_adjudication`。

当前 rerun 的一个明显信号是：

```text
333 GAME_LIKELY_CORRECT
但只有
314 keep_baseline
```

这约 19 个差额需要逐项解释，不能默认是新的真实问题。

### A3 规则

Raw flags 只能作为 feature，不得单独决定最终 `pitch_state`。

推荐 precedence：

```text
extractor conflict / calibrated hard evidence
    ↓
pitch_state = extractor_conflict / suspicious

weak evidence / unresolved identity
    ↓
pitch_state = unresolved

plateau/interior re-triage 已支持 GAME
且无更强当前反证
    ↓
pitch_state = stable
```

明确禁止：

```text
stale wrong_pitch flag
→ 直接 pitch_state=suspicious
```

必须新增 regression：

```text
legacy/raw flag = wrong_pitch
calibrated triage = GAME_LIKELY_CORRECT
无当前 strong opposing evidence
→ pitch_state = stable
→ decision = keep_baseline
```

## 5.2 Structure evidence 必须真正与 pitch triage 正交

当前 dual structure evidence 仍主要在：

```text
legacy triage == STRUCTURE_CANDIDATE
```

时才生成。

但一个 region 可以同时：

```text
F0 extractor conflict
+
GAME structure_varies
```

旧单标签 `classify()` 可能先返回 `F0_EXTRACTOR_CONFLICT`，从而让该 region 没有完整 RMVPE/FCPE structure evidence。

A3 必须改成：

```text
if consensus.structure_varies:
    ALWAYS compute RMVPE structure evidence
    ALWAYS compute FCPE structure evidence
    ALWAYS compute dual_structure_evidence
```

与 legacy `triage` 返回什么无关。

因此：

```text
pitch_state
structure_state
identity_state
separation_state
```

必须分别由自己的 evidence path 产生，legacy triage 不再作为其他维度 evidence 的开关。

## 5.3 SAFE gate passed 不能直接等于 `repair_candidate`

M2.3.2B 尚未实现 third-F0 / periodicity / harmonic adjudication。

因此 A 阶段的 SAFE gate 只能说明：

```text
现有 GAME + RMVPE + FCPE 条件允许进入下一层 pitch adjudication
```

不能说明：

```text
已经批准自动改谱
```

在 M2.3.2B 完成前，routing 应至少区分：

```text
keep_baseline
candidate_pending_adjudication
needs_adjudication
needs_phrase_review
auto_resolved
repair_candidate
```

A 阶段：

```text
safe_gate.eligible = true
→ candidate_pending_adjudication
```

B 阶段只有在 independent adjudication 通过后：

```text
candidate_pending_adjudication
→ auto_resolved
→ repair_candidate
```

这样第一个真正通过 SAFE gate 的 note 不会绕过 third-F0 / harmonic layer。

## 5.4 Cache provenance 补 separator model hash / config hash

当前 cache manifest 已有：

```text
source SHA256
separator model name
schema
```

但只有文件名：

```text
UVR-MDX-NET-Voc_FT.onnx
```

仍不足以识别“同名模型文件被替换”的情况。

A3 至少补：

```text
separator_model_sha256
separator_config_hash / canonical config
```

规则：

```text
source / separator model bytes / separator config 任一改变
→ separation cache invalid
```

后续第三 F0 / adjudicator 也沿用同一 provenance contract。

## 5.5 A3 regression requirements

至少补：

```text
1. stale raw wrong_pitch + calibrated GAME_LIKELY_CORRECT → stable/keep
2. structure_varies + F0_EXTRACTOR_CONFLICT → 仍生成 dual structure evidence
3. structure evidence generation independent from legacy triage enum
4. SAFE eligible before M2.3.2B → candidate_pending_adjudication, not repair_candidate
5. separator model bytes change → cache invalidation
6. separator config change → cache invalidation
7. 189s simultaneously保留 pitch conflict 与其他 orthogonal states
8. 202s 保持 identity-variable / no direct retune
```

## 5.6 A3 验收标准

```text
raw flags = features only
calibrated evidence owns final pitch_state
structure evidence is generated independently of pitch classification
SAFE gate cannot bypass M2.3.2B
separator cache is content/config bound
orthogonal states truly independent
routing counts 可解释
```

A3 完成后，M2.3.2A 系列正式冻结。

---

# 6. Orthogonal state contract

长期 schema：

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
  candidate_pending_adjudication
  needs_adjudication
  needs_phrase_review
  auto_resolved
  repair_candidate
```

要求：

- 一个 region 可以同时有多个非 stable 状态；
- evidence state 与 workflow decision 分离；
- legacy `triage` 只做 compatibility / reporting summary；
- 任何单一 legacy enum 都不能阻止其他 evidence path 运行；
- `repair_candidate` 必须是 adjudication 后状态，不是 pre-adjudication gate 状态。

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

同理 GAME 多 runs 是同模型 stochastic samples，不是多个独立模型。

confidence 应根据 family agreement / conflict / reliability 计算。

---

# 8. Cache / provenance contract

A3 后至少覆盖：

```text
source_audio_sha256
separator_model_name
separator_model_sha256
separator_config_hash
analysis schema version
GAME model hashes/config（report / dependency tracking）
```

后续逐步加入：

```text
RMVPE model hash/config
FCPE model hash/config
third-F0 version/config
adjudicator schema version
```

规则：

```text
input/model/config changed
→ invalidate only affected dependent artifacts
```

不能仅靠 source path 或 model filename 判断缓存有效性。

---

# 9. M2.3.2B — Automatic Pitch / Octave Adjudication

A3 冻结后开始。

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
GAME family
RMVPE family
FCPE family
third-F0 family
periodicity / autocorrelation
subharmonic support
weighted harmonic-series fit
local melodic context
separation sensitivity
```

简单 mix-vs-separated spectral comb 仍只作为 sensitivity flag，不能自己裁决真值。

输出到正交状态与 routing：

```text
pitch_state = stable / suspicious / extractor_conflict / unresolved
identity_state = stable / variable
separation_state = normal / sensitive

decision = keep_baseline / auto_resolved / needs_adjudication
```

自动解决至少要求：

```text
identity clear
structure stable
多个独立 evidence families 支持同一 written-note hypothesis
periodicity / harmonic / subharmonic evidence 不反对
separation-sensitive 不构成强冲突
confidence > calibrated threshold
```

若冲突：

```text
保持 Candidate 0
NO AUTO REPAIR
```

189s 是该阶段的首要 octave-conflict regression。

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
M2.3.2A3 state cleanup frozen
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
workflow decision
legacy triage vs calibrated state disagreement count
RMVPE / FCPE / third-F0 evidence families
periodicity/harmonic evidence
plateau center + temporal overlap
separation sensitivity
AUTO_RESOLVED / UNRESOLVED counts
phrase-review count
regression status
cache/provenance manifest
```

特别增加：

```text
GAME_LIKELY_CORRECT but decision != keep_baseline
```

的数量与原因分布，用于检测 stale-state / routing regression。

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

### M2.3.2A — Correctness cleanup ✅

完成 structure-first gate、frame-inclusive duration、dual extractor plateau、cache manifest、formal variant alignment、medoid sensitivity、separation diagnostic。

### M2.3.2A2 — Final correctness cleanup ✅

完成：

1. plateau `end = start + dur`；
2. RMVPE / FCPE 都要求 unique single plateau；
3. plateau overlap ≥0.5 hard gate；
4. non-overlap / multi-plateau rejection；
5. actual separated-vocal sample rate；
6. separation flag-only semantics；
7. orthogonal state schema 初版；
8. 对应 regression tests。

### M2.3.2A3 — State / routing cleanup ← 当前最高优先级

必须完成：

1. raw `wrong_pitch` / `possible_octave_error` 只做 feature，不得覆盖 calibrated state；
2. stale raw flag + calibrated correct 必须回到 stable / keep；
3. 所有 `structure_varies` region 独立生成 dual structure evidence；
4. structure evidence 不依赖 legacy triage enum；
5. SAFE eligible 在 B 前只能进入 `candidate_pending_adjudication`；
6. `repair_candidate` 只能由 automatic adjudication 产生；
7. separator model SHA256 + config hash 进入 cache provenance；
8. 补 stale-state / orthogonal-structure / routing / cache regressions；
9. 解释并收敛 `GAME_LIKELY_CORRECT` 与 `keep_baseline` 之间的异常差额。

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
10. **Raw flags 只是 feature，不能覆盖后续 calibrated judgement。**
11. **Pitch / structure / identity / separation evidence path 必须正交。**
12. **Legacy triage 只能做兼容摘要，不能控制其他 evidence 是否运行。**
13. **Pitch-hard 前必须先排除 structure / identity ambiguity。**
14. **SAFE pitch 必须有 RMVPE + FCPE 独立且时间一致的 plateau 支持。**
15. **Plateau 的 start/end/duration 必须几何一致。**
16. **Pre-adjudication SAFE candidate 不能直接成为 repair_candidate。**
17. **Octave conflict 要看 periodicity / harmonic / subharmonic，不做简单多数投票。**
18. **Separation artifact 只作为 uncertainty / confidence evidence，不能直接当真值。**
19. **所有音频分析必须使用实际 sample rate，不写死 44.1k。**
20. **Cache 必须绑定音频内容、模型 bytes 与配置 provenance。**
21. **正式 variant comparison 使用 formal sequence alignment。**
22. **Evidence confidence 按 family 计算，禁止重复计票。**
23. **Structure candidate 先自动 adjudicate，再决定是否人工。**
24. **人工默认审核完整乐句，不审核 isolated note。**
25. **Phrase A/B/C 除目标局部外必须完全一致。**
26. **Zoom clip 只是辅助。**
27. **189s 永久作为 extractor-conflict regression。**
28. **202s 永久作为 stochastic pitch / identity-variable regression。**
29. **candidate / auto-resolved / unresolved / confirmed repair 分层统计。**
30. **0 automatic repairs 是合法结果。**
31. **Candidate 0 永远可 rollback。**
32. **所有修改必须局部、可解释、可审计、可 A/B。**
33. **先把 written score 唱对，再生成 PITD。**
34. **先“唱对”，再做泠鸢风格。**
