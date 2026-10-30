# 年轮（nianlun）制作索引

按「主制作 / 局部修订与试验 / 历史记录 / 交付」四类索引；
每个 session 目录含 `manifest.json`（song_id、run_id、日期、模型归属证据、状态、听感状态、
本机原始 run 路径、产物清单），`scripts/`、`reports/`、`feedback/` 可跟踪，`workspace/` 被忽略。
模型归属只按原始日志/manifest 判定，没有证据的一律 `unknown-model`——**这不是缺陷，是不猜**。
历史 session 的目录名保持原样，不追溯重命名。

## 主制作（Production Session）

一次完整制作/重做某歌的 run；有本地 compiled/delivery 产物。

| session | 日期 | 模型 | 本机 run 目录 | run 文件数 | session 内归档文件 |
|---|---|---|---|---|---|
| [`20261028__unknown-model__nianlun-from-scratch-20261028`](sessions/20261028__unknown-model__nianlun-from-scratch-20261028/) | 20261028 | unknown-model | `runs/production/nianlun-from-scratch-20261028` | 904 | 39 |
| [`20261028__unknown-model__nianlun-from-scratch-v2-20261028`](sessions/20261028__unknown-model__nianlun-from-scratch-v2-20261028/) | 20261028 | unknown-model | `runs/production/nianlun-from-scratch-v2-20261028` | 2342 | 28 |
| [`20261029__unknown-model__nianlun-v3-20261029`](sessions/20261029__unknown-model__nianlun-v3-20261029/) | 20261029 | unknown-model | `runs/production/nianlun-v3-20261029` | 1121 | 244 |
| [`20261030__unknown-model__nianlun-from-scratch-v3-20261030`](sessions/20261030__unknown-model__nianlun-from-scratch-v3-20261030/) | 20261030 | unknown-model | `runs/production/nianlun-from-scratch-v3-20261030` | 3781 | 26 |

## 局部修订与试验（Revision / Investigation Session）

针对既有制作的只读诊断或局部修订；不产生新的整曲候选。

| session | 日期 | 模型 | 主题 | 是否改动工程/音频 |
|---|---|---|---|---|
| [`20261030-2309__deepseek-v4.1f__nianlun-autopitch-offkey-20261030`](sessions/20261030-2309__deepseek-v4.1f__nianlun-autopitch-offkey-20261030/) | 20261030 | deepseek-v4.1f | 自动音高（DiffSinger dspitch）跑调归因 | 否（只读诊断） |
| [`20261030-2350__deepseek-v4.1f__nianlun-autopitch-fix-20261030`](sessions/20261030-2350__deepseek-v4.1f__nianlun-autopitch-fix-20261030/) | 20261030 | deepseek-v4.1f | 自动音高跑调修复：4 变体对照，逐音符 22.0c→1.1c | 是（新增候选，未改 v3 原件） |
| [`20261031-0045__grok-4.7__nianlun-autopitch-consonant-hold`](sessions/20261031-0045__grok-4.7__nianlun-autopitch-consonant-hold/) | 20261031 | grok-4.7 | 功能版自动音高：下一字声母上按住当前音高 | 是（新增候选，未改功能版原件和 v3） |

## 交付索引

见 [`releases/README.md`](releases/README.md)：本机候选交付物与逐条确认状态。
**没有用户试听确认的版本不算正式交付**；大文件仍在本机被忽略的目录里，不随 Git 发布。

## 全局未归属条目

有 7 个 scratch 条目无法从正文与目录确证歌曲归属，统一登记在
[`migration/20261030-reorganization/uncertain-items.tsv`](../../../migration/20261030-reorganization/uncertain-items.tsv)，
**不在每首歌重复列出**，以免暗示它们属于本歌。
