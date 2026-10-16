# 当前执行流程

制作按Skill的[逐句工作循环](../skills/singing-expression-editor/references/phrase-by-phrase-workflow.md)：先通览/列音乐句，再把当前句的源观察、逐字意图、画线、原生编译、主体与跨字实际图审及成声检查做完，保存进度后才做下一句。整曲是逐句结果组装，不能先批量给全曲分派入口/平台再统一看图。用户试听另列，不要求每句人工批准；本页的制作步骤按当前句循环执行，最终再做跨句和整曲核查。

## 环境

从仓库根运行。`configs/defaults.yaml` 为默认设置；机器差异写入未跟踪的 `configs/local.yaml`（至少设置 `openutau_dir`、`default_singer`）。实际需要当前 OpenUtau、所选声库、GAME及RMVPE依赖、MelBand成套权重/YAML与manifest、ffmpeg、FCPE、Whisper、HubertFA。仓库不携带模型或录音。

文件边界见[目录与阶段规范](guides/repository-layout.md)。生产代码在`src/agent2utau`，测试在`tests`，知识表在`docs/knowledge`，仓库维护工具在`tools/repository`。新任务显式选择`runs/production/<run-id>`、`runs/experiments/<run-id>`或`runs/research/<run-id>`，按需要分输入/观测/谱面/设计/编译/原生/混音/评价/交付/反馈/日志；这只是`--out`组织约定，不是新的自动制作API。旧封存run不搬动。

`agent2utau deploy-bridge` 编译部署到配置的OpenUtau目录；bridge必须在那里运行，复用当前Core。`doctor`区分资源存在、声库加载与未执行的音频检查。

## 从头观测与判断

`observe-source <audio> --out <新的目录>` 默认解码并做分离、ASR、GAME、FCPE、RMVPE。`--steps asr,game,fcpe,rmvpe` 可明确选择观测步骤；不含separate时分析解码的原混音，需声明局限。每次新目录，绑定源哈希和实际产物，不扫描旧歌或作者项目。

GAME是音符事件，不是逐帧F0。ASR字符跨度是近似观察，不是已核实字界。Agent结合音频观测与语义准备歌词和HFA输入（裁剪音频与同名.lab），再执行当前HubertFA，例如：

```powershell
python external/HubertFA/onnx_infer.py -m external/hfa_model/1201_hfa_model/model.onnx -wf runs/new/hfa_inputs -l zh -np AP,EP -o runs/new/hfa
```

绑定HFA模型、输入与输出；保留unknown。Agent自行选择谱面和AP/SP上下文，用 `openutau/build.py` 或显式USTX编辑构建自己的音符，不自动把源F0直接写成PITD。

## 明确设计并编译

制作前必须按[知识接入](guides/knowledge-use-in-production.md)读取表1/表2当前相关ID，保存SHA绑定knowledge_context及逐条采用/拒绝/外推依据。`agent2utau knowledge-context`只读公开知识；`compile-functions`使用schema2，在原生执行或写输出前验证来源/字段/决策。没有匹配响应须明确absence_reason，不能把unknown当有效配方。旧schema1计划须迁移；历史封存输入不改。

先按问题检查当前相关系列的正例、阴性、副作用及后续反馈/更正，说明实际检索范围和怎样改变当前设计。门禁只核对已选记录，不能证明经验已检全；禁止历史制作载荷不自动禁止允许的公开方法/反馈知识。见[Skill知识接入](../skills/singing-expression-editor/references/knowledge-before-design.md)。

先用 `export-pitch` 和 `export-phonemes` 得到自己的谱面在当前声库中的原生时钟，建立完整条件清单。Agent对当前音乐句看连续原曲与歌词上下文，分别判断各字入口、主体、退出和跨字准备及发声目标；冻结本句意图后，才选择节点、有限动作、周期深度/频率/相位。主体窗口从实际到达判断，不默认先快速到中心再统一补浅波动。每个独立主张另检对应局部，不以一个入口的通过代替整句主体。`scripts/design_functions.py`的schema1只接受agent_designed计划，函数数学不替Agent判断。

数值计划尚不存在时执行 `freeze-musical-intent --brief <意图.json> --inventory <清单.json> --plan <未来函数计划路径> --out <lock.json>`。意图绑定原曲观察、备选、可观察后果及当前发声校准。少量代表性完整语境先提供试听机会，未试听维持 unvalidated；用户要求整曲时可以继续交候选。冻结工具记录局部执行顺序，不证明隐藏推理或音乐正确，旧制作不倒填。

`compile-functions --plan <json> --out <新目录>` 的外层格式：

