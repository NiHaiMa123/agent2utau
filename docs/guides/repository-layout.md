# 目录边界与各环节文件存放规范

更新：2026-10-09。生产、测试、研究、知识文档、发布工程和本机产物分开；目录分类不改变当前唯一制作流程。

## 1. 顶层职责

| 目录/文件 | 保存什么 | 不放什么 | Git |
|---|---|---|---|
| 根目录README、AGENTS、plan、plan-table2 | 项目入口、Codex约定和当前/后续专项计划 | 重复计划、音频、实验输出 | 提交 |
| src/agent2utau/ | 通用生产Python代码与独立评价实现 | test文件、固定歌曲脚本、作者控制数组 | 提交 |
| bridge/OuBridge/ | 真实OpenUtau原生桥接C#源码与项目文件 | 歌曲输出、测试fixture | 提交源码；bin/obj忽略 |
| skills/singing-expression-editor/ | 通用Codex制作Skill、参考方法、函数工具 | 具体歌曲参数/文件路径配置 | 提交，修改另按Skill维护要求 |
| tests/ | unit、contracts、skills自动测试 | 生产入口、真实录音、作者数组、声库模型 | 提交代码；临时数据不提交 |
| tools/repository/ | 仓库门禁、研究原件打包等维护工具 | 已完成歌曲制作脚本、试听实验 | 提交 |
| configs/ | 通用默认值、USTX模板、声库配置示例 | 模型权重、机器绝对路径进入公共配置 | 提交通用文件；local.yaml忽略 |
| schemas/ | 程序可读契约，例如运行state schema | 单次执行state/观测/日志 | 提交 |
| research/ | 只读作者资源、研究索引、历史实现记录 | 默认生产配方、运行输出/音频/模型 | 提交允许的原件/文本，不自动用于生成 |
| docs/guides/ | 使用说明、组织约定与方法文档 | 实验PCM、模型输入数组 | 提交 |
| docs/knowledge/<包名>/ | 表1/表2、CSV/JSON知识清单、摘要与来源审计 | 未标角色的作者数组、完整run副本 | 提交必要文本/聚合数据 |
| docs/reports/<主题>/ | 新可读实验、评价、维护报告 | 可直接运行的旧曲脚本、二进制产物 | 提交必要报告/有限聚合结果 |
| projects/latest/ | 用户指定保留/发布的USTX | 测试谱面、实验B/C、音频、模型 | 仅工程 |
| data/ | 本机导入资料，例如原录音、歌词工作副本 | 默认制作规则、通用配置 | 整目录忽略 |
| models/ | 本机权重、配套YAML/manifest | 代码/知识表 | 整目录忽略 |
| external/ | 本机外部工具/依赖/HFA模型 | 项目生产代码的默认维护位置 | 整目录忽略 |
| runs/ | 按角色分类的输入绑定、执行/研究/试听/测试/构建产物 | 自动当作新任务输入的缓存 | 整目录忽略 |
| demo/、.local-archive/ | 已有本机试听与旧路线归档 | 新工作默认入口 | 忽略，原路径保留 |

已有`docs/workflow.md`、`docs/evaluation-v0.md`及封存历史报告保留原路径；新内容按上述类别保存。已有`bridge/out*`及`bin/obj`是ignored构建产物，保留已部署/绑定路径，不重新部署或搬动本机安装。表格资料本次移动至`docs/knowledge`，历史脚本移动至`research/implementation-records`，迁移关系显式记录。

## 2. 生产代码按环节划分

| 环节 | 通用代码 | 主要输入/输出 |
|---|---|---|
| 配置与资源 | resources/、configs/ | 通用配置＋本机覆盖，doctor资源状态 |
| 原曲解码/分离 | audio/decode.py、audio/separate.py | 显式原曲→解码/分离文件＋来源SHA |
| 原曲观测 | transcription/、analysis/、workflow.observe_source | GAME、双F0、ASR/歌词观察；HFA显式外部执行 |
| 音乐/歌词/谱面判断 | Codex＋Skill、openutau/build.py/ustx.py | Agent自选身份、音符、音素和unknown，生成工作USTX |
| 显式表达设计 | expression/＋Skill scripts/ | 独立函数/动作/发声计划；预测基底与人工增量分开 |
| 原生编译/读取 | workflow.compile_functions、openutau/bridge.py、bridge/OuBridge | 编译USTX、pitch/phones、读回/隔离结果 |
| 当前依赖渲染 | openutau/bridge.py、真实Core/声库 | variance/acoustic/vocoder实际输入与波形 |
| 固定增益混音 | audio/mix.py | 指定声/伴奏增益，输出PCM，拒绝削波 |
| 独立评价/反馈 | evaluation/＋Codex/用户 | 显式输入/SHA的形态测量、风险、unknown和用户反馈 |
| 发布 | projects/latest/＋tools/repository/ | 被指定保留的USTX、报告、索引检查；不发布音频/模型 |

