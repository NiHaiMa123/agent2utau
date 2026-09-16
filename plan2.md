# agent2utau — Plan 2：GAME 主转谱 + 自动证据裁决 + 分阶段演唱建模

> 修订日期：2026-09-16
>
> 核心原则：**先把“唱对”解决，再把“唱得像泠鸢”解决。**
>
> 当前工程原则：**GAME 提供真实可渲染的乐谱候选；多次 GAME consensus 只作为 uncertainty / evidence graph。音高测量与 octave / pitch conflict 优先由程序裁决；人工只负责机器仍无法确定的音乐语义与候选听感，并且以完整乐句为审核单位，而不是孤立短切片。**

---

# Part A — 项目目标与已确认事实

## 1. 最终目标流程

```text
原曲
→ 人声 / 伴奏分离
→ GAME 多次转谱
→ 选择真实 GAME medoid run 作为 Candidate 0
→ 多 run consensus uncertainty graph
→ RMVPE + FCPE + 第三 F0 / 谐波证据
→ stable plateau / changepoint / onset / energy / lyric evidence
→ residual-error triage
→ automatic adjudication
→ 只修强证据局部错误
→ 对仍 unresolved 的结构问题做 phrase-level A/B/C 人工审核
→ lyrics ↔ melody mapping
→ OpenUtau / DiffSinger 基础渲染
→ constrained PITD / 演唱细节
→ 最后再做泠鸢风格迁移
```

旧主旋律方式：

```text
歌词字窗口
→ F0 中位数
→ heuristic split
→ MIDI note
```

已确认能力不足，只保留为显式 fallback，不再作为默认 melody transcription。

---

## 2. 当前已完成基础设施

仓库已经真正接入：

- 官方 GAME 1.0.3-medium ONNX；
- 官方 RMVPE ONNX；
- FCPE；
- GAME `encoder → segmenter → bd2dur → estimator`；
- OpenUtau AudioSlicer 等价切片；
- GAME 同配置多次运行；
- `diagnose --repeats N`；
- order-preserving sequence alignment；
- `1↔1 / gap / 1↔2 / 2↔1` 显式关系；
- GAME stochastic consensus；
- voiced-island structural F0；
- RMVPE / FCPE evidence packets；
- lyric-boundary evidence；
- GAME USTX + DiffSinger render；
- medoid baseline selection；
- stable plateau detection；
- residual-error triage；
- M2.3.1 SAFE gate；
- dual-extractor structure evidence；
- regression cases；
- listening-set 生成能力。

forced char `known_boundaries` 路径只保留实验用途，不进入默认主链。

---

## 3. GAME 是主转谱基座

早期 forced-boundary 实验曾出现：

```text
A raw ≈ 419 notes
B zh  ≈ 417 notes
C forced-char-boundary ≈ 760 notes
```

C 上的 suspicious 数不能代表 GAME raw 错误率，因为强制字符边界本身改变了 segmentation 和 estimator。

长期固定原则：

- GAME raw 是主 melody transcription 来源；
- lyric char start 不是天然 note boundary；
- RMVPE / FCPE / 第三 F0 都是 evidence，不是全曲主转谱器；
- correction 只修少量 residual errors，不重写整首谱。

---

## 4. GAME 存在真实 stochasticity

《年轮》同输入、同参数多次 raw GAME：

```text
约 418–425 voiced notes / run
```

所以：

```text
single GAME run != deterministic truth
```

stochasticity 本身是 uncertainty evidence：

- 多次一致 → 更可信；
- split / merge / pitch 多解 → 局部不确定；
- 自动 repair 不能依赖单次 GAME。

---

## 5. Formal sequence alignment ✅

当前 `diagnostic/seqalign.py` 使用：

```text
order-preserving DP
+ onset cost
+ IoU / overlap cost
+ duration cost
+ capped weak-pitch cost
+ gap
+ split
+ merge
```

显式表示：

