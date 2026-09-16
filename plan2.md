# agent2utau — Plan 2：GAME 主转谱 + 自动证据裁决 + Phrase-Level 审核

> 修订日期：2026-09-16
>
> 核心原则：**先把“唱对”解决，再把“唱得像泠鸢”解决。**
>
> 当前工程原则：**GAME 提供真实可渲染的 score candidate；multi-run consensus 只作为 uncertainty / evidence graph。能由程序测量的 pitch / octave 不交给人工猜；structure 先自动 adjudicate；只有 B/C 仍无法唯一解释的音乐语义才进入完整乐句人工审核。**

---

# 1. 最终目标流程

```text
原曲
→ decode / separation
→ GAME 多次同配置转谱
→ formal sequence alignment
→ 选择真实 GAME medoid run 作为 Candidate 0
→ multi-run uncertainty graph
→ RMVPE + FCPE + third-F0 + periodicity / harmonic evidence
→ orthogonal pitch / structure / identity / separation states
→ M2.3.2B pitch/octave adjudication
→ M2.3.2C structure adjudication
→ B/C unresolved 才进入 M2.3.2D phrase-level A/B/C review
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

Multi-run 的用途是 uncertainty evidence：

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

202s 案例证明 GAME 本身可能在同一区域给出约 MIDI 65 / 72 两套 stochastic 解，因此 medoid selection 和 pitch truth 必须分离。

## 2.5 Dual-F0 必要，但不能简单投票

189s 附近出现：

```text
RMVPE ≈ 高八度候选
FCPE  ≈ 低八度候选
GAME  ≈ 其中一个候选
```

固定原则：

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

只有 automatic structure adjudication 后仍存在多个合理 musical interpretations，才交给 phrase-level human review。

---

# 4. 当前工程状态

## M2.3 / M2.3.1 ✅

已完成：

- real GAME medoid Candidate 0；
- stochastic consensus；
- RMVPE + FCPE dual-F0；
- structural F0；
- plateau / interior re-triage；
- SAFE gate 初版；
- regression packets。

旧 40 组 isolated short clips 仅保留 debug/demo，不再是正式人工审核入口。

## M2.3.2A / A2 / A3 / A4 ✅ FROZEN

A-stage 已完成并冻结，不再新增 A5。

主要成果：

- structure ambiguity 优先于 pitch-hard；
- plateau frame-inclusive geometry 一致；
- RMVPE + FCPE unique target plateau + temporal overlap SAFE gate；
- actual sample rate；
- separation comb 只作为 uncertainty flag；
- raw flags 只作 features，不覆盖 calibrated result；
- structure evidence 与 legacy triage 解耦；
- SAFE eligible 只到 `candidate_pending_adjudication`，不直接 repair；
- pitch / structure / identity / separation 正交状态；
- pitch / structure adjudication 分 lane；
- structure candidate 不再直接进入人工；
- separator cache/provenance 绑定 `separate()` 实际解析出的 model path / bytes hash / config hash。

A4 commit：`7587c221...`

最新《年轮》rerun：

```text
medoid = run 4
baseline = 421 notes

顶层 decision：
338 keep_baseline
76  needs_pitch_adjudication
7   needs_structure_adjudication

routing_needs：
pitch     = 76
structure = 51
both      = 44
phrase_review = 0 at A-stage
repair_candidate = 0
```

解释：

- `decision` 只是下一步优先动作；
- 44 个 region 同时需要 pitch + structure adjudication；
- 所以顶层 76 pitch + 7 structure 与总计 51 structure needs 不矛盾；
- 421 notes 顶层路由闭合：`338 + 76 + 7 = 421`。

Regression：

```text
189.84s
pitch_state      = extractor_conflict
structure_state  = candidate
separation_state = sensitive
→ multi-axis adjudication

202.51s
GAME tone answer stochastic / identity variable
→ needs_pitch_adjudication
→ no direct retune

