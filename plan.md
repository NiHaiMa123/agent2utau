# agent2utau 当前实施计划：自动音高 + 稳定音素对齐

更新：2026-10-31（P1.1 交付复核后）。**这是目前唯一的执行计划，目标是让 MiniMax / DeepSeek 稳定完成歌词、音符、音素时间修正。当前执行阶段：P1.2 定向修复；完成局部门禁后，允许另开独立 run 进行 P2 短句试点，不必等待整首歌全部 unresolved 由人工清零。**

> **已完成阶段与审查事实：**截至仓库 `02628796e714874cd049f3d4598d69a99f6802ca`，MiniMax 已完成 P0/P1 初版与 P1.1 的 A～G 代码/报告，包括状态机、非法延音探针、观测分级、GAME 稳定性调查、三首歌回归及 40 个 scratch 历史文件的原字节归档。P1.1 报告称本机 **336 passed**；该数量不是独立质量验收。三首歌均仍是 `incomplete`：年轮 343/349 字（6 unresolved，11 个 voiced GAME 音符未归属）、最后一页 318/318 字（`n0060` 不能合法写为 `+`，工程缺此音符）、雨爱 366/371 字（5 unresolved，12 个 voiced GAME 音符未归属）。**映射覆盖不等于音符时间准确，也不等于音素可用。**报告：[P1.1 修复记录](experiments/alignment/phoneme-alignment-p1.1-20261031/reports/phoneme-alignment-p1.1-20261031.md)，[证据目录](experiments/alignment/phoneme-alignment-p1.1-20261031/evidence/)。
>
> **当前范围锁：仅执行新增「P1.2」的代码/验证任务。**P1.1 为历史实施记录，不再按其旧提示词重新跑一遍。P1.2 达到本计划的局部门禁后，**可以在下一个独立任务**选择 10～20 条安全短句开始 P2 原生音素试点；`n0060` 等未决句必须继续隔离，不能混入 `valid` 样本。

## 一、目标、优先级与已知事实

用户试听后认为泠鸢 DiffSinger 的自动音高已经很好。新目标不是逐字复刻原唱的滑音、颤音、强弱，而是以原曲提取歌词、基础旋律和节奏，让 DiffSinger 自由发挥，生成自然、好听的演唱。

| 环节 | 当前决策 | 不确定性 |
|---|---|---|
| 人声分离 | 沿用现有分离工具，保留原伴奏 | 需要记录源偏移、分离质量 |
| GAME | 产生音符事件（时间、tone、voiced） | 不是歌词字界，也不是逐帧 F0 |
| 歌词/音符/音素 | **当前 P1.2 定向修复**：行为正确性、合法候选、真实 USTX 时间校验、未分配音符审计；通过局部验收后开启 P2 短句试点 | P1.1 已交付，三首歌仍 incomplete；**音素 patch 尚未实现** |
| 音高 | 用泠鸢 DiffSinger 自动 pitch，保留正确 MIDI tone；不默认画 PITD | 需要检查旧人工曲线没有叠加 |
| VOIC/BREC/TENC/DYN/PEXP/CLR | 暂用声库默认预测，不默认让 Agent 改 | 以后只做单因素 A/B 实验 |
| 混音 | 先原伴奏 + 人声固定增益，确认无削波/错位 | 全自动混音/母带待定 |

**禁止**自动推进旧的“Agent 整曲设计 PITD、逐句冻结表达意图、模仿原唱”流程。旧代码和研究不删除，只是不再作为默认生产入口。

## 二、目标架构：程序承担正确性，Agent 只裁决歧义

~~~text
原曲 + 已核实歌词
  ├─分离 vocals / accompaniment
  ├─GAME note events（包括休止、同字多个音符）
  ├─ASR 粗候选 + HFA 按锁定歌词对齐
  └─FCPE/RMVPE 可辅助检查错音，不直接复制音高表现
        ↓
确定性歌词字/音节 ↔ GAME 音符映射（保留 + 延音）
        ↓
生成 baseline.ustx → 当前声库 export-phonemes
        ↓
对照原唱 HFA 观测 + 原生预测 → 生成局部候选和冲突清单
        ↓
Agent 按 5～15 字窗口选择 candidate_id，或 unresolved
        ↓
程序校验 / tick 量化 / patch 写回 USTX
        ↓
真实 OpenUtau Core roundtrip + export-phonemes 再次验证
        ↓
自动音高 + 默认发声 → 渲染 → 固定增益伴奏混合 → 连听
~~~

**关键区别**：原唱唱字起点、GAME 音符跳进点、辅音准备起点、合成元音核起点，可能是四个不同时间。不能把 HFA 所有时间原封不动复制到 DiffSinger，也不能让 LLM 给出没有证据的任意绝对毫秒时间戳。

## 三、项目结构：现有代码保留，新增职责清晰的模块

已存在：
- `src/agent2utau/audio/`：解码、分离、固定增益混音。
- `src/agent2utau/transcription/game_onnx.py`：GAME ONNX。
- `src/agent2utau/analysis/`：歌词 ASR、F0 等。
- `src/agent2utau/openutau/`、`bridge/OuBridge/`：USTX、原生音素导出/渲染。
- `tests/{unit,contracts,skills}/`、`songs/`、`benchmarks/model-comparisons/20261030-lyrics-alignment/`。

