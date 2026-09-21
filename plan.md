# agent2utau — Reference Expression Transfer Plan

> 新执行计划，2026-09-21。
>
> 旧的“Agent 直接模仿歌手、直接画 PITD/表现曲线”路线停止使用。
> 已经验证的基础转谱、歌词映射、bridge、QA 与 written-score 约束统一以 `pipeline.md` 为准。
> `plan2.md` 保留为 written-score adjudication 历史/审计资料，不再负责新的表现迁移路线。

## 1. 目标

输入：

- 原唱/参考人声；
- 已经通过当前 pipeline 的 GAME + HubertFA 基础 USTX；
- 本机 `YousaV1.65b` DiffSinger。

输出：

- 保持 written score / lyrics / timing 正确的可编辑 USTX；
- 自动生成但可审计的 PITD / DYN / TENC / BREC / VOIC；
- 稳定 vibrato 尽量写成 note vibrato 参数，不规则部分才进入 PITD；
- 可选的 Yousa voice-color / style 参数；
- 每轮 render、测量、候选和回退证据。

核心思想：

```text
原唱决定“目标表现”
Yousa neutral render 决定“声库自身已经会怎么唱”
两者的差值 residual 决定“还需要补多少”
Agent 只决定“这是什么表现事件、应该保留/缩放/抑制多少”
程序负责真正生成曲线
```

## 2. 明确废弃的旧路线

以下方法不再作为主路径：

1. `reference F0 - written MIDI tone` 直接生成整条 PITD。
2. 固定 20 points/s 后再平滑，把所有细节统一当噪声。
3. 让 LLM/Agent 直接输出数百个 `x/y` 曲线点。
4. 仅凭“像不像泠鸢”的自然语言判断去重画音高线。
5. 用 PITD/vibrato 去掩盖 GAME written-note 错误。
6. 同时叠加 DiffSinger 自带 pitch predictor、手绘 PITD、OpenUtau vibrato，却不测最终实际 F0。

旧 `analysis/pitchcurve.py` 可保留作 regression baseline，但不再代表目标实现。

## 3. 外部参考实现

优先研究并复用 `NewComer00/expressive` 的思路，而不是从零发明：

- reference vocal 与 UTAU/DiffSinger render 对齐；
- PITD：参考 F0 与合成 F0 的 residual；
- DYN：RMS/dynamics feature；
- BREC / VOIC：breath/voice index；
- TENC：现有 heuristic baseline；
- FastDTW + MFCC/RMS/F0，必要时可选 mHuBERT；
- 最终写回 OpenUtau expression curve。

该项目为 MIT；若启用它可选的 mHuBERT 权重，必须单独记录对应模型许可，
不能把第三方权重许可混同为仓库 MIT。

本项目不要求原样 vendor 整个 Expressive。第一阶段先做 adapter/实验，
验证在《年轮》+ Yousa 上确实优于旧算法，再决定抽取哪些模块。

## 4. 总体流程

```text
pipeline.md 已验证基础 USTX
        │
        ├─ written-score / lyric / timing hard gate
        │
        ↓
生成 Yousa neutral USTX
        ↓
OpenUtau bridge render
        ↓
neutral_yousa.wav
        │
原唱 vocal.wav
        │
        ├─ HFA phoneme/nucleus anchors
        ├─ F0 / RMS / MFCC
        └─ optional mHuBERT
        ↓
anchor-constrained local alignment
        ↓
reference vs neutral residual features
        ↓
expression event decomposition
        ↓
PITD / vibrato / DYN / BREC / VOIC / TENC / color candidate
        ↓
adaptive curve compilation
        ↓
OpenUtau render
        ↓
measurement + listening QA
        ↓
bounded parameter search / Agent decision
        ↓
accepted expression USTX
```

## 5. Stage A — 冻结基础乐谱

表现迁移开始前必须满足：

- GAME/HFA 生成的歌词顺序正确；
- bridge inspect：0 invalidNotes / invalidPhonemes；
- written-score 未解决区域有明确 audit 状态；
- 不在本 stage 修改 note count、identity、lyrics、基础 timing；
- M2.5 QUALITY HOLD 的结构候选不能偷偷混进 style 阶段。

