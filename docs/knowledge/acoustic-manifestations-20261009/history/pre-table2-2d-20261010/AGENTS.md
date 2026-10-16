# agent2utau 当前工作约定

## Codex与当前计划

- 本项目后续由Codex处理；开始工作先读本文件、根目录`plan.md`和`README.md`，结合用户最新范围确定当前步骤。
- 由当前Codex单个Agent执行，不启动子Agent、多Agent协作或委派到其他对话。只有用户之后明确改变此约定才调整。
- 测试与仓库门禁在本机执行；GitHub的CI工作流关闭自动运行，本地配置仅保留手动触发。不要自动启用远端CI或增加push、pull_request、schedule触发，以免再次产生运行通知邮件。
- 根目录`plan.md`是唯一当前执行计划，表1固定范围整合已完成并保留确认缺口，当前继续关联表2专项的记录确认。A提出47个分层实体；B完成31行定义/30组组合词审查，累计30条说法/25来源并保留缺口。C固定范围审查完成，状态reviewed_with_explicit_gaps：352条具体项覆盖48导航组，前320个ID保持；31节点、导出/播放/pan law、23项本机静态能力及103偏好字段/8嵌套属性、预设/网格写入与扩展接口范围已列。本机graph/masked、FX独立开关/WrapLive及MergePhrasesSec/ReduceAnimations声明字段缺失；MixFxApplyOnExportMixdown未被已核查出口读取。D状态protocol_review_complete_with_explicit_gaps：50协议覆盖A47及3个B候选，10组数组仅验证列明数学/组件范围，11源码/契约加1研究验证器SHA绑定；全部measurement_validated仍false。E状态coverage_review_complete_with_explicit_gaps：42项先冻结再36主映射/6过程复查，34结构可记录/8部分，16已有标签行、0完整测量结论；34候选被链接/16未覆盖。F状态consolidated_with_explicit_gaps：49个正式分层记录实体（24 ACO/15 EVT/9 PER/1 META）、1复音/拍频开放候选、30 DESC、48 CTRL/352 PARAM，31旧描述ID去向和14条RESP/OBS/AUD引用已迁移，原数值/状态/反馈/证据SHA精确保持。40份迁移前文件原字节/SHA保存，8组上下文/任务字段已定义但E的8部分项仍部分。表2专项2A状态source_binding_audit_complete_with_explicit_gaps：17份现行文档先冻结，14记录/52来源/五设计896封存文件声明/1079唯一仓库路径与67保护输入SHA通过。原表2/F产物及原报告/工程/Skill/旧run不改，音频/数组只流式核对字节SHA，未解码、复测、试听或执行模型。C-B/A-C角色、有效_grid5路径、TENC58混合依赖与其它47项范围、索引缺列/原话末尾句号/反馈元数据unknown及本次附加文件名勘误共7项明确。2B状态schema_revised_with_explicit_gaps：26份现行文档/脚本先冻结，14记录新增record_v3/17比较/6反馈组，原数值/状态/反馈/SHA与表1引用保持；深度恢复旧JSON、旧CSV等式与Markdown主体通过。抱C的本轮fresh/B映射逻辑C，旧B在上轮SHFC，原脚本SHA明确；当前runtime/指标复测/新听觉均未执行。2C状态record_review_complete_with_explicit_gaps：14记录复核完成，60份输入/预测NPZ只读、129实际读取绑定文件保持，823指标标量字段与原JSON/报告匹配。原生/fresh输入算术、支撑、通道、SHFC路径及重复输入/预测重查；20版本最终三通道由独立验证器重建检查。36项限定确认/24部分/56unknown逐项列明，不是新实验或普遍规律；旧2B与更旧记录可精确恢复。新模型/原生执行、PCM/mel/检测器数组读取、声学复测/试听均0，全部measurement_validated仍false。下一步2D知识缺口与有限协议冻结，2D–2H未执行。E不是独立音频留出；U17冻结word282误写已增补word295勘误，原冻结文本/unknown保留。F已纠正E的工具显示编码误判：原JSON严格UTF-8且SHA一致、1174字符串无替换/Latin1异常，10条反馈与原报告/CSV对应，未对正确原文转码；E冻结原记录保留。A旧提案读错atoms字段而生成14空关联，F按实际atomic_ids补齐，新增关联仍为结构候选非测量真值。44+25+17共86份唯一固定源码/六资源与Core/App绑定不等于全部非默认执行或模型验证；未读消费者/插件/真实设备增益unknown。C/D不替代试听；E核查已有反馈，新因果试听按表2后续冻结设计推进。B反例不是新音频或E独立覆盖，原清单/ID版本已正式迁移并保留legacy字段/原字节快照，局部证据不代表通用调参规律通过。
- 由Codex更新`plan.md`进度、报告引用及`README.md`当前状态。用户授权的`plan-table2.md`是根目录关联的专项计划，已完成2A来源/版本绑定审计、2B结构修订与2C记录复核，2D尚未执行；仍由根目录plan总入口维护，不自动进入新因果试听。旧计划已被替换，`docs`中的评价与实验报告保留作为历史证据，其中旧“下一步”不覆盖当前计划；不另建重复的活动计划。
- 当前根目录保留`README.md`、`AGENTS.md`、`plan.md`及用户授权的`plan-table2.md`，分别作为项目入口、Codex工作约定、当前计划及后续专项计划。根目录入口整理不改变歌曲工程、Skill或封存实验；后续按实际任务与已有授权推进。

