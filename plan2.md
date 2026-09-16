# agent2utau — Plan 2：以 GAME 为主转谱器的诊断、校正与分阶段演唱建模

> 修订日期：2026-09-16
>
> 本计划替代当前“歌词字窗口 → F0 中位数 → heuristic split → note”的主旋律生成思路。
>
> 核心原则：**先把“唱对”解决，再把“唱得像泠鸢”解决。**
>
> 新增的首要原则：**先测清 GAME 到底错在哪里，再决定自动纠错层需要做多复杂。不要预设错误分布后直接写一套 repair engine。**

---

## 1. 当前问题与 Plan 2 的目标

当前 pipeline 已经完成并验证了大量基础设施：

- 原曲解码与人声/伴奏分离；
- FCPE F0 提取；
- LRC 与 Whisper attention/DTW 逐字对齐；
- USTX 生成；
- OpenUtau headless bridge；
- DiffSinger 自动渲染；
- 混音、电平匹配与基础评价；
- OpenUtau note/phoneme 错误检查。

这些能力保留。

当前真正不可用的是**主旋律 note transcription**。

现有 `analysis/notes.py` 的核心逻辑是：

1. 先由歌词系统确定每个字的时间窗；
2. 在字窗口里取 F0 中位数；
3. 四舍五入到最近的 MIDI note；
4. 只有检测到持续一定时间、跨过一定半音阈值的变化时，才把一个字拆成多个音符。

这不是完整的 singing voice transcription。它容易把滑音、倚音、快速转音、真实换音位置、颤音与换音等处理错误。

因此：

- **GAME 成为默认主 melody transcription backend**；
- 现有 heuristic note builder 只保留为 fallback；
- F0 不再从零生成整首乐谱；
- 自动纠错只针对 GAME 的局部错误；
- 在写复杂 repair 前，先对 GAME 做系统诊断。

第一阶段只解决：

- 歌词正确；
- note 骨架正确；
- 时值和边界基本正确；
- 旋律与原唱一致；
- OpenUtau 可稳定渲染。

第二阶段才处理：

- 泠鸢的滑音；
- 颤音；
- 换气；
- 句内强弱；
- 音色选择；
- tension / breathiness 等表现参数。

---

## 2. 为什么 GAME 仍然会出错，以及我们的定位

GAME 是专门的 singing voice transcription 模型，但“真人歌声 → 离散 note”本身不是完全确定的问题。

例如：

```text
A4 ─────↗ B4
```

可以解释成：

```text
A4 一个 note + pitch curve 滑向 B4
```

也可能在某种标注规范下写成：

```text
A4 | B4
```

类似问题还包括：

- vibrato 是否属于一个 note 内的 pitch modulation；
- appoggiatura / grace note 是否应单独拆 note；
- portamento 什么时候算真正换音；
- 极短经过音是否写进 MIDI；
- 辅音、气声、分离残留造成的假 boundary；
- octave ambiguity；
- note onset / offset 本身存在几十毫秒的模糊区间。

因此 GAME 有少量：

- wrong pitch；
- octave error；
- false split；
- missed split；
- boundary shift；

属于预期能力边界，而不代表模型整体不可用。

### 2.1 我们不与 GAME 正面对打

本项目不以“训练一个总体转谱能力超过 GAME 的新模型”为目标。

我们的目标是：

> **GAME + 额外证据 + 局部校正 > 原始 GAME，在 OpenUtau / DiffSinger 翻唱这一特定任务上。**

我们比一个通用转谱器多掌握：

- GAME 自己的 prediction；
- RMVPE / FCPE continuous F0；
- 歌词文本；
- Whisper/LRC word/char boundaries；
- 相邻乐句上下文；
- OpenUtau 最终表示方式；
- 可选第二转谱模型的意见；
- 最终 DiffSinger render 的反馈。

所以任务从：

```text
audio → 从零猜整首 MIDI
```

