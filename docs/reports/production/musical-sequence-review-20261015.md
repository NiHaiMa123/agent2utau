# 制作顺序、评价区分能力与 Skill 整改实现

2026-10-15。状态：`musical_sequence_review_implemented_quality_unverified`。用户在[两轮失败分析](../../../songs/yuai/sessions/20261015__unknown-model__yuai-v02-two-pass-audit-20261015/reports/v02-two-pass-failure-analysis-20261015.md)后明确授权更改执行顺序、评价和 Skill。本次完成工具与方法接入，没有重新制作雨爱；音乐质量改善尚未验证。单 Agent，本机检查，CI 仍仅手动。

## 1. 执行顺序已改变

新顺序：完整乐句源观察/歌词上下文 → 到达、跨字路线与发声目标 → 冻结音乐意图 → 数值函数计划和前向账本 → 原生技术核验 → 实际音乐复审 → 听觉验收。

新增 `freeze-musical-intent`。它要求未来数值计划路径尚不存在，绑定当前真实单元清单、连续源观察及窗口、具体解释与备选、可观察后果、发声校准上下文，再生成 intent lock。完整物理单元必须由动作支撑并集覆盖，不能以一个短检查窗冒充整体。编译 contract v2 在原生操作及创建输出目录之前验证 lock；旧 v1 仍可技术回放，但交付状态限于候选。当前雨爱没有真实前置新意图，不倒填。

先判断是否低位准备、分段/延迟到达、跨字持续，再定义字腹和函数。不能先给每字快速到主音的平台，再把浅鼓包称为逐字音乐设计。中心途中节点保留当前所需速度，真正停留和极值允许零导数，不强制每字变化。

发声基底在扩展整曲前，用少量不同音乐/音素条件的完整语境校准，绑定实际音频、反馈和适用条件；Normal100及非零控制都不自动证明实感合适。无人试听写 unvalidated，用户要求完整候选仍可交付，不能因缺试听虚报校准或增加许可流程。

## 2. 评价现在能拒绝哪类错误

新增只读 [musical_review.py](../../../src/agent2utau/evaluation/musical_review.py)，共享入口仍为 [execution_review.py](../../../src/agent2utau/evaluation/execution_review.py)，已接 [compile-functions](../../../src/agent2utau/workflow.py) 和交付 receipt。

| 风险 | 新行为 | 限制 |
|---|---|---|
| 已画线后倒填音乐理由 | 数值计划创建前冻结独立意图，编译核 SHA/目标路径 | 局部工具顺序证据，不是签名或隐藏推理证明 |
| 目标跟随精确，但过程仍浅平 | 同一事前标准同时测实际线与浅偏差消融；must_differ 两者同过会拒绝 | 只可否定几何主张，不能判好听 |
| 字头滑动替字腹变化背书 | 意图按当前动作支撑和具体标准检查，完整物理单元覆盖独立核对 | 合理标准仍需 Agent 判断，文字不能保证判断正确 |
| 换 ID/数值掩盖同一种结构 | 归一化组件时间结构分组，另列全零中心斜率 | 是复审提示，不是变化配额或自动音乐失败 |
| keep 加非空文本被当作选择通过 | 仅记 agent_attested；独立逐句 critique 描述实际后果、回应结构提示 | 工具不能认证 Agent 理解、来源解释或审美 |
| 旧收据和换过证据继续通行 | 旧 true 不升级新流程；验证嵌套校准、critique、图册证据 SHA | 不刷新原收据；动态未登记来源仍不可证明 |

消融只用当前谱面音符中心和预先指定连接时长，裁去实际偏差超过预定浅预算的部分；浅起伏本身保留，避免用任意正弦相位制造“有区分力”。这不是目标生成器，不写工程，也不读取作者数组。预算/连接时长由当前意图声明，不是通用音分下限。有依据的稳定、浅动作可声明 may_match，hold 必须允许相同；采样不足/未知过程不升为通过。尚不能把重叠多声部混合成一条音乐动作。

## 3. 完成状态已拆开

- `technical_execution_complete`：身份、前向账本、原生实际动作、完整图像覆盖、登记来源的技术事项。
- `choice_review.status=agent_attested`：Agent 声明实际审阅；不是音乐正确。
- `musical_review`：冻结意图的实现、消融区分、结构回应、独立逐句判断及发声证据状态。
- `workflow_review_complete`：还需上述音乐过程、完整 critique 和绑定的发声试听证据；兼容字段 production_execution_complete 跟随此值。
- `musical_quality=unverified`：工具始终不自动认证最终听感；输出音频、人工标签和未见曲迁移另验。