## 目录与文件边界

- 按`docs/guides/repository-layout.md`存放文件。通用生产/只读评价在`src/agent2utau`，原生源码在`bridge/OuBridge`；测试只在`tests/unit`、`tests/contracts`、`tests/skills`，测试临时文件不写发布工程/生产run。
- 仓库维护工具在`tools/repository`；七份旧歌曲脚本在`research/implementation-records/lastpage-20261007`，保留原字节，不执行为新曲模板。历史manifest不改写，旧脚本路径核对使用显式目录迁移清单。
- 表1/表2知识包在`docs/knowledge/acoustic-manifestations-20261009`；新方法文档放`docs/guides`、新可读报告放`docs/reports/<主题>`。封存历史报告及Skill引用的稳定文档保留原路径，不改其原始证据。
- 新运行按生产/实验/研究/原生测试/构建角色在ignored `runs`创建新目录，再分观测、谱面、设计、编译、原生输入、混音、评价、交付、反馈与日志。旧封存run、作者原件/包、发布USTX和本机模型/安装不移动。
- `data`、`models`、`external`、`runs`均为本机资料/产物；不提交。移动/改名维护后检查文档、维护配置、pytest和生成脚本路径；工作树门禁为`python tools/repository/check_repository.py --worktree`，发布检查使用默认索引模式。

## 唯一制作流程

- 读 `skills/singing-expression-editor/SKILL.md` 和 `docs/workflow.md`。
- 当前原曲 GAME / 双 F0 / ASR / HFA 是观测，Agent 判断音乐身份、歌词、音素时钟和未知范围。
- Agent 选择函数、锚点、斜率、幅度、相位及发声过程，明确目的、备选和局部期待。
- 用显式函数计划编译全曲；原生 before-PITD 仅用于编码，不作为目标线。保留并检查 Agent 选择的 note pitch 衔接。
- 改音高、音素、声线、分句后，重建相关预测和实际输入；检查两阶段 speaker、当前张力/气声/有声基底、原生 DYN、拼接和固定增益。
- 保留 source unknown，不拿数学跟随、音量代理或图像检查宣布听觉自然度通过。没有听音工具时标明未听。

## 代码与资料

