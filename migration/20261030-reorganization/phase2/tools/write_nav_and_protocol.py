"""P0-B 余项 + P2-F：benchmark protocol 补全字段；根 README 加顶部导航并标注本机专属链接。"""
import re
import sys
from pathlib import Path

ROOT = Path(r"E:\project\agent2utau")
sys.stdout.reconfigure(encoding="utf-8")

# ---------- 1) benchmark protocol：补齐任务书要求的字段 ----------
proto = ROOT / "benchmarks" / "model-comparisons" / "20261030-lyrics-alignment" / "protocol.md"
proto.write_text("""# 跨模型歌词时间轴对照 · 协议模板

> 用途：同一首歌、同一输入，比较不同 AI 模型产出的**歌词时间轴**质量。
> 本目录目前只有已知的主观结果与本模板，**没有新的量化数据**；不填假的误差、成本或成功率。

## 1. 任务范围

- 歌曲：`<song>`（见 `songs/<song>/`）
- 范围：`<例：整曲歌词时间轴 / 指定段落>`
- 输入资产与其 SHA256（逐项列出，模型之间必须一致）：
  - `<原始音频路径>` — sha256 `<…>`
  - `<歌词文本>` — sha256 `<…>`

## 2. 模型与配置

每个模型一行，缺项写 `unknown`：

| 模型 slug | 版本/思考档位 | 工具权限 | 预算（token/时长） | 上下文与种子 | 原始日志路径 |
|---|---|---|---|---|---|
| `gpt-6.1-sol` | `<…>` | `<读文件/写文件/运行命令>` | `<…>` | `<…>` | `<…>` |
| `gemini-4` | `<…>` | `<…>` | `<…>` | `<…>` | `<…>` |
| `minimax-m3.1f` | `<…>` | `<…>` | `<…>` | `<…>` | `<…>` |
| `deepseek-v4.1f` | `<…>` | `<…>` | `<…>` | `<…>` | `<…>` |
| `gemini-3.8-flash` | `<…>` | `<…>` | `<…>` | `<…>` | `<…>` |

## 3. 输出约定

- 每次运行的产物写在自己的 session：`<song>/sessions/<YYYYMMDD-HHMM>__<model-slug>__<run-id>/`。
- 原始日志、音频与中间结果放 `local/`（被忽略），可复查的小型结果放 `results/`。
- 模型归属必须有原始日志或 manifest 佐证，否则记 `unknown-model`。

## 4. 误差口径

时间轴误差按**字级**统计，单位毫秒：

| 指标 | 定义 |
|---|---|
| 字起点偏差 | 该字在输出中的起点 − 参考起点，取绝对值 |
| 字尾偏差 | 同上，对字尾 |
| 字时长比 | 输出时长 ÷ 参考时长 |
| 缺失/多字 | 与参考逐字对齐后多出或缺失的字数 |
| 音素切分偏差 | 输出音素块边界 − 参考边界（可选） |

统计口径固定为：**同一参考时间轴、同一对齐算法、逐字取中位数与 p90**；不做人工修整。

## 5. 人工/盲评

- 音频盲评：随机化 A/B 顺序，评分表固定；**记录评分人、日期与是否有耳朵参考**。
- 用户主观反馈单独记录原话与限定范围，不与自动指标混写。
- 没有数据的项写 `unknown`，不写“无差异”。

## 6. 当前已知结果（可查证部分）

- 用户主观：GPT-6.1 Sol 与 Gemini 4 的效果尚可；其余模型存在歌词时间问题。
- 其余量化指标、具体误差、成本与成功率：**没有证据，记 unknown**。
""", encoding="utf-8")
print("protocol updated")

# ---------- 2) 根 README：顶部导航 + 本机专属链接标注 ----------
readme = ROOT / "README.md"
text = readme.read_text(encoding="utf-8")
NAV = """# agent2utau

> **导航**
> - 歌曲制作：[songs/](songs/README.md)（[年轮](songs/nianlun/) · [雨爱](songs/yuai/) · [最后一页](songs/lastpage/) · [花海](songs/huahai/)）
> - 基准测试：[benchmarks/](benchmarks/model-comparisons/20261030-lyrics-alignment/)
> - 方法实验：[experiments/](experiments/)
> - 通用代码：`src/agent2utau/`（CLI 与独立评价）、`bridge/`（原生桥）、`skills/`（制作 Skill）、`tests/`（自动测试）
> - 文档与规范：[docs/README.md](docs/README.md) · [目录规范](docs/guides/repository-layout.md) · [工作流](docs/workflow.md)
> - 本机产物（**仅本机，不随 Git 发布**）：`runs/`、`projects/latest/*.ustx`、`data/`、`models/`、`external/`、`demo/` ——
>   本文与各 README 里指向这些路径的链接，在 GitHub 上打不开属正常；可在本机按原路径访问。
> - 目录整理的盘点与验收记录：[migration/20261030-reorganization/](migration/20261030-reorganization/)
"""
if text.startswith("# agent2utau\n"):
    rest = text[len("# agent2utau\n"):].lstrip("\n")
    text = NAV + "\n" + rest
    readme.write_text(text, encoding="utf-8")
    print("README nav inserted")
else:
    print("README header not matched; skipped")

# ---------- 3) docs/README 对齐新入口 ----------
docs_readme = ROOT / "docs" / "README.md"
if docs_readme.exists():
    t = docs_readme.read_text(encoding="utf-8")
    add = """
## 新增入口（2026-10-30 整理后）

- 歌曲制作索引与交付索引：`../songs/README.md`（各歌 `README.md` + `releases/README.md`）
- 方法实验：`../experiments/`
- 跨模型对照：`../benchmarks/model-comparisons/20261030-lyrics-alignment/`
- 长期目录规范（替代旧的 runs/ 与 projects/ 单一入口说法）：`guides/repository-layout.md`
- 整理迁移的盘点/映射/验收：`../migration/20261030-reorganization/`

注意：`docs/reports/` 下部分公开文档被 `docs/knowledge` 知识包按**路径+SHA**绑定，
必须留在该目录，不能因为"按歌曲集中"而搬动；各歌曲 README 里已单独列出这些保留原位的文档。
"""
    if "新增入口（2026-10-30 整理后）" not in t:
        docs_readme.write_text(t.rstrip() + "\n" + add, encoding="utf-8")
        print("docs/README updated")