生成一个 immutable `base_score.ustx`，记录：

- file sha256；
- semantic notes hash；
- source vocal hash；
- singer/model/OpenUtau/bridge hash/version。

任何 material change 使后续 expression artifact stale。

## 6. Stage B — Yousa Neutral Render

目的不是“最终好听”，而是测量 **Yousa 对同一乐谱天然会唱成什么样**。

Neutral profile 第一版：

- 固定一个明确 voice color（先从 Normal 开始，但按语义名，不按索引猜）；
- 不写 reference-derived PITD；
- note vibrato = 0，避免把额外规则混进 baseline；
- DYN/TENC/BREC/VOIC 使用声库/renderer baseline；
- 不做后期压缩/混响；
- dry render，保留完整时间轴。

输出：

```text
neutral/base_score.ustx
neutral/yousa_neutral.wav
neutral/render_manifest.json
```

重新提取 neutral render 的 F0、RMS、voicing 等特征。

## 7. Stage C — 对齐：HFA hard anchor + 局部 feature alignment

不允许整首自由 DTW 随意扭曲时间。

### 7.1 一级 anchor

已有 HubertFA：

- char/phone span；
- vowel nucleus onset；
- phrase/LRC coverage。

这些构成局部 alignment window 的边界和顺序约束。

### 7.2 二级局部对齐

每个稳定 phrase/phoneme window 内，再使用：

- F0；
- MFCC；
- RMS；
- onset/energy；
- 可选 mHuBERT embedding。

实现可以参考 Expressive 的 FastDTW，但必须：

- 限定在相同歌词/phoneme carrier 内；
- 保持 monotonic；
- 不允许跨字交换；
- unvoiced/低置信区允许 unmatched；
- 输出 warp amount / confidence / failure reason。

如果 alignment 需要大幅扭曲才能匹配，该片段进入 `alignment_unreliable`，
不得直接生成高强度表现曲线。

## 8. Stage D — PITD 必须是 residual，不是 absolute imitation

正确目标：

```text
PITD_target(t)
≈ cents(F0_reference_aligned(t) / F0_yousa_neutral(t))
```

而不是：

```text
F0_reference - written_note_tone
```

原因：Yousa/DiffSinger 自己已有 pitch predictor 和自然 transition。
只补 residual 才能避免“双重滑音/双重颤音/过度偏移”。

### 8.1 F0 extraction

至少保留两个独立 F0 backend 做置信检查：

- torchfcpe/FCPE；
- RMVPE；
- third-F0 仅在冲突区使用。

低 coverage、octave conflict、unvoiced transition 不硬填曲线。

### 8.2 residual 分解

不要把 residual 当一条无语义折线。按 note/phoneme 拆成：

```text
slow intonation trend
+ onset scoop / overshoot
+ portamento
+ ornament
+ periodic vibrato
+ irregular residual
```

每个 event 输出参数化 representation 和 confidence。

## 9. Stage E — Vibrato 参数化

稳定 vibrato 优先检测为事件，而不是逐点 PITD：

- onset position；
- end position；
- rate Hz；
- depth cents；
- phase；
- fade-in；
- fade-out；
- drift；
- confidence。

检测建议：

1. 去掉 slow trend；
2. 在长 voiced note 后半段做局部频谱/autocorrelation；
3. 合理候选约 4–8 Hz，但不能仅靠频率阈值决定；
4. 要求连续若干周期、depth 稳定、F0 coverage 足够；
5. 与 ornament/portamento 竞争。

稳定周期事件编译到 OpenUtau note `vibrato`；
不稳定或非周期部分留给 PITD。

这样 Agent 调的是 `depth/rate/start`，不是几百个点。

## 10. Stage F — 自适应 PITD 曲线

禁止固定 `POINT_EVERY_SEC=0.05` 作为最终表示。

先在较高时间分辨率得到可信 residual，再做 error-bounded simplification：

