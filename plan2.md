# agent2utau — Plan 2：GAME 主转谱 + 证据驱动校正 + 分阶段演唱建模

> 修订日期：2026-09-16
>
> 核心原则：**先把“唱对”解决，再把“唱得像泠鸢”解决。**
>
> 当前最重要的工程原则：**GAME raw 是主 baseline；先量清 GAME 自身随机性与真实 residual error，再决定 repair。F0、歌词边界和第二模型都只是证据，不直接替代 GAME。**

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

旧主旋律生成方式：

```text
歌词字窗口
→ F0 中位数
→ heuristic split
→ MIDI note
```

能力不足，降级为 fallback，不再作为默认 melody transcription。

### 1.1 Plan2 已完成的基础设施

当前仓库已经真正接入：

- 官方 GAME 1.0.3-medium ONNX 权重；
- 官方 RMVPE ONNX 权重；
- GAME `encoder → segmenter → bd2dur → estimator` 推理链；
- OpenUtau AudioSlicer 等价切片；
- RMVPE 16 kHz / hop 160 推理；
- `diagnose` 命令；
- GAME USTX + DiffSinger render；
- RMVPE overlay；
- GAME raw evidence packets；
- lyric-boundary matching；
- variant time-alignment comparison。

第一轮诊断曾得到：

```text
A raw:        419
B zh:         417
C forced-bd:  760
```

最初在 C 上得到的 `76 suspicious / 54 wrong_pitch` 已确认**不能代表 GAME raw 的真实错误率**，因为 forced char boundaries 大量增加了 note。

### 1.2 M2.1.1 修正后的《年轮》结果

当前修正诊断 run：

```text
A raw:        421
B zh:         420
C forced-bd:  751
```

已修：

- IQR / dispersion 改为 cents；
- variant comparison 不再按 note index `zip`；
- structural F0 只填 <=40 ms 的短 unvoiced gap；
- GAME `known_boundaries` D3PM 初始化与官方实现对齐；
- suspicious 检测改为首先跑 GAME raw；
- lyric boundaries 改为 evidence/matching，不再强制参与主链；
- forced-boundary 版本降级为 experimental only。

当前 GAME raw 诊断：

```text
231 flagged / 421 voiced notes
228 含 high_dispersion
39 个 wrong_pitch 同时伴随高 dispersion
1 个 hard-evidence wrong_pitch / octave candidate
```

其中最强候选：

```text
~189.84 s
GAME vs RMVPE ≈ +1186 cents
F0 IQR ≈ 7 cents
voiced coverage = 1.0
```

它是目前首个非常强的 SAFE octave-repair 候选。

但：

> **231 flagged 不是 231 个错误。**

`high_dispersion > 60c` 对真人歌声过于敏感，会把 vibrato / transition / portamento 大量标记出来。因此 high dispersion 后续降级为 feature，不再单独触发 suspicious。

---

## 2. 项目定位

GAME 是专门的 singing voice transcription 模型，但真人歌声到离散 note 存在天然模糊：

- vibrato 是 note 内 modulation 还是多个 note；
- portamento 什么时候算真正换音；
- appoggiatura / grace note 是否单独记谱；
- 极短经过音是否写进 MIDI；
- 辅音、气声、分离残留是否形成假 boundary；
- octave ambiguity；
- onset / offset 本身有几十毫秒不确定性。

因此项目不尝试训练一个“总体超过 GAME 的新通用转谱器”。

目标是：

> **GAME + GAME self-consensus + RMVPE/FCPE + 歌词边界 + 局部上下文 + 可选 second opinion + DiffSinger render feedback，在 OpenUtau 翻唱这一特定任务上优于单次 GAME raw。**

任务从：

```text
audio → 从零猜整首 MIDI
```

变成：

```text
GAME 已给出大部分正确答案
→ 判断哪些 note/boundary 在 GAME 自身就不稳定
→ 再叠加 F0 / lyric / context 证据
→ 只修少量强证据错误
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

天然工作流：

```text
GAME → note skeleton
RMVPE → continuous pitch evidence
SlurCutter → MIDI refinement
```

### 3.2 SlurCutter

把人工修谱动作限制为：

```text
retune
split
merge
boundary_shift
delete_false_note
insert_missing_note
```

目标是自动化“人看 F0 修 GAME”的过程，而不是重新设计整首 MIDI。

### 3.3 HachiTune

借鉴：

```text
GAME segmentation + RMVPE/FCPE + piano-roll/pitch editor
```

默认只参考架构与交互，不直接复制代码。

### 3.4 ROSVOT

仅作为可选 second opinion / disagreement detector。

第一阶段不要求接入。只有 GAME consensus + 双 F0 仍无法稳定判断大量 region 时才增加。

---

# Part A — 主链路

## 4. 最终主流程

```text
原曲
  ↓
