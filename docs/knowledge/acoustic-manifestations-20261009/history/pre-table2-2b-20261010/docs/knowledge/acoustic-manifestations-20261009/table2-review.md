# 表2来源与版本绑定审计：2A

2026-10-10。2A为source_binding_audit_complete_with_explicit_gaps。冻结F后的17份现行文档，逐条审计10干预/2关联/2技术记录。只确认来源/版本/文件绑定，2B字段修订和2C隔离/指标结论复核尚未执行。未生成或解码音频、运行模型、改歌曲/Skill、申请新试听或启用远端CI。既有音频/数组只读取字节计算SHA，不作新的声学测量。

[完整绑定JSON](comparison-bindings.json)、[CSV](comparison-bindings.csv)、[差异JSON](table2-record-differences.json)、[差异CSV](table2-record-differences.csv)和[原字节快照清单](history/pre-table2-2a-20261010/snapshot-manifest.json)。原表2CSV/JSON/Markdown、F产物与原报告未改；原SHA和此版SHA分开保存。当前执行状态以[根目录计划](../../../plan.md)为准，F产物里的表2未执行为F完成时状态。

## 已核对的范围

原36来源均保持SHA，补列实际反馈/音素/接受与运行清单来源。五份封存manifest共896条文件声明逐一字节核对；67份保护输入保持。完整SHA检查和第二次无缓存复核在本批ignored run，公开文件只含有限路径/绑定摘要，不复制数组/波形。SHA一致不代表重新推理、重新解码PCM、复测F0或人工重听。

| 记录 | 比较/来源角色 | 核对结果与边界 |
|---|---|---|
| RESP-001 | B-A | 取消既有+14 TENC，不是新增任意负值；用户实际反馈绑定混音A/B。执行时pending与后续没区别分开。 |
| RESP-002 | B-A | 两条原话合并有显式标志；保留早期“开头”及最终“抱的字头”，精确伪影采样点unknown。 |
| RESP-003 | C-B | 听觉/能量主比较为C-B；F0保留明确A-B/A-C参照，不能混成同一比较。B波形明确复用，fresh/B状态文件不等于本轮新B声码器波形。 |
| RESP-004 | B-A | 完整A是已接受抱C的副本；1:27条件与原v02相同不代表完整工程就是v02。用户响度下降位置unknown。 |
| RESP-005 | B-A | 使用cohort显式A_path/B_path和relative_dir的_grid5版本；1-tick草稿/缓存不作为有效输入。六行共一组“全部没区别。”回报，不增加独立试验或补细分副作用标签。 |
| RESP-006 | B-A | 使用cohort显式A_path/B_path和relative_dir的_grid5版本；1-tick草稿/缓存不作为有效输入。六行共一组“全部没区别。”回报，不增加独立试验或补细分副作用标签。 |
| RESP-007 | B-A | 使用cohort显式A_path/B_path和relative_dir的_grid5版本；1-tick草稿/缓存不作为有效输入。六行共一组“全部没区别。”回报，不增加独立试验或补细分副作用标签。 |
| RESP-008 | B-A | 使用cohort显式A_path/B_path和relative_dir的_grid5版本；1-tick草稿/缓存不作为有效输入。六行共一组“全部没区别。”回报，不增加独立试验或补细分副作用标签。 |
| RESP-009 | B-A | 使用cohort显式A_path/B_path和relative_dir的_grid5版本；1-tick草稿/缓存不作为有效输入。六行共一组“全部没区别。”回报，不增加独立试验或补细分副作用标签。 |
| RESP-010 | B-A | 使用cohort显式A_path/B_path和relative_dir的_grid5版本；1-tick草稿/缓存不作为有效输入。六行共一组“全部没区别。”回报，不增加独立试验或补细分副作用标签。 |
| OBS-001 | 3:17可用果 minus 1:27问题果 | 同uo/E4跨上下文观察；3:17局部可以与3:44 word295 unknown分别保存。实际新成声state与已拒绝cached_result草稿分开。 |
| OBS-002 | 已接受抱C minus 原问题抱 | 已接受抱C减原问题A，属于SHFC完整干预的下游关联；不同于RESP-003的C-B，也不是独立VOIC/TENC/BREC因果试验。 |
| AUD-001 | not_an_effect_comparison | 词表/语言/原生时钟与HFA观测核查；不含新声音干预或发音自然度标签。MP3/HFA、字典及当前安装仅保留历史绑定，本轮不重新打开外部资源。 |
| AUD-002 | not_an_effect_comparison | 组合两次技术拒绝/修正：SHFC -4c→原定-400c、BREC 1tick→5tick。不是第六个听觉实验，也不将草稿缓存算成有效新成声。 |

