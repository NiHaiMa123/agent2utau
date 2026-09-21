# agent2utau — Fixed-Time Residual Expression Transfer Plan

> 修订日期：2026-09-21。
>
> 旧的“Agent 直接模仿歌手、直接画 PITD/表现曲线”路线停止使用。
> 2026-09-21 第一轮 A/B/C/D expression 实验也**不得用于路线裁决**：该实验把本来共享绝对时间轴的问题重新做成了 alignment/warp 问题，并存在 baseline/简化实现缺陷，详见 §18。
>
> 已验证的基础转谱、歌词映射、bridge、F0 语义与 written-score 约束统一以 pipeline.md 为准。
> plan2.md 只保留 written-score adjudication 的历史/冻结 contract，不再负责表现迁移路线。

## 1. 目标

输入：

- 原唱/参考人声；
- 已通过当前 pipeline.md 的 GAME + HubertFA 基础 USTX；
- 本机 YousaV1.65b DiffSinger。

输出：

- 保持 written score / lyrics / timing 正确的可编辑 USTX；
- 自动生成但可审计的 PITD / DYN / TENC / BREC / VOIC；
- 稳定 vibrato 尽量参数化，不规则部分才进入 PITD；
- 可选的 Yousa voice-color / style 参数；
- 每轮 render、测量、候选、rollback 与 provenance。

核心思想：

~~~text
GAME/HFA 已经给出与原唱共享的绝对乐谱时间轴
        ↓
在同一个 t 上比较 SOURCE 与 Yousa neutral
        ↓
reference(t) - neutral(t) = 需要补偿的表现 residual
        ↓
先识别 event，再编译参数
        ↓
render → 再测实际误差 → 小步闭环修正
~~~

Agent 只做“事件/策略/幅度”的高层判断；程序负责信号测量、曲线生成、渲染和验收。

## 2. 明确废弃/禁止的路线

以下方法不再作为生产主路径：

1. reference F0 - written MIDI tone 直接生成整条 PITD。
2. 为了计算 residual，先对 SOURCE 与 neutral 做全局/逐 note DTW、lag search 或 piecewise warp。
3. 把 HFA w0 当 GAME note onset 的时间锚点。
4. 固定 20 points/s 后统一平滑。
5. 让 Agent/LLM 直接输出大量 x/y 曲线点。
6. 用 PITD/vibrato/portamento 掩盖 written-note pitch/timing/identity 错误。
7. 对每个 note 边界强制 PITD 回 0，从而切断真实跨音 transition。
8. 在 event classification 前简单丢弃所有“大 residual”，把真实 onset/portamento/ornament 一起删除。
9. 用单一相关系数、单一 MOS 或“p95 帧跳变越低越好”作为路线 winner。
10. 在没有确认 neutral singer/color/score 完全一致前做 A/B/C/D 裁决。

旧 analysis/pitchcurve.py 与 expression/pitch_variants.py 仅保留为 regression / failed-prototype 证据，不代表目标实现。

## 3. 外部参考实现的定位

NewComer00/expressive 仍然值得研究，但定位改为**技术参考与独立对照**，不是当前生产架构的时间对齐 authority。

可借鉴：

- reference 与 synthesized render 的 residual 思路；
- F0 / RMS / MFCC / breath-voice feature 提取；
- DYN / BREC / VOIC / TENC 的表达参数构造；
- OpenUtau expression 写回；
- smoothing / visualization / audit 工具。

不能直接照搬：

- 将自由 DTW 作为本项目 residual 的默认前置步骤；
- 把其 heuristic TENC 当 ground truth；
- 未经核对就把自写 “Expressive-style” prototype 称为真正 Expressive baseline。

如后续需要 Expressive 对照，必须实际调用/适配其真实实现并记录版本/commit/config；否则只能标成 expressive_style_prototype。

该项目为 MIT；若启用其可选 mHuBERT 权重，单独记录模型许可。

## 4. 总体流程

~~~text
pipeline.md verified base USTX
        ↓
Stage A: freeze exact score / singer / color / timing
        ↓
Stage B: Yousa neutral dry render
        ↓
SOURCE 与 neutral 保持同一 project absolute time
        ↓
Stage C: HFA/GAME 只做 carrier / identity / voiced-region 约束
        ↓
