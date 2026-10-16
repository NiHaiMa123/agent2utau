# Skill 执行复检实际结果

2026-10-15。状态 `execution_review_implemented_transfer_unverified`。按[要求](skill-execution-review-requirements.md)完成最小实现、生产接入及真实旧工程回归；没有宣称新歌或听感已经通过。

## 实际版本与入口

- 分支 `codex/source-function-cleanup`，HEAD `79da450d1d202a05942c236ab9231ca633660ce4`。工作区原有大量改动，R0逐文件快照保存在 `runs/review/skill-execution-20261015/before`；没有reset、合并、提交或推送。新增/改动SHA及执行文件版本在同目录 `final-version.json`；requirements MD与开工状态在 `R0-version.json`。
- 共享实现：[execution_review.py](../src/agent2utau/evaluation/execution_review.py)、[local_views.py](../src/agent2utau/evaluation/local_views.py)。生产 `compile-functions --review-contract`、`review-inventory`、`review-execution`、`review-delivery`、`render-project --execution-review` 已调用共享契约。直接写工程的脚本不能通过缺失复检的交付检查；这不是操作系统级禁止任意脚本写文件。
- 旧schema2仍能技术复现，但缺sidecar会标 `candidate_review_incomplete`；移除了编译器无依据的“未继承作者曲线=false/true”式完成声明。schema3上下文动作库不是默认编译器的等价适配器，未支持表示明确失败，不静默换函数。
- 仓库与安装 `singing-expression-editor` 共38个有效文件逐字节/SHA一致。开工时37个相同，新增通用契约引用1份；更新后实际读取了安装版Skill及新引用。隐藏会话缓存状态unknown；不以磁盘一致宣称缓存已自动重载。

## 强制检查与Agent职责

程序从原生输入枚举分母、同元音延续及换字身份，绑定part/phrase/note/phone/锚点/时钟/声库/软件。缺原生为static_only；多声库逐轨环境尚不支持，明确拒绝。必要阶段与执行映射/实际参数/检查逐一绑定；未分配的元音支撑、unknown、漏阶段不通过。

独立facts先于计划/期待读取，保留实际绝对线、before-PITD、PITD、note.pitch/vibrato、控制原值、慢线性中心与残差。函数目标读回、主体位置、转向顺序、累计逆行及有序landmarks分别查。字头大运动、未使用/抵消/量化消失的动作不能顶替主体。短支撑不足以测周期保留unknown；有当前依据的hold合法，没有波动配额。阶段窗口和前版计划SHA保留；修订另存，不包装原计划。

Agent仍须读当前源证据、判断音乐阶段/参数与合理备选，并按句实际打开全部元音完整局部图，逐字给出具体保留/修改理由。重复理由/参数触发复审；文字与看图记录不能证明判断正确。程序核完整支撑、邻接、重叠页、固定尺度和版本；生成图册不算审阅，numeric_only不算图像覆盖。工程、输入、事实或图像变化使旧记录失效；不能证明无关时应扩大到整句/全曲复查，不自动猜原生模型依赖范围。

## 实际回归

| 层级 | 本轮实际结果 |
|---|---|
| 本机测试 | 194通过，失败0；日志/JUnit：`tests-delivery.log/.xml` |
| 新构造原生探针 | 3元音、3必要未分段阶段；慢中心、不对称有限回收、过冲和不等转折，最大读回误差0.499010975c；原生身份/阶段/动作检查通过 |
| 探针实际局部审阅 | 3图逐个用view_image打开并结合数值，3/3；最终共享复检complete=true，但仅为合成能力/过程案例，音频、自然度、迁移unknown |
| 既有雨爱只读接入 | 371元音组，358辅音、42非唱phone、unknown phone 0；实际Core重新导出，工程SHA保持 `d33223015985cc1e0973587f8452a0f7965a5302805209b01217a371ccc577ae` |
| 旧工程图册与覆盖 | 374局部视图，600px/s、50px/半音、2秒页/0.25秒重叠/0.22秒邻接；只实际打开3个诊断图，其余368组未打开。缺前向账本，正式完成0/371、待处理371；不倒填音乐选择/阶段，执行结果false |

原生探针位于 `runs/review/skill-execution-20261015/native-probe-v3`：先冻结spec/context/inventory/plan/ledger，再经真实compile-functions；编译首份报告因未看图为候选，看图后以 `actual-reviews.json` 复检，最终 `review-final/review.json`。这次修订增加实际审阅记录，没有修改音乐策略。-55c下探的0.2秒下降/0.5秒恢复、+40c过冲及不等节点均为新构造测试数值，不能变成新歌默认参数。

旧工程证据在同run的 `actual-project-v3/review-final` 与 `actual-diagnostic-image-access.json`。前三个观察分别是小主体运动、大入口滑音和同元音跨音符；不能拿它们代表全曲已审。371项当前音乐条件仍unknown，阶段只保留原生未分段nucleus。本轮没有替旧曲制作新的事前条件表。

首轮失败均保留：风险测试夹具字段/浮点边界错误；真实旧工程359→363→371的语言音素分类修正（英文v与中文v、y0、iu/ui）；探针v1把音素末端4.8秒当作最后5tick采样点4.796875秒、v2映射支撑也越过了采样尾。已改探针编码映射，元音完整支撑未缩短，原生误差门槛未放宽。v1/v2产物未覆盖。UTF-8 Skill校验初次因Windows默认GBK失败，使用Python `-X utf8` 后通过，未改正确原文。

测试涵盖缺身份/阶段、整句泛话、入口掩盖主体、合法平稳、慢弯折/有限动作、取消/量化/错位、未消费参数、未知/短支撑、来源改名/未登记读取、条件变化、只生成图/仅数值、长字重叠页、旧图/后改工程/当前声库环境失效及真实CLI拦截。mock只验证契约，真实Core探针另列。工作树门禁已通过（无音频载荷、3作者原件/5ZIP成员字节校验、Skill链接/安装一致）；作者原件仅门禁字节核对，不作为制作输入。

## 来源、音频与迁移边界

已登记来源角色/文件SHA、参数绑定及Python字面读取位置可核查；作者数组、改名派生参数和历史目标进入制作会失败。动态路径、谎报来源及Agent此前暴露知识无法由该检查器证明，`absolute_originality_certified=false`。探针只加载表1实体/参数定义，response列表为空；没有作者工程或历史歌曲数组作为目标。

未做新的variance/acoustic/vocoder成声、旧歌修复、整曲重渲染或人工试听；测试目录内只有构造的静音输入，不是演唱音频。真实渲染帧/多相位/声学效果仍unknown。音频交付API的finite/peak检查不认证模型输入、对齐或听感。

新歌迁移 **unverified**：花海、最后一页、雨爱均已暴露/用于开发，不能当未见曲；当前未确认其它已授权未见曲材料。未另取歌曲或要求立即试听。后续真正新歌须先冻结本轮版本、登记输入，保留首版及最多两轮音乐策略修订，完成整曲全部局部审阅与声音验收。函数/旧工程回归不能证明下一首已经做好。

AGENTS/README/根plan已更新当前入口；旧用户否决、局部接受、表1/表2数值与unknown保留。单Agent执行，CI仍仅手动。