- voiced transition/ornament：可保留 10–20ms 级细节；
- 稳音：几十到数百 ms 一个控制点即可；
- 使用 RDP / spline / piecewise cubic 等；
- 简化误差以 cents 限制，而不是固定点数；
- 第一版目标可从 max error 5–10 cents 做 A/B 校准；
- note/phoneme 边界附近单独保护关键点。

生成前后都保存 dense residual 和 compiled curve，保证可审计。

## 11. Stage G — DYN / BREC / VOIC / TENC

### DYN

不复制 reference 的绝对响度。

使用对齐后的局部 loudness/RMS envelope，计算：

```text
relative phrase dynamics(reference)
-
relative phrase dynamics(neutral)
```

并限制在自然范围，避免与 track gain / mix compressor 重复作用。

### BREC / VOIC

参考 Expressive 的 breath/voice index 做第一版，
但必须与 Yousa neutral 做 residual，而不是把真人绝对值直接映射到 OpenUtau。

重点区域：

- 句首气声；
- 尾音虚化；
- 弱声区；
- 明显 breath-to-voice transition。

### TENC

Expressive 当前的 tension 主要是基于 loudness/RMS 的 heuristic。
所以只把它当 baseline candidate，不把它当真人“声带张力 ground truth”。

第一版：

- neutral predictor 为基准；
- reference acoustic feature 给出 low-dimensional hint；
- Agent 只做 phrase-level bias/scaler；
- render 后再测，效果不好则关闭该 lane。

## 12. Stage H — Voice Color / 泠鸢 style

Color 不做逐帧 waveform regression。

先把五个 Yousa color 做受控 calibration render，建立：

```text
Bright
Cute
Normal
Whisper
Classic
```

在相同 note/lyric 上的声学差异和适用范围。

然后 style layer 只输出：

- phrase-level color；
- 少量平滑过渡；
- 必要时两种 color 的局部组合；
- confidence / rationale。

“泠鸢真人歌曲”只作为 style prior：
统计她常见的 vibrato start/depth、phrase dynamics、breathy ending 等分布，
不作为《年轮》的逐帧 target。

## 13. Agent 的新职责

### Agent 可以做

- 判断一个候选是 vibrato / scoop / portamento / ornament；
- 根据声学证据选择保留、缩放或丢弃；
- 为 phrase 设置少量参数：
  `pitd_scale`、`vibrato_depth_scale`、`dyn_scale`、`brec_bias`、color；
- 选择下一轮需要搜索/试听的参数；
- 读取 QA，决定是否 rollback。

### Agent 不可以做

- 从零手绘成百上千 PITD 点；
- 看到 reference F0 就直接复制；
- 用自然语言猜 exact F0；
- 在 written-score unresolved 时用表现参数“修听感”；
- 同时改多个 lane 后无法判断改善来源。

Agent 输出的是 **event + parameter decision**，确定性程序负责编译 USTX。

## 14. Stage I — Render loop / 参数搜索

每个 phrase 使用 bounded loop：

```text
neutral
→ extracted residual candidate
→ render
→ measure
→ candidate A/B
→ accept / scale / rollback
```

一次只主改一个参数 family，避免 attribution 混乱。

可用小规模优化器搜索连续参数：

- Optuna / CMA-ES / grid；
- PITD scaler；
- vibrato depth/start；
- DYN scaler；
- BREC bias；
- TENC bias。

目标函数不能只用一个 MOS：

- reference-vs-render F0 residual；
- pitch coverage；
- octave disagreement；
- temporal alignment；
- SingMOS-Pro；
- clipping / silence；
- 人工 phrase A/B。

自动指标负责筛异常，最终 style 优劣允许人工选择。

## 15. QA 与接受标准

每个 expression lane 都必须有 **neutral vs candidate** 比较。

### PITD

- render 实际 F0 是否更接近 aligned reference；
- 不得降低 voiced coverage；
- octave-conflict 区不得因错误 F0 被拉偏；
- onset/transition 不应出现尖锐折线。

### Vibrato

- rate/depth/start 与 reference event 接近；
- renderer 实际输出中确实存在对应周期；
- 不与 PITD 重复叠加造成 double vibrato。

### DYN/BREC/VOIC/TENC

