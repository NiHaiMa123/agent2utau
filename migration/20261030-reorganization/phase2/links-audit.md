# P0-B 文档链接审计

扫描当前 Git 跟踪的全部 Markdown（330 个文件），逐条解析 `](target)`：

| 分类 | 数量 | 含义 |
|---|---|---|
| ok | 1622 | 目标在 Git 跟踪中且存在 |
| local-only | 169 | 目标只在本机（runs/、projects/latest/*.ustx、音频等，被 .gitignore 排除），**GitHub 上打不开属正常** |
| external | 238 | 外部链接，未做网络检查 |
| outside | 33 | 指向仓库外的相对路径 |
| broken | 826 | 仓库内不存在 |

## 已修（活动文档）

- `songs/lastpage/reports/legacy/conditioned-voicing-feedback-20261011.md` → `../../sessions/20261011__unknown-model__lastpage-conditioned-voicing-20261011/reports/conditioned-voicing-feedback-20261011-audit.json`（原 `../../../../experiments/misc/reports/conditioned-voicing-feedback-20261011-audit.json`）
- `songs/lastpage/sessions/20261011__unknown-model__lastpage-accepted-baseline-20261011/reports/whole-song-baseline-review-20261011.md` → `whole-song-baseline-review-20261011-phrases.csv`（原 `../../../../../experiments/misc/reports/whole-song-baseline-review-20261011-phrases.csv`）
- `songs/lastpage/sessions/20261011__unknown-model__lastpage-li-kan-author-reference-20261011/reports/li-kan-author-reference-20261011.md` → `li-kan-author-reference-20261011-audit.json`（原 `../../../../../experiments/misc/reports/li-kan-author-reference-20261011-audit.json`）

## 未修（历史冻结证据，只登记不修改）

共 826 处，全部位于 `docs/knowledge/**/history/`、`research/implementation-records/`
等**受保护的历史快照**内。这些快照是第一轮前的原始证据，其链接指向当时的路径；
按整理计划「不因修链而修改受保护的旧字节」，只在此登记。

可查证的处理方式：这些历史目录本身已在 `docs/knowledge/` 内，其当前有效版本在同包的活动索引文件中；
对外检索走 `docs/knowledge/acoustic-manifestations-20261009/active-knowledge-sources.json`。

按出现文件分组（前 12 组）：

- `docs/knowledge/acoustic-manifestations-20261009/history/pre-table2-2e-execution-20261011/plan.md`：45 处
- `docs/knowledge/acoustic-manifestations-20261009/history/pre-table2-2e-execution-20261011/docs/knowledge/acoustic-manifestations-20261009/README.md`：42 处
- `docs/knowledge/acoustic-manifestations-20261009/history/pre-table2-2e-native-20261010/plan.md`：42 处
- `docs/knowledge/acoustic-manifestations-20261009/history/pre-table2-2e-native-20261010/docs/knowledge/acoustic-manifestations-20261009/README.md`：39 处
- `docs/knowledge/acoustic-manifestations-20261009/history/pre-table2-2e-prep-20261010/plan.md`：37 处
- `docs/knowledge/acoustic-manifestations-20261009/history/pre-table2-2e-prep-20261010/docs/knowledge/acoustic-manifestations-20261009/README.md`：35 处
- `docs/knowledge/acoustic-manifestations-20261009/history/pre-table2-2d-20261010/plan.md`：32 处
- `docs/knowledge/acoustic-manifestations-20261009/history/pre-table2-2e-execution-20261011/README.md`：32 处
- `docs/knowledge/acoustic-manifestations-20261009/history/pre-table2-2e-native-20261010/README.md`：31 处
- `docs/knowledge/acoustic-manifestations-20261009/history/pre-table2-2e-prep-20261010/README.md`：30 处
- `docs/knowledge/acoustic-manifestations-20261009/history/pre-table2-2d-20261010/README.md`：28 处
- `docs/knowledge/acoustic-manifestations-20261009/history/pre-table2-2c-20261010/README.md`：26 处

## 本机专属链接的说明

根 README 顶部导航已写明：`runs/`、`projects/latest/*.ustx`、`data/`、`models/`、`external/`、`demo/`
均为**仅本机、不随 Git 发布**的目录；文中指向它们的链接在 GitHub 上打不开属预期行为，
本机按原路径访问。
