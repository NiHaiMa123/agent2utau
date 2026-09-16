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
→ pitch / structure residual triage
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

当前使用 order-preserving DP：

```text
match 1↔1
gap 1↔0 / 0↔1
split 1↔2
merge 2↔1
```

cost 包含 onset / overlap / duration / capped weak pitch。

正式 consensus graph 约：

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

它只是 concrete baseline，不是 ground truth。

202s 案例已经证明 medoid selection 本身能消掉部分 stochastic pitch error：某些 runs 给约 MIDI 65，另一些给约 72；medoid 选择的 72 解与双 F0 plateau 一致，因此不再需要 retune。

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

189s 永久保留为 `F0_EXTRACTOR_CONFLICT / NO-REPAIR` regression case，直到更强 automatic adjudicator 能解决。

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

人工不负责猜：

```text
MIDI
Hz
cents
octave number
```

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

# 4. 当前 M2.3 / M2.3.1 状态

M2.3 初版约：

```text
416 baseline notes
312 likely-correct
47 structure-hard
37 needs-listening
16 F0 conflicts
3 ambiguous
1 pitch-hard
```

M2.3.1 已做：

- `PITCH_HARD_SUSPICIOUS` 与 SAFE candidate 分层；
- plateau / note-interior re-triage；
- structure-hard 降级为 `STRUCTURE_CANDIDATE`；
- RMVPE / FCPE structure evidence；
- regression packets；
- SAFE gate 初版；
- listening-set 生成。

最新结果大约：

```text
339 GAME_LIKELY_CORRECT
45  STRUCTURE_CANDIDATE
7   NEEDS_LISTENING_REVIEW
18  F0_EXTRACTOR_CONFLICT
0   PITCH_HARD_SUSPICIOUS
0   SAFE_RETUNE_CANDIDATE
```

原来的 40 组短 clip listening set 只保留 debug/demo，不再作为正式审核流程。

---

# 5. Review 发现：进入 M2.3.2 前必须先修

这一节来自对当前 `triage.py / seqalign.py / diagnostic/run.py / tests` 的再次 review。

## 5.1 PITCH_HARD 分类顺序存在结构歧义绕过风险

当前 `classify()` 先判断：

```text
dual F0 both_oppose_game + low IQR
→ PITCH_HARD_SUSPICIOUS
```

然后才处理：

```text
consensus.structure_varies
```

因此理论上一个 **结构本身不稳定** 的 region，只要双 F0 数值稳定，也可能先被归为 pitch-hard。

必须改成：

```text
if structure_varies / note identity unclear:
    先进入 STRUCTURE_CANDIDATE / AMBIGUOUS
    禁止 PITCH_HARD / SAFE retune
else:
    才允许 pitch-hard judgement
```

新增 regression test：

```text
structure_varies=True
+ dual F0 both oppose GAME
→ 不能返回 PITCH_HARD_SUSPICIOUS
```

## 5.2 Plateau duration 有一帧 off-by-one

当前 plateau duration：

```python
dur = ts[j] - ts[i]
```

对于 N 个 frame，实际覆盖应接近：

```text
N * frame_period
```

当前写法相当于少算一帧，在 `MIN_PLATEAU_S = 80ms` 附近会系统性把边界平台判短。

修正为 frame-inclusive duration，例如：

```text
(ts[j] - ts[i]) + frame_period
```

或直接：

```text
(j - i + 1) * frame_period
```

并补 70 / 80 / 90 ms 边界测试。

## 5.3 SAFE plateau gate 目前没有真正同时核验两个 extractor

当前 `plateau_matches_extractors` 主要比较：

```text
RMVPE structural plateau center
vs
RMVPE full-window center
```

虽然已有 RMVPE-vs-FCPE center agreement gate，但正式 SAFE pitch 还应要求：

```text
RMVPE plateau supports target
AND
FCPE plateau independently supports same target
```

不能把：

```text
RMVPE center
RMVPE structural plateau
```

算成两份独立证据。

SAFE pitch packet 应显式保存：

```text
rmvpe_target_plateau
fcpe_target_plateau
plateau_center_delta_cents
plateau_overlap_ratio
```

## 5.4 Evidence independence 必须显式建模

以下不是独立投票：

```text
RMVPE raw center
RMVPE structural plateau
```

它们来自同一 extractor。

同理：

```text
FCPE raw center
FCPE structural plateau
```

也高度相关。

