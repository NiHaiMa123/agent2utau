# agent2utau — Plan 2：GAME 主转谱 + F0 校验修复 + 分阶段演唱建模

> 修订日期：2026-09-16
>
> 本计划用于替代当前“歌词字窗口 → F0 中位数 → heuristic split → note”的主旋律生成思路。
>
> 核心原则：**先把“唱对”解决，再把“唱得像泠鸢”解决。**
>
> 第一阶段只关注：歌词正确、音符骨架正确、节奏正确、旋律与原唱一致、OpenUtau 可稳定渲染。
>
> 第二阶段才加入：泠鸢本人演唱风格、滑音、颤音、换气、句内强弱、音色选择与表现参数。

---

## 1. 为什么需要 Plan 2

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

现有 `analysis/notes.py` 基本逻辑为：

1. 先由歌词系统确定每个字的时间窗；
2. 在该时间窗中取 F0 中位数；
3. 四舍五入到最近的 MIDI note；
4. 只有检测到持续一定时间、跨过一定半音阈值的变化时，才把一个字拆成多个音符。

这不是完整的 singing voice transcription。它容易把滑音、倚音、多音转音、经过音、真实换音位置以及颤音与换音的区别处理错误。

因此 Plan 2 不继续微调 `MIN_NOTE_SEC`、`SPLIT_SEMITONES` 等阈值，而是把旋律骨架的主来源切换为 **GAME**。

现有 heuristic note builder 保留，但降级为 fallback，不再作为默认主路径。

---

## 2. 总体架构

第一阶段主流程：

```text
原曲
  ↓
解码 / 人声伴奏分离
  ↓
GAME：主旋律 note 骨架
(onset / offset / tone)
  +
F0 extractor：连续音高证据
(raw F0 + structural F0)
  ↓
GAME note validation
  ↓
suspicious-region detection
  ↓
局部 repair candidate generation
  ↓
candidate scoring + conservative acceptance
  ↓
corrected melody notes
  +
LRC / Whisper DTW 字时间
  ↓
lyrics ↔ melody notes 对齐
  ↓
基础 USTX
  ↓
原唱 raw F0 → 受约束 PITD / 局部表现
  ↓
DiffSinger 渲染
  ↓
reference vs score vs render 自动评价
  ↓
只回修低置信度区域
  ↓
第一阶段合格成品
```

第二阶段：

```text
泠鸢本人歌曲
  ↓
风格统计 / style profile
  ↓
滑音 / 颤音 / 换气 / 强弱 / 音色习惯
  ↓
对第一阶段已正确的工程做风格化重调
```

---

## 3. 三种信息必须分工明确

### 3.1 GAME：负责“唱什么音”

GAME 是主 melody transcription backend。

GAME 输出作为**主乐谱假设**：

- note onset；
- note offset / duration；
- note pitch；
- note sequence；
- 可获得时记录 confidence / raw logits / threshold 等诊断信息。

GAME 可以有局部错误，例如：

- 多切一个短音；
- 漏掉一个转音；
- note 高/低一个或若干半音；
- octave error；
- boundary 偏几十毫秒。

这些错误交给 validation + repair，而不是因此废弃 GAME。

### 3.2 F0：负责“证据”和“细节”，不负责从零生成整首乐谱

F0 extractor 使用 RMVPE 或 FCPE；第一实现可先沿用已修正的 FCPE，再做 RMVPE A/B。

F0 用途：

- 验证 GAME note pitch；
- 验证 note boundary；
- 检测漏拆 / 多拆；
- 检测 octave jump；
- 给 repair candidate 提供连续音高证据；
- 生成后续 PITD；
- 比较 reference 与 rendered vocal。

禁止恢复为：

```text
lyrics char window → median F0 → note
```

作为主流程。

### 3.3 LRC / Whisper DTW：负责“唱哪个字”

歌词系统只负责：

- 歌词文本；
- 每个字 / syllable 的时间范围；
- 句段边界；
- 间奏与无歌词区间。

歌词时间不再直接决定 note 数量和 note pitch。

例如 GAME 得到：

```text
A4 → B4 → C5 → B4
```

若四个 note 都属于“轮”字，则 OpenUtau 写为：

```text
轮  +  +  +
```

---

