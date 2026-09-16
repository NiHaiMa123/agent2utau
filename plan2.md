# agent2utau — Plan 2：GAME 主转谱 + 自动证据裁决 + Phrase-Level 审核

> 修订日期：2026-09-16
>
> 核心原则：**先把“唱对”解决，再把“唱得像泠鸢”解决。**
>
> 当前工程原则：**GAME 提供真实可渲染的 score candidate；多次 GAME consensus 只作为 uncertainty / evidence graph。能由程序测量的 pitch / octave 不交给人工猜；structure 先自动 adjudicate，只有机器仍无法唯一解释的音乐语义才进入完整乐句人工审核。**

---

# 1. 最终目标流程

```text
原曲
→ decode / separation
→ GAME 多次同配置转谱
→ formal sequence alignment
→ 选择真实 GAME medoid run 作为 Candidate 0
→ multi-run uncertainty graph
→ RMVPE + FCPE + third-F0 / periodicity / harmonic evidence
→ orthogonal pitch / structure / identity / separation states
→ pitch adjudication (M2.3.2B)
→ structure adjudication (M2.3.2C)
→ unresolved musical interpretation 才进入 phrase-level A/B/C review
→ 只修高置信局部错误
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
- RMVPE / FCPE / third-F0 都是 evidence，不是从零重建全曲谱面的工具；
- correction 只修 residual errors。

## 2.2 GAME 有真实 stochasticity

《年轮》同输入、同配置，多次 GAME raw 约 418–425 voiced notes/run。

因此：

```text
single GAME run != deterministic truth
```

多 run 的价值是 uncertainty evidence：

- 多次一致 → 更可信；
- split / merge / pitch 多解 → 局部不确定；
- 不允许单次 GAME 直接驱动 repair。

## 2.3 Consensus 不是最终谱面

Formal sequence alignment 使用：

```text
match 1↔1
gap 1↔0 / 0↔1
split 1↔2
merge 2↔1
```

历史 consensus graph 曾得到约：

```text
397 events
348 GAME_STABLE
2   GAME_VARIABLE
47  GAME_UNSTABLE
43  events 有 split/merge structure variance
```

**397 events != 最终 397 notes。**

Consensus component 只表示 multi-run correspondence + uncertainty。禁止把 `start_median / duration_median / tone_median` 拼成 synthetic final score。

## 2.4 Candidate 0 必须来自真实 GAME run

Candidate 0 选择真实 GAME medoid run：

```text
sum(pairwise alignment cost) 最小的真实 run
```

Medoid 只是 concrete baseline，不是 ground truth，也不能作为 correctness 的独立证据。

202s 案例已经证明 GAME 本身可能在同一区域给出约 MIDI 65 / 72 两套 stochastic 解，因此 medoid 选择和 pitch truth 必须分离。

## 2.5 Dual-F0 是必要的，但不能简单投票

189s 附近出现：

```text
RMVPE ≈ 高八度候选
FCPE  ≈ 低八度候选
GAME  ≈ 其中一个候选
```

因此固定原则：

> **单一 F0 extractor 永远不能独自推翻 GAME。**

189s 永久作为 extractor-conflict regression case。

---

# 3. F0 measurement 与 score interpretation 分离

## 3.1 F0 measurement

程序回答：

```text
这一帧 / 稳定区间的 fundamental frequency 是多少？
```

Evidence：

- RMVPE；
- FCPE；
- third-F0；
- waveform periodicity / autocorrelation；
- harmonic-series fit；
- subharmonic support。

人工不负责猜 MIDI / Hz / cents / octave number。

## 3.2 Score interpretation

系统回答：

```text
连续 F0 应记为一颗 note、两颗 note、slide、grace 还是 ornament？
```

Evidence：

```text
GAME multi-run structure
+ RMVPE / FCPE plateau/changepoint
+ third-F0（必要时）
+ onset / energy
+ voiced transition
+ lyric articulation
+ note-duration plausibility
+ local melodic context
```

只有 automatic structure adjudication 后仍有多个合理 musical interpretations，才交给 phrase-level human review。

---

# 4. 当前工程状态

## M2.3 / M2.3.1 ✅

已完成：

- real GAME medoid Candidate 0；
- stochastic consensus；
- RMVPE + FCPE dual-F0；
- structural F0；
- plateau / interior re-triage；
- structure candidates；
- SAFE gate 初版；
- regression packets。

旧 40 组 isolated short clips 仅保留 debug/demo，不再是正式人工审核入口。

## M2.3.2A correctness cleanup ✅

commit `44a488d...`：

- structure ambiguity 优先于 pitch-hard；
- frame-inclusive plateau duration；
- RMVPE + FCPE dual plateau；
- content-bound cache 初版；
- raw-vs-zh formal DP；
- medoid sensitivity；
- separation-sensitive diagnostic。

## M2.3.2A2 final correctness cleanup ✅

commit `6937ce8...`：

- `plateau end = start + dur`；
- 两 extractor 都要求 unique target plateau；
- `plateau_overlap_ratio >= 0.5` 进入 SAFE hard gate；
- multi-plateau / non-overlap reject；
- actual sample rate；
- separation comb 明确只作为 uncertainty flag；
- orthogonal state schema 初版。

## M2.3.2A3 state/routing cleanup ✅

commit `5b16d1d...`：

- raw `wrong_pitch / possible_octave_error` 只作为 feature，不再覆盖 calibrated result；
- `GAME_LIKELY_CORRECT` 即使带 stale raw flag 也保持 pitch stable；
- 所有 `structure_varies` region 都独立计算 dual structure evidence；
- SAFE eligible 改为 `candidate_pending_adjudication`，禁止直接 repair；
- separator provenance 增加 model path / SHA256 / config hash；
- +3 routing regressions，本地报告 54 tests passed。

最新《年轮》rerun：

```text
medoid run 2
baseline = 420 notes

