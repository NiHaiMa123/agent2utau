# agent2utau — Plan 2：GAME 主转谱 + 证据驱动校正 + 分阶段演唱建模

> 修订日期：2026-09-16
>
> 核心原则：**先把“唱对”解决，再把“唱得像泠鸢”解决。**
>
> 当前最重要的工程原则：**GAME raw 是主 baseline；先把 diagnostic 做正确，再统计 GAME 真实错误，再决定 repair。歌词边界和 F0 都是证据，不直接替代 GAME。**

---

## 1. 当前状态

旧 pipeline 已经具备：

- 原曲解码与人声/伴奏分离；
- FCPE F0；
- LRC + Whisper attention/DTW 歌词对齐；
- USTX 构建；
- OpenUtau headless bridge；
- DiffSinger 自动渲染；
- 混音与基础评价。

旧主旋律生成方式：

```text
歌词字窗口
→ F0 中位数
→ heuristic split
→ MIDI note
```

能力不足，降级为 fallback，不再作为默认 melody transcription。

### 1.1 Plan2 已完成的 M2.0 / M2.1

当前仓库已经真正接入：

- 官方 GAME 1.0.3-medium ONNX 权重；
- 官方 RMVPE ONNX 权重；
- GAME `encoder → segmenter → bd2dur → estimator` 推理链；
- OpenUtau AudioSlicer 等价切片；
- RMVPE 16 kHz / hop 160 推理；
- `diagnose` 命令；
- GAME USTX + DiffSinger render；
- RMVPE overlay 与 suspicious-region 初版诊断。

《年轮》第一轮结果：

```text
Variant A — GAME raw:        419 voiced notes
Variant B — GAME + zh:       417 voiced notes
Variant C — forced char bd:  760 voiced notes
```

初版 C validator 标记：

```text
76 suspicious
54 wrong_pitch
16 very_short
8 weak_f0
```

**这些数字目前不能解释成 GAME raw 真有 76 个错误。**

原因是 suspicious 检测跑在 Variant C 上，而 C 把约 349 个 Whisper/歌词字符起点直接作为 `known_boundaries` 强制加入 GAME，note 数从约 417 翻到 760。它更像“原 GAME boundaries + 大量强制字符边界”，不是我们希望的“用歌词证据把 GAME 边界修准”。

因此自动 repair 暂停，先进入 **M2.1.1 Diagnostic Correctness**。

---

## 2. 项目定位

GAME 是专门的 singing voice transcription 模型，但真人歌声到离散 note 本身存在模糊性：

- vibrato 是 note 内 modulation 还是多个 note；
- portamento 什么时候算真正换音；
- appoggiatura / grace note 是否单独记谱；
- 极短经过音是否写进 MIDI；
- 辅音、气声、分离残留是否形成假 boundary；
- octave ambiguity；
- onset / offset 本身有几十毫秒不确定性。

所以项目不尝试训练一个“总体超过 GAME 的通用转谱器”。

目标是：

> **GAME + RMVPE/F0 + 歌词边界 + 局部上下文 + 可选 second opinion + DiffSinger render feedback，在 OpenUtau 翻唱这个特定任务上优于 GAME raw。**

即：

```text
GAME 给出大部分正确答案
→ 找少量 suspicious region
→ 用额外证据判断
→ 只修强证据错误
```

---

## 3. 优先复用现有基座

### 3.1 OpenVPI dataset-tools

优先参考/复用：

- GAME inference；
- RMVPE；
- SlurCutter；
- DiffSinger 数据处理结构。

参考：

- https://github.com/openvpi/dataset-tools
- https://github.com/openvpi/GAME

其天然工作流就是：

```text
GAME → note skeleton
RMVPE → continuous pitch evidence
SlurCutter → MIDI refinement
```

### 3.2 SlurCutter

把人工修谱动作定义为 repair action：

```text
retune
split
merge
boundary_shift
delete_false_note
insert_missing_note
```

目标不是重新设计整套 MIDI，而是尽量自动化“人看 F0 修 GAME”的过程。

### 3.3 HachiTune

可借鉴其：

```text
GAME segmentation + RMVPE/FCPE + piano-roll/pitch editor
```

默认只参考架构和交互，不直接复制代码。

### 3.4 ROSVOT

仅作为可选 second opinion / disagreement detector。

