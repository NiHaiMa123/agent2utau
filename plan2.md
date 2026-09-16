# agent2utau — Plan 2：GAME 主转谱 + 自动证据裁决 + Phrase-Level 审核

> 修订日期：2026-09-16
>
> 核心原则：**先把“唱对”解决，再把“唱得像泠鸢”解决。**
>
> 当前阶段：**M2.3.2B 已冻结；M2.3.2C1 已实现但不可冻结；当前最高优先级 = E1 Remote CI + M2.3.2C2 Structure Correctness / Lifecycle Calibration。**

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
→ structure 未定：M2.3.2C structure adjudication
→ note identity 确定后：在真实/候选 note identity 上运行冻结版 B pitch/octave adjudicator
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
onset / re-attack
voiced transition / gap
energy envelope
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

A-stage 已冻结，不新增 A5。

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

主要成果：

- pitch / structure / identity / separation 正交状态；
- pitch / structure adjudication lanes 可共存；
- structure candidate 不直接进入人工；
- raw flags 不覆盖 calibrated result；
- SAFE eligible 不能直接 repair；
- separator provenance 绑定实际 model path / bytes hash / config hash。

## M2.3.2B1 / B2 / B3 ✅ FROZEN

B-stage 不新增 B4。

关键 commits：

```text
21be525c...  B1 initial pitch/octave adjudicator
283100704470cbffa1866569ed42b7e6d0ce7b28  B2 correctness/calibration
012cbfdf15253a98d50ca25f8f95c6b2c16c312b  B3 independence/provenance
e7500de43e7d99ca9e826430f5005d00281f05a5  B3 final group-gate consistency
```

Frozen B contract：

- GAME run-tone distribution 保留连续支持强度；
- RMVPE / FCPE 各自只算一个 evidence family；
- pYIN / ACF / harmonic / subharmonic 先融合为 bounded waveform group；
- score / margin / supporting groups / gates 使用统一 group-level semantics；
- raw feature 只用于 audit，不能绕过 group gate；
- ACF 处理 T / 2T / T/2 octave ambiguity；
- harmonic evidence 抑制 low-octave harmonic-set superset bias；
- third-F0 cache 比较当前 `librosa.__version__`；
- `safe_retune_gate(..., target_midi=B.winning_hypothesis)`；
- 189s / 202s 保持 NO FALSE REPAIR。

Frozen B latest baseline：

```text
60 resolved_keep
7  provisional resolved_change → C
15 unresolved
0  repair_candidate
93 local tests reported
```

> 历史上 A/B freeze 发生时仓库尚未建立 remote CI。E1 建立后，**A/B 全部 regression 必须在 remote CI 中补跑并 green；若失败，则对应 frozen contract 自动 reopen。**

## M2.3.2C1 ✅ IMPLEMENTED / ❌ NOT FROZEN

commit：

```text
676a26eab4dacd8e394eee4529e91e52d219b7db
```

C1 已实现：

- `discover_structure()` 扫描全部 baseline notes；
- existing structure lanes + independent discovery 都可进入 C；
- H0 keep / H1 split / H2 merge / H3 portamento；
- C 第一阶段只 adjudicate，不修改 Candidate 0；
- C unresolved 会清 pending，避免无限 loop；
- resolved_keep 能处理 provisional B 的基础 lifecycle；
- old B 在 structure change 后会被 invalidated。

C1 《年轮》结果：

```text
338 packets adjudicated
287 resolved_keep
  ├─ 220 clean keep
  └─ 67 portamento
47 TRUE_SPLIT_CANDIDATE
4 unresolved
0 merge
0 repair
106 local tests reported
```

这些数字**不是 correctness proof**。尤其 47 split candidates 当前必须视为 calibration set，而不是 47 个已确认 GAME 错误。

C1 尚未冻结的原因见 §8 C2。

---

# 4. Remote CI / Freeze Gate — E1（当前 P0 工程要求）

## 4.1 当前事实

仓库当前不存在：

```text
.github/workflows/
```

