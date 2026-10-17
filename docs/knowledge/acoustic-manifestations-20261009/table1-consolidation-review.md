# 表1正式整合与引用迁移：阶段F

2026-10-10。**F为consolidated_with_explicit_gaps**：正式登记49个分层记录实体（24 ACO、15 EVT、9 PER、1 META），30组听感词及48导航组/352具体项，另保留复音/拍频1个开放候选。这是可追溯记录结构，全部measurement_validated仍false，不是完整检测器、通用调参规律或自然度验收。

现行[JSON总表](knowledge-table.json)、[实体CSV](atomic-manifestations.csv)、[组合词CSV](composite-descriptors.csv)、[控制导航CSV](openutau-controls.csv)、[上下文/任务字段](context-schema.json)与[ID迁移](id-migration.json)。原40文件按原字节存于[迁移前快照清单](history/pre-f-20261010/snapshot-manifest.json)，snapshot链接按原路径解释；A–E报告为当时证据，不覆盖现行状态。

## 迁移范围

- 31个旧描述ID有明确分层去向；增加周期shimmer/感知音高，复音/拍频保持开放，不强制变成第50个正式实体。旧含义存legacy字段/快照，旧S1来源与声学对象使用独立命名空间。
- 30组词使用DESC、48组用CTRL、源码摘要用CODE、项目证据用EVID、旧来源用SRC；CLAIM/DSRC/ESRC来源的原阅读层级保留，PARAM/MEAS/CASE ID保持。
- 14条RESP/OBS/AUD现在从实际atomic_ids读取，逐个旧ID保留候选去向。A旧提案误读atoms而生成14条空关联，本次公开纠正。展开后的引用仅结构翻译，不称各声学/感知对象均被测到。
- 第二层原数值、干预、状态、原话、报告/工程/音频SHA及runtime绑定精确保持；只迁移类型明确的引用并附legacy字段。没有重查波形、模型或新因果试验。

## E缺口如何处理

8组上下文/任务字段记录层级/重音、调律参照、装饰目标序列、参与/目标角色、多标签情绪、谐波/感知音高关系及取样范围。字段定义完成不代表历史材料已补齐，更不让E的8部分表达项自动变为通过。E42案例、34可记录/8部分、16标签行/0完整测量结论不变；16个正式实体未被该清单覆盖。

C的未读消费者/非默认分支/开放插件与本机缺失保持；D的真实F0/共振、pulse/声源分解、边界与响度/空间验证缺口保持；B摘要/范围级资料和30组多义映射仍不能升级为全部证实。

## 公开纠错

E所称表2派生文字乱码为工具输出编码误判。原JSON严格UTF-8解析，SHA与基线一致；1174字符串无U+FFFD/Latin1异常，10条原话与可读报告/CSV逐项对应。没有把正确原文做猜测性转码，见[纠错与报告绑定](source-quality-correction.json)。E冻结记录原字节保留，当前入口以此纠错为准。U17冻结word282误写→word295勘误仍有效，听感unknown不变。

## 重建与验收边界

现行文件由research/table1-confirmation/build_stage_f.py从明确SHA绑定的迁移前资料/A–E产物生成；A–E构建器在正式迁移后拒绝覆盖。执行审计分别核对原历史基线、当前CSV/JSON、ID/来源、第二层去除迁移字段后的原记录等式及67份保护输入；不通过更新哈希绕过历史证据。

表1本轮按当前固定范围收口并交付缺口清单，不以未知迫使合成或试听。后续表2专项计划尚未执行；先做已授权记录审计，新的因果设计/人工试听按其冻结步骤开展。歌曲、音频、Skill、模型/安装不变，远端CI仍仅手动。[当前计划](../../../plan.md)、[执行审计](table1-execution-audit.json)。
