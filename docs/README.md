# 文档与知识资料

| 分类 | 位置与入口 |
|---|---|
| 当前计划 | 根目录[plan.md](../plan.md)与[表2专项计划](../plan-table2.md)，不复制到文档目录 |
| 制作流程/已有接口 | [workflow.md](workflow.md)、[evaluation-v0.md](evaluation-v0.md)；保留已被Skill和其它文档引用的入口路径 |
| 本轮授权复检补全 | [要求](skill-execution-review-requirements.md)、[实际结果](skill-execution-review-results.md)；这两份根层文件是用户指定路径例外 |
| 目录与文件规范 | [guides/repository-layout.md](guides/repository-layout.md) |
| 知识与结构化清单 | [knowledge/acoustic-manifestations-20261009](knowledge/acoustic-manifestations-20261009/README.md)，表1、表2、CSV/JSON和审计包同目录 |
| 新可读报告 | `reports/<主题>/`；本次[目录迁移报告](reports/maintenance/directory-reorganization-20261009.md)在`reports/maintenance/` |
| 历史评价结果 | [evaluation-v0-findings.md](evaluation-v0-findings.md)、[evaluation-v0-next-step.md](evaluation-v0-next-step.md) |
| 历史计划审查/路线清理 | [plan-feasibility-review-20261008.md](plan-feasibility-review-20261008.md)、[repository-cleanup.md](repository-cleanup.md) |
| 封存实验报告 | 本目录原`lastpage-*-20261008.md`；原路径/字节/SHA保留，原始报告互引不改；入口由[表2](knowledge/acoustic-manifestations-20261009/conditional-responses.md)索引 |

原始报告是有版本和绑定的证据，不因为目录整理改写历史结论。已有稳定入口及封存报告作为明确的历史例外保留原路径；新方法文档放`guides`、新报告放`reports`、新知识包放`knowledge`，不要继续把新文件平铺在本目录。

这里只保存可审查的说明和聚合证据。完整数组、音频、图册、日志、模型输入与运行输出放ignored `runs`；只提交必要的文本说明、有限聚合值和SHA，避免复制封存run。