因此没有 GitHub Actions remote CI。此前 plan 只规定：

```text
没有 remote CI 时，不得把 local tests passed 描述成 remote verified
```

这只是**报告约束**，不是**工程验收约束**，所以不足。

从本次 revision 起，remote CI 变成 hard gate。

## 4.2 必须建立 GitHub Actions

至少创建：

```text
.github/workflows/ci.yml
```

触发：

```text
push
pull_request
```

至少包含一个 Linux / Python 3.11 job（项目 `requires-python >=3.11`）：

```text
checkout
setup Python 3.11
install project + test dependencies
pytest -q
```

允许使用：

```text
uv sync --dev
```

或等价、可复现的安装方式。

CI unit/regression suite **不得依赖**：

```text
E:\ 本地路径
本地 OpenUtau GUI
Yousa voicebank
人工下载但未缓存/未声明的模型
交互式 UI
开发者机器已有环境状态
```

真正依赖本地 OpenUtau / voicebank / 大模型资源的测试应明确分为 integration/local acceptance，不得让基础 CI 假装覆盖它们。

## 4.3 Remote CI hard acceptance

从 C2 开始，任何 milestone / stage 想标记：

```text
✅ FROZEN
PASS
accepted
```

必须同时满足：

```text
1. local regression suite green
2. GitHub remote workflow run exists
3. remote required test job conclusion == success
4. workflow 对应当前被验收 commit/HEAD，而不是旧 commit
5. 没有 skipped core regression 来伪造 green
```

以下情况一律不得 freeze：

```text
CI missing
CI pending
CI cancelled
CI failure
CI only ran docs/lint but没有跑 core pytest
remote run 对应旧 SHA
```

以后 review 不再只看 classic `combined status`；应验证实际 GitHub Actions workflow/check run 是否存在且成功。

## 4.4 Backfill frozen stages

E1 CI 建立后，必须至少覆盖：

```text
A-stage regressions
B1/B2/B3 regressions
189s no-false-repair regression
202s no-false-repair regression
C tests
```

若 frozen A/B regression 在 remote CI 中失败：

```text
对应 frozen contract 自动 reopen
```

不得用“本地之前通过过”覆盖 remote failure。

## 4.5 Branch protection（推荐）

如果仓库权限允许，推荐把 CI job 设为 main merge 的 required check。

这不是 C2 算法 correctness 的必要条件，但能防止以后 agent 直接把 failing commit 推进 main。

---

# 5. Orthogonal state / lifecycle contract

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
  invalidated
  unresolved

structure_adjudication_status:
  not_needed
  pending
  resolved_keep
  resolved_change_candidate
  unresolved
