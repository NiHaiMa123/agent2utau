# 废弃计划与原字节历史备份

2026-10-31 切换到 DiffSinger 自动音高路线后，下列文件只用于**历史查证**，不再是执行指令：

- [旧根 plan.md：表1及大量历史制作记录](plan-table1-pre-autopitch-20261031.md)
- [旧 plan-table2.md：表2专项参数研究计划](plan-table2-pre-autopitch-20261031.md)
- [2026-10-30 目录整理计划](PROJECT_REORGANIZATION_PLAN_20261030.md)

全部使用原 Git blob 保留字节；内部相对链接以旧仓库根路径为原始上下文，归档时不重写历史证据。**现行计划**：[根目录 plan.md](../../plan.md)。

---

## 废止入口索引（代码仍在，但不再是主线）

2026-10-31 起主线改为"分离 → GAME → 锁定歌词 → 确定性字—音符映射 → 声库原生音素 → 局部时间修正 → 自动音高"。
下面这些入口属于**旧的显式表达线**（Agent 逐句画 PITD、逐句冻结表达意图），保留是为了旧实验可复现和历史查证，**不作为新任务依赖，也不要继续扩写**。

| 废止入口 | 位置 | 现状替代物 | 备注 |
|---|---|---|---|
| `singing-expression-editor` Skill | `skills/singing-expression-editor/` | 无（新主线是程序生成候选＋Agent 选候选） | 仍被仓库门禁校验其内部链接；方法资料可查，制作入口已停用 |
| 显式表达编译 | `agent2utau compile-functions` | `agent2utau align-lyrics` + `src/agent2utau/alignment/` | 旧"计划→编译→执行审查"链；不是新对齐器 |
| 音乐意图冻结 | `agent2utau freeze-musical-intent` | 无 | 旧线专有 |
| 执行审查链 | `agent2utau review-inventory` / `review-execution` / `review-delivery` | 无 | 旧线专有；对应 `src/agent2utau/evaluation/execution_review.py` |
| 知识接入 | `agent2utau knowledge-context`、`src/agent2utau/knowledge.py`、`docs/knowledge/**` | 无（新主线不查表1/表2参数） | 表1/表2属旧参数实验线；知识包**逐字节只读**，按路径＋SHA 绑定，不得删改 |
| 表达设计模块 | `src/agent2utau/expression/` | `src/agent2utau/alignment/` | 旧"函数化画线"组件；新主线不画整曲 PITD |
| 旧评估模块 | `src/agent2utau/evaluation/phonation*.py`、`controlled_probe.py`、`musical_review.py` | 无 | 绑定旧知识包与表达设计 |
| 历史实现记录 | `research/implementation-records/**` | 无 | 只读历史证据，按原字节保留 |
| 作者原件与授权包 | `research/baishuo/**` | 无 | 逐字节只读、SHA 核对；不是新歌的目标曲线来源 |
| 旧歌曲 session | `songs/*/sessions/**` | 无 | 历史制作记录与索引；不迁移、不重跑 |

仍然属于**现行主线**、不要标废止的部分：`src/agent2utau/{audio,transcription,analysis,openutau,alignment,resources,util}/`、`bridge/OuBridge/`（原生导出与渲染）、`schemas/`、`tests/`、`configs/`、`experiments/alignment/`、`songs/*/sessions/` 里 2026-10-31 起的新 session。

通用性工具型评估模块（`evaluation/wavcheck.py`、`local_views.py`、`features.py`、`independent.py`）不随旧线废止，可继续使用。
