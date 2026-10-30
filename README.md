# agent2utau

**新的主线：原曲人声分离 → GAME 得到基础音符事件 → 歌词与音符映射 → Agent 局部音素/时间修正 → 泠鸢 DiffSinger 自动音高 → 渲染与混音。**

用户试听确认泠鸢 DiffSinger 的**自动音高已经很好**；因此**不再默认让 Agent 全曲绘制 PITD、颤音和滑音，也不再逐字复刻原唱的表达**。目标是旋律、歌词、节奏正确，由声库自然发挥。其它发声参数是否交给 Agent、混音是否需要自动化，**目前没有决定**。

## 现在需要做什么

最高优先级是：**让 MiniMax / DeepSeek 稳定进行唱字—GAME 音符—声库音素映射和时间修正**。采用“程序生成候选、Agent 消歧、程序写回与真实原生验证”的流程。当前已有工具，但尚没有一键跑通的新自动编排器。

- [当前唯一实施计划：plan.md](plan.md)（P0–P5、数据契约、验证、跨模型评测、给 MiniMax 的执行任务）
- [当前执行流程](docs/workflow.md) · [目录规范](docs/guides/repository-layout.md) · [Agent 协作约定](AGENTS.md)
- [跨模型歌词时间轴基准](benchmarks/model-comparisons/20261030-lyrics-alignment/) · [歌曲索引](songs/README.md)
- [旧计划归档](docs/archive/legacy-plans/) · [历史 README/AGENTS](docs/archive/legacy-guidance/)；旧路线不再作为执行指令。

## 新工作流

~~~text
原曲 → 分离 → GAME + 锁定歌词 + ASR/HFA 观测
    → 确定性单调映射（同字多音符/延音 + /休止/重字）
    → 当前泠鸢声库原生 phonemizer 生成 baseline
    → Agent 只选择局部候选/标 unresolved
    → USTX patch → OpenUtau 原生 roundtrip/音素再导出
    → DiffSinger 自动音高 + 默认发声
    → 人声渲染 + 固定增益伴奏混合 → 听评
~~~

GAME 是 **note events**，不是原唱字界；原唱 HFA 不等于声库合成音素时钟。先修歌词、时序与音素，再考虑是否需要表情参数，避免变量混杂。旧 `compile-functions` / `singing-expression-editor` 保留为历史/可选实验，不属于现在的默认制作链。

## 现有实现和目标结构

| 路径 | 用途与状态 |
|---|---|
| `src/agent2utau/audio/` | 已有音频解码、分离、固定增益混音 |
| `src/agent2utau/transcription/game_onnx.py` | 已有 GAME 音符提取 |
| `src/agent2utau/analysis/` | 已有歌词 ASR、F0 观测 |
| `src/agent2utau/openutau/`、`bridge/OuBridge/` | 已有 USTX 建谱与原生导出/渲染 |
| `src/agent2utau/alignment/` | **待创建**：锁歌词、音符映射、原生音素、patch、validator |
| `tests/`、`benchmarks/` | 现有测试与模型对照，音素专项待扩展 |
| `songs/`、`experiments/`、`research/` | 现有歌曲 session、研究与历史证据 |
| `docs/archive/` | 废弃计划和历史入口快照，非当前生产指令 |

## 现有命令（工具，不是一键工作流）

~~~powershell
python -m pip install -e .
agent2utau doctor
agent2utau observe-source "<原曲>" --out "runs/production/<新任务>/observations" --steps separate,asr,game
agent2utau export-phonemes --project "<工作谱面.ustx>" --out "<音素.json>"
agent2utau roundtrip --project "<工作谱面.ustx>" --out "<目录>"
agent2utau render-project --project "<验证后的谱面.ustx>" --out "<音频>"
~~~

当前 `openutau/build.py` 使用**固定 120 BPM / 480 分辨率**把绝对秒映射成 USTX tick，**不是自动 BPM 检测**。配置本机 OpenUtau、泠鸢 DiffSinger、GAME、HFA 与 ffmpeg；`configs/local.yaml`、模型、原曲、`runs/` 和 `projects/latest/` 不提交 Git。

歌曲：[年轮](songs/nianlun/) · [最后一页](songs/lastpage/) · [雨爱](songs/yuai/) · [花海](songs/huahai/)；历史制作与模型归属保持，新的 session 记录日期与执行 AI。2026-10-30 的 [目录整理记录](migration/20261030-reorganization/) 不重跑。

**待定事项**：是否人工或 Agent 调 VOIC/BREC/TENC/DYN/PEXP；是否引入现成的自动混音/母带项目。先以默认模型演唱与透明固定混音建立听感基线。
