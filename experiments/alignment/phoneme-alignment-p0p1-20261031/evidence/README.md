# 归档证据（P0/P1 首版的文本部分）

这是 `runs/production/phoneme-alignment-p0p1-20261031/` 的**逐字节副本**，只含纯 JSON 证据；run 本身仍留在本机。

| 内容 | 用途 |
|---|---|
| `<song>/lyrics_locked.json` | 锁定歌词与 `syllable_id`（公开权威歌词来源与差异记录） |
| `<song>/notes_normalized.json` | GAME 事件归一化（`note_id`、单网格 tick） |
| `<song>/mapping.v1.json` | 首版确定性映射与窗口候选 |
| `<song>/anomalies.json` | 时钟/观测/映射异常 |
| `samples/index.json` | 22 个小样本索引（覆盖 8 类场景） |
| `samples/*/*.phones.json` | 三个样本的真实原生音素导出（OpenUtau Core 输出） |
| `command-inventory/observe-nianlun/game.json`、`asr.json` | 同源复跑 observe-source 得到的观测（用于 P1.1-E 的复现性对照） |

`MANIFEST.json` 给出每个文件在本机 run 里的对应路径、SHA256 与字节数，并标出副本与原文件是否逐字节一致。

**不在 Git 里的**：音频、USTX 工程、探针工程、分离件与 `runs/.../canonical_lyrics/`（第三方歌词正文转写）。

这份是**首版（P0/P1）**的证据；P1.1 的修复后证据与对照见
[`../phoneme-alignment-p1.1-20261031/evidence/`](../phoneme-alignment-p1.1-20261031/evidence/)，
两份的差异即 P1.1 的修复前后对照。
