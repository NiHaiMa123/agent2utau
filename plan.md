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

### 8.1 F0 evidence：以 residual consensus 为主

至少同时计算：

- FCPE；
- RMVPE；
- third-F0 只处理冲突区。

不能只检查 FCPE_source 与 RMVPE_source 是否差到一个八度。真正准备施加的是 residual，因此必须分别计算：

~~~text
r_fcpe(t) = FCPE_source(t) - FCPE_neutral(t)
r_rmvpe(t) = RMVPE_source(t) - RMVPE_neutral(t)
~~~

然后判断两个 extractor 对“需要补多少”是否一致。

例如：

~~~text
r_fcpe = +34c
r_rmvpe = +29c
→ residual_consistent

r_fcpe = +110c
r_rmvpe = +18c
→ extractor_sensitive / 不得直接写 PITD
~~~

当前 prototype 的 300c raw-F0 disagreement threshold 只够抓严重 octave/conflict，**不足以作为 expression transfer 的可信度 gate**。

v1 必须保存每帧：

- r_fcpe；
- r_rmvpe；
- residual disagreement；
- consensus residual；
- confidence/state。

F0 family 之间继续服从 pipeline.md 的 evidence-independence 规则；同一 extractor 既生成控制量又评价自己的结果时，不得把分数当独立验证。

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

### 10.0 Dense residual 是 observation，不是最终控制曲线

fixed-time residual 成立，只表示“这一时刻 SOURCE 与 neutral 在 F0 上差多少”。

**禁止把 dense residual 本身视为应该逐点复制的 ground truth。**

尤其当前 b5decb6 prototype 的 C1 仍只是 feature-preserving simplifier：

- 保留所有局部极值；
- 10ms 内变化 >40c 的 steep point 强制保留；
- 再按 vertical cents error 压缩。

这会同时保护真正的 vibrato/portamento 和 FCPE jitter/分离伪影/短促错误，因此当前 C1 **不得称为真正 event-aware**，也不得进入生产 acceptance。

真正的 Stage F 必须消费 Stage E 的 event JSON：

~~~text
dense observation
→ event classification
→ event parameters
→ deterministic curve compiler
~~~

### 10.1 曲线简化必须约束纵向 cents 重建误差

旧 RDP 把“秒”和“cent”放进二维欧氏距离，单位不成立；当前 vertical simplifier 修复了单位问题，但它只解决“压缩误差”，**没有解决“形状是否应该被保留”**。

最终简化器应只在同一已确认 event 内工作，并定义：

~~~text
error_i = |event_target(t_i) - interpolated_compiled_curve(t_i)|
~~~

验收约束：

- max / p95 cents reconstruction error；
- event keypoint 必须保留；
- voiced hole 不跨越填充；
- 不保护未分类的所有局部极值；
- 不因单帧 steep/jitter 自动保留控制点。

### 10.2 不强制所有 note boundary 回 0

只有证据显示 transition 确实回到 neutral，才写 0。

portamento / scoop / overshoot / vibrato 必须允许连续跨边界或接近边界。

### 10.3 形状优先于逐点贴合

不能以“median cents 越低”驱动编译器增加控制点。

如果增加点数只让 pointwise error 从 6c 降到 3c，却引入额外峰谷、折返或高频抖动，必须视为退化。

点数是结果，不是目标；正确 event topology 与 contour shape 高于逐帧数值贴合。

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

### 15.1 Pointwise pitch error 只是一项位置指标

same-time cents error 保留，但解释必须严格限定为：

> render 与 SOURCE 的 F0 在相同时间点上离得多远。

至少记录：

- median / p90 / p95 absolute cents；
- voiced coverage；
- octave conflict；
- per-note / per-event 分层统计。

它**不能**单独证明两条音高线“形状相似”或“听感相似”。

尤其 median 会天然忽略少量但听感显著的坏区；3–4c median 不得写成“高度复刻原唱”。

### 15.2 必须新增 contour-shape metrics

QA 至少同时测四个层级：

1. **position error**：当前逐帧 cents 位置误差；
2. **slope error**：一阶差分/局部音高变化速度是否一致；
3. **curvature error**：二阶差分/折返和弯曲方式是否一致；
4. **modulation structure**：局部周期、频谱、峰谷拓扑是否一致。