Stage D: same-time dense residual
        ↓
Stage E: event decomposition
  ├─ stable intonation
  ├─ onset scoop / overshoot
  ├─ portamento / transition
  ├─ ornament
  ├─ vibrato
  └─ timing/phoneme mismatch / extractor conflict
        ↓
Stage F: event-aware parameter compilation
        ↓
OpenUtau bridge render
        ↓
Stage I: same-time closed-loop error measurement
        ↓
bounded correction / accept / rollback
        ↓
Stage G/H: DYN/BREC/VOIC/TENC + Yousa style
~~~

**核心变化：默认流程里没有 SOURCE↔neutral time warp。**

## 5. Stage A — 冻结唯一可信基础乐谱

表现迁移开始前必须满足：

- GAME/HFA lyric sequence 正确；
- bridge inspect：0 invalidNotes / invalidPhonemes；
- written-score unresolved 区域有明确 audit 状态；
- 本 stage 不改 note count / identity / lyrics / base timing；
- M2.5 QUALITY HOLD 的 structure candidate 不得进入 style stage；
- 当前《年轮》base 必须与 pipeline.md 最新 verified artifact 对上。

当前特别 gate：

- pipeline.md 已记录《年轮》填词后 **393 notes**；
- 第一轮 expression 实验写的是 **392 notes**；
- 在解释并验证这 1-note 差异前，该实验的所有 A/B/C/D 结果不得作为路线证据。
- 如果后续确有更新后的 392-note trusted score，必须先把其来源、diff、bridge validation、semantic notes hash 回写 pipeline.md，再 supersede 393-note baseline。

生成 immutable：

~~~text
base_score.ustx
base_manifest.json
~~~

manifest 至少绑定：

- full file sha256；
- semantic notes hash；
- note count；
- source vocal sha256；
- singer / phonemizer / renderer；
- OpenUtau / bridge version/hash；
- color semantic name + 实际 expression 映射。

任何 material change 使后续 expression artifact stale。

## 6. Stage B — Yousa Neutral Render

Neutral 的目的：测量 **Yousa 对完全相同 written score 自己会唱成什么样**。

第一版：

- 明确固定 Yousa_Normal，按语义名写入，而不是依赖默认 option index；
- 不写 reference-derived PITD；
- note vibrato 设为 0；
- 保留声库/phonemizer 正常工作所需字段；
- **不得粗暴删除所有 phoneme_expressions**，因为 clr 本身就是 per-phoneme expression；
- 对每个 note/phoneme 验证实际 color 都是 Normal；
- DYN/TENC/BREC/VOIC 从 neutral baseline 开始，不注入 reference-derived curve；
- 不做后期 EQ/compression/reverb；
- dry render，保留项目绝对时间轴。

输出：

~~~text
neutral/base_score_neutral.ustx
neutral/yousa_neutral.wav
neutral/render_manifest.json
neutral/f0_neutral.*
~~~

验收：

- score semantic hash 与 Stage A 一致；
- singer/renderer/color 一致；
- wave 起点/总时间轴一致；
- bridge reopen/render 通过；
- 实际 render 非静音、无截断。

## 7. Stage C — 固定时间轴 + Carrier Masks

### 7.1 不做默认 time alignment

GAME note 与 SOURCE 来自同一原唱时间轴，neutral 又从该 score 渲染，所以默认比较：

~~~text
SOURCE F0 at t
vs
neutral F0 at the same t
~~~

如果 neutral 在某个 transition 上比 SOURCE 晚 50ms，这首先是**表现/合成误差本身**，不能在 residual 前通过 DTW 把它消掉。

只有在发现工程级固定 offset（例如 bridge/wav 导出产生整体常量偏移）时，才允许：

- 用独立的脉冲/已知时间标记测量；
- 一次性校正 deterministic global transport offset；
- 写入 manifest；
- 禁止靠 F0 “搜最佳 lag”反推出 offset。

### 7.2 HFA 的正确职责

当前 pipeline 已验证：

> GAME sung note onset ≈ HFA vowel nucleus onset，典型 ≤10ms。

因此：

