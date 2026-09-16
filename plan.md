# agent2utau — 基于本机资源的 Agent 一键翻唱计划

> 修订日期：2026-09-15。目标：用户在 Agent 中说“用泠鸢翻唱这首歌”，Agent 调用本地工具，以已安装的泠鸢 DiffSinger + OpenUtau 输出完整翻唱和可编辑工程。
>
> 本文是实施计划。已完成的是资源与配置核对，尚未实现 CLI、自动渲染或《年轮》翻唱；文中的命令、目录和接口均为待实现约定。
>
> **进度更新（2026-09-16）**：M0/M1 已验收（commit 390edf6：doctor、inspect-reference、migrate-phrase、a2u-bridge 无头渲染、roundtrip、render-smoke）。M2 进行中：`cover` 已跑通《年轮》主歌第一段闭环（分离→F0→LRC对齐→音符→USTX→渲染→混音→评价），实测 CPU 可用；faster-whisper 对歌声转写幻觉严重，暂以 LRC 时间轴 + onset 对齐替代；剩余工作为更大段落覆盖、AP/换气、音高校准收紧与完整评价报告。

## 1. 需求与“一键”的定义

用户入口是 Codex、Grok Build、Claude Code 等能够调用本机工具的 Agent。用户只需给原曲路径，默认使用本机泠鸢声库；Agent 完成检查、运行、诊断、有限重试和结果交付。CLI 是这些 Agent 共用的执行接口。

目标交互：

```text
用户：用泠鸢翻唱 E:\data\music\年轮 - 张碧晨.flac
Agent：读取配置 → 检查环境 → 运行翻唱 → 检查结果 → 必要时修正 → 返回 WAV、USTX 和报告
```

目标命令（PowerShell 单行示例）：

```powershell
agent2utau cover "E:\data\music\年轮 - 张碧晨.flac" --singer yousa --json
```

- 首次环境准备与日常翻唱分开。依赖、模型、路径和渲染适配通过检查后，日常运行不要求逐音符编辑、手动打开软件或点击导出。
- 歌词、伴奏、干声、MIDI/USTX、音色偏好均可选；只有原曲的流程必须独立通过验收。
- 可选参考工程属于加速路径，不能用参考工程通过测试来代替“仅音频输入”的验收。
- Agent 负责选择策略和解释证据；可重复执行的程序负责信号处理、工程修改与质量检查。
- 默认生成可靠初稿并自动修正明显问题；对低置信度歌词、分离串音等保留明确状态，不声称所有歌曲一次达到专业调校水平。

## 2. 已核实的本机资源

以下来自本次文件、配置、日志与硬件查询；“存在”与“实际运行通过”分别记录。

### 2.1 资源清单

| 资源 | 实际位置 / 内容 | 对实施的影响 |
| --- | --- | --- |
| 仓库 | `E:\project\agent2utau`，修订前只有 `plan.md` 与 Git 元数据 | 尚无 pipeline，不把设计接口当成现成功能 |
| OpenUtau | `E:\software\OpenUtau-win-x64 (6)\OpenUtau.exe` | 复用这套安装，先固定版本 |
| 应用版本 | `0.1.570.4`，commit `9699944ead5a3b27b59bdf5a35f73fada8c11b7b`，Alpha | 使用匹配版本的工程与源码作基准，避免跟随 master 改变行为 |
| 声库 | `E:\software\OpenUtau-win-x64 (6)\Singers\YousaV1.65b` | 当前 singer ID 为 `YousaV1.65b` |
| 参考工程 | **`E:\data\project_opentuau`** | 用户消息中的 `E:\data\project\_opentuau` 不存在；已找到这一路径下的 5 个工程 |
| 测试原曲 | `E:\data\music\年轮 - 张碧晨.flac` | FLAC STREAMINFO：44,100 Hz、双声道、16 bit、12,105,628 samples，约 274.504 秒 |
| 真人歌曲 | `E:\data\music\泠鸢`，10 个 FLAC | 用于演唱与音色参考，尚未做听感或音频特征分析 |
| GPU | NVIDIA GeForce RTX 5080，16,303 MiB，驱动 591.86 | 有本地加速资源，但 ONNX/PyTorch 实际设备兼容性仍须实测 |
| 运行工具 | PATH 可找到 `uv`、`.NET SDK 8.0.424 / 10.0.400` | 应用自带 net10.0 runtime；构建适配器需核对实际依赖 |
| 音频/Python 工具 | 当前 PATH 未找到 `python`、`ffmpeg`、`ffprobe` | 不等于机器完全未安装；需后续探测或准备项目专用依赖 |