GAME 5 runs 是同一模型的 stochastic samples，也不是 5 个独立模型。

因此 adjudicator 不得简单做“证据票数”。至少按 evidence family 分组：

```text
GAME family
RMVPE family
FCPE family
third-F0 family
waveform periodicity family
harmonic-spectrum family
musical-context family
```

confidence 按 family agreement / conflict 计算，而不是 raw feature count。

## 5.5 现有 cache provenance 不够安全

当前 shared cache key 基于：

```text
MD5(resolved source path string)
```

而不是源音频内容。

风险：

- 同一路径覆盖成新音频后仍复用旧 decode / separation；
- separator model / 参数更新后仍复用旧 stems；
- 后续 F0 / adjudicator 改版本时也可能混入 stale artifact。

M2.3.2A 必须改为内容与配置绑定的 provenance，例如：

```text
source_audio_sha256
separator_model_name
separator_model_hash / version
separator_config_hash
GAME model hashes
RMVPE model hash
FCPE model hash
third-F0 version/config
analysis schema version
```

cache manifest 必须能判断：

```text
input/model/config changed
→ invalidate dependent artifacts
```

不能仅靠路径区分 source。

## 5.6 raw-vs-zh 汇总仍残留旧 greedy matcher

正式 stochastic alignment 已经使用 DP，但 `diagnostic/run.py` 中 variant summary 仍保留旧 `_align_variants()`：

```text
150ms greedy onset matching
```

它不应继续用于正式 raw-vs-zh conclusions。

改为：

```text
formal align_pair / sequence-alignment summary
```

旧 greedy 仅可保留 legacy debug，或直接删除。

## 5.7 Medoid 只能定义 baseline，不能成为正确性证据

当前 medoid 的 pairwise cost 包含弱 pitch cost。

这可以用于选择“最代表性的一次真实 run”，但：

- 多数 GAME runs 一起错时，medoid 也会错；
- medoid 选择不能计入 pitch truth 的独立 evidence；
- medoid 不应因为和 majority 一致就自动升级为 SAFE。

建议额外输出：

```text
medoid_total_cost
all_run_costs
structure-only medoid sensitivity
selected-run pitch support
```

必要时比较：

```text
full-cost medoid
vs
structure-only medoid
```

若差异大，标 baseline selection uncertainty。

## 5.8 Separation artifact 必须进入 F0 adjudication uncertainty

F0 / harmonic 分析目前主要基于 separated vocal。

但 separation 可能：

- 削弱真实 fundamental；
- 强化某个 harmonic；
- 产生局部残留；
- 制造 octave ambiguity。

因此 octave adjudicator 应同时保留：

```text
separated-vocal evidence
original-mix local spectral evidence
(optional) accompaniment/residual evidence
```

如果 source stem 与 original mix 对候选 harmonic interpretation 明显冲突：

```text
SEPARATION_SENSITIVE
→ 降低 confidence / 保持 unresolved
```

不是强制从 mix 做 F0，而是用 mix 检查 separation 是否改变关键谐波关系。

## 5.9 当前测试覆盖不足

现有 triage tests 覆盖 basic plateau / medoid / classify，但还需要至少增加：

```text
structure ambiguity must block pitch-hard
plateau 80ms frame-inclusive boundary
SAFE gate requires both RMVPE+FCPE plateau
F0 family independence / no double counting
cache invalidation on source-content change
cache invalidation on model/config change
raw-vs-zh formal alignment
189s NO-REPAIR regression
202s pitch-unstable/medoid regression
phrase A/B invariance outside target region
```

---

# 6. M2.3.2A — Correctness Cleanup ← 当前第一优先级

在接第三 F0 之前，先完成上述 review fixes。

验收：

```text
1. structure ambiguity 不会被 pitch-hard 越过
2. plateau duration 边界正确
3. SAFE plateau 同时由 RMVPE + FCPE 独立支持
4. evidence family 不重复计票
5. cache 与 source/model/config hash 绑定
6. raw-vs-zh 使用 formal alignment
7. medoid 只作为 baseline，不作为 truth vote
8. separation-sensitive regions 可被标记
9. 新 regression tests 全部通过
```

M2.3.2A 未通过前，不实现自动 repair。

---

# 7. M2.3.2B — Automatic Pitch / Octave Adjudication

## 7.1 第三 F0

至少增加一个与现有方法足够独立的 estimator。

优先候选：

```text
pYIN / YIN
WORLD Harvest
```

