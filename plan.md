# agent2utau — Implementation Plan

> 目标：输入一首原曲音频，自动分析原唱，使用本地 **泠鸢 DiffSinger** 声库生成可编辑的 OpenUtau 工程，并最终输出完成度足够高的翻唱成品。
>
> 核心原则：**Agent 负责判断、编排、诊断和迭代；音频分析、音高提取、工程生成、渲染、评价等关键步骤尽量由确定性工具完成。不要让 Agent 依赖像素坐标逐个点击 OpenUtau，也不要把原唱逐帧 F0 原样复制成 pitch 曲线。**

---

## 1. 最终用户体验

第一阶段最终应做到：

```bash
agent2utau cover "input/song.wav" \
  --singer "泠鸢" \
  --output "output/song_cover.wav"
```

用户只必须提供原曲。

允许提供可选信息以提升结果，但不能成为默认流程的硬依赖：

```bash
--lyrics lyrics.txt
--instrumental instrumental.wav
--vocal vocal.wav
--bpm 128
--key C#m
--openutau-path "C:/OpenUtau/OpenUtau.exe"
--voicebank-path "C:/Users/.../OpenUtau/Singers/..."
```

默认输出：

```text
output/<song>/
├─ final_cover.wav                 # 最终翻唱
├─ vocal_render.wav                # DiffSinger 干声
├─ accompaniment.wav               # 分离得到的伴奏
├─ reference_vocal.wav             # 分离得到的原唱参考
├─ project.ustx                    # 可继续人工编辑的 OpenUtau 工程
├─ analysis.json                   # 结构化分析结果
├─ evaluation.json                 # 自动评价结果
├─ report.md                       # 本次生成/修正记录
└─ debug/                          # F0、note、alignment、curve 等调试数据
```

---

# 2. 第一版范围

## 2.1 必须支持

第一版优先处理以下歌曲：

- 中文歌曲；
- 单主唱或主唱明显；
- 常规流行唱法；
- 有明确旋律；
- 原曲中人声与伴奏可以较好分离；
- 使用泠鸢 DiffSinger 声库；
- Windows + OpenUtau；
- 最终必须生成 `.ustx`，而不是只生成一段不可编辑音频；
- 从输入原曲到最终翻唱默认不需要人工逐音符调校。

## 2.2 第一版暂不追求

以下问题放到后续版本，不能阻塞 MVP：

- 多人合唱自动拆分；
- 多声部和声自动重建；
- Rap 的复杂节奏/音高混合建模；
- 极端气声、尖叫、哭腔等特殊发声；
- 完整复刻原唱音色；
- 自动训练新的 DiffSinger 声库；
- 用 OpenUtau 完成完整母带制作；
- 对所有歌曲都保证“一次生成即最终成品”。

项目目标是自动生成**可靠的第一版翻唱并自动迭代修正明显问题**，而不是假设任何一次分析都绝对正确。

---

# 3. 总体架构

```text
Original Song
    │
    ▼
[1] Audio Preprocess
    │
    ├──► Vocal Separation ──────► reference_vocal.wav
    └──► Accompaniment ─────────► accompaniment.wav
                                   │
                                   ▼
[2] Reference Analysis
    ├── BPM / beat / tempo map
    ├── lyric transcription + alignment
    ├── frame-level F0 + confidence
    ├── voiced/unvoiced mask
    ├── note segmentation
    ├── phrase segmentation
    ├── dynamics envelope
    └── expressive pitch features
                                   │
                                   ▼
[3] Score Reconstruction
    ├── clean note skeleton
    ├── lyric-to-note mapping
    ├── note timing
    ├── phoneme timing hints
    └── expression curves
                                   │
                                   ▼
[4] OpenUtau Project Builder
    ├── .ustx
    ├── singer / phonemizer / renderer settings
    ├── notes + lyrics
    ├── pitch
    ├── dynamics
    └── DiffSinger expressions
                                   │
                                   ▼
[5] OpenUtau / DiffSinger Render
                                   │
                                   ▼
[6] Automatic Evaluation
    ├── pitch accuracy
    ├── octave errors
    ├── timing
    ├── lyric/phoneme alignment
    ├── dynamics consistency
    └── audible artifact checks
                                   │
                fail ─────────────┘
                 │
                 ▼
[7] Agent Diagnosis + Targeted Retune
                 │
                 └──────────────► rerender

                pass
                 │
                 ▼
[8] Mix with accompaniment
                 │
                 ▼
            final_cover.wav
```