- candidate 相比 neutral 有可测变化；
- 无不自然 jump；
- 不导致 phoneme 消失、噪声化或整体失衡；
- lane 无稳定收益时可以保持 neutral。

## 16. 实施里程碑

### R0 — Expressive baseline  ✅ 已完成（见 §18.1）

- clone/adapter Expressive；
- 选《年轮》3–5 个代表句；
- 用当前 base USTX render neutral；
- 生成 Expressive PITD/DYN/BREC/VOIC/TENC；
- A/B：neutral vs Expressive；
- 只验证，不先大改仓库。

### R1 — Residual PITD  🔄 原型已建，对齐未达标

- ✅ `expression/pitch_variants.py`（替代 `analysis/expression_pitch.py`）；
- ✅ reference vs neutral F0 residual；
- ⚠️ HFA anchor constrained alignment —— 已实现但产出不稳（见 §18.2 难点）；
- ⚠️ dense residual artifact —— 有 audit，尚无独立 dense 文件；
- ✅ adaptive curve compiler（RDP ε=8c，替代固定 20 points/s）；
- ❌ 尚不能替换旧主路径：C 在 3 个乐句上均未稳定优于 A/D。

### R2 — Event decomposition

- vibrato detector；
- onset scoop / portamento detector；
- event JSON schema；
- periodic vibrato → note vibrato；
- irregular → PITD。

### R3 — Other expression lanes

- dyn residual；
- brec/voic residual；
- tenc experimental lane；
- 每 lane 独立 enable/disable。

### R4 — Agent controller

- Agent 只消费 event JSON / QA；
- 输出 bounded parameter decisions；
- deterministic compiler；
- rollback。

### R5 — Yousa style profile

- 受控五 color calibration；
- 泠鸢真人歌曲统计；
- style prior；
- phrase-level color + parameter prior。

### R6 — Full-song acceptance

完整《年轮》：

- base written score 不被 style stage 改坏；
- 全曲 expression artifact 可追踪；
- neutral / expression / final 三版可复现；
- bridge reopen/render 通过；
- QA + 人工重点句试听通过。

## 17. 建议新增结构

```text
src/agent2utau/
  expression/
    pitch_variants.py   ✅ 已有：A/B/C 生成器 + RDP 简化（原型）
    align.py            ⬜ 待拆：HFA 锚点 / 局部 DTW（当前在 pitch_variants 内）
    pitch_residual.py   ⬜ 待拆：事件分解前的 residual 主路径
    events.py
    vibrato.py
    dynamics.py
    breath_voice.py
    tension.py
    simplify.py         ⬜ 待拆：RDP 目前在 pitch_variants 内
    compile_ustx.py
    controller.py

schemas/
  expression_alignment.schema.json
  expression_events.schema.json
  expression_plan.schema.json
  expression_eval.schema.json

runs/<id>/expression/
  neutral/
  alignment/
  dense/
  events/
  candidates/
  accepted/
```

## 18. 第一项实际任务

不要直接全曲实现。

先选《年轮》三个 phrase：

1. 普通稳音句；
2. 明显滑音/转音句；
3. 长音带颤音句。

对每句同时生成：

```text
A = current old pitchcurve.py
B = Expressive baseline
C = new residual prototype
D = neutral
SOURCE = 原唱 vocal
```

保持相同 base score、singer、color、context、gain。

先确认 **B/C 是否明显优于 A**。如果 residual 方法在这三类句型上都不能稳定改善，
先查 alignment/F0/renderer 叠加语义，不进入全曲开发。

### 18.1 实验结果（2026-09-21，run `expr-20260921`）

已完成 Stage A/B + 三乐句 A/B/C/D 渲染：

- Stage A：`runs/expr-20260921/expression/base_score.ustx` + `base_manifest.json`
  （392 notes，`vocal_pipeline`，sha256/notes_hash/singer/renderer 已记录）；
- Stage B：`neutral/ustx_neutral.ustx` + `neutral/yousa_neutral_vocal.wav` +
  `neutral/f0_neutral.npz`（剥 vibrato/pitch.data/phoneme 表达式字段）；
