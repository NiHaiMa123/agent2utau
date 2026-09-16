# agent2utau — Plan 2：GAME 主转谱 + 自动证据裁决 + Phrase-Level 审核

> 修订日期：2026-09-16
>
> 核心原则：**先把“唱对”解决，再把“唱得像泠鸢”解决。**
>
> 当前工程原则：GAME 提供真实可渲染的 score candidate；multi-run consensus 只作为 uncertainty / evidence graph。可程序测量的 pitch / octave 不交给人工猜；structure 未确定时不做 final written-pitch adjudication；只有机器仍无法唯一解释的音乐语义才进入完整乐句人工审核。

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
→ 若 structure 未定：先 structure adjudication
→ 在确定 note identity 上做 pitch/octave adjudication
→ finalized machine unresolved 才进入 phrase-level A/B/C review
→ 只修高置信局部错误
→ lyrics ↔ melody mapping
→ OpenUtau / DiffSinger 基础渲染
→ constrained PITD / 演唱细节
→ 泠鸢 style profile
```

旧主流程：

```text
歌词字符窗口 → F0 median → heuristic split → MIDI
```

只保留 fallback，不再作为默认 melody transcription。

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
cross-F0 plateau/changepoint
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

## M2.3.2B1 ✅ IMPLEMENTED

commit `21be525c...`

已实现：

- third F0 = `librosa.pyin`；
- GAME run-tone distribution；
- RMVPE / FCPE reliability-weighted evidence；
- pYIN；
- FFT-ACF；
- harmonic / subharmonic；
- local continuity；
- separation sensitivity 只降 confidence；
- `resolved_keep / resolved_change / unresolved` lifecycle；
- Candidate 0 不被 B 覆盖。

B1 rerun：

```text
87 pitch lanes
72 resolved_keep
0 resolved_change
15 unresolved
0 repair
```

B1 未冻结，原因：structure/pitch ordering、octave waveform bias、cache/independence correctness 尚需收紧。

## M2.3.2B2 ✅ IMPLEMENTED / NOT YET FROZEN

commit `283100704470cbffa1866569ed42b7e6d0ce7b28`

已完成：

1. pitch+structure concurrent region：

```text
B result = provisional
→ C first
→ pitch need 保留
```

2. structure ambiguous event 不再把 aggregate `run_tones` 当真实 pitch hypotheses；
3. ACF 增加 T / 2T / T/2 octave discrimination；
4. harmonic score 加 odd-harmonic discrimination，削弱低八度 harmonic-set superset bias；
5. 新增 true-low / true-high / weak fundamental / missing fundamental / breathy / vibrato / short / silence waveform regressions；
6. pYIN / ACF / harmonic / subharmonic 在 gate 上归到 waveform correlation group；
7. `safe_retune_gate(..., target_midi=B.winning_hypothesis)`；
8. third-F0 增加独立 vocal/config/schema provenance；
9. 189s / 202s 继续 NO REPAIR。

最新《年轮》B2 rerun：

```text
87 pitch lanes
64 resolved_keep
2  resolved_change  # provisional，转入 C
14 unresolved
0  repair_candidate

final decisions:
331 keep_baseline
57 needs_structure_adjudication
23 auto_resolved
9  needs_phrase_review
```

189.84s：

```text
winner ≈ 58.1
GAME + FCPE + waveform 支持
RMVPE opposition + separation sensitive
→ unresolved
→ NO REPAIR
```

202.52s：

```text
baseline 本轮写 65.3
B winner ≈ 72.3
RMVPE + FCPE + waveform 支持
periodicity / separation counter-evidence
→ unresolved
→ NO REPAIR
```

本地报告 87 tests passed；GitHub 当前无 remote combined CI status，不能把本地测试表述成远端 CI 已验证。

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

# 5. Evidence independence contract

禁止按 raw feature 数量简单投票。

逻辑独立源至少区分：

```text
GAME stochastic
RMVPE
FCPE
waveform / periodicity / spectral mechanism group
musical context
```

注意：

```text
RMVPE raw center + RMVPE plateau
→ 同一 family