- nucleus 用于确认 lyric carrier / vowel onset / token identity；
- w0 是字/音素起点，可能比有声核早 100–260ms，**不能**直接映射为 GAME note onset；
- HFA 用于定义“这帧属于哪个字/元音/phoneme region”，不是 time-warp control points；
- 同字多 note / melisma 仍以 GAME note identity + HFA lyric mapping 为准。

### 7.3 Frame state

每个约 10ms frame 至少分类：

~~~text
same_note_both_voiced
source_only_voiced
neutral_only_voiced
both_unvoiced
extractor_conflict
note_transition
phoneme_transition
~~~

只有适合 PITD 的 frame 才进入 dense pitch residual。

## 8. Stage D — Same-Time Dense PITD Residual

基础定义：

~~~text
residual_cents(t)
= 1200 * log2(F0_source(t) / F0_neutral(t))
~~~

条件：

- SOURCE 和 neutral 使用相同绝对 project time t；
- 两边都 voiced；
- 至少两个独立 F0 family 对 octave/voicing 没有 material conflict；
- frame 已绑定到合法 note/lyric carrier。

### 8.1 F0 evidence

至少：

- FCPE；
- RMVPE；
- third-F0 只处理冲突区。

F0 family 之间按 pipeline.md 的 evidence-independence 规则处理。

### 8.2 不把所有 residual 都当 PITD

下列情况先路由，不直接写 PITD：

- SOURCE voiced、neutral unvoiced → timing/phoneme/renderer lane；
- neutral voiced、SOURCE unvoiced → release/timing lane；
- octave conflict → extractor-conflict lane；
- note identity unresolved → block；
- transition 区大偏差 → event decomposition；
- stable voiced body 的连续偏差 → PITD/intonation candidate。

**禁止简单用 |residual| > 150c 一类阈值直接删除。**
大偏差可能正是真实 scoop / portamento / ornament，也可能是 extractor error；必须先分类。

### 8.3 保存 dense truth

在任何简化前保存：

~~~text
dense/source_f0.*
dense/neutral_f0.*
dense/frame_state.*
dense/residual_cents.*
dense/evidence.*
~~~

后续所有简化/事件/曲线都必须能追溯回 dense artifact。

## 9. Stage E — Event Decomposition

先从 dense residual 识别事件，再决定 OpenUtau 表示。

### 9.1 Stable intonation

- note body 内低频慢变；
- 可以编译到 PITD；
- 不跨 extractor-conflict hole 强插值。

### 9.2 Onset scoop / overshoot

- note/nucleus 附近的短时单向或反向偏移；
- 保留其真实绝对时间；
- 不通过 warp 消掉；
- 不强制 note start PITD=0。

### 9.3 Portamento / transition

- 前后 note 的跨边界连续音高轨迹；
- 允许跨 note boundary；
- 不能因为每个 note 独立处理而截断；
- 与 written split/structure error 区分：written score 已冻结；若证据指向 score 错误则回 written-score lane，而不是 style lane 修。

### 9.4 Ornament

- 短转音、倚音式连续 F0 轨迹；
- 先判断是 written note 还是 expression；
- structure unresolved 时不得 style 化掩盖。

### 9.5 Vibrato

参数化：

- start/end；
- rate Hz；
- depth cents；
- phase；
- fade-in/out；
- drift；
- confidence。

稳定周期事件优先编译到 note vibrato 或明确的 periodic representation；非周期余量留 PITD。

### 9.6 Timing/phoneme mismatch

如果差异本质是 voiced onset/release 时间不同，而不是同一时刻的音高偏差：

- 不用 PITD 修；
- 记录为 timing/phoneme/renderer event；
- 后续另开 lane 调 duration/phoneme timing/variance，且不得越过 Stage A written-score contract。

## 10. Stage F — Event-Aware Curve Compilation

### 10.1 不再使用当前 RDP 的混合单位几何距离

当前 prototype 把“秒”和“cent”放进二维欧氏距离，再声称 eps=8c，单位不成立。

新简化器必须定义为**纵向 cents 重建误差**：

~~~text
error_i = |dense_residual(t_i) - interpolated_compiled_curve(t_i)|
~~~

验收直接约束：

- max / p95 cents reconstruction error；
- event keypoint 必须保留；
- voiced hole 不跨越填充；
- note/phoneme transition keypoint 单独保护。

### 10.2 不强制所有 note boundary 回 0