## 版本与原话差异

- T2A:F01：C-B听觉/能量与A-C F0、原A基底并存；JSON已有说明，但未统一拆成comparison_id/版本字段。 2B拆分比较与状态来源；2A不改旧值，不补B基底。
- T2A:F02：有效工程/原生输入/新预测在cohort显式_grid5目录；不带该后缀的旧目录含拒绝草稿。 2A绑定具体有效路径；2B将版本/失败角色作为字段，保留旧manifest。
- T2A:F03：共享47项runtime来自BREC冻结清单。TENC的frozen_dependencies是不同范围；不能套用相同runtime_group视为逐实验运行证明。 按五设计关联各自历史清单，逐项比较共有/新增/不同值；当前模型/安装未重查，未运行。
- T2A:F04：原36来源未单独列TENC反馈、SHFC字头反馈及果接受/音素审计JSON；原报告有引用，2A补明确来源绑定。 补索引，不改原报告/原36来源审计或既有反馈。
- T2A:F05：派生user_feedback.verbatim省略原反馈JSON末尾中文句号；文字内容一致，原“全部没区别。”精确保留在2A反馈来源字段。 2B保留原文与展示摘要各自来源；2A不静默修改冻结的派生JSON。
- T2A:F06：历史反馈未完整记录精确提交时间、设备/监听、盲法及逐项任务；日期目录或文件mtime不能补成这些事实。 保持unknown；2C限定已有听觉结论，新的冻结试听另外记录。
- T2A:F07：2A预冻结附加候选误用native_isolation.json文件名，该路径不存在；实际相关记录为封存manifest内preservation_check.json及fresh核查。 冻结原错误条目不改；补真实来源与locator勘误。这不是原实验文件丢失或隔离失败证据。

## 逐实验runtime范围

| 设计 | 历史清单项数 | 与共享清单相同 | 共有但值不同 | 仅本设计 | 共享中未在本设计列出 |
|---|---:|---:|---:|---:|---:|
| TENC | 58 | 6 | 0 | 52 | 41 |
| SHFC | 47 | 47 | 0 | 0 | 0 |
| ONSET | 47 | 47 | 0 | 0 | 0 |
| GUO | 47 | 47 | 0 | 0 | 0 |
| BREC | 47 | 47 | 0 | 0 | 0 |

上述清单SHA/交集只确认历史记录。TENC包含工程/Skill/当时源码等混合依赖，范围与其余47项不同；共享组名不能抹去诊断桥/资源范围差异。本轮没有重新哈希当前外部模型/安装或执行设备，因此不将缺列补成相同、不将旧源码路径当作现行执行证明。

旧pending/自然度未验收标志保留原时间角色，后续用户反馈保持优先范围；六条件BREC共一次汇总回报。抱C局部可用、果SHFC否决、TENC与BREC无感知改善结论保持；word295、313未知字、细分副作用与整曲/泛化状态不升级。

下一步2B修订比较/版本/基底/下游与反馈状态字段，再由2C逐项复核隔离声明、指标来源及结论范围。新的因果试听须经2D冻结且进入2E执行范围，本轮不自动开展。[专项计划](../../../plan-table2.md)、[研究构建说明](../../../research/table2-confirmation/README.md)。
