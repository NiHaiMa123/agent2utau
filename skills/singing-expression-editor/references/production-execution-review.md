# 逐元音执行复检

本契约分别检查技术执行、事前音乐意图的可证伪性和 Agent 审阅声明，听觉质量独立保留。数学期待、图像和参数散布不证明自然度。保持单 Agent；用户要求整曲时可以交付缺口明确的候选，不为流程另增人工许可。

## 前向工作顺序

以下步骤对[当前音乐句](phrase-by-phrase-workflow.md)完整执行一次，再推进下一句；整曲源观测/底谱身份可提前准备，后句的数值目标不能提前批量派发。音乐句与原生RenderPhrase分别登记，必要依赖上下文和授权写入区域分开。每句保存进度和版本，用户试听状态另列，不新增逐句许可等待。当前contract/CLI没有验证整曲逐句真实先后顺序的字段，该顺序须由Agent实际执行和记录，旧收据不倒填。

1. 记录当前 Git/工作树、仓库与实际安装 Skill SHA、执行入口。安装文件一致不证明隐藏的会话缓存已更新；实际读过的文件与不能观察的缓存状态分开。
2. 从当前自己的谱面导出 `export-pitch`、`export-phonemes`；保存 provenance schema1：`project_sha256`、`pitch_sha256`、`phonemes_sha256`、`environment`（`core_sha256`、`bridge_sha256`、`singer_id`、`singer_config_sha256`）。原生数组是编码/观察，不能倒填事前动作。
3. 用 `review-inventory --project <ustx> --out <inventory.json> --native-pitch <json> --phonemes <json> --provenance <json> [--sources <json>] [--context <json>]` 建条件清单。来源 manifest、context 必须冻结；初次可只枚举身份，再补当前证据冻结完整版本。缺原生环境保留 static_only。
4. 先检查原曲连续轨迹、歌词及上下文，写下文的 musical intent brief；确定到达方式和跨字路线，再划分主体，不能先把所有字快速送到中心再补小波动。原曲秒轴和当前谱面秒轴分别登记，不能默认相等。未观测到的动作标 unknown。发声基底先用少量代表性完整语境做试听校准，绑定音频、反馈和适用条件；未获试听就写 unvalidated，不默认 Normal100 合适。只有当前谱面的 unit ID 可进入制作，作者参数不进入此过程。
5. **数值函数计划尚不存在时**执行 `freeze-musical-intent --brief <json> --inventory <json> --plan <未来计划路径> --out <lock.json>`。它验证身份、完整支撑及证据，并记录工具观察到的先后顺序；不认证隐藏推理或绝对原创性。不要删除已有计划来补造前向证据；旧制作只能回归，不能倒填。
6. 根据冻结意图编写 schema2 函数计划、knowledge_context、逐 ID 决策和前向 ledger。`compile-functions --plan <json> --out <新目录> --review-contract <schema2契约>` 在原生执行前核 intent lock、身份和阶段覆盖；编译后独立提取实际最终线，检查执行并生成局部图册。初编译 reviews/musical_critique 为 null，不是假装完成。
7. 按句查看每个元音完整局部图与实际数值，再回看句子。检查低位准备、分段/延迟到达、跨字延续、主体和退出是否真的发生；不能仅核对函数跟随。短字可邻接，长字连续重叠页全部查看。保存逐字 review records，并另写 phrase critique，解释实际与备选的区别。生成图册或非空 keep 理由只证明审阅声明。
8. `review-execution` 传入 `--ledger --plan --reviews --intent-lock --musical-critique`，可用 `--atlas` 复用同 SHA 的既有图册。检查事前标准能否排除“快速连接加浅起伏”消融；工具也按归一化结构揭示重复。工程、音素、输入或证据变化使旧 SHA 失效，扩大到实际依赖的邻接；未证明无关时全量复检。失败须修音乐动作或诚实修改判断，保留前版，不能事后放宽阈值包装通过。
9. `render-project --project <ustx> --out <新目录> --execution-review <review.json>` 渲染前验证当前 SHA 和嵌套证据，渲染后另写实际交付 receipt。自定义脚本接同一个 `review_execution` / `delivery_review`。优先给有限代表组试听机会，再按用户范围扩整曲；无人试听仍可交候选，听感维持 unknown。

完整 CLI 参数以 `python -m agent2utau.cli <命令> --help` 为准。只读旧工程回归工具是 `tools/repository/run_execution_review_regression.py`；旧歌缺 ledger 直接报告缺失，不从成品线反推 forward。

## Sidecar schema1

所有文件引用是 `{path, sha256}`。身份清单的分母来自实际原生 group，保留 part/phrase/primary/note/phone IDs、秒、原生锚点、跨音符音乐阶段、邻接与条件。AP/SP、辅音、unknown 分开。同元音延续可合并，同音新字分开。默认只认未分段 nucleus，不虚构四阶段。