---

# 4. 核心设计原则

## 4.1 OpenUtau 是工程与最终渲染基准，不是主要控制界面

OpenUtau 当前官方版本已经包含 DiffSinger 支持，因此以官方 OpenUtau 为基准。

优先级：

1. 直接读写结构化工程数据；
2. 调用稳定 API / renderer；
3. 调用命令或内部接口；
4. 最后才使用 UI Automation；
5. 禁止把屏幕坐标点击作为核心逻辑。

原因：GUI 自动化很容易被窗口大小、DPI、主题、弹窗、版本更新破坏。

第一版允许为了完成“导入/刷新/导出音频”等缺少稳定外部接口的动作使用 Windows UI Automation，但必须封装在单独 adapter 中。

## 4.2 Agent 不直接“猜”音乐数据

LLM/Agent 不应该逐帧生成 F0，也不应该凭听感直接手写几千个 pitch 点。

Agent 应负责：

- 根据工具结果判断失败模式；
- 选择下一种分析/修正策略；
- 判断某段是否需要重新提取；
- 判断是 octave error、note segmentation、timing、pitch smoothing、phoneme alignment 还是 dynamics 问题；
- 管理迭代次数；
- 记录原因与证据。

确定性模块负责真正的数据处理。

## 4.3 不直接复制原唱 F0

原唱 F0 包含：

- 真正的旋律音符；
- vibrato；
- portamento；
- 转音；
- 瞬时抖动；
- 分离模型伪影；
- 无声/气声区域错误；
- octave jump；
- pitch detector 错误。

因此 pitch reconstruction 必须拆成：

```text
Reference F0
  = Note Skeleton
  + Intentional Expression Residual
  + Noise / Extraction Error
```

系统的任务是保留前两者，去掉第三者。

---

# 5. 标准化中间数据

所有模块不能直接互相传递难以调试的临时对象。

建立统一 `analysis.json` schema。

建议结构：

```json
{
  "audio": {
    "sample_rate": 44100,
    "duration_sec": 0.0
  },
  "tempo": {
    "bpm": 0.0,
    "beats": []
  },
  "phrases": [],
  "notes": [
    {
      "id": "n0001",
      "start_sec": 0.0,
      "end_sec": 0.0,
      "midi": 60,
      "lyric": "",
      "confidence": 0.0,
      "pitch_residual": [],
      "dynamics": []
    }
  ],
  "f0": {
    "time": [],
    "hz": [],
    "confidence": [],
    "voiced": []
  },
  "warnings": []
}
```

具体 schema 在实现时单独放入 `schemas/` 并做版本控制。

---

# 6. Pipeline 详细实现

## Phase A — Environment Probe

### A1. 检测 OpenUtau

自动检查：

- OpenUtau 安装路径；
- OpenUtau 版本；
- singer 目录；
- 泠鸢 DiffSinger 是否可加载；
- voicebank singer id；
- phonemizer；
- DiffSinger renderer；
- vocoder 是否完整；
- 能否打开测试 USTX；
- 能否成功渲染 3~5 秒测试音。

输出：

```text
workspace/env.json
```

### A2. Voicebank Adapter

不能把“泠鸢”声库的具体目录名、speaker 名、版本等硬编码在 pipeline。

建立：

```text
configs/singers/lingyuan.yaml
```

记录本机实际探测得到的：

- display name；
- OpenUtau singer id；
- voicebank path；
- languages；
- phonemizer；
- supported expressions；
- preferred vocal range；
- renderer 参数；
- speaker/subbank/voice color（如存在）。

声库文件本身不得提交到仓库。

### Gate A

只有以下测试通过才进入下一阶段：