新 render 状态区分 rendered_workflow_reviewed、rendered_technical_candidate、rendered_candidate_review_incomplete。缺项不禁止候选交付，也不将技术成功包装为音乐成功。原输出报告/收据原字节保留，新结论写在新回归目录。

## 4. Skill 和执行文档已同步

修改主 Skill 及六份方法引用：source-condition-to-function、production-execution-review、planning-and-evaluation、voice-baseline-and-stability、joint-phonation-and-sustain、project-tools。[完整契约](../../../skills/singing-expression-editor/references/production-execution-review.md)给出 brief/lock/critique、contract v2、CLI 及候选边界；[workflow](../../workflow.md)同步顺序。

VOIC 不再把100默认/零增量说成引擎硬上限。合法范围从当前工程声明读取，加载、重采样、模型特征裁剪及声音响应分别核实，权威说明统一指向 pitch-phonation-and-loudness；没有采用作者旧129或擅自把所有工程上限改成200。测试分别验证当前 max100 拒绝正偏移、max200 可合法编码，二者均不证明变实。

仓库与已安装 Skill 的38份文件逐项 SHA 一致，本轮同步7份；安装前快照保存在本轮 ignored run。文件同步不证明不可观察的会话缓存已刷新。

## 5. 实际回归与本机验证

全套 **208 项 pytest 通过**。新增11项音乐契约反例和1项当前描述符范围反例；测试是合成几何/身份契约，不是真人或歌曲试听。覆盖事后冻结拒绝、明显低位准备可区分、浅起伏同过标准被拒绝、快速到达不符延迟意图、有依据 hold 合法、完整支撑遗漏拒绝、编译前失效、证据替换失效和旧收据不升级。

第一轮全套执行因沙箱默认临时目录不可写出现69项setup错误及1项临时目录相关失败；保留失败XML，随后显式使用本轮 workspace TEMP/TMP/basetemp重跑通过，没有放宽业务断言。Skill quick_validate 通过；本机工作树门禁检查工程原件/ZIP、无音频载荷、Skill引用及安装一致，结果见本轮 gate.json，未运行远端CI。

使用当前雨爱v02原有原生导出、账本、全部图审和同 SHA 图册作只读回归：

| 项目 | 新结果 |
|---|---|
| 实际元音/图审 | 371，完整覆盖371/371，未重新声称本轮看过这些图 |
| 技术执行 | true，原技术事实保留 |
| 新流程/兼容production完成 | false，缺真实前置新意图与发声校准 |
| 音乐状态 | unverified，Agent旧keep为审阅声明 |
| 结构提示 | 1425/1425中心节点零斜率、6组归一化重复组件结构 |
| 音乐质量、听感、迁移 | unverified / unknown / unverified |

11项开始时保护文件及此前公开v02记录的13项文件引用SHA核对一致，包括发布工程、三份作者原件、已有试听/人声和旧审计/收据。原作者仅作字节身份门禁，没有开展新参考研究，也没有搬用参数。更新前101份源码/测试/方法/入口文件已快照；没有新模型调用、原生导出、音频渲染、试听标签或通用声学响应结论。

## 6. 尚未证明与下一步

本次证明工具能挡住上述错误，并使流程缺口可见；尚未证明 Agent 会稳定作出更好的音乐选择，也没有解决“太虚”的单一声学病因。brief 和 critique 的文字仍可能空泛或判断错误，来源可靠性与真实试听需诚实核查；有绑定证据不等于全曲被接受。

下一制作按根目录 plan 的新顺序，从当前原曲重新展开代表性乐句，先判断到达/跨字路线和发声基底，提供有限代表组试听后再扩整曲。不回放失败生成脚本，不倒填雨爱v02前置意图，不把本次回归当留出迁移；本轮不自动制作v03。

可复核结果：[公开记录](musical-sequence-review-20261015.json)；本机原始产物在 `runs/review/skill-musical-sequence-20261015/`，含开始快照/保护、pytest XML、雨爱新回归、Skill同步收据和门禁结果。旧两轮分析及原生产run保持。