**已在 P0/P1 初版中新增：**
- `src/agent2utau/alignment/` 中的 `lyrics.py`、`notes.py`、`observations.py`、`canonical.py`、`candidates.py`、`validator.py`、`baseline.py`、`pipeline.py`。
- `schemas/alignment_evidence_v1.schema.json`、`tests/unit/test_alignment_{lyrics,notes,mapping,canonical}.py`、`tests/contracts/test_alignment_evidence.py`、`agent2utau align-lyrics` 命令。P1.1 又新增 `alignment/status.py`、CLI 退出码测试、baseline/line/observations 回归、三首歌的归档证据及历史文件清单。**现行待修缺陷见 P1.2，不再将 P1.1 重做为新任务。**

**仍待创建（P2 起）：**
- `src/agent2utau/alignment/phonemes.py`、`patch.py`，以及相应原生读回校验器。
- `schemas/phoneme_patch_v1.schema.json`、`tests/contracts/test_native_phonemes.py` 和真实音素 patch/回归样本。
- `benchmarks/model-comparisons/phoneme-timing-v1/`：固定样本、参考标注、统一测评和跨模型结果。
- 如需要新的可重用 Agent skill，可独立新建 `skills/phoneme-alignment/`，**不要继续扩写旧的 singing-expression-editor 为主入口**。

已有 `compile-functions` 是旧的显式音乐表达编译器，不能改个名字当作新音素对齐器。`docs/knowledge/`、`research/`、歌曲旧 session 与完整报告保留，不重新执行 2026-10-30 的目录搬迁。新 session 继续按日期、AI 模型、run-id 命名；历史 unknown-model 不追溯。

## 四、P0：固定输入、建立无 Agent 的 baseline

1. 盘点真实命令：`agent2utau observe-source`、`export-phonemes`、`roundtrip`、`render-project`，确认当前声库、phonemizer、Core、模型版本、配置及可读输出。不得将“接口存在”写作“自动闭环已完成”。
2. 新 run 中保存 source、vocals、伴奏、locked lyrics、GAME note、ASR、HFA 的来源、SHA256、时钟原点、模型 hash、偏移；歌词以用户确认的完整文本为准，ASR 只能提示，不能静默改词。
3. 每个唱字用出现顺序分配 `syllable_id`（尤其重复字），每个 GAME 事件分配 `note_id`；保持原始 index、start、dur、tone、voiced/rest。不能仅按字面字符串关联。
4. 现有 `openutau/build.py` 是**固定 120 BPM、480 分辨率，用绝对秒映射 tick**，不是检测原曲 BPM。以全局 start/end 边界一次量化，禁止 start/duration 分别舍入产生重叠。保留 1 字跨多个音符及 `+`：年轮已有实验证明，任意合并 `+` 会严重损坏音高走向。
5. 选《年轮》《最后一页》《雨爱》的局部样本，覆盖一个字一音、多音连字、重复字、字头抢拍、短元音、休止、跨句、多音字；按用户授权才能使用现成研究资料，不拿作者曲线作为新歌的目标。

交付 `observations/manifest.json`、`lyrics_locked.json`、`notes_normalized.json`、10 个以上小样本、异常清单及 baseline 工程。**P0 不需要改音高或人工发声。**

## 五、P1：字 ↔ GAME 音符的稳定映射

程序按时间、歌词顺序、HFA 元音核/字界、ASR 粗时间、GAME 休止/音长生成**多候选单调映射**。先做确定性动态规划/最短路径 baseline，然后让 Agent 判断模棱两可的局部情况。算法、权重、时间阈值写在配置与测试里，不允许随模型更换。

硬约束：
- 字序必须完整；不能跳字、偷换字、添加字；同一音符不可分给两个唱字；一个唱字可以有连续多音符。
- `+` 只能连接前一字的延音、不能跨非法间隙。已有 build 检查要保留。
- 明确区分 AP/SP/EP、休止、和声、非唱段，不硬塞进歌词字。
- 不允许负时长、非法重叠、跨句漂移；不可确定输出 `unresolved` 而不是胡乱补齐。
- 字界不是元音核起点：允许辅音提前准备，不可把原曲辅音一律压在 GAME 音符头。

交付 `mapping.v1.json`：每字对应音符 ID、选择的候选、证据来源、未解问题；检查字符 100% 有去向（包括标记 unresolved），**绝不能把 unresolved 算成成功**。

## 五点五、P1.1：历史交付与仍待处理事项（2026-10-31 已实施，保留原验收合同）

**以下是 P1.1 执行前的历史审查基线，保留作为旧任务合同；请不要照此重复执行。最新结果及当前任务参见下方 P1.2。**

**审查基线（2026-10-31）：** `experiments/alignment/phoneme-alignment-p0p1-20261031/` 报告记录：《年轮》345/349 字已映射、4 unresolved、391/400 voiced note 已归属；《最后一页》318/318 字、368/368 note 归属，但 baseline 实际只有 **367 note**；《雨爱》366/371 字、5 unresolved、413/425 note 已归属。总计 **9 unresolved 字**；实际字/音符身份、时间误差和演唱听感均**未独立验收**。本轮保留这些原始数据和失败记录作前后对照，不用“覆盖率更高”代替正确性。

### P1.1-A｜必须修：结果状态与错误退出码（P0）

**现状证据：** `alignment/pipeline.py::run_alignment` 遇到 `problems` 会返回 `completed_with_problems`，`cli.py` 的通用退出判断未将此状态作为失败；`experiments/.../scripts/build_p0p1_artifacts.py::main` 汇总问题后仍无条件 `return 0`。此外 `pipeline.py` 生成 `clock_problems`，但没有将它并入门禁 `problems`；异常列表、schema 通过、原生成功不能混为一谈。