```

强制：

- evidence state 与 workflow decision 分离；
- pitch / structure needs 可共存；
- provisional result 不得 repair；
- `needs_phrase_review` 只能在 machine-computable lanes 真正结束后产生；
- Candidate 0 永不被 adjudication 原地覆盖。

---

# 6. Evidence independence / audit contract

逻辑独立 group：

```text
GAME stochastic
RMVPE
FCPE
waveform mechanism group
musical context（soft）
```

相关 waveform：

```text
pYIN
ACF
harmonic
subharmonic
```

必须先 within-group fusion。

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

只用于解释 / audit。

`opposing_independence_groups` 当前实现仍部分消费 raw opposition，**audit-only**，不得作为新的 gate truth。

---

# 7. Cache / provenance contract

至少覆盖：

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

---

# 8. M2.3.2C2 — Structure Correctness / Lifecycle Calibration ← 当前算法最高优先级

C1 架构可保留，但**不得基于 C1 的 47 split candidates 开始 structure repair**。

C2 目标：

```text
降低 over-split 风险
补齐 C → new note identities → frozen B 的闭环
让 final structure resolution 真正成为后续 gate truth
```

## 8.1 P0：resolved_change_candidate 必须重建 candidate notes 并 rerun frozen B

C1 当前行为错误：

```text
C resolved_change_candidate
→ invalidate old B
→ phrase_review
```

这跳过了机器仍可完成的 pitch adjudication。

C2 强制改为：

```text
C proposes split / merge / material boundary change
→ old B = invalidated
→ 创建 VIRTUAL candidate note identities/spans
→ 对每颗新 note 重新生成 per-note evidence packet
→ 在新 note spans 上运行 frozen B
→ 保存 new-note pitch adjudication results
→ 只有 frozen B/C 之后仍 unresolved 才允许 phrase review
```

这里的 virtual notes：

```text
只存在 candidate artifact / audit packet
不得直接写回 Candidate 0
```

可复用已计算的 full-track RMVPE / FCPE / third-F0 contours，但**必须按新 span 重新切 per-note evidence**；旧 note 的：

```text
winner
confidence
margin
group_scores
safe gate
```

全部不得复用。

### Split

```text
1 old note
→ virtual A + virtual B
→ B(A)
→ B(B)
```

### Merge

```text
old note_i + note_j
→ virtual merged note
→ regenerate evidence over merged span
→ B(merged)
```

### Boundary shift

只要 pitch evidence extraction window material change：

```text
invalidate old B
→ rerun B
```

## 8.2 C resolved_keep：什么时候 finalize，什么时候 rerun

如果：

```text
note count unchanged
start/end unchanged
pitch evidence span unchanged
```

则 C `resolved_keep` 可以：

```text
finalize existing provisional B
```

不要求无意义地重复计算。

如果 C 虽归类为 keep，但实际修改了用于 pitch evidence 的：

```text
boundary
span
identity mapping
```

则不能简单 finalize，必须 invalidate + rerun B。

必须有 regression 明确覆盖两种情况。

## 8.3 P0：两个 plateau ≠ 两颗 written notes

C1 当前 H1 过宽：

```text
len(RMVPE plateaus) >= 2 → RMVPE split support = 1
len(FCPE plateaus) >= 2 → FCPE split support = 1
```

这是不允许的。

C2 中每个 extractor 的 structure evidence 至少要描述：

```text
pre_plateau_center
post_plateau_center
pitch_delta_st
boundary_time
plateau duration/stability
```

双 extractor 还要计算：

```text
boundary_time_delta_ms
pitch_delta_direction_agreement
pitch_delta_magnitude_difference
```

Split support 必须考虑：

```text
实际 pitch delta 是否 meaningful
两个 extractor 对 delta 方向是否一致
两个 extractor 对 delta magnitude 是否兼容
candidate boundary 是否时间一致
pre/post plateaus 是否足够稳定且持续足够长
```

禁止：

```text
“两个 extractor 都被 plateau detector 切成两段”
==
“两个 extractor 都给 H1 满票”
```

建议把初始 `MIN_STRUCTURE_DELTA_ST` 参数化并通过 synthetic + real distribution calibration，不要把阈值散落成 magic number。

结构 delta 应尽量 octave-offset invariant，例如：

```text
RMVPE: +3.0 st
FCPE:  +3.1 st
```

即使两 extractor 整体相差一个 octave，仍属于 strong relative structure agreement。

## 8.4 P0：H1 split vs H3 portamento/ornament 必须真正竞争

两个 extractor 同时看到 changepoint，只能说明：

```text
pitch movement 是真实声学现象
```

不能直接证明：

```text
written score 必须有 note boundary
```

C2 对 `TRUE_SPLIT_CANDIDATE` 至少要求以下二者之一：

```text
A. strong GAME split/boundary support
   + acoustic/F0 confirmation

或

B. dual-F0 relative-delta agreement
   + 至少一个独立 non-F0 boundary family
