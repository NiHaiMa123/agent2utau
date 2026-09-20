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
