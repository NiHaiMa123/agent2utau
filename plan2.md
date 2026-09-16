# agent2utau — Plan 2：GAME 主转谱 + 自动证据裁决 + Phrase-Level 审核

> 修订日期：2026-09-16
>
> 核心原则：**先把“唱对”解决，再把“唱得像泠鸢”解决。**
>
> 当前阶段：**M2.3.2B 已正式冻结；M2.3.2C Automatic Structure Adjudication 为当前最高优先级。**

---

# 1. 最终流程

```text
原曲
→ decode / separation
→ GAME 多次同配置转谱
→ formal sequence alignment
→ 选择真实 GAME medoid run 作为 Candidate 0
→ multi-run uncertainty graph
→ RMVPE + FCPE + third-F0 + periodicity / spectral evidence
→ orthogonal pitch / structure / identity / separation states
→ structure 未定：先 M2.3.2C structure adjudication
→ note identity 确定后：在真实 note identity 上运行冻结版 B pitch/octave adjudicator
→ finalized machine unresolved 才进入 M2.3.2D phrase-level A/B/C review
→ 只修高置信、已 finalized 的局部错误
→ lyrics ↔ melody mapping
→ OpenUtau / DiffSinger 基础渲染
→ constrained PITD / 演唱细节
→ 泠鸢 style profile
```

旧主流程：

```text
歌词字符窗口 → F0 median → heuristic split → MIDI
```

已确认不足，只保留 fallback，不再作为默认 melody transcription。

---

# 2. 固定事实 / 不再反复推翻的原则

## 2.1 GAME 是主转谱基座

- GAME raw 是主 melody transcription 来源；
- lyric char start 不是天然 note boundary；
- RMVPE / FCPE / third-F0 是 evidence，不从零重建整首谱；
- correction 只修 residual errors；
- forced-char-boundary 曾把约 419 notes 扩张到约 760 notes，并制造大量假 suspicious，禁止回到该路线。

## 2.2 GAME 有真实 stochasticity

```text
single GAME run != deterministic truth
```

GAME 多 runs 是同一模型 stochastic samples，不是多个独立模型。

Multi-run 用途：

```text
一致 → 增强置信
分歧 → 暴露 uncertainty
```

## 2.3 Consensus 不是最终谱面

Formal sequence alignment 支持：

```text
match / gap / split / merge
```

Consensus event 只表示 correspondence + uncertainty。

禁止把：

```text
start_median / duration_median / tone_median
```

拼成 synthetic final score。

## 2.4 Candidate 0 必须来自真实 GAME run

Candidate 0 = pairwise alignment cost 最小的真实 GAME medoid run。

Medoid 是 baseline selection，不是 correctness proof。

202s 已证明 GAME 自己可在同一区域产生约 MIDI 65 / 72 两套 stochastic 解：

```text
medoid selection != pitch truth
```

## 2.5 F0 measurement 与 score interpretation 分离

F0 measurement：

```text
RMVPE
FCPE
third-F0
periodicity
spectral / harmonic / subharmonic evidence
```

Score interpretation：

```text
GAME multi-run structure
cross-F0 plateau / changepoint
onset / energy
voiced transition
lyric articulation
duration plausibility
local melodic context
```

人工不负责猜 MIDI / Hz / cents / octave。

---

# 3. 当前工程状态

## M2.3 / M2.3.1 ✅

已完成：

- real GAME medoid Candidate 0；
- stochastic consensus；
- RMVPE + FCPE dual-F0；
- structural F0；
- plateau / interior re-triage；
- SAFE gate 初版；
- regression packets。

## M2.3.2A / A2 / A3 / A4 ✅ FROZEN

A-stage 已冻结，不再新增 A5。

主要成果：

- structure ambiguity 优先于 pitch-hard；
- frame-inclusive plateau geometry；
- RMVPE + FCPE unique plateau + temporal-overlap SAFE gate；
- raw flags 不覆盖 calibrated result；
- structure evidence 与 legacy triage 解耦；
- SAFE eligible 不能直接 repair；
- pitch / structure / identity / separation 正交状态；
- pitch / structure adjudication 分 lane，可共存；
- structure candidate 不直接进入人工；
- separator provenance 绑定实际 model path / bytes hash / config hash。