本次 `uv python find --offline` 因默认缓存目录权限失败，不能据此判定 Python 缺失。后续将 uv 缓存、虚拟环境、模型缓存放在本项目可写目录，记录实际解析到的解释器与工具路径。

### 2.2 参考工程不是可以原样运行的当前版本模板

| 工程 | USTX 版本 | 旧 singer ID | 音符条目数¹ | 特别注意 |
| --- | --- | --- | ---: | --- |
| `雨爱-有参by白烁.ustx` | 0.7 | `yousaV1.56` | 638 | 顶层 bpm=120，`tempos[0]`=80；多声轨 |
| `花海+4-有参by白烁.ustx` | 0.9 | `yousaV1.56` | 564 | 顶层 bpm=150，`tempos[0]`=75；含旧升调音频引用 |
| `江南-有参by白烁.ustx` | 0.9 | `yousaV1.56` | 654 | 含指向父目录的音频引用 |
| `最后一页-有参by白烁.ustx` | 0.9 | `yousaV1.56`，另有 `nsf` 轨 | 1,208 | 不能把所有轨都替换成泠鸢 |
| `极星流浪夜有参.ustx` | 0.7 | `yousaV1.53` | 1,074 | 多个歌唱轨，先辨认目标轨与声部 |

¹ 按文本 `tone:` 字段统计，包含各轨与 AP/SP 等音符，不是有效歌词字数；后续以正式解析结果为准。

已发现的兼容性问题：

1. 5 个工程共 14 个 `relative_path` 音频引用，在相对于工程解析的路径上全部不存在。目录中只有 USTX，没有配套原唱/伴奏/成品；可复用音符和调校结构，不能宣称具有成对训练或音频评测数据。
2. 旧工程音色名为 `01:Bright / 02:Cute / 03:Normal / 04:Whisper / 05:Classic`。本机自动保存工程的 `voice_color_names` 顺序为 `Yousa_Bright / Yousa_Classic / Yousa_Cute / Yousa_Normal / Yousa_Whisper`，而声库 dsconfig 中的 speakers 顺序又不同。
3. 必须按音色名称语义迁移 `clr`、`cl01…cl05` 及关联字段，并核对当前 renderer 的实际映射。只替换 singer ID 或按索引照抄会有选错音色的风险。
4. `expressions` 注册了某参数，不代表这个声库支持，也不代表工程实际画了该曲线。统计时区分参数定义、轨级设置、音素参数、part 曲线及其非默认值。
5. 工程有拼音歌词、`+`、`AP`、`SP`，并有 `pitd`、`brec`、`voic`、`tenc`、音色曲线等真实用例。优先研究这些已有结构。
6. 时间轴不能只读顶层 bpm。以当前 OpenUtau 加载后的 tempo map 为准，处理 part 起点、note 相对位置、前导静音和格式迁移。

### 2.3 当前声库的实际能力

由 `character.yaml`、各级 `dsconfig.yaml`、vocoder 配置、文件清单和本机自动保存工程核对：