变为：

```text
GAME 已给出大部分正确答案
→ 找出少量可疑区域
→ 判断是否有足够证据修改
```

这是难度完全不同的问题。

---

## 3. 优先复用现有基座，不从零造轮子

### 3.1 第一优先：OpenVPI dataset-tools

优先调查并复用 OpenVPI 自己的 `dataset-tools`：

- GAME inference；
- RMVPE；
- SlurCutter；
- DiffSinger 数据处理相关结构。

参考：

- https://github.com/openvpi/dataset-tools
- https://github.com/openvpi/GAME

这套工具链与我们的目标天然接近：

```text
GAME → note skeleton
RMVPE → continuous pitch evidence
SlurCutter → MIDI refinement
```

优先研究它的现有 executable / DLL / model/runtime 调用方式，避免重复实现推理后端。

### 3.2 SlurCutter：把“人工修谱动作”作为 repair action 定义

SlurCutter 已经把人工修谱归纳为非常接近我们需要的基本操作：

- 调整 note pitch；
- split note；
- merge slur / note；
- 调整边界。

因此我们的自动纠错层可以理解为：

> **把 SlurCutter 中人看着 F0 做的判断，尽可能自动化。**

Repair action 先限制为：

```text
retune
split
merge
boundary_shift
delete_false_note
insert_missing_note
```

不要一开始发明更多复杂编辑动作。

### 3.3 HachiTune：架构参考，不默认复制代码

HachiTune 已经采用类似：

```text
GAME note segmentation
+
RMVPE / FCPE pitch
+
piano roll / pitch curve editing
```

可用于参考 GAME 与 F0 如何同时展示和交互。

项目：

- https://github.com/KCKT0112/HachiTune

许可证要求与本项目不同，默认只作为架构参考，不直接拷贝实现，除非后续明确确认许可证兼容性。

### 3.4 ROSVOT：可选 second opinion

ROSVOT 可作为第二个 singing voice transcription backend，用于**分歧检测**，不是默认替代 GAME。

目标：

```text
GAME
   \
    → agreement / disagreement → validator
   /
ROSVOT

+
RMVPE structural F0
```

如果多个证据一致，置信度提高；如果 GAME 与 second opinion 明显冲突，则把该局部标记为 suspicious。

第一版不要求必须接入 ROSVOT。只有 GAME + F0 无法稳定判断的错误比例较高时才加入。

### 3.5 其他项目/论文

VOCANO 等“pitch extraction + note segmentation”路线可作为算法参考，但不作为默认主 backend。

核心思想只借鉴：

> **continuous pitch estimation 与 discrete note segmentation 应是两个不同问题。**

---

## 4. 总体架构

第一阶段目标流程：

```text
原曲
  ↓
解码 / 人声伴奏分离
  ↓
┌──────────────────────────────┐
│ GAME：主旋律 note 骨架      │
│ onset / offset / tone        │
└──────────────────────────────┘
  +
┌──────────────────────────────┐
│ RMVPE / FCPE：F0 证据        │
│ raw F0 + structural F0       │
└──────────────────────────────┘
  +
┌──────────────────────────────┐
│ LRC / Whisper：歌词边界      │
└──────────────────────────────┘
  ↓
Diagnostic / Validator
  ↓
suspicious regions
  ↓
局部 repair candidates
  ↓
conservative scoring
  ↓
corrected melody notes
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

第二阶段：

```text
泠鸢本人歌曲
  ↓
style analysis
  ↓
style_profile.json
  ↓
