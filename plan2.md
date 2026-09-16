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
→ structure 未定：先 M2.3.2C structure adjudication
→ note identity 确定后：M2.3.2B finalized pitch/octave adjudication
→ finalized machine unresolved 才进入 M2.3.2D phrase-level A/B/C review
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

完成初版 automatic pitch/octave adjudicator：

- third F0 = `librosa.pyin`；
- GAME run-tone distribution；
- RMVPE / FCPE reliability-weighted evidence；
- pYIN / ACF / harmonic / subharmonic；
- local continuity；
- separation sensitivity；
- `resolved_keep / resolved_change / unresolved` lifecycle；
- Candidate 0 不被覆盖。

## M2.3.2B2 ✅ IMPLEMENTED

commit `283100704470cbffa1866569ed42b7e6d0ce7b28`

完成 correctness/calibration：

- pitch+structure concurrent → B provisional，C first；
- structure ambiguous event 不再使用 aggregate `run_tones` 作为真实 pitch hypothesis；
- ACF 增加 T / 2T / T/2 octave discrimination；
- harmonic score 增加 odd-harmonic discrimination，抑制 low-octave harmonic-set superset bias；
- true-low / true-high / weak fundamental / missing fundamental / breathy / vibrato / short / silence regression；
- pYIN / ACF / harmonic / subharmonic 归入 waveform correlation group；
- `safe_retune_gate(..., target_midi=B.winning_hypothesis)`；
- third-F0 拥有独立 provenance；
- 189s / 202s 保持 NO REPAIR。

## M2.3.2B3 ✅ IMPLEMENTED / FINAL PATCH PENDING

commit `012cbfdf15253a98d50ca25f8f95c6b2c16c312b`

B3 已完成原计划中的两个 blocker：

1. third-F0 freshness 已比较当前 `librosa.__version__`；
2. final hypothesis score / margin 已改成 group-level fusion，waveform correlated features 不再 feature-level 叠加。

当前 group-level score：

```text
game
+ rmvpe
+ fcpe
+ bounded waveform group
+ soft context
```

waveform 内：

```text
third-F0 / periodicity / harmonic support
+ periodicity / subharmonic / third-F0 opposition
→ bounded waveform net group score
```

最新《年轮》B3 rerun：

```text
65 resolved_keep
2  provisional resolved_change → structure lane
16 unresolved
0  repair_candidate
```

关键 regression：

```text
189s → unresolved → NO REPAIR
202s → unresolved → NO REPAIR
```

本地报告 91 tests passed；GitHub 当前仍无 remote combined CI status，因此不能把本地测试表述成远端 CI 已验证。

**B3 现在只剩一个 final consistency patch。修完后 M2.3.2B 正式 FROZEN，不新增 B4。**

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

逻辑独立 group：

```text
GAME stochastic
RMVPE
FCPE
waveform mechanism group
musical context（soft）
```

注意：

```text
RMVPE raw center + RMVPE plateau
→ 同一 RMVPE group

pYIN + ACF + harmonic + subharmonic
→ correlated waveform evidence
→ 先做 within-group fusion
→ 最终只形成一个 bounded waveform group influence
```

**最终 score、margin、supporting group、resolution gate 必须使用同一套 group-level semantics。**

raw features：

```text
supporting_features
opposing_features
```

只用于解释 / audit，不允许再作为另一套 group-support 判定源。

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

B3 已要求：

```text
cached third-F0 version == current librosa.__version__
```

禁止只检查 version 非空。

---

# 7. M2.3.2B3 Final Patch — Group Gate Consistency ← 当前最高优先级

> 不新增 B4。该 patch 属于 B3 完成条件。完成后立即冻结 B，进入 C。

## 7.1 当前剩余问题

B3 已正确把 hypothesis score 改成 group-level fusion，例如：

```text
waveform_group_score =
bounded support
− bounded opposition
```

但当前 `supporting_independence_groups` 仍可能根据 raw：

```text
win.supporting[feature] > threshold
```

推导，而不是根据融合后的：

```text
win.group_scores[group]
```

推导。

这样会出现 score/gate 语义不一致。

示例：

```text
periodicity support = 0.30
third-F0 opposition = 0.90

waveform net group score
= max(0, 0.30 - 0.5*0.90)
= 0
```

此时正确语义是：

```text
waveform 没有净支持 winner
```

但如果仍从 raw feature 看：

```text
periodicity support 0.30 > threshold
```

就可能错误得到：

```text
"waveform" ∈ supporting_independence_groups
```

