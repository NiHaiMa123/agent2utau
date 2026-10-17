# 表2 2B：记录结构和版本迁移

2026-10-10。状态`schema_revised_with_explicit_gaps`，2C尚未执行。本轮将14条原记录迁移到schema 3，新增17个明确比较、6个共享反馈组及逐版本来源。没有新合成、声学复测、试听、当前模型/安装验证、歌曲或Skill修改。

26份现行文档/历史构建入口先按原字节冻结。现行JSON每条新增record_v3，旧数值、状态、反馈、工程/音频SHA及表1类型引用保持。CSV原10干预行保留旧列并加4列，另有[完整14行结构CSV](table2-record-structure.csv)；Markdown保留完整旧主体，顶部给当前结构。恢复规则与快照SHA明确，旧F及2A审计保持其历史版本范围。

| 修订 | 结果与边界 |
|---|---|
| 比较对象 | 10干预主比较，抱C附加B-A/C-A参照，2观察比较，3技术比较，共17；绝对F0距离与signed delta分开 |
| 抱C版本 | 旧B复用；本轮fresh/B槽位映射新C，package.py/analyze.py原SHA绑定；原A实际基底不作为B状态 |
| 果版本 | 完整A/B保留接受抱C；目标果原基底独立，不写整项目等同v02 |
| BREC有效版本 | 六条件固定_grid5历史来源；人工额外剂量、原曲线/预测、最终输入与PCM代理分层；不重算新状态 |
| 推理与runtime | 历史fresh、旧波形复用、只读关联、技术拒绝分别声明；TENC58混合与其它47项逐设计范围保留，当前本机执行unknown |
| 反馈 | 4单次反馈+1六条件共享组+1中间果标签组；精确原话、SHFC两次定位、音频SHA、时间/设备/盲测unknown、局部范围保留 |
| 时态 | 原listening_pending/naturalness_accepted以及measured内false仍为执行时声明，后续反馈/现行汇总独立；不倒写旧状态 |
| 观察/审计 | OBS002 C-A状态关联借C-B标签，非C-A试听；OBS001旧unknown角色与word247局部解释并存；两个技术审计不新增听觉实验 |
| 表1 | TENC/SHFC/BREC绑定具体PARAM:C13.01/C14.01/C12.01；观察状态通道另列VOIC；技术审计列音素/语言/offset及单位范围/量化的具体字段引用。实体仍结构候选，不冒充整个导航组参数或听觉效果均已验证 |

字段、单位/窗口与unknown读取规则见[字段说明](table2-fields.md)，机器扩展见[JSON schema](table2-record-schema.json)，来源仍见[2A绑定](comparison-bindings.json)。[迁移](table2-schema-migration.json)说明精确恢复与文件标签证明；[本轮审计](table2-stage-2b-audit.json)记录独立检查和本地门禁结果。

尚缺精确反馈时间/设备/任务/盲测信息、部分版本完整可读基底摘要、动作/邻字条件、检测器掩码阈值、唯一中介与留出/跨曲验证；均未猜补。指标复算、隔离声明复核与逐行结论确认属于2C；2D冻结后才进入2E新因果渲染与人工试听。本轮结构修订不宣布通用响应规律或完整记录确认通过。

本轮本地验证：88项pytest通过，工作树门禁通过（音频载荷0、三作者工程/五ZIP成员、102处Skill链接）。独立结构检查、旧JSON精确恢复、CSV/Markdown一致、26快照/52来源元数据/67保护输入SHA及4历史写入口guard通过。生成产物重复构建与冻结拒绝覆盖检查见本轮审计；测试/日志使用新ignored run与TEMP/TMP，原实验日志和manifest不改。schema检查限实际声明关键词及错误样例拒绝，未安装外部标准引擎，不扩称完整标准兼容性验证。