## 4. F0 双层表示：structural F0 与 raw F0

这是 GAME 自动纠错能否稳定的关键。

真人演唱中的 raw F0 包含：

- vibrato；
- portamento；
- 音头滑入；
- 尾音；
- 倚音；
- 微小 intonation；
- 分离噪声与 extractor 毛刺。

如果直接拿 raw F0 判断 note split，会把“怎么唱”误认为“唱了几个音”。

因此保留两条曲线：

```text
raw_f0
  ↓ 去毛刺 / 平滑 / 稳定区提取
structural_f0
```

职责：

- `structural_f0`：用于 note pitch、boundary、split/merge 的验证与 repair；
- `raw_f0`：用于后续 PITD、滑音、颤音等演唱细节。

structural F0 的生成不能简单重度低通。需要尽量保留真正稳定的换音平台，同时压制 vibrato 半周期、单帧跳点和极短装饰。

建议同时保存：

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

## 5. Phase 1：接入 GAME

### 5.1 输出统一 schema

新增独立 transcription 层，例如：

```text
src/agent2utau/transcription/game.py
src/agent2utau/transcription/schema.py
```

内部统一：

```json
{
  "id": "note_0127",
  "start": 42.135,
  "end": 42.552,
  "dur": 0.417,
  "tone": 69,
  "source": "game",
  "game_confidence": null
}
```

### 5.2 接入原则

优先复用本机 OpenUtau 已安装环境中的 GAME 能力，先调查实际入口：

- OpenUtau Core / plugin 是否能直接调用；
- bridge 是否能无头调用；
- 模型与 runtime 的实际路径；
- 若 UI 层只是薄包装，优先复用底层实现；
- 最后才考虑单独 Python 包装。

记录：GAME 版本、模型 hash、输入采样率、参数、输出 note 数量、耗时、是否经过后处理。

### 5.3 fallback

只在 GAME 不可用、运行失败、输出为空/损坏时回退现有 heuristic。

报告必须写：

```text
melody_source: game | heuristic_fallback
```

不得静默 fallback。

---

## 6. Phase 2：GAME Validator

GAME 输出不能直接视为最终乐谱。

Validator 对每个 note 及相邻 boundary 建立证据包。

### 6.1 每个 note 的基本特征

至少计算：

- GAME tone；
- structural F0 median / mode / stable center；
- voiced coverage；
- pitch IQR / dispersion；
- GAME tone 与 stable F0 的 cents disagreement；
- note duration；
- 左右 boundary 的 F0 change；
- 左右 boundary 的 voiced/unvoiced change；
- energy change；
- 与前后音的 interval；
- lyric overlap / syllable mapping 情况。

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

### 6.2 至少识别以下异常类型

```text
wrong_pitch
possible_octave_error
false_split
missed_split
boundary_shift
very_short_isolated_note
weak_f0_evidence
unvoiced_note
possible_missing_note
lyric_alignment_conflict
```

Validator 只负责**发现问题并提供证据**，不直接修改乐谱。

---

## 7. Phase 3：GAME 自动纠错

### 7.1 总原则

**不是重新转谱，而是只修 GAME 的局部异常。**

目标不是做一个比 GAME 更大的黑盒模型，而是：

> 保留 GAME 已正确的绝大多数结果，只修最后少量有强证据的问题。

整体：

```text
GAME notes
  +
structural F0 / energy / voiced / lyrics
  ↓
Validator
  ↓
suspicious regions
  ↓
Candidate Generator
  ↓
Scorer
  ↓
只有显著优于原 GAME 时才接受
  ↓
corrected notes
```

原 GAME 方案永远作为 Candidate 0 保留。

### 7.2 Repair 类型 A：retune / wrong pitch

例：

```text
GAME: B4
structural F0: A4 +8c，稳定、覆盖 91%
```

生成候选：

```text
C0: 保持 B4
C1: B4 → A4
```

只有 voiced coverage 高、stable dispersion 小、差异显著、邻接上下文不冲突时才允许自动 retune。

不要按单帧 F0 修音。

### 7.3 Repair 类型 B：octave error

典型：

```text
GAME: A5
structural F0: A4
前后音也位于 A4 附近
```

±12 semitone 是高优先级检查项。

满足：