在已正确 melody 上做风格化调校
```

---

## 5. 三类信息必须严格分工

### 5.1 GAME：负责“乐谱骨架”

GAME 输出作为主乐谱假设：

- note onset；
- note offset / duration；
- note pitch；
- note sequence；
- 可取得时保存 boundary probability / threshold / intermediate 信息。

GAME 不是绝对真值，但默认比我们自己的 heuristic 更可信。

### 5.2 F0：负责“证据”和“演唱轨迹”

优先 RMVPE；现有已修正 FCPE 可作为 A/B 与 fallback。

F0 用途：

- 验证 GAME pitch；
- 验证 boundary；
- 找 octave 异常；
- 检测漏拆 / 多拆候选；
- 构造 PITD；
- 对比 reference 与 rendered vocal。

禁止恢复为：

```text
lyrics char window → median F0 → note
```

作为主转谱逻辑。

### 5.3 Lyrics：负责“唱哪个字”

LRC / Whisper DTW 负责：

- 歌词文本；
- word / char 时间；
- 乐句边界；
- 间奏 / 无歌词区域。

歌词边界不再直接决定 note 数和 note pitch。

例如 GAME：

```text
A4 → B4 → C5 → B4
```

若都属于“轮”：

```text
轮  +  +  +
```

---

# Part A：先诊断 GAME，不急着自动修

## 6. M2.1 必须先做 diagnostic experiment

这是 Plan 2 的第一实施任务。

**在任何复杂 repair engine 开发前，先跑《年轮》的 GAME 基线实验。**

目的：

> 先回答“GAME 在我们的实际输入上到底哪里会错、错多少、错误类型是什么”。

### 6.1 对同一个分离后 vocal 跑至少四套结果

#### Variant A — GAME raw

```text
vocal.wav → GAME default
```

不提供歌词边界，不做额外后处理。

#### Variant B — GAME + language/context

如果当前 GAME backend 支持 language / locale / singing language 条件，则明确使用中文配置。

若该版本不支持，报告中明确写 `unsupported`，不能伪造差异。

#### Variant C — GAME + known word boundaries

使用现有：

```text
LRC + Whisper attention/DTW
```

得到的 word / syllable boundaries 作为 side information，调用 GAME 支持的 known-boundary / alignment 能力。

这是非常重要的一版，因为我们本来就掌握歌词时间。

#### Variant D — Variant C + RMVPE overlay

不修改 GAME note，只把 RMVPE continuous F0 叠加到 GAME note 上，生成诊断数据。

目标不是自动修，而是可视化：

```text
GAME note rectangles
RMVPE pitch trace
lyrics boundaries
```

### 6.2 第一轮禁止自动 repair

M2.1 只允许：

- 转谱；
- 诊断；
- 比较；
- 标记 suspicious；
- 生成人工试听/检查材料。

禁止：

- 自动 retune；
- 自动 split；
- 自动 merge；
- 自动 boundary shift。

原因：我们先需要真实误差分布。

### 6.3 输出物

至少保存：

```text
runs/<id>/diagnostic/
  game_raw.json
  game_raw.ustx
  game_word_boundaries.json
  game_word_boundaries.ustx
  rmvpe_f0.npz
  structural_f0.npz
  overlay.json
  suspicious_regions.json
  diagnostic_report.md
```

如果方便，再导出：

```text
GAME raw vocal render
GAME + boundaries vocal render
```

用于直接 A/B。

---

## 7. 先建立真实 error taxonomy

在《年轮》诊断中，对 GAME 真实错误逐项归类。

预定义类别可以有：

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
```

但不要假设每类都会大量发生。

诊断报告必须回答：

```text
总 note 数
明显正确 note 数
可疑 note / region 数
人工确认错误 region 数
各 error type 数量
各类型占比
word boundaries 是否改善
GAME 参数变化是否影响结果
```

例如最终可能得到：

```text
500 notes
462 acceptable
38 suspicious

confirmed errors:
15 octave/wrong pitch
8 false split
7 boundary shift
5 missed split
3 complex/ambiguous
```

也可能完全不是这个分布。

**只有看到真实分布后，才确定 repair engine 的优先级。**

---

# Part B：Evidence Layer

## 8. F0 双层表示：raw F0 与 structural F0

raw F0 包含：

