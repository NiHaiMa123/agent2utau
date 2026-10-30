# 最后一页（lastpage）制作索引

按「主制作 / 局部修订与试验 / 历史记录 / 交付」四类索引；
每个 session 目录含 `manifest.json`（song_id、run_id、日期、模型归属证据、状态、听感状态、
本机原始 run 路径、产物清单），`scripts/`、`reports/`、`feedback/` 可跟踪，`workspace/` 被忽略。
模型归属只按原始日志/manifest 判定，没有证据的一律 `unknown-model`——**这不是缺陷，是不猜**。
历史 session 的目录名保持原样，不追溯重命名。

## 主制作（Production Session）

一次完整制作/重做某歌的 run；有本地 compiled/delivery 产物。

| session | 日期 | 模型 | 本机 run 目录 | run 文件数 | session 内归档文件 |
|---|---|---|---|---|---|
| [`20261011__unknown-model__lastpage-accepted-baseline-20261011`](sessions/20261011__unknown-model__lastpage-accepted-baseline-20261011/) | 20261011 | unknown-model | `runs/production/lastpage-accepted-baseline-20261011` | 17 | 3 |
| [`20261011__unknown-model__lastpage-author-control-neutral-20261011`](sessions/20261011__unknown-model__lastpage-author-control-neutral-20261011/) | 20261011 | unknown-model | `runs/experiments/lastpage-author-control-neutral-20261011` | 111 | 4 |
| [`20261011__unknown-model__lastpage-author-pitch-ablation-20261011`](sessions/20261011__unknown-model__lastpage-author-pitch-ablation-20261011/) | 20261011 | unknown-model | `runs/experiments/lastpage-author-pitch-ablation-20261011` | 240 | 2 |
| [`20261011__unknown-model__lastpage-author-voice-swap-20261011`](sessions/20261011__unknown-model__lastpage-author-voice-swap-20261011/) | 20261011 | unknown-model | `runs/experiments/lastpage-author-voice-swap-20261011` | 109 | 2 |
| [`20261011__unknown-model__lastpage-conditioned-voicing-20261011`](sessions/20261011__unknown-model__lastpage-conditioned-voicing-20261011/) | 20261011 | unknown-model | `runs/experiments/lastpage-conditioned-voicing-20261011` | 134 | 1 |
| [`20261011__unknown-model__lastpage-li-kan-author-reference-20261011`](sessions/20261011__unknown-model__lastpage-li-kan-author-reference-20261011/) | 20261011 | unknown-model | `runs/research/lastpage-li-kan-author-reference-20261011` | 37 | 1 |
| [`20261011__unknown-model__lastpage-voice-baseline-20261011`](sessions/20261011__unknown-model__lastpage-voice-baseline-20261011/) | 20261011 | unknown-model | `runs/experiments/lastpage-voice-baseline-20261011` | 73 | 2 |
| [`20261012__unknown-model__lastpage-author-interaction-20261012`](sessions/20261012__unknown-model__lastpage-author-interaction-20261012/) | 20261012 | unknown-model | `runs/experiments/lastpage-author-interaction-20261012` | 80 | 3 |
| [`20261012__unknown-model__lastpage-own-bright-cute-20261012`](sessions/20261012__unknown-model__lastpage-own-bright-cute-20261012/) | 20261012 | unknown-model | `runs/experiments/lastpage-own-bright-cute-20261012` | 158 | 3 |
| [`20261012__unknown-model__lastpage-own-control-neutral-20261012`](sessions/20261012__unknown-model__lastpage-own-control-neutral-20261012/) | 20261012 | unknown-model | `runs/experiments/lastpage-own-control-neutral-20261012` | 78 | 5 |
| [`20261012__unknown-model__lastpage-own-li-dyn-20261012`](sessions/20261012__unknown-model__lastpage-own-li-dyn-20261012/) | 20261012 | unknown-model | `runs/experiments/lastpage-own-li-dyn-20261012` | 79 | 2 |
| [`20261012__unknown-model__lastpage-own-li-tenc-stages-20261012`](sessions/20261012__unknown-model__lastpage-own-li-tenc-stages-20261012/) | 20261012 | unknown-model | `runs/experiments/lastpage-own-li-tenc-stages-20261012` | 71 | 2 |
| [`20261012__unknown-model__lastpage-own-li-voic-stages-20261012`](sessions/20261012__unknown-model__lastpage-own-li-voic-stages-20261012/) | 20261012 | unknown-model | `runs/experiments/lastpage-own-li-voic-stages-20261012` | 77 | 2 |
| [`20261013__unknown-model__lastpage-own-li-entry-pitch-20261013`](sessions/20261013__unknown-model__lastpage-own-li-entry-pitch-20261013/) | 20261013 | unknown-model | `runs/experiments/lastpage-own-li-entry-pitch-20261013` | 71 | 3 |
| [`20261013__unknown-model__lastpage-skill-whole-song-20261013`](sessions/20261013__unknown-model__lastpage-skill-whole-song-20261013/) | 20261013 | unknown-model | `runs/production/lastpage-skill-whole-song-20261013` | 615 | 0 |
| [`20261014__unknown-model__lastpage-v04-dynamic-envelope-20261014`](sessions/20261014__unknown-model__lastpage-v04-dynamic-envelope-20261014/) | 20261014 | unknown-model | `runs/production/lastpage-v04-dynamic-envelope-20261014` | 213 | 0 |
| [`20261027__unknown-model__zuihouyiye-from-scratch-20261027`](sessions/20261027__unknown-model__zuihouyiye-from-scratch-20261027/) | 20261027 | unknown-model | `runs/production/zuihouyiye-from-scratch-20261027` | 4868 | 63 |

