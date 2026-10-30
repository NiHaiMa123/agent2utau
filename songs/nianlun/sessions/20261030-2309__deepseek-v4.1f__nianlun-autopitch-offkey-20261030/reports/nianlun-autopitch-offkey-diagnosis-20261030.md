# 年轮自动音高（DiffSinger dspitch）为什么会跑调 — 诊断报告

- 日期：2026-10-30
- 对象：上一轮 22:26–22:43 的 `scratch/nianlun_v3_rebuild` / `nianlun_v3_rebuild_audio`（把 v3 谱面重建成「自动音高」版本），以及 22:07–22:12 的 `scratch/nianlun_func_dspitch` 功能版
- 结论先行：**不是渲染坏了，是自动音高这条线本身把「谱面 12 平均律台阶」当成了旋律**。渲染音频对设计线的中位偏差只有 **4.0 音分**（严格跟随），但这条线相对原唱中位 **49 音分**、p90 **183 音分**，全曲 8 个 30 秒段无一例外。v3 手工版是 **3.7 / 18.1 音分**。
- 状态：`listening=unknown`、`musical_quality=unverified`；本报告只做数值归因，不宣称听感已修好。

---

## 一、先排除的两个嫌疑（都排除了）

| 嫌疑 | 检验 | 结果 |
|---|---|---|
| PITD 写错了（公式/偏移/夹取） | 把 `final.ustx` 里 18027 个 PITD 点逐点用官方公式 `y = tones*100 - pitchesBeforeDeviation[idx]` 重算 | 中位 **0.00c**、p95 **0.00c**、max **0.00c**，完全一致 |
| 渲染环节没跟上音高线 | 渲染人声 F0 vs `export-pitch` 的 `final_cents`（逐帧） | 中位 **+0.2c**、p05 −12.8 / p95 +15.2c，**只有 3.3% 帧 >50c** |

所以「线画到位了、渲染也唱到位了」，跑调一定在线本身。这条线就是 DiffSinger 音高预测器的输出。

## 二、真正的差距：自动音高线 vs 原唱

同一套窗口（逐音符源 F0 迹线）、同一套 F0 检测器、同一批 528 个音符：

| | 逐音符中位 | p90 | >100c 音符 | 帧级中位 | 帧级 p90 | 帧级 >100c |
|---|---|---|---|---|---|---|
| v3 手工描源 | **8.1c** | 64.7c | 34 | **3.7c** | 18.1c | 1.3% |
| 自动音高（dspitch） | **30.0c** | 134.6c | 82 | **49.3c** | 182.5c | **26.0%** |
| 参考：谱面名义音高本身 | 23.4c | 123.4c | 67 | — | — | — |

按 30 秒分段（帧级 |误差| 中位，音分）：

```
段起点(s)   20    50    80   110   140   170   200   230
v3 手工    3.8   3.7   4.2   3.6   4.1   3.7   3.3   2.6
自动音高   49.2  48.6  49.9  56.6  48.4  58.0  38.4  44.7
```

**全曲均匀地差，不是某几句坏掉**——这说明它是系统性的方法差异，不是偶发 bug。

## 三、误差分解：一半来自谱面量化，一半来自模型

对 528 个音符做误差分解（RMS 音分）：

| 组成 | RMS |
|---|---|
| 谱面名义音高 − 原唱（12 平均律台阶 vs 真人滑音） | **86.7c** |
| 预测 − 谱面（模型自己的偏离） | **69.3c** |
| 渲染 − 预测（渲染误差） | 30.6c |
| 合计（渲染 − 原唱） | 102.0c |

两条结论：

1. **谱面台阶是第一大误差源（86.7c）**。原唱 100ms 内音高中位移动 **54c、p90 221c**，52% 的窗口移动超过 50c——这是一条大量滑音/颤音的唱法。而谱面是 `tone` 整数半音，100ms 内移动中位 **0c**、只有 29% 超过 50c。自动音高把这种台阶忠实唱出来，就会"一个音一个音地蹦"，听感即"跑调"。
2. **模型还额外加了 69.3c**。预测 vs 谱面中位差 13.0c、p90 69.2c，说明模型本来也会做一点平滑/滑音，但量级远不够补上台阶差。