- vibrato；
- portamento；
- 音头滑入；
- 尾音；
- 倚音；
- intonation deviation；
- extractor 毛刺。

如果直接用 raw F0 判断 split，会把“怎么唱”误认为“唱了几个音”。

因此保存：

```text
raw_f0
  ↓
去毛刺 / 稳定区提取 / segmentation-friendly smoothing
  ↓
structural_f0
```

职责：

- `structural_f0`：用于 note/boundary validation；
- `raw_f0`：用于后续 PITD 与演唱表现。

structural F0 不能只是强低通；必须尽量保留真正换音平台，同时压制 vibrato half-cycle 和短时毛刺。

建议每帧保存：

```json
{
  "time": 42.150,
  "raw_midi": 69.34,
  "structural_midi": 69.02,
  "voiced": true,
  "energy": 0.073
}
```

---

## 9. Validator：只发现问题，不直接修改

GAME 输出后，对每个 note 和 boundary 建 evidence packet。

至少计算：

- GAME tone；
- GAME duration；
- structural F0 stable center；
- voiced coverage；
- pitch dispersion / IQR；
- GAME vs F0 cents disagreement；
- 左右 boundary 的 F0 change；
- voiced/unvoiced transition；
- energy change；
- 前后 interval；
- lyric overlap；
- 可选 GAME 多参数 consensus；
- 可选 second transcriber agreement。

示例：

```json
{
  "id": "note_0213",
  "game_tone": 72,
  "f0_stable_midi": 70.97,
  "pitch_error_cents": -103,
  "voiced_coverage": 0.88,
  "f0_iqr_cents": 24,
  "left_boundary_score": 0.81,
  "right_boundary_score": 0.42,
  "flags": ["wrong_pitch", "boundary_shift"]
}
```

Validator 只输出：

```text
healthy
suspicious
ambiguous
```

以及证据。

---

## 10. GAME 自一致性与 second opinion

### 10.1 GAME 参数共识

只对 suspicious regions，使用少量相近参数重复 GAME inference。

例如轻微改变 boundary threshold / decoding 参数。

如果：

```text
Run A: A4 | C5 | B4
Run B: A4 | C5 | B4
Run C: A4 | C5 | B4
```

则 GAME consensus 高。

如果：

```text
Run A: A4 | C5 | B4
Run B: A4 ----- | B4
Run C: A4 | B4
```

则属于模型本身不稳定区域。

注意：

- 只对可疑局部复核；
- 不做整首暴力 ensemble；
- 实际可调参数以当前 GAME backend 暴露的能力为准。

### 10.2 ROSVOT second opinion（可选）

只有在以下情况才接：

- GAME + RMVPE 仍有大量难判断 region；
- 自动 repair 的 false positive 风险高；
- second opinion 确实能提升诊断价值。

它首先作为**分歧检测器**，不是默认主转谱器。

---

# Part C：根据真实错误分布再实现 Repair

## 11. Repair Engine 的实施原则

只有完成 M2.1/M2.2 诊断后，才开始实现自动 repair。

Repair 的核心目标：

> **保留 GAME 已正确的绝大多数结果，只修少数有强证据的问题。**

GAME 原版永远作为 Candidate 0。

不得：

- 对整首重新生成 note；
- 为追求评价分数大范围改写 GAME；
- 没有 evidence 就修改；
- 把 F0 median 再次变成主转谱器。

---

## 12. Repair action 集合

### 12.1 retune

用于 GAME pitch 明显错误。

条件至少包括：

- voiced coverage 足够；
- structural F0 有稳定平台；
- dispersion 小；
- GAME tone 与稳定平台差异显著；
- 不像 portamento / vibrato；
- 上下文不反对修改。

### 12.2 octave repair

重点检测 ±12 semitone。

如果：

```text
GAME: A5
F0:   A4
前后也在 A4/B4 区间
```

且 octave 修正后所有证据显著改善，可列入 SAFE repair。