- singer：`YousaV1.65b`；renderer：`DIFFSINGER`。
- 默认 phonemizer：`OpenUtau.Core.DiffSinger.DiffSingerChinesePhonemizer`。
- 声学模型：`0818_no_shuffle.onnx`；采样率 44,100 Hz，hop size 512。
- 已有 `dsdur` 的 linguistic/duration、`dspitch` 的 linguistic/pitch、`dsvariance` 的 variance 模型。
- 本地 vocoder：`dsvocoder\yousa_vocoder_FT_1002_pc_nsf_wm.onnx`，并有 `vocoder.yaml`。
- 五种 speaker：`Yousa_Bright`、`Yousa_Cute`、`Yousa_Normal`、`Yousa_Whisper`、`Yousa_Classic`；相关 `.emb` 文件存在。
- 配置启用 key shift、speed、breathiness、voicing、tension；未启用 energy、falsetto。不要仅因旧工程有 `ene` 就生成 energy 控制。
- `languages.json` 有 en/ja/ko/zh；MVP 仍以中文为范围，不据此保证其他语言已验收。
- `prefs.json` 中 DiffSinger steps=20、pitch steps=10、variance steps=20；`OnnxRunner` 为空。它们是现有偏好，不是已验证的 GPU 执行设置。
- 模型 `max_depth=0.6`，偏好 `DiffSingerDepth=1`；含义、缩放和截断规则须按对应版本实现确认，不能直接把其中一个值抄成另一个参数。

日志显示应用启动并加载过 Yousa；本次未触发合成，没有自动导出成功证据。环境报告必须分开记录 `files_found`、`singer_loaded`、`render_passed`、`automation_passed`。

## 3. 三类资源如何发挥作用

| 来源 | 主要提供 | 使用边界 |
| --- | --- | --- |
| 《年轮》原曲 | 歌词、旋律、时值、曲式、伴奏和主要演唱走向 | 不迁移张碧晨的绝对响度、混响或分离噪声 |
| 大佬 USTX | 工程结构、延音与换气写法、pitch/表现参数用法、音色切换方式 | 先迁移再统计；不同歌曲的逐点曲线不能直接套到《年轮》 |
| 泠鸢本人 10 首歌曲 | 可选音色比较、换气、滑音、颤音和句内强弱的统计参考 | 是混音歌曲，不能当干声；不是《年轮》的逐帧目标，也不保证形成唯一“泠鸢风格” |

真人歌曲清单：几分造作、我的心是不夜城、大海带不走、待我回返、我的故事未写完、小柳儿、你别忘、萤梦 ver.2022、大喜、群青。

实现两级参考使用：

- **基础级**：直接使用现有声库与其时长/音高/表现预测；从已迁移 USTX 提取保守参数范围，短句比较五种音色，形成初始 preset。`Yousa_Normal` 只作初始候选，不把默认索引 0 当成 Normal。
- **增强级**：选择若干适合《年轮》的真人歌曲片段，分离后提取带置信度的统计，形成 `style_profile.json`；比较基线和候选合成，调整表现强度。首次分析缓存，后续按需复用。

不训练或微调声库，不另建声音转换模型。随附 `readme.txt` 明确限制二次训练及可使用的编辑器/平台，因此原计划中独立 Python direct DiffSinger 后端不列入本项目默认路线；渲染优先在现有 OpenUtau 内完成。

## 4. 跨 Agent 的执行契约

### 4.1 共用 CLI，Agent 适配保持轻量

```powershell
agent2utau doctor --json
agent2utau inspect-reference "E:\data\project_opentuau" --json
agent2utau render-smoke --json
agent2utau cover "E:\data\music\年轮 - 张碧晨.flac" --singer yousa --json
agent2utau status <run-id> --json
agent2utau resume <run-id> --json
agent2utau retry <run-id> --phrase <phrase-id> --action <action> --json
```

可选输入：`--lyrics`、`--instrumental`、`--vocal`、`--score`、`--style-profile`、`--transpose`、`--output-dir`。默认不升降调；如声库表现不佳，先在原调比较音色/参数，再按显式选项处理移调。移调时伴奏、工程、目标 F0 和评价基准必须同步。