pYIN + ACF
→ 都高度依赖周期机制
→ 不能机械算两张独立 hard votes
```

B2 已在“resolution gate 数组”层面引入 independence groups，但 **B3 必须继续把 independence 约束推进到实际 score / margin 本身。**

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

“记录 provenance”不等于“真正参与 invalidation”。

---

# 7. M2.3.2B3 — Final Independence / Provenance Calibration ← 当前最高优先级

B2 主体正确，但还有两个 blocker。**B3 只解决这两个问题，不再扩展新算法。完成后冻结 B，进入 C。**

## 7.1 Blocker 1：third-F0 runtime version 必须真正参与 cache invalidation

当前 `_third_f0_fresh()` 已检查：

```text
vocal_sha256
schema
implementation/config
version 字段存在
```

但当前实现只验证：

```text
prov.version is not None
```

并没有验证：

```text
prov.version == 当前运行时 librosa.__version__
```

因此可能发生：

```text
旧 cache: librosa 1.0.0
当前环境: librosa 1.x
配置相同
→ 旧 third_f0.npz 仍被误认为 fresh
```

### 必须修改

当前 runtime expected provenance 必须显式包含：

```text
implementation = librosa.pyin
runtime_version = librosa.__version__
fmin
fmax
frame_length
hop_length / hop_ms
voicing config
schema
vocal_sha256
```

Fresh 条件必须逐项比较：

```text
cached runtime_version == current runtime_version
```

禁止只检查 version 字段非空。

### Regression

至少：

```text
same vocal + same config + same version → cache hit
same vocal + changed librosa version → cache stale
changed vocal bytes → stale
changed pYIN config → stale
changed schema → stale
```

## 7.2 Blocker 2：independence grouping 必须影响 score / margin，而不只影响 gate count

B2 已正确做到：

```text
pYIN + ACF + harmonic + subharmonic
→ waveform group
```

因此它们不会在 `MIN_FAMILIES` 上被机械算成 4 个独立 family。

但当前 winner score / margin 仍主要按 feature-level 相加：

```text
GAME
+ RMVPE
+ FCPE
+ pYIN
+ ACF
+ harmonic
+ continuity
```

也就是说：

```text
pYIN + ACF + harmonic
```

虽然 gate 上只有一个 waveform group，仍可能在：

```text
winner score
margin_to_runner_up
```

中贡献多次，从而放大同一相关机制的影响。

### B3 强制改为 group-level fusion

推荐 pipeline：

```text
feature evidence
↓
within-group fusion / normalization
↓
group scores
↓
final hypothesis score / margin
```

至少产生：

```text
game_group_score
rmvpe_group_score
fcpe_group_score
waveform_group_score
context_group_score  # soft only
```

waveform group 内可以采用：

```text
calibrated weighted mean
或 robust aggregate
```

但必须：

```text
固定范围 / cap
```

防止因为 waveform features 数量增加而自动提高 group 权重。

### 强制性质

例如：

```text
Case A:
waveform only has ACF support = 0.8

Case B:
同一个底层 octave failure 同时导致
pYIN=0.8 + ACF=0.8 + harmonic=0.8
```

Case B 不得仅因为相关 features 更多，就把 waveform group 从“一票”膨胀成三票，并明显人为扩大 winner margin。

### Regression

至少：

```text
1. duplicate correlated waveform feature does not materially increase group score
2. pYIN+ACF+harmonic 同向时仍只占 bounded waveform-group influence
3. adding another correlated waveform feature cannot alone flip an otherwise unresolved decision
4. cross-group convergence CAN legitimately increase confidence
5. GAME + FCPE + waveform 与 GAME + FCPE + 3×waveform-feature 在 independent-group count 上等价
```

## 7.3 B3 不允许破坏 B2 已通过的 contract

继续必须通过：

```text
true-low octave regression
true-high octave mirror regression
weak fundamental
missing fundamental
breathy/noisy
vibrato
short note
silence/unvoiced
189s NO REPAIR
202s NO REPAIR
safe gate target == B winning hypothesis
structure-ambiguous run_tones 不进入 final hypotheses
provisional B 不产生 repair
```

## 7.4 B3 acceptance

```text
third-F0 current runtime version participates in freshness check
feature-level correlated evidence cannot inflate final margin without bound
final score / margin reflects independence groups
189s no false repair
202s no false repair
Candidate 0 unchanged
all existing B2 regressions remain green
```

允许：

```text
resolved_change = 0
repair = 0
```

不为了自动化率放松 gate。

B3 完成后：

```text
M2.3.2B1 / B2 / B3 = FROZEN
→ M2.3.2C
```

---

# 8. M2.3.2C — Automatic Structure Adjudication

> B3 完成后正式进入。C 同时承担 concurrent pitch+structure region 的 note-identity resolution。

当前 B2 rerun 顶层有约：

```text
57 needs_structure_adjudication
```

但 C **不能只处理现有 structure_varies cases**。

## 8.1 Existing structure candidates

Evidence：

```text
GAME multi-run structure distribution
RMVPE plateau / changepoint
FCPE plateau / changepoint
third-F0（必要时）
onset / energy
voiced transition
lyric articulation
duration plausibility
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

## 8.2 Independent structure discovery：防止 GAME stable-but-wrong

C 必须扫描所有 Candidate 0 baseline notes，寻找：

```text
GAME 5/5 stable one-note
但 dual-F0 显示 two plateaus
+ changepoint / onset / articulation 支持 boundary
```

至少检测：

```text
dual-F0 multi-plateau agreement
cross-extractor changepoint agreement
strong voiced-to-voiced pitch transition
onset / energy transition
lyric articulation boundary
suspiciously merged long note
suspiciously short neighbouring notes
```

足够强时，即使：

```text
GAME structure_varies = false
```

也必须进入 C。

## 8.3 C hypotheses

```text
H0 = current GAME structure
H1 = split candidate
H2 = merge candidate
H3 = one-note-with-portamento / ornament
```

