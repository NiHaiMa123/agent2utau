# 目录整理与验证 · 2026-10-09

此次只调整代码/测试/研究记录/知识文档的存放和维护引用，不生成音频或推进表1/表2确认。当前目录规则见[规范](../../../../docs/guides/repository-layout.md)，项目入口见[README](../../../../README.md)。

## 已完成的移动

| 原位置 | 新位置 | 内容边界 |
|---|---|---|
| tests根目录6个局部计算测试 | tests/unit/ | 内容保持 |
| tests根目录3个接口测试 | tests/contracts/ | 内容保持；原生和重模型使用模拟，不宣称真实集成验收 |
| tests根目录4个Skill测试 | tests/skills/ | 仅更新搬迁后的Skill脚本相对路径 |
| tools/check_repository.py与package_research_projects.py | tools/repository/ | 打包脚本字节保持；门禁更新根路径，并增加整理后未暂存时的工作树检查模式 |
| tools中七份最后一页实现脚本 | research/implementation-records/lastpage-20261007/ | 原字节/SHA保持，不重跑、不修写历史路径 |
| docs/acoustic-manifestations-20261009/的12份资料 | docs/knowledge/acoustic-manifestations-20261009/ | CSV/结构化知识与来源审计字节保持；README相对链接及资料包位置审计更新 |

所有移动先检查源/目标绝对路径均在工作区、目标不存在，再用同一PowerShell执行。逐文件移动关系、前后SHA与保护核查见[迁移清单](../../../../experiments/misc/reports/directory-reorganization-20261009.json)。旧历史manifest原文不动，涉及搬迁脚本的核对须显式采用清单查找对应字节；它不授权重放脚本或自动修改新曲输入。

## 未移动的固定资源

`src/agent2utau`和原生bridge源码未改，公开CLI/包导入保持；Skill、三个发布USTX、白烁三份原件/ZIP和本机模型/安装未改。封存run及原报告保留原路径/内容。保护核查87项中86项字节保持，唯一有意修订为`docs/workflow.md`的目录/历史实现入口说明。

已有流程/评价入口和有SHA绑定的历史报告是明确的路径例外。新方法、新知识、新可读报告按`docs/guides`、`docs/knowledge`、`docs/reports`存放；原始数据、实际模型输入、图册、音频与完整日志仍存本机ignored run，不复制成Git研究输出。

## 维护入口

- `.github/workflows/ci.yml`改为新门禁工具路径；pytest仍只收集`tests`，明确排除研究、运行产物和外部依赖目录。
- `data/`、`models/`整目录加入忽略，本机资料/模型不进入Git。已有媒体、权重、run、外部工具与缓存排除继续保留。
- `.gitattributes`明确搬迁历史脚本、知识包及绑定的原始实验报告不做换行转换，防止提交/检出后字节哈希漂移；作者原件与ZIP原保留规则不变。
- README、AGENTS、两份根计划、工作流程和知识生成脚本同步新路径；表1/表2的八份核心CSV/JSON基线SHA保持。
- 维护工具默认检查索引列出的路径；当前尚未暂存的移动用`--worktree`检查现存跟踪文件与未忽略的新文件。正式发布/CI仍使用默认模式，不能把工作树检查冒充已完成索引发布审计。

## 验证与限制

完整pytest初次运行受Windows沙箱默认TEMP权限影响：71通过、1失败、16个fixture错误，未据此宣布成功。将该次测试的TEMP/TMP和pytest临时目录放进全新的工作区ignored目录后，同一完整套件**88通过**，未修改测试断言、产品行为或权限策略。

检查内容包括生产包不导入tests/research、迁移字节/明确修订、固定资源与来源哈希、知识包审计、81个活动文档路径，以及工作树媒体/作者包/Skill门禁（155文件、媒体0、作者工程3、ZIP成员5、Skill引用102）。CLI及研究打包工具的帮助入口也通过。详细命令和通过项由本次执行记录核查，后续发布仍须按AGENTS要求检查当时的Git索引。

没有重新编译部署OpenUtau或渲染模型，没有新增真实声库集成/听觉验收；移动不会把旧试验或局部反馈升级为质量通过。本轮未执行Git提交或推送。