```text
1 ↔ 1   same-note candidate
1 ↔ 0   missing
0 ↔ 1   extra
1 ↔ 2   split disagreement
2 ↔ 1   merge disagreement
```

最新 5+5 GAME runs 的 raw consensus evidence graph：

```text
397 events
348 GAME_STABLE
2   GAME_VARIABLE
47  GAME_UNSTABLE
43  events 有 split/merge structure variance
```

---

## 6. Consensus 只是 evidence graph，不是最终谱面

必须长期保持：

```text
397 consensus events != 最终 397 notes
```

包含 split / merge 的 component 只表示局部结构不确定。

禁止把：

```text
start_median
duration_median
tone_median
```

直接拼成 synthetic USTX。

`event_as_note()` 只能用于 diagnostic / cross-consensus comparison。

union-find component 由于存在 transitive bridging 风险，也不负责决定唯一结构。

---

## 7. Candidate 0 必须来自真实 GAME run

从多次 raw GAME 中选 medoid run：

```text
对其他 runs 的总 pairwise alignment cost 最小
```

当前《年轮》M2.3/M2.3.1 已验证这种策略有效。

意义：

- 每颗 baseline note 都来自真实 GAME 推理；
- 不产生不存在于任何 run 的 synthetic structure；
- correction 可 audit / rollback；
- 某些 stochastic pitch error 可直接通过 medoid selection 被消除。

202.52s 就是实际案例：早期单次 GAME 曾给出约 MIDI 65.3，而其他 GAME runs 存在约 72.4 解；M2.3.1 的 medoid baseline 选择到了约 72.4，与双 F0 plateau 一致，因此该问题被 baseline selection 自身解决，不再是 SAFE-retune candidate。

---

# Part B — F0 与 Pitch Evidence

## 8. Dual-F0 已证明必要 ✅

189s 附近出现过典型 octave conflict：

```text
RMVPE ≈ 高八度候选
FCPE  ≈ 低八度候选
GAME  ≈ 其中一个候选
```

单看 RMVPE 会产生错误 octave-repair 风险。

因此：

> **任何单一 F0 extractor 都不能独自推翻 GAME。**

189s 区域永久保留为 `F0_EXTRACTOR_CONFLICT / NO-REPAIR` regression case，直到自动 adjudicator 能给出更强证据。

---

## 9. F0 measurement 与 score interpretation 必须分开

这是 M2.3.2 的核心认识。

### F0 measurement

问题：

```text
这一帧 / 这一稳定区间的 fundamental frequency 是多少？
```

这是程序更擅长的问题，应由：

- RMVPE；
- FCPE；
- 第三独立 F0 estimator；
- waveform periodicity；
- harmonic spectrum；

共同处理。

### Score interpretation

问题：

```text
这一段连续 F0 应记为一颗 note、两颗 note、滑音还是 ornament？
```

这是 GAME + structure evidence + musical context 的问题。

人工可以参与后者的最终模糊案例，但不应承担“猜 MIDI / 猜 cents / 猜绝对音高”的工作。

---

## 10. Structural F0

当前处理：

```text
raw F0
→ 仅填 <=40 ms 短 unvoiced gap
→ 按连续 voiced island 独立 filtering
→ structural F0
```

职责：

- structural F0：note / plateau / boundary / changepoint evidence；
- raw F0：PITD / vibrato / portamento / intonation。

所有 pitch error / dispersion 对外统一 cents。

`high_dispersion` 只作为 feature，不单独触发 suspicious。

---

## 11. Full-window median 只适用于结构稳定区域

对稳定 note，GAME note window 内 F0 median 有用。

对以下情况必须优先看 plateau / changepoint：

- split；
- merge；
- missed split；
- portamento；
- 快速转音；
- grace / ornament。

M2.3.1 已加入 note interior / plateau re-triage，实际把大量 vibrato/transition 假阳性消掉。

---

# Part C — Lyrics Evidence

## 12. Lyric timestamp 永远不是默认 note boundary

必须区分：

```text
Whisper char start
辅音起点
元音起点
F0 voiced onset
GAME note onset
```