- octave 修正后与 structural F0 显著更吻合；
- 与相邻音的 interval 更连续；
- 不是确实存在的大跳；

可列为 SAFE repair。

### 7.4 Repair 类型 C：false split / merge

例：

```text
GAME: A4 | A4 | A4
structural F0: A4 ----------------
中间无真实 F0 / voiced / energy boundary
```

候选：

```text
C0: 保持三音
C1: merge 0+1
C2: merge 1+2
C3: merge 0+1+2
```

不能因为相邻 tone 一样就直接 merge。必须证明 GAME 声称的 boundary 缺乏声学证据。

### 7.5 Repair 类型 D：missed split

例：

```text
GAME: A4, 800 ms
structural F0:
A4 300 ms → C5 250 ms → B4 250 ms
```

若存在多个持续足够长、稳定且有明确 changepoint 的平台，生成 split candidates。

优先流程：

```text
检测候选 boundaries
  ↓
用 GAME/其底层能力在修正后的 boundaries 上重新估计 pitch（若本机接口支持）
  ↓
否则用 structural F0 + 上下文生成 pitch candidate
  ↓
统一交给 Scorer
```

不要把当前 heuristic `_split_char()` 直接搬来作为主 missed-split 算法。

### 7.6 Repair 类型 E：boundary shift

GAME note 数量和 tone 都合理，但 boundary 落错。

例：

```text
真实 changepoint ≈ 0.500 s
GAME boundary = 0.580 s
```

候选：

```text
0.580 → 0.500 附近若干局部候选位置
```

优先搜索范围限制在原 boundary 周围的小窗口，避免大范围漂移。

调整 boundary 后重新验证左右 note 的稳定 F0 与 duration。

### 7.7 Repair 类型 F：voiced/rest / missing note

检查：

- GAME 认为 rest，但存在持续稳定 voiced F0；
- GAME 给了极短 note，但实际只是辅音、换气、分离残留；
- note 区域绝大部分 unvoiced，且没有歌词/旋律证据。

这类修改风险高于单纯 retune，默认至少进入 PROBABLE 级候选评分。

---

## 8. Candidate Scorer

发现异常不能直接改，必须比较候选。

一个 suspicious region 可能生成：

```text
C0 GAME 原样
C1 retune
C2 boundary shift
C3 split
C4 merge
C5 split + retune
```

建议总分由下列项组成：

```text
score =
    pitch_fit
  + boundary_fit
  + voiced_consistency
  + duration_plausibility
  + game_prior
  + lyric_compatibility
  + local_melodic_continuity
  - complexity_penalty
  - unsupported_edit_penalty
```

第一版不要把“符合调性/和弦”设成强约束，因为流行歌存在经过音、借音、蓝调音和装饰音；音乐理论只能做弱证据。

### 8.1 必须有 minimum improvement

例如：

```text
C0 GAME original: 0.88
C1 repair:        0.90
```

差异太小，不改。

只有：

```text
C0: 0.61
C1: 0.91
```

才允许高置信接受。

核心原则：**宁可保留 GAME 的小错误，也不要让自动纠错把正确结果改坏。**

### 8.2 评分必须输出可审计证据

```json
{
  "region": [57.42, 58.31],
  "original": {"score": 0.61},
  "candidates": [
    {"action": "retune", "score": 0.92},
    {"action": "boundary_shift", "score": 0.67}
  ],
  "accepted": "retune",
  "improvement": 0.31,
  "evidence": {
    "f0_agreement": 0.95,
    "boundary_agreement": 0.83,
    "voiced_coverage": 0.92
  }
}
```

---

## 9. GAME 自一致性 / 多配置共识

对于边界不确定区域，可在局部片段对 GAME 使用少量不同 threshold / inference 参数做重复转谱。

目的不是暴力 ensemble 整首，而是判断：

> 这个 note/boundary 是 GAME 稳定认为存在，还是参数轻微变化就消失？

例：

```text
Run A: A4 | C5 | B4
Run B: A4 | C5 | B4
Run C: A4 | C5 | B4
→ high GAME consensus
```

相反：

```text
Run A: A4 | C5 | B4
Run B: A4 ----- | B4
Run C: A4 | B4
→ ambiguous
```

生成：

```text
game_consensus_score
```