- CLI只有原曲观测、显式函数编译、原生导出/渲染和资源检查；旧 cover / repair / 候选搜索 / 自动参考路线已撤出。
- 独立只读评价入口为 `python -m agent2utau.evaluation`。只接显式输入和SHA绑定，不读取制作计划的expectations作真值，不自动修歌或搜索缓存；覆盖未知与听觉验收分开。
- 研究资料 `research/baishuo` 的三份原件保持只读；不能把作者数组裁剪、移调、重定时或拟合后接入独立制作。
- `research/implementation-records/lastpage-20261007/`中的脚本为最近完成歌曲的实现记录，不是新曲模板。新曲应使用通用接口与新计划；不可原样重跑已经绑定的旧目录。
- 历史路线及笔记在本机 `.local-archive/cleanup-20261008`，不自动加载、不作为默认入口。此前方案的失败与试听待验收状态不会因清理变成成功。
- 最近用户反馈定位：最后一页响度v02，1:27与3:04偏假/顶上去，1:33与2:56偏实；只完成诊断，尚未修复或听觉验收。
- 2026-10-08 用户授权的单个3:04 TENC实验已完成，见 `docs/lastpage-tenc-controlled-probe-20261008.md`。当前A与v02波形/片段PCM相同，无变化重复精确；B仅取消“抱”的有限TENC偏移，原生输入隔离通过并有小幅谱响应。75项测试通过；六份USTX/36份Skill及当前旧run绑定567文件保持原哈希。局部试听待评价，口型改善/唯一病因unknown；不自动修整曲、更新Skill或推进P2。
- 用户随后试听回报“没啥区别”：本次TENC取消未获可感知改善支持，不采用该B。只读核查当前自身状态并裁切原版约1:14/3:04/3:31同字“抱”作定位对照，PCM/增益保持，另两处听感unknown；不把数值谱变化当改善或自动加大参数。
- 同字对照用户回报“我听着都一样”：只记录未感知差别，不自动标三处均异常/正常。已核查本机GENC=0/falsetto未启用及pitch条件路径；有限SHFC保留vocoder F0为后续候选，尚未执行。报告depth误写偏好1已纠正为实际0.6，实验输入和结果未变；不据此改Skill、发布工程或恢复旧路线。
- 用户再次授权“下一步”后完成有限SHFC -400c条件隔离，见 `docs/lastpage-shfc-controlled-probe-20261008.md`。先前-4存储值只有-4c，被原生单位校验拒绝并保留；诊断B明确所选SHFC合法范围±1200后实现原定-4半音，发布工程不变。24帧条件偏移，variance只pitch变，vocoder F0/人工控制精确保持，全新variance11/acoustic101、A/重复精确、原生DYN/固定1.5/.7。双F0主体相近但局部40–45c检测差，不宣称实测F0固定或病因/自然度通过。84项测试通过，42工程/Skill、47运行依赖、旧run567与旧TENC104绑定保持；试听待评价，不自动扫参数、修整曲或改Skill。

- SHFC试听最新反馈：“更实了，但是有破音的情况”，位置明确“抱的字头”。当前B不采用；只读检查无文件满幅削波/特征裁剪，字头谱变化及上下文预测是候选线索，未证实破音病因。反馈和审计在独立新run，原封存实验不动；下一项候选只检验条件进入时间形状，保持字腹平台/退出及其他控制。本轮未生成新候选或改Skill/整曲。

- 用户授权下一步后完成单个SHFC进入时间C：55→145ms，提前元音80ms准备，-400c平台/退出原生精确。完整新variance11/acoustic101/vocoder，原A/重复精确，旧B明确封存复用；同增益B/C已交付。元音入口响应减小，但b RMS约-5.326dB、谱变化增大，咬字/破音/字腹听感均待评价，不采用为整曲修复。检查器浮点除法顺序误判1帧修正，精确等式/容差保持，失败与F0时基断言保留，85项测试通过。见docs/lastpage-shfc-onset-probe-20261008.md；不继续候选或改Skill。

- 用户对145ms条件进入B/C试听回报“可以”：记录为C在3:04“抱”的局部可用反馈，独立反馈run绑定对照/C工程/波形SHA；原72封存文件保持。未扩为1:27或整曲验收，未补造“完全无破音”等细分标签。本轮没有新合成、发布USTX或Skill变更。

- 用户授权下一步后完成1:27“果”独立SHFC -200c试验：约330Hz/uo/无人工三通道增量，160ms进入/70ms退出，已接受“抱”在完整A/B精确保留。全新variance11/acoustic101/vocoder、原A/重复/currentPCM精确，原生路径/手工控制/vocoderF0/DYN/1.5/.7通过。实际双F0主体相近，uo电平+0.09dB、g+1.69dB/后zh-1.99dB声明；听感待评价，不宣布病因或整曲修复。85测试/资源审计通过，旧567/116/72/接受反馈1及42工程Skill/47运行依赖保持。见docs/lastpage-guo-register-probe-20261008.md；不自动继续参数或改Skill。