歌词只用于：

```text
matching
articulation evidence
weak boundary-snap evidence
missing-boundary evidence
lyrics ↔ notes mapping
```

禁止：

```text
char start → 强制新增 GAME boundary
```

只有：

```text
GAME boundary / structure 不稳定
+
RMVPE / FCPE changepoint 支持
+
energy / onset 支持
+
lyric articulation 支持
```

才允许生成 boundary repair candidate。

---

# Part D — M2.3 / M2.3.1 当前真实状态

## 13. M2.3 Residual-Error Triage ✅

初版曾得到：

```text
416 baseline notes
312 GAME_LIKELY_CORRECT
47  structure-hard
37  needs-listening
16  F0 conflicts
3   ambiguous
1   pitch-hard
```

这些只是 validator 输出，不等于 confirmed errors。

---

## 14. M2.3.1 Triage Calibration ✅ 实现完成

M2.3.1 已完成以下收紧：

- `PITCH_HARD_SUSPICIOUS` 与 `SAFE_RETUNE_CANDIDATE` 分层；
- SAFE gate 加入 GAME presence / tone agreement / structure stability / single plateau / neighbours 等硬条件；
- wrong-pitch 用 plateau / note-interior center 重判，不再依赖 full-window median；
- `STRUCTURE_HARD_SUSPICIOUS` 改名 `STRUCTURE_CANDIDATE`；
- RMVPE / FCPE 独立生成 structure evidence；
- regression cases 落地；
- listening-set 生成能力落地。

最新《年轮》结果约为：

```text
339 GAME_LIKELY_CORRECT
45  STRUCTURE_CANDIDATE
7   NEEDS_LISTENING_REVIEW
18  F0_EXTRACTOR_CONFLICT（最新 listening set）
0   PITCH_HARD_SUSPICIOUS
0   SAFE_RETUNE_CANDIDATE
```

关键修正：

```text
202.52s
早期：看起来像 GAME 低约 700c
M2.3.1：发现 GAME runs 自身 tone-unstable（约 65.3 / 72.4）
medoid baseline 选择约 72.4
与 RMVPE / FCPE 稳定 plateau 一致
→ baseline selection 自行解决
→ 不需要 retune
```

这是一个重要结论：**程序化 consensus / medoid 可以先消掉一部分错误，不应该过早把问题交给人工。**

---

## 15. 当前 listening-set 的问题

当前 demo 已生成约 40 组：

```text
SOURCE short clip
RENDER short clip
```

并要求人工判断：

```text
这里是高八度还是低八度？
这里更像 MIDI 65 还是 MIDI 72？
```

该审核设计不再作为正式流程。

原因：

1. 普通听者没有绝对音高，不应承担 F0 detector 的职责；
2. 0.5–1.5s 孤立片段缺乏前后旋律上下文；
3. 短音、转音、辅音、气声和 DiffSinger 音色都会干扰判断；
4. 人耳更适合比较完整旋律关系，而不是给 isolated tone 标 MIDI；
5. 当前系统已经有足够证据继续把 pitch adjudication 自动化。

当前 listening set 保留为 debug/demo，不作为 M2.3.2 的正式人工验收界面。

---

# Part E — 当前最高优先级：M2.3.2 Automatic Adjudication

## 16. 总目标

目标是进一步减少：

```text
F0_EXTRACTOR_CONFLICT
NEEDS_LISTENING_REVIEW
STRUCTURE_CANDIDATE
```

中真正需要人工介入的数量。

原则：

> **能程序测量的东西不要交给人耳；只有音乐语义仍然多解时才让人选。**

---

## 17. Pitch / octave conflict 自动裁决

对 `F0_EXTRACTOR_CONFLICT` 不再默认人工试听猜音高。

自动 evidence stack：

```text
RMVPE
+
FCPE
+
第三独立 F0 estimator
+
waveform periodicity / autocorrelation
+
harmonic spectral evidence
+
GAME multi-run pitch distribution
+
local melodic context
```

