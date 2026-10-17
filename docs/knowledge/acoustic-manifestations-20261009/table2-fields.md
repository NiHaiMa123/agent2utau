# 表2 schema 3：字段与读取规则

2026-10-10，2B。机器入口为[conditional-responses.json](conditional-responses.json)，每条记录新增`record_v3`；旧字段保持值相同。schema 3是记录结构修订，2C隔离/指标/结论复核尚未执行。不能把字段存在或来源SHA相同解释为实际输入、检测器或通用调参规律已确认。

| 字段 | 含义与读取规则 |
|---|---|
| record_version / record_kind | 3；response、observation、technical_audit分别读取，技术审计不作为效果样本 |
| comparison_id / comparisons | 主比较及附加比较；每个ID明确reference_variant、intervention_variant、direction、operation、listener_evidence。signed delta为后者减前者；绝对F0距离没有有符号方向 |
| variants | 逻辑版本、工程SHA、推理run、文件槽位、预测/最终输入/原始波形SHA、历史执行/复用、种子与speaker。所有newly_executed_in_2B=false |
| table1_refs | 具体PARAM与实体候选/导航CTRL分开；PARAM路径审查不等于剂量或听觉方向通过，实体关联不等于已检测到该表现 |
| condition_context | 旧条件指针、实际基底来自哪个版本、逐实验runtime、source unknown、时钟及缺口。registry未列组件保持unknown，不用公共47项补全TENC58项混合清单 |
| control_layers | 外部操作、直接输入、预测基底、人工增量、最终模型输入、旧隔离声明、允许下游响应与未隔离中介分开 |
| pitch_layers（干预记录） | native音符目标、acoustic条件pitch、vocoder目标F0、检测器测得F0分别标单位/时钟。vocoder输入相同不能推出PCM检测F0相同 |
| metric_bindings | 指向本记录原measured/state_differences的JSON Pointer、对应比较ID或单版本、操作、单位、窗口与帧数。未抄入的精确窗/质量阈值到绑定来源核对；没有来源时unknown，不复算补齐 |
| feedback_group_id | 全表table2_schema_revision.feedback_groups中的反馈来源与原话、比较音频SHA、元数据及共享关系；缺失设备、时间、盲测/任务协议均unknown |
| state_timeline | 历史执行时pending/未验收、后续反馈、现行总结独立；旧false字段不是后来用户没感知/拒绝的证明 |
| record_confirmation | schema_revised_with_explicit_gaps；2C尚未执行，不能标整轮记录确认完成 |

逻辑版本必须与文件槽位分开。RESP-003的C使用本轮`fresh/B_*`，其旧B使用上一轮SHFC的`fresh/B_*`；原`package.py`把本轮dynamics_B组装为C，`analyze.py`把本轮fresh/B映射为C。两份原脚本SHA来自2A已核对的封存manifest，见[迁移证明](table2-schema-migration.json)。本轮只读脚本，没有执行、加载数组或解码PCM。原A的condition.baseline_actual_state仍是A，不能冒充旧B。RESP-004的完整A工程已包含接受抱C，果所在乐句的原基底保持。

RESP-003主试听及邻音RMS为C-B；F0有A-B、A-C、B-C绝对距离，分别指向B-A、C-A、C-B的版本对。原名A_B表示版本对，不是有符号A减B。adjacent_frame_level_removed_mel_shape_RMS是各版本自身相邻帧形状变化量，不是C-B差值；新字段因此给三个variant_ids，不给伪造比较ID。

预测基底与人工增量使用模型特征单位；额外BREC -10经原变换给名义-1.2增量，不能写成最终状态-1.2或PCM -1.2dB。抱C原人工BREC曲线[-3,-2,-1,0]保留，叠加-10后的UI最低值由原设计给出为-13；不由新表重算逐帧曲线。最终值、裁剪和基底没有来源的版本继续unknown。SHFC允许完整variance预测响应，因此最终BREC/VOIC/TENC可随上下文变；不能据此声称人工多通道同时干预或找到唯一中介。

## 原指标的单位、窗与限制

以下是原字段的解释契约，不是新的测量方法验证。精确结果仍按原值存储；原报告/JSON及2A绑定见[来源审计](comparison-bindings.json)。