进而错误通过：

```text
change_requires_waveform_support
extractor_conflict_unresolved_by_waveform
MIN_FAMILIES
```

等 gate。

## 7.2 强制修复

`supporting_independence_groups` 必须**直接从 finalized group_scores 派生**。

推荐：

```text
group_scores:
  game
  rmvpe
  fcpe
  waveform
  context
```

其中：

```text
supporting_independence_groups =
  groups whose FINAL NET group score > calibrated_support_threshold
```

至少：

```text
game:
  group_scores.game > threshold

rmvpe:
  group_scores.rmvpe > threshold

fcpe:
  group_scores.fcpe > threshold

waveform:
  group_scores.waveform > threshold
```

`context` 保持 soft evidence，默认不计入 hard-family / MIN_FAMILIES。

禁止：

```text
先用 group_scores 算 score/margin
然后又从 raw supporting_features 重新推 supporting groups
```

必须保证：

```text
feature evidence
→ group fusion
→ group_scores
→ supporting/opposing groups
→ score / margin / gates
```

是一条单向、统一的证据链。

## 7.3 Change gate 与 extractor-conflict gate

以下 gate 都必须消费 finalized net groups：

```text
MIN_FAMILIES
change_requires_waveform_support
extractor_conflict_unresolved_by_waveform
```

例如：

```text
would_change == true
AND waveform_group_score <= support_threshold
→ 必须有 change_requires_waveform_support
```

即使某个 waveform raw feature 单独 > threshold，也不能放行。

Extractor conflict：

```text
waveform net group support
+ 至少一个 non-GAME extractor net group support
```

才允许认为 waveform/extractor convergence 存在。

## 7.4 建议增加 opposing group audit

可选但推荐输出：

```text
supporting_independence_groups
opposing_independence_groups
group_scores
```

`opposing_independence_groups` 同样从 group-level net/opposition semantics 派生。

目的不是再加新票，而是让 audit 能明确回答：

```text
哪些独立机制净支持 winner？
哪些独立机制净反对 winner？
```

## 7.5 强制 regression

至少新增：

```text
1. raw periodicity weak-support + stronger same-group opposition
   → waveform net score == 0
   → waveform NOT IN supporting_independence_groups

2. waveform net score == 0
   → automatic resolved_change 不能靠 waveform gate 通过

3. extractor conflict:
   raw waveform feature 有支持，但 waveform net group 无支持
   → 必须保持 unresolved

4. supporting_independence_groups 与 group_scores 一致
   → 不存在 group_score<=threshold 但 group 被标 supporting

5. 已有 B3 correlated-feature regressions 全部继续通过
```

## 7.6 B freeze acceptance

B 最终冻结要求：

```text
third-F0 runtime version freshness PASS
group-level score fusion PASS
supporting groups derived from finalized net group scores
raw feature cannot bypass group gate
true-low / true-high mirror PASS
weak/missing fundamental regressions PASS
189s NO FALSE REPAIR
202s NO FALSE REPAIR
safe gate target == B winning hypothesis
provisional B cannot repair
Candidate 0 unchanged
all B regressions green
```

允许：

```text
resolved_change = 0
repair = 0
```

不为了自动化率放松 gate。

完成后：

```text
M2.3.2B1 / B2 / B3 = FROZEN
→ 不新增 B4
→ M2.3.2C
```

---

# 8. M2.3.2C — Automatic Structure Adjudication

> B freeze 后正式进入。C 同时承担 concurrent pitch+structure region 的 note-identity resolution。

当前 B3 rerun 顶层 structure lane 数量以最新 diagnostic 为准；不要硬编码旧的 51/57，rerun 后重新统计。

C **不能只处理现有 `structure_varies` cases**。

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

C 必须扫描**所有 Candidate 0 baseline notes**，寻找：

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

反向也必须能识别：

```text
GAME stochastic split
但 acoustic evidence 支持 single note / portamento
→ resolved_keep
```

## 8.3 C hypotheses

```text
H0 = current GAME structure
H1 = split candidate
H2 = merge candidate
H3 = one-note-with-portamento / ornament
```

候选优先来自：

```text
真实 GAME run structure
或明确 acoustic boundary evidence
```

禁止由 consensus median 拼 whole-score synthetic result。

每个 hypothesis 至少记录：

```text
GAME structure support ratio
RMVPE changepoint / plateau support
FCPE changepoint / plateau support
third-F0 support if used
onset / energy support
lyric articulation support
duration plausibility
local melodic context
supporting groups
opposing groups
margin
reason
```