第三 F0 estimator 优先选择与 RMVPE / FCPE 机制足够独立的实现，例如：

```text
pYIN / YIN
WORLD Harvest
CREPE（可作为额外 neural opinion）
```

第一版只需要选一个可靠、易集成、CPU 可运行的独立 estimator；不必一次接全部。

---

## 18. Octave adjudicator

对候选：

```text
F0 = f
vs
F0 = 2f
```

不能只做 extractor 多数投票。

需要计算：

```text
candidate periodicity score
harmonic-series fit
subharmonic support
spectral harmonic summation / comb score
voiced stability
extractor confidence / agreement
GAME-run support
```

例如真实基频较弱但二次谐波很强时：

```text
f      弱
2f     强
3f     强
4f     强
```

单模型可能误判为 `2f`，但完整 harmonic series 应能支持 `f`。

输出分类：

```text
AUTO_PITCH_RESOLVED
AUTO_OCTAVE_RESOLVED
F0_UNRESOLVED
```

只有 `F0_UNRESOLVED` 才允许进入后续人工/第三证据流程。

人工不得被要求输出：

```text
MIDI 58 / 70
+1200c / -1200c
Hz 数值
```

---

## 19. Pitch auto-resolution gate

程序自动决定 pitch 至少要求：

```text
1. GAME note identity / region identity 清楚
2. 至少两个独立 pitch evidence 支持同一 written-note hypothesis
3. octave/subharmonic test 不反对
4. harmonic spectral evidence 支持
5. local melodic context 不产生明显矛盾
6. 无显著 structure ambiguity
7. confidence 高于 calibrated threshold
```

若冲突：

```text
保持 Candidate 0
标 F0_UNRESOLVED
NO AUTO REPAIR
```

而不是强行让人工猜绝对音高。

---

## 20. Structure candidate 自动裁决

45 个 `STRUCTURE_CANDIDATE` 不直接交给人工。

自动 evidence：

```text
GAME 5-run structure distribution
RMVPE plateau / changepoint
FCPE plateau / changepoint
第三 F0 / periodicity（必要时）
onset strength
energy change
voiced/unvoiced transition
lyric articulation
note-duration plausibility
local melodic continuity
```

尝试区分：

```text
ONE_NOTE_WITH_PORTAMENTO
TRUE_SPLIT
TRUE_MERGE
GRACE_OR_ORNAMENT
F0_ARTIFACT
UNRESOLVED_STRUCTURE
```

只有 `UNRESOLVED_STRUCTURE` 或多个候选分数接近时才进入人工审核。

---

## 21. Automatic adjudication 输出

新增：

```text
runs/<id>/diagnostic/
  pitch_adjudication.json
  octave_adjudication.json
  structure_adjudication.json
  unresolved_pitch_regions.json
  unresolved_structure_regions.json
  phrase_review_set.json
  regression_cases/
```

每个 adjudication packet 至少保存：

```text
region
GAME candidate(s)
GAME multi-run distribution
RMVPE evidence
FCPE evidence
third-F0 evidence
periodicity evidence
harmonic evidence
structure evidence
candidate scores
decision
confidence
reason
```

---

# Part F — 人工审核只做 Phrase-Level Musical Review

## 22. 人工审核职责

人工不再承担：

```text
测 F0
猜 MIDI
猜 cents
判断具体 Hz
```

人工只负责：

```text
哪一种完整唱法更像原唱？
哪一种 note structure 在上下文里更自然？
A / B / C 是否存在明显听感错误？
```

主要应用于：

- split vs one-note + slide；
- merge vs two distinct notes；
- grace / ornament 是否应记为独立 note；
- 多个候选结构分数接近；
- 自动证据仍无法唯一裁决的区域。

---

## 23. 人工审核单位必须是完整乐句

禁止把 0.5–1.5s 的孤立 note clip 作为默认审核入口。

每个人工 review case 必须先构建 phrase window。

phrase boundary 优先来源：

