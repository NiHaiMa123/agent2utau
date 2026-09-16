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

当前 pipeline 已经完成并验证了很多基础设施：

- 原曲解码与人声/伴奏分离；
- FCPE F0 提取；
- LRC 与 Whisper attention/DTW 逐字对齐；
- USTX 生成；
- OpenUtau headless bridge；
- DiffSinger 自动渲染；
- 混音、电平匹配与基础评价；
- OpenUtau note/phoneme 错误检查。

这些能力保留。

当前真正不可用的部分是**主旋律 note transcription**。

现有 `analysis/notes.py` 的基本逻辑是：

1. 先由歌词系统确定每个字的时间窗；
2. 在这个时间窗里取 F0 中位数；
3. 四舍五入到最近的 MIDI note；
4. 只有检测到持续一定时间、跨过一定半音阈值的变化时，才把一个字拆成多个音符。

这套方法不是完整的 singing voice transcription。它容易把：

- 滑音；
- 倚音；
- 多音字内转音；
- 短暂经过音；
- 真实换音位置；
- 颤音与换音的区别；

压成错误的单音，或者切成错误的多个 note。

因此 Plan 2 不继续微调 `MIN_NOTE_SEC`、`SPLIT_SEMITONES` 等阈值，而是把旋律骨架的主来源切换为 **GAME**。

现有 heuristic note builder 保留，但降级为 fallback，不再作为默认主路径。

---

## 2. 总体架构

最终主流程：

```text
原曲
  ↓
解码 / 人声伴奏分离
  ↓
┌──────────────────────────────┐
│ A. GAME：主旋律 note 骨架   │
│ onset / offset / tone        │
└──────────────────────────────┘
  ↓
┌──────────────────────────────┐
│ B. F0：连续音高证据          │
│ RMVPE 或 FCPE                │
└──────────────────────────────┘
  ↓
GAME note validation
  ↓
局部 anomaly detection
  ↓
局部自动 repair
  ↓
修正后的 melody notes
  +
LRC / Whisper DTW 字时间
  ↓
lyrics ↔ melody note 对齐
  ↓
基础 USTX
  ↓
原唱 F0 → 受约束 PITD / 局部表现
  ↓
DiffSinger 渲染
  ↓
reference vs score vs render 自动评价
  ↓
仅回修低置信度区域
  ↓
第一阶段合格成品
```

第二阶段在此基础上增加：

```text
泠鸢本人歌曲
  ↓
风格统计 / style profile
  ↓
滑音 / 颤音 / 换气 / 强弱 / 音色习惯
  ↓
对第一阶段工程做风格化重调
```

---

## 3. 三种信息必须分工明确

### 3.1 GAME：负责“唱什么音”

GAME 是主 melody transcription backend。

GAME 应提供：

- note onset；
- note offset / duration；
- note pitch；
- note sequence；
- 若可获得，附带 confidence / raw transcription 信息。

GAME 的输出被视为**主乐谱假设**，但不是绝对真值。

它允许存在局部错误，例如：

- 多切一个短音；
- 漏掉一个转音；
- 某个 note 高/低一个半音；
- octave error；
- note boundary 有几十毫秒偏差。

这些问题交给后续 validation + repair 处理。

### 3.2 F0：负责“证据”和“细节”，不负责从零生成整首乐谱

F0 extractor 使用 RMVPE 或 FCPE。

用途：

- 验证 GAME note pitch；
- 验证 note boundary；
- 检测漏拆 / 多拆；
- 检测 octave jump；
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

歌词时间**不再直接决定 note 数量和 note pitch**。

例如 GAME 得到：

```text
A4 → B4 → C5 → B4
```

如果四个 note 都属于“轮”字，则 OpenUtau lyric 表达为：

```text
轮  +  +  +
```

而不是强制一个字只能生成一个 note。

---

## 4. Phase 1：接入 GAME，替代当前 heuristic 主转谱