A4 baseline：

```text
421 notes
338 keep_baseline
76 pitch needs
51 structure needs
44 both
0 phrase review at A-stage
0 direct repair
```

## M2.3.2B1 / B2 / B3 ✅ FROZEN

B-stage 已冻结，不新增 B4。

### B1

commit `21be525c...`

初版 automatic pitch/octave adjudicator：

- third F0 = `librosa.pyin`；
- GAME run-tone distribution；
- RMVPE / FCPE reliability-weighted evidence；
- pYIN / ACF / harmonic / subharmonic；
- local continuity；
- separation sensitivity；
- `resolved_keep / resolved_change / unresolved` lifecycle；
- Candidate 0 不被覆盖。

### B2

commit `283100704470cbffa1866569ed42b7e6d0ce7b28`

完成 correctness/calibration：

- pitch+structure concurrent → B provisional，C first；
- structure ambiguous event 不再使用 aggregate `run_tones` 作为真实 pitch hypothesis；
- ACF 增加 T / 2T / T/2 octave discrimination；
- harmonic score 增加 odd-harmonic discrimination，抑制 low-octave harmonic-set superset bias；
- true-low / true-high / weak fundamental / missing fundamental / breathy / vibrato / short / silence regression；
- pYIN / ACF / harmonic / subharmonic 归入 waveform correlation group；
- `safe_retune_gate(..., target_midi=B.winning_hypothesis)`；
- third-F0 独立 provenance；
- 189s / 202s 保持 NO REPAIR。

### B3

commits：

```text
012cbfdf15253a98d50ca25f8f95c6b2c16c312b

e7500de43e7d99ca9e826430f5005d00281f05a5
```

完成最终 independence/provenance calibration：

1. third-F0 freshness 真正比较当前 `librosa.__version__`；
2. correlated waveform features 先做 bounded group fusion；
3. final hypothesis score / margin 使用 group-level score；
4. `supporting_independence_groups` 只从 finalized net `group_scores` 推导；
5. raw feature support 不再能绕过 `MIN_FAMILIES` / change gate / extractor-conflict gate；
6. `opposing_independence_groups` 增加用于 audit。

最终 evidence chain：

```text
raw features
→ within-group fusion
→ finalized group_scores
→ supporting_independence_groups
→ score / margin / resolution gates
```

禁止重新从 raw feature 反推 supporting group。

### 最新《年轮》B frozen baseline

```text
60 resolved_keep
7  resolved_change
15 unresolved
0  repair_candidate
```

其中 7 个 `resolved_change` 均因同时存在 structure pending 而：

```text
provisional = true
→ needs_structure_adjudication
→ 不允许 repair
```

例如：

```text
note_0385 @ 184.65s
B winner ≈ 61.87
→ provisional
→ route to C
```

本地报告：

```text
93 tests passed
```

GitHub 当前无 remote combined CI status，因此只能表述为本地测试报告通过。

189s / 202s 继续保持：

```text
NO FALSE REPAIR
```

---

# 4. Orthogonal state / lifecycle contract

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
```

Workflow 至少维护：

```text
routing_needs:
  pitch_adjudication: bool
  structure_adjudication: bool
  phrase_review: bool

pitch_adjudication_status:
  not_needed
  pending
  provisional
  resolved_keep
  resolved_change
  unresolved

structure_adjudication_status:
  not_needed
  pending
  resolved_keep
  resolved_change_candidate
  unresolved