- OpenUtau 可启动；
- 泠鸢声库可识别；
- 测试音符可以渲染为非静音 WAV；
- 无 renderer fatal error。

---

## Phase B — Audio Preprocess & Separation

### B1. 统一音频

使用 ffmpeg 或等价库：

- 解码常见格式；
- 保留原始文件；
- 转换到统一 PCM workspace；
- 禁止在分析前做 aggressive loudness normalization；
- 保存精确时长和 sample offset。

### B2. Vocal / Accompaniment Separation

接口化：

```python
class SourceSeparator:
    def separate(audio) -> SeparationResult:
        ...
```

第一版可以使用当前效果较好的 UVR/BS-Roformer/Demucs 类模型之一，但模型名称不能写死在上层逻辑中。

必须输出：

```text
reference_vocal.wav
accompaniment.wav
separation.json
```

`separation.json` 至少记录：

- model；
- version；
- parameters；
- duration；
- clipping；
- vocal confidence / quality estimate（如可获得）。

### B3. 分离结果预处理

分析使用的 vocal 可以进行：

- DC removal；
- 极轻量 denoise；
- 非人声区 mask；
- transient / bleed 检测。

但禁止为了“听起来干净”而过度处理，从而破坏 F0 和 timing。

### Gate B

至少确认：

- vocal stem 非静音；
- accompaniment stem 非静音；
- 两者长度与原曲一致；
- 无明显 sample offset；
- 没有因为重采样产生漂移。

---

## Phase C — Reference Vocal Analysis

这是整个项目最关键的一层。

### C1. Tempo / Beat

提取：

- BPM；
- beat positions；
- tempo changes（如存在）；
- downbeat；
- time signature 估计。

不要强行把自由速度歌曲量化到固定 BPM。

### C2. F0 Extraction

采用专门的 monophonic vocal pitch detector。

输出每帧：

```text
(time, f0_hz, confidence, voiced)
```

必须实现：

- confidence threshold；
- unvoiced mask；
- octave jump detection；
- isolated spike removal；
- short-gap interpolation；
- raw F0 永久保留到 debug 数据中。

至少准备两个可替换 backend，用于低置信度片段交叉验证。

### C3. Octave Error Correction

不能只做简单 median filter。

需要结合：

- 前后帧连续性；
- note candidate；
- 音阶/调性先验；
- 2x / 0.5x F0 候选；
- detector confidence；
- phrase 内合理音程；
- 第二 pitch backend 的结果。

Agent 只决定“是否触发重新分析/采用哪个候选”，最终修正由算法完成。

### C4. Note Segmentation

从连续 F0 还原离散音符：

1. 找 voiced region；
2. 将 F0 转成 semitone；
3. 做稳健滤波；
4. 寻找稳定 pitch plateau；
5. 检测真实 note transition；
6. 避免把 vibrato 拆成多个音符；
7. 避免把转音完全抹平；
8. 对短装饰音使用独立规则。

输出：

```text
start
end
midi note
confidence
transition type
```

### C5. Lyrics Recognition

默认流程必须支持只有音频、没有歌词文件。

流程：

```text
vocal stem
  -> singing-aware ASR / transcription
  -> phrase text
  -> syllable segmentation
  -> forced alignment
  -> note mapping
```

如果用户提供歌词：

```text
provided lyrics
  -> forced alignment only
```

优先保证**歌词与时间轴正确**，不要为了 ASR 文字置信度高而破坏音符边界。

### C6. Phrase Segmentation

依据：

- 长停顿；
- 呼吸区；
- lyric punctuation；
- musical phrase；
- note continuity。

后续 tuning/evaluation 都以 phrase 为主要修正单位，而不是整首歌一次性重做。

### Gate C

生成可视化 debug：

```text
debug/f0.png
debug/notes.png
debug/alignment.png
```

要求自动检查：

- 无大面积 octave doubling/halving；
- note 数量处于合理范围；
- voiced region 与 reference vocal 基本重叠；
- lyrics 不出现大段整体漂移。

---

# 7. Pitch Reconstruction — 重点解决之前的问题

