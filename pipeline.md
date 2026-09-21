# 歌声 → OpenUtau 歌词工程 pipeline（已验证）

目标：原曲 → 分离人声 → GAME 转谱 → HubertFA 字级对齐 → 填词 →
可打开的 `.ustx`。本文件只记录**实际跑通并验证过**的步骤与参数；
每步附验证方法。验证记录见文末，新验证通过的步骤再补进来。

## 0. 环境与输入

| 项 | 值 |
|---|---|
| repo / venv | `E:\project\agent2utau`，`.venv/Scripts/python.exe`（3.12）、`.venv/Scripts/agent2utau.exe` |
| 原曲 | `E:\data\music\年轮 - 张碧晨.flac`，274.504s，sha256 前16 `5f851d3a760f230a` |
| 歌词 | `data/lyrics/nianlun_studio.lrc`（35 行 349 字；**不要用 `nianlun.lrc`**，那是错版编曲） |
| OpenUtau | `E:\software\OpenUtau-win-x64 (6)`；bridge 命令须以它为 cwd |
| GAME 模型 | `E:\software\OpenUtau-win-x64 (6)\Dependencies\game`（encoder/segmenter/bd2dur/estimator onnx） |
| HubertFA 代码 | `external/HubertFA`（`git clone --depth 1 https://github.com/wolfgitpr/HubertFA`） |
| HubertFA 模型 | `external/hfa_model/1201_hfa_model/`（release v0.0.5 `1201_hfa_model.zip`，244MB；含 model.onnx、vocab.json、opencpop-extension.txt 词典） |
| pip 依赖 | pypinyin、textgrid、librosa、onnxruntime、soundfile、matplotlib（均已装） |
| ustx 网格 | 480 tpq @ 120bpm ⇒ `TICKS_PER_SEC = 960`；note position/duration 为 part 相对 tick，part.position 为工程绝对 tick |

## 0.1 已验证基础设施与硬契约

以下内容此前散落在 `plan.md / plan2.md / AGENTS.md`，但当前 pipeline 实际依赖，现统一记录在这里。

### OpenUtau / Yousa

- singer：`YousaV1.65b`；renderer：`DIFFSINGER`；默认 phonemizer：
  `OpenUtau.Core.DiffSinger.DiffSingerChinesePhonemizer`。
- 当前声库已确认存在 duration / pitch / variance 模型；可用表现维度至少包括
  pitch、breathiness、voicing、tension。不要因为 USTX expression 表里存在
  `ene` / falsetto 字段就假设本声库实际支持。
- 五种 color：`Yousa_Bright / Cute / Normal / Whisper / Classic`。
  `clr` 是 **per-phoneme expression**；旧工程的 `01:Bright...` 必须按语义名称迁移，
  不能按旧索引直接照抄。
- `cl01..cl05` 的索引语义来自 character/subbank 顺序，而 `clr` option 顺序不同；
  二者不得混为同一个索引空间。
- part curve 的 x 是 **part-relative tick**；note.position 也是 part-relative；
  part.position 才是 project-absolute。所有曲线/音符/波形比较必须先统一到绝对时间轴。

### Headless render bridge

仓库的 `bridge/OuBridge` 已验证可复用 OpenUtau 自身的 load / phonemize /
DiffSinger render 路径，不重写合成器。当前命令运行时仍要求 OpenUtau 安装目录作为 cwd。

Bridge 负责：

- inspect：加载工程并报告 invalidNotes / invalidPhonemes；
- render：导出实际 DiffSinger 干声；
- round-trip：验证工程加载/保存后语义仍有效。

不要用 GUI 自动化或伪造 `OpenUtau.exe --render` 取代已经跑通的 bridge。

### F0 语义

- `torchfcpe(..., retur_uv=True)` 返回的是 **unvoiced mask**（1=无基频），使用前必须反转；
  模型原生时间步为 160 samples @16k = 10ms，不能拿 44.1k 输入采样率错误换算 hop。
- 旧的错误 voiced-mask/F0 缓存不得继续作为质量证据；F0 cache/version 变更必须使旧结果 stale。
- RMVPE / FCPE / third-F0 属于不同 evidence family；同一个模型的多次扰动/多次随机运行
  不能伪装成多个独立测量家族。

## 1. 分离人声（verified）

