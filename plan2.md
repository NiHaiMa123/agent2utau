# agent2utau — Plan 2：GAME 主转谱 + 证据驱动校正 + 分阶段演唱建模

> 修订日期：2026-09-16
>
> 核心原则：**先把“唱对”解决，再把“唱得像泠鸢”解决。**
>
> 当前工程原则：**GAME raw / GAME consensus 是主旋律 baseline；先把 GAME 自身 stochasticity、序列结构和真实 residual error 量清，再做 repair。F0、歌词边界和第二模型都只是证据，不直接替代 GAME。**

---

## 1. 当前状态

旧 pipeline 已具备：

- 原曲解码与人声/伴奏分离；
- FCPE F0；
- LRC + Whisper attention/DTW 歌词对齐；
- USTX 构建；
- OpenUtau headless bridge；
- DiffSinger 自动渲染；
- 混音与基础评价。

旧主旋律生成：

```text
歌词字窗口
→ F0 中位数
→ heuristic split
→ MIDI note
```

该逻辑能力不足，降级为 fallback，不再作为默认 melody transcription。

### 1.1 已完成的 Plan2 基础设施

仓库已真正接入：

- 官方 GAME 1.0.3-medium ONNX；
- 官方 RMVPE ONNX；
- GAME `encoder → segmenter → bd2dur → estimator`；
- OpenUtau AudioSlicer 等价切片；
- RMVPE 16 kHz / hop 160；
- `diagnose`；
- GAME USTX + DiffSinger render；
- RMVPE overlay；
- GAME raw evidence packets；
- lyric-boundary matching；
- variant time-alignment；
- GAME 同配置重复推理；
- GAME stochastic consensus；
- voiced-island structural F0。

### 1.2 第一轮错误结论已经纠正

早期结果：

```text
A raw:        419
B zh:         417
C forced-bd:  760
```

最初在 C 上看到：

```text
76 suspicious
54 wrong_pitch
```

这些数字不能代表 GAME raw 的真实错误率，因为强制字符边界大量增加 note，并改变 estimator 输出。

因此：

- GAME raw 保留为主 baseline；
- forced known-boundaries 仅保留实验用途；
- 歌词字符边界只作为 evidence，不再直接驱动 note segmentation。

### 1.3 M2.1.1 corrected diagnostic

修正后一次完整 run：

```text
A raw:        421
B zh:         420
C forced-bd:  751
```

修复内容：

- IQR / pitch error 对外统一 cents；
- variant comparison 不再 index zip；
- structural F0 只填短 unvoiced gap；
- GAME known-boundaries D3PM init 与官方实现一致；
- suspicious 改为 GAME raw-first；
- lyric boundaries 改为 overlay / matching；
- forced-boundary 降级 experimental；
- structural F0 改为 voiced-island filtering，不再 `NaN→0` 后整体 median filter。

### 1.4 M2.1.2 stochastic consensus 已完成

《年轮》同配置 GAME 重跑 5 次：

```text
raw note counts: 415–425
zh note counts:  418–427
```

当前 raw consensus：

```text
453 consensus events
338 GAME_STABLE
47  GAME_VARIABLE
68  GAME_UNSTABLE
```

raw consensus vs zh consensus：

```text
437 matched
14 pitch disagreements > 1 semitone
```

结论：

> **单次 GAME 输出不是稳定真值；很多单次 A/B 差异只是 D3PM stochasticity。后续所有语言条件、repair 改进和错误率判断都必须建立在 consensus / sequence alignment 上。**

---

## 2. 项目定位

GAME 是 singing voice transcription 模型，但真人歌声到离散 note 天生存在模糊：

- vibrato 是 note 内 modulation 还是多个 note；
- portamento 何时算真实换音；
- grace note / appoggiatura 是否单独记谱；
- 极短经过音是否应进入 MIDI；
- 辅音、气声、分离残留可能制造假 boundary；
- octave ambiguity；
- onset / offset 本身存在几十毫秒模糊区间。

本项目不训练一个总体超过 GAME 的新转谱器。

目标是：

> **GAME + GAME self-consensus + RMVPE/FCPE + lyric evidence + local context + optional second opinion + render feedback，在 OpenUtau / DiffSinger 翻唱这一特定任务上优于单次 GAME raw。**

任务从：

```text
audio → 从零猜整首 MIDI
```

变成：