## 历史记录（Legacy Record）

只有报告/审计/反馈记录，没有独立脚本产物；多因被知识包按路径+SHA 绑定而保留原位。

| session | 日期 | 模型 | 本机 run 目录 | run 文件数 | session 内归档文件 |
|---|---|---|---|---|---|
| [`20261011__unknown-model__lastpage-conditioned-voicing-rejected-compile-20261011`](sessions/20261011__unknown-model__lastpage-conditioned-voicing-rejected-compile-20261011/) | 20261011 | unknown-model | `runs/research/lastpage-conditioned-voicing-rejected-compile-20261011` | 9 | 1 |
| [`20261012__unknown-model__lastpage-author-interaction-feedback-20261012`](sessions/20261012__unknown-model__lastpage-author-interaction-feedback-20261012/) | 20261012 | unknown-model | `runs/research/lastpage-author-interaction-feedback-20261012` | 14 | 1 |
| [`20261013__unknown-model__lastpage-li-condition-review-20261013`](sessions/20261013__unknown-model__lastpage-li-condition-review-20261013/) | 20261013 | unknown-model | `runs/research/lastpage-li-condition-review-20261013` | 22 | 0 |
| [`20261013__unknown-model__lastpage-texture-listening-preparation-20261013`](sessions/20261013__unknown-model__lastpage-texture-listening-preparation-20261013/) | 20261013 | unknown-model | `runs/research/lastpage-texture-listening-preparation-20261013` | 23 | 1 |
| [`20261014__unknown-model__lastpage-v04-acceptance-skill-20261014`](sessions/20261014__unknown-model__lastpage-v04-acceptance-skill-20261014/) | 20261014 | unknown-model | `runs/research/lastpage-v04-acceptance-skill-20261014` | 23 | 1 |
| [`20261014__unknown-model__lastpage-whole-song-v03-delivery-audit-20261014`](sessions/20261014__unknown-model__lastpage-whole-song-v03-delivery-audit-20261014/) | 20261014 | unknown-model | `runs/research/lastpage-whole-song-v03-delivery-audit-20261014` | 14 | 0 |

## 跨歌曲流程：对齐 P0/P1（2026-10-31）