202.09s
legacy enum stale，但 calibrated pitch stable
→ keep_baseline
```

本地报告 64 tests passed；当前 GitHub 没有 remote combined CI status，因此不能把本地测试表述为远端 CI 已验证。

---

# 5. Orthogonal state / routing contract

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
- `needs_phrase_review` 必须是 B/C adjudication 后 unresolved 的结果；
- `repair_candidate` 必须是 adjudication 后状态。

---

# 6. Evidence independence

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

仍属于同一个 RMVPE family。

GAME 5 runs 也是同一模型 stochastic samples，不是 5 个独立模型。

Confidence 必须按 family agreement / conflict / reliability 计算。

---

# 7. GAME stochastic evidence 必须保留连续置信度

A4 中：

```text
identity_state = variable if tone_agreement < 1.0
```

这个 binary state 只用于“是否值得送进 B 检查”，不能在 B 内把所有 variable 当成同等强度的反证。

`tone_agreement` 当前表示：各 GAME run 的 aggregate tone 与 event median 相差 `< 0.5 semitone` 的比例。

B 必须保留并使用连续信息，例如：

```text
GAME support ratio
per-run tone distribution
tone_min / tone_max / spread
presence_rate
run count
structure relation
```

解释建议：

```text
5/5 agreement → very strong GAME support
4/5           → strong support
3/5           → ambiguous / moderate
2/5 or lower  → weak support
```

这些不是硬编码 truth label，而是 evidence strength。

禁止：

```text
tone_agreement == 1 → true
tone_agreement < 1  → equally unreliable
```

尤其 202s：GAME 65/72 两套答案应保留完整 run distribution，而不是只记录 `identity_state=variable`。

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

# 9. M2.3.2B — Automatic Pitch / Octave Adjudication ← 当前最高优先级

A-stage 已冻结，正式进入 B。

当前输入：

```text
76 pitch-adjudication lanes
其中 44 个同时有 structure need
```

## 9.1 Third-F0

第一版只接一个足够独立、稳定、可复现的 estimator。

优先：

```text
pYIN / YIN
或 WORLD Harvest
```

CREPE 可作为额外 neural opinion，但不能因为“模型更多”就自动增加 confidence。

Third-F0 必须记录：

```text
implementation/version
config
frame period
voicing/confidence
cache provenance
```

## 9.2 Pitch hypothesis，不做简单多数投票

对于 octave conflict：

```text
f vs 2f
```

至少结合：

```text
RMVPE family
FCPE family
third-F0 family
periodicity / autocorrelation
subharmonic support
weighted harmonic-series fit
GAME per-run pitch distribution
local melodic context
separation sensitivity
```

简单 mix/separated spectral comb 仍只能作为 sensitivity flag，不能直接决定 truth。

## 9.3 Per-hypothesis evidence score

B 应显式生成候选 hypothesis，而不是“哪个 extractor 数量多就选哪个”。

例如：

```text
H0 = Candidate 0 / GAME current written pitch
H1 = lower-octave F0 hypothesis
H2 = upper-octave F0 hypothesis
H3 = optional local alternative
```

每个 hypothesis 记录：

```text
GAME support ratio / run distribution
RMVPE support + reliability
FCPE support + reliability
third-F0 support + reliability
periodicity score
subharmonic evidence
harmonic-series evidence
local continuity / leap plausibility
separation sensitivity penalty
structure status
```

输出必须包含：

```text
winning_hypothesis
score / confidence
margin_to_second
supporting evidence families
opposing evidence families
reason
```

## 9.4 GAME evidence 不得二值化

B 内禁止仅使用：

```text
identity_state = stable / variable
```

必须消费第 7 节连续 stochastic evidence。

例如 GAME 4/5 支持 H0、1/5 支持 H1，与 3/5 vs 2/5 必须有不同置信度。

## 9.5 自动解决条件

自动 resolution 至少要求：

```text
多个独立 evidence families 支持同一 hypothesis
winner 对 runner-up 有足够 margin
periodicity/harmonic/subharmonic 没有强反证
GAME stochastic support 被连续地计入，而非二值化
separation-sensitive 无未解释强冲突
若同时存在 structure need，不允许假装 structure 已经解决
```

注意：

```text
pitch 可 resolved
structure 仍 pending
```

是合法状态。

不得因为 pitch solved 就清掉该 region 的 structure need。

## 9.6 B adjudication result state

不要只留一个 `b_c_unresolved` bool。

至少增加：

```text
pitch_adjudication_status:
  not_needed
  pending
  resolved_keep
  resolved_change
  unresolved
```

必要字段：

```text
pitch_adjudication:
  status
  winning_hypothesis
  confidence
  margin
  evidence_families
  reason
```

Routing：

```text
resolved_keep
→ clear pitch_adjudication need

resolved_change
→ candidate_pending_repair / repair_candidate only after repair gates