```text
GAME 给出绝大多数正确骨架
→ 识别 GAME 自身不稳定或与其他证据强冲突的局部
→ 只修少量 residual errors
```

---

# Part A — 总体主链路

## 3. 最终目标流程

```text
原曲
  ↓
解码 / 人声伴奏分离
  ↓
GAME raw 多次同配置推理
  ↓
正式 sequence alignment
  ↓
GAME stochastic consensus
  ↓
consensus note skeleton
  +
RMVPE raw/structural F0
  +
FCPE raw/structural F0
  +
LRC / Whisper lyric evidence
  ↓
Validator / Evidence Layer
  ↓
hard suspicious / ambiguous regions
  ↓
local repair candidates
  ↓
conservative scoring
  ↓
corrected melody
  ↓
lyrics ↔ melody mapping
  ↓
基础 USTX
  ↓
raw F0 → constrained PITD
  ↓
DiffSinger render
  ↓
reference / score / render 三层评价
```

第二阶段才增加：

```text
泠鸢本人歌曲
→ style analysis
→ style_profile.json
→ 滑音 / 颤音 / 换气 / 强弱 / 音色 / tension 等
```

---

## 4. 信息分工

### 4.1 GAME：乐谱骨架

GAME 负责：

- onset；
- offset / duration；
- note pitch；
- voiced/rest；
- note sequence。

GAME raw 永远保留为 Candidate 0。

单次 GAME 不能直接视为最终真值；同配置多次推理形成 consensus 后再作为主 baseline。

### 4.2 F0：证据 + 演唱轨迹

- RMVPE：主 F0 evidence；
- FCPE：第二独立 F0 opinion / fallback。

F0 用于：

- 验证 GAME pitch；
- 验证 octave；
- 验证 boundary；
- 发现 false/missed split candidate；
- 后续生成 PITD；
- 比较 rendered vocal 与 reference。

禁止恢复：

```text
char window → median F0 → note
```

作为主转谱逻辑。

### 4.3 Lyrics：歌词和 articulation evidence

LRC / Whisper 负责：

- 文本；
- word / char 时间；
- 乐句范围；
- 无歌词区间。

**char start 不是天然 note onset。**

Whisper timestamp、辅音开始、元音开始、F0 voiced onset、GAME note onset 必须区分。

歌词边界只用于：

```text
matching
weak snapping evidence
missing-boundary evidence
lyric-note mapping
```

不得直接强制生成 note boundary。

---

# Part B — GAME stochastic consensus

## 5. M2.1.2 已验证的事实

同一输入、同一参数，GAME ONNX 会产生 note-count / boundary /局部结构波动。

因此：

```text
single run != deterministic score
```

后续必须保存：

```text
model hash
input vocal hash
backend
sampling steps
boundary threshold
boundary radius
score threshold
language
run index
note count
```

第一版固定至少 5 runs。

---

## 6. 当前临时 consensus 实现的定位

当前 `diagnostic/consensus.py` 已实现：

- onset proximity clustering；
- `presence_rate`；
- `tone_agreement`；
- start/duration IQR；
- `structure_varies`；
- `GAME_STABLE / VARIABLE / UNSTABLE`。

当前临时匹配阈值：

```text
MATCH_TOL_S = 0.15
```

即 ±150 ms onset proximity。

该实现足以证明 GAME stochasticity 存在，也足以做 M2.1.2 诊断；**但不得直接作为最终自动 repair 的结构依据。**

原因：

1. 150 ms 对快速歌声 note 来说偏大；
2. onset-only proximity 可能把两个真实相邻短 note 混为同一个 event；
3. 当前 greedy clustering 具有 run-order dependency；
4. split/merge 不能只靠 midpoint-count 稳健判断；
5. 快速转音正是 repair 最敏感的区域。

---

# Part C — M2.2A：正式 Sequence Alignment

## 7. 为什么必须升级 consensus matching

目标不是“聚出差不多的事件”，而是明确识别：

```text
1 ↔ 1   same note
1 ↔ 0   missing in one run
0 ↔ 1   extra in one run
1 ↔ 2   split disagreement
2 ↔ 1   merge disagreement
```

例如：

```text
Run A:
A4 ─── B4 ── C5 ───── D5

Run B:
A4 ──────── C5 ───── D5
```

正式 alignment 应得到：