```text
LRC 当前歌词行 / phrase
+
vocal silence / phrase gap
+
GAME phrase context
```

建议范围：

```text
最短约 3s
常规约 5–8s
最长约 12s
```

并保证目标区域前后都有足够上下文，优先包含：

```text
目标前 2–3 个 notes
目标 region
目标后 2–3 个 notes
```

若单行歌词太短，可向前/后扩展一个短句；若过长，优先在明显 silence / breath 处分割。

---

## 24. Phrase-level A/B/C 包

正式人工审核包：

```text
SOURCE_PHRASE_original_mix.wav
SOURCE_PHRASE_separated_vocal.wav
BASELINE_PHRASE.wav
CANDIDATE_A_PHRASE.wav
CANDIDATE_B_PHRASE.wav
CANDIDATE_C_PHRASE.wav   # 仅有第三候选时
```

要求：

- 所有 render 使用同一 singer / phonemizer / color / volume / PITD policy；
- 除目标局部外，Baseline / A / B / C 必须完全相同；
- 不允许候选间同时改变无关参数；
- review metadata 明确标目标 region，但不要要求用户识别音名。

用户只需回答：

```text
A 更像原唱
B 更像原唱
C 更像原唱
Baseline 已经最好
都差不多
都不对
```

---

## 25. Zoom clip 只是辅助放大镜

每个 phrase case 可以额外生成：

```text
zoom/source.wav
zoom/baseline.wav
zoom/candidate_A.wav
zoom/candidate_B.wav
```

但流程必须是：

```text
先听完整乐句
↓
能判断 → 结束
↓
仍难判断
↓
再听 zoom
```

不能把 zoom 当主审核材料。

---

## 26. Phrase review 结果

输出：

```text
human_phrase_review.json
```

只记录 preference / judgement：

```json
{
  "region": [188.2, 191.4],
  "choice": "candidate_b",
  "confidence": "high|medium|low",
  "comment": "optional"
}
```

人工结果不写成“ground-truth F0”；它只作为 musical-semantic / perceptual evidence。

---

# Part G — Repair Engine

## 27. M2.4 SAFE repair 的进入条件

M2.3.2 达到以下条件后才进入：

```text
pitch/octet conflicts 有 automatic adjudicator
189s regression 不会被错误自动修
pitch auto-resolution 有 confidence gate
structure candidate 已能先自动筛掉明显 case
人工 review 已改为 phrase-level A/B/C
Candidate 0 / rollback contract 保持完整
```

第一版 repair 仍以：

```text
single-note pitch retune
```

为最简单类型。

如果最终没有高置信 SAFE pitch candidate，则允许输出：

```text
0 automatic repairs
```

这不是失败。

---

## 28. Candidate 0 与修复审计

永久保留：

```text
Candidate 0 = selected real GAME medoid run
```

每个 repair 必须记录：

```text
region
before
candidate after
evidence
reason
confidence
which gate passed
phrase-level A/B（若需要）
rollback information
```

不能直接覆盖原 GAME baseline。

---

## 29. SAFE retune

只允许高置信 single-note written-pitch 修正。

目标 pitch 应来自：

```text
多个独立 evidence 对同一 written-note hypothesis 的一致支持
```

不能把任意 raw F0 deviation 直接写成 MIDI note。

---

## 30. Structure repair 暂不直接进入 SAFE

以下默认仍属于 PROBABLE / AMBIGUOUS：

```text
split
merge
missing note
false note
large boundary shift
```

只有某类 automatic adjudication + phrase review 的 precision 足够高，才逐类升级。

修改 boundary 后优先让 GAME estimator 重新估局部 pitch，而不是退回 `median F0 → note`。

---

## 31. Candidate scoring

候选：

```text
C0 real GAME baseline
C1 retune
C2 boundary shift
C3 split
C4 merge
C5 local combined repair
```

证据包括：

