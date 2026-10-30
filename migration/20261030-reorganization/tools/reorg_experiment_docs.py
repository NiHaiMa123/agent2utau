"""为 experiments/ 与 benchmarks/ 写入口说明，并重生成 session manifest 与歌曲 README。"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(r"E:\project\agent2utau")
sys.stdout.reconfigure(encoding="utf-8")

EXPERIMENTS = {
    "alignment": ("音素/歌词对齐", "HFA 强制对齐、GAME 音符事件、ASR 转写、字级时钟重建的通用实验。"),
    "pitch": ("音高", "F0 提取与对比、PITD 曲线生成、音高主体/字腹形状的通用研究。"),
    "phonation": ("发声", "VOIC/BREC/TENC/声线等发声参数的 A/B 研究与剂量-响应探针。"),
    "evaluation": ("独立评价", "独立事实、消融与对照实验；评价接口本身在 src/agent2utau/evaluation，不搬到这里。"),
    "research-tables": ("表1/表2 复核", "研究表1/表2 的复核记录（与 research/table1-*、table2-* 对应）。"),
    "research-baishuo": ("白烁研究", "白烁相关的研究性实验；作者原件仍在 research/baishuo，字节不变。"),
    "covers": ("试唱/对照", "面向某首歌的局部试唱与版本对照，脚本按歌曲归档在 songs/ 下。"),
    "diagnostics": ("诊断脚本", "通用诊断工具（不含歌曲归属的最小复现）。"),
}
for cat, (title, desc) in EXPERIMENTS.items():
    d = ROOT / "experiments" / cat
    d.mkdir(parents=True, exist_ok=True)
    (d / "README.md").write_text(f"# experiments/{cat} — {title}\n\n{desc}\n\n"
                                 f"本目录只放**通用技术实验**；属于某首歌的局部修订/试唱放在 "
                                 f"`songs/<song>/sessions/<session>/scripts|reports`。\n", encoding="utf-8")

bench = ROOT / "benchmarks" / "model-comparisons" / "20261030-lyrics-alignment"
(bench / "README.md").write_text(
    "# 20261030 歌词时间轴跨模型对照\n\n"
    "同一首歌的歌词时间轴在多个 AI 模型上各跑一遍，比较它们的歌词对齐结果。\n\n"
    "- `protocol.md`：对照协议与输入说明。\n"
    "- `results/`：小型对照记录（表、结论）。\n"
    "- `local/`：被忽略的原始输出与音频（不进 Git）。\n\n"
    "已知且可查证的用户主观结果：GPT-6.1 Sol 与 Gemini 4 效果尚可，其余模型存在歌词时间问题。\n"
    "其余细节（各模型输入、模式、日志、误差、成本）没有可核证据，一律记 unknown，不造分数。\n", encoding="utf-8")
(bench / "protocol.md").write_text(
    "# 对照协议\n\n"
    "## 目的\n比较不同 AI 模型在同一首歌的**歌词时间轴**产出上的差异，定位是模型能力问题还是流程问题。\n\n"
    "## 已知输入\n"
    "- 歌曲：年轮（见 `songs/nianlun/`）。\n"
    "- 模型：gpt-6.1-sol、gemini-4、minimax-m3.1f、deepseek-v4.1f、gemini-3.8-flash。\n"
    "- 统一入口：本仓库的 `python -m agent2utau.cli` 与 `skills/singing-expression-editor`。\n\n"
    "## 指标\n"
    "- 歌词字与时间轴的对齐偏移（毫秒）。\n"
    "- 每个模型产出里被复检判负的单元数。\n\n"
    "## 证据要求\n"
    "每个模型必须留下原始执行日志或 manifest；没有原始日志的模型只能记 unknown-model，"
    "不得因为脚本由谁写成就把作品归给那个模型。\n", encoding="utf-8")
(bench / "results" / "README.md").write_text(
    "# 对照结果\n\n"
    "这里放小型对照记录（CSV/表格/结论）。原始音频与完整日志放 `local/`（被忽略）。\n\n"
    "当前状态：已知的用户主观结果是「GPT-6.1 Sol 与 Gemini 4 效果还行，其余模型歌词时间有问题」；"
    "其余量化指标尚无证据，暂记 unknown。\n", encoding="utf-8")
print("experiments/benchmarks readmes written")