```json
{
  "schema_version": 2,
  "project": "score.ustx",
  "source_audio": "source.wav",
  "input_hashes": {"score.ustx": "<SHA256>", "source.wav": "<SHA256>"},
  "scope": "whole_song",
  "phrases": [{"part_index": 0, "position": 0, "design": "<此处填完整函数对象，不是文件名>"}],
  "knowledge_context": {
    "path": "knowledge_context.json",
    "sha256": "<包SHA256>",
    "decisions": [{"id": "<每个取回ID各一条>", "decision": "use", "reason": "<选择依据>", "condition_match": "<当前条件的匹配或差异>", "limitations": "<本次证据的限制>"}]
  }
}
```

路径相对计划文件。当前编译器要求scope=whole_song及输入工程全部原生短句的完整覆盖，尚无局部scope参数；逐句制作以保持绝对时钟和必要上下文的工作副本为输入。提取与回写后核对音乐/音素身份、授权区目标等价和区外保持，不能把工作副本通过当完整工程已经等价。phrases按原生导出顺序完整排列；position是原生phrase.position，非秒。design是Skill helper完整schema1对象（support_s、center_nodes、components、decisions、expectations），support_s覆盖该句所有原生前导/尾帧。center_nodes为[绝对秒,绝对cents,cents/秒斜率]。整曲最终只组装已逐句复核目标，不重新发配函数。

编译器移除原有PITD和内置vibrato重复贡献，保留Agent自己的note.pitch、音符/音素时钟和其它表达；before-PITD仅参与目标编码。检查全部乐句覆盖、局部期待、范围、整数网格冲突、音素几何和实际读回≤0.501c；失败留日志，不输出成功声明。

schema3 `expression/context_actions.py`仍可执行显式音素锚点的分层动作，但它与上述helper的函数/包络定义不同，不能静默混用参数。需要其它函数时明确实现并验证，不改为近似模板。

## 发声、渲染与验收

### 生产执行复检

新制作顺序为条件清单/原曲判断 → 冻结音乐意图 → 数值计划/前向 ledger → 原生技术核验 → 实际音乐复审 → 听觉验收。`compile-functions --review-contract <schema2-sidecar>` 接共享契约，含 inventory/ledger/reviews/intent_lock/musical_critique；数值函数计划仍为schema2，其余sidecar各有版本。身份、阶段和 intent lock 在编译前验证；最终线独立 facts 先于计划期待读取。旧schema1契约及无契约回放保留为候选，不补认新流程。

编译产物含固定尺度的全曲逐字 atlas；Agent逐句打开每字完整视图及邻接，保存实际访问、数值和判断。另写逐句音乐 critique，说明与备选的实际区别，并回应归一化结构重复/全零斜率提示；不是重复参数配额。`review-execution --reviews <records> --intent-lock <lock> --musical-critique <critique>` 既验覆盖，也用冻结标准对比实际线和快速连接/浅偏差消融。实际与消融同过，不能宣称标准排除了平直路线；有依据的稳定动作允许相同。评价不写回曲线。

`technical_execution_complete` 与 `workflow_review_complete` 分列，keep/理由只是 agent_attested。完整流程还需前置意图、实际/消融检查、具体音乐复审和发声试听证据；兼容 production_execution_complete 跟随新流程。音乐质量仍 unverified，最终听感另验。`render-project --execution-review <review.json>` 渲染前查当前版本及嵌套证据，波形另写交付 receipt；自定义入口同用 `delivery_review`。旧收据不会自动升级。改工程/音素/来源后复查实际依赖，缺项仍可交候选。

详细字段与边界见[Skill执行契约](../skills/singing-expression-editor/references/production-execution-review.md)。只读已有工程回归：`python tools/repository/run_execution_review_regression.py --project <ustx> --out <新目录>`；没有原账本就报告缺失，不倒填前向设计。`tools/repository/probe_native_expression.py` 是新构造的函数/原生能力探针，不能作新歌生成器或听感验收。

发声事件通过Skill `compile_control_overlay.py`写入有限支撑；只编译所选控制，不自动补VOIC或每字归一化。SHFC、GENC、CLR及模型支持须单独核实。发声控制不是compile-functions自动生成的内容。

`render-project`调用原生渲染；`export-render-probe --indices 0,1,...`导出当前variance/acoustic实际输入。当前条件改变后重算依赖；固定种子、缓存、声线embedding、模型权重与波形拼接须另行绑定，不能直接复用旧状态。

`audio/mix.py`只使用明确给定的固定声/伴奏增益，PCM24输出；不自动平衡、不压缩或归一化，削波时失败并要求重新选择增益。分开检查音高、字界、发声、真实短窗能量与听感；没有听觉验收不宣布自然度解决。

当前七个《最后一页》脚本保留在[历史实现记录](../research/implementation-records/lastpage-20261007/README.md)，含当次Agent明确数值选择及原路径/哈希限制。本次搬迁保留字节与SHA，旧路径/导入不改写，不作为可直接重跑的新歌CLI。最新接受/否决反馈见[表2](knowledge/acoustic-manifestations-20261009/conditional-responses.md)，局部接受不代表整曲问题已修复。
