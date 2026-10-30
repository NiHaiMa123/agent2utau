# agent2utau 当前实施计划：自动音高 + 稳定音素对齐

更新：2026-10-31。**这是目前唯一的执行计划，目标是让 MiniMax / DeepSeek 也能可靠完成歌词、音符、音素时间修正。**

## 一、目标、优先级与已知事实

用户试听后认为泠鸢 DiffSinger 的自动音高已经很好。新目标不是逐字复刻原唱的滑音、颤音、强弱，而是以原曲提取歌词、基础旋律和节奏，让 DiffSinger 自由发挥，生成自然、好听的演唱。

| 环节 | 当前决策 | 不确定性 |
|---|---|---|
| 人声分离 | 沿用现有分离工具，保留原伴奏 | 需要记录源偏移、分离质量 |
| GAME | 产生音符事件（时间、tone、voiced） | 不是歌词字界，也不是逐帧 F0 |
| 歌词/音符/音素 | **P0–P3 最高优先级**，确定性映射 + Agent 局部消歧 + 原生验证 | 尚未实现一键闭环 |
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

**待创建**，并非当前已经实现：
- `src/agent2utau/alignment/`：`lyrics.py`（锁定歌词/编号）、`notes.py`（GAME 归一化和音符映射）、`candidates.py`（HFA/native 候选）、`phonemes.py`（声库符号与映射）、`patch.py`（局部覆写）、`validator.py`（强制校验）。
- `schemas/alignment_evidence_v1.schema.json`、`schemas/phoneme_patch_v1.schema.json`。
- `tests/unit/test_alignment_*.py`、`tests/contracts/test_native_phonemes.py`。
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

## 六、P2：当前最高价值工作——音素分配与时间修正

**核心原则：原生预测先行，有限修改优先。**

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

**第一轮只做 P0 + P1**：实测已有工具→规范化 ID/时间→实现不含 LLM 的映射 baseline→有测试与 bad cases。禁止重做歌曲/动 PITD/混音。第二轮 P2：真实声库 phoneme baseline + 小片段 patch + 原生写回与验证。第三轮 P3/P4：为 MiniMax 和 DeepSeek 添加 schema 与局部候选决策、修复门禁、跨模型基准。最后完成一首“自动音高 + 默认发声 + 固定混音”连续试听，才讨论 P5。

每轮提供：修改文件清单、运行命令和环境、输入/输出 SHA、真实测试结果、未完成的字 ID、是否经过原生 roundtrip、试听状态、下一轮最小任务。**不删除原件、不迁移旧 session、不启动未授权 CI、不自动多 Agent。**

复制给执行 Agent 的起始提示：

> 读取根目录 plan.md，仅执行 P0～P1。不要按历史计划画 PITD，不改旧歌曲工程、VOIC/BREC、混音；先盘点现有 GAME、HFA、OpenUtau 原生接口并给字/音符稳定 ID。实现确定性 baseline、单调映射与测试。每个歧义窗口 5～15 字、候选必须由代码生成；失败保存 unresolved。不要虚报 Core 测试与听觉验收。完成本阶段即停止并报告。

历史原计划： [旧表1](docs/archive/legacy-plans/plan-table1-pre-autopitch-20261031.md)、[旧表2](docs/archive/legacy-plans/plan-table2-pre-autopitch-20261031.md)、[上轮目录整理](docs/archive/legacy-plans/PROJECT_REORGANIZATION_PLAN_20261030.md)。