之前自动做翻唱最容易失败的是：

1. 自动 pitch 线不平滑；
2. 部分 pitch 判断错误；
3. 原唱的自然转音被当成错误；
4. vibrato 被滤掉或被拆成音符；
5. 分离伪影造成突刺。

本项目禁止使用：

```text
raw F0 -> every frame -> OpenUtau pitch curve
```

## D1. Note Skeleton

每个 note 得到稳定基准音高：

```text
base_pitch = robust center pitch of stable voiced frames
```

候选方法：

- weighted median；
- trimmed mean；
- confidence weighted mode；
- HMM/Viterbi note path。

## D2. Expression Residual

计算：

```text
residual_cents = cleaned_f0 - note_skeleton
```

将 residual 分解为：

- attack transition；
- portamento；
- sustain drift；
- vibrato；
- ornament；
- noise。

只有前五项可以进入最终 tuning。

## D3. Adaptive Smoothing

不能整段统一平滑。

规则示例：

- sustain：适度平滑；
- vibrato：保留周期成分；
- transition：保留连续滑音；
- low confidence：加强平滑或直接回退到 note center；
- isolated spike：删除；
- octave discontinuity：重估而不是平滑过去。

## D4. OpenUtau Pitch Representation

第一版需要研究并实现两种输出路径：

### Path 1 — pitch control points

优点：

- OpenUtau 内可直接编辑；
- 便于人工检查；
- 数据量较小。

### Path 2 — DiffSinger PITD / render-pitch compatible curve

优点：

- 能保留更细表达；
- 更接近原始 F0。

最终根据 OpenUtau 当前 renderer 行为选择主路径，另一条保留作 fallback。

所有转换必须有 round-trip test：

```text
analysis pitch
 -> ustx
 -> OpenUtau load
 -> render pitch / exported representation
 -> compare
```

---

# 8. Timing / Lyrics / Phoneme Reconstruction

## E1. Note Timing

禁止简单把所有 note snap 到网格。

需要保留：

- pickup；
- anticipatory onset；
- laid-back timing；
- legato；
- short transition note。

但允许在极小误差范围内做节拍吸附，以避免分析噪声造成杂乱工程。

## E2. Lyrics Mapping

中文默认最小单位：汉字/音节。

必须处理：

- 一字多音；
- 一字多音符；
- 延音；
- 连音；
- 空拍；
- `+` extender 类结构；
- 标点不进入真实 phoneme。

## E3. Phoneme Timing

优先让 DiffSinger/OpenUtau phonemizer 和 rhythmizer 产生基础结果，再根据 reference vocal 调整必要 timing。

不能在第一阶段手工硬编码每个中文音素时长。

---

# 9. Dynamics / Expression Reconstruction

之前出现“手动调之后响度不一致”的问题，因此 dynamics 也必须结构化处理。

## F1. 不复制原唱绝对响度

原唱振幅受到：

- 压缩；
- 混音；
- EQ；
- 距离；
- reverb；
- separation model；
- master limiter；

影响。

因此只迁移：

- phrase 内相对强弱；
- 长音趋势；
- 重音位置；
- crescendo / decrescendo；
- 句间相对关系。

## F2. Voicebank Compensation

同一 dynamics 值在不同音高/音素上可能得到不同实际响度。

建立 render-measure-correct loop：

```text
requested dynamics
 -> DiffSinger render
 -> measure loudness envelope
 -> compare target envelope
 -> correction curve
 -> rerender
```

最终目标不是让参数曲线看起来漂亮，而是让**实际渲染的声音**稳定。

## F3. Expression Adapter

Voicebank 支持哪些控制参数必须通过 adapter 获取。

不要假设每个 DiffSinger voicebank 都支持完全相同的：

- dynamics；
- tension；
- breathiness；
- gender；
- voicing；
- energy；
- voice color；
- variance expressions。

---

# 10. OpenUtau Project Builder

目录：

```text
src/agent2utau/openutau/
├─ project.py
├─ ustx_reader.py
├─ ustx_writer.py
├─ singer.py
├─ renderer.py
└─ automation.py
```