解码 / 人声伴奏分离
  ↓
GAME raw 多次同配置推理
  ↓
GAME stochastic consensus
  ↓
consensus note skeleton
  +
RMVPE / FCPE raw F0
  +
structural F0
  +
LRC / Whisper lyric boundaries
  ↓
Validator / Evidence Layer
  ↓
hard suspicious regions
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

GAME 提供：

- note onset；
- note offset / duration；
- note pitch；
- voiced/rest；
- note sequence。

GAME raw 是默认 Candidate 0，但**单次 GAME 输出不是绝对确定结果**。

当前 OpenUtau GAME 说明中明确存在 D3PM stochastic boundary removal；ONNX backend 不接受外部 seed 进行稳定复现。因此同一音频、同一参数多次运行可能得到略有不同的 note/boundary。

这不是自动 repair 的障碍，反而可以成为重要证据：

> GAME 自己多次都稳定给出的 note，比单次偶然出现的 note 更可信。

### 5.2 F0：证据 + 演唱轨迹

- RMVPE：主要 evidence；
- FCPE：第二 F0 opinion / A/B / fallback。

F0 用于：

- 验证 GAME pitch；
- 验证 boundary；
- 确认 octave 异常；
- 发现 false/missed split candidate；
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

歌词边界只作为 matching / snapping / missing-boundary evidence，不直接强制新增 GAME boundary。

---

# Part B — Diagnostic Correctness

## 6. Variant 定位

### Variant A — GAME raw

主 baseline。

必须输出：

- GAME notes；
- USTX；
- vocal render；
- RMVPE/FCPE evidence；
- evidence packets；
- hard suspicious regions。

### Variant B — GAME + zh

仅用于研究 language conditioning。

**不能再用单次 A vs 单次 B 的差异直接归因于 language。**

必须先量出同配置 GAME 自身 stochastic variance，再比较 raw consensus 与 zh consensus。

### Variant C — forced known boundaries

仅 experimental。

当前《年轮》已经表明它会大量增加 note，并影响 estimator 输出。

不参与默认 melody selection，也不把其 suspicious 数当作 GAME error rate。

### Variant D — GAME raw + F0 overlay

主要 validation baseline。

显示：

```text
GAME notes
RMVPE raw F0
FCPE raw F0（后续加入）
structural F0
voiced mask
```

### Variant E — GAME raw + lyric-boundary overlay

歌词边界只参与 evidence。

分类：

```text
matched
possible_snap
possible_missing_boundary
unsupported_lyric_boundary
```

当前《年轮》约：

```text
57 matched
265 possible_snap
1 possible_missing
26 unsupported
```

其中 80–300 ms 的大量 `possible_snap` 不能直接 snap，因为 Whisper char start、辅音开始、元音/F0 开始、谱面 note onset 并不是同一个概念。

---

## 7. M2.1.1 已完成的 correctness 修复

已完成：

1. dispersion / pitch error 对外统一 cents；
2. variant comparison 按时间匹配，不再 index zip；
3. structural F0 只插值短 gap；
4. known-boundary D3PM init 与官方规范一致；
5. suspicious 改为 GAME raw-first；
6. lyric boundary 仅 overlay/matching；
7. forced-boundary 降级 experimental；
8. 完整重跑《年轮》。

### 7.1 仍需修 structural F0 filter contamination

当前实现虽然不再跨长静音插值，但 median filter 前仍把 NaN 临时变成 `0.0 MIDI`：

```text
NaN / long silence
→ temporary MIDI 0
→ median_filter
→ 再设回 NaN
```

这可能污染长静音两侧的少量 voiced frames。

下一版应改为：

```text
按连续 voiced island 分段
→ 每个 island 内单独 median/filter
→ island 之间绝不互相影响
```

短 gap <= 30–50 ms 可在同 island 内插值；长 gap 彻底断开。

---

# Part C — M2.1.2：GAME Stochastic Baseline / Consensus

## 8. 为什么必须先测 GAME 自身随机性

同一首《年轮》当前不同完整运行得到：

```text
raw run #1: 419 notes
raw run #2: 421 notes
```

这意味着在比较：

```text
raw vs zh
raw vs repaired
```

之前，必须先知道：