- Python CLI 与本地 runner 不内嵌某一供应商 Agent SDK，不默认要求第二套 LLM API/key。现有 Agent 可用自己的判断调用有限动作。
- `cover` 的保守默认策略必须能自行跑完；高级修正可由外部 Agent 根据报告调用 `retry`，两者共享同一状态与重试预算。
- 统一文档 `docs/agent-contract.md` 描述命令、JSON、状态和恢复规则。以后可提供薄的 Agent 入口文档；MCP 只是可选包装，不是 MVP 依赖。
- 同一台 Windows 上能执行本地命令的 Agent 共用接口。若 Agent 运行在云端/容器，需先具备到本机 runner 的受控连接与路径映射；不能假设它能直接访问 E 盘或控制 Windows 桌面。

### 4.2 长任务和可恢复性

`cover` 创建 run、启动本地任务并尽快返回 `run_id`；可选等待模式供终端使用。Agent 调用 `status` 获取状态，不依赖某产品的长工具调用超时策略。实现须实测宿主结束工具调用后 worker 的生命周期。

JSON 至少包含：`schema_version`、`run_id`、`status`、`stage`、`progress`、`artifacts`、`metrics`、`warnings`、`failure_code`、`retryable`、`next_actions`。机器结果写 stdout，诊断日志写 stderr；项目路径中的中文、空格、括号必须可用。

状态：`queued → running → completed / completed_with_warnings / needs_input / failed`，另有显式 `cancelled`。硬错误不能标成 completed。退出码区分请求已接受、前置条件不满足、执行失败；最终作业结果以状态 JSON 为准。

每个 run 有文件锁和原子状态写入；OpenUtau 渲染队列默认串行。缓存键包含输入/配置/模型 hash、应用版本和有效渲染参数。保存随机 seed（如支持），区分完全相同的缓存复用与允许数值小差异的重新推理。

## 5. 总体流程与产物

```text
本地资源探测 ──→ 参考工程迁移/短句渲染基线
                         │
原曲 → 解码/分离 → 歌词与对齐 + F0/音符 → 统一 score
                         │                   │
真人歌曲统计 + USTX 参数经验 + 声库预测 ──────→ 调校策略
                                             │
                                     构建并验证 USTX
                                             │
                                 OpenUtau 内 DiffSinger 渲染
                                             │
                              评价 → 有限修正 → 混音 → 交付
```

每次运行写入项目内独立目录，外部原始资源仅作为输入：

```text
runs/<run-id>/
├─ request.json / state.json / environment.json
├─ source_manifest.json / reference_migration.json
├─ audio/original.wav / reference_vocal.wav / accompaniment.wav
├─ analysis.json / score.json / tuning.json
├─ project.ustx
├─ vocal_render.wav / final_cover.wav
├─ evaluation.json / mix.json / report.md
├─ iterations/                    # 候选结果与修正证据
└─ debug/                         # 原始F0、对齐、图表、日志
```

交付工程引用的伴奏应位于该 run 中并可相对定位；干声包含正确前导静音或提供明确 sample offset，混音不能把歌曲第一句挪到零秒。原曲、真人歌曲、第三方工程、模型权重和运行缓存不提交 Git；仓库只放配置示例与自制测试数据。

## 6. 优先解决：工程迁移与 OpenUtau 自动渲染

### 6.1 从现成工程切出可验证基线

1. 解析 5 个 USTX，记录原文件 hash、版本、歌唱轨/音频轨、缺失文件、tempo map、实际使用的曲线与歌词类型。
2. 在 run 内复制工程；仅将选定的旧泠鸢轨迁移至 `YousaV1.65b`，保留其他 singer 的身份与诊断信息。
3. 建立 `01:Bright → Yousa_Bright` 等名称映射，根据当前加载结果重建音色索引/曲线映射；保留旧值、映射依据和新值。
4. 从目标主唱轨抽取一个约 5–10 秒、含连音和实际调校的短句；输出到新工程。缺失音频在这个纯合成测试副本中移除，不伪造文件、不覆盖原工程。
5. 截取必须同步裁剪/平移 notes、曲线、phoneme overrides、tempo、part offset，并保留合成所需上下文与前后余量。
6. 加载、保存、重新解析迁移副本，检查歌词、音符、时序、有效曲线、音色映射。格式转换允许无语义变化的字段重排。
7. 自动渲染该短句；另用自制 4–8 音符小工程测基本功能及换气/延音。

