# 测试目录

本目录只保存测试代码和必要的无媒体测试资料，不作为生产入口。生产包在`src/agent2utau`，实际桥接源码在`bridge/OuBridge`，Skill执行工具在`skills/singing-expression-editor/scripts`。

| 目录 | 测试范围 | 外部资源要求 |
|---|---|---|
| unit/ | 表达函数、节奏、variance预期、分离选择等局部计算与边界 | 合成数据；不加载真实歌曲/模型 |
| contracts/ | 显式计划编译、独立评价、受控输入隔离等接口契约 | `tmp_path`生成输入；原生桥接/重模型使用模拟，不声称真实OpenUtau已执行 |
| skills/ | Skill函数、控制叠加、稀疏线和物理视窗 | 导入当前仓库Skill脚本，使用合成数据 |

从仓库根运行`python -m pytest -q`，或指定`tests/unit`、`tests/contracts`、`tests/skills`。pytest仍只收集`tests`；不会收集`research`的历史实现脚本。

音频/临时USTX/JSON/模型输入使用`tmp_path`，随测试生命周期管理；不向`projects/latest`、封存run或生产配置写入。需要共享静态资料时另建`tests/fixtures`，仅允许可审查的小型文本合成资料，不复制作者数组或真实录音。

当前自动套件包含确定性计算与模拟契约检查，没有真实声库音频的自然度验收。未来真实OpenUtau/模型集成检查应独立为`tests/native`、显式选择运行，结果放本机`runs/native-tests/<run-id>`；该目录和检查目前尚未新增，不能当作已经覆盖。
