# agent2utau

根据原曲观测和 singing-expression-editor Skill，由 Agent 选择函数、独立设计整曲音高及发声控制，再编译 OpenUtau 工程和试听。

原曲 → 分离 / ASR / GAME / 双 F0 / HFA 观测 → Agent判断与显式计划 → 函数采样 → 原生编译及读回 → 当前条件渲染 → 固定增益混音 / 试听。

## 当前入口

- [Skill](skills/singing-expression-editor/SKILL.md)：表达判断和完整检查要求。
- [执行流程](docs/workflow.md)：环境、命令、计划格式和验证边界。
- `src/agent2utau/workflow.py`：原曲观测和独立函数的原生编译，不替 Agent 决定画法。
- `bridge/OuBridge`：使用实际 OpenUtau Core 导出音高、音素、模型输入及渲染。
- `tools/lastpage_fresh_*` / `lastpage_loudness_skill_v02_20261007.py`：最近完成歌曲的实现记录；不是通用生产入口，不能直接换曲名或常量运行。

## 使用

安装 Python 3.11+ 依赖：`pip install -e .`。OpenUtau / 声库 / 模型、ffmpeg、HubertFA 是本机依赖，按 [执行流程](docs/workflow.md) 配置。

```powershell
agent2utau doctor
agent2utau observe-source "<原曲路径>" --out runs/new-source
agent2utau export-phonemes --project runs/new-score.ustx --out runs/phones.json
agent2utau export-pitch --project runs/new-score.ustx --out runs/pitch.json
agent2utau compile-functions --plan runs/functions.json --out runs/compiled
agent2utau render-project --project runs/compiled/project.ustx --out runs/native.wav --mixdown
```

观测命令不会自动生成歌词谱面或音高线。Agent 先审阅观测、选择音乐身份、整理歌词/HFA及原生音素，再明确设计函数。编译通过只证明数字与原生读回，不等于自然度通过。

## 白烁研究资料

[三份原始工程](research/baishuo/projects)及 [ZIP包](research/baishuo/baishuo-projects.zip)包括《花海+4》《雨爱》《最后一页》，SHA256见 [清单](research/baishuo/manifest.json)。仅用于授权研究；独立制作不加载作者曲线、profile或参数路线。

仓库当前版本不包含音频、模型权重、缓存或 runs 产物。旧路线已移到本机 `.local-archive/cleanup-20261008/`；Git历史中的旧音频未重写删除。清理范围见 [记录](docs/repository-cleanup.md)。
