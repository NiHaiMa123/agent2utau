# agent2utau 当前 Agent 协作规则（2026-10-31）

**只执行当前 [plan.md](plan.md) 与 [docs/workflow.md](docs/workflow.md)**。历史路线已归档；旧 `singing-expression-editor`、旧研究表1/表2、旧 README/AGENTS 不能覆盖当前指令。

1. **优先 P0–P3**：原曲分离、GAME 音符事件、锁定歌词、确定性字—音符映射、当前声库的音素预测、局部时间修正、真实原生读回、小模型稳定性。默认使用泠鸢 DiffSinger 自动音高；不画整曲 PITD，不模仿原唱表达，不调整 VOIC/BREC/TENC/DYN 或混音。
2. **程序负责正确性，Agent 负责歧义决策。** 按 5～15 字提供 candidate_id；模型仅选已存在候选或 unresolved。不可凭空产生音素 token/毫秒数、重排全曲歌词或直接覆写原工程。
3. 用户锁定歌词是正文；ASR 只是粗建议；GAME 是音符事件不是字界；原唱 HFA 是时间观测不是合成时钟真值；原生 phonemizer 的输出必须实际导出。
4. 必须校验歌词 ID、音符 ID、`+` 连音连续性、词表、时间非负/单调、tick 量化、目标外不变项和源 SHA；patch 写回后通过真实 OpenUtau Core roundtrip / phoneme 再导出。失败标 unresolved，不能声称“完成”。
5. 每个新 run/session 记录日期、执行模型、输入/输出、运行命令、测试结果、真正做过的原生验证、人工听感状态。历史 unknown-model 原样保留。
6. 不删改既有 USTX、歌曲历史 session、封存报告、知识包、Skill 或资产；不批量迁移、不开未授权 GitHub CI、不自动多 Agent。旧的 `compile-functions` 不是新对齐器。
7. 新工作流尚未一键实现；先盘点已有命令，再分批增量实现。真实运行结果与人的音乐感受必须分开叙述。

[原版旧 AGENTS 完整快照](docs/archive/legacy-guidance/AGENTS_pre-autopitch_20261031.md) 仅供历史查阅。
