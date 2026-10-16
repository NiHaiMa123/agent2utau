# 表1确认研究

2026-10-10：A–F在固定范围内完成，确认缺口保留。现行构建入口为`build_stage_f.py`，从明确SHA绑定的40份迁移前资料及A–E产物生成49个分层记录实体/1开放候选、30 DESC、48 CTRL/352 PARAM、8组上下文/任务字段，并同步14条RESP/OBS/AUD引用。

```powershell
.venv/Scripts/python.exe research/table1-confirmation/build_stage_f.py
.venv/Scripts/python.exe research/table1-confirmation/build_audit.py --verification-run <本次runs/research目录>
```

`freeze_stage_f.py`已执行一次；快照清单及`stage_f_baseline_binding.json`绑定原路径/原字节SHA，拒绝再次冻结覆盖。`frozen_inputs.py`只按显式登记解析历史版本，不搜索缓存或改变旧哈希。审计分别核对旧基线、现行产物、CSV/JSON、命名空间、候选引用与原记录等式：将第二层新增迁移字段去掉并还原legacy引用后，整个JSON必须与迁移前精确相等。CTX字段完成定义不代表E的8部分表达项历史信息补齐，全部measurement_validated仍false。

A旧提案误读atoms字段导致14条空关联，F改从实际atomic_ids读取；展开后的实体仅为结构候选。E所称表2乱码已证实为工具显示误判，原UTF-8中文/反馈正确，未做转码；原审查/冻结字节保留，另有可追溯纠错。U17 word295勘误仍有效。见[正式整合报告](../../docs/knowledge/acoustic-manifestations-20261009/table1-consolidation-review.md)。

以下A–E命令说明历史构建过程；正式迁移后这些构建器在入口拒绝覆盖，不能作为现行重建命令。现行F生成器与历史审查报告的状态分开。

`build_stage_a.py`保存Codex对原31行的显式结构审查决定，生成[阶段A报告](../../docs/knowledge/acoustic-manifestations-20261009/table1-review.md)、CSV/JSON和候选ID迁移。它不读取音频、作者曲线或历史制作方案，不执行模型、分类器或歌曲修复，也不是生产模块。

从仓库根运行：

```powershell
.venv/Scripts/python.exe research/table1-confirmation/build_stage_a.py
```

A当时构建前核对六份原表/第二层基线SHA；不匹配就拒绝重建，需人工审查版本变化。CSV为UTF-8 BOM。当时原清单与第二层保持原字节，F迁移前已保存快照；不要通过修改哈希绕过新版本审查。

`build_audit.py`检查CSV/JSON一致性、候选ID引用、文档链接和`protected-inputs.json`里的67份显式保护文件。后者是已有Skill/作者原件/发布工程及报告/封存绑定的SHA摘要，不含音频或运行数组。封存run在其它机器不可用时明确记unavailable，不声称那些证据已验证。仓库门禁另运行`tools/repository/check_repository.py --worktree`。

`build_stage_b.py`生成30条已核对的文献说法及31行定义/30组听感词审查。显式审查数据在`stage_b_review_data.py`；源码控制路径未查的、测量未验证的、资料不足的都独立记录。组合词两种解释及假设反例是工程提案，不是来源验证过的中文词映射或新音频标签，也不能作E独立覆盖样本。命令格式与A相同，只替换脚本名；不抓取网站或假定全文已读取，增加说法须先实际核对来源。

`build_stage_c.py`合并首批184、第二批136及`stage_c_editor_review.py`的32项，共352条，前320个ID保持；另生成31节点、23项本机矩阵及103偏好字段/8嵌套属性审查。必须传旧快照、两批同提交新快照、离线metadata、安装与声库。原44+25源码重查，编辑批21份中4份重复SHA一致/17份新增，共86份唯一来源及六资源绑定。配置/USTX只作数据，参数区分默认、发布声明、clip和本机证据；固定范围审查完成不等于全部插件/本机非默认执行通过。

```powershell
.venv/Scripts/python.exe research/table1-confirmation/build_stage_c.py --upstream runs/acoustic_inventory_20261009/upstream --additional-upstream <第二批run/upstream> --editor-upstream <编辑批run/upstream> --local-metadata <离线PE观测目录> --openutau <当前安装目录> --singer YousaV1.65c
.venv/Scripts/python.exe research/table1-confirmation/build_audit.py
```

snapshot显式给出，每文件匹配原审计、`stage_c_source_bindings.json`或`stage_c_editor_source_bindings.json`固定SHA；重复来源先核对同SHA再复用，不覆盖旧snapshot。builder不下载/替换，安装目录不写入公开表；缺资源重建拒绝，不能绕过校验。偏好CSV/JSON分类是显式研究决定，词法引用只表明固定范围内出现，不等于全部consumer已读取/执行。窗口状态和工具8属性另列；未读live值、未选插件及声音效果保留unknown。