第一阶段不要求接入。只有 GAME + RMVPE 仍无法稳定判断大量 region 时再增加。

---

# Part A — 主链路

## 4. 最终主流程

```text
原曲
  ↓
解码 / 人声伴奏分离
  ↓
GAME raw
  ↓
主旋律 note skeleton
  +
RMVPE / FCPE raw F0
  +
structural F0
  +
LRC / Whisper lyric boundaries
  ↓
Validator / Evidence Layer
  ↓
suspicious regions
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

## 5. 信息分工

### 5.1 GAME：乐谱骨架

默认 source of truth candidate：

- note onset；
- note offset / duration；
- note pitch；
- voiced/rest；
- note sequence。

GAME 不是绝对真值，但默认优先于自制 heuristic。

### 5.2 F0：证据 + 演唱轨迹

RMVPE 为主要 F0 evidence，FCPE 作为 A/B/fallback。

F0 用于：

- 验证 GAME pitch；
- 验证 boundary；
- 发现 octave 异常；
- 发现可能 false/missed split；
- 后续生成 PITD；
- 比较 render 与 reference。

禁止恢复：

```text
char window → median F0 → note
```

作为主转谱器。

### 5.3 Lyrics：歌词与时间证据

LRC / Whisper 负责：

- 文本；
- word/char 时间；
- 乐句范围；
- 间奏与无歌词区。

**歌词字符起点不是天然 note boundary。**

歌词边界默认只作为 evidence / matching / snapping 的依据，不直接强制新增 GAME boundary。

---

# Part B — M2.1.1：先修正 Diagnostic

## 6. 当前 Variant C 的定位调整

原设计：

```text
Variant C = GAME + 所有 char known_boundaries
```

第一轮《年轮》：

```text
A 419
B 417
C 760
```

C 几乎把所有字符起点都变成额外 boundary，因此 C 不再作为默认主候选。

新的定位：

- **A / GAME raw：主 baseline；**
- B / language=zh：辅助实验；
- C / forced known boundaries：仅用于研究 GAME `known_boundaries` 行为；
- D / GAME raw + RMVPE：主要诊断路径；
- E / GAME raw + lyric-boundary overlay：歌词只叠加、不强制修改 note。

自动 repair 之前，所有 suspicious 统计必须首先针对 **A/raw**。

---

## 7. Diagnostic 必修的四个问题

### 7.1 修正 `high_dispersion` 单位

当前 structural F0 使用 MIDI semitone 单位，若写：

```python
IQR > 60
```

实际含义是 60 semitones，而不是 60 cents。

应统一为 cents，例如：

```text
f0_iqr_cents = midi_iqr * 100
```

再与 60 cents 等阈值比较。

诊断字段必须明确单位，避免 `midi / semitone / cents` 混用。

### 7.2 A/B/C 比较禁止按 note index `zip`

A=419、C=760 时，C 只要前面插入一个 note，后续 index 全部错位。

因此 variant 比较必须基于：

```text
time overlap
boundary matching
sequence alignment
```

而不是：

```text
note[i] vs note[i]
```

至少输出：

- matched notes；
- inserted boundaries；
- deleted boundaries；
- pitch disagreement on matched regions；
- onset/offset drift。

### 7.3 structural F0 只允许插值短 unvoiced gap

当前不能让长静音在滤波前被 `np.interp` 跨越。

例如：

```text
A4 ---- [800ms silence] ---- B4
```

不能先伪造一条 A4→B4 连续坡线再 median filter。

只允许填补短 gap，例如初始实验：

```text
<= 30–50 ms
```

具体阈值以后按诊断调。

长 gap 保持 NaN / unvoiced。

### 7.4 known_boundaries 路径必须严格核对 GAME ONNX 规范

当使用 `known_boundaries` 时，D3PM 第一个 sampling step 的初始化必须与官方规范/官方实现一致。

尤其核对：

```text
known_boundaries
prev_boundaries initial value
sampling loop
threshold
radius
```

Variant C 只有在这条路径通过与官方 GAME/OpenUtau 的一致性测试后，才能用于算法结论。

---

## 8. 新的 Diagnostic Experiment

### Variant A — GAME raw

```text
vocal.wav → GAME default
```

这是核心 baseline。

必须为 A 直接生成：

- `game_raw.json`；
- `game_raw.ustx`；
- vocal render；
- RMVPE overlay；
- suspicious regions；
- evidence packets。

### Variant B — GAME + zh

保留用于确认 language conditioning 的实际影响。

当前《年轮》 A=419 / B=417，说明 zh 条件对 note 数影响很小，但仍保留数据。

### Variant C — forced known boundaries

只作为研究实验。

不参与默认 melody selection，也不把其 suspicious 数当 GAME error rate。

重点回答：

- known boundary 是替换、吸附还是强制新增？
- 距离已有 GAME boundary 很近时会发生什么？
- 对 estimator 与 note count 有什么影响？

### Variant D — GAME raw + RMVPE overlay

这是新的主要 validation baseline。

不改 GAME notes，只输出：

```text
GAME note rectangles
RMVPE raw F0
structural F0
voiced mask
```

### Variant E — GAME raw + lyric-boundary overlay

歌词边界只显示/参与 evidence，不强制进入 GAME。

对每个 lyric boundary 做 nearest-GAME-boundary matching：

```text
lyric boundary
     |
     | distance Δt
     ↓
