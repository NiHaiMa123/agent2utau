# 年轮 v10：按白烁画法完成音高线 + 音色层（2026-10-29）

对象：`runs/production/nianlun-v3-20261029`
素材：`E:\data\music\年轮 - 张碧晨.flac`（274.5s）

---

## 一、用户两条提示确定了方向

1. **"原曲的 f0 不能作为标准答案。因为如果这个是标准答案，我就不需要做这个项目了"**
   → 源 F0 只能作条件，不能作目标。我最初三版（v3d/v3i/v3h）都在做"贴合源 F0"，方向错了。

2. **"实际上就是音高线没做好，有白烁的项目记录，我说的逼近本人的就是他调的"**
   → 直接指向答案：学白烁的**画法结构**。

---

## 二、白烁画法的实测结构（只读归纳，不复制数值）

来源：`research/baishuo/projects/雨爱-有参by白烁.ustx`，499 个音符 / 15763 个 PITD 点。

| 特征 | 实测 |
|---|---|
| **载体** | `note.pitch` 全部是**直线**（每音符 2 点 y=0）；**所有细节画在 PITD** |
| **PITD 密度** | step 中位 **10 ticks ≈ 15.6ms**，11082 点 |
| **值分布** | p50 **-5c**、p75 +16c、p95 +119c、p99 **+410c** |
| **极端值** | \|y\|>200 占 **8.8%**、>400 占 2.5%、>800 占 0.3%（用到满量程 ±1200） |
| **极端值形态** | 157 个 \|y\|>300 的**连续段**：段长中位 **23ms**、p90 125ms、峰值中位 **432c** |
| **方向偏置** | 157 段中负向 **115 个**、正向 42 个 |
| 字头 (u<0.15) | 中位 -5c、**p10 -153c**、std 110c |
| 字腹 (0.35-0.65) | 中位 -3c、**p10 -175c**、std 160c |
| 字尾 (u>0.85) | 中位 -8.5c、**p10 -220c**、std 166c |
| 字腹幅度 vs 长度 | 短字 std **13.5c** / 中 20.9c / 长 **60.6c** |
| 平滑度 | 二阶差分中位 **12c**（手绘平滑，非噪声） |

**结论：字头滑入、字腹随长度展开、字尾滑出，用密集 PITD 逐点画出。**

---

## 三、v10 做了什么

### 音高线（PITD，12ms 网格）

- 载体：`note.pitch` 保持直线（与白烁一致），细节全在 PITD
- 51 parts 共 **15525 点**
- 字头滑入：句首 -560c、上行大跳 -480c、下行大跳 +420c、同音重咬 -300c（**方向由音程符号决定，不再系统性偏负**）
- 字腹：短字 14c / 中 30c / 长 70-120c，再按"有无运动/是否周期"缩放
- 字尾滑出：句尾 -500c、下接低音 -400c、上接高音 +370c
- 极端偏移为**持续段**（40-160ms），不是单点尖峰

**与白烁同口径对比：**

| 分位 | v10 | 白烁 |
|---|---|---|
| p1 | -506c | -513c |
| p5 | -339c | -225c |
| p25 | -74c | -52c |
| p50 | -28c | -5c |
| p75 | -1c | +16c |
| p95 | +146c | +119c |
| p99 | +358c | +410c |
| \|y\|>200 | 11.4% | 8.8% |
| std | 137c | 125c |

### 音色层（本轮新增，之前一直没启用）

**发现**：我们所有版本 `clr` 的 options 都是 `['']`、max=0，**5 种音色一个都没启用**——一直在用未配置的默认音色。白烁用了 cl01/cl02/cl05 混合。

`dsconfig.speakers` 顺序 → clNN 语义：
`cl01=Bright, cl02=Cute, cl03=Normal, cl04=Whisper, cl05=Classic`

**实测选优**（同段 1/3 倍频程谱形，距源人声 RMS 距离）：

