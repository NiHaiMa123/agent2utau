# 表2记录确认研究

现行2A–2C记录确认已收口，状态record_review_complete_with_explicit_gaps；[2C逐行报告](../../docs/knowledge/acoustic-manifestations-20261009/table2-record-confirmation.md)、[JSON](../../docs/knowledge/acoustic-manifestations-20261009/table2-record-confirmation.json)和[审计](../../docs/knowledge/acoustic-manifestations-20261009/table2-stage-2c-audit.json)为当前入口。以下2B/2A说明保留各自阶段时态，原审计输出不刷新。

`freeze_stage_2c.py`冻结26份文档/脚本并核对40份直接注册的输入/预测数组SHA，不复制数组。`stage_2c_inputs.py`独立检查原生/variance支撑、SHFC浮点变换、人工增量、native/fresh最终算术和重复输入/预测；`build_stage_2c.py`读取全部明确manifest绑定的60份输入/预测NPZ（含20份A-repeat）与JSON，129读取文件前后SHA保持。823原指标标量字段回到原结果JSON/报告核对，RMS比dB及观察配对中位数差检查；新模型/原生执行、PCM/mel/检测器数组读取或声学复测均0。`verify_stage_2c.py`再独立重建20版本的最终三通道、检查精确恢复、来源/反馈/CSV/Markdown与已确认/部分/unknown范围；3个混杂错误样例拒绝，2B写入口拒绝降级覆盖。

```powershell
.venv/Scripts/python.exe research/table2-confirmation/build_stage_2c.py --run runs/research/table2-2c-record-confirmation-20261010
.venv/Scripts/python.exe research/table2-confirmation/verify_stage_2c.py --run runs/research/table2-2c-record-confirmation-20261010 --local-checks
```

schema版本仍3，只更新record_confirmation、增加confirmation_ref及顶层确认引用；移除新增确认字段并还原2B状态后应精确等于更新前JSON，CSV其余单元格相同，旧Markdown主体保留。范围迁移见[迁移清单](../../docs/knowledge/acoustic-manifestations-20261009/table2-confirmation-migration.json)。36项限定确认、24部分及56未知是每条声明范围统计，不能当新增样本。当前测量协议的measurement_validated仍全部false，通用规律0；下一步2D梳理缺口与冻结有限设计，新因果试听在2E，不在记录收口时自动开始。

## 2B阶段历史说明

2B当时完成schema 3修订，2C尚未执行。[2B报告](../../docs/knowledge/acoustic-manifestations-20261009/table2-schema-review.md)、[字段说明](../../docs/knowledge/acoustic-manifestations-20261009/table2-fields.md)与[审计](../../docs/knowledge/acoustic-manifestations-20261009/table2-stage-2b-audit.json)为2B冻结时入口；现在2B写入口已guard，现行使用上方2C构建/验证。以下2A说明保留当时范围。

2B先冻结26份文档/脚本，拒绝覆盖。`build_stage_2b.py`只读明确绑定的历史JSON与两份打包/分析脚本，给14记录新增record_v3、17比较、6反馈组；C在本轮fresh/B槽位，旧B在上一轮SHFC，依据封存脚本而非文件名猜测。旧字段保留，可恢复到schema 2；10行原CSV旧单元格保持，14行结构CSV另列。原F及2A的写入口在2B注册后拒绝运行，不能把旧审计刷新成当前新版通过；原脚本字节在pre-table2-2b快照。

```powershell
.venv/Scripts/python.exe research/table2-confirmation/build_stage_2b.py --run runs/research/table2-2b-schema-revision-20261010
.venv/Scripts/python.exe research/table2-confirmation/verify_stage_2b.py --run runs/research/table2-2b-schema-revision-20261010 --local-checks
```

现行验证检查旧JSON深度恢复、旧CSV等式、Markdown原主体、声明schema关键词及3个错误样例拒绝、版本/比较/反馈/表1引用、52份来源元数据SHA、67保护输入SHA、4个历史入口guard与文档链接。无外部JSON Schema引擎，验证范围限本schema实际使用的type/required/const/enum/minItems/minLength/items/properties，并补比较ID/来源语义核查；不声称所有标准关键词实现。2B不打开音频/数组，也不验证当前外部模型/设备，不新执行原实验。

## 2A阶段历史说明

2A当时只做现有记录的来源/比较/版本绑定审计，不执行新模型、解码音频、复制数组、编辑工程或修改Skill。`stage_2a_review_data.py`保存明确的比较角色、来源与差异决定；不是调参方案或自动实验队列。

`freeze_stage_2a.py`先核对F产物SHA，按原字节保存17份现行文档，绑定原36来源及附加的既有反馈/审计记录。快照在知识包history，绑定在`stage_2a_baseline_binding.json`；已有冻结拒绝覆盖。快照内链接仍按原位置解释，不改历史字节。预冻结有一处附加候选文件名误用，原条目保留，2A另按果实验封存manifest补实际`preservation_check.json`并公开勘误，不视作旧文件丢失。

```powershell
.venv/Scripts/python.exe research/table2-confirmation/freeze_stage_2a.py --run <全新runs/research目录>
.venv/Scripts/python.exe research/table2-confirmation/build_stage_2a.py --run <该冻结目录>
.venv/Scripts/python.exe research/table2-confirmation/verify_stage_2a.py --run <该冻结目录>
```

2A冻结已完成；下列2A入口现在为历史说明，2B注册后拒绝覆盖。2A当时构建器核对明确登记的五份实验完成清单，逐文件计算SHA；只读取清单给定路径，不遍历旧cache选结果。音频、NPZ、F32只流式计算字节SHA，不解码、加载或派生声学指标；第二次无缓存核对防止审计过程中变化。公开JSON/CSV只存有限来源/角色/聚合检查与SHA，不提交运行数组和完整文件清单。

BREC有效路径取cohort内明确的`A_path/B_path/relative_dir`，必须为`_grid5`版本；旧1tick草稿不是有效成声输入。抱C的主听觉对照为旧B，原A及A-C F0参照分别保留。实际用户绑定音频与所有保留交付分别列出；六条件BREC仍共一次汇总反馈，不补未知细分标签。

每设计的runtime清单只比较历史声明范围、共同SHA及差异；不重新打开当前外部模型/安装、不把共享47项自动套给TENC混合依赖清单。原pending字段保存执行时角色，后续反馈单列。原JSON/CSV/Markdown、F产物、旧run、报告、工程和Skill保持字节；2B修订记录schema、2C复核隔离/指标/结论，尚未执行。

结果见[2A报告](../../docs/knowledge/acoustic-manifestations-20261009/table2-review.md)、[绑定JSON](../../docs/knowledge/acoustic-manifestations-20261009/comparison-bindings.json)与[差异](../../docs/knowledge/acoustic-manifestations-20261009/table2-record-differences.json)。当前步骤以[根目录计划](../../plan.md)及关联[表2专项计划](../../plan-table2.md)为准。新因果渲染/人工试听依后续冻结范围推进，不因记录审计完成而自动开始。