当前 `Backups\Untitled-autosave.ustx` 可提供本版本字段示例，但它属于用户工作状态，只读参考，不能当作稳定受控 fixture。

### 6.2 渲染接入决策

本次尚未验证这个版本具有可用 headless CLI 或远程 API。不能编造 `OpenUtau.exe --render`，也不能把内部类视为稳定公共 API。

按以下顺序进行有边界的验证：

1. 查匹配 commit 的参数入口、插件能力和渲染/导出代码；若确有可调用入口，先用真实短句证明可自动导出。
2. 如无合适入口，验证 Windows UI Automation 的可访问树、菜单命令和快捷键，仅负责打开工程、触发渲染/导出、等待完成与错误采集。
3. 如 Avalonia 的可访问性或导出控制不足，评估固定版本的 OpenUtau 应用内扩展/小补丁，通过本地命令队列调用其原有工程加载和渲染逻辑。复用模型，不重写推理器；另用项目内测试安装验证。
4. 一个方案经过短句加载、导出及重启复测后才列为 supported。若均不通过，M1 明确失败，保留可编辑 USTX 与诊断，不能转而把手动导出称为“一键”。

GUI adapter 必须有 Windows 会话/桌面可用性探测；避免固定坐标、固定 sleep 和逐音符点选。记录加载/渲染/导出阶段超时、进程退出、日志和目标文件更新，防止把上次留下的 WAV 当作成功。

自动任务不得关闭或覆盖用户正在编辑的工程。使用受控实例或队列，并在接入验证中确认本版本实例行为、偏好与缓存隔离方式。GPU/CPU 路径各自报告可用性；一条通过即可继续，CPU 慢不等于算法失败。

干声导出需排除伴奏与混音效果；已有 `MixFxApplyOnExportMixdown=true`，不能直接将默认 mixdown 当作干声。渲染 bridge 保存有效 steps、depth、设备和声库 hash。

## 7. 音频到可编辑乐谱

### 7.1 解码、分离与计算资源

- ffmpeg/ffprobe 或经过验证的等价工具解码，保留原始采样时间线；统一工作采样率与分析用单声道派生版本。
- 分离先选定一个实测能在这张 GPU/可用后端运行的模型，封装 `SourceSeparator`；具体包、模型版本、权重来源与 hash 在环境准备阶段锁定。本次未发现已安装的分离、ASR、F0 模型，不假设资源现成。
- 检查人声/伴奏非静音、长度、起点和尾段；可利用重建残差检查明显延迟，但不要求分离模型的两轨严格逐样本相加等于原曲。
- 分离、ASR、F0 与 OpenUtau 默认分阶段使用 GPU，支持卸载模型、分段及重叠拼接；先测显存峰值再决定并发。
- 常规首版不叠加大量去噪；把混响、和声、伴奏残留作为分析置信度因素。GPU 实测失败可采用可用 CPU 路径，或明确报依赖/兼容问题。

### 7.2 歌词、对齐、音符一起建模

- 只有音频时：歌唱人声转写 → 中文字/音节 → 强制对齐 → 与 F0、起音及停顿联合生成音符。保存原转写、修订、置信度和来源。
- 有外部歌词时先对齐；《年轮》测试分别记录“仅音频”和“辅助歌词”两种结果，不能在前者中暗中加入答案。
- 不允许 Agent 凭歌曲名补出未识别歌词。低置信度段先局部重跑或比较候选；仍不可靠时输出明确区段与状态，保留已有工程。
- 音高平台不能单独决定音符边界：同音高上的多个字仍可能是多个音符；一字跨多个音符要正确生成延音结构。
- 汉字、多音字与拼音按当前词典解析；区分 `+`、`AP`、`SP`，不能把气声区强制填入有声 F0。
- 优先让已安装 phonemizer + dsdur 预测音素时长，再修正可测量的错位，不从零手写所有中文音素时长。