```text
A4 ↔ A4
B4 ↔ gap
C5 ↔ C5
D5 ↔ D5
```

而不是仅通过 150 ms 最近 onset 贪心匹配。

---

## 8. Sequence Alignment 设计

采用保持 note 顺序的 dynamic programming / sequence alignment。

匹配 cost 至少考虑：

```text
onset distance
时间 overlap
end / duration distance
weak pitch distance
voiced/rest compatibility
sequence order
```

建议把 pitch 只作为弱 cost：

> 不能因为 GAME 音高本身错了，就导致对应 note 无法匹配。

可定义：

```text
match_cost =
    w_onset   * onset_distance
  + w_overlap * overlap_penalty
  + w_dur     * duration_difference
  + w_pitch   * capped_pitch_difference
```

另外定义：

```text
gap_penalty
split_penalty
merge_penalty
```

第一版不必追求数学最优模型，但必须满足：

- 顺序不交叉；
- run permutation 不应改变最终 consensus；
- 快速相邻 notes 不被随意混并；
- split/merge 是显式关系，不是 midpoint heuristic 的副产物。

---

## 9. Consensus graph 输出

正式 consensus event 建议至少保存：

```json
{
  "start_median": 42.135,
  "start_iqr_ms": 18,
  "duration_median": 0.417,
  "duration_iqr_ms": 26,
  "tone_median": 69.08,
  "tone_agreement": 0.8,
  "presence_rate": 1.0,
  "structure": "1_to_1",
  "n_runs": 5
}
```

注意当前代码里的：

```text
tone_mode = median(tones)
```

命名不准确。

正式实现统一改为：

```text
tone_median
```

如果后续真的计算离散众数，再单独增加：

```text
tone_mode
```

---

## 10. Consensus 分类

继续保留：

```text
GAME_STABLE
GAME_VARIABLE
GAME_UNSTABLE
```

但分类必须基于正式 alignment 的结构关系，而不是单纯 onset cluster。

参考：

### GAME_STABLE

```text
5/5 presence
pitch 基本一致
boundary spread 小
结构 1↔1 稳定
```

### GAME_VARIABLE

```text
4/5 presence
或 boundary spread 中等
或轻微 pitch disagreement
```

### GAME_UNSTABLE

```text
<=3/5 presence
或显式 split/merge disagreement
或多个 pitch solution
```

阈值由《年轮》实测校准，不写成不可变常量。

---

# Part D — M2.2B：Dual-F0 Evidence

## 11. RMVPE + FCPE 必须同时进入 hard-suspicious 验证

当前最强 octave candidate：

```text
~189.84 s
GAME consensus tone ≈ 58.15
GAME presence = 5/5
RMVPE disagreement ≈ +1183 cents
RMVPE IQR ≈ 9 cents
```

GAME 的 pitch 结果在 5 次里高度稳定，但该区域同时存在一定 split/merge structure variance。

因此它不能只靠 RMVPE 直接自动修。

M2.2 必须加入 FCPE：

```text
GAME consensus
+
RMVPE
+
FCPE
+
正式 aligned note region
```

再判断。

---

## 12. 双 F0 比较字段

对每个 hard candidate 保存：

```text
RMVPE voiced coverage
FCPE voiced coverage
RMVPE stable center
FCPE stable center
RMVPE IQR cents
FCPE IQR cents
RMVPE vs FCPE cents
GAME vs RMVPE cents
GAME vs FCPE cents
transition timing agreement
```

### 双 F0 一致

如果：

```text
RMVPE → A4
FCPE  → A4
GAME  → A5
```

并且两个 F0 extractor 都稳定，则 octave repair 证据极强。

### 双 F0 冲突

例如：

```text
RMVPE → A4
FCPE  → A5
```

则：

```text
AMBIGUOUS
```

禁止 SAFE repair。

---

## 13. 189.84s 作为首个 benchmark case

必须生成一个独立 evidence packet，例如：

```json
{
  "region": [189.7, 190.4],
  "game": {
    "presence_rate": 1.0,
    "tone_median": 58.15,
    "structure_stability": "VARIABLE"
  },
  "rmvpe": {},
  "fcpe": {},
  "aligned_structure": {},
  "decision": "pending"
}
```

验收顺序：