### 4.1 目标

建立独立的 melody transcription 层：

```text
vocal.wav → GAME → melody.json
```

建议新增：

```text
src/agent2utau/transcription/game.py
src/agent2utau/transcription/schema.py
```

统一内部 note schema，例如：

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

### 4.2 GAME 接入优先级

优先复用本机 OpenUtau 已可用的 GAME 能力，而不是重新造一套推理链。

实现时先调查本机实际 OpenUtau 版本中 GAME 的入口：

- 是否可以通过现有 OpenUtau Core / plugin API 调用；
- 是否存在可直接复用的模型文件和 runtime；
- 是否可以由 bridge 无头调用；
- 若只能通过 UI 插件入口调用，是否可以抽出内部调用链；
- 最后才考虑单独 Python 封装。

必须记录：

- GAME 版本；
- 模型路径 / hash；
- 调用 backend；
- 输入采样率；
- 输出 note 数量；
- 运行耗时；
- 是否经过额外后处理。

### 4.3 fallback

只有以下情况才回退到现有 heuristic：

- GAME 不可用；
- GAME runtime 失败；
- GAME 输出为空或明显损坏；
- 用户显式要求 fallback。

报告中必须明确：

```text
melody_source: game | heuristic_fallback
```

不得静默 fallback。

---

## 5. Phase 2：GAME note validation

GAME 输出后不直接写 USTX。

对每个 note 计算 validation features。

### 5.1 Pitch agreement

对 GAME note 的时间范围取 reference F0：

- median pitch；
- mean pitch；
- voiced coverage；
- stable-region pitch；
- 与 GAME tone 的 cents difference。

示例：

```text
GAME tone: B4
reference median: A4 + 8c
pitch disagreement: -192c
voiced coverage: 0.91
→ suspicious
```

### 5.2 Boundary agreement

检查 GAME onset / offset 是否落在真实变化附近。

关注：

- F0 transition；
- voiced ↔ unvoiced transition；
- energy / onset；
- 相邻 note 的稳定区间。

若 boundary 落在长时间稳定 F0 中间，则可能是 false split。

若一个 note 内存在明显稳定的多段音高，则可能是 missed split。

### 5.3 Suspicious note 类型

至少覆盖：

```text
wrong_pitch
possible_octave_error
false_split
missed_split
boundary_shift
very_short_isolated_note
weak_f0_evidence
unvoiced_note
lyric_alignment_conflict
```

每个 note 输出：

```json
{
  "id": "note_0213",
  "game_tone": 72,
  "reference_median": 70.97,
  "pitch_error_cents": -103,
  "voiced_coverage": 0.88,
  "boundary_score": 0.42,
  "confidence": 0.31,
  "flags": ["wrong_pitch", "boundary_shift"]
}
```

---

## 6. Phase 3：局部自动 repair

原则：**只修可疑点，不重新生成整首。**

GAME 正确的绝大多数 note 保持不动。

### 6.1 Pitch repair

候选规则：

- GAME tone 与 reference stable median 相差 > 阈值；
- reference F0 覆盖充分；
- 相邻 notes / 调性上下文支持修改；
- 排除明显 portamento / vibrato 造成的误判。

修复候选：

```text
GAME B4
reference stable region ≈ A4
→ candidate: A4
```

不要仅根据单帧 F0 修改。

### 6.2 False split merge

示例：

```text
GAME: A4  A4  A4
reference: 一整段稳定 A4，无真实 onset
→ merge
```

判断依据：

- tone 相同或极近；
- 中间没有明显 F0 / energy boundary；
- duration 合并后合理；
- lyrics 关系允许。

### 6.3 Missed split

示例：

```text
GAME: A4，800 ms
reference:
A4 300 ms → C5 250 ms → B4 250 ms
→ candidate split: A4 / C5 / B4
```

必须要求每个候选稳定段满足最小时长与 voiced evidence。

### 6.4 Octave repair