```powershell
.venv/Scripts/agent2utau.exe diagnose "E:\data\music\年轮 - 张碧晨.flac"
```

`diagnose` 内部完成 decode → 分离（`UVR-MDX-NET-Voc_FT.onnx`）→ 缓存。
缓存目录 `runs/_cache/<md5(source路径)>/`，本曲为 `082598c2b4b5/`：

- `original_(Vocals)_UVR-MDX-NET-Voc_FT.wav` = 分离人声（44.1k stereo）
- `original.wav` = 原曲混音
- `manifest.json` 绑定 source_sha256 + 分离模型（防串源）

已验证：`runs/review_combined/source_vocal.wav` 与 vocals 分轨 md5 一致。

## 2. GAME 转谱（verified）

同一条 `diagnose` 命令产出 `runs/<run-id>/diagnostic/game_raw.ustx`——
GAME raw（variant A）单 part，428 notes，part.position=10291 ticks（10.72s 起）。

本次使用 run `diag-20260917-181538-6aec`。GAME 是随机模型：同配置
`--repeats N` 可多跑取 medoid/consensus（见 AGENTS.md M2.1.2）。

## 2.1 GAME 多跑、Candidate 0 与 uncertainty（verified）

GAME 是 stochastic model。当前 written-score 诊断链使用同配置多次运行并做 formal sequence
alignment；**Candidate 0 必须是某一次真实 GAME run**，不能是把多次结果平均后凭空构造的新谱。

约束：

- 多跑用于估计不确定性、split/merge correspondence 和 medoid 选择；
- GAME 多个 stochastic runs 仍属于同一个模型 family，不可在证据投票时当成多个独立模型；
- consensus/median 只能描述 uncertainty，不能覆盖 Candidate 0；
- Candidate 0 在 adjudication / review / repair 中保持 immutable；所有修改 copy-on-write 生成新 artifact。

## 2.2 Written-score 诊断/修复链（已实现部分）

在歌词映射和表现调校之前，仓库已有一套 fail-closed 的 written-score 审计链：

```text
GAME multi-run
→ formal alignment / medoid Candidate 0
→ RMVPE + FCPE + third-F0 + waveform evidence
→ pitch / structure / identity / separation 正交状态
→ structure adjudication
→ identity 固定后 pitch/octave adjudication
→ unresolved 才进入 phrase-level review
→ 仅 machine-safe 或 valid human-authorized candidate 可进入 repair
```

当前必须保留的安全规则：

1. F0 measurement 不等于 score interpretation；F0 changepoint 本身不能证明 note boundary。
2. missing/low-confidence evidence = neutral，既不是 support 也不是 opposition。
3. structure 未 finalized 时，pitch 只能 provisional；structure identity/span 改变后旧 pitch verdict 必须重算。
4. split 必须与 portamento/ornament 等解释竞争；两个 F0 plateau 本身不等于 written split。
5. 单 note 自动 pitch repair 只能改 written tone；不得同时改 identity/timing/count/lyrics/PITD。
6. phrase review 必须比较完整自然唱句，共享同一 context / singer / renderer / gain；候选音频需绑定 exact hash。
7. 聊天中的“选 A/B”本身不是 repair authority，必须重新绑定到正式 decision/package。
8. 0 repair 是合法结果；不能为了让流程继续而降低 gate。
9. 当前 M2.5 bulk structure repair 仍处于 QUALITY HOLD：未通过 review-readiness 的候选不得进入 trusted written score。

这些审计规则不是当前 HFA 填词算法的替代品；它们负责防止错误 GAME 结构/音高被静默写入基础乐谱。

## 3. 组装对比工程（verified）

`runs/review_combined/cover_review.ustx` = 三轨同绝对时间轴：

- `tracks[0]` vocal：旧 ASR cover（`voice_parts` 多段，参考用）
- `tracks[1]` GAME raw：`voice_parts` 里 `name: game_raw_seg0`、`track_no: 1`、`position: 10291` 的单个 part
- `tracks[2]` source vocal：`wave_parts` 一项，`relative_path: source_vocal.wav`、`position: 0`、track_no 2（与 ustx 同目录放 wav 副本）

装配要点：part.position/note.position 全部用绝对 tick 网格量化后再减
part 锚点；`wave_parts` 是顶层字段，不参与渲染。