### 7.3 时间与音高的中间格式

`analysis.json` 保存原始测量，`score.json` 保存重建乐谱，`tuning.json` 保存目标演唱与应用策略，均有 `schema_version` 和来源索引。

- 音频绝对位置以 sample index / 秒记录；USTX 使用对应版本的 ticks，转换包含 tempo map、part offset 与音符相对位置。分段分析保留全局 offset。
- BPM/节拍帮助结构化编辑，不强行吸附所有音符。若节拍不可靠，可用明确标注的固定工程 tempo 表达绝对时值，不把它声称为已识别真实 BPM。
- F0 同时存 raw/cleaned、confidence、voiced mask；Hz、MIDI、cents 的单位明确。
- 主 F0 backend 加一个按需交叉验证后端；先落实主路径，第二后端重点处理持续八度歧义。禁用无证据的调性吸附，保留经过音和真实转音。
- notes 至少包含 id、phrase id、起止 sample/秒、MIDI、字/拼音、syllable id、置信度及来源；密集帧数据可放 NPZ，JSON 保存路径/hash。

## 8. 调校：先验证模型基线，再增加表现迁移

### 8.1 两种明确的音高策略

**模型基线**：以重建音符和歌词为输入，使用当前声库 pitch/variance 预测，先证明旋律、字音、时长正确。这是 MVP 的默认候选。

**混合表现**：从高置信度参考 F0 提取音符中心、滑音、颤音与装饰音，以可调强度注入目标演唱；结合真人歌曲和参考 USTX 的统计约束参数幅度。分离伪影、孤立跳点、八度错误不进入曲线。

不能把 raw F0 每帧直接当 pitch 点；也不把“完全禁止任何 F0 迁移”作为限制。清理后的高置信度 F0 可以作为目标曲线或局部参照。

转换前必须确认当前版本 note pitch 点、`pitd`、模型预测音高、vibrato、`pexp` 的单位、相对基准、时间轴与叠加顺序。`pitd` 不是可以直接写 Hz 的槽位。每个片段记录谁负责最终音高，防止模型预测、手绘曲线和 vibrato 重复叠加。

首版只实现一条通过 round-trip 和实际渲染测试的主表示；另一表示按需要添加。验证包括稳音、滑音、长音颤音、休止和 part 偏移；不要求一开始同时完成两套后端。

### 8.2 强弱与音色

- 先比较五种音色或少量明确候选；按语义名称解析，逐句平滑切换。将选择依据写入报告。
- 原曲只提供相对强弱参考，避免把混响或压缩包络直接复制为 `dyn`。
- breathiness/voicing/tension 从模型基线起步，用有效范围内的局部修改；不控制未支持的 energy/falsetto。
- render → 测量 → 小幅修正，避免层层叠加 track volume、note volume、dyn 和后期增益。
- 五首旧工程只能形成初步经验，不能据此硬编码可靠音域；音域和参数对响度的影响通过当前版本短句渲染校准。

## 9. 自动评价、重试与混音

### 9.1 评价对象与成功条件

区分三件事：乐谱重建是否忠于原曲、渲染是否实现目标乐谱/曲线、成品听感是否合适。自动指标能发现常见错误，不能证明音色一定像真人或调校达到专业水平。