- [ ] 明确 **valid / incomplete / invalid**（或等价机器可识别枚举）。**valid**：全部强约束通过且无未处理必需身份；**incomplete**：存在 unresolved / 待人工处理但未发生非法写回，允许诊断产物、禁止标记正式可交付；**invalid**：语义错误/非法音符、非法延音、原生不一致，阻止后续使用该 baseline。
- [ ] CLI 的 `status` 与**实际 process exit code** 一致：invalid 必须非零；incomplete 按明确的“非完成”状态回报，若将其作为生产命令也必须非零或要求显式 `--allow-incomplete` 仅输出诊断，不能静默返回成功。批处理 `build_p0p1_artifacts.py` 同样聚合失败状态，不得常量返回 0。
- [ ] `notes.py` 的非法 duration / overlap 应按语义进入 hard fail；正常 silence gap 只作为信息。量化后相邻边界、原始时钟与 USTX 回读必须使用同一口径，不用所有 gap 一律阻断。
- [ ] 把“可生成 diagnostic baseline”与“通过生产门禁”分离；即使允许输出供调查的 USTX，也不得在 `status=valid` 下发布有非法缺失的工程。
- [ ] 注入 1 个负长音符、1 个 overlap、1 个丢字、1 个 unresolved、1 个延音非法案例；测试 JSON 状态和 shell 退出码，而非仅判断是否产生文件。

### P1.1-B｜必须修：`+` 延音被静默丢弃（P0）

**现状证据：** `alignment/baseline.py::rows_to_segments` 对非法间隙的 `+` 执行 `continue`。报告已指出《最后一页》`n0060` 间隙约 160ms，映射显示 368/368 已分配，实际 baseline 只保留 367 note，造成**映射与工程不一致**。

- [ ] 删除“发现非法 `+` 就静默丢弃”的默认行为；保留 `note_id`、`syllable_id`、原始音高和时钟。先评估是否为 GAME 错切分、合法休止、歌词重新起音、或需要新 voice part。
- [ ] 制作**有限候选**：若可以无损切 part 且新 part 的发音标注合法，则提供方案；若必须重复歌词或改变发音身份，需要明确理由与人工/Agent 选择，不能自动把 `+` 换成新唱字。不能通过强行拉长上一音符跨过 160ms 间隙掩盖问题。
- [ ] 对不能解决的情况输出 `unresolved_note_ids` 与 `baseline_status=incomplete`，阻止当作完整基线进入 P2。
- [ ] 测试前后 `mapped_note_ids` 与**实际 USTX note 对照表**一致，任何未授权减少、增加、合并或修改 tone 都失败；提供 `n0060` 的实际修复结果或保留未解决证据。

### P1.1-C｜必须修：分句/连音硬约束与候选可达性（P1）

**现状证据：** `candidates.py` 的 DP 检查原始 GAME 事件索引相邻，但没有对**同字连音的实际间隙**设置硬约束；也缺少对歌词句 ID 与音符时区的强绑定。现有候选枚举固定窗口 note budget；《雨爱》有 **7 个歧义窗口、仅 6 个候选**，不能直接说“歧义更少/映射更准确”。

- [ ] 给每个歌词句建立可审计的时间区间/锚点与只读上下文，禁止映射无证据跨入远处句子；句界尚不确定时列 `review_required`，不强行规定发行版换行必为音乐边界。
- [ ] 同字跨音符支持合法的连续延音，不得跨真实休止/超过允许间隙仍输出 `+`；根据 OpenUtau 的**实际建谱后量化结果**判断合法性。不要通过放宽间隙阈值来隐藏问题。
- [ ] 修补窗口生成：每个有歧义且需要 Agent 决策的窗口必须有 ≥1 **合法且可验证**的候选；否则明确 `no_valid_candidate` / `unresolved`，不能产生看似已解决的空窗口。
- [ ] 候选必须约束 `syllable_id`、`note_id` 在当前窗口，不能越界抢邻句；候选内部也必须满足**字序、音符单调、同字连音合法**等硬约束。候选如果仅改写已知最佳方案、没有有效可比替代，应明确“无需 Agent/无可选修复”，而不是让 LLM 猜。
- [ ] 不能仅依靠 DP 代价差宣称准确；人工检查三个歌的所有 unresolved、所有空候选和各类难例（重复副歌、同字多音、快唱、短元音、跨句）。
- [ ] 补充跨句错配、`+` 中间有 gap、单窗无方案、同歌重复字、窗口首尾不能抢音符等回归测试。

### P1.1-D｜必须修：HFA/ASR 的证据等级与歌词来源安全（P1）

**现状证据：** `observations.py::match_observations` 默认允许相同剩余数量下的 positional fallback，即使歌词文本不一致；`build_evidence` 选择 HFA 优先 ASR，却没有根据 observation match 方法区分可靠性。报告对《最后一页》出现大量初始缺失及 residual 回退匹配（203 缺、130 residual、3 positional），这些**不是精确对齐真值**。

- [ ] 为 HFA、ASR 观测明确 `exact_token / exact_text / residual_text / positional / missing` 等匹配级别，并绑定时间差、匹配范围、是否同句、来源。旧字段与新枚举可兼容，但不得默认为全可信。
- [ ] 残余或按位置配对只能作为弱建议，不能以与精确 HFA 相同的代价权重推动大位移；超阈值、跨句、重复字冲突要降级为 review/unresolved。**不要让模型或程序猜测出不存在的观察时间。**
- [ ] 复查 `match_observations` 的 `used` 跟踪：回退匹配加入 `matched` 后，未同步更新 `used`，可能把已匹配观测误报为 unused；修复同时保留完整原始 provenance。
- [ ] 歌词锁定仍以**经用户或可审计复核的实际演唱版本**为准。公开歌词仅作为候选来源，不能在没有逐字核对录音的情况下自动覆盖已锁定的歌词；`canonical.py::apply_canonical` 的 substitution 要有 diff 与批准记录。将《年轮》两处“份→分”的自动替换列为**待复核候选**，不直接以网络文字替代录音事实。
- [ ] 为不同来源匹配设计独立测试，报告各等级的数量和误差；不可用“最终有时间戳”当作 HFA 成功。

