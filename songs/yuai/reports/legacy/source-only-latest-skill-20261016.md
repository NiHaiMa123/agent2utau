# 雨爱 source-only 制作报告（2026-10-16）

范围：只用源 FLAC、分离人声、GAME 音符事件与逐帧 F0 观测，按最新 Skill 逐句流程重制整曲。
未读取历史制作 run、未读取白烁工程/曲线/参数。

## 结论

研究/技术交付完成，可试听候选已生成；音乐听感未验证（无试听工具，等待用户反馈）。

- 工程：`delivery/yuai_source-only_v1.ustx`（54 段、137 原生乐句、405 音符）
- 音频：`delivery/yuai_source-only_v1_mix.wav/.mp3`（260.5s，人声+6dB / 伴奏−6dB，峰值 0.831，无削波）
- 纯人声：`delivery/yuai_source-only_v1_vocal.mp3`

## 观测与乐谱

- `source/`：解码、MelBand Roformer 分离、faster-whisper ASR、GAME、FCPE/RMVPE 双 F0
- 标准歌词（官方歌词）校正 ASR 误差；拼音 `.lab` 送 HFA 强制对齐，365 音节序列与 HFA 词层 100% 匹配
- 乐谱：HFA 音节边界定时 + GAME 音符音高；多音音节保留为延续音（56 个 `+`）
- 底谱经原生核验：54 段、139 render phrases、无无效音符/音素

## 逐句设计（最新 Skill 方法）

- 源观察：逐句连续 F0 + GAME 音符骨架 → `design/native_struct.json`
- 主体模型 `design/bodymodel.py`：分离慢中心与振荡，测真实颤音（多为 4–8Hz、深度 8–70c）
- 函数设计：音符级保持/短连接 + 有限回收（finite_return）+ 变深变速周期（oscillation）
- 逐句意图：`contract/brief.json`（137 句、361 单元）→ `freeze-musical-intent` 冻结（计划存在前）
- 数值计划：`design/plan.json`（schema2，137 句全覆盖）；实际线读回误差 ≤0.49996c
- 前向账本 `contract/ledger.json`：361 单元决策（hold 185 / center 109 / oscillation 40 / finite_return 27）
- 图审：`contract/final-review` atlas，逐字实际打开 361 元音完整视图及邻接

## 知识与边界

- `design/knowledge_context.json`：取表1机制实体（ACO:P4/P5、EVT:P3/T5、PER:S1、ACO:S1）+ OpenUtau 控制参数（C03.01/C10.01/C11.01/C13.01/C19.01），逐 ID 决策
- 未取歌相关响应/反馈包（本次用户边界禁用历史制作载荷），absence_reason 已记录
- 未改歌曲发布工程、旧 run、Skill；未启用 CI；单 Agent

## 验证状态（诚实分列）

| 项 | 状态 |
|---|---|
| 原生身份/时钟/覆盖 | pass |
| 实际动作执行 | 358 pass / 3 unknown |
| 逐字图审覆盖 | 357 / 361 |
| 前向意图与消融 | agent_attested（intent_execution/discrimination 因 4 个微元音+非区分性 hold 未判 pass） |
| 结构性提示 | 全零中心斜率（音符级锚点，已在 critique 说明）+ 归一化重复形态（源共性） |
| 未通过单元 | 4 个：均为 10ms 微元音（后字声母被音素器提前放置，核被挤到 10ms，无法验证主体） |
| technical_execution_complete | False（4 个微元音未覆盖，未包装为完成） |
| musical_quality | unverified |
| 听感 | unknown（未听） |

## 未决与下一步

- 4 个未通过单元（p12:f0:v1、p14:f0:v3、p37:f0:v1、p41:f0:v3）：10ms 微元音源于源时钟（声母提前），不改源时钟的边界内无法给出可用元音；如实保留 unknown。
- 17 个 hold 被 tool 标为 non-discriminating（浅对照可满足）：因全零中心斜率的源驱动设计，已如实列出。
- 下一步接本版整曲试听反馈，不自动扫参、不改源时钟掩盖问题。

## 边界重申

技术通过 ≠ 听感通过。RMS、频谱、F0 保持、图审均不能代替听觉验收。本次未生成任何新听觉结论。