> **同配置 raw vs raw 自己会变化多少。**

否则无法区分：

```text
真正的 language effect
```

和：

```text
GAME D3PM 自身 stochasticity
```

## 9. 同配置重复推理

对同一个 separated vocal、完全相同参数跑至少 5 次：

```text
A1 raw
A2 raw
A3 raw
A4 raw
A5 raw
```

建议第一版 5 次；如果计算成本低，可扩展到 8–10 次做统计验证。

每次必须记录：

```text
GAME model hash
backend
sampling steps
boundary threshold
boundary radius
score threshold
language
input vocal hash
note count
```

## 10. 建立 consensus note graph

不能简单按 index 对齐。

按：

```text
onset proximity
时间 overlap
pitch proximity
sequence order
```

将多次运行的 note 聚类成 consensus events。

每个 event 至少保存：

```json
{
  "start_median": 42.135,
  "start_iqr_ms": 18,
  "duration_median": 0.417,
  "duration_iqr_ms": 26,
  "tone_mode": 69,
  "tone_agreement": 0.8,
  "presence_rate": 1.0,
  "n_runs": 5
}
```

关键指标：

- `presence_rate`：这个 note 在多少次 GAME 里存在；
- `tone_agreement`：出现时多少次 tone 一致；
- `start_iqr_ms`；
- `duration_iqr_ms`；
- boundary stability；
- voiced/rest stability。

## 11. Consensus 分类

建议：

```text
GAME_STABLE
GAME_VARIABLE
GAME_UNSTABLE
```

例如：

### GAME_STABLE

```text
5/5 runs 都有
pitch 5/5 一致
boundary spread < 30 ms
```

### GAME_VARIABLE

```text
4/5 runs 有
或 boundary spread 30–100 ms
或 pitch 有少量分歧
```

### GAME_UNSTABLE

```text
<=3/5 runs 有
或 split/merge 结构频繁变化
或 pitch 多解
```

阈值先作为实验值，后续按《年轮》真实分布校准。

## 12. Consensus 如何参与 repair

GAME consensus 是 evidence，不是独立真值。

### Case A：GAME 稳定，但 F0 反对

```text
GAME 5/5: A5
RMVPE:     A4
FCPE:      A4
stable F0
```

这是“模型稳定地犯错”的可能情况，不能因 consensus 高就拒绝修。

需要更高证据门槛。

### Case B：GAME 自己不稳定，F0 明确

```text
GAME: A5 / A4 / A4 / A5 / A4
RMVPE: A4
FCPE:  A4
```

这是非常强的 repair 候选。

### Case C：GAME 不稳定，F0 也不稳定

```text
GAME split/merge 多解
RMVPE/FCPE 在 vibrato/portamento 区也分歧
```

直接进入 AMBIGUOUS，不自动改。

---

# Part D — F0 Evidence

## 13. 双 F0：RMVPE + FCPE

当前 octave candidate 不能只依赖 RMVPE 一家确认。

对 hard suspicious region 同时提取：

```text
RMVPE
FCPE
```

至少比较：

- voiced/unvoiced；
- stable center；
- octave；
- IQR / dispersion；
- transition timing。

如果：

```text
RMVPE + FCPE 都稳定指向同一个 octave/pitch
```

证据显著增强。

如果两者冲突：

```text
AMBIGUOUS
```

不允许 SAFE repair。

## 14. raw F0 与 structural F0

保留：

```text
raw F0
→ 去毛刺
→ 短 gap 插值
→ voiced-island filtering
→ structural F0
```

职责：

- structural F0：note / boundary evidence；
- raw F0：PITD / vibrato / portamento / intonation。

所有对外 dispersion / pitch error 统一为 cents。

---

# Part E — Validator Calibration

## 15. `high_dispersion` 不再单独触发 suspicious

当前：

```text
228 / 421 notes high_dispersion > 60c
```

说明该 flag 对真人歌声没有筛选价值。

以后：

```text
f0_iqr_cents
```

只保留为 feature。

禁止：

```text
IQR > X
→ suspicious
```

单条件触发。

## 16. Hard suspicious 使用组合条件

例如 wrong pitch：

```text
abs(GAME - F0 stable center) > 100c
AND voiced coverage > 0.8
AND F0 IQR < calibrated threshold
AND RMVPE/FCPE agreement sufficiently high
```

Octave candidate：

```text
error ≈ 1200c
AND stable voiced evidence
AND dual-F0 agree
```

Boundary candidate：