unresolved
→ clear repeated B loop
→ mark phrase_review eligibility
```

但如果 structure 仍 pending，应先完成 C，再决定是否真的进入 D。

## 9.7 B 输出分类

可保留 reporting class：

```text
AUTO_PITCH_KEEP
AUTO_PITCH_CHANGE
AUTO_OCTAVE_KEEP
AUTO_OCTAVE_CHANGE
F0_UNRESOLVED
SEPARATION_SENSITIVE
```

这些是 adjudication result，不替代正交 states。

## 9.8 B regression / acceptance

必须覆盖：

```text
1. 189s octave extractor conflict 不被简单 majority vote 误修
2. 202s GAME stochastic pitch distribution 被完整消费
3. 5/5、4/5、3/5 GAME support 对 confidence 影响不同
4. separation-sensitive 只能降低 confidence / 保留 unresolved
5. third-F0 failure/low-confidence 不等于反对某 hypothesis
6. pitch resolved 后不会清掉 concurrent structure need
7. B unresolved 不会无限重新路由回 B
8. no B result directly overwrites Candidate 0
```

B 完成标准：

```text
76 pitch lanes 全部得到 resolved_keep / resolved_change / unresolved
189s regression pass
202s regression pass
所有 decision 可审计
```

---

# 10. M2.3.2C — Automatic Structure Adjudication

当前已知输入：

```text
51 existing structure routing needs
```

但 C **不能只处理这 51 个**。

## 10.1 Existing structure candidates

对 A-stage 已发现的：

```text
structure_varies
split / merge disagreement
```

使用：

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

## 10.2 Independent structure discovery：防止 GAME “稳定地错”

这是 C 的强制要求。

当前 A-stage structure lane 主要由：

```text
consensus.structure_varies == true
```

触发。

但存在盲区：

```text
GAME 5/5 都稳定地产生 1 note
↓
RMVPE 显示两个稳定 plateau
FCPE 也显示两个稳定 plateau
onset / energy / articulation 支持中间 boundary
↓
GAME stable-but-structure-wrong
```

因此 C 必须额外扫描**所有 Candidate 0 baseline notes**，寻找 independent structure evidence。

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

如果独立证据足够强：

```text
structure_state = candidate
routing_needs.structure_adjudication = true
```

即使：

```text
GAME structure_varies = false
```

也必须进入 C。

反向同理：GAME 多 run 偶发 split，但 dual-F0 / onset / articulation 都不支持，可以 adjudicate 为 ONE_NOTE_WITH_PORTAMENTO / GAME stochastic artifact。

## 10.3 C hypothesis scoring

对一个 region 生成真实可解释候选：

```text
H0 = current GAME structure
H1 = split candidate
H2 = merge candidate
H3 = one-note-with-portamento / ornament
```

候选应尽量来自真实 GAME run structure 或由明确 boundary evidence 构造，不允许从 consensus median 拼 synthetic whole-score。

每个 hypothesis 记录：

```text
GAME run structure support
RMVPE changepoint support
FCPE changepoint support
third-F0 support if available
onset / energy support
lyric articulation support
local duration plausibility
melodic continuity
```

自动决定必须有足够 score margin；否则 unresolved。

## 10.4 C adjudication result state

至少增加：

```text
structure_adjudication_status:
  not_needed
  pending
  resolved_keep
  resolved_change_candidate
  unresolved
```

`resolved_change_candidate` 第一阶段只表示：机器高置信认为结构应变，不等于立即自动改谱。

结构 repair 仍需之后单独做 precision calibration。

## 10.5 C → D routing

C 必须显式终止自己的 pending 状态。

禁止：

```text
UNRESOLVED_STRUCTURE
→ b_c_unresolved = true
但 structure_adjudication 仍为 pending
→ routing 又回 C
```

正确逻辑：

```text
C unresolved
→ structure_adjudication_status = unresolved
→ clear structure_adjudication pending need
→ phrase_review eligible = true
```

如果 pitch B 尚 pending：

```text
先完成 B
```

只有所有机器 adjudication lane 都不再 pending、且至少一个为 unresolved，才进入 D。

## 10.6 C regression / acceptance

至少覆盖：

```text
1. existing structure_varies candidates 全部有 C result
2. GAME-stable + dual-F0 two-plateau case 能被 independent discovery 找到
3. GAME stable-but-wrong synthetic regression
4. GAME stochastic split + acoustic evidence single-note 可 resolved_keep
5. pitch+structure concurrent region 两条 lane 独立结束
6. C unresolved 不会无限重新路由回 C
7. unresolved 才能进入 phrase review eligibility
8. no structure adjudication directly overwrites Candidate 0
```

---

# 11. M2.3.2D — Phrase-Level Human Review

人工只处理 B/C 之后仍 unresolved 的音乐语义。

## 11.1 D 的可达条件

必须同时满足：

```text
pitch_adjudication_status != pending
structure_adjudication_status != pending
AND
至少一条 lane == unresolved
```

才允许：

```text
routing_needs.phrase_review = true
→ decision = needs_phrase_review
```

这样 D 不会被 B/C priority 永久遮蔽。

## 11.2 人工不做什么

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

## 11.3 Review 单位

默认完整乐句：

```text
最低约 3s
常规 5–8s
最长约 12s
```

优先：

```text
LRC line / phrase
+ vocal silence / breath gap
+ GAME phrase context
```

至少尽量包含目标前后各 2–3 notes。

## 11.4 Review 包

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
A-stage frozen
B pitch/octave adjudicator available
C structure adjudication available
189s regression no false repair
202s identity-variable case no direct retune
phrase review workflow available
Candidate 0 / rollback contract complete
```

