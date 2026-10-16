# 表2 2C：逐行记录确认

2026-10-10。状态record_review_complete_with_explicit_gaps。14条记录完成来源、比较、输入声明、历史指标与反馈结论复核。这里的“确认”限列明记录/数学范围，缺口继续公开；未确认通用响应规律。

本轮读取60份输入/预测NPZ，129份明确SHA绑定的实际读取文件保持；823处原指标标量字段与来源匹配，20份A/目标最终输入另由独立验证器重建检查。逐记录列出36项限定确认、24项部分确认及56项unknown，均为声明范围，不是36个新实验/检测器或独立反馈。原2A的52份来源、67保护输入及26更新前快照另核对。

[机器报告](table2-record-confirmation.json)含已确认/部分/未知逐项清单，[CSV](table2-record-confirmation.csv)同14行；[本轮审计](table2-stage-2c-audit.json)绑定检查和本地日志。[更新前快照](history/pre-table2-2c-20261010/snapshot-manifest.json)保存26份原字节和40份输入/预测数组SHA（不复制数组）。

本轮只读核查原生输入JSON和封存fresh输入/预测NPZ，包括明确manifest绑定的A-repeat。独立检查直接通道/variance条件、支撑、SHFC浮点运算、人工增量与clip(pred+delta)、fresh通道/预测变化、输入/预测重复。没有运行原生引擎/模型、重新解码PCM、读取mel/检测器数组或生成新F0；原波形重复、DYN/混音/PCM代理仍是历史检查，不伪称本轮重验波形。speaker tensor精确保持不等于重新验证当前embedding/安装。

| 记录 | 输入/比较复核 | 用户或使用边界 |
|---|---|---|
| RESP-001 | RESP-001:B-A；native_and_fresh_input_math_rechecked | no_perceived_difference |
| RESP-002 | RESP-002:B-A；native_and_fresh_input_math_rechecked | benefit_with_side_effect |
| RESP-003 | RESP-003:C-B；native_and_fresh_input_math_rechecked | local_accepted |
| RESP-004 | RESP-004:B-A；native_and_fresh_input_math_rechecked | no_benefit_with_side_effect |
| RESP-005 | RESP-005:B-A；native_and_fresh_input_math_rechecked | no_perceived_difference |
| RESP-006 | RESP-006:B-A；native_and_fresh_input_math_rechecked | no_perceived_difference |
| RESP-007 | RESP-007:B-A；native_and_fresh_input_math_rechecked | no_perceived_difference |
| RESP-008 | RESP-008:B-A；native_and_fresh_input_math_rechecked | no_perceived_difference |
| RESP-009 | RESP-009:B-A；native_and_fresh_input_math_rechecked | no_perceived_difference |
| RESP-010 | RESP-010:B-A；native_and_fresh_input_math_rechecked | no_perceived_difference |
| OBS-001 | OBS-001:word247-word112；stored_state_summary_and_pair_arithmetic_rechecked; no_independent_intervention | observation；非独立听觉因果比较 |
| OBS-002 | OBS-002:accepted_C-original_A；stored_state_summary_and_pair_arithmetic_rechecked; no_independent_intervention | observation；非独立听觉因果比较 |
| AUD-001 | AUD-001:HFA_observation-native_g_uo；bound_historical_identity_or_rejection_correction_record | technical_audit；非独立听觉因果比较 |
| AUD-002 | AUD-002:SHFC_400c_intended-SHFC_4c_rejected；bound_historical_identity_or_rejection_correction_record | technical_audit；非独立听觉因果比较 |

抱C：本轮fresh/B槽位为逻辑C，原A→C输入检查与主C-B检查分开；旧B未重新声码器执行。C-B仅12帧条件采样改变，平台/退出保持；完整预测可改变平台/邻字，不能独立归因“提前”与“拉长”。用户“可以”只支持3:04抱C局部使用，细分破音/咬字、乐句/全曲仍unknown。

果：完整A来自接受抱C；uo RMS +0.090115dB与用户响度下降反馈并存。原报告-4.200dB短窗及-4.032dB频带是舍入代理，未作为用户精确位置或主观响度真值。保留用户“好像”的不确定表达，不采用果SHFC B，也不否定抱C局部接受。

BREC：六个_grid5有效版本只改变breathiness最终输入，fresh预测相同；额外-10、基底曲线和最终状态分开，模型增量不写成PCM dB。六条仍共一份“全部没区别。”和12音频SHA，不用未报告副作用补造“全无副作用”。阴性反馈限定当前剂量/条件，不将通道整体判无效。

TENC取消已有+14未获可感知差别支持；SHFC -400c“更实”伴抱字头破音，不采用B。无满幅削波只排除文件满幅，破音种类/生理寄存器/共振峰与唯一中介unknown。固定vocoder F0与原实测40–45c局部检测差不矛盾。

OBS001是word247与word112跨上下文关联，word295仍unknown；OBS002为接受C与原A状态关联，其局部可用标签来自C-B，不伪造C-A听觉比较。AUD001合法g/uo映射与近似时钟不等于自然时长/咬字通过；AUD002拒绝4c/1tick草稿，保留400c/5tick有效版本，不能算新增听觉实验。

历史声学数值按原JSON逐叶匹配并检查RMS比的dB方向、明确窗与帧数；高F0共振峰、破音分类、检测器估计真值未验证。未重新测量PCM/mel/F0，没有用报告代理或原perceived_improvement=false覆盖后来反馈。缺失反馈时间/设备/盲测、当前runtime、动作上下文、唯一机制、乐句/全曲/留出与跨曲状态都保留unknown。

现行JSON/两份CSV/Markdown同步添加本轮确认引用，原2B扩展和全部更旧字段均可精确恢复；原报告、工程、Skill、旧run、F/2A/2B审计不重写。本轮属于2A–2C记录确认收口，下一步2D仅梳理缺口与冻结有限设计；新因果渲染/人工试听仍在2E并依实际授权范围进入。

本轮本地验证见执行审计：88项pytest和工作树门禁通过，音频载荷0、三作者工程/五ZIP成员、102处Skill链接；生成产物重复构建、既有冻结拒绝覆盖及2个2B写入口guard通过。使用本批新ignored run和TEMP/TMP，原运行不写入。两次研究读取器误用字段名的KeyError在任何现行产物写出前被拒绝，修正为实际known_labels[].metrics后通过；原失败日志保留，未修改原报告或数值。