nearest GAME boundary
```

根据距离 + F0 + energy/onset 分成：

```text
matched
possible_snap
possible_missing_boundary
unsupported_lyric_boundary
```

---

## 9. 歌词边界的正确用途：matching / snapping / missing-boundary evidence

不要：

```text
每个汉字开始时间 → 强制插入 GAME boundary
```

优先：

```text
GAME boundary 12.52s
lyrics boundary 12.57s
Δt = 50ms
→ match
→ boundary confidence increase
→ 必要时产生 snap candidate
```

只有同时满足多种证据时，歌词 boundary 才能支持“新增 note boundary”：

- 与最近 GAME boundary 距离明显较远；
- structural F0 出现真实稳定平台变化；
- voiced/energy/onset 支持；
- lyric articulation 支持；
- 插入后 note duration 合理。

否则只记录，不插入。

---

## 10. M2.1.1 输出物

```text
runs/<id>/diagnostic/
  game_raw.json
  game_raw.ustx
  game_raw_vocal.wav

  game_zh.json

  game_forced_boundaries.json        # experimental only
  game_forced_boundaries.ustx

  rmvpe_f0.npz
  structural_f0.npz

  raw_evidence_packets.json
  raw_suspicious_regions.json
  lyric_boundary_matches.json
  variant_alignment.json
  diagnostic_report.md