### 12.3 false split / merge

只有 GAME boundary 缺乏声学证据时才考虑 merge。

不能因为：

```text
A4 | A4
```

就自动 merge。

必须检查：

- F0 boundary；
- energy / onset；
- voiced transition；
- lyric mapping；
- GAME consensus。

### 12.4 missed split

如果一个长 GAME note 内存在多个持续足够长的 structural F0 稳定平台，可产生 split candidate。

优先流程：

```text
检测候选 boundaries
→ 若 GAME 支持 known boundaries / estimator，则重新调用 GAME 估 pitch
→ 否则才用 structural F0 产生候选 pitch
```

### 12.5 boundary shift

note 数和 tone 正确，但 onset/offset 偏离明显变化点时，局部搜索更优 boundary。

限制搜索窗口，避免大范围漂移。

### 12.6 false / missing note

涉及：

- GAME 认为 rest，但有持续稳定 voiced F0；
- GAME 给极短 note，但实际只是辅音/气声/分离残留。

风险较高，默认进入 PROBABLE 或 AMBIGUOUS，不先作为 SAFE 自动动作。

---

## 13. Candidate Scorer

一个 suspicious region 可以生成：

```text
C0 GAME original
C1 retune
C2 boundary shift
C3 split
C4 merge
C5 split + retune
```

评分证据：

```text
pitch_fit
boundary_fit
voiced_consistency
duration_plausibility
game_prior
game_consensus
lyric_compatibility
optional_second_model_agreement
local_melodic_continuity
complexity_penalty
unsupported_edit_penalty
```

不要把调性/和弦设成硬规则，只能作为弱证据。

### 13.1 minimum improvement

必须存在显著改善门槛。

```text
C0: 0.88
C1: 0.90
→ 不改
```

```text
C0: 0.58
C1: 0.93
→ 可接受
```

原则：

> **宁可保留 GAME 的小错误，也不要让自动纠错把正确结果改坏。**

### 13.2 所有修改必须可审计

```json
{
  "region": [57.42, 58.31],
  "before": "C5",
  "after": "B4",
  "action": "retune",
  "original_score": 0.54,
  "candidate_score": 0.93,
  "evidence": {
    "f0_agreement": 0.95,
    "game_consensus": 0.44,
    "voiced_coverage": 0.92
  }
}
```

---

## 14. 三级安全策略

### Level 1 — SAFE

可自动接受，但保留 before/after：

- 高置信 octave error；
- 高 voiced coverage + 稳定平台下的明显 wrong pitch；
- 诊断证明确实高频且规则稳定的某类 false split；
- 小范围 boundary correction，且左右拟合都显著改善。

### Level 2 — PROBABLE

生成候选 + 评分，只有超过 minimum improvement 才接受：

- split；
- merge；
- 较大 boundary shift；
- missing / false note；
- 轻度证据冲突。

### Level 3 — AMBIGUOUS

不自动改：

- 快速复杂转音；
- 大幅 portamento；
- vibrato 与真实换音难区分；
- 分离质量差；
- GAME 多配置不稳定；
- F0 extractor 明显冲突；
- multiple candidates 分数接近。

交给 Agent review / 人工试听。

---

## 15. Agent 的职责边界

Agent 不从头听完整首再凭感觉画 MIDI。

程序应先把：

```text
500 notes
```

压缩成类似：

```text
460 healthy → untouched
28 probable → candidate scoring
12 ambiguous → Agent review
```

Agent 输入使用 evidence packet：

```text
Region: 57.42–58.31 s
GAME: G4 180 ms | A4 205 ms | C5 370 ms
structural F0: G4 174 ms | A4 201 ms | B4 361 ms
GAME consensus: 0.44
candidate: C5 → B4
candidate score: 0.93
original score: 0.54
```

Agent 可以：

- 选择 candidate；
- 保留原 GAME；
- 标记 needs_review；
- 提议局部额外 candidate。