```

强制规则：

- evidence state 与 workflow decision 分离；
- pitch / structure needs 可共存；
- provisional result 不得产生 repair；
- `needs_phrase_review` 只能在所有 machine lanes 不再 pending/provisional 后产生；
- Candidate 0 永不被 adjudication 原地覆盖。

---

# 5. Evidence independence / audit contract

逻辑独立 group：

```text
GAME stochastic
RMVPE
FCPE
waveform mechanism group
musical context（soft）
```

相关 waveform evidence：

```text
pYIN
ACF
harmonic
subharmonic
```

必须先做 within-group fusion，再影响 final score / margin。

最终：

```text
supporting_independence_groups
```

必须从 finalized net `group_scores` 推导。

raw：

```text
supporting_features
opposing_features
```

仅保留解释 / audit，不允许参与另一套 supporting-group gate。

### 关于 opposing_independence_groups

当前实现中：

```text
supporting_independence_groups
→ finalized net group semantics
```

而：

```text
opposing_independence_groups
```

仍部分消费 raw opposition，用作 **audit-only**。

因此当前不要把 `opposing_independence_groups` 当作新的 resolution gate truth。

后续若需要统一，可显式为每组保存：

```text
support_score
oppose_score
net_score
```

再从 group-level opposition 派生 opposing groups。

这不是 C 的 blocker，不新增 B4。

---

# 6. Cache / provenance contract

最终 provenance 至少覆盖：

```text
source_audio_sha256
separator_actual_model_path
separator_model_sha256
separator_config_sha256
GAME model hashes/config
RMVPE model hash/config
FCPE model hash/config
third-F0 vocal_sha256
third-F0 implementation
third-F0 runtime version
third-F0 config
third-F0 analysis schema
pitch adjudicator schema/config
structure adjudicator schema/config
```

规则：

```text
input / model / implementation / runtime version / config / schema changed
→ invalidate affected dependent artifact
```

Third-F0 frozen contract：

```text
cached version == current librosa.__version__
```

禁止只检查 version 字段非空。

---

# 7. M2.3.2C — Automatic Structure Adjudication ← 当前最高优先级

C 的目标不是直接“改谱”，而是先可靠回答：

```text
这里到底应该是一颗 note、两颗 notes、merge、portamento、grace，还是 artifact？
```

第一阶段：

```text
structure evidence
→ structure hypotheses
→ adjudication
→ precision calibration
```

**第一阶段禁止自动执行 split / merge / boundary repair。**

只有 C adjudication precision 经验证后，后续 M2.5 才讨论 structure repair。

## 7.1 输入不能只限现有 structure_varies

C 至少有两类输入。

### A. Existing structure candidates

来自：

```text
GAME multi-run split / merge variance
existing structure_state != stable
routing_needs.structure_adjudication == true
```

### B. Independent structure discovery

必须扫描 **全部 Candidate 0 baseline notes**，防止 GAME stable-but-wrong。

典型 case：

```text
GAME 5/5 stable one-note
但：
RMVPE 显示 two plateaus
FCPE 也显示 two plateaus
+ changepoint / onset / articulation 支持内部 boundary
```

即使：

```text
GAME structure_varies = false
```

也必须进入 C。

因此禁止：

```text
C input = only existing structure_varies
```

## 7.2 Independent discovery 至少检测

```text
dual-F0 multi-plateau agreement
cross-extractor changepoint agreement
strong voiced-to-voiced pitch transition
onset / energy transition
lyric articulation boundary
suspiciously merged long note
suspiciously short neighbouring notes
voiced gap / re-attack evidence
```

反向也必须识别：

```text
GAME stochastic split
但 acoustic evidence 支持 one note / portamento
→ 可以 resolved_keep
```

## 7.3 C evidence

至少使用：

```text
GAME multi-run structure distribution
RMVPE plateau / changepoint
FCPE plateau / changepoint
third-F0（必要时）
onset / RMS / energy
voiced transition / gap
lyric articulation
duration plausibility
local melodic continuity
```

注意 evidence independence：

```text
RMVPE 多个字段不是多票
FCPE 多个字段不是多票
同一 acoustic changepoint 的派生 feature 不得机械重复计数
```

C 也应尽量采用：

```text
feature evidence
→ mechanism/group fusion
→ hypothesis score / margin
```

而不是按 raw feature 数量投票。

## 7.4 C hypotheses

至少支持：

```text
H0 = current GAME structure
H1 = split candidate
H2 = merge candidate
H3 = one-note-with-portamento / ornament
```

目标分类至少：

```text
ONE_NOTE_WITH_PORTAMENTO
TRUE_SPLIT_CANDIDATE
TRUE_MERGE_CANDIDATE
GRACE_OR_ORNAMENT
F0_ARTIFACT
ALIGNMENT_ARTIFACT
UNRESOLVED_STRUCTURE
```

候选优先来自：

```text
真实 GAME run structure
或明确 acoustic boundary evidence
```

禁止：

```text
用 consensus median 拼 synthetic whole-score candidate
```

每个 hypothesis 至少记录：

```text
GAME structure support ratio
RMVPE changepoint / plateau support
FCPE changepoint / plateau support
third-F0 support if used
onset / energy support
lyric articulation support
duration plausibility
local context
supporting evidence/groups
opposing evidence/groups
score
margin
reason
```

---

# 8. C ↔ Frozen-B Lifecycle Contract — P0

这是 C 最重要的 correctness contract。

当前已有若干：

```text
B resolved_change
+ structure pending
→ B provisional
```

C 必须真正接管这些区域。

## 8.1 C resolved_keep

如果 C 判断当前 note identity / boundary 正确：

```text
structure_adjudication_status = resolved_keep
```

则：

```text
当前 note identity 固定
→ provisional B 必须 finalize 或重新 rerun frozen B
→ pitch_adjudication_status 不能继续 provisional
→ pitch pending 必须最终清理
```

禁止出现：

```text
C resolved_keep
但 provisional B 永久挂起
```

## 8.2 C resolved_change_candidate

如果 C 判断 structure 应改变：

```text
split
merge
boundary shift
note identity/time span material change
```

则原 B result **全部失效**。

强制：

```text
invalidate old provisional pitch_adjudication
→ generate NEW note identity / note spans
→ regenerate pitch evidence packets
→ rerun frozen B independently on each actual new note
```

不能：

```text
沿用旧 note identity 上的 B winner
沿用旧 confidence
沿用旧 margin
```

只要改变任一：

```text
note count
boundary
note identity
pitch-evidence extraction time span
```

都必须 invalidate + rerun B。

## 8.3 C unresolved

如果 structure 无法机器唯一决定：

```text
structure_adjudication_status = unresolved
structure pending = false
```

同时：

```text
provisional B 不允许 repair
```

并确保不会：

```text
unresolved
但 structure pending 仍 true
→ 无限重新进入 C
```

之后只有在所有 machine lane 都不再 pending/provisional 时，才进入 D。

---

# 9. C 第一阶段禁止自动 Structure Repair

当前阶段只允许产生：

```text
structure adjudication result
hypothesis ranking
confidence / margin
audit packet
```

暂时禁止自动写入 Candidate 0：

```text
split
merge
boundary shift
```

即：

```text
resolved_change_candidate
!= automatic structure repair
```

目的：先测 precision，再给修改权限。

必须保留：

```text
Candidate 0 unchanged
rollback contract intact
```

---

# 10. M2.3.2C Acceptance / Regression Matrix

至少完成以下验收。

## 10.1 Existing candidates

```text
1. 所有当前 structure_adjudication lane 都得到明确 C result
2. 不存在 pending 永久残留
3. result 可解释、有 evidence / score / margin
```

## 10.2 Independent discovery

```text
4. 扫描全部 Candidate 0 baseline notes
5. GAME-stable + dual-F0 two-plateau synthetic case 能被发现
6. GAME stable-but-wrong case 不依赖 structure_varies 才能进入 C
7. 没有 acoustic support 的普通 stable notes 不应大量误报
```

## 10.3 Reverse case

```text
8. GAME stochastic split + acoustic single-note / portamento
   → 能 resolved_keep 或 ONE_NOTE_WITH_PORTAMENTO
