# 年轮翻唱 v3 重制报告（2026-10-29）

对象：`runs/production/nianlun-v3-20261029`
素材：`E:\data\music\年轮 - 张碧晨.flac`（274.5s，SHA `5f851d3a…`）
性质：按项目 Skill 从头重做。**v1/v2 目录与产物全部保留未改。**

---

## 一、先诊断：前两版"差到无法给出建议"的根因

在写任何代码前，对 v2 做了分层归因（全部可复现）：

| 层 | 实测 | 结论 |
|---|---|---|
| 引擎还原（渲染 vs 设计线） | 中位 **3.1c** | 完美，**不是**引擎问题 |
| 音符整数音高 | 中位 21c，81.5% 在 50c 内 | 基本可接受 |
| **最终线 vs 原唱** | 中位 **39c**，p90 **239c**，**27.7% >100c** | **主因** |
| 时间对齐 | 最佳平移中位 **0ms** | **不是**时钟错位 |
| 幅度比 | std(设计)/std(源) = **0.96** | **不是**过度压缩 |

**真正原因（逐条对应 Skill 明文禁令）：**

1. **v2 把"源残差 × 0.8"当字腹设计，13989 个中心节点 = 每字 40 点**，等于逐帧抄写源 F0。
   Skill 明令：*"不要将整条源F0统一平滑、统一缩幅后当作Agent字腹设计……滤波对不同速率的衰减
   可能不同，后续稀疏化又可能删掉转向"*。抄写把检测噪声与微抖动一并抄入，却丢掉了真正的
   演唱动作（入口/承接/到达/展开/退出）。
2. **音符音高被量化到整数半音**（`int(round(core_cents/100))`），半音内的精细音高全部丢失，
   导致字腹内部实际是平的。
3. **HFA 字长不可信**：实测 HFA 在多处把连续字压成 **0.02s**（seg10 开头 10 个字挤在 0.24s，
   而 GAME 显示该处有 5 个 ~0.4s 音符、真实演唱跨 131.75–135.0）。照抄 HFA 字界 →
   12 个 0.019–0.097s 碎字、吞字。
4. **发声层只有 7 种段落级取值**，349 个字逐字无差异 → 虚实、强弱、气口全无设计。
5. **ASR 歌词有 9 处错字**，被两版沿用。

---

## 二、v3 的做法

### 复用（用户授权）
分离伴奏/人声、GAME、双 F0、ASR —— **逐字节校验与 v2 一致**（`manifest.json` 记录 SHA）。

### 全部重做
| 环节 | 做法 | 与 v2 的差别 |
|---|---|---|
| 歌词 | 权威歌词（百度百科），修正 9 处 ASR 错字 | 寒夜/清晨/世间/有缘却无份/笨/丛生/倒也过/数着/自尊 |
| 句结构 | 17 个真实有声段（能量检测）+ GAME 音符起点，不依赖 ASR 分段 | ASR 漏了整个第一段主歌 |
| 字时钟 | 51 句 349 字，句内按字数均分 + 吸附到音符起点/能量谷 | 最短 **0.20s**，**0 个 <100ms**（v2 有 34 个） |
| 旋律骨架 | GAME 音符（实测 vs 源 F0 中位 **9.2c**、p90 41.7c） | v2 用 HFA 核心段中值且量化到半音 |
| 意图 | 51 句 / 349 单元，每单元独立观察（入口/主体/退出三分法） | v2 的 checks 100% 是 range 自证型 |
| 判据 | **direction 285 / cycles 28 / range 17 / hold 10**，无自证式 range | v2：range 349（全部自证） |
| 音高函数 | 中心节点按**实测运动量自适应**：稳定 3 点、中等 60ms、强运动 35ms；5.4k 中值滤波去噪但保留局部折返 | v2：统一"平台+单一 ±52c 鼓包" |
| 发声层 | 每句独立 DYN(51)/VOIC(51)/BREC(51)/TENC(42)，由该句源 RMS 与谐波性代理驱动 | v2：7 种段落级取值，逐字无差异 |
| 呼吸 | 15 个，全部来自真实静默，时长中位 0.50s，**无一个固定 0.200s** | v2：51 个固定 0.200s |

### 关键工程修复（本轮实测发现）
- **USTX 曲线 `ys` 必须是整数**。浮点值会让 OpenUtau 的 .NET YAML 反序列化抛
  `Exception during deserialization`（用隔离测试逐项确认）。项目现有文档未记载此约束。
- **曲线 `xs` 必须是 part 相对 tick**，用绝对 tick 会写坏文件。
- **设计支撑外的 Hermite 外推会爆炸**：AP 呼吸音符使原生 RenderPhrase 起点早于 part 演唱起点
  （18.23 vs 18.73），直接采样会得到 33984c 的荒谬值。改为边界值保持（AP 段本就不是演唱音高）。

---

## 三、客观核验结果（技术指标，**不含听感结论**）

### 1. F0 追踪（渲染人声 vs 原唱，双检测器一致窗）

| 版本 | med\|Δ\| | p90 | >100c | >200c |
|---|---|---|---|---|
| v2 | 33.5c | 195.1c | 23.7% | 9.6% |
| **v3** | **44.2c** | **175.0c** | 24.8% | **7.5%** |

