# 制作前读取表1与表2

表1规定记录对象、参数机制和unknown边界；表2提供绑定条件、干预、技术响应与后续试听证据。Skill负责方法，Agent负责当前条件判断和参数设计。此入口不改Skill、不按表自动挑配比，也不将局部成功升级为通用规则。

先按当前问题检查相关系列的正例、阴性、副作用、后续更正和接受范围，保存实际检索来源/ID、条件匹配与设计后果；详细方法见[Skill设计前知识接入](../../skills/singing-expression-editor/references/knowledge-before-design.md)。来源门禁只检查所选记录，不能发现所有漏选经验。不读历史制作工程/曲线/音频/数组时，仍按用户范围使用允许的公开方法与反馈结论；不搬旧剂量，受限时用显式目录隔离载荷。没有相应证据保留unknown，继续有边界的候选制作，不自动重启大规模研究。

先调用显式检索入口：

```powershell
agent2utau knowledge-context --entities PER:S1 EVT:L2 --parameters PARAM:C11.01 --responses RESP:LASTPAGE-OWN-CONTROL-NEUTRAL-01 --out runs/production/new/design/knowledge_context.json
```

入口读取[当前来源目录](../knowledge/acoustic-manifestations-20261009/active-knowledge-sources.json)。新增响应/反馈应先追加不可覆盖的报告，再更新来源目录的response_packets或新索引引用。来源目录快照进入context；来源表、实际记录与反馈文件SHA进入bindings，旧接入记录保持当时版本。检索按Agent指定ID，相关条件仍由Agent确认。没有可用对照时，responses留空并写absence-reason，保留外推/未知。

制作计划schema2新增knowledge_context：path、sha256、decisions。每个取回ID都有一项decision（use/reject/extrapolate/keep_unknown）、reason、condition_match、limitations。不能声称检索或技术门禁本身证明音乐判断正确、跨曲适用或measurement_validated。

compile-functions在写输出目录和调用原生之前检查包SHA、源文件SHA、原记录字段等式及逐条决策覆盖；缺失、不完整或过期即失败。旧schema1必须显式迁移，旧封存计划/产物保持原字节。研究runner使用同一check_plan_knowledge门禁，在执行前保存knowledge_receipt；它不把研究作者数组接入生产函数计划。

计划中选择有限动作，编译、原生检查、渲染后核查实际响应，收到试听后追加到表2；下一次检索时仍区分局部反馈、阴性、unknown和泛化。生成规则的可靠性靠实际曲目复核，来源和决策检查仅保证知识确实进入了计划。