### P1.1-E｜必须做：GAME 可复现性调查与观测冻结（P1）

报告已观察到同源、同分离文件、同模型 hash、同 seed 的 GAME 事件数 **469 vs 467**。当前 `transcription/game_onnx.py` 的 `infer_chunk` 创建了 RNG 但未使用，**这并不能证明随机机制被 seed 控制；也未证明具体原因就是 ONNX 多线程**。

- [ ] 首先固定当前三首歌的输入 GAME JSON 和 SHA，后续 P1.1/P2 不偷偷重新生成，保留“固定观测集”与“GAME 稳定性调查”两条独立路径。
- [ ] 在可复现环境对相同音频/同配置进行 ≥3 次重复，记录 chunk 边界、provider、线程数、ORT 版本、环境/模型 hash、输出 SHA、事件数及逐事件差异位置。
- [ ] 仅在有实验支持的前提下评估单线程、不同执行 provider / 优化档或已知边界输入的影响；不擅自更改生产 GAME 推理语义、seed 处理或强制合并音符。确认不了根因就如实保持 `nondeterministic`，并以固定 JSON 的 hash 保证下游回归稳定。

### P1.1-F｜必须做：历史删除核查与范围控制（P1）

从上次文档提交 `1a3a5bab` 到审查版本 `9e5435a7`，对比中有 **41 个已跟踪文件被移除，其中 40 个位于 `scratch/`**，包括《年轮》《最后一页》的旧 JSON/审查收据。它们仍可从 Git 历史找回，但用户此前要求的是保留历史而非主动删除。

- [ ] 列出所有删除文件及原 Git blob SHA，判定是否为已迁移到其他**可核对**位置，不能只靠工作树 `.gitignore` 判断“已保存”。
- [ ] 对未确认已可靠备份的原件优先恢复（或建立不改变字节的归档副本与原路径映射），不批量重新清理旧实验；若确需删除已追踪副本，必须说明理由和去向，并等待授权。
- [ ] 只对这一批受影响文件做核对；不要借本轮修 P1.1 之名再次重组整个仓库或搬迁按路径+SHA 锁定的知识包。

### P1.1-G｜回归协议与放行门槛

**固定基线**：三首歌当前 GAME/HFA/歌词观测、输入 SHA、P0/P1 历史报告、原 baseline 及异常；只以**新 run**输出修复结果，原资产不可覆盖。执行模型与时间写新 session manifest（旧 unknown-model 不追溯）。

| 验收项 | 必须达成 |
|---|---|
| 进程状态与退出码 | 以注入故障验证 invalid 必失败、incomplete 不可混入 valid；批处理不能忽略子任务失败 |
| 唱字身份 | 没有无证据换词、漏字、重字；unresolved 有稳定 ID、原因和人工处理入口 |
| 延音与工程一致性 | 所有被标记 mapped 的 note 均与实际 USTX 一一对应；《最后一页》`n0060` 修复或明确 incomplete，不能丢弃后算成功 |
| 跨句、连音与窗口 | 无无证据跨句、非法 gap `+`、越界候选；全部歧义窗口有可用候选**或明确无解/需复核** |
| HFA/ASR 证据 | 精确/残余/位置回退分级，弱证据不能被当作真值；公开歌词替换经过核对 |
| GAME 固定输入 | 不改变当前生产 GAME 文件；报告重复运行差异及根因的“已证实/未证实” |
| 回归测试 | 新增单元/契约 + CLI 端到端失败码测试；本机可运行时至少对三首固定观测重跑，并保存差异摘要 |
| 保护历史 | 本轮不删除历史 run、USTX、实验数据和报告；前述 41 个删除文件逐项查证并说明 |

**本轮完成 ≠ 映射达到 100% 或音素已可用。**可以保留暂时无法解决的 9 字和其他问题，但必须确保它们不会悄悄进入“完整工程”的成功路径。验收后才进入 P2 的 native phoneme baseline 和局部 patch。不要为降低 unresolved 数量牺牲字义、音乐结构或原生可运行性。

**交付报告必须包含：**涉及的代码文件、修复前后每首歌的字/音符覆盖、所有未解字与 note ID、映射到 USTX 的逐 note 核对、候选窗口异常、HFA 可靠性分布、测试命令/实际输出、运行环境、固定输入和新产物 hash、历史删除清单、真实原生执行边界。没有运行的测试标未执行；没有音频聆听则 `listening=unknown`。执行完成即停止，**不自动开始 P2**。

## 五点六、P1.2：行为正确性与可进入 P2 的短句门禁（**下一轮唯一执行阶段**）

**范围与前置：**这一轮只做少量确定性修补、真实测例与证据产出，禁止新的全曲重构、批量改谱、重新跑 GAME、盲目调参数或继续堆报告。以 P1.1 的 `02628796` 代码、`experiments/alignment/phoneme-alignment-p1.1-20261031/evidence/` 与原输入 SHA 作为只读对照；修复写入新 run/session `phoneme-alignment-p1.2-<日期>`，不要覆盖 P0/P1 或 P1.1。**当前三首歌 incomplete 是已知状态，不要求 P1.2 自动解决全部 11 个 unresolved 字或 `n0060`。**

### P1.2-A｜修正“弱观测降权”的真实行为，而不只是权重数值（必须）