检测：

- 单个 note 相比前后突然 ±12 semitones；
- reference F0 显示连续；
- 修正一个 octave 后与上下文一致。

### 6.5 Boundary shift

GAME tone 正确，但 onset / offset 偏离真实换音点时，只调整边界，不改 tone。

### 6.6 Agent 的角色

优先用 deterministic rules 完成高置信度 repair。

Agent 不负责逐音符“凭感觉重画整首”。

Agent 只处理：

- 多种修复候选同时合理；
- evidence 冲突；
- 乐句结构需要上下文判断；
- 自动规则置信度不足但对听感影响大的区域。

每次 Agent 修改必须留下：

```text
before
candidate evidence
after
reason
confidence
```

---

## 7. Phase 4：歌词与 melody notes 对齐

输入：

```text
repaired melody notes
+
forced-aligned lyric chars
```

目标不是“一个字一个音”，而是建立多对多但有约束的映射。

典型关系：

```text
1 char → 1 note
1 char → N notes   （转音 / melisma）
N chars → N notes
```

默认不允许无依据的：

```text
多个不同汉字挤在同一个不可分 note 中
```

如果出现歌词时间和 GAME note 严重冲突：

- 先标记 conflict；
- 不通过移动歌词到附近 voiced block 来“伪修复”；
- 回查 alignment 或 GAME boundary。

OpenUtau lyric 规则：

```text
第一个 note：真实歌词字
后续同字转音：+
换气：AP
静音：按实际需要使用 SP / gap
```

---

## 8. Phase 5：生成“唱对”的基础 USTX

第一阶段 USTX 只包含必要信息：

- repaired notes；
- lyrics；
- 正确 timing；
- singer / renderer；
- 必要的基础 phonemizer 配置。

先不要混入复杂风格曲线。

第一份基础版必须回答一个简单问题：

> **不看任何风格调校，这个工程是不是已经在唱《年轮》正确的旋律？**

如果答案是否定的，不允许进入泠鸢风格阶段。

---

## 9. Phase 6：reference F0 → 受约束 PITD

在 note 骨架正确以后，再利用 reference F0 建立局部 pitch expression。

目的：

- 保存合理滑音；
- 保存重要 portamento；
- 保存有音乐意义的转音细节；
- 保留适量颤音趋势；
- 避免把分离噪声和 F0 抖动直接复制到 PITD。

禁止：

```text
raw F0 frame-by-frame → PITD
```

需要：

- voiced gating；
- smoothing；
- outlier rejection；
- note-relative normalization；
- 最大 cents 限制；
- 对 vibrato / slide / stable region 分类处理。

原唱 F0 在这一阶段决定的是“这一版参考演唱怎么走”，不是最终泠鸢风格。

---

## 10. Phase 7：渲染后闭环评价

渲染后同时保留三层：

```text
A. repaired GAME score
B. reference vocal F0
C. rendered DiffSinger F0
```

评价不能再只看“每个 note 窗口内的 F0 中位数误差”。

至少增加：

### 10.1 Score-level metrics

- note count；
- note pitch agreement；
- note onset error；
- note offset / duration error；
- note boundary confidence；
- suspicious note ratio；
- octave anomaly count。

### 10.2 Frame-level F0 metrics

在 reference 与 rendered 的共同 voiced 区域比较：

- frame-level cents error；
- contour correlation；
- voiced coverage；
- 大于 50 / 100 / 200 cents 的帧比例；
- phrase-level contour mismatch。

### 10.3 Lyric metrics

- char coverage；
- missing char；
- repeated char；
- lyric → note mapping validity；
- invalid OpenUtau note / phoneme = 0。

### 10.4 Listening gate

任何自动分数都不能直接声明“成品可用”。

状态保持：

```text
completed_with_warnings
```

直到至少通过人工试听确认：

```text
melody_verified_by_listener = true
lyrics_verified_by_listener = true
```

---