本歌的锁定歌词（syllable_id）、GAME 归一化（
ote_id）、确定性字—音符映射（mapping.v1.json）与 baseline 工程
属于跨歌曲流程实验，记录在 [experiments/alignment/phoneme-alignment-p0p1-20261031/](../../../experiments/alignment/phoneme-alignment-p0p1-20261031/)，
本机产物在 
uns/production/phoneme-alignment-p0p1-20261031/lastpage/。歌词未经用户逐字确认（verification 非 user-confirmed），
未做音素写回（属 P2），听感未验证。

## 交付索引

见 [`releases/README.md`](releases/README.md)：本机候选交付物与逐条确认状态。
**没有用户试听确认的版本不算正式交付**；大文件仍在本机被忽略的目录里，不随 Git 发布。

## 因知识契约保留原位的文档

下列文档被 `docs/knowledge` 知识包按路径+SHA 引用，属字节保护范围，
按整理计划保留在 `docs/reports/` 原位（不搬进 songs/）：

- `docs/reports/lastpage/J-method-whole-song-v03-20261013.json`
- `docs/reports/lastpage/J-method-whole-song-v03-checker-audit-20261014.json`
- `docs/reports/lastpage/author-control-neutral-20261011.json`
- `docs/reports/lastpage/author-controls-feedback-20261012.json`
- `docs/reports/lastpage/author-interaction-20261012.json`
- `docs/reports/lastpage/author-interaction-feedback-20261012.json`
- `docs/reports/lastpage/author-pitch-ablation-20261011.json`
- `docs/reports/lastpage/author-pitch-feedback-20261011.json`
- `docs/reports/lastpage/author-voice-feedback-20261011.json`
- `docs/reports/lastpage/author-voice-swap-20261011.json`
- `docs/reports/lastpage/conditioned-voicing-feedback-20261011.json`
- `docs/reports/lastpage/conditioned-voicing-probe-20261011.json`
- `docs/reports/lastpage/li-condition-review-20261013.json`
- `docs/reports/lastpage/li-kan-author-reference-20261011.json`
- `docs/reports/lastpage/li-texture-listening-20261013.json`
- `docs/reports/lastpage/own-J-acceptance-and-whole-song-authorization-20261013.json`
- `docs/reports/lastpage/own-bright-cute-feedback-20261012.json`
- `docs/reports/lastpage/own-bright-cute-probe-20261012.json`
- `docs/reports/lastpage/own-control-neutral-probe-20261012.json`
- `docs/reports/lastpage/own-layering-feedback-20261012.json`
- `docs/reports/lastpage/own-li-DYN-feedback-20261012.json`
- `docs/reports/lastpage/own-li-DYN-probe-20261012.json`
- `docs/reports/lastpage/own-li-TENC-feedback-20261013.json`
- `docs/reports/lastpage/own-li-TENC-stages-probe-20261012.json`
- `docs/reports/lastpage/own-li-entry-pitch-feedback-20261013.json`
- `docs/reports/lastpage/own-li-entry-pitch-probe-20261013.json`
- `docs/reports/lastpage/own-li-voic-feedback-20261012.json`
- `docs/reports/lastpage/own-li-voic-stages-probe-20261012.json`
- `docs/reports/lastpage/v03-voice-volume-feedback-20261014.json`
- `docs/reports/lastpage/v04-DYN-acceptance-and-skill-20261014.json`
- `docs/reports/lastpage/v04-native-DYN-voice-recovery-20261014.json`
- `docs/reports/lastpage/voice-baseline-feedback-20261011.json`
- `docs/reports/lastpage/voice-baseline-probe-20261011.json`

## 全局未归属条目

有 7 个 scratch 条目无法从正文与目录确证歌曲归属，统一登记在
[`migration/20261030-reorganization/uncertain-items.tsv`](../../../migration/20261030-reorganization/uncertain-items.tsv)，
**不在每首歌重复列出**，以免暗示它们属于本歌。