```text
GAME boundary unstable across runs
AND structural F0 changepoint stable
AND duration remains plausible
```

## 17. Validator 输出分层

不要再把所有 feature flag 混成一个 suspicious count。

建议输出：

```text
feature_only
hard_suspicious
ambiguous
healthy
```

其中：

- `feature_only`：如 high dispersion、vibrato、较弱 lyric offset；
- `hard_suspicious`：足够值得进入 repair candidate；
- `ambiguous`：存在问题但无法可靠决定；
- `healthy`：无需处理。

报告重点显示：

```text
hard_suspicious count
ambiguous count
```

而不是 feature 总数。

---

# Part F — Lyrics Evidence

## 18. lyric boundary 只做 evidence

禁止：

```text
每个汉字 start → 强制 GAME boundary
```

优先：

```text
lyric boundary
→ nearest GAME consensus boundary
→ distance + F0 + onset/energy + articulation
→ match / weak-snap / missing-boundary candidate
```

## 19. 先研究 timestamp 语义差异

对于 80–300 ms 的大量偏差，需要区分：

```text
Whisper char timestamp
辅音起点
元音起点
F0 voiced onset
GAME note onset
```

这几者可能天然不同。

因此 lyric timestamp 不得直接被当作“更准确的 note onset”。

只有当：

- GAME consensus boundary 不稳定；
- lyric evidence 支持；
- structural F0 / energy/onset 也支持；

才生成 boundary-shift / missing-boundary candidate。

---

# Part G — Error Taxonomy

## 20. 真实 GAME residual error taxonomy

只有完成：

```text
GAME stochastic consensus
+
dual-F0 evidence
+
validator calibration
```

之后，才统计 GAME raw 的真实 residual errors。

类型：

```text
wrong_pitch
possible_octave_error
false_split
missed_split
boundary_shift
very_short_false_note
missing_note
weak_f0_evidence
lyric_alignment_conflict
ambiguous_ornament
```

报告必须区分：

```text
raw feature flags
hard suspicious
人工确认 error
```

不能再把 feature flag 当 error count。

---

# Part H — Repair Engine

## 21. Repair 原则

目标：

> **GAME 做绝大多数工作；我们只修少量 residual error。**

永久保留：

```text
Candidate 0 = GAME raw / GAME consensus baseline
```

不得：

- 对整首重新生成 notes；
- 没 evidence 就修改；
- 为追求指标大面积改写 GAME；
- 把 F0 median 再变成主转谱器。

## 22. SAFE repair

第一批只做真实确认过的强证据类型。

当前最可能首个 SAFE 动作：

```text
octave retune ±12 semitone
```

但在正式自动执行前，至少要求：

```text
GAME consensus 已知
RMVPE 同意
FCPE 同意
稳定 voiced region
人工试听/检查首个样例通过
```

## 23. 其他 repair actions

### retune

明显 wrong pitch，要求稳定 F0 与上下文支持。

### false split / merge

只有 GAME boundary 缺乏声学证据，且多次 GAME 推理本身不稳定时才优先考虑。

### missed split

长 note 内存在稳定多个 structural F0 平台。

修 boundary 后优先让 GAME estimator 重新估 pitch。

### boundary shift

只在原 boundary 附近小窗口搜索。

### false / missing note

高风险，默认 PROBABLE / AMBIGUOUS。

---

## 24. Candidate Scorer

候选：

```text
C0 GAME original/consensus
C1 retune
C2 boundary shift
C3 split
C4 merge
C5 combined local repair
```

评分 evidence：