1. 正式 sequence alignment 确认比较的是同一个 musical note；
2. RMVPE 稳定支持 octave correction；
3. FCPE 独立支持同一 correction；
4. 原音频局部试听支持；
5. repair 后单独 A/B render；
6. 确认没有把 split/merge 问题误当成 octave。

通过后它才成为：

> **第一个 SAFE octave-repair benchmark。**

---

# Part E — Structural F0 / Validator

## 14. Structural F0

当前已改为：

```text
raw F0
→ 仅填 <=40ms 短 unvoiced gap
→ 按连续 voiced island 独立 median filter
→ structural F0
```

长 silence 不参与相邻岛屿过滤。

职责：

- structural F0：note / boundary evidence；
- raw F0：PITD / vibrato / portamento / intonation。

所有对外 pitch error / dispersion 使用 cents。

---

## 15. `high_dispersion` 只能是 feature

实测：

```text
228 / 421 notes IQR > 60c
```

真人 vibrato / transition 很容易超过 60 cents。

因此：

```text
f0_iqr_cents
```

只保存为 feature。

禁止：

```text
IQR > X
→ suspicious
```

单条件触发。

---

## 16. Hard suspicious 使用组合证据

### Wrong pitch

例如：

```text
abs(GAME - stable F0) > 100c
AND voiced coverage 高
AND local F0 稳定
AND RMVPE/FCPE agree
```

### Octave

```text
error ≈ ±1200c
AND GAME note identity 已通过 sequence alignment
AND RMVPE/FCPE agree
AND stable voiced evidence
```

### Boundary

```text
GAME structure/boundary unstable
AND structural F0 changepoint stable
AND onset/energy evidence 支持
AND new duration plausible
```

---

## 17. Validator 输出分层

统一输出：

```text
healthy
feature_only
hard_suspicious
ambiguous
```

不要再以 feature 总数代表错误数量。

报告重点：

```text
hard_suspicious count
ambiguous count
confirmed error count
```

---

# Part F — Lyrics Evidence

## 18. Lyric boundary 继续 evidence-only

禁止：

```text
每个汉字 start → 强制 GAME boundary
```

当前《年轮》约：

```text
57 matched
265 possible_snap
1 possible_missing
26 unsupported
```

大量 80–300 ms 偏差必须先理解 timestamp 语义：

```text
Whisper char start
辅音起点
元音起点
F0 voiced onset
GAME note onset
```

只有：

```text
GAME boundary 不稳定
+
lyric articulation 支持
+
structural F0 支持
+
energy/onset 支持
```

才生成 boundary-shift / missing-boundary candidate。

---

# Part G — Residual Error Taxonomy

## 19. 只有 M2.2 完成后才统计真实 GAME residual errors

类型：

```text
wrong_pitch
octave_error
false_split
missed_split
boundary_shift
very_short_false_note
missing_note
weak_f0_evidence
lyric_alignment_conflict
ambiguous_ornament
```

报告必须严格区分：

```text
feature flags
hard suspicious
ambiguous
人工确认 error
```

不能再把 validator feature 数当 GAME error count。

---

# Part H — Repair Engine

## 20. Repair 原则

目标：

> **GAME 做绝大多数工作；我们只修少量 residual errors。**

永久保留：

```text
Candidate 0 = GAME baseline / consensus baseline
```

不得：

- 对整首重新生成 note；
- 没 evidence 就改；
- 为追求指标大面积重写 GAME；
- 把 F0 median 再变成主转谱器。

---

## 21. SAFE repair

第一批只实现已确认的强证据类型。

首个 benchmark：

```text
octave retune ±12 semitone
```

自动执行前至少要求：

```text
正式 sequence alignment 已确认 note identity
GAME consensus 已知
RMVPE 同意
FCPE 同意
稳定 voiced region
首个人工 A/B benchmark 通过
```

---

## 22. PROBABLE / AMBIGUOUS actions

### retune

明显 wrong pitch，要求双 F0 + context 支持。

### split / merge

只能由正式 sequence alignment 明确看到 1↔2 / 2↔1 disagreement 后，再结合 F0 / onset / lyric evidence。

### missed split

长 note 内多个稳定 structural F0 平台。

修 boundary 后优先让 GAME estimator 重新估 pitch。

### boundary shift

只在原 boundary 周围小窗口搜索。

### false / missing note

高风险，默认 PROBABLE / AMBIGUOUS。

---

## 23. Candidate Scorer

候选：

