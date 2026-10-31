# 归档证据（本机 run 的文本部分）

这是 `runs/production/phoneme-alignment-p1.1-20261031/` 的**逐字节副本**，只含纯 JSON 证据；run 本身仍留在本机。

| 内容 | 用途 |
|---|---|
| `<song>/lyrics_locked.json` | 锁定歌词与 `syllable_id`（含出处与待复核的公开歌词差异） |
| `<song>/notes_normalized.json` | GAME 事件归一化（`note_id`、原始时钟、单网格 tick、时钟异常） |
| `<song>/mapping.v1.json` | 确定性字—音符映射、句区间、窗口候选与决策、未解字 |
| `<song>/anomalies.json` | 观测匹配分级、映射/USTX 问题、非法延音与有限候选 |
| `<song>/baseline_verification.json` | 映射 → USTX 的**逐 note 核对表**（缺音、多音、改音高、字不符） |
| `run_summary.json` | 三首歌的状态、覆盖、冻结输入哈希与退出码口径 |
| `game_stability/game_stability.json` | GAME 复现性实验（3 配置 × 3 次：同会话/新会话/单线程） |
| `game_stability/cross_process.json` | 跨进程对照（每进程一个新会话，只推理一次） |

`MANIFEST.json` 给出每个文件在本机 run 里的对应路径、SHA256 与字节数，并标出副本与原文件是否逐字节一致。

**不在 Git 里的**：音频、USTX 工程、探针工程、观察到的分离件，以及 `runs/.../canonical_lyrics/`（第三方公开发布的歌词正文转写，按版权考虑只留在本机，仓库里只记 URL、检索时间与哈希）。

结论与未决项见 [`../reports/phoneme-alignment-p1.1-20261031.md`](../reports/phoneme-alignment-p1.1-20261031.md)；本轮**停在 P2 之前**。