```text
GAME presence consensus
GAME tone consensus
GAME boundary stability
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

## 25. 三级安全策略

### SAFE

- dual-F0 + GAME evidence 强一致的 octave error；
- 极稳定 F0 下明显 wrong pitch；
- 已经过真实样本验证的简单错误。

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

## 26. Lyrics ↔ corrected melody

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

若歌词与 melody 冲突：

- 标 `lyric_alignment_conflict`；
- 回查 alignment / GAME boundary；
- 不把歌词强行移动到“最近 voiced block”伪修复。

## 27. 基础 USTX

第一阶段只含：

- corrected notes；
- lyrics；
- timing；
- singer / renderer；
- phonemizer 必要设置。

核心验收：

> **不做复杂风格调校，是否已经在唱正确的《年轮》旋律？**

## 28. raw F0 → constrained PITD

note 骨架通过后再做：

- portamento；
- 音头滑入；
- ornament；
- vibrato；
- intonation deviation。

PITD 不能掩盖 written-note 错误。

---

# Part J — Evaluation

## 29. Diagnostic level

至少记录：

- GAME raw 每次 run 的 note count；
- consensus event count；
- GAME_STABLE / VARIABLE / UNSTABLE 数；
- hard suspicious / ambiguous 数；
- dual-F0 agreement；
- lyric boundary evidence 分布；
- 人工确认 error 数；
- validator false positive / false negative。

## 30. Score level

记录：

- corrected vs consensus baseline；
- retune；
- octave repair；
- split / merge；
- boundary shift；
- ambiguous；
- GAME preservation ratio。

## 31. F0 / Render level

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

旧 per-note median cents 可保留，但不能单独证明旋律正确。

---

# Part K — 实施顺序

## 32. Milestones

### M2.0 — Foundation survey ✅

- GAME/RMVPE 官方权重；
- OpenUtau backend；
- dataset-tools / SlurCutter 调研。

### M2.1 — Initial diagnostic ✅

初版 A/B/C/D 已完成，但 forced-boundary 结果曾导致错误解读。

### M2.1.1 — Diagnostic correctness ✅ / 基本完成

已完成：

- cents 单位；
- time alignment；
- raw-first validator；
- lyric evidence-only；
- known-boundary init；
- forced C 降级。

剩余小修：

- structural F0 改成 voiced-island filtering，避免 `NaN→0` median contamination。

### M2.1.2 — GAME stochastic baseline ← 当前最高优先级

必须：

1. 同配置 GAME raw 重跑至少 5 次；
2. 生成 consensus note graph；
3. 统计 note count variance；
4. 统计 onset/duration/pitch stability；
5. 输出 GAME_STABLE / VARIABLE / UNSTABLE；
6. raw-vs-zh 比较必须基于各自 consensus，而不是单次运行；
7. 确认 189.84s octave candidate 在 GAME 多次运行中的稳定性。

**M2.1.2 未完成前，不进入正式 SAFE repair。**

### M2.2 — Dual-F0 + Raw GAME error taxonomy

- RMVPE + FCPE；
- 确认 hard suspicious；
- 人工试听/检查；
- 得到真实 error distribution。

### M2.3 — Validator calibration

- `high_dispersion` 降为 feature-only；
- suspicious 改成组合条件；
- 建 hard_suspicious / ambiguous；
- 测 false positive / false negative。

### M2.4 — SAFE repair

只实现《年轮》中已真实确认、证据强的错误类型。

优先测试：

```text
octave ±12 semitone
```

### M2.5 — PROBABLE candidate system

只在实际需要时实现：

- split；
- merge；
- missing / false note；
- scorer；
- minimum improvement gate。

### M2.6 — Optional second opinion

只有 GAME consensus + RMVPE + FCPE + lyric evidence 仍不足时再接 ROSVOT。

### M2.7 — Lyrics mapping + base USTX

corrected score → lyrics/melisma → 可编辑工程。

### M2.8 — PITD + render loop

raw F0 → constrained PITD → DiffSinger → 三层评价。

### M2.9 — 《年轮》M2 验收

主要比较：

```text
GAME consensus baseline
vs
corrected
```

forced-boundary 仅保留实验材料。

通过后冻结 melody score。

### M3 — 泠鸢风格迁移

只有 M2.9 通过后开始。

---

## 33. 第二阶段：泠鸢 style profile

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

## 34. 最终原则

1. **GAME raw / GAME consensus 是默认主旋律 baseline。**
2. **单次 GAME 输出不等于绝对确定结果，必须量出自身 stochasticity。**
3. **raw-vs-zh 等比较必须先扣除 same-config stochastic variance。**
4. **forced-char-boundary 路径只保留为实验。**
5. **RMVPE + FCPE 是证据与演唱轨迹，不是从零主转谱器。**
6. **high dispersion 是 feature，不是错误本身。**
7. **歌词字符边界只用于 matching/snapping/evidence。**
8. **structural F0 按 voiced islands 处理，不跨长 silence 过滤。**
9. **所有 pitch dispersion/error 对外统一 cents。**
10. **自动 repair 只针对 hard suspicious residual errors。**
11. **GAME baseline 永远保留为 Candidate 0 / 回退基线。**
12. **只实现真实出现且值得修的错误类型。**
13. **复杂区域宁可 needs_review，不强行自动修。**
14. **先把 note 骨架唱对，再生成 PITD。**
15. **先“唱对”，再做泠鸢风格。**
16. **所有自动修改必须可解释、可审计、可 A/B、可回退。**
