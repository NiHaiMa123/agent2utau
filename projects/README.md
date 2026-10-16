# 发布工程

`latest/`只保存当前用户指定保留/发布的USTX：花海、最后一页、雨爱。它们不等于整曲质量已经验收；局部试验获接受也不自动覆盖这里的工程。

新曲工作谱面、音素导出、函数计划、编译候选和渲染产物放本机`runs/production/<run-id>/`。试听A/B候选放`runs/experiments/<run-id>/`，测试谱面用pytest临时目录，不放`latest/`。

发布USTX时绑定源、输入和验证结果，再按用户任务范围更新；音频、模型和缓存不进入本目录或Git。作者工程在`research/baishuo/projects/`只读，不能与这里的Agent工程混用角色。