```

non-F0 boundary family 可包括：

```text
onset / spectral-flux / re-attack
voiced→unvoiced→voiced or voiced-probability drop
boundary-local energy envelope minimum + recovery
lyric/syllable articulation boundary（若可用）
```

单纯：

```text
F0 changepoint agreement
```

不得独自把 H1 判为 resolved change。

Portamento/ornament hypothesis 必须在 dual-F0 changepoint agree 时仍可参与竞争。

## 8.5 P1：energy discovery 改为 boundary-local，不用 whole-note min/mean

C1：

```text
min(note_energy) < 0.55 * mean(note_energy)
```

过宽，正常人声动态也容易触发。

C2 改为围绕 candidate boundary 的局部特征，例如：

```text
local minimum prominence
pre/post energy recovery
energy derivative
onset strength / spectral flux
voiced probability dip
```

如果根本没有 candidate boundary，不应仅因 note 内任意一点能量较低就产生 strong split evidence。

Discovery 可以宽，但 adjudication 必须严格；同时记录：

```text
all-baseline discovery rate
entry reason distribution
false-positive-oriented calibration stats
```

C1 的：

```text
315 / 421 notes entered discovery
```

说明 discovery 很宽，C2 必须量化并收敛，而不是默认这是正常值。

## 8.6 P1：GAME merge evidence 不得把 run_note_counts == 0 当 merge support

Consensus `run_note_counts == 0` 的语义是：

```text
该 consensus component 在该 run 中没有成员
```

它可能代表 gap / alignment miss / event absence，**不等于 merge**。

因此禁止：

```text
count == 0
→ GAME supports merge
```

真正 merge support 应来自显式结构关系，例如：

```text
pairwise alignment 的 merge op
某 run 中一颗真实 GAME note 跨越 candidate i+j 的 combined span
per-run boundary distribution 明确缺少中间 boundary
```

必要时扩展 consensus/audit artifact，保存：

```text
per-run member note spans
per-run internal boundaries
explicit split/merge correspondence
```

而不是从 `run_note_counts` 猜语义。

## 8.7 P1：final structure resolution 必须覆盖 raw structure_varies 的 gate 阻塞

Raw：

```text
consensus.structure_varies
```

是 evidence，不是永久真值。

如果 C 高置信得到：

```text
structure_adjudication_status = resolved_keep
```

后续 repair gate 不得仍因历史 raw：

```text
structure_varies = true
```

永久失败。

需要显式 final semantics，例如：

```text
final_structure_clear = C resolved_keep
```

然后 SAFE/final repair gate 消费：

```text
finalized structure result
```

raw `structure_varies` 继续留在 audit 中。

这不要求重开 frozen B scorer；可以在 C/M2.4 的 final gate interface 中解决。

## 8.8 47 split candidates = calibration set，不直接人工逐个听

先生成统计：

```text
entry source: existing lane vs independent discovery
GAME one/split support ratio
RMVPE pre/post delta
FCPE pre/post delta
delta direction/magnitude agreement
boundary time delta
non-F0 boundary support
H1/H3 scores
winner margin
note duration
```

目标是先判断：

```text
47 中有多少是强 split
多少是 portamento/ornament
多少只是 plateau segmentation artifact
多少应 unresolved
```

不要把 47 个全部直接推给人工。

---

# 9. M2.3.2C2 Acceptance / Regression Matrix

C2 必须同时满足 E1 remote CI gate。

## 9.1 Lifecycle

```text
1. C resolved_change_candidate 会创建 virtual candidate note identities
2. old B 被 invalidated
3. 新 note span 重新生成 pitch evidence
4. frozen B 在每颗 virtual note 上重新执行
5. old winner/confidence/margin/group_scores 不复用
6. machine-computable new-note B 未结束前不得 phrase_review
7. C resolved_keep + unchanged span 可 finalize provisional B
8. C material span change 即使 note count 不变也必须 rerun B
```

## 9.2 Split correctness

```text
9. two plateaus alone 不等于 full split support
10. cross-extractor pitch-delta direction/magnitude agreement 被显式计算
11. boundary-time agreement 被显式计算
12. small/inconsistent delta regression 不得误判 TRUE_SPLIT
13. true stable two-note synthetic regression 能判 TRUE_SPLIT
14. large portamento with dual-F0 agreement 仍允许 H3 赢
15. F0-only changepoint、无独立 boundary evidence 时不得高置信 auto split
```

## 9.3 Boundary evidence

```text
16. energy 使用 candidate-boundary-local evidence
17. ordinary within-note dynamics 不应大量触发 strong split
18. onset/re-attack 或 voiced-gap evidence 可独立增强 boundary
19. discovery rate / reason distribution 被记录
```

## 9.4 Merge

```text
20. run_note_counts==0 不再作为 merge support
21. merge support 来自 explicit span/boundary correspondence
22. true merge synthetic regression PASS
23. gap/event-absence regression 不得误判 merge
```

## 9.5 Final gate semantics

```text
24. C resolved_keep 后 raw structure_varies 不得永久阻塞 final repair gate
25. raw structure evidence 仍保留 audit
26. Candidate 0 unchanged
27. 189s NO FALSE REPAIR
28. 202s NO FALSE REPAIR
29. frozen B regressions 全部 green
```

## 9.6 Remote CI

```text
30. .github/workflows/ci.yml exists
31. current C2 acceptance SHA 有 remote workflow run
32. core pytest job success
33. A/B/C regression suite 在 remote CI 中 green
34. 不得只凭 local “N tests passed” 标记 C frozen
```

只有 1–34 满足后：

```text
M2.3.2C = FROZEN
```

---

# 10. M2.3.2D — Phrase-Level Human Review

人工只处理 finalized B/C 后仍 unresolved 的音乐语义。

可达条件：

```text
pitch machine lane not pending/provisional/invalidated-waiting-rerun
structure lane not pending
AND
至少一条 finalized lane == unresolved
```

才允许：

```text
needs_phrase_review
```

人工不猜 F0 / MIDI / Hz / cents / octave。

Review 单位：

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

Review 包：

```text
SOURCE_PHRASE_original_mix.wav
SOURCE_PHRASE_separated_vocal.wav
BASELINE_PHRASE.wav
CANDIDATE_A_PHRASE.wav
CANDIDATE_B_PHRASE.wav
CANDIDATE_C_PHRASE.wav optional
```

要求：

- 时间窗一致；
- singer / phonemizer / color / volume / PITD policy 一致；
- 除目标 region 外 score 一致；
- 一次只改变一个待判断因素。

人工只选：

```text
Baseline / A / B / C / 都差不多 / 都不对
```

---

# 11. M2.4 — SAFE Repair Engine

进入条件：

```text
A frozen contracts remote-regression green
B frozen contracts remote-regression green
C frozen + remote CI green
189s no false repair
202s no false repair
phrase review workflow available
Candidate 0 / rollback contract complete
```

第一版优先：

```text
single-note written-pitch retune
```

每个 repair 记录：

```text
region
before / after
B/C result
winning hypothesis
group_scores
supporting/opposing groups
confidence / margin
gates passed
rollback data
```

0 SAFE repairs 是合法结果。

禁止覆盖 Candidate 0。

---

# 12. Lyrics / USTX / PITD

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

# 13. Evaluation / Audit

至少记录：

```text
GAME run note counts
pairwise alignment costs
selected medoid + sensitivity
GAME per-event run tone distribution
per-run structure/boundary evidence
match/gap/split/merge counts
orthogonal states
routing needs / decision
pitch adjudication status / provisional / invalidated
structure adjudication status
RMVPE / FCPE / third-F0 evidence
plateau pre/post centers + relative deltas
changepoint timing agreement
onset / energy / voiced-gap boundary evidence
periodicity octave metrics
spectral octave metrics
group_scores
supporting_independence_groups
opposing_independence_groups (audit-only unless group-level opposition finalized)
winner / runner-up / margin
separation sensitivity
AUTO_RESOLVED / UNRESOLVED counts
independent structure discoveries
structure discovery rate + reason distribution
virtual candidate note B results
phrase-review count
regression status
local test result
remote CI workflow URL/run id/SHA/conclusion
cache/provenance manifest
```

Score artifacts：

```text
Candidate 0
virtual candidates
corrected score
retune count
split/merge/boundary-shift count
GAME preservation ratio
rollback coverage
```

---

# 14. Milestones

### M2.0 — Foundation survey ✅
### M2.1 / M2.1.1 — Initial diagnostic + correctness ✅
### M2.1.2 — GAME stochastic baseline ✅
### M2.2A — Formal sequence alignment ✅
### M2.2B — Dual-F0 ✅
### M2.3 — Residual-error triage ✅
### M2.3.1 — Triage calibration ✅
### M2.3.2A / A2 / A3 / A4 — Correctness + routing/provenance ✅ FROZEN (remote CI backfill required)
### M2.3.2B1 / B2 / B3 — Pitch/octave adjudication ✅ FROZEN (remote CI backfill required)
### M2.3.2C1 — Structure adjudication framework ✅ IMPLEMENTED / NOT FROZEN
### E1 — GitHub Actions remote CI ← 当前 P0 工程 gate
### M2.3.2C2 — Structure correctness/lifecycle calibration ← 当前算法 P0
### M2.3.2C — Freeze only after E1 + C2 acceptance
### M2.3.2D — Phrase-level human review
### M2.4 — SAFE repair
### M2.5 — PROBABLE structure repair
### M2.6 — Optional second opinion
### M2.7 — Lyrics mapping + base USTX
### M2.8 — PITD + render loop
### M2.9 — 《年轮》M2 验收
### M3 — 泠鸢 style profile

> **原唱决定“唱什么”；泠鸢参考决定“怎么唱”。**

---

# 15. 最终原则

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
13. **C resolved_keep 仅在 identity/span 未变时可 finalize provisional B。**
14. **C 改变 note identity/time span 后必须 invalidate / regenerate / rerun B。**
15. **C resolved_change_candidate 不得直接跳过 new-note B 去人工。**
16. **两个 F0 extractors 都出现 two plateaus，不等于 written score 必须 split。**
17. **Split 必须比较 cross-extractor relative pitch delta + boundary evidence。**
18. **F0 changepoint agreement 证明声学 movement，不单独证明 written-note boundary。**
19. **Portamento/ornament 必须与 split hypothesis 真正竞争。**
20. **Energy boundary evidence 必须 boundary-local，不用 whole-note min/mean 代替。**
21. **run_note_counts==0 不得解释为 GAME merge support。**
22. **Raw structure_varies 是 evidence；final C resolution 才是后续 final gate semantics。**
23. **Octave ACF 必须处理倍周期歧义。**
24. **Harmonic score 必须避免低八度 harmonic-set 超集偏置。**
25. **相关 waveform features 必须先 group fusion。**
26. **supporting independence groups 必须从 finalized net group scores 推导。**
27. **raw feature support 不得绕过 group-level gate。**
28. **opposing_independence_groups 当前仅 audit-only。**
29. **Cache/provenance 必须真正参与 invalidation。**
30. **Third-F0 runtime version 必须参与 freshness check。**
31. **Repair gate 必须显式绑定 adjudicator winning hypothesis。**
32. **C 必须扫描全部 baseline，防止 GAME stable-but-wrong。**
33. **C 第一阶段只 adjudicate，不自动 structure repair。**
34. **B/C 使用 explicit pending/provisional/resolved/invalidated/unresolved lifecycle。**
35. **needs_phrase_review 只能在 machine-computable lanes 全结束后产生。**
36. **人工默认审核完整乐句，不审核 isolated note。**
37. **189s 永久作为 extractor-conflict regression。**
38. **202s 永久作为 stochastic pitch / identity-variable regression。**
39. **0 automatic repairs 是合法结果。**
40. **Candidate 0 永远可 rollback。**
41. **所有修改必须局部、可解释、可审计、可 A/B。**
42. **从 C2 起，没有 remote CI green，不允许任何 stage 标记 FROZEN/PASS。**
43. **Remote CI 必须对应被验收的当前 SHA，不能拿旧 run 充数。**
44. **A/B frozen regressions 必须在 CI 建立后 backfill；remote failure 会 reopen contract。**
45. **先把 written score 唱对，再生成 PITD。**
46. **先“唱对”，再做泠鸢风格。**