此分数进入 Candidate Scorer。

第一实现只对 Validator 已标记的 suspicious regions 做多配置复核，避免把推理成本扩大到整首。

---

## 10. 三级修复安全策略

### Level 1 — SAFE

可自动接受，但仍记录 before/after。

典型：

- 明显 octave error；
- 高 voiced coverage + 极稳定 F0 下的明显错音；
- 极强证据的重复 false split；
- 不改变 note 数量的小幅 boundary correction，且左右拟合都显著改善。

### Level 2 — PROBABLE

必须生成多个候选并评分，只有 improvement 超过阈值才接受。

典型：

- split；
- merge；
- 较大 boundary shift；
- missing note / false note；
- 多个证据源有轻度冲突。

### Level 3 — AMBIGUOUS

不自动改。

交给 Agent review 或最终人工试听：

- 快速复杂转音；
- 大幅 portamento；
- vibrato 与真正换音难区分；
- 分离质量差；
- F0 extractor 之间明显冲突；
- GAME 多配置结果不稳定；
- 多个 candidate 得分接近。

报告必须给出具体时间范围，使 Agent/用户可以快速试听。

---

## 11. Agent 的职责边界

Agent 不负责“从头听完整首再凭感觉画音高线”。

程序先把几百个 notes 压缩成少量异常区域，例如：

```text
500 total notes
442 high-confidence → untouched
41 probable → deterministic candidate scoring
17 ambiguous → Agent review
```

Agent 输入应该是结构化 evidence packet：

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

- 选择候选；
- 要求保留原 GAME；
- 标记 needs_review；
- 在局部上下文内提出额外候选。

Agent 的每次修改必须留下：

```text
before
after
reason
evidence
confidence
```

---

## 12. Phase 4：歌词与 corrected melody 对齐

输入：

```text
corrected melody notes
+
forced-aligned lyric chars
```

目标是多对多但受约束的 mapping。

典型：

```text
1 char → 1 note
1 char → N notes（melisma）
N chars → N notes
```

OpenUtau：

```text
第一个 note：真实歌词字
同字后续转音：+
换气：AP
静音：按实际需要 gap / SP
```

如果歌词与 melody 严重冲突：

- 标记 `lyric_alignment_conflict`；
- 回查 forced alignment 或 GAME boundary；
- 禁止把歌词直接移动到“最近 voiced block”来伪修复。

---

## 13. Phase 5：先生成“唱对”的基础 USTX

第一阶段基础 USTX 只包含：

- corrected notes；
- lyrics；
- 正确 timing；
- singer / renderer；
- 必要 phonemizer 配置。

先不要把复杂泠鸢 style、AP、强弱、音色自动化与旋律修复混在一起。

核心验收问题：

> **不看复杂风格调校，这个工程是不是已经在唱原曲正确的旋律？**

如果否，不进入第二阶段。

---

## 14. Phase 6：raw F0 → 受约束 PITD

note 骨架正确后，raw F0 才用于“怎么唱”。

用途：

- portamento；
- 音头滑入；
- 局部转音细节；
- vibrato 轮廓；
- intonation deviation。

原则：

- 不逐帧硬拷 raw F0；
- 去除 extractor 毛刺；
- PITD 必须围绕 corrected written note 构造；
- 不让 PITD 掩盖一个本来错误的 note；
- note 与 PITD 必须分开评价。

---

## 15. 自动评价必须改造

旧 per-note median cents 可以保留，但不能作为“旋律正确”的主要证据。

新增至少：

### 15.1 Score-level

- GAME original vs corrected note count；
- 自动修改 note 数和比例；
- pitch repair 数；
- split / merge 数；
- boundary shift 数；
- ambiguous 数；
- GAME preservation ratio。

`GAME preservation ratio` 应尽量高，作为“自动系统没有无故重写 GAME”的保护指标。

### 15.2 Pitch contour

- frame-level voiced F0 error；
- structural F0 agreement；
- octave error count；
- stable-region pitch accuracy。

### 15.3 Boundary

- reference structural changepoint 与 note boundary 的 timing error；
- unsupported boundaries；
- missed structural changes。

### 15.4 Render

最终比较三层：

```text
reference structural/raw F0
corrected score
rendered DiffSinger F0
```