- 三乐句：`runs/expr-20260921/phrases/{P1_sustain,P2_slides,P3_vibrato}/`
  各含 A/B/C/D ustx+wav + src/SOURCE.wav + 汇总 `report.json`。

**中位 |渲染 F0 − 原唱 F0|（fcpe，越低越像原唱）：**

| | A 旧转写 | B Expressive | C residual | D neutral |
|---|---|---|---|---|
| P1 稳音 | 23.8 | **21.8** | 71.9 | 27.7 |
| P2 滑音 | 27.9 | **26.8** | 44.8 | 31.6 |
| P3 长音颤音 | **21.4** | 24.5 | 43.6 | 28.9 |

| p95 帧跳变（毛糙度） | A | B | C | D |
|---|---|---|---|---|
| P1 | 27.7 | 67.3 | 35.7 | **12.1** |
| P2 | 56.5 | 102.8 | 58.1 | **25.7** |
| P3 | 42.3 | 74.0 | 66.7 | **24.8** |

**判读：B/C 未"明显优于 A"——按 plan 规则触发 alignment 排查，不进入全曲开发。**

- B 贴原唱最近但最糙（DTW 把原唱连同毛刺一起 warp，265-473 点）；
- C 三轮对齐全部失败，见 §18.2；
- A 意外地不差——但它抄绝对 F0，不是目标架构；
- pitd 执行链本身已验证（意图 vs 渲染 corr=0.97），问题只在"算什么"。

### 18.2 当前难点：对齐是瓶颈

C 的 residual 概念已验证可行（`neutral + residual` 能忠实渲染出来），
败因全在"residual 用什么对齐"：

1. **per-note lag（±40ms 搜索）**：稳音上 lag 不可辨识，argmin 在噪声里乱跳，
   渲染比 neutral 更偏离原唱。
2. **全局 lag（±100ms 搜索）**：P1 搜到边界值——median-error 曲面对 lag 太平。
3. **HFA 锚点 warp**（plan 正解，已实现）：HFA 字起点比 GAME 音符起点
   **早 100-260ms**（辅音段归属不同），分段线性 warp 把原唱的过渡段
   拉进音体，residual 中位出现 -150~-240c 伪偏移。

深层原因：**GAME 音符边界和 HFA 字边界不是同一套时间基准**。
核(nucleus)在元音稳态区是可靠锚点；字起点(w0)含辅音，两边定义不一致，
直接当锚点会污染 residual。

### 18.3 待决策项

1. **C 的对齐方案**：
   a. 只用 nucleus↔nucleus 锚点（避开字起点争议，推荐先试）；
   b. |resid|>150c 的区域不算 residual，留给事件分解（onset/portamento
      单独建模，符合 Stage D 分层）；
   c. 用 neutral render 的音素时序反推 written 侧核位置（不假设 r 比例）。
2. **B 是否保留为对照基线**：它最贴原唱但不可解释、毛糙；
   建议保留作 upper-bound 参考，不进生产路径。
3. **QA 指标口径**：`med|render−ref|` 对"把表达重定时到 written grid"的
   方法有系统性惩罚（时序差被算两次）。需要一个 timing-invariant 指标
   （如 DTW 后误差 / 每音 lag 后误差）才能公平比较 residual 类方案。
4. **试听裁决**：数值排除不了 A vs B——需要人工听 `phrases/P*/` 下
   四变体 + SOURCE，确认"糙但像"(B) 与 "稳但偏"(A) 哪个更可接受，
   再决定 C 的修复方向投入。

## Definition of Done

系统不再依赖 Agent 手工模仿整条音高/表现曲线。

对一个已经唱对 written score 的 USTX，能够：

1. 渲染 Yousa neutral baseline；
2. 将原唱与 neutral 在歌词/音素约束下对齐；
3. 提取 reference-minus-neutral 的表现 residual；
4. 将 residual 拆成可解释的演唱事件；
5. 自动编译成 OpenUtau 可编辑参数；
6. 用 render loop 验证实际输出；
7. Agent 只做少量高层参数决策；
8. 所有变化都能与 neutral 比较、回滚和复现。
