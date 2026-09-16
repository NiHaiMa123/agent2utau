# agent2utau — Plan 2：GAME 主转谱 + 自动证据裁决 + Phrase-Level 审核

> 修订日期：2026-09-16
>
> 核心原则：**先把“唱对”解决，再把“唱得像泠鸢”解决。**
>
> 当前工程原则：**GAME 提供真实可渲染的 score candidate；multi-run consensus 只作为 uncertainty / evidence graph。可程序测量的 pitch / octave 不交给人工猜；structure 先自动 adjudicate；只有机器仍无法唯一解释的音乐语义才进入完整乐句人工审核。**

---

# 1. 最终目标流程

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

- GAME raw 是主 melody transcription 来源；
- lyric char start 不是天然 note boundary；
- RMVPE / FCPE / third-F0 都是 evidence，不从零重建全曲谱面；
- correction 只修 residual errors。

forced-char-boundary 实验曾把约 419 notes 扩张到约 760 notes，并制造大量假 suspicious，不能回到该方案。

## 2.2 GAME 有真实 stochasticity

《年轮》同输入、同配置，多次 GAME raw 约 418–425 voiced notes/run。

```text
single GAME run != deterministic truth
```

Multi-run 的用途：

```text
一致 → 增强置信
分歧 → 暴露局部 uncertainty
```

GAME 5 runs 是同一模型 stochastic samples，不是 5 个独立模型。

## 2.3 Consensus 不是最终谱面

Formal sequence alignment 支持：

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

Consensus component 只表示 correspondence + uncertainty。禁止用 `start_median / duration_median / tone_median` 拼 synthetic final score。

## 2.4 Candidate 0 必须来自真实 GAME run

Candidate 0 = pairwise alignment cost 最小的真实 GAME medoid run。

Medoid 只是 baseline，不是 ground truth。

202s 已证明 GAME 自己可在同一区域产生约 MIDI 65 / 72 两套 stochastic 解，所以：

```text
medoid selection != pitch truth
```

## 2.5 Dual-F0 / octave conflict

189s：

```text
RMVPE ≈ 高八度候选
FCPE  ≈ 低八度候选
GAME  ≈ 其中一个候选
```

固定原则：

> **单一 F0 extractor 永远不能独自推翻 GAME。**

189s 永久作为 extractor-conflict regression。

---

# 3. F0 measurement 与 score interpretation 分离

## 3.1 F0 measurement

程序回答：

```text
这一帧 / 稳定区间的 fundamental frequency 是多少？
```

Evidence：

```text
RMVPE
FCPE
third-F0
waveform periodicity
spectral / harmonic / subharmonic evidence
```

人工不负责猜 MIDI / Hz / cents / octave。

## 3.2 Score interpretation

系统回答：

```text
应记成一颗 note、两颗 note、slide、grace 还是 ornament？
```

Evidence：

```text
GAME multi-run structure
+ cross-F0 plateau / changepoint
+ onset / energy
+ voiced transition
+ lyric articulation
+ duration plausibility
+ local melodic context
```

只有 automatic structure adjudication 后仍有多个合理 musical interpretations，才进入 phrase-level human review。

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

旧 isolated short clips 仅保留 debug/demo。

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

## M2.3.2B1 — Automatic pitch/octave adjudication ✅ IMPLEMENTED / NOT FROZEN

commit `21be525c...`

已实现：

- third F0 = `librosa.pyin`；
- GAME `run_tones` 连续分布进入 hypothesis scoring；
- RMVPE / FCPE reliability-weighted centers；
- pYIN evidence；
- FFT-ACF periodicity；
- subharmonic / harmonic-series evidence；
- local continuity；
- separation sensitivity 只降 confidence，不直接决定 winner；
- `resolved_keep / resolved_change / unresolved` lifecycle；
- Candidate 0 不被 B 覆盖。

最新《年轮》B1 rerun：

```text
87 pitch lanes
72 resolved_keep
0  resolved_change
15 unresolved
0  automatic repair

最终 decision：
323 keep_baseline
69  needs_structure_adjudication
23  auto_resolved
8   needs_phrase_review
```

关键 regression：

```text
189.84s
winner 倾向低八度，但 RMVPE opposition + separation sensitivity 存在
→ unresolved
→ NO REPAIR

202.52s
winner 倾向当前高音，但 periodicity 有 counter-evidence
→ unresolved
→ NO REPAIR
```

本地报告 74 tests passed。当前 GitHub 无 remote combined CI status，不能把它表述成远端 CI 已验证。

B1 的整体架构正确，但 review 发现 octave evidence 与 pitch/structure ordering 仍有 correctness 风险，因此 B 暂不冻结。

---