- 渲染检查：非空有效 WAV、无 NaN、无意外整句静音/截断、无明显 clipping、无错加载 singer、无残留原唱轨。
- 音高：比较高置信度 voiced 区域中的目标音高与渲染音高，另报有效覆盖率；不能只统计双方都有 F0 的区域而忽略漏唱。混合风格与移调后使用相应目标，不硬逼逐帧复制张碧晨。
- 时序：检查句首、句末、歌词对齐、全曲漂移；先测并报告固定偏移再比较形状，不用任意时间扭曲掩盖错误。
- 强弱：检查非预期突跳、长句衰减与人声/伴奏平衡；不把合理的主副歌动态差当成错误。
- 输出 `debug/f0.png`、`notes.png`、`alignment.png` 和关键短句 A/B 音频，供开发校准和最终试听。

原计划的 35 cents / 80 cents、60–80 ms、1% 八度错误率等只作起始研究目标。M1/M2 校准检测器误差与音符边界定义后再锁入版本化评测配置；报告阈值、覆盖率、样本量，低覆盖率不得判优秀。

### 9.2 有限修正

初始渲染后最多 3 次修正；按 phrase 分类处理：八度错误、音符边界、歌词漂移、音素时长、音高突刺、响度、分离残留、渲染失败、混音失衡。

每次保存 `before / evidence / action / after / metric_delta`。优先复用未变的分析与伴奏；局部重算包含上下文。若 renderer 不支持局部独立导出，允许整轨重渲染，不假设任意切片都能无缝拼接。

重试共享预算且有总时限；只保留经过硬检查的最佳候选，退化时回退。耗尽预算后标记 `completed_with_warnings` 或 `failed/needs_input`，不得将不可用输出叫成品。网络/设备的有限重试与调校尝试分别计数。

### 9.3 混音

通过结构检查的干声与伴奏按样本时间轴对齐，再做增益平衡、按需轻量 EQ/压缩/去齿音/混响，末端控制 true peak。默认保留原曲结构与尾段，处理尾音时记录长度变化。

保存 `mix.json`；确认没有将原唱误加回主声轨。分离伴奏可能残留原唱/和声，需要报告残留风险；不能声称两轨分离天然保证完全换人。先输出 PCM WAV，其他格式后续添加。

## 10. 实施里程碑与验收

| 阶段 | 交付 | 完成条件 |
| --- | --- | --- |
| M0 资源与运行骨架 | 项目环境、配置、`doctor`、状态与模型清单 | 已探测/未验证严格区分；中文路径可用；缺依赖给具体诊断 |
| M1 现有工程短句闭环 | reference inspector、迁移报告、受控 USTX、render adapter | 旧声库/音色正确迁移，缺配套音频也能合成；自动导出非静音短句；应用重启后重复通过 |
| M2 《年轮》短片段 | 分离、ASR、对齐、F0、note、模型基线调校 | 自动选主歌/副歌/长音等 3–5 段，总约 30–60 秒；仅音频输入生成可唱且基本对齐的工程与混音 |
| M3 首次完整一键 | `cover/status/resume`、整首 USTX/WAV/报告 | 《年轮》约 274.504 秒全流程；不逐音符操作；前奏、间奏、尾奏保留，时间轴无累计漂移 |
| M4 表现增强 | 参考 USTX 统计、可选真人 style profile、混合音高与音色候选 | 与 M3 基线 A/B 比较，有证据改善且不破坏歌词/旋律；不以风格分析阻塞完整初稿 |
| M5 稳定交付 | 有限修正、异常恢复、跨 Agent 契约验证 | 相同配置可恢复/复跑；常见失败可诊断；可用 Agent 宿主执行同一命令，未测试宿主明确标注 |

最终验收必须包含一次新 run 的《年轮》“只给原曲”测试，并确认输出工程能在当前 OpenUtau 重新打开及重渲染。开发时允许人工试听与抽查；日常用户流程不要求人工调校。M3 代表功能闭环，M4/M5 完成后才宣称达到本计划完整交付。

### 第一项实际开发任务

完成 **M0 + M1 的最小贯通**：

```text
探测本机资源
  → 解析五个参考工程
  → 选择一个泠鸢主唱短句
  → 迁移 singer、音色、时间轴并处理缺失音频引用
  → 当前 OpenUtau 加载/保存验证
  → 自动导出 dry WAV
  → 非静音、时长、音高范围与重复运行检查
```

