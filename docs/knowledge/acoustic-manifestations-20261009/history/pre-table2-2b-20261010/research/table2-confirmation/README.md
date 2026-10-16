# 表2记录确认研究

当前阶段2A只做现有记录的来源/比较/版本绑定审计，不执行新模型、解码音频、复制数组、编辑工程或修改Skill。`stage_2a_review_data.py`保存明确的比较角色、来源与差异决定；不是调参方案或自动实验队列。

`freeze_stage_2a.py`先核对F产物SHA，按原字节保存17份现行文档，绑定原36来源及附加的既有反馈/审计记录。快照在知识包history，绑定在`stage_2a_baseline_binding.json`；已有冻结拒绝覆盖。快照内链接仍按原位置解释，不改历史字节。预冻结有一处附加候选文件名误用，原条目保留，2A另按果实验封存manifest补实际`preservation_check.json`并公开勘误，不视作旧文件丢失。

```powershell
.venv/Scripts/python.exe research/table2-confirmation/freeze_stage_2a.py --run <全新runs/research目录>
.venv/Scripts/python.exe research/table2-confirmation/build_stage_2a.py --run <该冻结目录>
.venv/Scripts/python.exe research/table2-confirmation/verify_stage_2a.py --run <该冻结目录>
```

冻结已完成，正常复核只运行build/verify。构建器核对明确登记的五份实验完成清单，逐文件计算SHA；只读取清单给定路径，不遍历旧cache选结果。音频、NPZ、F32只流式计算字节SHA，不解码、加载或派生声学指标；第二次无缓存核对防止审计过程中变化。公开JSON/CSV只存有限来源/角色/聚合检查与SHA，不提交运行数组和完整文件清单。

BREC有效路径取cohort内明确的`A_path/B_path/relative_dir`，必须为`_grid5`版本；旧1tick草稿不是有效成声输入。抱C的主听觉对照为旧B，原A及A-C F0参照分别保留。实际用户绑定音频与所有保留交付分别列出；六条件BREC仍共一次汇总反馈，不补未知细分标签。

每设计的runtime清单只比较历史声明范围、共同SHA及差异；不重新打开当前外部模型/安装、不把共享47项自动套给TENC混合依赖清单。原pending字段保存执行时角色，后续反馈单列。原JSON/CSV/Markdown、F产物、旧run、报告、工程和Skill保持字节；2B修订记录schema、2C复核隔离/指标/结论，尚未执行。

结果见[2A报告](../../docs/knowledge/acoustic-manifestations-20261009/table2-review.md)、[绑定JSON](../../docs/knowledge/acoustic-manifestations-20261009/comparison-bindings.json)与[差异](../../docs/knowledge/acoustic-manifestations-20261009/table2-record-differences.json)。当前步骤以[根目录计划](../../plan.md)及关联[表2专项计划](../../plan-table2.md)为准。新因果渲染/人工试听依后续冻结范围推进，不因记录审计完成而自动开始。