## 11. 第一阶段验收标准：“唱对”

第一阶段不评价“像不像泠鸢”，只评价是否已经是一份可靠翻唱底稿。

### 必须满足

1. 默认 melody backend = GAME；
2. heuristic builder 仅 fallback；
3. GAME 原始输出、validation、repair 前后结果均可追溯；
4. OpenUtau 0 invalid notes；
5. OpenUtau 0 invalid phonemes；
6. 不允许因独立四舍五入产生 note overlap；
7. 歌词版本与具体录音绑定；
8. lyric ↔ note 映射可追溯；
9. GAME suspicious regions 可定位；
10. 自动 repair 只修改低置信度区域；
11. 生成完整 USTX、vocal WAV、mix WAV、report；
12. 人工试听确认《年轮》主旋律整体正确。

### 不以以下内容作为“旋律正确”的充分证据

- export 成功；
- WAV 非静音；
- 单个 median cents 指标很好；
- DiffSinger 能正常发音；
- GAME 大多数 note 有输出。

---

## 12. 第二阶段：泠鸢风格建模

只有第一阶段通过后才开始。

输入：

```text
E:\data\music\泠鸢\*.flac
```

目标不是复制某一首歌的逐帧 F0，而是提取可迁移的演唱习惯。

### 12.1 可分析维度

- phrase-level pitch approach；
- note onset 偏移；
- portamento 方向与幅度；
- vibrato rate / depth / onset delay；
- 句尾收音；
- breath placement；
- breathiness；
- tension；
- voicing；
- voice color 使用倾向；
- 强弱起伏；
- 长音处理；
- 转音密度与位置。

### 12.2 输出 style profile

建议：

```text
runs/style/yousa/style_profile.json
```

profile 应是统计分布 / 条件规则，而不是某首歌曲线模板。

例如：

```json
{
  "vibrato": {
    "long_note_min_sec": 0.65,
    "onset_delay_median": 0.31,
    "rate_hz_median": 5.4,
    "depth_cents_median": 43
  }
}
```

### 12.3 风格化原则

```text
原唱决定：唱什么
泠鸢参考决定：怎么唱
```

原唱提供：

- melody；
- rhythm；
- lyric；
- song structure。

泠鸢 profile 提供：

- expression；
- vocal manner；
- color；
- vibrato / slide / breath choices。

禁止直接把泠鸢另一首歌的逐点 PITD 曲线复制到《年轮》。

---

## 13. 建议的代码结构

```text
src/agent2utau/
  transcription/
    __init__.py
    game.py
    schema.py
    validate.py
    repair.py
    align_lyrics.py
  analysis/
    f0.py
    lyrics.py
    pitchcurve.py
  style/
    extract.py
    profile.py
    apply.py
  evaluation/
    score_eval.py
    contour_eval.py
    lyric_eval.py
```

当前 `analysis/notes.py`：

```text
保留
↓
改名或明确标记为 heuristic_fallback
↓
不得作为默认 path
```

---

## 14. 建议的中间产物

每次 run 应保留：

```text
runs/<run-id>/
  audio/
    original.wav
    vocals.wav
    instrumental.wav
    rendered_vocal.wav
    mix.wav

  transcription/
    game_raw.json
    game_notes.json
    f0_reference.npz
    validation.json
    suspicious.json
    repairs.json
    repaired_notes.json

  lyrics/
    source.lrc
    alignment.json
    note_lyric_mapping.json

  score/
    base.ustx
    pitd.ustx

  evaluation/
    score_metrics.json
    contour_metrics.json
    lyric_metrics.json

  report.json
```

这样 Agent 可以针对某个异常点继续修，不需要整条链重复猜测。

---

## 15. 建议 CLI

新增调试型命令：

```powershell
agent2utau transcribe-game <audio> --json
agent2utau validate-score <run-id> --json
agent2utau repair-score <run-id> --json
agent2utau align-lyrics <run-id> --json
agent2utau render-score <run-id> --json
agent2utau evaluate-score <run-id> --json
```