330 keep_baseline
45  needs_adjudication
45  needs_phrase_review
0   candidate_pending_adjudication
0   repair_candidate
```

A3 证明 stale pitch flag 问题已修：`keep_baseline` 从 314 回升到 330。

189.84s 当前可以同时表达：

```text
pitch_state      = extractor_conflict
structure_state  = candidate
separation_state = sensitive
```

202.52s 继续保持：

```text
identity_state = variable
→ no direct retune
```

---

# 5. M2.3.2A4 — Routing / Provenance Finalization ← 当前最高优先级

A4 是 correctness 系列最后一个小阶段。**A4 完成后不再新增 A5，直接进入 M2.3.2B。**

## 5.1 Structure candidate 不能直接进入人工

当前 routing 仍存在：

```text
structure_state != stable
→ needs_phrase_review
```

这与目标架构冲突。

45 个 structure candidate 应先经过 M2.3.2C automatic structure adjudication，而不是现在就交给用户听。

正式 routing 应拆分：

```text
keep_baseline
candidate_pending_adjudication
needs_pitch_adjudication
needs_structure_adjudication
needs_phrase_review
auto_resolved
repair_candidate
```

A 阶段 routing：

```text
pitch conflict / suspicious
→ needs_pitch_adjudication

structure candidate / split_merge_variable
→ needs_structure_adjudication

SAFE dual-F0 gate eligible
→ candidate_pending_adjudication

只有之后 B/C 明确 unresolved
→ needs_phrase_review
```

**禁止：**

```text
structure candidate
→ 直接 needs_phrase_review
```

## 5.2 Pitch 和 structure routing 必须真正分流

同一个 region 可以同时：

```text
needs_pitch_adjudication
+
needs_structure_adjudication
```

workflow 不应该强迫它只能属于一个 legacy bucket。

建议 state 中增加 routing needs：

```text
routing_needs:
  pitch_adjudication: bool
  structure_adjudication: bool
  phrase_review: bool