**待验证/修复：** `src/agent2utau/alignment/candidates.py::_assign_cost` 目前使用 `abs(anchor_s - note.start) / (time_scale_s * anchor_weight)`，把 `anchor_weight` 从 1 降为 0.25，**相同误差惩罚反增为 4 倍**；`expected_dur_s` 时长惩罚还未按置信度一致处理。这可能使不可靠 HFA/ASR 证据比可靠证据**更强地推动 unresolved**，与“弱证据影响小”的目标不一致。

- [ ] 将**观测置信度**与**匹配候选的物理可行性**分开：低置信度只应减轻/限制该观测对于最佳映射的影响，不应无根据地变成更强的绝对距离约束。可采用 `weight * robust_time_residual` + 相应加权时长项，或另一种有对照证明的数学设计；不得把 `weight=0` 意味着强罚或偷偷伪造时间。
- [ ] 将过大时差、跨句、重复字等视为**独立的可信约束或复核信号**，不让弱观测靠自身不可信时间设定一个绝对硬边界。未观测的 syllable 以次序/句界/其它可靠信号作候选，必要时 unresolved。
- [ ] **证据统计按来源与匹配阶段分组。**当前报告《最后一页》的 `203 observation_missing / 130 residual / 3 positional` 为汇总日志，可能混合 HFA/ASR、第一轮缺失与第二轮补配，**不能据此直接宣称 HFA 有 203 个最终缺锚**。逐条分解 `hfa.exact_text / hfa.positional / hfa.unmatched` 与 `asr.exact_text / asr.residual_text / asr.positional / asr.unmatched`；最终锚点分布从 `mapping[].evidence.anchor_source/anchor_level` 另行汇总，避免把初始匹配缺失算成最终失败。
- [ ] 加入**反事实行为测试**：同一真实音符/歌词，给出正确的精确锚与明显错误的 positional/residual 锚；精确锚可影响选择，弱错误锚降权后不应反向拖走正确匹配或更容易制造 unresolved。用三首歌的冻结输入列出修复前后 `syllable_id → note_ids` 差异，不以 `assert weight<1` 代替决策验证。

### P1.2-B｜让“无合法候选”有可审计含义（必须）

**待验证/修复：** `candidates.py::_local_paths` 在枚举时受到 `max_paths`/深度优先遍历顺序限制，外层先按 `max_options` 收集并截断再过滤 `legal`；因此 `no_valid_candidate` 可能是“搜索预算内没找到”，不等于“数学上没有合法方案”。

- [ ] 将**合法性判定前置到转移/枚举**（尤其 `+` 间隙、休止、句界及窗口 note budget），只对**合法候选**计数，或提供 bounded best-first / K-best 搜索；保持可确定复现、可限制复杂度，不做全曲指数暴搜。
- [ ] 不可直接把“前 K 个候选均非法”标为 `no_valid_candidate`；区分 `no_legal_solution_proven`、`search_budget_exhausted`、`legal_alternatives_available`、`only_baseline` 等状态，**只有搜索能证明无解时才宣称无解**。预算耗尽时列 `review_required`，且整个窗口仍是 incomplete。
- [ ] 复查 `_local_paths` 的前缀/后缀代价下界、窗口 cursor 和候选 `total_cost` 口径，确保所有候选内部满足同字多音、时序、句界规则，未被枚举顺序人为偏置；不得生成越界 ID 或让多个重叠窗口给出互相冲突的写回。
- [ ] 用《最后一页》`w02`（`s0045–s0049`，含 `n0060`）做定点回归：打印“约束导致无解”还是“搜索预算不足”，验证 `max_options/max_paths` 扩大后的结论是否一致。**仍非法则保留 unresolved，不强行用延长、合并、重复歌词解决。**

### P1.2-C｜真正检查 USTX 的 note ID、绝对时间和音高（必须）

**待验证/修复：** `alignment/baseline.py::verify_ustx_notes` 目前通过歌词 `SequenceMatcher` 匹配，比较数量/歌词/`tone`，**没有检查音符 position 和 duration**。相邻或重复 `+` / 相同歌词容易被错配；`one_to_one=true` 不代表时间轴正确。谱面 builder 还可能在 ±1 tick 的间隙处调整前音时长。

- [ ] 写出显式的 `note_id/syllable_id → (part_index, note_index, lyric, absolute_start_tick, end_tick, duration_tick, tone)` 构建账本；如 USTX 原生结构不保留 ID，使用建谱前后有稳定键的 sidecar（而非仅依赖重复歌词的文本匹配）重建身份。
- [ ] 使用 `voice_parts[].position + notes[].position` 计算**绝对起点 tick**，逐一比较目标 `sec_to_tick(original.start/end)`，校验 `duration`、终点、音高、歌词、part 位置、单调性和所有 `+` 的合法前驱；把 builder 经授权的 ±1 tick 贴合改动单独记录成可审计差异，不要默默通过。
- [ ] `one_to_one` 仅当身份、时钟、音高、歌词、数量**全部**满足定义才为 true；异常报告包含 `shifted_note_ids`、`duration_changed_note_ids`、`missing/extra/retuned` 和允许/非法的偏差，状态门禁据此判定。不能把“不完整但已记录缺失”当成全谱验证成功。
- [ ] 加失败注入测试：note 开始时间错 1 拍、时长改变、part 整体漂移、两个相同 `+` 互换、一处重复歌词，必须能抓住；保留 `lastpage n0060` 的缺失记录，不能因新验证策略掩盖原错误。必要时调用真实 Core inspect/roundtrip，**不得把纯 YAML 对照说成原生验收**。

### P1.2-D｜所有未归属 voiced GAME 音符必须有去向（必须）