CREPE 可作为额外 neural opinion，但不应因为“模型数量更多”就自动增加 confidence。

第一版只需一个稳定、可复现、易部署的第三 estimator。

## 7.2 Octave adjudicator

对于：

```text
f
vs
2f
```

不得只做模型多数投票。

计算至少：

```text
periodicity / autocorrelation score
candidate harmonic-series fit
subharmonic support
spectral comb / harmonic summation score
voiced stability
GAME run pitch distribution
local melodic context
separation sensitivity
```

输出：

```text
AUTO_PITCH_RESOLVED
AUTO_OCTAVE_RESOLVED
F0_UNRESOLVED
SEPARATION_SENSITIVE
```

若 evidence families 冲突：

```text
保持 Candidate 0
NO AUTO REPAIR
```

## 7.3 Pitch auto-resolution gate

至少要求：

```text
note / region identity clear
structure_varies = false
多个独立 evidence families 支持同一 written-note hypothesis
RMVPE / FCPE / third-F0 的支持关系已知
periodicity/harmonic evidence 不反对
octave/subharmonic test 不反对
separation-sensitive check 不反对
local melodic context 无强冲突
confidence > calibrated threshold
```

自动 pitch 修正不需要用户先猜 MIDI。

---

# 8. M2.3.2C — Automatic Structure Adjudication

45 个 `STRUCTURE_CANDIDATE` 先自动分析，不直接交给人工。

Evidence：

```text
GAME 5-run structure distribution
RMVPE plateau/changepoint
FCPE plateau/changepoint
third-F0/periodicity（必要时）
onset strength
energy change
voiced/unvoiced transition
lyric articulation
note-duration plausibility
local melodic continuity
```

分类：

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

或两个以上候选 score 非常接近时才进入人工。

Structure repair 第一阶段仍不是 SAFE 自动修改；先积累 precision。

---

# 9. Phrase-Level Human Review

## 9.1 人工职责

人工不做：

```text
F0 measurement
MIDI identification
Hz/cents judgement
```

人工只回答：

```text
哪种完整唱法更像 source？
哪种 note structure 在上下文中更自然？
```

适用：

- one note + slide vs two notes；
- split vs merge；
- grace / ornament 是否独立记谱；
- 自动 structure evidence 多解；
- candidate scores 接近。

## 9.2 Review 单位必须是完整乐句

默认禁止 0.5–1.5s isolated clip 作为主审核入口。

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

优先包含：

```text
目标前 2–3 notes
目标 region
目标后 2–3 notes
```

## 9.3 Phrase A/B/C 包

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
- 除目标 region 外，score 与 render config 必须完全一致；
- 不允许 A/B 同时改变多个无关因素；
- source 与 candidates 使用相同 phrase boundary，避免上下文错位。

人工只需选：

```text
Baseline
A
B
C
都差不多
都不对
```

可附 confidence：high / medium / low。

## 9.4 Zoom clip 只是辅助

流程：

```text
先听 phrase
→ 能判断：结束
→ 仍难判断：再听 zoom
```

zoom 不作为默认主证据。

---

# 10. Repair Engine

## 10.1 M2.4 SAFE repair 进入条件

必须先满足：

```text
M2.3.2A correctness cleanup 通过
pitch/octet automatic adjudicator 可用
189s regression 不会被误修
separation-sensitive gate 可用
phrase review workflow 可用
Candidate 0 / rollback contract 完整
```

第一版仍优先最简单：

```text
single-note written-pitch retune
```

若最终：

```text
0 SAFE repairs
```

也是合法结果。

## 10.2 Candidate 0 与审计

永久保留：

```text
Candidate 0 = selected real GAME medoid run
```

每个 repair 记录：

```text
region
before
after
evidence families
reason
confidence
gates passed
phrase A/B（若需要）
rollback data
```

禁止覆盖原 baseline。

## 10.3 Structure repair

以下默认 PROBABLE / AMBIGUOUS：

```text
split
merge
missing note
false note
large boundary shift
```

只有 automatic adjudication + phrase calibration 证明某类规则 precision 足够高，才逐类升级。

修改 boundary 后优先让 GAME estimator 局部重估 pitch，不退回 `median F0 → note`。

---

# 11. Lyrics / USTX / PITD

melody 稳定后才正式映射 lyrics：

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

通过后才加入：

- portamento；
- onset slide；
- ornament；
- vibrato；
- intonation deviation。

