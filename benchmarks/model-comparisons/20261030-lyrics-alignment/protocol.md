# 对照协议

## 目的
比较不同 AI 模型在同一首歌的**歌词时间轴**产出上的差异，定位是模型能力问题还是流程问题。

## 已知输入
- 歌曲：年轮（见 `songs/nianlun/`）。
- 模型：gpt-6.1-sol、gemini-4、minimax-m3.1f、deepseek-v4.1f、gemini-3.8-flash。
- 统一入口：本仓库的 `python -m agent2utau.cli` 与 `skills/singing-expression-editor`。

## 指标
- 歌词字与时间轴的对齐偏移（毫秒）。
- 每个模型产出里被复检判负的单元数。

## 证据要求
每个模型必须留下原始执行日志或 manifest；没有原始日志的模型只能记 unknown-model，不得因为脚本由谁写成就把作品归给那个模型。
