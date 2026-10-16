# 仓库维护工具

本目录只放跨任务的仓库维护工具。歌曲制作使用`src/agent2utau`的CLI与Skill；测试使用`tests`；固定歌曲实现记录放在[research/implementation-records](../research/implementation-records/lastpage-20261007/README.md)。

| 工具 | 使用与边界 |
|---|---|
| [repository/check_repository.py](repository/check_repository.py) | 默认检查Git索引所列文件、媒体/模型排除、作者包及Skill；整理后尚未暂存时用`--worktree`检查当前跟踪及未忽略的新文件 |
| [repository/package_research_projects.py](repository/package_research_projects.py) | 仅在明确指定原件目录与新输出目录时打包三份授权白烁USTX、说明和SHA；不包含音频，不覆盖原包 |

从仓库根运行`python tools/repository/check_repository.py --worktree`。正式发布/CI使用不带该选项的索引检查。维护工具不决定唱法、不运行旧曲方案、不扫描历史产物来补新任务。