## G1. USTX Builder

必须支持：

- project metadata；
- tempo；
- tracks；
- voice part；
- notes；
- lyrics；
- singer id；
- phonemizer；
- renderer；
- pitch data；
- vibrato；
- supported DiffSinger expression curves。

不要一开始自己猜完整 USTX schema。

实现方式：

1. 从当前 OpenUtau 源码确认字段；
2. 创建最小真实工程作为 golden fixture；
3. 逐字段 round-trip；
4. OpenUtau 实际加载验证；
5. 保存后重新解析进行一致性测试。

## G2. 不要让 UI Automation 成为 USTX 编辑器

禁止：

```text
打开 OpenUtau
-> 逐个创建 note
-> 逐个输入歌词
-> 逐个拖 pitch
```

正确方式：

```text
analysis.json
-> build project.ustx
-> OpenUtau load
```

UI Automation 仅负责必要的应用生命周期动作。

---

# 11. Render Backend

定义统一接口：

```python
class RenderBackend:
    def render(project, output_path) -> RenderResult:
        ...
```

## H1. 主 Backend：OpenUtau

最终验收以 OpenUtau + 泠鸢 DiffSinger 实际渲染为准。

如果当前稳定版本没有满足项目需求的完整 headless CLI，则实现 Windows UI Automation adapter，只做：

- 启动；
- 加载指定 USTX；
- 等待 singer/renderer ready；
- 触发 render/export；
- 监听完成状态；
- 捕获错误；
- 保存 log。

严禁使用固定屏幕坐标。

优先：

- UI Automation tree；
- menu/action name；
- keyboard shortcut；
- window/dialog detection。

## H2. 可选 Backend：Direct DiffSinger

后续可以评估兼容 OpenUtau voicebank 的 Python/CLI DiffSinger inference backend，用于：

- CI；
- 快速单元测试；
- 大量候选参数批渲染。

但它不能替代 OpenUtau 作为第一阶段的最终验收路径。

---

# 12. 自动评价与闭环迭代

不能使用“生成了 WAV = 成功”。

系统必须重新分析生成的 vocal。

## I1. Pitch Evaluation

只在 reference 和 render 都为 voiced 且 reference confidence 足够高的区域评价。

指标：

- median absolute cents error；
- P90 cents error；
- octave error rate；
- note center accuracy；
- transition shape similarity；
- vibrato frequency/depth difference。

注意：目标是旋律与表达一致，不是逐采样点完全相同。

## I2. Timing Evaluation

评价：

- phrase onset；
- phrase offset；
- note onset；
- note duration；
- consonant/vowel timing；
- overall drift。

## I3. Dynamics Evaluation

比较平滑后的相对 loudness envelope：

- phrase-level difference；
- note-level accent；
- sudden loudness jump；
- silent gap；
- clipping。

## I4. Artifact Detection

至少检测：

- clipping；
- unexpected silence；
- render truncation；
- NaN/invalid sample；
- isolated extreme pitch jump；
- duplicated phrase；
- timeline offset；
- abnormal loudness discontinuity。

## I5. Failure Classification

Agent 每次迭代必须先分类，禁止无目标地“再调一次”。

失败模式：

```text
PITCH_OCTAVE_ERROR
PITCH_SPIKE
PITCH_OVER_SMOOTH
PITCH_UNDER_SMOOTH
NOTE_SEGMENTATION_ERROR
NOTE_TIMING_ERROR
LYRIC_ALIGNMENT_ERROR
PHONEME_TIMING_ERROR
DYNAMICS_INCONSISTENT
SOURCE_SEPARATION_ARTIFACT
RENDERER_ERROR
VOICEBANK_RANGE_PROBLEM
MIX_BALANCE_PROBLEM
UNKNOWN
```

Agent 输出：

```json
{
  "failure_mode": "PITCH_OCTAVE_ERROR",
  "region": [42.13, 44.01],
  "evidence": {},
  "action": "rerun_pitch_with_secondary_backend"
}
```

## I6. Targeted Retry