## 4. HubertFA 字级对齐（verified 2026-09-20）

核心事实：**中文字的 sung onset 对的是"韵腹（vowel nucleus）起点"**，
不是字的起点——声母（zh/q/ch/sh…）不带音高。GAME note onset 与
HFA 韵腹起点逐点吻合（典型差 ≤10ms）；Whisper DTW 字界系统性偏早
0.3–0.6s，不可用作 onset 依据。

```powershell
# 4a. 按 LRC 行切 vocal + 生成拼音 .lab（pypinyin）
.venv/Scripts/python.exe runs/hfa/prep.py
#   -> runs/hfa/segments/segNN.wav + segNN.lab + meta.json
#   切片窗口 [行起点-0.30, 下行起点+0.45]；meta.json 记每段 offset

# 4b. HubertFA ONNX 推理（35 段 ≈ 12s CPU）
.venv/Scripts/python.exe external/HubertFA/onnx_infer.py `
  -m external/hfa_model/1201_hfa_model/model.onnx `
  -wf runs/hfa/segments -l zh -np AP,EP -o runs/hfa/out
#   -> runs/hfa/out/TextGrid/segNN.TextGrid（words+phones 两层）

# 4c. 提取每字韵腹起点（全局秒）
.venv/Scripts/python.exe runs/hfa/extract_nucleus.py
#   -> runs/hfa/char_nucleus.json：349 行 {line,ci,char,py,w0,w1,nuc,phs}
```

验证：349/349 字有 nucleus；抽查争议段韵腹 vs GAME onset
（却34.95/遮35.35/住35.74/了36.54/黄36.99/昏37.40 全部落在对应 note onset ±10ms）。

注意：`.lab` 是**拼音**（词典 key 是 pinyin，非汉字）；pypinyin 默认
读音，多音字可能读错（本曲未发现明显错读，逐字未全核对）。

## 5. 填词（verified 2026-09-20）

```powershell
.venv/Scripts/python.exe runs/review_combined/fill_lyrics_hfa.py
# 输入: game_raw.ustx(音符结构) + char_nucleus.json(韵腹)
# 输出: .notes_block_hfa.yaml(可直接替换的 notes 块) + game_assign_hfa.json(审计)
```

规则（`runs/review_combined/fill_lyrics_hfa.py` 头部 docstring 为准）：

1. **字区域 = `[nuc_i, nuc_{i+1})`**；区域界吸附到 ≤60ms 内的 GAME note onset
   （该 note 即此字真实 onset）。
2. 区域内第一个 note = 本字歌词；其后区域内 note = `+`（必须与前 note
   tick 紧邻，否则转 `a` 噪音）。
3. 区域内无 onset 的字，按序兜底：
   a. 争抢边界：nuc 后 ±20ms 内有 note 被**更晚**的字占用 → 本字夺下，
      被挤字在自己区域内顺延；
   b. 覆盖 split：nuc 落在前字 note 内部 → 该 note 在 nuc 处切开，
      后半=本字，并按 `min(w1, region_end)` 延长（GAME 漏检的弱元音尾，
      本曲 2 处 split、其中 1 处延长到 223.61s）；
   c. 吞延音：nuc 在间隙中、且紧邻前一条是前字的非 onset `+` note
      （前字还保有更早 onset）→ 该 note 改归本字（本曲 `轮`@159.90）；
   d. 否则顺延到其后第一个空 note。
4. 无词噪音 note（前奏误检/间奏/尾音）先标 `a`，**输出时整条删除**
   （verified：37 条删除后 393 notes，无零时长/重叠，bridge ok）。
5. 严格按 LRC 文本序处理；最终校验 `match:True`（实字序列 == 歌词源）。

## 6. 写入 ustx + 校验（verified）

```powershell
.venv/Scripts/python.exe runs/review_combined/apply_notes.py
# 把 .notes_block_hfa.yaml 替换进 cover_review.ustx 的 game_raw_seg0 part

cd "E:\software\OpenUtau-win-x64 (6)"
.\a2u-bridge.exe inspect --project "E:\project\agent2utau\runs\review_combined\cover_review.ustx"
# 要求: ok=True, invalidNotes=[], invalidPhonemes=[]
```