所有 Agent 修改也必须留下 audit。

---

# Part D：歌词、USTX 与表现层

## 16. Lyrics ↔ corrected melody mapping

输入：

```text
corrected melody notes
+
forced-aligned lyric chars
```

典型映射：

```text
1 char → 1 note
1 char → N notes（melisma）
N chars → N notes
```

OpenUtau：

```text
第一个 note：真实歌词
同字后续 note：+
换气：AP
静音：实际 gap / SP
```

若歌词与 melody 严重冲突：

- 标记 `lyric_alignment_conflict`；
- 回查 forced alignment / GAME boundary；
- 禁止把歌词移到最近 voiced block 来伪修复。

---

## 17. 先生成“唱对”的基础 USTX

第一阶段基础 USTX 只含：

- corrected notes；
- lyrics；
- timing；
- singer / renderer；
- 必要 phonemizer 配置。

先不要混入：

- 泠鸢复杂 style；
- 自动换气策略；
- 大量 expression；
- 复杂音色切换。

核心验收问题：

> **不看任何复杂调校，这个工程是不是已经在唱原曲正确的旋律？**

如果否，不进入 style 阶段。

---

## 18. raw F0 → constrained PITD

note 骨架通过后，raw F0 才用于“怎么唱”。

用途：

- portamento；
- 音头滑入；
- ornament；
- vibrato；
- intonation deviation。

原则：

- 不逐帧硬拷 raw F0；
- 去 extractor 毛刺；
- PITD 围绕 corrected written note 构造；
- 不能用 PITD 掩盖错误 written note；
- note 与 PITD 分开评价。

---

# Part E：评价与验收

## 19. 自动评价改造

旧 per-note median cents 保留，但不能作为“旋律正确”的主要证据。

### 19.1 Diagnostic level

记录：

- GAME raw note count；
- GAME + boundaries note count；
- 两版差异 region；
- suspicious region 数；
- 人工确认错误数；
- 各 error type 分布；
- GAME preservation ratio。

### 19.2 Score level

记录：

- corrected vs GAME note count；
- retune 数；
- octave repair 数；
- split / merge 数；
- boundary shift 数；
- ambiguous 数；
- preservation ratio。

### 19.3 F0 contour

至少：

- structural F0 agreement；
- stable-region pitch error；
- octave error count；
- unsupported boundary count；
- missed structural change count。

### 19.4 Render level

比较：

```text
reference structural/raw F0
corrected score
rendered DiffSinger F0
```

把问题区分为：

- transcription 错；
- lyric alignment 错；
- PITD 错；
- DiffSinger render 偏离。

---

## 20. 《年轮》第一阶段验收

至少保留：

```text
GAME raw USTX
GAME + word boundaries USTX
corrected USTX
GAME raw vocal render
GAME + boundaries vocal render
corrected vocal render
reference vocal excerpts
RMVPE overlay data
repair_audit.json
diagnostic_report.md
```

人工试听顺序：

```text
GAME raw
→ GAME + word boundaries
→ corrected
```

先回答：

1. GAME raw 本身到什么水平？
2. known word boundaries 是否显著改善？
3. 剩余错误主要是哪几类？
4. correction 是否确实只修少数局部？
5. corrected 是否明显优于 GAME baseline？
6. correction 有没有引入新错误？

只有“旋律基本正确”后，冻结 melody score。

---

# Part F：第二阶段 — 泠鸢风格

## 21. style_profile

M2 完成后，再分析泠鸢本人歌曲：

- vibrato rate / depth；
- portamento 类型 / 长度；
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

风格层不得无理由改动已经冻结的主旋律骨架。

---

## 22. 建议代码结构