**现有数据：**年轮 400 voiced/389 assigned，**11 个未归属**；雨爱 425/413，**12 个未归属**；最后一页 368/368，然而 `n0060` 仍属已归属但不能合法写谱。P1.1 状态机直接检查 unresolved syllables/extends/review，而**未单独给每个 unassigned voiced note 建立有理由的去向记录**。

- [ ] 以固定 GAME note IDs 导出 `unassigned_voiced_notes.json`：每条包含时间、时长、tone、前后字/休止/句界、可引用 HFA/ASR、分类和 reason_code。分类可用 `probable_false_positive` / `rest_or_nonlead` / `candidate_melisma` / `needs_alignment` / `unresolved`，不允许“因为 DP 跳过了就不算问题”。
- [ ] 自动伪音符判定必须有**可核对的独立证据**与测试；没有证据的保持待审，不能默认删除，也不能为凑覆盖强塞给某个字。`unassigned` 不一定都是错误，更不能强制 100% 分配以掩盖 GAME 过切分。
- [ ] 将未审的 voiced note 纳入生产状态门禁，并且**按 song/segment 分开**：整曲 `incomplete`，但未接触这些 note/不触及非法 `+` 的干净短句可独立判为可做 P2 试点的候选。决不把有漏音的整曲宣称 valid。
- [ ] 分别对年轮 11、雨爱 12、最后一页 `n0060` 建清单并统计分类数、未解决数，不以覆盖率百分比替代逐 ID 证据。

### P1.2-E｜基础 MIDI 音高取整：隔离 A/B，不自动全曲换规则（必须做调查）

**已复核的冻结 GAME 数据：**目前 `openutau/build.py::to_ustx_tone()` 使用 `int(tone)` 截断；与 `round(tone)` 比较，年轮 **143/400（35.8%）**、最后一页 **144/368（39.1%）**、雨爱 **265/425（62.4%）** 的 voiced note 相差 1 个 MIDI 半音，合计 **552/1,193（46.3%）**。两种做法产生大量不同，**但这不是“取整必然错”的证据**。

- [ ] 不直接改动已有 `to_ustx_tone()` 生产语义，不覆盖历史 USTX；在新实验脚本与短句副本中分别生成 `truncate`/ `round` 的 A/B（同一 GAME/HFA/音频、音符身份/起止时间，只有 tone 量化不同）。
- [ ] 先核对 GAME `tone` 的真实定义与输出分布，特别是 0.99、0.01 附近的值；用可访问的原曲 F0（FCPE/RMVPE 等）**仅验证基础音高**，结合人耳和已知旋律判断 MIDI 半音差，不能复制原唱颤音或逐帧 pitch 曲线。
- [ ] 报告至少按三首歌汇总：全部 1193 voiced 音符的取整差异分布、偏差方向、异常音区、随机抽样和高差异短句的人工/音频证据；若 FCPE/RMVPE 与 GAME 矛盾，要标 uncertain 并核查 octave/分离/失声，不直接任选一个当真值。
- [ ] 给出“保持截断 / 改四舍五入 / 用带置信度纠错”的**证据导向建议**，但本轮不替用户决定生产策略；如暂无足够证据，明确结论 `undetermined`。自动音高仍由 DiffSinger 预测，P1.2 不画 PITD。

### P1.2-F｜局部放行与 P2 试点样本选择（只建立门禁和清单，不在本轮启动 patch）

- [ ] 选择 **10～20 个跨三首歌的短句**（约 5～15 字/段，包含普通句、连音、重复字、休止边界、短元音等），优先采用既有 `samples/` 与新 P1.2 结果；可适当选更长片段让前后音素上下文完整。
- [ ] 每句输出 `segment_id`、所需 `syllable_id/note_id`、歌词/音符时间范围、前后上下文、输入 hash、`local_gate`（`ready_for_p2_native_baseline` 或 `blocked`）、以及明确的阻断理由。**局部放行 ≠ 整曲放行**。
- [ ] 放行要求：片段内及边界上下文无未解唱字/未审核 voiced note/非法 `+`；歌词文字已核对、候选映射身份稳定、原声源 SHA 固定、note 真实 USTX tick/音高/时长一致，无跨句未知漂移。涉及全曲共享 voice part、上下文 phonemizer 影响时保留邻句，只把目标片段作为可编辑范围。
- [ ] **P1.2 本轮停止于“样本与真实校验报告”。**下一轮 P2 试点才使用泠鸢当前声库 `export-phonemes` → 原生基线 → 选少量确有问题的边界 → schema patch → 真实 Core roundtrip/再导出/试听。P2 样本可以先没有人工问题修正，只验证原生时钟读取闭环；禁止给全部音符默认生成改写。
- [ ] 用户尚未确认 `n0060`、“份/分”、发行版分句与生产 tone 取整口径；**这些决策继续 pending，不阻止与其无关的局部 P2 试点**，但涉及的句子一律 blocked。P2 不提前启动、也不作整曲可交付声明。

### P1.2-G｜针对性回归、产物和停止条件