# 5. Orthogonal state / adjudication lifecycle

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

Workflow state 至少包括：

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

核心要求：

- evidence state 与 workflow decision 分离；
- pitch / structure need 可共存；
- `needs_phrase_review` 只能在所有机器 adjudication lane 不再 pending 后产生；
- `repair_candidate` 只能基于 finalized adjudication，不得来自 provisional result。

---

# 6. Evidence independence / correlation groups

禁止按 feature 数量简单投票。

Evidence source：

```text
GAME stochastic family
RMVPE family
FCPE family
third-F0 family
waveform periodicity family
spectral octave family
musical-context family
```

但“不同字段”不等于“独立证据”。

例如：

```text
RMVPE raw center + RMVPE plateau
→ 同一个 RMVPE family

pYIN + simple ACF
→ 都依赖 periodicity，failure mode 明显相关
→ 不能仅凭二者凑够两个完全独立 hard families
```

B2 必须显式引入：

```text
independence_group / correlation_group
```

建议：

```text
GAME stochastic
neural-F0      : RMVPE / FCPE 各自保留独立 tracker family
periodic-time  : pYIN / YIN / ACF（相关，不得机械重复计票）
spectral-octave
musical-context
```

高风险 octave change 应优先要求**跨机制**收敛，而不是同一周期机制内部重复确认。

---

# 7. GAME stochastic evidence 保留连续置信度

B 内必须消费：

```text
per-run tone distribution
support ratio
tone spread
presence_rate
run count
structure relation
```

不能把：

```text
5/5
4/5
3/5
2/5
```

全部压成 `stable / variable`。

但当 structure 尚未确定时，`run_tones` 可能来自一个 run 内多个 notes 的 aggregate median，因此不得把它当最终 pitch truth。该问题由 B2 §9.1 处理。

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
third-F0 input-vocal hash
third-F0 implementation/version/config
third-F0 analysis schema
pitch adjudicator schema/config
structure adjudicator schema/config
```

规则：

```text
input / model / implementation / config / schema changed
→ invalidate affected dependent artifact
```

“记录 provenance”不等于“真正用于 cache invalidation”。

---

# 9. M2.3.2B2 — Pitch Adjudication Correctness / Calibration ← 当前最高优先级

B1 不回滚，保留现有框架；B2 修 correctness 风险后再冻结 B。

## 9.1 P0：Pitch + Structure 共存时，Structure identity 必须先确定

A4/B1 中存在大量：

```text
pitch_adjudication = true
structure_adjudication = true
```

当前 consensus event 的 `run_tones` 对一个 run 内多个 member notes 取 aggregate median。

例如某 run 真实结构：

```text
60 → 64
```

如果属于同一 split/merge component，aggregate tone 可能成为：

```text
median(60,64) = 62
```

这个 62 并不是该 run 实际存在的 written note，却可能被 B 加入 hypothesis。

更根本的问题：

```text
B 先回答“这一颗 note 是什么 pitch”
C 随后判断“这里其实应是两颗 notes”
```

此时原 B result 的 note identity 已失效。

### 强制 routing 规则

```text
pitch only
→ B

structure only
→ C