- sources：`{schema_version:1,sources:[{id,role,file:{path,sha256},description}]}`。role 可为 source_observation/current_score/native_export/software/implementation/inferred_rule/unknown；author_array/derived_author_parameters/historical_target 在制作中失败。来源改名不能洗掉角色；Agent必须按实际来源登记。AST只检查已登记 Python 的字面读取，动态路径、谎报角色、已暴露知识仍不可证明，绝对原创性始终不获认证。
- context：`{schema_version:1,units:[{id,condition:{status,evidence_ids,observation,interpretation,reliability},stages:[{id,kind,support_s,required}]}]}`。status 为 observed/interpreted/unknown；阶段按真实过程取 arrival/body/release/transition/unsegmented_nucleus。未分段或缺阶段维持 unknown；局部缩窗不能替完整元音通过。全部实际支撑必须有明确阶段归属；没有把握就保留未分段阶段和未知条件。
- contract **schema2**：`{schema_version:2,inventory:{path,sha256},ledger:{path,sha256},reviews:null,intent_lock:{path,sha256},musical_critique:null}`。初编译尚无实际审阅，两个记录置 null；之后直接 review-execution 绑定当前证据。schema1 旧契约仍供技术回放，但只能交候选，不补认新流程通过。此契约版本与外层函数计划 schema2、其余 sidecar schema1 各自独立。
- ledger：`{schema_version:1,inventory:{path,sha256},plan:{path,sha256},timing:"forward",decisions:[...],revisions:[]}`。每项含 `id,unit_ids,stage_ids,support_s,evidence_ids,observation,interpretation,reliability,purpose,choice,alternative,rejected_because,parameter_basis,execution,checks,uncertainty`。每个必要阶段恰一项；跨字共享须列齐身份与共享原因。choice 为 hold/center/finite_return/oscillation/landmarks/control/unknown/unsupported，后两者不通过。
- execution 每项：`{kind,part_index,position,id,support_s,parameters_sha256}`。kind 是 center_nodes（id= center_nodes，SHA 绑定整个节点数组）、component（绑定实际完整组件对象）或 control（绑定当前 USTX 完整 curve 对象）。position 是原生 phrase.position。`parameters_sha256` 用共享 API `digest` 的规范 JSON，不是文件 SHA。unsupported 不静默换成正弦。控制曲线绑定证明消费了何值，不能替代声学响应与听感检查。
- checks 每项：`{stage_id,kind,support_s,parameters}`。range/hold 参数 min_c/max_c；direction 为 direction(up/down)/min_delta_c/max_backtrack_c；landmarks 为 points（绝对秒/绝对 cents）、tolerance_c/time_tolerance_s；cycles 为 min_cycles/prominence_c。期待必须检验所选动作，非 hold 的 0–1600c 空泛幅度会触发复审。短支撑采样不足输出 unknown。不得在失败后改窗口/阈值来包装通过。
- 修改选择另存新文件，revisions 追加 `{previous:{path,sha256},reason,evidence_ids,unit_ids}`，保留前版。条件变化而参数相同触发重审，允许有证据地保留；不鼓励随机变化。

## 数值计划之前的 musical intent schema1

顶层是 `{schema_version:1,inventory:{path,sha256},phrases:[...],phonation:{...}}`，独立于函数参数文件。phrases 每项：

```json
{
  "id": "phrase-id", "unit_ids": ["<实际清单ID>"], "support_s": [0.0, 1.0],
  "intention": "当前整句的音乐目的",
  "observations": [{"id":"obs-id", "source_id":"<source_observation来源ID>",
    "source_window_s":[0.0,1.0], "description":"连续轨迹观察及局限", "reliability":"uncertain"}],
  "gestures": [{"id":"gesture-id", "unit_ids":["<实际清单ID>"],
    "role":"arrival", "support_s":[0.0,1.0], "observation_ids":["obs-id"],
    "interpretation":"为何当前上下文需要这种到达", "alternative":"具体可替代的唱法",
    "rejected_because":"备选会丢失什么可观察后果",
    "contrast":{"mode":"must_differ", "shallow_limit_c":25, "connection_s":0.08,
      "reason":"仅示意当前诊断反事实；实际数值须按当前意图选择"},
    "checks":[{"kind":"landmarks", "support_s":[0.0,1.0],
      "parameters":{"points":[[0.1,5850],[0.7,6000]], "tolerance_c":15, "time_tolerance_s":0.02}}]
  }]
}
```

示例不是唱法模板。phrase 的 unit_ids 恰好分割全部实际单元；每个单元的完整物理支撑须由归属的 gesture 支撑并集覆盖，不能用短窗代替整体。gesture 可共享多个字；role 为 arrival/body/connection/release/hold/unknown。observations 指向绑定的当前原曲观测，可靠性 observed/uncertain/unknown。未知不由源数组自动变成目标。checks 使用上文五种标准，省去 stage_id，由工具绑定 gesture；标准必须描述意图后果，不能仅容纳已经画好的线。

诊断对照只用于评价：按当前音符中心和预定 connection_s 生成统一连接中心，将**实际轨迹相对该中心的偏差裁至 ±shallow_limit_c**。这保留浅起伏本身，消去超过预算的过程；不写回工程、不用作者线、不作为生成器。must_differ 要求实际通过且至少一项消融失败；两者同过则标准无区分能力。may_match 允许有源依据的稳定/浅动作，hold 必须使用它。不用统一最低音分或波动配额，诊断参数本身也不是好听标准。采样不足/断档输出 unknown；重叠多声部尚不能合为单条动作，不能静默选一路。