v3 之所以准，是因为它**绕过了谱面**：中心线直接描原唱双检测器一致 F0 迹线，`tone` 只当名义参考。自动音高反过来，唯一输入就是 `tone` + 时长。

## 四、定位到的三个具体机制（都可修）

### M1 导出接口没有 `voiced` 掩码 → 静音帧被写进 PITD

`bridge/OuBridge/Program.cs` 的 `export-autopitch` 只导出 `ticks` / `tones` / `retake_mask`，**没有导出 `result.voiced`**。而 OpenUtau 官方 `NoteBatchEdits.LoadRenderedPitch`（第 549 行）明确靠它跳过静音帧：

```csharp
if (result.voiced != null && i < result.voiced.Length && !result.voiced[i]) {
    continue;   // 头部/尾部 padding 与音素间空档的模型输出是伪迹，不能写回
}
```

我们这版写入器没有这个掩码，只能用「落在音符里」代替。实测后果：

- 38339 个 PITD 采样点中，**546 个（1.4%）落在首音符之前/末音符之后**（模型 padding 区）；
- **2871 个（7.5%）落在 AP/SP 休止块上**；
- 全体 65 个 AP/SP 音符的预测偏离中位 **+18.3c**、p90 **182c**（全曲最大一类），其中 23 个 >100c。

这解释了乐句/气口边界上那种"突然窜一下"的听感。**修法**：`export-autopitch` 增加 `voiced` 字段，写入器按官方逻辑跳过。

### M2 音符太短时，模型一帧都分不到 → 预测变成邻居的音

654 个音符里最短的只有 40–60ms，而模型帧长是 **11.46ms**（hop 512 @44.1k），即约 11.1 tick。40–60ms 的音符只有 **5 帧**。

- 20 个「|预测 − 本音| > 200c」的音符中，**9 个（45%）的预测值落在相邻音符音高的 120c 以内**——典型的帧分配错位；
- 短音符误差显著更大：80–120ms 音符 |err| 中位 **52c**、120–200ms **67.6c**，而 200–350ms 只有 **23.1c**。

**修法**：短于 ~2 帧的音符不应指望自动音高，改用「继承前一音符音高」的平滑处理；或先把这类音符合并/延长再跑预测。

### M3 `+` 延长块的 tone 被写成"源里那一段的中位"，跳到 2 个半音外

v3 的 `build_nianlun_v3_score.py` 为了把 PITD 拉回预算内，把源偏离 >420c 的字在级差点拆成「字 + `+` 延长块」，两块各自取源中位当 `tone`：

```python
first["tone"]  = int(round(median(v_grid[t_grid < cut])  / 100))
second["tone"] = int(round(median(v_grid[t_grid >= cut]) / 100))   # lyric = "+"
```

实测 236 个 `+` 块里，**230 个的 tone 与前一音符不同，128 个差 ≥3 个半音，最大差 9 个半音**（中位 +2）。对 v3 无害（因为它不读 tone 画线），但对自动音高是致命的：模型收到的"旋律"在这些位置是**错的**。这也是为什么 236 个 `+` 块中仍有 16 个 >100c 偏差。

**修法**：自动音高版本必须把 `+` 块的 tone 改回其父音节的音高（或直接用源 F0 中位量化），否则模型被喂了一条不存在的跳进。

## 五、为什么"功能版"也一样（不是偶发）

22:12 的 `nianlun_func_dspitch`（另一份更早的谱面，391 个可比音符）：

| | |err| 中位 | p90 | >100c |
|---|---|---|---|
| 渲染 vs 原唱 | 22.3c | 101.8c | 41（10%） |
| 谱面 vs 原唱 | 25.1c | 134.5c | 70（18%） |

同一模式：**渲染误差 ≈ 谱面量化误差**，模型几乎只是在照谱唱。所以换成哪份谱面都一样——只要走"自动音高"，输出就等于"把谱面半音台阶唱准"，而不是"唱出原唱的滑音"。

## 六、结论与建议（按性价比排序）

**根因一句话**：自动音高把 `tone` 当作旋律的唯一来源，而这份谱面的 `tone` 是 12 平均律台阶、且 `+` 块音高本身就是错的；原唱是一条滑音密集的唱法（100ms 内移动中位 54c）。谱面台阶贡献 86.7c RMS、模型附加 69.3c，而 v3 手工版直接描源线，所以只有 3.7c。