PITD 不得掩盖 written-note error。

---

# 12. Evaluation

## Diagnostic

记录：

```text
GAME run note counts
pairwise alignment costs
selected medoid + medoid sensitivity
match/gap/split/merge counts
consensus stability
RMVPE/FCPE/third-F0 evidence families
periodicity/harmonic evidence
separation sensitivity
pitch adjudication
structure adjudication
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

# 13. Milestones

### M2.0 — Foundation survey ✅

### M2.1 / M2.1.1 — Initial diagnostic + correctness ✅

### M2.1.2 — GAME stochastic baseline ✅

### M2.2A — Formal sequence alignment ✅

### M2.2B — Dual-F0 ✅

### M2.3 — Residual-error triage ✅

### M2.3.1 — Triage calibration ✅

已完成 plateau/interior re-triage、SAFE gate 初版、structure candidates、dual structure evidence、regression packets；202s stochastic pitch case 已由 medoid baseline 解决，当前 run 为 0 SAFE pitch candidate。

### M2.3.2A — Correctness cleanup ← 当前最高优先级

必须修：

1. structure ambiguity 优先于 pitch-hard；
2. plateau frame-inclusive duration；
3. SAFE gate 同时核验 RMVPE + FCPE plateau；
4. evidence-family independence；
5. content/model/config-hash cache provenance；
6. raw-vs-zh 改 formal alignment；
7. medoid sensitivity 输出；
8. separation-sensitive 标记；
9. 补齐对应 regression tests。

### M2.3.2B — Automatic pitch/octave adjudication

第三 F0 + periodicity + harmonic/subharmonic + separation-sensitive check。

### M2.3.2C — Automatic structure adjudication

先自动筛 structure candidates，只把真正 unresolved 的结构语义交给人工。

### M2.3.2D — Phrase-level human review

正式生成 3–12s（常规 5–8s）的 source / baseline / A/B/C phrase 包；旧 short-clip listening 只保留 debug。

### M2.4 — SAFE repair

只实现已被 adjudicator 高置信确认的简单局部修复。

### M2.5 — PROBABLE structure repair

按实际 precision 决定是否实现 split / merge / missing / false note / boundary shift。

### M2.6 — Optional second opinion

只有 GAME + formal alignment + multi-F0 + periodicity/harmonic + onset/lyric 仍留下大量关键 unresolved region 时，才考虑 ROSVOT 等额外模型。

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

# 14. 最终原则

1. **GAME 是默认 melody transcription 基座。**
2. **最终 baseline 必须来自真实 GAME run，不是 synthetic consensus。**
3. **Medoid 是 concrete baseline selection，不是 correctness proof。**
4. **Consensus 是 uncertainty graph，不是最终 note skeleton。**
5. **F0 measurement 与 score interpretation 分开。**
6. **能程序测量的 pitch/octave 不交给人工猜。**
7. **单 F0 extractor 不能独自推翻 GAME。**
8. **同一 extractor 的 raw/structural features 不是独立票。**
9. **GAME 多 runs 是 stochastic samples，不是多个独立模型。**
10. **Pitch-hard 前必须先排除 structure ambiguity。**
11. **SAFE pitch 必须有 RMVPE + FCPE 独立 plateau 支持。**
12. **Octave conflict 要看 periodicity/harmonic/subharmonic，不做简单多数投票。**
13. **Separation artifact 是 adjudication uncertainty 的一部分。**
14. **Cache 必须绑定音频内容与模型/配置 hash，不能只按路径。**
15. **正式 variant comparison 使用 formal sequence alignment。**
16. **Evidence confidence 按 family 计算，禁止重复计票。**
17. **Structure candidate 先自动 adjudicate，再决定是否人工。**
18. **人工默认审核完整乐句，不审核 isolated note。**
19. **Phrase A/B/C 除目标局部外必须完全一致。**
20. **Zoom clip 只是辅助。**
21. **189s 永久作为 F0 conflict / NO-REPAIR regression。**
22. **202s 永久作为 stochastic pitch / medoid regression。**
23. **candidate / auto-resolved / unresolved / confirmed repair 分层统计。**
24. **0 automatic repairs 是合法结果。**
25. **Candidate 0 永远可 rollback。**
26. **所有修改必须局部、可解释、可审计、可 A/B。**
27. **先把 written score 唱对，再生成 PITD。**
28. **先“唱对”，再做泠鸢风格。**