- [ ] 新增能反证上述缺陷的自动测试，不只是 schema/已有 336 项回归：弱证据与强证据的**最终映射差异**、候选搜索预算变化、真实 USTX 时间/ID 故障注入、未归属 voiced note 的状态门禁、截断/四舍五入的 A/B 纯量化断言、局部门禁边界案例。
- [ ] 跑现有 `pytest`、CLI 状态测试和 repository 检查；有条件时在 Windows 的真实 OpenUtau 上做短句 inspect/roundtrip。每条记录**执行环境、实际输出、失败案例**，没有执行不能写 passed。
- [ ] 重新跑同一冻结三首歌并对比 P1.1：映射差异逐 `syllable_id → note_ids`、候选分布、`unresolved`、未归属 note 分类、非法 extend、起止 tick 偏差、`local_gate` 清单。不得仅凭未解字减少或总覆盖率上升认定改进。
- [ ] 保留 `docs/archive/legacy-scratch/` 原 SHA 字节；归档清单表明原 40 个 scratch 文件的本地工作副本中 **28 个已与历史提交不同**，核查工作副本是否另有安全备份，不擅自覆盖这些更新后的本地工作件；不删除历史测试/歌曲/session、知识包。
- [ ] 提交 `experiments/alignment/phoneme-alignment-p1.2-<日期>/` 的脚本、manifest、报告和必要的**合规文本证据**；有版权限制的完整歌词、原曲、wav/USTX 等继续留在本机并列路径+SHA。报告明确 `tests_observed`、`native_verified`、`listening_status`、`blocked_segments`，禁用“全部问题解决”这类无证据结论。

**通过定义：**A～E 缺陷被针对性回归覆盖且没有新的非法映射；未归属 voiced note 全部显式登记（允许待审）；有一批局部门禁严格通过且可回查的短句。若有阻断也可如实结束 P1.2、列出 blocker，**不要制造通过结果或清空 unresolved**。完成后立即停止，不自动执行 P2。

## 六、P2：P1.2 局部放行后的核心工作——音素分配与时间修正

**核心原则：原生预测先行，有限修改优先。P2 可先在 P1.2 局部放行的 10～20 个短句上试点，并不要求三首整曲达到 valid。**须完整保留冻结输入与邻句，只编辑通过门禁的目标范围；未授权的 `n0060` 等问题继续 blocked。P2 试点验收后，才考虑逐句扩大到整曲。

1. 使用映射结果建无人工 PITD 的 `baseline.ustx`，调用当前泠鸢声库 `agent2utau export-phonemes --project ... --out ...`。读取真实 token、phoneme index、与唱字/音符关联、时序。多音字/组合韵母采用声库当前 phonemizer 的符号与词典；若不支持，标 unsupported，禁止模型发明 token。
2. HFA 按锁定歌词得到的“原唱观测”与原生“合成默认预测”对照。将问题分 A（原生正确、不修改）、B（局部音素边界/字头/元音核确实异常，可提出有限修正）、C（歌词/谱面/声库支持冲突，回到 P1 或人工检查）。
3. 按缺字、错字、吞音、抢拍、辅音准备、元音主体被挤压的优先级修正；不要把正常的声库演唱时序强迫还原为原唱的逐音素时间。
4. 通过程序创建的 `candidate_id` 选择新边界，Agent 只返回 ID 和简短 reason_code；不得直接生成随意的绝对秒值。对于未知，保留原生时钟并标 unresolved。
5. patch 通过 `note_id + syllable_id + phoneme_index` 精确定位，先在真实 Core 中核实 USTX `phoneme_overrides` 字段、offset 与 duration 的语义，绝不只凭 YAML 字段名猜测。编译时校验整数 tick、正时长、音素次序、同字和相邻字窗口。
6. **真实 roundtrip**：写入一个工作副本→重新 `export-phonemes`→逐项检查 before/after 与允许范围。变更音素上下文后应重建必要的模型预测/缓存并渲染；检查任何受影响邻句。未跑真实原生导出只能标 proposed。
7. 每个修改存：原时钟、原唱观测、原生基线、候选 ID、选择理由、写回后真实时钟、测试与 A/B 听感。音高 tone、歌词、非目标窗口的既有用户接受内容不得发生未授权变化。

交付 `phoneme_baseline.json`、`phoneme_patch.v1.json`、`phoneme_after.json`、`native_roundtrip_report.json`、`unresolved.json`、短句 A/B 工程/试听索引。**任何 Core 不一致、时钟非法、消字重字或非授权修改 → hard fail，禁止称通过。**

## 七、P3：给 MiniMax / DeepSeek 的结构化决策协议

LLM 不读取整个仓库的旧制作记录，不负责直接拼装全曲 USTX。每次只获得 5～15 字、前后 1～2 字只读上下文、稳定 ID、有限候选列表、来源摘要和必要的可访问音频窗口。

示意 patch（schema 与实际字段仍需实现并测试）：

~~~json
{
  "schema_version": 1,
  "segment_id": "s03",
  "input_hashes": {"score": "sha256:...", "lyrics": "sha256:..."},
  "decisions": [
    {
      "syllable_id": "s0018",
      "note_ids": ["n0042", "n0043"],
      "operation": "choose_mapping",
      "candidate_id": "map:s03:option2",
      "reason_code": "same_syllable_melisma"
    },
    {
      "syllable_id": "s0019",
      "note_ids": ["n0044"],
      "operation": "choose_phoneme_boundary",
      "phoneme_index": 1,
      "candidate_id": "native-hfa:s03:option4",
      "reason_code": "consonant_vowel_transition"
    }
  ],
  "unresolved": []
}
~~~

Agent 的输出只能包含白名单操作、已存在的 note/字/phoneme/candidate ID；不允许自造音素或毫秒数字。`confidence` 若记录，只是自报，**不作为质量证明**。

运行顺序：
1. 工具提供候选和约束，LLM 一次给出决策，不得让它同时画 pitch、调整声线和混音。
2. JSON Schema + 引用 ID + source SHA + 单调性 + 原生 token 词表 + 合法时间 + 修改隔离由程序检查。
3. 失败时只返回**错误码和局部证据**，让同一模型修复失败项；最多重试 2 次。不通过标 unresolved，进入人工复核，**禁止用全曲重新生成覆盖成功段落**。
4. 固定提示词、候选生成程序、样本、工具权限、temperature、模型版本/思考档位；每次记录耗时、tokens、尝试次数、输入/输出 SHA。保证跨模型唯一变化是 Agent 决策器。