只能重做失败区或受影响 phrase。

示例：

```text
octave error
 -> secondary F0 detector
 -> choose alternative octave candidate
 -> rebuild affected notes
 -> rerender phrase

pitch spike
 -> confidence-aware residual cleanup
 -> rebuild curve only

loudness mismatch
 -> keep notes/pitch unchanged
 -> correct dynamics only

lyric drift
 -> rerun forced alignment
 -> keep pitch analysis unchanged
```

避免一个局部错误导致整首歌所有步骤重新跑一遍。

---

# 13. Mixing

OpenUtau 干声通过自动评价后，才进入 mixing。

第一版目标不是专业母带，而是生成可直接试听的翻唱成品。

流程：

```text
rendered vocal
 + accompaniment
 -> time alignment
 -> gain staging
 -> light EQ / de-ess if configured
 -> compression if configured
 -> optional reverb
 -> limiter
 -> final_cover.wav
```

默认必须保证：

- 不 clipping；
- 人声不会忽大忽小；
- 人声不会明显被伴奏淹没；
- 最终音频与原曲时长/结构一致。

所有处理参数写入 `mix.json`，避免隐藏状态。

---

# 14. Agent Tool Design

Agent 不直接操作任意 Python shell 作为长期接口。

为 Agent 暴露明确工具：

```text
inspect_environment
inspect_voicebank
preprocess_audio
separate_audio
analyze_tempo
transcribe_lyrics
extract_pitch
build_notes
align_lyrics
build_expression
build_ustx
validate_ustx
render_openutau
analyze_render
evaluate_reference_match
retune_region
mix_cover
build_report
```

每个 tool：

- 输入必须结构化；
- 输出必须结构化；
- 写明 side effects；
- 写明 artifacts；
- 错误可分类；
- 可重复执行；
- 同输入尽量得到一致结果。

Agent 只做 orchestration 和 diagnosis。

---

# 15. 建议仓库结构

```text
agent2utau/
├─ README.md
├─ plan.md
├─ pyproject.toml
├─ configs/
│  ├─ default.yaml
│  └─ singers/
│     └─ lingyuan.example.yaml
├─ schemas/
│  ├─ analysis.schema.json
│  ├─ evaluation.schema.json
│  └─ singer.schema.json
├─ src/
│  └─ agent2utau/
│     ├─ cli.py
│     ├─ pipeline.py
│     ├─ state.py
│     ├─ audio/
│     │  ├─ preprocess.py
│     │  ├─ separate.py
│     │  └─ mix.py
│     ├─ analysis/
│     │  ├─ tempo.py
│     │  ├─ pitch.py
│     │  ├─ octave.py
│     │  ├─ notes.py
│     │  ├─ lyrics.py
│     │  ├─ alignment.py
│     │  ├─ phrases.py
│     │  └─ dynamics.py
│     ├─ tuning/
│     │  ├─ pitch_reconstruction.py
│     │  ├─ expression.py
│     │  └─ retune.py
│     ├─ openutau/
│     │  ├─ ustx_reader.py
│     │  ├─ ustx_writer.py
│     │  ├─ singer.py
│     │  ├─ renderer.py
│     │  └─ automation.py
│     ├─ evaluation/
│     │  ├─ pitch.py
│     │  ├─ timing.py
│     │  ├─ dynamics.py
│     │  └─ artifacts.py
│     └─ agent/
│        ├─ orchestrator.py
│        ├─ diagnosis.py
│        └─ tools.py
├─ tests/
│  ├─ unit/
│  ├─ integration/
│  └─ fixtures/
└─ scripts/
```

---

# 16. 实施里程碑

## M0 — Repository Skeleton

目标：项目能安装、能运行空 pipeline。

任务：

- [ ] Python project skeleton；
- [ ] CLI；
- [ ] config loader；
- [ ] workspace/artifact manager；
- [ ] structured logging；
- [ ] dependency lock；
- [ ] test framework。

验收：

```bash
agent2utau doctor
```

能够生成环境报告。

---

## M1 — OpenUtau + 泠鸢最小闭环