```text
src/agent2utau/
  transcription/
    game.py
    game_backend.py
    schema.py
    rosvot.py              # optional

  diagnostic/
    experiment.py
    compare_game_runs.py
    report.py

  analysis/
    f0.py
    rmvpe.py
    structural_f0.py
    lyrics.py

  repair/
    validator.py
    candidates.py
    scorer.py
    rules.py
    consensus.py
    audit.py

  alignment/
    lyric_note_map.py

  expression/
    pitchcurve.py
    style_profile.py       # M3

  evaluation/
    score_eval.py
    contour_eval.py
    render_eval.py
```

现有：

```text
analysis/notes.py
```

改为：

```text
heuristic_fallback
```

不能继续作为默认 melody generator。

---

## 23. 新的推荐实施顺序

### M2.0 — Foundation survey

先确认本机可直接复用的：

- OpenVPI dataset-tools；
- GAME backend / model；
- GameInfer executable / DLL / runtime；
- RMVPE backend；
- 当前 OpenUtau GAME plugin 实际调用路径；
- SlurCutter 数据格式 / refinement 操作。

不要先写新的 GAME inference wrapper，除非现成路径不能满足无头调用。

### M2.1 — GAME diagnostic baseline

对《年轮》跑：

```text
A. GAME raw
B. GAME + language/context（若支持）
C. GAME + known word boundaries
D. C + RMVPE overlay
```

不自动修。

产出 diagnostic report + A/B USTX/render。

### M2.2 — Error taxonomy

人工 + 程序联合标记：

- 实际错误数量；
- 实际错误类型；
- GAME raw 与 boundaries 版的差异；
- 哪些错误是 GAME 本身；
- 哪些错误来自分离/F0/歌词对齐。

根据真实数据决定下一步。

### M2.3 — Evidence layer / Validator

- raw + structural F0；
- GAME evidence packet；
- suspicious region detection；
- 仍然不自动修改。

### M2.4 — SAFE repair

只实现《年轮》诊断中**真实出现且高置信**的错误类型。

通常优先：

- octave；
- 明显 wrong pitch；
- 极稳定 false split；
- 小 boundary shift。

如果某一类在真实诊断里几乎没有出现，不提前开发复杂规则。

### M2.5 — PROBABLE candidate system

仅在实际需要时实现：

- split；
- merge；
- missing / false note；
- scorer；
- minimum improvement gate。

### M2.6 — Optional second opinion

只有 evidence 不足时再考虑 ROSVOT / 第二模型。

### M2.7 — Lyrics mapping + base USTX

- corrected melody ↔ forced lyrics；
- melisma `+`；
- conflict 检查；
- 生成基础可编辑 USTX。

### M2.8 — PITD + render loop

- raw F0 → constrained PITD；
- DiffSinger render；
- score / contour / render 三层评价。

### M2.9 — 《年轮》M2 验收

完成：

```text
GAME raw vs GAME+boundaries vs corrected
```

逐段 A/B。

通过后冻结 melody score。

### M3 — 泠鸢风格迁移

只有 M2.9 通过后开始。

---

## 24. 最终原则

1. **优先复用 OpenVPI 现成 GAME/RMVPE/SlurCutter 基础设施。**
2. **先诊断 GAME 的真实误差分布，再写 repair。**
3. **GAME 是主乐谱骨架，不是绝对真值。**
4. **F0 是证据和演唱轨迹，不是主转谱器。**
5. **歌词决定唱什么字，不决定唱几个音。**
6. **自动纠错只改 suspicious regions，不重写整首。**
7. **原 GAME 永远保留为 Candidate 0 和回退基线。**
8. **只实现真实存在、且值得修的错误类型。**
9. **只有证据显著改善时才接受 repair。**
10. **复杂、模糊区域宁可 needs_review，不强行自动修。**
11. **second transcriber 是证据源，不默认替代 GAME。**
12. **先保证 note 骨架正确，再生成 PITD。**
13. **先“唱对”，再做泠鸢风格。**
14. **所有自动修改必须可解释、可审计、可 A/B、可回退。**