```text
GAME presence / tone consensus
GAME structural stability
sequence-alignment relation
RMVPE pitch evidence
FCPE pitch evidence
third-F0 evidence
periodicity / harmonic evidence
RMVPE / FCPE plateau + changepoint
voiced consistency
energy / onset
lyric compatibility
duration plausibility
local melodic continuity
complexity penalty
unsupported-edit penalty
```

必须设置 minimum improvement。

原则：

> **宁可保留 GAME 的小错误，也不要让 correction 制造新错误。**

---

# Part H — Lyrics / USTX / PITD

## 32. Lyrics ↔ corrected melody

melody 稳定后再映射：

```text
1 char → 1 note
1 char → N notes（melisma）
N chars → N notes
```

OpenUtau：

```text
首 note：真实歌词
同字后续：+
换气：AP
静音：gap / SP
```

lyrics 与 melody 冲突时标 `lyric_alignment_conflict`，不得通过把歌词强移到最近 voiced block 来伪修复。

---

## 33. 基础 USTX 验收

第一阶段只含：

- corrected score；
- lyrics；
- timing；
- singer / renderer；
- 必要 phonemizer 设置。

核心验收：

> **不做泠鸢 style 和复杂 PITD 时，是否已经唱对《年轮》的旋律和节奏？**

人工验收也以完整乐句/整段为主，不以 isolated note 为主。

---

## 34. raw F0 → constrained PITD

written score 通过后才加入：

- portamento；
- 音头滑入；
- ornament；
- vibrato；
- intonation deviation。

PITD 不得掩盖 written-note 错误。

---

# Part I — Evaluation

## 35. Diagnostic level

至少记录：

- 每次 GAME run note count；
- pairwise alignment cost；
- medoid baseline run；
- `1↔1 / gap / split / merge` 数；
- consensus stability；
- residual triage 分类；
- RMVPE / FCPE / third-F0 agreement；
- octave adjudication；
- harmonic / periodicity evidence；
- RMVPE / FCPE structure agreement；
- candidate count；
- AUTO_RESOLVED count；
- UNRESOLVED count；
- phrase-review count；
- confirmed repair count；
- regression-case status。

---

## 36. Score level

记录：

```text
real GAME Candidate 0
corrected score
retune count
split / merge count
boundary-shift count
GAME preservation ratio
rollback coverage
```

GAME preservation ratio 应尽量高。

---

## 37. Render / listening level

机器比较：

```text
source / separated vocal F0
real GAME baseline score
candidate corrected score
DiffSinger baseline render
DiffSinger corrected render
```

人工比较：

```text
phrase-level source
phrase-level baseline
phrase-level A/B/C candidates
```

明确区分：

- GAME transcription error；
- F0 extractor error；
- octave ambiguity；
- structure representation ambiguity；
- lyric alignment error；
- PITD error；
- DiffSinger render deviation。

---

# Part J — Milestones

## 38. 当前实施顺序

### M2.0 — Foundation survey ✅

完成。

### M2.1 / M2.1.1 — Initial diagnostic + correctness ✅

完成 forced-boundary 误读修正、cents、raw-first、lyric evidence-only、voiced-island structural F0 等。

### M2.1.2 — GAME stochastic baseline ✅

完成多次 GAME 与 stochasticity 测量。

### M2.2A — Formal sequence alignment ✅

完成 DP `match/gap/split/merge` 与 consensus evidence graph。

### M2.2B — Dual-F0 evidence ✅

完成 RMVPE + FCPE；189s 成为 extractor-conflict regression case。

### M2.3 — Residual-error triage ✅

完成 medoid baseline、plateau 初版和全曲 triage。

### M2.3.1 — Triage calibration ✅

完成：

- SAFE gate；
- plateau/interior re-triage；
- needs-listening 大幅减少；
- structure-hard 降级 structure candidates；
- dual structure evidence；
- regression cases；
- 202s stochastic pitch case 由 medoid baseline 自动解决；
- 当前 run 0 SAFE pitch candidate。

旧“40 个短 clip 人工猜音高”的 listening workflow **废弃为正式验收方式**，只保留 debug/demo。