这样可以区分：

- 转谱错；
- PITD 错；
- DiffSinger 渲染偏离；
- 歌词/时值错。

---

## 16. 第一阶段验收标准

第一阶段目标不是“专业成品”，而是可靠、可编辑、明显唱对。

必须满足：

1. 默认 melody source 为 GAME；
2. 当前 heuristic 不再是主路径；
3. GAME 原始输出和 corrected 输出都保留；
4. 每个自动修改都有 evidence + before/after；
5. 不允许整首无解释地重写 GAME；
6. SAFE/PROBABLE/AMBIGUOUS 三层可区分；
7. ambiguous region 可直接定位试听；
8. lyrics 不再决定 melody note 数量；
9. corrected score 可生成有效 USTX；
10. OpenUtau 原生 note / phoneme validation 通过；
11. 人工试听确认主旋律基本与原曲一致；
12. 只有通过以上条件，才开始泠鸢风格迁移。

对于《年轮》当前基准，必须专门保存：

```text
GAME original USTX
corrected USTX
GAME original vocal render
corrected vocal render
reference vocal excerpt
repair audit.json
```

支持逐段 A/B。

---

## 17. 第二阶段：泠鸢 style profile

第一阶段通过后，再使用泠鸢本人歌曲分析：

- vibrato rate / depth 分布；
- portamento 类型与长度；
- 音头处理；
- 句尾处理；
- breath placement；
- dynamics / tension / breathiness 倾向；
- voice color 使用倾向；
- 不同音区的表现差异。

形成：

```text
style_profile.json
```

原则：

> 原唱决定“唱什么”；泠鸢参考决定“怎么唱”。

风格迁移不得修改已经通过第一阶段验收的主旋律，除非明确标记为风格性 ornament 且可以回退。

---

## 18. 建议代码结构

```text
src/agent2utau/
  transcription/
    game.py
    schema.py

  analysis/
    f0.py
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
    style_profile.py        # Phase 2

  evaluation/
    score_eval.py
    contour_eval.py
    render_eval.py
```

旧：

```text
analysis/notes.py
```

保留为：

```text
heuristic_fallback
```

不能继续作为默认旋律生成器。

---

## 19. 推荐实现顺序

### M2.1 — GAME baseline

- 接入 GAME；
- 导出 `melody_game.json`；
- 直接生成 GAME baseline USTX；
- 先人工试听 GAME 原始水平。

### M2.2 — structural F0 + Validator

- 建 raw/structural F0；
- 为 GAME 每个 note 计算 evidence；
- 只标异常，不修改。

### M2.3 — SAFE repair

先做最可靠：

- octave；
- 明显 wrong pitch；
- 极强证据 false split；
- 小范围 boundary shift。

### M2.4 — PROBABLE candidate system

- split；
- merge；
- missing/false note；
- 多候选 scorer；
- minimum improvement gate。

### M2.5 — GAME consensus + Agent review packet

- suspicious region 多参数复核；
- ambiguity 分类；
- 输出 Agent 可读 evidence packet。

### M2.6 — lyrics mapping

- corrected melody ↔ forced lyrics；
- melisma `+`；
- conflict 检查。

### M2.7 — PITD + render loop

- raw F0 → constrained PITD；
- DiffSinger render；
- contour / score / render 三层评价。

### M2.8 — 《年轮》第一阶段验收

- GAME baseline A/B corrected；
- 主旋律人工试听；
- repair audit；
- 通过后冻结 melody score。

### M3 — 泠鸢风格迁移

只有 M2.8 通过后开始。

---

## 20. 最终原则

1. **GAME 是骨架，不是绝对真值。**
2. **F0 是证据和演唱轨迹，不是主转谱器。**
3. **歌词决定唱什么字，不决定唱几个音。**
4. **自动纠错只改 suspicious regions，不重写整首。**
5. **原 GAME 永远保留为 Candidate 0 和可回退基线。**
6. **只有证据显著改善时才自动接受 repair。**
7. **复杂、模糊区域宁可 needs_review，不强行自动修。**
8. **先保证旋律正确，再生成 PITD。**
9. **先“唱对”，再做泠鸢风格。**
10. **所有自动修改必须可解释、可审计、可 A/B、可回退。**