日常入口仍保持：

```powershell
agent2utau cover "E:\data\music\年轮 - 张碧晨.flac" --singer yousa --json
```

但内部执行顺序变为：

```text
separate
→ game
→ f0
→ validate
→ repair
→ lyric alignment
→ base ustx
→ pitd
→ render
→ evaluate
→ targeted retry if needed
```

---

## 16. 实施顺序

### M6-A：GAME integration

- 找到本机 OpenUtau GAME 实际调用链；
- 完成 headless GAME transcription；
- 输出统一 melody schema；
- 在《年轮》上保存 raw GAME notes；
- 暂时不做自动 repair。

**验收：** GAME 输出能独立导出为基础 USTX，并明显优于当前 heuristic 转谱。

### M6-B：GAME validation

- F0 与 GAME note 对齐；
- 实现 pitch / boundary / octave / split anomaly 检测；
- 输出 suspicious note 列表与证据。

**验收：** 人工已知的 GAME 小错误能够被自动标记，而正确区域不被大量误报。

### M6-C：High-confidence repair

- pitch correction；
- octave correction；
- same-tone false split merge；
- obvious missed split；
- boundary shift。

**验收：** repair 后 GAME 已知小错误减少，不允许整体旋律退化。

### M6-D：Lyrics ↔ score mapping

- 合并现有 Whisper DTW；
- 支持 1 char → N notes；
- 稳定生成 `+` melisma；
- 保证无吞字、无重复字。

**验收：** 《年轮》完整歌词与 repaired score 正确映射。

### M6-E：Pitch expression

- reference F0 → filtered PITD；
- 不复制噪声；
- 不破坏 repaired note skeleton。

**验收：** 加 PITD 后旋律轮廓更接近原唱，不引入明显怪音。

### M6-F：闭环评价

- score-level metrics；
- frame-level contour metrics；
- phrase-level mismatch；
- targeted retry。

**验收：** 系统能指出“哪一句、哪几个 note 仍有问题”，而不是只给一个总体 cents 分数。

### M7：Yousa style profile

第一阶段“唱对”通过后再启动。

---

## 17. 明确禁止的方向

为避免再次出现“代码指标看起来很好、试听完全不可用”的情况，Plan 2 明确禁止：

1. 不再用歌词字窗口作为主 note segmentation；
2. 不再通过调几个 heuristic threshold 来替代 GAME；
3. 不以 per-note median cents 作为唯一旋律质量指标；
4. 不允许模型在没有证据时批量改写 GAME 正确 note；
5. 不在旋律还没唱对时提前加入复杂“泠鸢风格”；
6. 不把 export success 当作 listening success；
7. 不让歌词系统为了匹配有声区把错误歌词自动搬到附近；
8. 不直接把 raw F0 逐帧写进 PITD；
9. 不静默使用 fallback；
10. 不宣称未试听版本已经达到成品质量。

---

## 18. 最终目标

### 第一阶段

实现：

```text
原曲
→ GAME 得到可靠旋律骨架
→ F0 自动发现并修 GAME 局部错误
→ 歌词正确映射
→ OpenUtau / DiffSinger 正确唱出原曲
```

目标状态不是“完全零错误自动转谱”，而是：

> **GAME 已经提供高质量 baseline，系统能够自动发现并修掉相当一部分局部错误，并把剩余低置信度区域明确暴露给 Agent / 用户。**

### 第二阶段

实现：

```text
正确旋律底稿
+
泠鸢本人歌曲形成的 style profile
→ 更接近泠鸢演唱习惯的翻唱
```

最终形成真正可复用的一键工作流：

```text
用户只给原曲
→ Agent 自动得到可编辑、可诊断、可继续优化的泠鸢 DiffSinger 翻唱工程
```

而不是依赖一次性手工修音或不可解释的黑盒结果。