- 果SHFC试听被否决：“果字没啥区别，这的咬字好像也没啥区别，而且引入新的问题，响度下降”。B不采用，保留A（已接受抱C），发布工程本来未写入B。独立反馈run保留原文/对照SHA，原67封存文件保持；uo总RMS接近但2–5kHz约-4.03dB、接口30ms约-4.20dB，代理不等于用户精确位置/感知响度真值。停止果SHFC/增益补偿，下一项先只读核查g→uo时序/映射/过渡，尚未执行。无新合成/Skill变更，不否定抱的局部接受或宣布病因。

- 用户授权下一步后完成果音素只读核查：实际g/uo词表及语言ID4匹配，uo整体token；HFA观测对原生元音起点差0.303ms、时长差约14ms，无明确大错位/吞元音证据。五处自己同字时钟保留，当前生成版1:27/3:17/3:44同MIDI64原PCM三段用于标签定位，不是因果对照，另两处标签unknown。无新合成/参数/Skill/unknown改动，已接受抱保留；不直接拆uo或缩g。见docs/lastpage-guo-phoneme-audit-20261008.md。

- 用户对三处果原PCM对照回报“中间这个可以”：word247约3:17局部可用，1:27原反馈保留、3:44仍unknown。实际新成声state比较：主体音高相近，通过处voicing略高、breathiness略低，入口差更明显；仅线索，非因果。缓存导出不等于新成声的草稿被拒绝保留，567当前run文件哈希保持。无新合成/参数/Skill修改，已接受抱保留；下一项候选有限VOIC单因素支撑，尚未执行。见 docs/lastpage-guo-positive-comparison-20261008.md。

- 用户确认研究通用规律而非继续单点修复后，完成318当前字跨条件只读研究：5个原版标签+接受抱C变体，313字听感unknown保留。接受抱voicing更低、tension更高，否定统一提高VOIC/降低TENC；同元音配对breathiness降低方向一致但未隔离。冻结6条件同剂量BREC单因素检验方案（2问题+4偏实/可用），尚未渲染，不拟合阈值或扫参数。停止先前果VOIC提案；不更新Skill或改音频，接受抱保留。见 docs/lastpage-cross-condition-study-20261008.md。

- 执行冻结六条件BREC -10单因素对照，18套新variance11/acoustic101/vocoder、Normal75/Classic25；仅fresh breathiness改变，预测/其他输入/原SHFC保持，6原A与此前波形和6重复精确。原生DYN/固定1.5/.7/PCM通过，特征裁剪0；元音RMS变化约±0.03dB，双F0中位差0.03～0.16c、最大3.20/2.44c，技术响应不是口型改善。1tick编码被独立检查拒绝后改原5tick网格，原生初始化崩溃普通同输入重试成功，草稿/失败保留；88测试通过。六组同增益A/B已交付待听感，不扫参数/改Skill/发布工程，接受抱C保持。见 docs/lastpage-brec-cohort-probe-20261008.md。

- 六组分开试听后用户回报“全部没区别”：本轮BREC -10在两个问题及四个偏实/可用条件均未获得可感知差别，不采纳B，不把数值响应当改善或写入Skill，也不自动增大剂量。限于当前剂量/条件的否定证据，不宣布整个气声通道无效；原标签/接受抱C/源unknown保持。独立反馈run绑定12份A/B人声SHA，原537封存文件精确。无新合成/参数/Skill修改。见 docs/lastpage-brec-cohort-probe-20261008.md#最新试听反馈。

## Git

- 不提交音频、模型、缓存、run输出、本机归档或绝对路径配置 `configs/local.yaml`。
- 发布前运行当前测试、检查Skill引用、验证作者包SHA及ZIP成员，再审计Git索引内容。
- 不改写既有Git历史；删除旧音频跟踪只清理当前树。本机音频与已完成工程仍保留。
