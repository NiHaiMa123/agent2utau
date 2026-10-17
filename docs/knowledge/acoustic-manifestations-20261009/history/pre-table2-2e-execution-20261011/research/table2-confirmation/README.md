# 表2记录确认与有限协议研究

当前2E历史实际输入/完整时钟、5tick采样重建及静态接入核查已完成，整体2E仍未完成。见[输入与静态核查](../../docs/knowledge/acoustic-manifestations-20261009/table2-stage-2e-native-check.md)：41实际音素/421与594帧，抱整数曲线及两路径采样与旧C精确，只的33帧为计划/IL重建；六组两阶段speaker、47资源SHA及三模型声明通过。55研究契约测试通过，无新原生导出/推理/音频/反馈。下一步有限执行前置项及明确授权的新批次；通过技术检查后人工试听。以下保留此前阶段范围。

当前2E研究接口准备已完成，整体2E未完成。[准备报告](../../docs/knowledge/acoustic-manifestations-20261009/table2-stage-2e-preparation.md)、[JSON](../../docs/knowledge/acoustic-manifestations-20261009/table2-stage-2e-preparation.json)及[审计](../../docs/knowledge/acoustic-manifestations-20261009/table2-stage-2e-prep-audit.json)为当前续项。A/S/D/P组装、独立检查器及有限批/惰性后端代码通过40项合成契约测试；47当前资源SHA精确，未运行真实模型、原生导出或音频。下一步实际native身份/5tick采样和后端接入核查，人工试听仍待新对照通过技术检查；原2D协议/审计及2C记录保持。


`shfc_path_adapter.py`组装有限研究路径，`shfc_path_checks.py`独立重建/重复/新裁剪门禁，`shfc_path_runner.py`仅接受冻结条件和predictor回调；不从历史预测文件合成。`shfc_path_backend.py`惰性ONNX接入代码未构造真实session，只有未来显式调用才在新run创建噪声适配器。无自动入口、DYN/交付编码或参数搜索。

`build_stage_2e_prep.py`/`verify_stage_2e_prep.py`已guard，保留原准备报告/审计。当前入口为`build_stage_2e_native.py`与`verify_stage_2e_native.py`；原生静态检查输出一次写入新run，拒绝覆盖。

`freeze_stage_2e_prep.py`先冻结24文档/源码并绑定79生产/Skill/工程文件；`check_stage_2e_runtime.py`以明确登记表映射核对实际安装，仅记文件SHA。测试在tests/contracts，新临时目录在runs/test-results。2D验证写入口已guard，旧源码快照及封存设计不改。以下保留各阶段完成时范围。

## 2D阶段历史说明

2D完成时缺口审查及有限协议已冻结。[2D报告](../../docs/knowledge/acoustic-manifestations-20261009/table2-protocol-review.md)、[协议](../../docs/knowledge/acoustic-manifestations-20261009/validation-protocols/shfc-path-separation-v1.md)为当前续项：352 PARAM/49正式表现及1开放候选，单个SHFC路径分离设计、2条件/4路径/各两次，计划16套新波形，实际0套。D/P需要新研究接口，先实现独立检查器，不写生产原生工程。人工试听仍须在新对照技术核查通过后进行。2C文档/原审计原字节保持；2C写入口已guard，快照保留原脚本，以下各阶段叙述保留当时范围。


`freeze_stage_2d.py`保存23份更新前文档/脚本；`stage_2d_design.py`声明有限设计，`build_stage_2d.py`生成6份覆盖/协议文件，首次`--seal`绑定协议及设计/构建源码SHA。`verify_stage_2d.py`独立检查352具体ID、50表现/测量引用、2×2路径/16套预算、3个错误设计拒绝、67保护输入与旧2C不变。封存后不能修改协议或设计/构建源码，必须显式新版本。

```powershell
.venv/Scripts/python.exe research/table2-confirmation/build_stage_2d.py
.venv/Scripts/python.exe research/table2-confirmation/verify_stage_2d.py --local-checks
```

## 2C阶段历史说明

2C完成时2A–2C记录确认已收口，状态record_review_complete_with_explicit_gaps；[2C逐行报告](../../docs/knowledge/acoustic-manifestations-20261009/table2-record-confirmation.md)、[JSON](../../docs/knowledge/acoustic-manifestations-20261009/table2-record-confirmation.json)和[审计](../../docs/knowledge/acoustic-manifestations-20261009/table2-stage-2c-audit.json)为当前入口。以下2B/2A说明保留各自阶段时态，原审计输出不刷新。

`freeze_stage_2c.py`冻结26份文档/脚本并核对40份直接注册的输入/预测数组SHA，不复制数组。`stage_2c_inputs.py`独立检查原生/variance支撑、SHFC浮点变换、人工增量、native/fresh最终算术和重复输入/预测；`build_stage_2c.py`读取全部明确manifest绑定的60份输入/预测NPZ（含20份A-repeat）与JSON，129读取文件前后SHA保持。823原指标标量字段回到原结果JSON/报告核对，RMS比dB及观察配对中位数差检查；新模型/原生执行、PCM/mel/检测器数组读取或声学复测均0。`verify_stage_2c.py`再独立重建20版本的最终三通道、检查精确恢复、来源/反馈/CSV/Markdown与已确认/部分/unknown范围；3个混杂错误样例拒绝，2B写入口拒绝降级覆盖。

```powershell
.venv/Scripts/python.exe research/table2-confirmation/build_stage_2c.py --run runs/research/table2-2c-record-confirmation-20261010
.venv/Scripts/python.exe research/table2-confirmation/verify_stage_2c.py --run runs/research/table2-2c-record-confirmation-20261010 --local-checks
```

schema版本仍3，只更新record_confirmation、增加confirmation_ref及顶层确认引用；移除新增确认字段并还原2B状态后应精确等于更新前JSON，CSV其余单元格相同，旧Markdown主体保留。范围迁移见[迁移清单](../../docs/knowledge/acoustic-manifestations-20261009/table2-confirmation-migration.json)。36项限定确认、24部分及56未知是每条声明范围统计，不能当新增样本。当前测量协议的measurement_validated仍全部false，通用规律0；下一步2D梳理缺口与冻结有限设计，新因果试听在2E，不在记录收口时自动开始。

## 2B阶段历史说明

2B当时完成schema 3修订，2C尚未执行。[2B报告](../../docs/knowledge/acoustic-manifestations-20261009/table2-schema-review.md)、[字段说明](../../docs/knowledge/acoustic-manifestations-20261009/table2-fields.md)与[审计](../../docs/knowledge/acoustic-manifestations-20261009/table2-stage-2b-audit.json)为2B冻结时入口；现在2B/2C写入口已guard，现行使用2D构建/验证。以下2A说明保留当时范围。

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