pitch + structure
→ C FIRST
→ 固定 / 解析 note identity
→ 对 C 输出的实际 note(s) 跑 B
```

如果工程上暂时必须保留 B-first：

```text
B result = provisional
```

且 C 发生 split / merge / boundary identity change 后：

```text
invalidate provisional B result
→ regenerate pitch packets
→ rerun B
```

**禁止把 structure-ambiguous event 上的 aggregate `run_tone` 当最终 written-pitch hypothesis。**

## 9.2 P0：Octave waveform evidence 必须去除低八度结构偏置

### ACF 问题

当前简单比较：

```text
ACF(T_hyp)
```

存在倍周期歧义：真实周期为 T 时，`ACF(2T)` 也可能很高。

所以：

```text
high ACF(candidate lag)
!= octave identity proof
```

B2 应使用更 octave-discriminative 的 time-domain evidence，例如：

```text
first strong periodic peak
R(T) vs R(2T)
peak prominence
neighbor-lag contrast
subharmonic / double-period penalty
```

### Harmonic-series 问题

对于 `f` vs `2f`：

```text
low candidate f : f,2f,3f,4f,...
high candidate 2f: 2f,4f,6f,...
```

简单累计 `k*f` spectral energy 时，低 octave 的 harmonic set 天然近似高 octave 的超集，会产生低八度偏置。

因此禁止把简单：

```text
sum energy around k*f
```

作为可直接比较的 octave winner score。

应改用能区分 octave identity 的方法，例如：

```text
matched-vs-unmatched harmonic contrast
odd/even harmonic pattern
fundamental / subharmonic presence
harmonic sieve / normalized harmonic likelihood
upper-candidate-exclusive consistency
spectral peak assignment with penalty for unexplained peaks
```

具体算法可迭代，但必须通过镜像 octave regression。

## 9.3 强制 waveform regression matrix

现有测试主要覆盖“真实低 octave”。B2 至少新增：

```text
1. true low octave
2. true high octave
3. weak fundamental + strong 2nd harmonic
4. missing-fundamental style synthetic signal
5. breathy/noisy vocal-like signal
6. vibrato around true F0
7. short-note / low-cycle-count case
8. silence / unvoiced / weak periodicity
```

关键对称测试：

```text
候选 58 vs 70
true = 58 → 能正确支持 58
true = 70 → 不能因 harmonic/ACF 结构偏置错误支持 58
```

任何明显单向 bias 都必须 blocking B freeze。

## 9.4 Third-F0 cache 必须拥有自己的 invalidation contract

B1 已保存：

```text
third_f0.npz
third_f0_provenance.json
```

但不能只依赖 separation cache 是否 fresh。

Third-F0 cache key 至少绑定：

```text
separated_vocal_sha256
implementation = librosa.pyin
librosa version
fmin / fmax
frame_length
hop_length
voicing config / thresholds
analysis schema version
```

任一变化：

```text
→ third_f0 cache stale
→ recompute pYIN
```

测试至少覆盖：

```text
librosa/config/schema change invalidates
vocal bytes change invalidates
same provenance can reuse
```

## 9.5 pYIN / ACF 相关性不得被当作完全独立硬票

B1 的 `MIN_FAMILIES >= 2` 不能让：

```text
pYIN support
+
ACF support
```

单独满足“两个独立 family”的安全语义。

建议 adjudication packet 同时输出：

```text
supporting_features
supporting_families
supporting_independence_groups
```

Octave change 的高置信自动 resolution 建议要求：

```text
至少跨 2 个 mechanism groups
且至少有 waveform/spectral 一类可区分 octave 的独立支持
```

Extractor conflict case 可更严格。

## 9.6 SAFE repair gate 必须显式绑定 B winning hypothesis

当前 `resolved_change` 后重新调用 SAFE gate，但 target 不能再隐式从 RMVPE 推导。

接口必须显式类似：

```text
safe_retune_gate(
    packet,
    ...,
    target_midi = pitch_adjudication.winning_hypothesis
)
```

然后验证：

```text
B winning hypothesis
RMVPE plateau support
FCPE plateau support
third-F0 / waveform evidence
```

指向的是同一目标。

禁止：

```text
B winner = A
SAFE gate 实际验证的是 RMVPE target B
→ 仍进入 repair
```

## 9.7 Separation-sensitive unresolved 不应直接提前进入人工

B unresolved 只表示：

```text
B 无法安全唯一决定 pitch
```

如果该 region 仍有 structure pending：

```text
先 C
```

只有：

```text
pitch status != pending/provisional
structure status != pending
AND
至少一条 status == unresolved
```

才进入 D。

所以 B 的 unresolved 可以先设置：

```text
phrase_review_eligible = true
```

但 `decision = needs_phrase_review` 必须等其他 machine lanes 结束。

## 9.8 B2 acceptance

B2 必须满足：

```text
1. pitch+structure concurrent region 不再用未解析结构做 final B decision
2. structure change 会 invalidate / rerun provisional pitch result
3. ACF octave evidence 有 double-period discrimination
4. spectral octave score 不存在明显低八度超集偏置
5. high-octave mirror regression pass
6. weak-fundamental / missing-fundamental regression 保守
7. pYIN + ACF 不可机械算两票独立 evidence
8. third-F0 cache 真正绑定其自身 version/config/schema/input bytes
9. repair gate target 显式等于 B winning hypothesis
10. 189s 保持 no false repair
11. 202s 保持 no false repair
12. Candidate 0 永不被 adjudication 原地覆盖
```

允许结果：

```text
resolved_keep 很多
resolved_change = 0
repair = 0
```

只要 evidence 仍不够，就保持 unresolved，不为了自动化率放松 gate。

B2 完成后：

```text
M2.3.2B = FROZEN
→ 正式进入 C
```

---

# 10. M2.3.2C — Automatic Structure Adjudication

> 注意：由于 B2 §9.1，C 的一部分工作会提前服务于 `pitch+structure` concurrent region 的 note-identity resolution。

当前已知 structure needs 约 51，但 C **不能只处理现有 structure_varies cases**。

## 10.1 Existing structure candidates

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

## 10.2 Independent structure discovery：防止 GAME “稳定地错”

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

足够强时，即使 GAME `structure_varies=false`，也必须进入 C。

## 10.3 C hypothesis scoring

生成可解释的真实结构候选：

```text
H0 = current GAME structure
H1 = split candidate
H2 = merge candidate
H3 = one-note-with-portamento / ornament
```

候选优先来自真实 GAME run structure 或明确 acoustic boundary evidence，禁止由 consensus median 拼 whole-score synthetic result。

## 10.4 C 与 B 的交互 contract

如果 C：

```text
resolved_keep
→ 保留当前 note identity
→ concurrent provisional B 可继续 / finalize