> **必须诚实说明**：v3 的 med\|Δ\| 比 v2 **更大**。这不是退步，而是设计取向不同：
> v2 逐帧抄写源 F0，自然"贴合"；v3 用稀疏节点表达演唱动作，必然偏离源的微抖动。
> 实测原唱每个字内部的 F0 标准差中位为 **72.9c**（其中 151 字是 5.6Hz 颤音、133 字是 2.3Hz
> 慢走势），任何平滑设计都会与逐帧原唱产生数十音分差异。v3 在 p90 与 >200c 上反而更好。

### 2. 动态层次与电平

| | IQR | p10 | p90 | peak | rms |
|---|---|---|---|---|---|
| 原唱 | **8.7dB** | -33.5 | -13.8 | 0.775 | 0.1098 |
| v2 | 7.7dB | -31.7 | -14.7 | **1.000（削波）** | 0.1000 |
| **v3** | **8.2dB** | -30.5 | -14.1 | 0.913 | **0.1125** |

> v3 的动态层次已接近原唱并超过 v2；峰值不再削波；整体电平与原唱匹配（差 0.2dB）。

### 3. 字时钟
349 字，最短 0.20s，中位 0.54s，**<100ms 0 个，<80ms 0 个**。

### 4. 呼吸组织
15 个呼吸音符，全部来自真实静默，时长中位 0.50s，**无固定 0.200s**。

### 5. 生成过程合规
- 中心节点 **5394（15.46/字）**，v2 为 13989（40/字）
- 判据类型：direction 285 / cycles 28 / range 17 / hold 10 —— 无自证式 range
- `native_max_error = 0.500000c`（契约 <0.501c）**通过**
- 发声层：dyn 51 / voic 51 / brec 51 / tenc 42

---

## 四、交付物

| 文件 | 说明 |
|---|---|
| `render/nianlun_v3_mix.wav` | 整曲混音（人声 + 分离伴奏，固定增益 0/-6.5dB，峰值 0.9599） |
| `render/nianlun_v3_vocal_matched.wav` | 纯人声，已匹配到原唱人声响度（差 0dB） |
| `compiled/project.voiced.ustx` → `project_voiced.ustx` | OpenUtau 工程（可直接打开试听） |
| `evaluation/verification.json` | 全部技术指标原始数据 |

---

## 五、诚实的边界

1. **听感完全未验证**。本 Agent 没有音频感知工具。`musical_quality = unverified`、
   `listening = unknown`。以上全部是数值/结构证据。
2. **v3 的 F0 逐帧贴合度不如 v2**（44.2c vs 33.5c）。这是"表达设计"与"逐帧复刻"的取向差异，
   不是数值上的改进。**是否更好听必须由人耳判断。**
3. **图审未完成**：编译器生成了 58 个原生短语的图册，但本轮未逐张实际打开审阅。
   按 Skill，生成图册不计已审阅。
4. **`workflow_review_complete = false`**：缺少逐元音图审记录、intent lock 与独立 critique
   的完整绑定。技术执行通过，音乐流程未闭环。
5. **对拍器局限**：双检测器一致窗只覆盖约 51% 的帧；颤音速率上限约 8Hz；浅运动可能漏检。
6. 复用了用户授权的观测（分离/GAME/双F0/ASR），未重新分离或重新转谱。

---

## 六、下一步（建议）

1. **先听 `nianlun_v3_mix.wav` 和 `nianlun_v3_vocal_matched.wav`**，与 v2 对比。
2. 重点听：① 有无吞字/碎字（v2 的 p45–p50 有 22ms 字）；② 强弱是否有层次；
   ③ 虚实是否连贯；④ 旋律是否跑调。
3. 若仍"差"，请给出**具体位置 + 具体听感**（哪句/哪个字/什么感觉），
   这样我才能定位到层（音高/时钟/发声/混音）而不是继续盲改。

---

## 七、复现路径

```
songs/nianlun/sessions/20261028__unknown-model__nianlun-from-scratch-v2-20261028/scripts/v3_stage0_bind.py         复用观测 + SHA 校验
songs/nianlun/sessions/20261029__unknown-model__nianlun-v3-20261029/scripts/v3_stage1_final.py        歌词与 51 句结构
songs/nianlun/sessions/20261029__unknown-model__nianlun-v3-20261029/scripts/v3_segments.py            真实有声段检测
songs/nianlun/sessions/20261029__unknown-model__nianlun-v3-20261029/scripts/v3_stage2_clock6.py       自建字时钟（349 字）
songs/nianlun/sessions/20261029__unknown-model__nianlun-v3-20261029/scripts/v3_stage2b_score.py       USTX 谱面
songs/nianlun/sessions/20261029__unknown-model__nianlun-v3-20261029/scripts/v3_stage3_intent.py       逐句意图冻结
songs/nianlun/sessions/20261029__unknown-model__nianlun-v3-20261029/scripts/v3d_plan.py               自适应音高函数
songs/nianlun/sessions/20261029__unknown-model__nianlun-v3-20261029/scripts/v3b_remap.py              映射到 58 原生短语
  agent2utau compile-functions    编译（0.5c 通过）
songs/nianlun/sessions/20261029__unknown-model__nianlun-v3-20261029/scripts/v3_stage7c_phonation.py   发声层
  agent2utau render-project       渲染
songs/nianlun/sessions/20261029__unknown-model__nianlun-v3-20261029/scripts/v3_stage8_mix.py          混音
songs/nianlun/sessions/20261029__unknown-model__nianlun-v3-20261029/scripts/v3_stage9_verify.py       客观核验
```