只有证据显示 transition 确实回到 neutral，才写 0。

portamento / scoop / overshoot / vibrato 必须允许连续跨边界或接近边界。

### 10.3 初始精度

第一版可从：

- stable body：p95 reconstruction error ≤5–10c；
- transition/event：保护关键 extrema/zero-crossing/phase points；

开始做 A/B 校准。

点数是结果，不是目标。

## 11. Stage G — DYN / BREC / VOIC / TENC

这些 lane 同样默认在**共享绝对时间轴**上测量，不先自由 DTW。

### DYN

比较 phrase-relative loudness/RMS envelope：

~~~text
relative SOURCE dynamics(t)
-
relative neutral dynamics(t)
~~~

避免复制绝对响度/压缩/混响。

### BREC / VOIC

可参考 Expressive 的 breath/voice index，但做 SOURCE-vs-neutral residual。

重点：

- onset breath；
- ending de-voice；
- weak voice；
- breath→voice transition。

### TENC

Expressive-style RMS heuristic 只能当 candidate。

第一版：

- neutral variance predictor 为基准；
- SOURCE feature 只生成低维 hint；
- phrase-level bias/scaler；
- render 后验证；
- 没稳定收益就保持 neutral。

## 12. Stage H — Voice Color / Yousa Style

Color 不做逐帧 waveform regression。

先对五种 Yousa color 做受控 calibration render：

~~~text
Bright
Cute
Normal
Whisper
Classic
~~~

必须在相同 score/lyric/context 下比较，并确认实际 clr per-phoneme mapping。

style layer 输出：

- phrase-level color；
- 少量平滑过渡；
- confidence；
- rationale。

泠鸢真人歌曲只提供 style prior，例如：

- vibrato start/depth/rate 分布；
- breathy ending；
- phrase dynamics；
- color/timbre 倾向。

不作为《年轮》逐帧 target。

## 13. Agent 的职责

### Agent 可以做

- 判断 event 类型；
- 判断 extractor conflict 是否应 block；
- 选择保留/缩放/丢弃某个 event candidate；
- 给 phrase 设少量 bounded 参数；
- 选择下一轮要搜索的参数；
- 读取 QA 决定 accept / retry / rollback。

### Agent 不可以做

- 手绘数百/数千 PITD 点；
- 自由 warp SOURCE 来“让指标更好看”；
- 看到 reference F0 就逐帧复制；
- 在 written-score unresolved 时做 style 补丁；
- 同时修改多个 lane 而无法 attribution。

输出是：

~~~text
event decision
+ bounded parameters
+ provenance
~~~

确定性程序负责编译 USTX。

## 14. Stage I — Closed-Loop Render Correction

对于 stable voiced residual，优先做小步闭环，而不是一次性假设 PITD 完全线性：

~~~text
PITD_0(t) = 0
render_0

error_0(t) = SOURCE_F0(t) - render_0_F0(t)

PITD_1(t) = compile(alpha * error_0(t))
render_1

error_1(t) = SOURCE_F0(t) - render_1_F0(t)

PITD_2(t) = PITD_1(t) + compile(alpha * error_1(t))
...
~~~

规则：

- alpha 初始 <1，避免 overshoot；
- 通常 1–3 次；
- 只在 same-note / both-voiced / extractor-consistent frame 更新；
- event lane 与 stable-body lane 分开；
- error 不下降则 rollback；
- 不允许迭代把 written-score error 吸进 PITD。

这比“先把两条 F0 warp 成一样再求差”更符合当前项目已有的共同时间轴。

## 15. QA 与接受标准

### 15.1 主指标必须使用真实共同时间轴

PITD 主指标：

- same-time |F0_render(t)-F0_SOURCE(t)|；
- voiced coverage；
- octave conflict count；
- per-event reconstruction；
- note/phrase 分层统计。

**DTW-after-error 只能作为 diagnostic，不得作为生产优化目标。**
否则会把 transition timing error 本身消掉。

### 15.2 不再把 p95 frame jump 直接叫“毛糙度”

10ms F0 jump 会同时响应：

- 真 vibrato；
- 真 portamento；
- ornament；
- extractor jitter；
- 错误尖刺。

因此只能作为 anomaly feature。