PyYAML 解析 ustx 复核 note 数/零时长/重叠（见验证记录命令）。
`'+'` 合法性依赖紧邻（`Prev.End == position`），断裂会报 invalid phoneme。

## 验证记录

- **2026-09-20 全链路（年轮 274.5s）**：HFA 对齐 349/349；填词后
  `却 遮 住 + 了 黄 昏`（L2+副歌两处）、`等 清 + + 晨`、`是 树 + + 根`
  均与用户判定一致；349/349 字 match LRC 源；bridge ok、58→50 phrases、
  0 invalid。`a` 噪音 note 删除（37 条）→ 393 notes 再次 bridge 验证通过。
- 遗留：间奏/前奏/尾音的 GAME 误检 note 已删；`印在我`段"我"为单
  note（GAME 只检出一个 onset，HFA 词尾暗示元音持续到 23.53s，
  未做时长扩展——待听辨后定夺）。

## 已验证但未纳入本流程的备选

- `agent2utau cover`（旧 ASR 全曲渲染管线）：歌词不可靠，仅作 vocal 轨参考。
- GAME align 模式（known_boundaries 硬约束）：会把错误的字界当硬边界，
  对本任务不适用——保留 GAME 原生 note + HFA 区域归属才是正确分工。
- Whisper DTW 字级 span：系统性偏早 0.3–0.6s，仅作行级窗参考。

## 当前 pipeline 的不可破坏顺序

后续任何新调校计划必须服从下面的层级：

```text
原曲/分离
→ GAME written melody
→ written-score audit / 必要修复
→ HubertFA lyric/nucleus mapping
→ base USTX + bridge validation
→ neutral DiffSinger render
→ 表现参数（PITD/DYN/TENC/BREC/VOIC/color）
→ render loop / QA
```

**先唱对，再唱得像。** PITD、vibrato、portamento、color、breathiness 等都不得用来掩盖
written-note pitch/timing/identity 错误。

## 渲染质检管线 (runs/qa, 2026-09-21)

`runs/qa/score.py` — 逐 LRC 行对 GAME 渲染轨 vs 原唱人声打分排序:

- **渲染**: bridge `render` → `runs/qa/render*/game_GAME raw.wav` (GAME 轨独立干声)
- **SingMOS-Pro** (`runs/qa/mos_predictor.py`, 本地 clone `external/singmos` +
  ckpt `external/singmos_pro.pth` + wav2vec2-LL60k upstream; 需 torchaudio
  兼容 shim: `set_audio_backend`/`sox_effects` stub, 全部 16kHz 输入)
  —— 每行渲染/原唱各打一分; 静音=1.16, 渲染句 3.1-4.7, 原唱句 3.1-4.9。
  **必须裁到 sung extent**(窗内首 note 起-0.25s ~ 末 note 尾+0.35s),
  否则间奏静默会把 MOS 压到 ~1.6-2.3 造成假阳性(已踩过)。
- **ASR CER**: `analysis.lyrics.transcribe` (faster-whisper large-v3-turbo,
  CPU int8) 逐行回译 → 汉字编辑距离 vs LRC 期望字; 渲染/原唱同算,
  只看相对差(ASR 对合成音本身有偏差)。
- **音高跟踪**: `analysis.f0.extract_f0` (torchfcpe) 渲渲染 F0;
  每 note 帧级对比 `tone*100 + pitd(t)` 意图曲线 → med/p95 偏差 +
  voiced 覆盖率。实测 pdev 中位 ~2c — 合成器忠实执行 pitd,
  "怪"不在跟踪层。
- **渲染vs原唱 F0 偏离**: 同时间戳配对(±15ms 最近帧), >1200c 计为
  倍频分歧另算 —— 不能用各自 voiced 集合按下标配对(曾产生 200c 假
  偏离, voiced 分布不同导致错位)。
- **MCD**: 25 阶 MFCC 均方根距(音色粗糙距离, 区分度弱)。

输出 `qa_report.md/.csv` 按 suspicion = -z(MOS_r)+1.5z(CER_r)+z(pdev)
+0.7z(sdev)+0.5z(mcd) 排序; 附 p95 偏差最差 note 表和 voiced 覆盖率
最低 note 表。全曲 35 行 ≈ 6min CPU(whisper 大头)。