```

## 10.4 Provisional-B lifecycle

```text
9. C resolved_keep 后 provisional B 被 finalize/rerun
10. C structure change 后 old B 被 invalidated
11. 新 note identities 上重新生成 pitch evidence
12. frozen B 在新 note(s) 上重新执行
13. old winner/confidence/margin 不得复用
```

## 10.5 D reachability

```text
14. C unresolved 会 clear structure pending
15. unresolved 不会无限回 C
16. machine lanes 未 finalized 时不能进入 D
17. machine lanes finalized 且至少一个 unresolved 才能 needs_phrase_review
```

## 10.6 Safety / immutability

```text
18. C 第一阶段不自动修改 Candidate 0
19. provisional B 不得 repair
20. 189s / 202s no-false-repair regression 继续通过
21. frozen B regressions 全部保持 green
```

---

# 11. M2.3.2D — Phrase-Level Human Review

人工只处理 finalized B/C 后仍 unresolved 的音乐语义。

## 11.1 可达条件

```text
pitch_adjudication_status not in {pending, provisional}
structure_adjudication_status != pending
AND
至少一条 lane == unresolved
```

才允许：

```text
needs_phrase_review
```

人工不猜 F0 / MIDI / Hz / cents / octave。

## 11.2 Review 单位

默认完整乐句：

```text
最低约 3s
常规 5–8s
最长约 12s
```

优先：

```text
LRC line
vocal silence
breath gap
GAME phrase context
```

尽量包含目标前后各 2–3 notes。

## 11.3 Review 包

```text
SOURCE_PHRASE_original_mix.wav
SOURCE_PHRASE_separated_vocal.wav
BASELINE_PHRASE.wav
CANDIDATE_A_PHRASE.wav
CANDIDATE_B_PHRASE.wav
CANDIDATE_C_PHRASE.wav  # optional
```

要求：

- 时间窗完全一致；
- singer / phonemizer / color / volume / PITD policy 一致；
- 除目标 region 外 score 完全一致；
- 一次只改变一个待判断因素。

人工只选：

```text
Baseline / A / B / C / 都差不多 / 都不对
```

zoom clip 仅作二级辅助。

---

# 12. M2.4 — SAFE Repair Engine

进入条件：

```text
A frozen
B frozen
C available and calibrated
189s no false repair
202s no false repair
phrase review workflow available
Candidate 0 / rollback contract complete
```

第一版优先：

```text
single-note written-pitch retune
```

每个 repair 必须记录：

```text
region
before / after
B/C adjudication result
winning hypothesis
group_scores
supporting/opposing groups
confidence / margin
gates passed
rollback data
```

若最终 0 SAFE repairs，也是合法结果。

禁止覆盖 Candidate 0。

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

歌词冲突标：

```text
lyric_alignment_conflict
```

不得靠强移 voiced block 伪修复。

基础 USTX 验收：

> **不做泠鸢 style 和复杂 PITD 时，是否已经唱对旋律和节奏？**

通过后再加入：

```text
portamento
onset slide
ornament
vibrato
intonation deviation
```

PITD 不得掩盖 written-note error。

---

# 14. Evaluation / Audit

至少记录：

```text
GAME run note counts
pairwise alignment costs
selected medoid + sensitivity
GAME per-event run tone distribution
match/gap/split/merge counts
orthogonal states
routing needs / decision
pitch adjudication status / provisional flag
structure adjudication status
RMVPE / FCPE / third-F0 evidence
periodicity octave metrics
spectral octave metrics
supporting raw features
opposing raw features
group_scores
supporting_independence_groups
opposing_independence_groups (audit-only unless group-level opposition finalized)
winner / runner-up / margin
separation sensitivity
AUTO_RESOLVED / UNRESOLVED counts
independent structure discoveries
phrase-review count
regression status
cache/provenance manifest
```

Score artifact：

```text
Candidate 0
corrected score
retune count
split/merge/boundary-shift count
GAME preservation ratio
rollback coverage
```

---

# 15. Milestones

### M2.0 — Foundation survey ✅
### M2.1 / M2.1.1 — Initial diagnostic + correctness ✅
### M2.1.2 — GAME stochastic baseline ✅
### M2.2A — Formal sequence alignment ✅
### M2.2B — Dual-F0 ✅
### M2.3 — Residual-error triage ✅
### M2.3.1 — Triage calibration ✅
### M2.3.2A / A2 / A3 / A4 — Correctness + routing/provenance ✅ FROZEN
### M2.3.2B1 — Initial pitch/octave adjudicator ✅
### M2.3.2B2 — Pitch correctness/calibration ✅
### M2.3.2B3 — Independence/provenance/group-gate calibration ✅ FROZEN

最新 frozen B：

```text
60 resolved_keep
7 provisional resolved_change → C
15 unresolved
0 repair
93 local tests reported
```

### M2.3.2C — Automatic structure adjudication ← 当前最高优先级

重点：

```text
existing structure lanes
+ all-baseline independent discovery
+ provisional-B finalize/invalidate/rerun lifecycle
+ no automatic structure repair in first C stage
```

### M2.3.2D — Phrase-level human review

仅 machine lanes 全部 finalized 且存在 unresolved 后生成 3–12s phrase A/B/C 包。

### M2.4 — SAFE repair
### M2.5 — PROBABLE structure repair
### M2.6 — Optional second opinion
### M2.7 — Lyrics mapping + base USTX
### M2.8 — PITD + render loop
### M2.9 — 《年轮》M2 验收
### M3 — 泠鸢 style profile

> **原唱决定“唱什么”；泠鸢参考决定“怎么唱”。**

---

# 16. 最终原则

1. **GAME 是默认 melody transcription 基座。**
2. **Candidate 0 必须来自真实 GAME run。**
3. **Medoid 是 baseline selection，不是 correctness proof。**
4. **Consensus 是 uncertainty graph，不是最终 note skeleton。**
5. **F0 measurement 与 score interpretation 分开。**
6. **能程序测量的 pitch / octave 不交给人工猜。**
7. **单 F0 extractor 不能独自推翻 GAME。**
8. **同一 extractor 的多个 feature 不是多票。**
9. **GAME 多 runs 是 stochastic samples，不是多个独立模型。**
10. **GAME stochastic support 保留连续置信度。**
11. **结构未定时，不做 final written-pitch adjudication。**
12. **Pitch+structure concurrent region 先解析 note identity，或 B 只能 provisional。**
13. **C resolved_keep 后必须 finalize/rerun provisional B。**
14. **C 改变 note identity/time span 后必须 invalidate / regenerate / rerun B。**
15. **Octave ACF 必须处理倍周期歧义。**
16. **Harmonic score 必须避免低八度 harmonic-set 超集偏置。**
17. **相关 waveform features 必须先 group fusion，再影响 final score / margin。**
18. **supporting independence groups 必须从 finalized net group scores 推导。**
19. **raw feature support 不得绕过 group-level gate。**
20. **opposing_independence_groups 当前仅作为 audit，不作为额外 gate truth。**
21. **pYIN 与 ACF 不能机械算作两个完全独立 hard votes。**
22. **Octave change 优先要求跨机制 evidence convergence。**
23. **Separation artifact 只作为 uncertainty，不直接当真值。**
24. **Cache/provenance 必须真正参与 invalidation。**
25. **Third-F0 runtime version 必须参与 freshness check。**
26. **Repair gate 必须显式绑定 adjudicator winning hypothesis。**
27. **Pitch / structure / identity / separation 使用正交状态。**
28. **C 必须扫描全部 baseline 做 independent structure discovery，防止 GAME stable-but-wrong。**
29. **C 第一阶段只 adjudicate，不自动执行 structure repair。**
30. **B/C 有 explicit pending/provisional/resolved/unresolved lifecycle。**
31. **needs_phrase_review 只能在 machine lanes 全结束后产生。**
32. **人工默认审核完整乐句，不审核 isolated note。**
33. **Phrase candidates 除目标局部外必须完全一致。**
34. **189s 永久作为 extractor-conflict regression。**
35. **202s 永久作为 stochastic pitch / identity-variable regression。**
36. **0 automatic repairs 是合法结果。**
37. **Candidate 0 永远可 rollback。**
38. **所有修改必须局部、可解释、可审计、可 A/B。**
39. **先把 written score 唱对，再生成 PITD。**
40. **先“唱对”，再做泠鸢风格。**