```

报告必须明确分开：

```text
GAME raw suspicious
forced-boundary suspicious
```

禁止再把二者混成 GAME error count。

---

# Part C — Error Taxonomy / Evidence Layer

## 11. 先统计 GAME raw 真实错误

对 A/raw 419 notes 建 taxonomy：

```text
wrong_pitch
possible_octave_error
false_split
missed_split
boundary_shift
very_short_isolated_note
false_note
missing_note
weak_f0_evidence
lyric_alignment_conflict
ambiguous_ornament
```

报告必须回答：

```text
raw note 总数
healthy 数
suspicious 数
人工确认错误 region 数
各错误类型数量/比例
RMVPE 是否支持该判断
歌词边界是否支持该判断
```

**只有这个阶段完成，才能决定 Repair Engine 优先级。**

---

## 12. raw F0 与 structural F0

保留两条 pitch representation：

```text
raw F0
→ 去毛刺 + 仅填短 gap + segmentation-friendly smoothing
→ structural F0
```

职责：

- structural F0：note pitch / boundary / split-merge evidence；
- raw F0：PITD / vibrato / portamento / intonation。

structural F0 不能通过重度低通抹掉真实换音，也不能跨长 unvoiced 区插值。

每帧统一保存单位：

```json
{
  "time": 42.150,
  "raw_midi": 69.34,
  "structural_midi": 69.02,
  "voiced": true,
  "energy": 0.073
}
```

所有 dispersion / error 指标对外统一使用 cents。

---

## 13. Validator

Validator 只发现问题，不直接修改。

每个 GAME raw note 至少计算：

- tone；
- duration；
- stable F0 center；
- voiced coverage；
- F0 IQR cents；
- GAME vs F0 cents；
- left/right boundary F0 change；
- voiced/unvoiced transition；
- energy/onset evidence；
- lyric boundary distance；
- 前后 interval；
- optional GAME consensus；
- optional second-model agreement。

输出：

```text
healthy
suspicious
ambiguous
```

并保存 evidence packet。

---

# Part D — Repair Engine（诊断正确后再实现）

## 14. Repair 原则

目标：

> **保留 GAME 正确的绝大多数 note，只修少量强证据错误。**

永久保留：

```text
Candidate 0 = GAME raw
```

不得：

- 对整首重新生成 note；
- 没 evidence 就修改；
- 为追求分数大面积重写 GAME；
- 把 F0 median 再变成主转谱器。

### 14.1 retune

用于明显 wrong pitch。

必须结合：

- 高 voiced coverage；
- 稳定 F0 platform；
- 较低 dispersion；
- 明显 cents disagreement；
- 排除 vibrato/portamento；
- 邻接上下文不冲突。

### 14.2 octave repair

优先检查 ±12 semitone。

满足：

- octave 修正后 RMVPE 显著更匹配；
- 前后音域连续；
- 没有真实大跳证据；

可作为首批 SAFE repair。

### 14.3 false split / merge

不能因为相邻同音就 merge。

必须证明 GAME boundary 缺乏：

- F0 changepoint；
- energy/onset；
- voiced transition；
- lyric articulation；
- GAME consensus。

### 14.4 missed split

长 note 内若出现多个持续稳定 structural F0 平台，产生 split candidate。

修 boundary 后优先让 GAME estimator 重新估 pitch；只有接口无法使用时才由 structural F0 产生候选 tone。

### 14.5 boundary shift

note 数和 pitch 正确但换音点偏移时，只在原 boundary 周围小窗口搜索。

歌词 boundary 可参与 snap evidence，但不能单独决定位置。

### 14.6 false / missing note

风险较高，默认 PROBABLE / AMBIGUOUS。

---

## 15. Candidate Scorer

每个 region 可能有：

```text
C0 GAME raw
C1 retune
C2 boundary shift
C3 split
C4 merge
C5 combined local repair
```

评分证据：

```text
pitch_fit
boundary_fit
voiced_consistency
energy/onset evidence
lyric compatibility
duration plausibility
GAME prior
GAME consensus
optional second model
local melodic continuity
complexity penalty
unsupported edit penalty
```

必须设置 minimum improvement：

```text
C0 0.88 vs C1 0.90 → 不改
C0 0.58 vs C1 0.93 → 可接受
```

原则：**宁可保留 GAME 的小错误，也不要让 correction 制造新错误。**

---

## 16. 三级安全策略

### SAFE

可自动接受，但必须 audit：

- 高置信 octave error；
- 极稳定 F0 下明显 wrong pitch；
- 经过真实数据验证的简单 false split；
- 小范围 boundary snap，且多证据一致。

### PROBABLE

生成多候选，只有显著优于 C0 才接受：

- split；
- merge；
- 较大 boundary shift；
- false/missing note；
- 部分证据冲突。

### AMBIGUOUS

不自动改：

- 快速复杂转音；
- 大 portamento；
- vibrato 与真实换音难区分；
- 分离质量差；
- GAME 多配置不稳定；
- F0 extractor 冲突；
- 多候选接近。

交给 Agent review / 人工试听。

---

# Part E — Lyrics / USTX / PITD

## 17. Lyrics ↔ corrected melody

在 corrected melody 稳定以后才正式做歌词映射：

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

若歌词与 melody 严重冲突：

- 标 `lyric_alignment_conflict`；
- 回查歌词 alignment / GAME boundary；
- 不通过把歌词移动到“最近 voiced block”来伪修复。

---

## 18. 基础 USTX

第一阶段只含：

- corrected notes；
- lyrics；
- timing；
- singer / renderer；
- phonemizer 必要设置。

此时核心验收只有一个：

> **不做复杂风格调校，是否已经在唱正确的《年轮》旋律？**

若否，不能进入 style 阶段。

---

## 19. raw F0 → constrained PITD

note 骨架通过后，raw F0 才用于：

- portamento；
- 音头滑入；
- ornament；
- vibrato；
- intonation deviation。

原则：

- 不逐帧硬拷 F0；
- 去 extractor 毛刺；
- PITD 围绕 corrected written note；
- 不能用 PITD 掩盖错误 written note；
- note 与 PITD 分开评价。

---

# Part F — Evaluation

## 20. Diagnostic level

至少记录：

- GAME raw note count；
- raw healthy / suspicious / ambiguous；
- zh variant note count；
- forced-boundary variant note count；
- lyric boundary matched / snap / missing candidates；
-人工确认错误数；
-各 error type；
- validator false-positive / false-negative 情况。

### Variant comparison

所有不同 note-count 序列必须使用时间/序列对齐，不允许 index zip。

---

## 21. Score level

记录：

- corrected vs raw note count；
- retune；
- octave repair；
- split / merge；
- boundary shift；
- ambiguous；
- GAME preservation ratio。

GAME preservation ratio 应尽量高。

---

## 22. F0 / Render level

比较：

```text
reference raw/structural F0
GAME raw score
corrected score
rendered DiffSinger F0
```

区分：

- transcription error；
- lyric alignment error；
- PITD error；
- DiffSinger render deviation。

旧 per-note median cents 可保留，但不能单独证明旋律正确。

---

# Part G — 实施顺序

## 23. Milestones

### M2.0 — Foundation survey ✅

- GAME/RMVPE 官方权重；
- OpenUtau backend；
- dataset-tools / SlurCutter 调研。

### M2.1 — Initial diagnostic ✅，但结论待修正

已完成 A/B/C/D 初版。

已确认：

```text
A=419
B=417
C=760
```

C 强制字符边界过于激进，C suspicious 不能代表 GAME raw 错误率。

### M2.1.1 — Diagnostic correctness ← 当前最高优先级

必须完成：

1. 修 high-dispersion 单位；
2. 修 variant time/sequence alignment；
3. structural F0 只填短 gap；
4. 核对 known-boundary D3PM 初始化与官方规范；
5. suspicious 检测改为首先跑在 GAME raw；
6. 新增 lyric-boundary overlay/matching，不强制插入；
7. 重新跑《年轮》完整诊断。

**M2.1.1 未通过前禁止开始自动 repair。**

### M2.2 — Raw GAME error taxonomy

人工 + 程序联合确认：

- GAME raw 实际错多少；
- 错误类型；
- 哪些是 separation / RMVPE / lyric alignment 假象；
- 哪些值得自动修。

### M2.3 — Validator calibration

- 调 suspicious thresholds；
- 测 false positive；
- 建 evidence packet；
- 仍不修改 note。

### M2.4 — SAFE repair

只实现《年轮》中真实高频、强证据错误。

### M2.5 — PROBABLE candidate system

只在实际需要时实现 split / merge / missing note 等复杂动作。

### M2.6 — Optional second opinion

只有 GAME + RMVPE + lyric evidence 仍不足时再接 ROSVOT。

### M2.7 — Lyrics mapping + base USTX

corrected score → lyrics/melisma → 可编辑工程。

### M2.8 — PITD + render loop

raw F0 → constrained PITD → DiffSinger → 三层评价。

### M2.9 — 《年轮》M2 验收

主要 A/B：

```text
GAME raw
vs
corrected
```

forced-boundary 版本只作为实验材料，不再作为默认最终候选。

通过后冻结 melody score。

### M3 — 泠鸢风格迁移

只有 M2.9 通过后开始。

---

## 24. 第二阶段：泠鸢 style profile

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

## 25. 最终原则

1. **GAME raw 是默认主旋律 baseline。**
2. **先保证 diagnostic 本身正确，再讨论 GAME 错误率。**
3. **当前 C=760 的 forced-char-boundary 路径只保留为实验，不做默认主链。**
4. **RMVPE/F0 是证据与演唱轨迹，不是从零主转谱器。**
5. **歌词字符边界默认用于 matching/snapping/evidence，不直接强制生成 note boundary。**
6. **不同 note-count 序列必须按时间/序列对齐，禁止 index zip 比较。**
7. **structural F0 不跨长 unvoiced gap 插值。**
8. **所有 pitch dispersion/error 单位必须明确并统一为 cents。**
9. **known-boundaries GAME 路径必须先与官方 ONNX 行为一致。**
10. **自动 repair 只针对 GAME raw 的真实 suspicious regions。**
11. **GAME raw 永远保留为 Candidate 0 / 回退基线。**
12. **只实现真实出现且值得修的错误类型。**
13. **复杂区域宁可 needs_review，不强行自动修。**
14. **先把 note 骨架唱对，再生成 PITD。**
15. **先“唱对”，再做泠鸢风格。**
16. **所有自动修改必须可解释、可审计、可 A/B、可回退。**