修的顺序：

1. **先修 M3**（`+` 块 tone 回父音节）：改动最小、收益直接，消除 128 处不该有的跳进。
2. **再修 M1**（导出 `voiced` 并跳过静音帧）：消掉 1.4% 越界点 + 7.5% 休止块写入，主要在句界/气口。
3. **M2 短音符**用继承/合并处理，覆盖 20 个 >200c 坏点里的 9 个。
4. **想真正接近 v3**：自动音高只能当基底。做法是保留预测线，再用**逐音符残差**（源 F0 中位 − 预测中位）作为 PITD 偏置叠上去——这样既有模型的自然连贯，又贴住原唱。纯自动音高不可能达到 v3 的 3.7c，因为信息不在谱面里。

**不建议**：靠提高 `DiffSingerStepsPitch`（当前 prefs 为 10）或换种子——误差 86.7c 来自输入谱面，不是采样不足；这次也没测采样步数的影响，属未验证。

## 七、复现与产物

诊断脚本归档在本 session 的 `scripts/`（只读，不改工程/音频/谱面）。先导出一次渲染器自己的音高网格：

```powershell
cd E:\project\agent2utau
$py  = ".\.venv\Scripts\python.exe"
$S   = "songs\nianlun\sessions\20261030-2309__deepseek-v4.1f__nianlun-autopitch-offkey-20261030\scripts"

# 前置：导出 step1 工程的渲染器音高网格（diag_render_vs_design.py 的输入）
& $py -m agent2utau.cli export-pitch `
    --project "scratch\nianlun_v3_rebuild_audio\step1_pitch_only.ustx" `
    --out     "scratch\diag_step1_pitch.json"

& $py $S\diag_autopitch_v3.py        # 预测 vs 谱面名义音高
& $py $S\diag_autopitch_detail.py    # PITD 落点分布（越界/休止块）
& $py $S\diag_autopitch_hyp.py       # 帧长/短音符/加号块假设
& $py $S\diag_attribution.py         # 按音符类别归因
& $py $S\diag_score_identity.py      # 谱面是否与 v3 逐音符相同（0 差异）
& $py $S\diag_score_vs_source.py     # 谱面名义音高 vs 原唱
& $py $S\diag_render_vs_design.py    # 渲染 vs 设计线（+0.2c，需上面的 export-pitch）
& $py $S\diag_threeway.py            # 源/谱/预测/渲染四方对比
& $py $S\diag_decompose.py           # 误差分解
& $py $S\diag_neighbour.py           # 邻居音高假设（45%）
& $py $S\diag_alignment.py           # 时间对齐 / 逐句相关
& $py $S\diag_frame_level.py         # 帧级全曲对比 + 分段
& $py $S\diag_motion.py              # 旋律运动量对比
& $py $S\diag_func_dspitch.py        # 功能版复核
```

脚本读取的既有产物（均由上一轮 22:07–22:43 生成，本轮未改）：

- `scratch/nianlun_v3_rebuild/`：`autopitch.json`（渲染器 `LoadRenderedPitch` 输出）、`baseline_no_pitch_no_dyn.ustx`、`baseline_pitch.json`、`phones.json`
- `scratch/nianlun_v3_rebuild_audio/`：`step1_pitch_only.ustx`、`step1_vocal_vocal.wav`（仅音高）、`final.ustx`、`final_vocal_vocal.wav`
- `scratch/nianlun_func_dspitch/`：`nianlun_functional_dspitch.ustx`、`vocal_vocal.wav`

关键事实来源：

- 谱面与 v3 逐音符**完全一致**（51 part / 650 note，0 处差异）→ 问题不在重建谱面
- 渲染 vs 设计线：中位 +0.2c、仅 3.3% 帧 >50c → 问题不在渲染
- PITD 18027 点按官方公式重算，误差恒为 0.00c → 问题不在写曲线
- 预测器 tick 间距 11–12 tick（11.46ms），最短音符仅 5 帧
- prefs：`DiffSingerStepsPitch=10`、`DiffSingerDepth=1`、`DiffSingerTensorCache=true`
- OpenUtau 官方 `NoteBatchEdits.LoadRenderedPitch:549` 用 `result.voiced` 跳过静音帧；本仓 `export-autopitch` 未导出该字段