M1 未通过前不投入整曲 ASR、复杂风格建模或完整多工具 Agent 框架；资源解析、依赖定位和受控工程准备仍可继续。

## 11. 建议仓库结构与验证重点

```text
agent2utau/
├─ plan.md / README.md / pyproject.toml / uv.lock
├─ configs/                      # defaults、local.example、singers/yousa.example
├─ docs/agent-contract.md
├─ schemas/                      # request、state、analysis、score、evaluation
├─ src/agent2utau/
│  ├─ cli.py / pipeline.py / state.py
│  ├─ resources/                 # 环境、声库、参考工程、依赖与hash
│  ├─ audio/                     # 解码、分离、混音
│  ├─ analysis/                  # 歌词、对齐、F0、音符、节拍
│  ├─ tuning/                    # 模型基线、表现、音色、局部修正
│  ├─ openutau/                  # 版本适配、USTX迁移与构建、渲染接入
│  └─ evaluation/                # 结构、旋律、时序、响度
├─ bridge/                       # 仅在M1证明有必要时添加应用内接入
├─ tests/fixtures/               # 自制小工程与结构化数据
└─ runs/                         # 忽略Git
```

优先测真正容易出错的边界：

- 旧音色名称与当前不同顺序的映射，包括 `clr` 与曲线；0.7/0.9 加载保存后的语义一致性。
- 顶层 bpm 与 tempo map 不一致、part offset、变速、截句和 sample/tick 往返。
- 同音高多字、一字多音符、`+ / AP / SP`、多音字、phoneme overrides。
- F0 八度候选、转音与颤音区分、模型/手工曲线重复叠加、评价覆盖率。
- 输出旧文件误判、应用退出/超时、缺 singer/音频、设备不可用、并发与 resume。
- 整曲干声与伴奏对齐、尾段完整、工程重新打开后引用仍可解析。

不要求第一版实现多主唱自动拆分、复杂和声重建、Rap、极端发声、自动训练或专业母带。单主唱中文流行歌曲优先，已有多轨工程只作为资源解析与迁移用例。

## 12. 证据与技术依据

本机主要证据（只读核对）：

- `E:\software\OpenUtau-win-x64 (6)\OpenUtau.dll` 的版本信息。
- 同目录 `prefs.json`、`OpenUtau.runtimeconfig.json`、`Logs\log20260915.txt`、`Backups\Untitled-autosave.ustx`。
- `Singers\YousaV1.65b\character.yaml`、`dsconfig.yaml`、`dsdur/dspitch/dsvariance` 配置、`dsvocoder\vocoder.yaml`、`languages.json`、`readme.txt`。
- `E:\data\project_opentuau` 的五个 USTX 与引用路径检查。
- 《年轮》FLAC STREAMINFO；真人歌曲文件清单；`nvidia-smi` 与 `.NET` 查询。

[OpenUtau 官方发布页](https://github.com/openutau/OpenUtau/releases/tag/0.1.570.4-alpha)与本机版本/commit 对应。实现时核对[官方仓库](https://github.com/openutau/OpenUtau)中该 commit 的 `OpenUtau.Core/Ustx/`、`OpenUtau.Core/DiffSinger/`、渲染/导出与程序入口。本次网页工具未能取得指定源码文件内容，因此本文没有把 CLI、headless 或内部 API 能力列为已验证事实。

## Definition of Done

在准备好的本机环境中，用户通过任一具备本地执行能力并遵守共用契约的 Agent，只提供原曲音频，系统能自动完成分析、可编辑 USTX 构建、当前泠鸢 DiffSinger 在 OpenUtau 内的合成、有限评价修正和伴奏混音，交付完整可试听 WAV、干声、可重新打开的工程和真实质量报告。资源可追溯、失败可恢复，全过程不要求用户逐音符调校或手动导出。