`metadata-reader/`是研究用离线PEReader，不加载被检查的DLL，不解析/执行依赖、不初始化OpenUtau、不读取live偏好/模型/音频。使用.NET 10 SDK框架内置System.Reflection.Metadata，无新增第三方包。构建产物全部放新ignored `runs/build`；运行输出放新研究run：

```powershell
dotnet build research/table1-confirmation/metadata-reader/MetadataReader.csproj -p:BaseIntermediateOutputPath=<新构建绝对路径/obj/> -p:OutputPath=<新构建绝对路径/bin/>
dotnet <新构建路径/bin/MetadataReader.dll> <显式安装/OpenUtau.Core.dll> <新研究run/observations/core-metadata.json>
dotnet <新构建路径/bin/MetadataReader.dll> <显式安装/OpenUtau.dll> <新研究run/observations/app-metadata.json>
```

`stage_c_local_review.py`核对metadata与实际DLL SHA，断言精确成员缺失/选定IL调用及常量，提取方法token与偏移。它保存成员存在、实际读取路径、未执行/未听的独立状态；不得把未读分支升级为验证通过。本机graph/masked缺失，FX独立模块开关/WrapLive缺失；导出路径和pan公式静态存在。首批按声明推定的MixFxApplyOnExportMixdown导出开关说法已按出口固定true纠正。完整raw metadata/失败重试说明留ignored run，docs仅保留有限证据摘要。

`build_audit.py --verification-run <本次runs/research目录>`读取显式pytest/worktree日志；若存在retry日志则保留首轮并核查retry，否则核查首轮。上一批临时环境失败/重试与PE Infinity序列化失败记录仍保留；新批使用新workspace TEMP/TMP及basetemp，不凭旧日志宣布新检查通过。控制/偏好CSV一致、前320身份、节点/来源/本机绑定、67保护输入和CI仅手动均在审计内。

`stage_d_protocol_data.py`保存50条显式协议，`build_stage_d.py`绑定A47候选实体、B遗留3项与原31行，核对12份本机源码/研究验证器SHA并生成[协议报告](../../docs/knowledge/acoustic-manifestations-20261009/table1-measurement-review.md)、CSV/JSON及组件来源。窗口/算法候选、现有实现、数学组件验证、真实音频准确率分别记录；不运行模型或迁移ID。

```powershell
.venv/Scripts/python.exe research/table1-confirmation/verify_stage_d_arrays.py --out <新runs/research目录/observations/array-checks.json>
.venv/Scripts/python.exe research/table1-confirmation/build_stage_d.py --array-checks <显式新run/observations/array-checks.json>
```

数组验证器不读写音频，拒绝覆盖既有输出。10组已知值只检验单位、趋势/周期曲线、掩码、log-mel、tempo、forward RMS窗、调制代数、clip/seam及mono关系；不是50个完整检测器验证。初次反相相关精确断言失败后声明1e-12容差，失败与重试在新run保留。复现前核对`stage_d_source_bindings.json`，生产源码变更不能绕过SHA拒绝；审计核对所有协议/来源/原身份、CSV、行号与观测记录SHA。

`stage_e_checklist_data.py`的42项问题没有候选维度/MEAS映射；`freeze_stage_e.py`先核对作者原件/原报告与存储的证据JSON，把有限note结构、输入SHA和清单写入docs及新run checkpoint。它拒绝既有冻结/映射覆盖；原42项分母、36主映射/6过程复查分区保持，已有样本不称音频留出。源码已有A–D上下文，复查只是一种过程分区。

```powershell
.venv/Scripts/python.exe research/table1-confirmation/freeze_stage_e.py --run <新runs/research目录>
.venv/Scripts/python.exe research/table1-confirmation/build_stage_e.py --phase main --run <该目录>
.venv/Scripts/python.exe research/table1-confirmation/build_stage_e.py --phase final --run <该目录>
```

`stage_e_mapping_data.py`保存36项主映射，`stage_e_recheck_data.py`保存主checkpoint后写的6项复查。final当时核对冻结与主映射SHA、不修改主映射，生成[覆盖报告](../../docs/knowledge/acoustic-manifestations-20261009/table1-coverage-review.md)、CSV/JSON及未覆盖/取样轴。不能重跑freeze改变分母；U17的word编号错误另写勘误而不改冻结原字节。E当时的乱码判断由F纠正为工具显示误判，原中文正确；数据来源和实际音频验证分开，已有交付SHA引用不等于本轮重查波形。

A–F整合完成并保留具体确认缺口。E有34项限定结构可记录、8部分表达、16已有标签行；全部能力执行/真实测量与普遍描述完整性仍未确认。下一步为表2的2A记录审计，尚未执行。C/D不能代替人工试听，E回核已有反馈，新因果试听按后续表2冻结设计。迁移前文档字节保存在docs/knowledge的history，日志/运行快照在ignored runs；旧run不覆写，状态以[根目录计划](../../plan.md)为准。