```

最终 `decision` 只表示当前下一步，不能丢掉其它未完成 adjudication 需求。

优先级建议：

```text
candidate_pending_adjudication
> needs_pitch_adjudication
> needs_structure_adjudication
> needs_phrase_review
> keep_baseline
```

但所有 orthogonal needs 仍保留在 packet 中。

## 5.3 `NEEDS_LISTENING_REVIEW` 不应天然等于 pitch suspicious

Legacy `NEEDS_LISTENING_REVIEW` 可能由不同 raw flags 产生，因此不能永久使用：

```text
legacy triage enum
→ pitch_state
```

目标方向应反转：

```text
raw + calibrated evidence
→ pitch_state
→ structure_state
→ identity_state
→ routing needs / decision
→ legacy triage compatibility summary
```

A4 不要求一次删除 legacy `triage`，但新逻辑不得依赖 legacy enum 决定另一个正交 state 的含义。

## 5.4 Separator provenance 必须使用实际运行解析出的模型

`separate()` 已能返回：

```text
model_path
model_sha256
```

但当前 `run.py` 在 separation 前仍自行猜：

```text
/tmp/audio-separator-models/UVR-MDX-NET-Voc_FT.onnx
```

然后 manifest 主要写入这份预估 path/hash。

这在模型实际路径不同的机器上可能产生：

```text
pre-run guessed hash = None / wrong path
actual separator resolved model = valid file
manifest = guessed provenance
```

正确 contract：

### cache miss

```text
run separate()
→ obtain actual model_path / actual model_sha256
→ write actual values into separation.json + manifest
```

### cache hit

```text
read manifest.actual_model_path
→ hash current bytes
→ compare with manifest.actual_model_sha256
→ config hash / source hash / schema also compare
```

禁止由 diagnostic 层猜 audio-separator 的内部 model directory 作为最终 truth。

## 5.5 A4 regression requirements

至少新增：

```text
1. structure candidate -> needs_structure_adjudication, NOT phrase review
2. unresolved structure after C -> only then needs_phrase_review
3. pitch conflict -> needs_pitch_adjudication
4. simultaneous pitch+structure conflict preserves both routing needs
5. SAFE eligible -> candidate_pending_adjudication
6. no A-stage state can directly become repair_candidate
7. actual separate() model_path/hash becomes manifest provenance
8. guessed model path differs from actual path -> manifest uses actual
9. actual separator model bytes changed -> cache invalid
10. separator config changed -> cache invalid
11. stale raw pitch flag does not resurrect adjudication
12. 189s remains multi-axis conflict regression
13. 202s remains identity-variable/no-direct-retune regression
```

## 5.6 A4 acceptance

```text
structure candidates no longer go directly to human
pitch and structure adjudication have separate routing
orthogonal routing needs can coexist
legacy triage no longer owns orthogonal semantics
separator provenance is based on actual resolved model bytes
all A-stage repairs remain disabled
```

完成后：

```text
M2.3.2A / A2 / A3 / A4 = FROZEN
→ start M2.3.2B
```

---

# 6. Orthogonal state / routing contract

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

routing_needs:
  pitch_adjudication: bool
  structure_adjudication: bool
  phrase_review: bool

decision:
  keep_baseline
  candidate_pending_adjudication
  needs_pitch_adjudication
  needs_structure_adjudication
  needs_phrase_review
  auto_resolved
  repair_candidate
```

要求：

- evidence state 与 workflow decision 分离；
- 一个 region 可以同时有多个 non-stable state；
- 一个 region 可以同时需要 pitch 与 structure adjudication；
- legacy `triage` 仅作 compatibility/reporting；
- `needs_phrase_review` 必须是 B/C adjudication 之后的 unresolved outcome；
- `repair_candidate` 必须是 adjudication 后状态。

---

# 7. Evidence independence

禁止按 raw feature 数量简单投票。