resolved_change_candidate
→ old pitch adjudication invalid
→ 在新 note identities 上 regenerate pitch packets
→ rerun B

unresolved
→ pitch 只能保留 provisional / unresolved
→ machine lanes 全部结束后再进入 D
```

## 10.5 C result state

```text
structure_adjudication_status:
  not_needed
  pending
  resolved_keep
  resolved_change_candidate
  unresolved
```

Structure repair 第一阶段不自动执行；先验证 adjudication precision。

---

# 11. M2.3.2D — Phrase-Level Human Review

人工只处理 B/C 后仍 unresolved 的音乐语义。

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

人工不猜 F0 / MIDI / Hz / cents / octave number。

## 11.2 Review 单位

完整乐句：

```text
最低约 3s
常规 5–8s
最长约 12s
```

优先使用：

```text
LRC line / vocal silence / breath gap / GAME phrase context
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

- 所有 candidate 时间窗完全一致；
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
B2 frozen
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
independence groups
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

歌词冲突标 `lyric_alignment_conflict`，不得靠强移 voiced block 伪修复。

基础 USTX 验收：

> **不做泠鸢 style 和复杂 PITD 时，是否已经唱对旋律和节奏？**

通过后再加入 portamento / onset slide / ornament / vibrato / intonation deviation。

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
independence groups
separation sensitivity
winner / runner-up / margin
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
### M2.3.2B1 — Initial automatic pitch/octave adjudicator ✅ IMPLEMENTED

最新 B1：87 pitch lanes → 72 keep / 0 change / 15 unresolved / 0 repair；189s、202s 均未误修。

### M2.3.2B2 — Pitch adjudication correctness/calibration ← 当前最高优先级

必须完成：

1. concurrent pitch+structure → structure identity first；
2. provisional B invalidation / rerun contract；
3. octave ACF double-period discrimination；
4. spectral low-octave bias removal；
5. symmetric low/high octave regressions；
6. third-F0 cache own provenance/invalidation；
7. pYIN/ACF correlation grouping；
8. repair gate target = B winning hypothesis；
9. 189s / 202s no-false-repair regressions。

### M2.3.2C — Automatic structure adjudication

Existing structure candidates + all-baseline independent discovery；同时承担 concurrent pitch+structure region 的 note identity resolution。

### M2.3.2D — Phrase-level human review

仅 machine lanes 全部结束且存在 unresolved 后生成 3–12s phrase A/B/C 包。

### M2.4 — SAFE repair

只修 finalized adjudicator 高置信确认的简单局部错误。

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
12. **Pitch+structure concurrent region 必须先解析 note identity，或把 B 标为 provisional。**
13. **C 改变 note identity 后必须 invalidate / rerun B。**
14. **Octave ACF 必须处理倍周期歧义。**
15. **Harmonic score 必须避免低八度 harmonic-set 超集偏置。**
16. **pYIN 与 ACF 不能机械算作两个完全独立 hard votes。**
17. **Octave change 优先要求跨机制 evidence convergence。**
18. **Separation artifact 只作为 uncertainty，不直接当真值。**
19. **Cache/provenance 必须真正参与 invalidation。**
20. **Third-F0 必须有独立 cache provenance contract。**
21. **Repair gate 必须显式绑定 adjudicator winning hypothesis。**
22. **Pitch / structure / identity / separation 使用正交状态。**
23. **C 必须做 independent structure discovery，防止 GAME stable-but-wrong。**
24. **B/C 有 explicit pending/provisional/resolved/unresolved lifecycle。**
25. **needs_phrase_review 只能在 machine lanes 全结束后产生。**
26. **人工默认审核完整乐句，不审核 isolated note。**
27. **Phrase candidates 除目标局部外必须完全一致。**
28. **189s 永久作为 extractor-conflict regression。**
29. **202s 永久作为 stochastic pitch / identity-variable regression。**
30. **0 automatic repairs 是合法结果。**
31. **Candidate 0 永远可 rollback。**
32. **所有修改必须局部、可解释、可审计、可 A/B。**
33. **先把 written score 唱对，再生成 PITD。**
34. **先“唱对”，再做泠鸢风格。**