| 配方 | 谱形距离 |
|---|---|
| **bright50_cl50** | **4.69 dB** ← 采用 |
| mix 26/6/34/34 | 7.24 dB |
| classic100 | 8.16 dB |
| normal70_cl30 | 8.39 dB |
| normal100 | 10.18 dB |

v10 采用 `cl01=50, cl05=50`（Bright 50 + Classic 50）。

### 发声层
dyn / voic / brec / tenc 各 51/51/51/42 条，逐句由源 RMS 与谐波性代理驱动。

---

## 四、技术核验

| 指标 | 原唱 | v2 | v6 | v9 | **v10** |
|---|---|---|---|---|---|
| 动态 IQR | 8.7 dB | 7.7 | 8.3 | 9.8 | **10.3** |
| 峰值 | 0.775 | **1.000** | 1.000 | 1.000 | 1.000 |
| 满幅样本 | 0 | 0 | 0 | 0 | **0（无削波）** |
| rms | 0.1098 | 0.1000 | 0.1132 | 0.1365 | 0.1426 |

- `native_max_error = 0.5c`（契约 <0.501c）**通过**
- 58 个原生短语全部编译通过
- 混音：固定增益，单次全局余量 -1.98dB，峰值 0.95
- 曲线层齐全：pitd / cl01 / cl05 / dyn / voic / brec / tenc

---

## 五、交付物

| 文件 | 说明 |
|---|---|
| `demo/nianlun_v3/nianlun_v10_mix.mp3` | 整曲混音（人声+伴奏） |
| `demo/nianlun_v3/nianlun_v10_vocal.mp3` | 纯人声（匹配原唱响度） |
| `demo/nianlun_v3/_v2_vocal_REFERENCE.mp3` | v2 对照 |
| `runs/production/nianlun-v3-20261029/compiled/project_v10.ustx` | OpenUtau 工程 |
| `runs/production/nianlun-v3-20261029/score/v9_score.ustx` | 含密集 PITD 的谱面 |

---

## 六、诚实的边界

1. **听感未验证**：我没有音频感知工具，`musical_quality = unverified`。以上全是数值证据。
2. **p50 仍偏负**（-28 vs 白烁 -5）：整体线略低，可能听成"偏低"。
3. **音色是"谱形最接近源"的选法**，不等于"最适合这首歌对泠鸢的演绎"。谱形距离只是代理，最终要听。
4. **逐元音图审 0/349**：编译器生成了图册但我没有逐张审阅，按 Skill 不计已审阅。
5. **ASR 反向识别 bigram-recall 未复测**（v6 时 73.8%，原唱 79.5%），咬字清晰度仍有差距。
6. 复用了用户授权的观测（分离/GAME/双F0/ASR）。

---

## 七、下一步（若方向正确）

1. 把 p50 从 -28c 拉回 ~0（整体线别再偏低）
2. 逐元音图审 + ASR 反向验证咬字
3. 若"还不够像"：考虑 PITD 与 note.pitch 的分工（白烁的 note.pitch 是直线，我目前也是），
   以及 tenc/brec 的逐字粒度（现在是逐句）

---

## 八、复现

```
songs/yuai/reports/legacy/bs_pitd.py              白烁 PITD 结构
songs/yuai/reports/legacy/bs_profile.py           字内位置分档
songs/yuai/reports/legacy/bs_extremes.py          极端值形态分析
songs/nianlun/sessions/20261029__unknown-model__nianlun-v3-20261029/scripts/v9_pitd.py              生成密集 PITD（15525 点）
songs/nianlun/sessions/20261029__unknown-model__nianlun-v3-20261029/scripts/v5_compile_plan.py      构造编译计划（v9 复用）
  agent2utau compile-functions  -> native_max_error 0.5c
songs/nianlun/sessions/20261029__unknown-model__nianlun-v3-20261029/scripts/v9_timbre_grid.py       音色配方实测选优
songs/nianlun/sessions/20261029__unknown-model__nianlun-v3-20261029/scripts/v10_assemble.py         音色层 + 发声层
  agent2utau render-project
```