真正需要比较：

- 与 SOURCE 对应 event 的 rate/depth/trajectory 差；
- 高于 SOURCE 的非预期 high-frequency residual；
- curve reconstruction error；
- render 是否产生额外 spike。

### 15.3 Corr 不足以证明执行链正确

intent vs render corr≈0.97 只能说明趋势相关。

还必须检查：

- gain；
- offset；
- absolute cents error；
- local transition；
- saturation/clamp；
- coverage。

### 15.4 Neutral contract

任何 candidate 比较前必须证明：

- 同一 trusted score；
- 同一 singer；
- 同一 Normal color；
- 同一 renderer/profile；
- 同一 project time；
- 同一 phrase window；
- 不因 candidate 改 context/gain。

## 16. 实施里程碑

### R0 — Baseline integrity reset ← CURRENT

旧 expr-20260921 不能算 R0 完成。

必须先：

- 解释 392 vs verified 393 notes；
- 重建 trusted Stage A base；
- 重建确定为 Yousa_Normal 的 neutral；
- 验证没有错误删除 clr per-phoneme expression；
- 验证 SOURCE / score / neutral 的 project absolute time；
- 固化 manifest/hash。

### R1 — Fixed-Time Dense Residual

- 新建真正的 expression/pitch_residual.py；
- 不调用 DTW / lag search / HFA warp；
- same-time FCPE + RMVPE；
- frame-state mask；
- dense residual artifact；
- 三个 phrase 跑通。

### R2 — Event Decomposition

- onset scoop / overshoot；
- portamento；
- ornament；
- vibrato；
- timing/phoneme mismatch；
- event JSON schema。

### R3 — Correct Curve Compiler

- vertical-cent error simplifier；
- event keypoint protection；
- no forced-zero note boundaries；
- render round-trip；
- dense→compiled reconstruction QA。

### R4 — Closed-Loop PITD

- neutral → residual → render → residual correction；
- 1–3 iteration bounded update；
- per-phrase rollback；
- prove error decreases。

### R5 — Other Expression Lanes

- dyn residual；
- brec/voic residual；
- tenc experimental；
- lane-isolated QA。

### R6 — Agent Controller

- Agent 消费 event/evidence/QA；
- bounded parameter decision；
- deterministic compile；
- rollback。

### R7 — Yousa Style Profile

- 5 color calibration；
- 泠鸢真人歌统计；
- style prior；
- phrase-level style mapping。

### R8 — Full-Song Acceptance

完整《年轮》：

- base score 不被 expression stage 改坏；
- neutral / dense / events / compiled / final 全部可追踪；
- bridge reopen/render；
- same-time QA；
- 人工重点句试听。

## 17. 建议目录

~~~text
src/agent2utau/
  expression/
    pitch_variants.py      # failed experiment/regression only
    pitch_residual.py      # fixed-time dense residual
    frame_state.py
    events.py
    vibrato.py
    portamento.py
    dynamics.py
    breath_voice.py
    tension.py
    simplify.py            # vertical-cent reconstruction error
    compile_ustx.py
    controller.py

schemas/
  expression_dense.schema.json
  expression_events.schema.json
  expression_plan.schema.json
  expression_eval.schema.json

runs/<id>/expression/
  base/
  neutral/
  dense/
  events/
  candidates/
  renders/
  accepted/
~~~

不再把 alignment/ 作为默认生产 stage；只有 transport-offset diagnosis 或独立对照实验才使用。

## 18. 2026-09-21 第一轮实验：INVALID FOR ROUTE SELECTION

run：expr-20260921

该轮 A/B/C/D 可以保留作 regression/debug artifact，但**不能用于判断 A/B/C/D 哪条路线更好**。

### 18.1 为什么无效

#### A. C 的 HFA warp 与 verified pipeline 相冲突

prototype _build_anchor_warp() 做了：

~~~text
GAME note start → HFA w0
推算 written nucleus → HFA nucleus
~~~

但 pipeline.md 已验证：

~~~text
GAME sung onset ≈ HFA vowel nucleus
~~~

因此 100–260ms 的所谓“GAME vs HFA 对齐差”主要是 prototype 主动把有声 note onset 映射到了更早的辅音/字起点。

结论：