Evidence families：

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
RMVPE raw center + RMVPE plateau
```

仍属于一个 RMVPE family。

GAME 5 runs 也是同一模型 stochastic samples，不是 5 个独立模型。

Confidence 按 family agreement / conflict / reliability 计算。

---

# 8. Cache / provenance contract

最终 provenance 至少覆盖：

```text
source_audio_sha256
separator_actual_model_path
separator_model_sha256
separator_config_sha256
GAME model hashes/config
RMVPE model hash/config
FCPE model hash/config
third-F0 version/config
analysis/adjudicator schema version
```

规则：

```text
input/model/config changed
→ invalidate affected dependent artifact
```

不能仅靠 source path 或 model filename 判断 cache 有效性。

---

# 9. M2.3.2B — Automatic Pitch / Octave Adjudication

A4 冻结后立即开始。

## 9.1 Third-F0

第一版只接一个足够独立、稳定、可复现的 estimator。

优先：

```text
pYIN / YIN
或 WORLD Harvest
```

CREPE 可作为额外 neural opinion，但不能因为“模型更多”就自动增加 confidence。

## 9.2 Octave adjudicator

对于：

```text
f vs 2f
```

禁止简单多数投票。

至少结合：

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

简单 mix/separated spectral comb 仍只能作为 sensitivity flag，不能直接决定 truth。

## 9.3 Output

```text
AUTO_PITCH_RESOLVED
AUTO_OCTAVE_RESOLVED
F0_UNRESOLVED
SEPARATION_SENSITIVE
```

自动 pitch resolution 至少要求：

```text
identity clear
structure stable / 已完成 structure adjudication
多个独立 evidence families 支持同一 hypothesis
periodicity/harmonic evidence 不反对
separation-sensitive 无强冲突
confidence > calibrated threshold
```

冲突时：

```text
保持 Candidate 0
NO AUTO REPAIR
```

189s 是核心 B regression。

---

# 10. M2.3.2C — Automatic Structure Adjudication

A4 后，当前 structure candidates 全部先进入 C，不直接人工。

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

目标分类：

```text
ONE_NOTE_WITH_PORTAMENTO
TRUE_SPLIT_CANDIDATE
TRUE_MERGE_CANDIDATE
GRACE_OR_ORNAMENT
F0_ARTIFACT
ALIGNMENT_ARTIFACT
UNRESOLVED_STRUCTURE
```

只有：

```text
UNRESOLVED_STRUCTURE
```

或多个候选 score 非常接近时，才设置：

```text
routing_needs.phrase_review = true
```

Structure repair 第一阶段仍不自动执行；先统计 adjudication precision。

---

# 11. M2.3.2D — Phrase-Level Human Review

人工只处理 B/C 之后仍 unresolved 的音乐语义。

人工不做：

```text
F0 measurement
MIDI identification
Hz / cents judgement
octave guessing
```

人工只回答：

```text
哪种完整唱法更像 source？
哪种 note structure 在上下文里更自然？
```

## Review 单位

默认完整乐句：

```text
最低约 3s
常规 5–8s
最长约 12s
```

优先使用：

```text
LRC line / phrase
+ vocal silence / breath gap
+ GAME phrase context
```

至少尽量包含目标前后各 2–3 notes。

## Review 包

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
- 除目标 region 外 score 完全一致；
- 一次只改变一个待判断因素；
- source / baseline / candidates 使用同一 phrase boundary。

人工只需选：

```text
Baseline / A / B / C / 都差不多 / 都不对
```

zoom clip 只做二级辅助。

---

# 12. M2.4 — SAFE Repair Engine

进入条件：

```text
A4 frozen
B pitch/octave adjudicator available
C structure adjudication available
189s regression no false repair
202s identity-variable no direct retune
phrase review workflow available
Candidate 0 / rollback contract complete
```

第一版只优先：

```text
single-note written-pitch retune
```

若最终 0 SAFE repairs，也是合法结果。

每个 repair 必须记录：

```text
region
before / after
evidence families
orthogonal states
adjudication result
confidence
gates passed
phrase A/B（若需要）
rollback data
```

禁止覆盖 Candidate 0。

Structure repair 默认仍为 PROBABLE / AMBIGUOUS，只有 precision 证明足够高才逐类升级。

---

# 13. Lyrics / USTX / PITD

Melody written score 稳定后再映射 lyrics：

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

通过后再加入 portamento / onset slide / ornament / vibrato / intonation deviation。

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
routing_needs / decision
RMVPE / FCPE / third-F0 evidence families
periodicity/harmonic evidence
plateau center + temporal overlap
separation sensitivity
AUTO_RESOLVED / UNRESOLVED counts
pitch-adjudication count
structure-adjudication count
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

人工评估只比较 phrase-level source / baseline / candidates。

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
### M2.3.2A2 — Final correctness cleanup ✅
### M2.3.2A3 — State/routing cleanup ✅

最新 rerun：420-note baseline；330 keep；45 当前 pitch/adjudication path；45 当前 structure path；0 direct repair。

### M2.3.2A4 — Routing/provenance finalization ← 当前最高优先级

必须完成：

1. structure candidate 不再直接进人工；
2. pitch / structure adjudication routing 分流；
3. simultaneous pitch+structure needs 可共存；
4. legacy triage 不再决定 orthogonal semantics；
5. separator manifest 使用 actual resolved model path/hash；
6. provenance/cache regression；
7. A-stage 永不直接产生 repair_candidate。

A4 完成后冻结整个 A 系列，不再新增 A5。

### M2.3.2B — Automatic pitch/octave adjudication

Third-F0 + periodicity + harmonic/subharmonic + evidence-family confidence。

### M2.3.2C — Automatic structure adjudication

先程序解决 split/merge/portamento/ornament 等结构问题，仅 unresolved 进入人工。

### M2.3.2D — Phrase-level human review

正式生成 3–12s（常规 5–8s）的 source / baseline / A/B/C phrase 包；short clip 仅 zoom/debug。

### M2.4 — SAFE repair

只修 adjudicator 高置信确认的简单局部错误。

### M2.5 — PROBABLE structure repair

按真实 precision 决定是否实现 split / merge / missing / false note / boundary shift。

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
2. **Candidate 0 必须来自真实 GAME run，不是 synthetic consensus。**
3. **Medoid 是 baseline selection，不是 correctness proof。**
4. **Consensus 是 uncertainty graph，不是最终 note skeleton。**
5. **F0 measurement 与 score interpretation 分开。**
6. **能程序测量的 pitch / octave 不交给人工猜。**
7. **单 F0 extractor 不能独自推翻 GAME。**
8. **同一 extractor 的 raw / structural features 不是独立票。**
9. **GAME 多 runs 是 stochastic samples，不是多个独立模型。**
10. **Pitch-hard 前必须先排除 structure / identity ambiguity。**
11. **SAFE dual-F0 必须有独立且时间一致的 RMVPE + FCPE plateau 支持。**
12. **Octave conflict 必须看 periodicity / harmonic / subharmonic，不做简单多数投票。**
13. **Separation artifact 只作为 uncertainty，不直接当真值。**
14. **Cache/provenance 必须绑定实际音频内容与实际模型 bytes/config。**
15. **Pitch / structure / identity / separation 使用正交状态。**
16. **Pitch adjudication 与 structure adjudication 必须分流。**
17. **Structure candidate 必须先 automatic adjudication，不能直接扔给人工。**
18. **needs_phrase_review 只能是 B/C 之后 unresolved 的结果。**
19. **人工默认审核完整乐句，不审核 isolated note。**
20. **Phrase A/B/C 除目标局部外必须完全一致。**
21. **Zoom clip 只是辅助。**
22. **189s 永久作为 extractor-conflict regression。**
23. **202s 永久作为 stochastic pitch / identity-variable regression。**
24. **candidate / auto-resolved / unresolved / confirmed repair 分层统计。**
25. **0 automatic repairs 是合法结果。**
26. **Candidate 0 永远可 rollback。**
27. **所有修改必须局部、可解释、可审计、可 A/B。**
28. **先把 written score 唱对，再生成 PITD。**
29. **先“唱对”，再做泠鸢风格。**