phonation 为 `{baseline,target,status,contexts}`：status 是 unvalidated/listening_evidence；后者须有非空 contexts，每项 `{unit_ids,role,audio:{path,sha256},feedback:{path,sha256}}`。绑定文件只证明证据存在和身份，Agent仍须确认是真实试听、反馈方向、完整语境和当前适用条件；不是工具自动听过或全曲接受。没有反馈不伪造 calibration。

lock 由 CLI 生成并绑定 brief/inventory、未来计划绝对路径、`plan_existed_at_freeze:false` 和 UTC 时间。修改 brief/清单/试听证据需新版本与新流程，不刷新旧收据。计划不存在的局部观测不是签名证明，也不能防止 Agent 谎报；此限制须保留。

## 看图记录、音乐复审和结论

每句编译后立即完成这里的实际图审与音乐复核，处理本句已发现的漏画/动作检查失败后再标ready_for_next。逐字记录写具体观察，不把一段整句评语加范围数值重复到所有字。

当前检查器对一个gesture的must_differ只要求至少一项判据否决浅对照。多个独立字/主体主张须拆为各自gesture及局部检查，不让一个入口代表全句区分。声称主体展开时，提前声明绑定主体区的范围、有序转向/恢复或周期等可检查后果，不能只有字头landmarks。主体稳定仍可明确hold/may_match；不统一最低音分或波动配额。现有代码不会自动发现所有语义漏项，文案和非空理由不等于门禁已经实现。

records 文件：`{schema_version:1,inventory:{path,sha256},facts:{path,sha256},ledger:{path,sha256},atlas:{path,sha256},records:[...]}`。facts 为本轮 independent-facts.json，atlas 为 atlas/atlas.json。每条含 `unit_id,view_ids,method,view_evidence,facts_sha256,observation,result,reason,evidence_ids,resolved_findings`。

method 为 image_and_numeric 或 numeric_only；前者须绑定实际工具打开图像的访问记录/产物引用，后者不计图像覆盖。facts_sha256 是该单元事实对象的 `digest`。result 为 keep/revise/fail/unknown。view_ids 必须覆盖该单元完整支撑并属于正确 ID。resolved_findings 仅列本次有具体依据处理的复审 code，不复制统一结论。重复参数/理由是复审线索，不是波动配额；相关全部区域仍须逐字看。工具访问证明打开文件，不能证明理解正确。

独立 facts 在读 ledger/plan 之前提取，保留原始最终线、before-PITD、PITD、慢线性中心与残差、note.pitch/vibrato 和控制原值。慢线性中心是描述代理，不是任意非线性中心的真值；转向和局部路线还须看原始线。实际 final 必须与已消费函数相符，动作位置/顺序独立检查；字头大运动不抵消缺失的主体动作。

当前原生环境契约只支持同一已绑定声库；多声库轨道未支持逐轨环境时明确拒绝。渲染入口还会对照当前安装的Core/bridge/声库配置SHA，防止拿旧导出收据通过新环境；其余模型输入与实际音频仍须另验。

音乐 critique 为 `{schema_version:1,lock:{path,sha256},project:{path,sha256},pitch:{path,sha256},facts:{path,sha256},records:[...],structural_responses:[...]}`。每句 records 为 `{phrase_id,judgment,observed_consequences,evidence:[{path,sha256}]}`，judgment=retain/revise/unknown；描述实际后果，而非再抄参数。structural_responses 每项 `{code,context,evidence:[...]}`，回应工具本轮的全部结构提示。全零节点斜率、不同 ID/幅度下相同时间归一化组件会提示复审；允许有上下文理由地重复，不能用随机变化凑数量。证据文本完备只得 agent_attested；动作/消融失败不能被 retain 覆盖。评价记录与数值计划分开，原输出不就地修改。

报告分别列 `technical_execution_complete`（身份、前向账本、原生动作、完整图像覆盖、来源）、`choice_review.status=agent_attested`（审阅活动声明）、`musical_review`（冻结意图、消融、结构复审、声线证据）。`workflow_review_complete` 还要求真实前置 intent、动作/消融通过、完整 Agent critique 和绑定的发声试听证据；兼容字段 `production_execution_complete` 现在跟随它。`musical_quality` 始终 unverified，最终听感/迁移独立，不由这些字段自动认证。旧 true 收据不会在新交付入口被升级；原文件保持。缺项可交 rendered_technical_candidate / rendered_candidate_review_incomplete，不能称音乐设计通过。schema3上下文动作库尚非该生产编译器的等价适配器。

新歌迁移需冻结规则后使用未参与开发且已授权的源材料，保存首版及最多两轮策略修订。已暴露曲目只算开发回归。缺新歌材料时 transfer=unverified；函数/原生探针不替代真实新歌，也不要求用户立刻听音。