候选优先来自真实 GAME run structure 或明确 acoustic boundary evidence。

禁止由 consensus median 拼 whole-score synthetic result。

## 8.4 C ↔ provisional B contract

如果 C：

```text
resolved_keep
→ 当前 note identity 固定
→ provisional B 必须 finalize 或 rerun
→ pitch pending 最终被清理

resolved_change_candidate
→ old provisional B INVALID
→ regenerate pitch packets for new note identities
→ rerun B

unresolved
→ structure status = unresolved
→ provisional pitch 不得直接 repair
→ machine lanes 全结束后才进入 D
```

这不是注释约定，必须有可执行 lifecycle + regression。

## 8.5 C result state

```text
structure_adjudication_status:
  not_needed
  pending
  resolved_keep
  resolved_change_candidate
  unresolved
```

第一阶段 structure repair 不自动执行；先验证 adjudication precision。

---

# 9. M2.3.2D — Phrase-Level Human Review

人工只处理 finalized B/C 后仍 unresolved 的音乐语义。

## 9.1 可达条件

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

## 9.2 Review 单位

```text
最低约 3s
常规 5–8s
最长约 12s
```

优先：

```text
LRC line / vocal silence / breath gap / GAME phrase context
```

尽量包含目标前后各 2–3 notes。

## 9.3 Review 包

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

# 10. M2.4 — SAFE Repair Engine

进入条件：

```text
A frozen
B3 frozen
C available
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
independence group scores
confidence / margin
gates passed
rollback data
```

若最终 0 SAFE repairs，也是合法结果。

禁止覆盖 Candidate 0。

---

# 11. Lyrics / USTX / PITD

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

歌词冲突标 `lyric_alignment_conflict`，不得靠强移 voiced block 伪修复。

基础 USTX 验收：

> **不做泠鸢 style 和复杂 PITD 时，是否已经唱对旋律和节奏？**

通过后再加入 portamento / onset slide / ornament / vibrato / intonation deviation。

PITD 不得掩盖 written-note error。

---

# 12. Evaluation / Audit

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
supporting features
independence group scores
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

# 13. Milestones

### M2.0 — Foundation survey ✅
### M2.1 / M2.1.1 — Initial diagnostic + correctness ✅
### M2.1.2 — GAME stochastic baseline ✅
### M2.2A — Formal sequence alignment ✅
### M2.2B — Dual-F0 ✅
### M2.3 — Residual-error triage ✅
### M2.3.1 — Triage calibration ✅
### M2.3.2A / A2 / A3 / A4 — Correctness + routing/provenance ✅ FROZEN
### M2.3.2B1 — Initial pitch/octave adjudicator ✅
### M2.3.2B2 — Pitch correctness/calibration ✅ IMPLEMENTED / NOT FROZEN

最新 B2：

```text
87 pitch lanes
64 resolved_keep
2 provisional resolved_change → C
14 unresolved
0 repair
```

### M2.3.2B3 — Final independence/provenance calibration ← 当前最高优先级

只做两件事：

1. third-F0 当前 runtime version 真正进入 cache freshness；
2. final score / margin 改为 independence-group-level fusion，禁止相关 waveform features 数量膨胀影响力。

B3 完成后冻结 B，不再新增 B4。

### M2.3.2C — Automatic structure adjudication

Existing structure candidates + all-baseline independent discovery；同时兑现 provisional-B invalidate/finalize/rerun contract。

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

# 14. 最终原则

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
13. **C 改变 note identity 后必须 invalidate / rerun B。**
14. **Octave ACF 必须处理倍周期歧义。**
15. **Harmonic score 必须避免低八度 harmonic-set 超集偏置。**
16. **相关 waveform features 必须先 group fusion，再影响 final score / margin。**
17. **pYIN 与 ACF 不能机械算作两个完全独立 hard votes。**
18. **Octave change 优先要求跨机制 evidence convergence。**
19. **Separation artifact 只作为 uncertainty，不直接当真值。**
20. **Cache/provenance 必须真正参与 invalidation。**
21. **Third-F0 runtime version 必须参与 freshness check。**
22. **Repair gate 必须显式绑定 adjudicator winning hypothesis。**
23. **Pitch / structure / identity / separation 使用正交状态。**
24. **C 必须做 independent structure discovery，防止 GAME stable-but-wrong。**
25. **B/C 有 explicit pending/provisional/resolved/unresolved lifecycle。**
26. **needs_phrase_review 只能在 machine lanes 全结束后产生。**
27. **人工默认审核完整乐句，不审核 isolated note。**
28. **Phrase candidates 除目标局部外必须完全一致。**
29. **189s 永久作为 extractor-conflict regression。**
30. **202s 永久作为 stochastic pitch / identity-variable regression。**
31. **0 automatic repairs 是合法结果。**
32. **Candidate 0 永远可 rollback。**
33. **所有修改必须局部、可解释、可审计、可 A/B。**
34. **先把 written score 唱对，再生成 PITD。**
35. **先“唱对”，再做泠鸢风格。**