```text
C0 GAME baseline
C1 retune
C2 boundary shift
C3 split
C4 merge
C5 combined local repair
```

评分 evidence：

```text
GAME presence consensus
GAME pitch consensus
GAME structural stability
sequence-alignment relation
RMVPE agreement
FCPE agreement
structural F0 fit
voiced consistency
energy/onset evidence
lyric compatibility
duration plausibility
local melodic continuity
complexity penalty
unsupported edit penalty
```

必须设置 minimum improvement。

原则：

> **宁可保留 GAME 的小错误，也不要让 correction 制造新错误。**

---

## 24. 三级安全策略

### SAFE

- 双 F0 + aligned GAME evidence 强一致的 octave error；
- 极稳定 F0 下明显 wrong pitch；
- 已经过 benchmark 验证的简单错误。

### PROBABLE

- split；
- merge；
- 较大 boundary shift；
- false/missing note；
- 轻度 evidence conflict。

### AMBIGUOUS

- 快速复杂转音；
- 大 portamento；
- vibrato 与真实换音难区分；
- separation 差；
- GAME stochasticity 高；
- RMVPE/FCPE 冲突；
- 多候选接近。

不自动改，交 Agent review / 人工试听。

---

# Part I — Lyrics / USTX / PITD

## 25. Lyrics ↔ corrected melody

melody 稳定后再映射：

```text
1 char → 1 note
1 char → N notes (melisma)
N chars → N notes
```

OpenUtau：

```text
第一个 note：真实歌词
同字后续 note：+
换气：AP
静音：gap / SP
```

若冲突：

- 标记 `lyric_alignment_conflict`；
- 回查 alignment / GAME boundary；
- 不通过移动歌词到“最近 voiced block”伪修复。

---

## 26. 基础 USTX

第一阶段只含：

- corrected notes；
- lyrics；
- timing；
- singer / renderer；
- 必要 phonemizer 设置。

验收：

> **不做复杂风格调校，是否已经唱对《年轮》的旋律和节奏？**

---

## 27. raw F0 → constrained PITD

note 骨架通过后才做：

- portamento；
- 音头滑入；
- ornament；
- vibrato；
- intonation deviation。

PITD 不能掩盖 written-note 错误。

---

# Part J — Evaluation

## 28. Diagnostic level

至少记录：

- 每次 GAME run note count；
- sequence alignment statistics；
- 1↔1 / 1↔0 / 0↔1 / 1↔2 / 2↔1 数；
- consensus event count；
- GAME_STABLE / VARIABLE / UNSTABLE；
- hard suspicious / ambiguous；
- RMVPE/FCPE agreement；
- lyric evidence 分布；
- confirmed errors；
- validator false positive / false negative。

## 29. Score level

记录：

- corrected vs consensus baseline；
- retune；
- octave repair；
- split / merge；
- boundary shift；
- ambiguous；
- GAME preservation ratio。

## 30. F0 / Render level

比较：

```text
reference raw/structural F0
GAME consensus score
corrected score
rendered DiffSinger F0
```

区分：

- transcription error；
- lyric alignment error；
- PITD error；
- DiffSinger render deviation。

旧 per-note median cents 只作辅助，不能单独证明旋律正确。

---

# Part K — 实施顺序

## 31. Milestones

### M2.0 — Foundation survey ✅

- GAME/RMVPE 官方权重；
- OpenUtau backend；
- dataset-tools / SlurCutter 调研。

### M2.1 — Initial diagnostic ✅

A/B/C/D 初版完成；forced-boundary 曾导致错误解读。

### M2.1.1 — Diagnostic correctness ✅

已完成：

- cents 单位；
- time alignment；
- raw-first validator；
- lyric evidence-only；
- known-boundary init；
- forced C 降级；
- voiced-island structural F0。

### M2.1.2 — GAME stochastic baseline ✅

已完成：

- `diagnose --repeats N`；
- raw / zh 同配置多次运行；
- note-count variance；
- 临时 consensus events；
- STABLE / VARIABLE / UNSTABLE；
- raw-consensus vs zh-consensus；
- 189.84s candidate 的 5/5 GAME stability 验证。

当前结论：

```text
GAME 的主体旋律稳定
单次局部差异有明显 stochastic noise
自动 repair 不能依赖单次 GAME
```

### M2.2A — Formal sequence alignment ← 当前最高优先级