推荐基础定义：

~~~text
p(t) = pitch in cents

slope(t) = Δp / Δt
curvature(t) = Δ²p / Δt²

E_slope = robust(|slope_render - slope_source|)
E_curve = robust(|curvature_render - curvature_source|)
~~~

计算前只做经过声明的低通/稳健去噪版本，并同时保留 raw 诊断，避免把 extractor jitter 当成真实 shape。

### 15.3 Turning-point / topology QA

逐个 event window 比较：

- 峰数量；
- 谷数量；
- zero-crossing 数量；
- 峰谷顺序；
- 峰间距；
- 非 SOURCE 中出现的额外 turning points。

例如 SOURCE 一个平滑上拱只包含 1 peak，而 render 出现 4 peaks + 3 valleys，即使 median error 很低，也必须标记：

~~~text
extra_modulation / over_tracing
~~~

这类 topology mismatch 是当前 C1 最需要防止的问题。

### 15.4 Vibrato 必须按结构评估

P3/长音 vibrato 不以最低 frame jump 或最低 pointwise cents 为目标。

至少比较：

- start/end；
- rate Hz；
- depth cents；
- cycle-to-cycle period stability；
- depth envelope；
- phase continuity；
- drift；
- waveform regularity / extra cycles。

如果 render 每帧都接近 SOURCE，但周期忽快忽慢、深度乱变或多出峰谷，仍判 vibrato shape mismatch。

### 15.5 Cross-extractor validation，防止“同一测量器出题又判卷”

不能只做：

~~~text
FCPE residual → 生成 PITD → FCPE 评分
~~~

至少做交叉实验：

~~~text
C-F: FCPE residual 生成 → RMVPE 评价
C-R: RMVPE residual 生成 → FCPE 评价
C-consensus: 仅 residual-consistent 区生成 → FCPE + RMVPE 双评价
~~~

如果出现：

~~~text
FCPE→FCPE = 3c
FCPE→RMVPE = 25c
~~~

则 3c 只能解释为 measurement/extractor overfit，不能作为质量 PASS。

### 15.6 p95 frame jump 只能是 anomaly feature

10ms F0 jump 同时会响应真实 vibrato、portamento、ornament、extractor jitter 和错误尖刺，不能直接命名为“毛糙度”。

应改为比较：

- SOURCE 中已有的 modulation；
- render 新增的非预期 high-frequency modulation；
- event shape mismatch；
- extra spike / turning point。

### 15.7 Corr 不足以证明执行链正确

intent vs render corr≈0.97 只能说明趋势相关，还必须检查：

- gain；
- offset；
- absolute cents error；
- slope/curvature；
- local transition；
- saturation/clamp；
- coverage。

### 15.8 Neutral contract

任何 candidate 比较前必须证明：

- 同一 trusted score；
- 同一 singer；
- 同一 Normal color；
- 同一 renderer/profile；
- 同一 project time；
- 同一 phrase window；
- 不因 candidate 改 context/gain。

### 15.9 人工试听是 shape/perception gate，不是兜底形式

机器指标通过后仍需 phrase A/B。

试听时重点记录可操作标签：

~~~text
too_many_turns
too_wiggly
too_flat
wrong_vibrato_shape
wrong_portamento_shape
over_traced
extra_spike
natural / unnatural
~~~

人工听到明显异常而 pointwise metric 很好时，优先视为 QA metric blind spot，不得用低 cents 分数否定听感。

## 16. 实施里程碑

### R0 — Baseline integrity reset / formal close

b5decb6 工作流已报告 G0–G4，但 Git authority 仍需正式闭环：

- 392 vs pipeline verified 393 的 exact 1-note merge 必须回写 pipeline.md；
- 提交 superseding trusted score hash/note count；
- Yousa_Normal per-phoneme clr contract 固化；
- SOURCE/neutral project-time 与 bridge manifest 固化。

在 pipeline.md 未正式 supersede 393 baseline 前，不把 G0 标为 FROZEN。

### R1 — Fixed-Time Dense Residual  ✅ measurement prototype

b5decb6 已实现：

- no DTW / lag / warp；
- same-time dense residual；
- FCPE + RMVPE raw conflict observation；
- frame-state mask；
- dense artifact；
- C0/C1 render prototype。