- 不是“还需要更好的 HFA warp”；
- 是**默认不应 warp**。

#### B. B 不是严格的 Expressive baseline

当前 variant_B 是本项目自写的 FastDTW prototype。

它没有资格把结果归因成“Expressive 本身粗糙”。

同时当前实现对 FastDTW path 的 duplicate index / warp curve 处理也未达到可作为 reference baseline 的严格程度。

后续若需要 B，只能：

~~~text
B_real = actual Expressive adapter
B_proto = current expressive_style_prototype
~~~

分开命名。

#### C. C 在代码层主动删除了关键表现区

prototype：

- note 前约 90ms 不算 residual；
- note 尾约 40ms 不算；
- 每个 note start/end 强插 0。

这会系统性删除：

- onset scoop；
- overshoot；
- portamento；
- 跨 note transition。

因此用 P2 “滑音句”评价该 C，本身就是不公平/不完整实现。

#### D. RDP 的 eps=8c 实际不是 8 cents

当前 RDP 对 (seconds, cents) 使用二维几何距离。

秒和 cents 混在同一个欧氏空间，单位不成立。

因此“C 只需要 24–40 个点且误差 8c”之类的解释无效。

#### E. Base score 数量存在 392 vs 393 未解释差异

pipeline.md verified 年轮结果：393 notes。

实验 manifest/plan：392 notes。

在解释这一差异前，无法确认四个 variant 使用的是当前 trusted score。

#### F. Neutral color contract 未证明

实验记录称 neutral 会“剥 phoneme expressions”。

但 Yousa clr 是 per-phoneme expression，默认 option 0 又不是 Normal。

如果删除方式导致 Normal 语义丢失，neutral baseline 就不再是 plan 要求的 Yousa_Normal。

### 18.2 旧数值只保留作 debug

原实验报告中的：

- median F0 error；
- p95 frame jump；
- PITD point count；
- intent/render corr；

全部保留用于复现 bug/变化，但不得再写成路线 winner/loser。

尤其：

- p95 frame jump ≠ perceptual roughness；
- corr≈0.97 ≠ 执行链完全正确；
- B_proto 贴近 SOURCE ≠ Expressive 已验证；
- C_proto 失败 ≠ fixed-time residual 概念失败。

### 18.3 新的第一项实际任务

不要先试听旧 B/C。

按下面顺序重跑三个 phrase：

1. P1：稳音；
2. P2：滑音/transition；
3. P3：长音 vibrato。

先做 contract gate：

~~~text
G0 trusted score note count/hash matches pipeline
G1 neutral confirmed Yousa_Normal
G2 SOURCE and neutral project time aligned by construction
G3 bridge/render manifest valid
G4 FCPE/RMVPE frame clocks verified
~~~

然后只生成：

~~~text
D = neutral
A = legacy absolute-F0 baseline（diagnostic only）
C0 = fixed-time dense residual, no simplification
C1 = fixed-time event-aware compiled residual
SOURCE
~~~

可选：

~~~text
B_real = actual Expressive implementation
~~~

但 B_real 不是 R1 的 blocker。

第一轮验收：

- P1：C1 same-time F0 error 应稳定低于 D；
- P2：不得通过 warp 消除 transition timing；C1 应保留/改善 SOURCE transition trajectory；
- P3：先识别 vibrato event，再比较 rate/depth/start，不以最低 frame jump 为目标；
- C1 若不优于 D，先查 dense residual / event classification / renderer response，不进入全曲。

## Definition of Done

对一个已经唱对 written score 的 USTX，系统能够：

1. 锁定唯一 trusted base score / singer / Normal color / absolute time；
2. 渲染 Yousa neutral baseline；
3. 不做默认 time warp，在同一绝对时刻比较 SOURCE 与 neutral；
4. 生成有 evidence mask 的 dense residual；
5. 将 residual 拆成 stable intonation / onset / transition / ornament / vibrato / timing-conflict 等事件；
6. 用有物理单位意义的误差约束编译 OpenUtau 参数；
7. render 后在同一时间轴重新测量并做 bounded closed-loop correction；
8. Agent 只做少量高层事件与参数决策；
9. 所有变化都可追踪、回滚、复现；
10. expression stage 不破坏 pipeline.md 已验证的 written score / lyrics / timing。