| 原字段族 | 量与单位 | 窗/帧、掩码与比较 |
|---|---|---|
| PCM_vowel_metrics / nucleus_RMS_change_db / phone_level_proxies / phones[].AB_level_change_db | RMS为PCM线性幅度；level_change_db为20log10(RMS后者/RMS前者)，不是感知响度；wave_delta_rms为PCM差波RMS | 原元音/phone interval_s或support_s；PCM采样窗，不拿mel帧数替代；B-A，RESP-003邻音C-B |
| short_window_energy | PCM窗口RMS比的dB聚合，原30/50ms及window_step_s保留；not_perceptual_loudness=true | min/median/max、core分别读取；core窗按原来源，缺少精确边界不猜补 |
| spectral_band_power_proxy / reported_2_to_5kHz / reported_30ms | 频带功率比或RMS比dB；reported字段是原报告舍入代理 | 频带边界按键；不是共振真值/主观响度，30ms代理不定位用户精确样本 |
| actual_dual_F0 / first_65ms_F0 / window_responses[].F0 | 原A/B median_Hz为Hz；abs_cents_p50/p95/max为绝对音分距离；repeat_f0_exact为历史重复声明 | 原comparable_frames/all_three_comparable_frames，65ms或明确interval_s；检测器时基与原质量掩码，精确阈值未列时unknown。不是模型输入MIDI |
| variance_prediction_response | breathiness_pred/voicing_pred/tension_pred为预测特征单位；changed_frames为帧数，max_abs_change为绝对变化 | 原整个乐句/支持外/元音分别读，不能把整句响应当局部输入泄漏；实际隔离待2C |
| input_delta_min/max | 最终模型输入增量，BREC特征单位；不是最终气声基底或PCM dB | 原完整输入数组声明范围；本轮不加载数组验证 |
| mel_response / mel_shape_AB_RMS | log-mel特征RMS及去电平形状代理；不是formant或改善真值 | 原frames；historical perceived_improvement=false保留，不能替代用户结果 |
| baseline_actual_state / state_differences | final_breathiness/voicing/tension为模型特征；pitch_MIDI为对应条件/目标F0转换摘要的MIDI；差值为第二条件减第一条件 | whole、core20_80、onset60ms、tail60ms及各n独立；原摘要不足以还原完整曲线/所有动作时钟 |
| no_full_scale_or_feature_clipping / repeat_* | 原文件/特征裁剪、确定性技术声明 | 无削波不等于没有听感破音；相同PCM重复不等于跨条件泛化 |

## 反馈和状态

RESP-001～004分别绑定四份反馈；RESP-005～010共享FB:BREC-cohort的一次“全部没区别。”及12份分开A/B音频SHA，不能算六次独立回报。SHFC正文“更实了，但是有破音的情况”和定位“开头”“抱的字头”分开保留，旧合并文本仍在user_feedback。RESP-003“可以”只支持该C局部使用，字头破音、咬字等细项与乐句/全曲验收保持unknown。

OBS-001“中间这个可以”限word247；原反馈accepted_clip.perceptual_label=unknown与原interpretation同时保留并注明角色，word295仍unknown。OBS-002的C可用标签来自RESP-003的C-B试听，C-A状态关联没有新增直接试听；不把它升级为C-A因果试验。反馈组6个不等于6个独立受试者，10干预仍是5设计。

## 版本迁移与构建

[JSON schema](table2-record-schema.json)约束新增扩展；[迁移清单](table2-schema-migration.json)给精确恢复规则。去除table2_schema_revision和14个record_v3，schema_version置2后应与冻结JSON深度相同；CSV去除4新列后旧单元格相同；旧Markdown主体原文保留。旧字节见[26份快照清单](history/pre-table2-2b-20261010/snapshot-manifest.json)。conditional-responses.csv原来只有10条干预，本轮维持原行范围并新增扩展JSON列；[完整结构CSV](table2-record-structure.csv)另列14条RESP/OBS/AUD，与JSON扩展一致，不把旧10行CSV冒称包含OBS/AUD。

F和2A审计针对冻结时版本，原产物不覆盖重写为schema3通过。其构建/写审计入口在2B冻结注册后拒绝运行，防止降级覆盖；原脚本字节已快照。现行构建与验证使用research/table2-confirmation/build_stage_2b.py和verify_stage_2b.py。表1实体/控制、response-coverage、旧来源索引不改，当前来源扩展索引使用2A comparison-bindings，不另假造原索引已完整。