### M2.3.2 — Automatic adjudication + phrase review ← 当前最高优先级

必须完成：

1. 接入至少一个独立第三 F0 estimator；
2. octave / pitch conflict 增加 periodicity + harmonic spectral adjudication；
3. 输出 `AUTO_PITCH_RESOLVED / AUTO_OCTAVE_RESOLVED / F0_UNRESOLVED`；
4. 人工不再输入 MIDI / Hz / cents；
5. structure candidates 先做自动 evidence scoring；
6. 只有真正 unresolved structure 才进入 human review；
7. human review 默认生成 3–12s、常规 5–8s 的完整 phrase；
8. Baseline / A / B / C 除目标区域外必须完全一致；
9. zoom clip 只做二级辅助；
10. 人工只回答 A/B/C/Baseline/都不对/差不多；
11. 189s conflict 作为 automatic octave-adjudication regression case；
12. 统计自动解决比例与真正需要人工的比例。

### M2.4 — SAFE repair

只实现 M2.3.2 已能稳定自动裁决的简单强证据错误。

### M2.5 — PROBABLE structure repair

只有自动 adjudication + phrase-level calibration 证明 precision 足够高时才逐步实现 split / merge / missing / false note / boundary shift。

### M2.6 — Optional second opinion

只有 GAME + formal alignment + 多 F0 + harmonic/periodicity + lyric/onset evidence 仍留下大量关键 unresolved region 时才考虑 ROSVOT 等额外模型。

### M2.7 — Lyrics mapping + base USTX

corrected real score → lyrics / melisma → 可编辑工程。

### M2.8 — PITD + render loop

raw F0 → constrained PITD → DiffSinger → reference / score / render 三层评价。

### M2.9 — 《年轮》M2 验收

主要比较：

```text
selected real GAME medoid baseline
vs
corrected score
```

人工听感以完整乐句/完整段落为主，不以孤立 note 为主。

通过后冻结 melody score。

### M3 — 泠鸢 style profile

只有 M2.9 通过后开始。

原则：

> **原唱决定“唱什么”；泠鸢参考决定“怎么唱”。**

---

# 39. 最终原则

1. **GAME 是默认 melody transcription 基座。**
2. **最终可渲染 baseline 必须来自真实 GAME run，不是 synthetic consensus。**
3. **Candidate 0 使用 real GAME medoid run。**
4. **Consensus 是 uncertainty / evidence graph，不是 note skeleton。**
5. **RMVPE / FCPE / third-F0 是 evidence，不是主转谱器。**
6. **F0 measurement 与 score interpretation 必须分开。**
7. **能由程序测量的 pitch / octave 不交给人工猜。**
8. **单 F0 extractor 永远不能独自推翻 GAME。**
9. **octave conflict 要加入 periodicity / harmonic evidence，而不是简单多数投票。**
10. **自动 evidence 仍冲突时保持 unresolved，不强行 repair。**
11. **structure candidate 先程序裁决，再决定是否人工。**
12. **人工审核的默认单位是完整乐句，不是孤立短切片。**
13. **phrase review 常规 5–8s，并保留目标前后旋律上下文。**
14. **zoom clip 只是辅助放大镜。**
15. **人工只做 A/B/C/基线/都不对等相对听感选择，不要求 MIDI / Hz / cents。**
16. **Baseline / A / B / C 除目标局部外必须完全一致。**
17. **189s 永久作为 extractor-conflict / octave-adjudication regression case。**
18. **202s 已证明 medoid baseline 本身能解决部分 stochastic pitch error。**
19. **candidate / unresolved / auto-resolved / confirmed repair 必须分层统计。**
20. **如果真实 residual errors 很少，就保持 correction layer 轻量。**
21. **0 automatic repairs 也是合法结果。**
22. **Candidate 0 永远可 rollback。**
23. **所有修改必须局部、可解释、可审计、可 A/B。**
24. **先把 written score 唱对，再生成 PITD。**
25. **先“唱对”，再做泠鸢风格。**