这是最高优先级，不要一开始先做完整 AI 分析。

手工提供一小段已知正确的：

- notes；
- lyrics；
- pitch；

系统完成：

```text
structured score
 -> USTX
 -> OpenUtau
 -> 泠鸢 DiffSinger
 -> WAV
```

任务：

- [ ] 探测 OpenUtau；
- [ ] 探测泠鸢 voicebank；
- [ ] USTX 最小 writer；
- [ ] singer/renderer/phonemizer 设置；
- [ ] render adapter；
- [ ] round-trip test。

验收：

- OpenUtau 能正常打开工程；
- 无 missing singer；
- 无 note error；
- 可自动导出非静音 WAV；
- 无人工点击。

**M1 不通过，不进入整曲自动分析。**

---

## M2 — Original Vocal -> Clean Note Skeleton

任务：

- [ ] source separation；
- [ ] F0 extraction backend A；
- [ ] F0 backend B；
- [ ] voiced mask；
- [ ] octave correction；
- [ ] note segmentation；
- [ ] phrase segmentation；
- [ ] debug plots。

验收：

抽取 3~5 段不同难度的人声片段，与人工观察结果对比。

重点先保证：

- 不乱跳八度；
- 不把 vibrato 拆成音符；
- 不产生大量 20~50 ms 假音符。

---

## M3 — Lyrics + Timing

任务：

- [ ] singing ASR adapter；
- [ ] external lyrics input；
- [ ] forced alignment；
- [ ] Chinese syllable mapping；
- [ ] extender handling；
- [ ] phoneme/rhythmizer validation。

验收：

生成的 USTX 在 OpenUtau 中查看时，大部分音符无需人为整体平移歌词。

---

## M4 — Natural Pitch Reconstruction

任务：

- [ ] note skeleton / residual 分离；
- [ ] adaptive smoothing；
- [ ] vibrato detection；
- [ ] portamento detection；
- [ ] ornament preservation；
- [ ] pitch curve -> OpenUtau conversion；
- [ ] pitch round-trip test。

验收重点：

- 没有明显锯齿；
- 没有孤立 pitch spike；
- 不因 smoothing 丢失所有转音；
- 不把原唱 vibrato 变成机械直线；
- 不出现明显错误 octave。

---

## M5 — Dynamics / Expression

任务：

- [ ] relative loudness analysis；
- [ ] phrase dynamics；
- [ ] accent extraction；
- [ ] render-measure-correct loop；
- [ ] voicebank expression adapter。

验收重点：

- 无明显一句很大、下一句突然很小；
- 长句内部强弱自然；
- 不通过粗暴 normalize 掩盖生成问题。

---

## M6 — Automatic Evaluation + Agent Retry

任务：

- [ ] pitch evaluator；
- [ ] timing evaluator；
- [ ] loudness evaluator；
- [ ] artifact detector；
- [ ] failure classifier；
- [ ] targeted retry；
- [ ] max iteration guard。

默认最多：

```text
initial render + 3 correction passes
```

超过上限必须输出当前最佳结果和 unresolved warnings，禁止无限循环。

---

## M7 — One-command Cover

实现：

```bash
agent2utau cover song.wav --singer lingyuan
```

完整完成：

```text
original
 -> separation
 -> analysis
 -> USTX
 -> DiffSinger render
 -> evaluate
 -> targeted correction
 -> remix
 -> final cover
```

---

# 17. 初始量化验收指标

这些是第一轮工程目标，不代表最终听感上限；后续根据真实测试数据调整。

## Pitch

在高置信度 voiced 区域：

- median absolute pitch error <= 35 cents；
- P90 pitch error <= 80 cents；
- octave error rate < 1%；
- 禁止出现持续的错误半音/整音偏移；
- 孤立 > 200 cents 的异常跳变必须被检测并处理。

## Timing

- phrase onset median error <= 60 ms；
- note onset median error <= 80 ms；
- 整首歌不得出现随时间逐渐累积的 timeline drift。

## Dynamics