但当前结论只能是：

~~~text
fixed-time residual measurement: PASS
direct residual → PITD quality: NOT ACCEPTED
3–4c median quality claim: INVALID
C1 event-aware claim: FALSE / prototype only
~~~

R1 下一补丁必须加入 residual-consensus 与 cross-extractor evaluation。

### R2 — Contour QA + Event Decomposition ← CURRENT QUALITY BLOCKER

- slope metric；
- curvature metric；
- turning-point/topology metric；
- modulation spectrum / local periodicity；
- residual consensus；
- onset scoop / overshoot；
- portamento；
- ornament；
- vibrato；
- timing/phoneme mismatch；
- event JSON schema。

先用 P1/P2/P3 证明：机器能区分“点位很近但形状不对”。

### R3 — True Event-Aware Curve Compiler

- 只消费已分类 event；
- vertical-cent error simplifier；
- 不保护所有 raw extrema/steep points；
- event keypoint protection；
- no forced-zero note boundaries；
- dense→event→compiled QA；
- shape metric 不退化。

### R4 — Closed-Loop PITD

- neutral → residual → event → compile → render → remeasure；
- 1–3 iteration bounded update；
- objective 同时包含 position + shape；
- 禁止为了压低 median cents 增加无意义曲线抖动；
- per-phrase rollback。

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
- pointwise + contour-shape QA；
- cross-extractor QA；
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

### 18.3 第二轮 fixed-time 实验状态（b5decb6）

第二轮修正了 warp 问题，fixed-time residual measurement 本身成立；但当前报告中的 3–4c median 不能作为听感/shape 成功证据。

原因：

1. 生成控制量和评分都高度依赖同一 F0 measurement family，存在 self-scoring/measurement overfit 风险；
2. C1 还没有真正 event decomposition，只是保留 extrema/steep point 的 vertical simplifier；
3. pointwise median/p90 只测位置，不测曲线运动方式；
4. median 对少量但听感显著的坏区不敏感；
5. P3 vibrato 仍可能被当成大量 PITD 点描摹，而不是结构化 vibrato event。

因此第二轮不得记为“residual quality confirmed”，只能记为：

~~~text
fixed-time residual framework: PASS
dense measurement path: PASS
direct dense residual to PITD: UNACCEPTED
contour/perceptual similarity: UNMEASURED
~~~

### 18.4 下一项实际任务

仍使用 P1/P2/P3，但先不追求更低 median cents。

必须生成并提交：

~~~text
qa/position_metrics.json
qa/slope_metrics.json
qa/curvature_metrics.json
qa/topology_metrics.json
qa/modulation_metrics.json
qa/cross_extractor_metrics.json
events/*.json
~~~

实验至少包括：

~~~text
D  = neutral
C0 = dense residual diagnostic
C1 = current simplifier（仅 regression）
C2 = residual-consensus + event-aware compiler
SOURCE
~~~

并执行：

~~~text
FCPE-generated → RMVPE evaluation
RMVPE-generated → FCPE evaluation
consensus-generated → both evaluation
~~~

第一轮 shape acceptance：

- P1：不能为了压低 cents 引入额外峰谷/高频 modulation；
- P2：transition trajectory 的 slope/curvature/topology 应比 D 更接近 SOURCE；
- P3：必须先产生 vibrato event（rate/depth/start/period stability），再编译；禁止直接以 100+ PITD 点描 vibrato；
- 人工试听若明确认为 C2 比 D/C1 更自然，而 pointwise cents 略差，允许 C2 胜出；
- pointwise metric 与 contour/perceptual metric 冲突时，不得以 median cents 单独裁决。

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
10. expression stage 不破坏 pipeline.md 已验证的 written score / lyrics / timing；
11. QA 同时覆盖 pitch position、slope、curvature、turning-point/topology、modulation structure；
12. 生成与评价至少存在 cross-extractor 验证，不允许同一 extractor 的自评分单独 PASS；
13. vibrato / portamento / ornament 等主要 gesture 以 event 结构验证，不以逐帧 cents 最低为唯一目标；
14. 人工试听与机器指标冲突时，必须形成可解释的 metric-blind-spot artifact，而不是用低 cents 分数覆盖听感。