## 8.4 C ↔ provisional B contract

这是 C 的 P0。

如果 C：

```text
resolved_keep
→ 当前 note identity 固定
→ provisional B 必须 finalize / rerun
→ pitch pending 最终被清理

resolved_change_candidate
→ old provisional B INVALID
→ regenerate pitch packets for NEW note identities
→ rerun frozen B on each actual note

unresolved
→ structure status = unresolved
→ provisional pitch 不得产生 repair
→ machine lanes 全结束后才进入 D
```

**这不是注释约定，必须有可执行 lifecycle + regression。**

### 强制 invalidation

C 改变任一：

```text
note count
boundary
note identity
time span materially used by pitch evidence
```

都必须：

```text
invalidate old provisional pitch_adjudication
regenerate evidence packet
rerun B
```

不能沿用旧 note identity 上的 B winner/confidence。

## 8.5 C result state

```text
structure_adjudication_status:
  not_needed
  pending
  resolved_keep
  resolved_change_candidate
  unresolved
```

第一阶段 structure repair **不自动执行**；先验证 adjudication precision。

## 8.6 C routing / D reachability

C unresolved 后：

```text
structure_adjudication_status = unresolved
clear structure pending
```

不能：

```text
unresolved
但 structure_adjudication 仍 pending
→ 无限回 C
```

只有：

```text
pitch_adjudication_status not in {pending, provisional}
structure_adjudication_status != pending
AND 至少一条 lane == unresolved
```

才允许进入 D。

## 8.7 C acceptance / regressions

至少：

```text
1. existing structure candidates 全部得到 C result
2. GAME-stable + dual-F0 two-plateau 能被 independent discovery 找到
3. GAME stable-but-wrong synthetic regression
4. GAME stochastic split + acoustic single-note 可 resolved_keep
5. pitch+structure concurrent region：C resolved_keep 后 provisional B 被 finalize/rerun
6. C structure change 后旧 B invalidated，并在新 note identities 上 rerun
7. C unresolved 不会无限回 C
8. unresolved 只有 machine lanes finalized 后才进入 D
9. no C result directly overwrites Candidate 0
```

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
B frozen
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
group_scores
supporting/opposing groups
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
supporting raw features
opposing raw features
group_scores
supporting_independence_groups
opposing_independence_groups if implemented
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
### M2.3.2B2 — Pitch correctness/calibration ✅
### M2.3.2B3 — Independence/provenance calibration ✅ IMPLEMENTED / FINAL PATCH PENDING

最新 B3：

```text
65 resolved_keep
2 provisional resolved_change → C
16 unresolved
0 repair
91 local tests reported
```

当前唯一 patch：

```text
supporting_independence_groups / change gates
必须从 finalized net group_scores 推导
不得从 raw feature support 反推
```

修完：

```text
M2.3.2B = FROZEN
不新增 B4
```

### M2.3.2C — Automatic structure adjudication ← B final patch 后下一阶段

Existing structure candidates + all-baseline independent discovery；兑现 provisional-B invalidate/finalize/rerun contract。

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
17. **supporting independence groups 必须从 finalized net group scores 推导。**
18. **raw feature support 不得绕过 group-level gate。**
19. **pYIN 与 ACF 不能机械算作两个完全独立 hard votes。**
20. **Octave change 优先要求跨机制 evidence convergence。**
21. **Separation artifact 只作为 uncertainty，不直接当真值。**
22. **Cache/provenance 必须真正参与 invalidation。**
23. **Third-F0 runtime version 必须参与 freshness check。**
24. **Repair gate 必须显式绑定 adjudicator winning hypothesis。**
25. **Pitch / structure / identity / separation 使用正交状态。**
26. **C 必须做 independent structure discovery，防止 GAME stable-but-wrong。**
27. **B/C 有 explicit pending/provisional/resolved/unresolved lifecycle。**
28. **needs_phrase_review 只能在 machine lanes 全结束后产生。**
29. **人工默认审核完整乐句，不审核 isolated note。**
30. **Phrase candidates 除目标局部外必须完全一致。**
31. **189s 永久作为 extractor-conflict regression。**
32. **202s 永久作为 stochastic pitch / identity-variable regression。**
33. **0 automatic repairs 是合法结果。**
34. **Candidate 0 永远可 rollback。**
35. **所有修改必须局部、可解释、可审计、可 A/B。**
36. **先把 written score 唱对，再生成 PITD。**
37. **先“唱对”，再做泠鸢风格。**