- phrase 相对 loudness 不应出现无音乐原因的 > 3 dB 突跳；
- final mix 不 clipping；
- render 不允许整段异常静音。

## Automation

在支持范围内：

- 输入原曲后不要求人工逐音符修改；
- 不要求人工点击 OpenUtau；
- 能生成可重新打开的 `.ustx`；
- rerun 可复现主要结果；
- 所有自动修正可在 report 中追踪原因。

---

# 18. 测试策略

## Unit Tests

覆盖：

- Hz <-> MIDI；
- cents；
- tempo/tick/time conversion；
- octave candidate；
- note segmentation；
- smoothing；
- vibrato detection；
- USTX serialization；
- lyric mapping；
- dynamics normalization。

## Golden Tests

保存少量**自制/可合法分发**的测试数据：

```text
input analysis.json
expected project.ustx
expected metrics.json
```

不要把商业原曲、泠鸢声库或不允许再分发的音频提交进仓库。

## Integration Tests

```text
synthetic reference vocal
 -> analyze
 -> USTX
 -> render
 -> evaluate
```

本地存在泠鸢声库时再执行真实 voicebank integration test。

---

# 19. Agent 行为规范

Agent 每次执行必须遵守：

1. 先读取 pipeline state；
2. 判断当前 milestone / stage；
3. 检查前置 artifact；
4. 调工具获取证据；
5. 先分类 failure mode；
6. 再决定修正；
7. 修正范围最小化；
8. render 后重新测量；
9. 不允许把“听起来应该好了”当作验收；
10. 不允许因为一个局部问题偷偷扩大任务范围。

每个自动修正记录：

```text
before
reason
evidence
action
after
metric delta
```

---

# 20. 第一轮开发顺序

不要按“最酷”的功能顺序开发。

严格按下面顺序：

```text
1. M0 skeleton
2. M1 OpenUtau + 泠鸢最小渲染闭环
3. M2 原唱 -> note skeleton
4. M3 lyrics/timing
5. 第一版整曲 USTX
6. M4 natural pitch
7. M5 dynamics
8. M6 evaluate/retry
9. M7 one-command cover
```

其中 **M1 是第一个真正的 blocker**。

如果连一个人工构造的 10 秒 score 都不能稳定自动生成 USTX 并通过泠鸢 DiffSinger 渲染，那么不应该先投入时间做 ASR、pitch extraction 或 Agent reasoning。

---

# 21. 第一项实际任务

实现 `M1 — OpenUtau + 泠鸢最小闭环`。

第一项 PR/commit 应完成：

```text
agent2utau doctor
```

以及：

```text
fixtures/minimal_score.json
   ↓
build_ustx
   ↓
workspace/minimal.ustx
   ↓
OpenUtau + 泠鸢 DiffSinger
   ↓
workspace/minimal.wav
```

`minimal_score.json` 使用约 5~10 秒、4~8 个简单中文音符即可。

完成后才进入真实歌曲逆向分析。

---

# 22. 技术参考基线

实现时优先核对当前官方源码，而不是依赖旧教程：

- OpenUtau: https://github.com/openutau/OpenUtau
- OpenUtau `OpenUtau.Core/Ustx/`
- OpenUtau `OpenUtau.Core/DiffSinger/`
- OpenUtau phonemizer API
- DiffSinger/OpenUtau 当前 renderer implementation

可以研究兼容 OpenUtau voicebank 的第三方 direct inference 工具作为批渲染/CI backend，但正式结果必须经过 OpenUtau 路径验收。

---

## Definition of Done

`agent2utau` 第一阶段完成的定义不是“Agent 能打开 OpenUtau”，而是：

> 对支持范围内的一首中文歌曲，只给原曲音频，系统能够自动分离原唱与伴奏，重建旋律、歌词、时值和主要演唱表达，生成可编辑的 OpenUtau USTX，使用本地泠鸢 DiffSinger 声库完成渲染，通过自动评价发现并修正明显 pitch/timing/dynamics 问题，并输出可以直接试听的完整翻唱 WAV；整个默认流程不需要用户逐音符修音或手动操作 OpenUtau。
