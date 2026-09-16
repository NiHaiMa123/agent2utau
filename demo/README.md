# 试听 Demo —《年轮》泠鸢翻唱（run `cover-20260916-094634-841c`）

> **旧版已被试听判定不可用。** 以下旧 MP3 保留用于对照，不能视作完整合格成品。
> 已查明错误版本歌词、F0 无声掩码反转、ASR 采样率错误、音符量化重叠吞字及混音未匹配电平。
> 修复说明与新试听入口见 `docs/audition-repair-20260916.md`。

在 GitHub 上点开任意 `.mp3` 文件页即可内嵌播放。

| 文件 | 内容 |
|---|---|
| `nianlun_mix_full.mp3` | **完整混音成品**（泠鸢人声 + 原伴奏，274.5s） |
| `nianlun_vocal_pitd.mp3` | 干声 — pitd 修正版（自动选中） |
| `nianlun_vocal_baseline.mp3` | 干声 — 模型基线（A/B 对比用） |
| `color_Yousa_{Bright,Classic,Cute,Normal,Whisper}.mp3` | 五音色同片段对比（各 ~25s） |

已知限制（详见各 run 的 `report.json` caveats）：固定 120bpm 时间轴、
对唱源用单声部渲染、一行歌词因编排不符跳过、`quality_confidence: low`。

## v2 修复版（run `cover-20260916-102646-95f0`，commit `2eaf9d1` 之后）

修复 F0 掩码反转、ASR 采样率、逐字声学对齐、吞字量化问题后重渲：

| 文件 | 内容 |
|---|---|
| `v2_nianlun_mix_full.mp3` | 完整混音（已按参考人声自动配比） |
| `v2_nianlun_vocal.mp3` | 干声（631 音符，含录音室版歌词对齐） |

音高指标已大幅改善（中位 17.4 音分、覆盖率 94.6%），但感知上仍存在
跑调/咬字问题——`status=completed_with_warnings`，待试听确认。