门禁分级：Hard fail（词/音符/音素 ID 异常、漏字、重叠、负长、+ 断链、超界、SHA 变化、原生回读失败）；Review（HFA/ASR 与 GAME 冲突、多音字/极短元音、上下文变化）；Info（正常微小时差、原唱表现与模型自动音高不同）。不能用超宽松阈值刷成功率。

## 八、P4：跨模型回归和真实验收

复用现有 [跨模型歌词时间轴基准](benchmarks/model-comparisons/20261030-lyrics-alignment/)，新增 `phoneme-timing-v1`。先以人工复核的字界/音素局部参考和**真实原生输出**构建同一标注集；不允许拿任一模型输出充当其他模型真值。建议开发阶段覆盖 ≥30 个有代表性的短片段，再保留未调参的歌曲/片段作留出；未取得标注前不声称已经达标。

**统一指标**：
- 缺失/新增/错位唱字、note 归属错误、+ 错配：目标是**0 个未披露错误**。
- 对可人工定位字界统计绝对偏差 median / p90；首版工程目标 median ≤50ms、p90 ≤120ms，按高歧义类型分别报告并依据试听复核调整，不得伪称实测已达成。
- 真实原生音素序列/合法时钟/非授权字段差异：非法写回目标 0。
- 同输入模型重复 3 次：Schema 通过率、实际验证成功率、自动修复次数、patch 稳定性、人工介入率；报告失败样本全体。
- 运行成本 tokens、工具时间、渲染次数；用户试听吞字、抢拍、辅音清晰度、连贯性和自然度单独标注。

**对比组**：无 LLM 的确定性 baseline；MiniMax；DeepSeek；GPT-6.1 Sol / Gemini 4 参照。统一输入、工具、评分、音乐句，不给可靠模型特殊人工帮助。若小模型相对 baseline 无提升，应缩小 Agent 职责而非加长 prompt。不能仅通过模型自称“处理完成”宣布胜利。

## 九、P5：其它参数与混音先作为未来研究

- **自动音高**：只保留正确 note tone + 当前声库内置 pitch；检测旧 PITD/vibrato 是否冲突、PEXP 是否实际支持。年轮自动音高与辅音时段已有独立实验，可用于分析，但不硬编码为所有歌曲的通用技巧。
- **其它控制**：默认 VOIC/BREC/TENC/DYN/CLR/PEXP 不自动改；只有特定句用户明确反馈问题、当前声库支持、变量隔离且可做 A/B 时，再比较 Agent 是否真的优于默认预测。
- **混音**：当前 `src/agent2utau/audio/mix.py` 仅固定增益混合。先检验人声/伴奏偏移、峰值、削波及可听平衡；不要将“不用调音”当事实，也不要凭空决定要装自动母带。整曲歌词时间稳定后再比较可复现的自动响度/EQ/压缩或现成开源基座。

## 十、MiniMax 执行顺序与交付格式

**P0/P1 与 P1.1 代码及报告已完成，整曲仍 incomplete**。**下一轮只执行 P1.2（A～G）**：弱观测权重的行为性修复、候选枚举合法性/预算、USTX note 身份和绝对时钟验证、未分配 voiced GAME note 审计、tone 截断与四舍五入的隔离对照、10～20 个短句局部门禁清单。测试和证据写独立 P1.2 run，完成即停止。**再下一轮**才是 P2 短句试点：真实声库 phoneme baseline、小片段 patch 与 native 往返；与 `n0060` 等未决问题无关的可靠短句可先推进，但不能把局部 success 宣传为整曲 valid。之后才开展 P3/P4 的 MiniMax、DeepSeek 结构化决策与跨模型基准；整曲听感验证通过后再讨论 P5。

每轮提供：修改文件清单、运行命令和环境、输入/输出 SHA、真实测试结果、未完成的字 ID、是否经过原生 roundtrip、试听状态、下一轮最小任务。**不删除原件、不迁移旧 session、不启动未授权 CI、不自动多 Agent。**

复制给执行 Agent 的起始提示：

> 读取根目录 plan.md，**本轮仅执行「五点六、P1.2」A～G，不要重新执行 P0/P1/P1.1，也不要提前做 P2 patch**。先以行为测试修复 `_assign_cost` 的低置信度 HFA/ASR 锚点惩罚方向，并分开统计 HFA/ASR、初始缺失与最终匹配；再修合法候选的搜索顺序/预算，定点复核最后一页 w02，不能把预算耗尽称为数学无解。改 `verify_ustx_notes` 为按稳定 note ID 校验 USTX 的绝对起点、时长、终点、歌词、tone、part；登记年轮 11、雨爱 12 个未归属 voiced note 的来源和状态。隔离对照 `int(tone)` 与 `round(tone)`，用原曲 F0/短句试听核实，不自动改生产取整策略。最后选择 10～20 条没有跨句/延音/未归属等阻断的短句出具 `local_gate`，为**下一轮** P2 原生音素试点准备。用冻结 SHA 和真实测试记录前后差异，修复失败也必须如实记录；不画 PITD、不改声线/混音、不删除旧资料。提交 P1.2 报告后停止。

历史原计划： [旧表1](docs/archive/legacy-plans/plan-table1-pre-autopitch-20261031.md)、[旧表2](docs/archive/legacy-plans/plan-table2-pre-autopitch-20261031.md)、[上轮目录整理](docs/archive/legacy-plans/PROJECT_REORGANIZATION_PLAN_20261030.md)。