第一版优先只做：

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
confidence / margin
gates passed
phrase A/B（若需要）
rollback data
```

禁止覆盖 Candidate 0。

Structure repair 默认仍为 PROBABLE / AMBIGUOUS；只有 precision calibration 证明足够高才逐类升级。

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
GAME per-event support ratio / tone distribution
match/gap/split/merge counts
consensus stability
pitch_state / structure_state / identity_state / separation_state
routing_needs / decision
pitch_adjudication status/result
structure_adjudication status/result
RMVPE / FCPE / third-F0 evidence families
periodicity/harmonic/subharmonic evidence
plateau center + temporal overlap
separation sensitivity
AUTO_RESOLVED / UNRESOLVED counts
independent structure discoveries
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
### M2.3.2A4 — Routing/provenance finalization ✅ FROZEN

最新 baseline：421 notes；338 keep；76 pitch lanes；51 structure needs；44 both；A-stage 0 phrase-review / 0 direct repair。

### M2.3.2B — Automatic pitch/octave adjudication ← 当前最高优先级

Third-F0 + periodicity + harmonic/subharmonic + GAME continuous stochastic support + per-hypothesis evidence score。

### M2.3.2C — Automatic structure adjudication

处理 existing structure candidates，并对所有 baseline notes 做 independent structure discovery，避免 GAME stable-but-wrong 盲区。

### M2.3.2D — Phrase-level human review

只有 B/C lane 已结束且至少一条 unresolved 才进入。正式生成 3–12s（常规 5–8s）的 source / baseline / A/B/C phrase 包；short clip 仅 zoom/debug。

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
10. **GAME stochastic support 必须保留连续置信度，不能只二值 stable/variable。**
11. **Pitch-hard 前必须先排除 structure / identity ambiguity。**
12. **SAFE dual-F0 必须有独立且时间一致的 RMVPE + FCPE plateau 支持。**
13. **Octave conflict 必须看 periodicity / harmonic / subharmonic，不做简单多数投票。**
14. **Separation artifact 只作为 uncertainty，不直接当真值。**
15. **Cache/provenance 必须绑定实际音频内容与实际模型 bytes/config。**
16. **Pitch / structure / identity / separation 使用正交状态。**
17. **Pitch adjudication 与 structure adjudication 必须分 lane，且可共存。**
18. **Structure candidate 必须先 automatic adjudication，不能直接扔给人工。**
19. **C 必须做 independent structure discovery，不能只依赖 GAME 自己出现 structure variance。**
20. **B/C 必须有 explicit pending/resolved/unresolved lifecycle，避免 unresolved 无限回流。**
21. **needs_phrase_review 只能在所有机器 adjudication lane 不再 pending 后产生。**
22. **人工默认审核完整乐句，不审核 isolated note。**
23. **Phrase A/B/C 除目标局部外必须完全一致。**
24. **Zoom clip 只是辅助。**
25. **189s 永久作为 extractor-conflict regression。**
26. **202s 永久作为 stochastic pitch / identity-variable regression。**
27. **candidate / auto-resolved / unresolved / confirmed repair 分层统计。**
28. **0 automatic repairs 是合法结果。**
29. **Candidate 0 永远可 rollback。**
30. **所有修改必须局部、可解释、可审计、可 A/B。**
31. **先把 written score 唱对，再生成 PITD。**
32. **先“唱对”，再做泠鸢风格。**