`evaluation`是供实际工程使用的通用只读功能，所以仍在生产包；验证它的测试在`tests/contracts`。不把生产评价器误移到测试目录。生产模块不得导入`tests`或固定歌曲研究实现。

## 3. 本机运行目录与阶段文件

新任务按目的选择`runs/production/<run-id>`、`runs/experiments/<run-id>`、`runs/research/<run-id>`、`runs/test-results/<run-id>`、`runs/native-tests/<run-id>`或`runs/build/<构建名>`。运行ID包含主题/日期/唯一标识，每次使用新目录；旧封存run不搬动、不重写。

建议阶段子目录如下，它是文件组织约定，**不是已经新增的自动编排API**。现有CLI只写调用者提供的`--out`；相对路径计划须按实际文件位置准备，不能因目录名称推断已执行。

```text
<run-id>/
  manifest.json          # 原曲/工程/工具/模型/版本与输入绑定
  inputs/                # 显式选择的输入副本、歌词、HFA输入
  observations/          # 解码/分离/GAME/F0/ASR/HFA观测
  score/                 # Agent自有工作谱面、原生音素/时钟
  design/                # 函数/控制计划、目的、备选、unknown
  compiled/              # 原生写入工程、编译与读回报告
  native/                # 当前预测/实际输入/渲染、依赖核查
  mix/                   # 固定增益音频、拼接与峰值检查
  evaluation/            # 独立结果、图册和unknown
  delivery/              # 交付USTX/独立A/B文件及SHA
  feedback/              # 用户原话、比较对象、音频绑定
  logs/                  # 命令、失败、重试；不覆盖失败证据
```

测试默认使用pytest `tmp_path`，不写生产run或发布工程；受限环境需指定临时目录时，TEMP/TMP与pytest `--basetemp`使用全新的`runs/test-results/<run-id>`，禁止指向已有任务/封存目录。真实声库测试若以后新增，再显式使用native-tests。一般研究产物不进入Git；需要可复查的结论时，提取有限摘要与SHA到对应知识包/报告，原始数组和波形仍留run。

## 4. 文件类型与角色

| 类型 | 位置 |
|---|---|
| .py/.cs通用逻辑 | src、bridge；Skill通用数学脚本仍在Skill目录 |
| test_*.py及测试辅助 | tests的相应类别；不放src/tools/research活动入口 |
| .yaml通用默认/模板 | configs；模型配套文件随本机模型，绝对路径配置仅local.yaml |
| .json/.csv知识与规则 | docs/knowledge，必须标来源、证据层级、unknown和版本 |
| .json运行state/实际输入/.npy/.npz | runs，不能因是文本JSON就提交完整run输出 |
| .txt/.lab歌词与音素对齐输入 | 本机data或run的inputs；经审查的合成测试资料才放tests/fixtures |
| .jsonl/.log执行与事件记录 | run的evaluation/feedback/logs；可读结论提取至docs/reports |
| .png/.svg/.pdf检查图册 | 运行检查图册放runs/evaluation；独立说明用的少量静态插图可随docs/guides/assets管理 |
| .md方法/计划/实验报告 | 根目录计划、docs/guides方法、docs/reports报告；Skill方法随Skill |
| .ustx Agent工作/候选 | runs/production或experiments；只有指定发布版进入projects/latest |
| .ustx作者原件及授权ZIP | research/baishuo，逐字节只读、SHA核对、无媒体成员 |
| .wav/.mp3/.flac等音频 | 本机data、runs或已有demo，所有目录均禁止上传Git |
| .onnx/.pt/.pth等权重 | 本机models/external/安装声库；不提交Git |
| .exe/.dll、构建/测试缓存 | 本机构建目录/安装目录和ignored缓存；不提交Git |

每个文件的角色以来源/绑定为准，不能只看扩展名。制作预期、数学检查、实际测量和听觉反馈分开，不因目录“evaluation”或“delivery”就认为质量通过。