必须：

1. 替换 150 ms greedy onset clustering；
2. 实现顺序保持的 dynamic-programming alignment；
3. cost 使用 onset + overlap + duration + capped weak-pitch；
4. 显式识别 1↔1 / missing / extra / split / merge；
5. run 输入顺序不能影响 consensus；
6. `tone_mode` 更名 `tone_median`；
7. 用新 alignment 重新统计 STABLE / VARIABLE / UNSTABLE；
8. 重新检查 189.84s 的 note identity / split-merge structure。

**M2.2A 未完成前，不允许让 consensus 直接驱动自动 repair。**

### M2.2B — Dual-F0 evidence

必须：

1. 接入 FCPE；
2. 对 hard candidates 同时计算 RMVPE + FCPE；
3. 记录两个 extractor 的 stable center / IQR / voiced coverage；
4. 双模型一致才允许进入 SAFE repair；
5. 用 189.84s 做首个完整 benchmark；
6. 生成局部 before/after A/B render。

### M2.2C — Raw GAME residual error taxonomy

在 sequence alignment + dual-F0 完成后：

- 人工 + 程序确认真实错误；
- 统计 error distribution；
- 区分 feature / hard suspicious / ambiguous / confirmed error。

### M2.3 — Validator calibration

- high dispersion feature-only；
- hard suspicious 使用组合条件；
- 校准 false positive / false negative；
- 确认哪些 error type 值得自动修。

### M2.4 — SAFE repair

只实现《年轮》中已真实确认、证据强的错误类型。

首个目标：

```text
octave ±12 semitone
```

### M2.5 — PROBABLE candidate system

按真实需要实现：

- split；
- merge；
- missing / false note；
- scorer；
- minimum improvement gate。

### M2.6 — Optional second opinion

只有：

```text
GAME consensus
+
formal alignment
+
RMVPE
+
FCPE
+
lyric evidence
```

仍无法稳定判断大量 region 时，才接 ROSVOT。

### M2.7 — Lyrics mapping + base USTX

corrected score → lyrics/melisma → 可编辑工程。

### M2.8 — PITD + render loop

raw F0 → constrained PITD → DiffSinger → 三层评价。

### M2.9 — 《年轮》M2 验收

主要 A/B：

```text
GAME consensus baseline
vs
corrected
```

forced-boundary 只保留实验材料。

通过后冻结 melody score。

### M3 — 泠鸢风格迁移

只有 M2.9 通过后开始。

---

## 32. 第二阶段：泠鸢 style profile

使用泠鸢本人歌曲统计：

- vibrato rate/depth；
- portamento；
- 音头；
- 句尾；
- breath placement；
- dynamics；
- tension / breathiness；
- voice color；
- 音区差异。

形成：

```text
style_profile.json
```

原则：

> **原唱决定“唱什么”；泠鸢参考决定“怎么唱”。**

style layer 不应无理由修改已经冻结的 melody skeleton。

---

## 33. 最终原则

1. **GAME raw / GAME consensus 是主旋律 baseline。**
2. **单次 GAME 输出不是绝对确定结果。**
3. **M2.1.2 已证明 GAME 存在真实 stochasticity。**
4. **当前 150 ms greedy consensus 只用于诊断，不得直接驱动 repair。**
5. **正式 consensus 必须来自顺序保持的 sequence alignment。**
6. **split/merge 必须是 alignment 的显式结构关系。**
7. **RMVPE + FCPE 是双独立 F0 证据，不是主转谱器。**
8. **双 F0 不一致时禁止 SAFE repair。**
9. **high dispersion 是 feature，不是错误本身。**
10. **歌词字符边界只用于 matching/snapping/evidence。**
11. **structural F0 按 voiced islands 处理。**
12. **所有 pitch error / dispersion 对外统一 cents。**
13. **自动 repair 只针对 hard suspicious residual errors。**
14. **GAME baseline 永远保留为 Candidate 0 / 回退基线。**
15. **189.84s 是首个 octave-repair benchmark，不是在验证完成前直接自动修。**
16. **只实现真实出现且值得修的错误类型。**
17. **复杂区域宁可 needs_review，不强行自动修。**
18. **先把 note 骨架唱对，再生成 PITD。**
19. **先“唱对”，再做泠鸢风格。**
20. **所有自动修改必须可解释、可审计、可 A/B、可回退。**
