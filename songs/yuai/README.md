# 雨爱（yuai）制作索引

按「主制作 / 局部修订与试验 / 历史记录 / 交付」四类索引；
每个 session 目录含 `manifest.json`（song_id、run_id、日期、模型归属证据、状态、听感状态、
本机原始 run 路径、产物清单），`scripts/`、`reports/`、`feedback/` 可跟踪，`workspace/` 被忽略。
模型归属只按原始日志/manifest 判定，没有证据的一律 `unknown-model`——**这不是缺陷，是不猜**。
历史 session 的目录名保持原样，不追溯重命名。

## 主制作（Production Session）

一次完整制作/重做某歌的 run；有本地 compiled/delivery 产物。

| session | 日期 | 模型 | 本机 run 目录 | run 文件数 | session 内归档文件 |
|---|---|---|---|---|---|
| [`20261014__unknown-model__yuai-from-source-20261014`](sessions/20261014__unknown-model__yuai-from-source-20261014/) | 20261014 | unknown-model | `runs/production/yuai-from-source-20261014` | 2829 | 1 |
| [`20261015__unknown-model__yuai-intent-source-only-20261015`](sessions/20261015__unknown-model__yuai-intent-source-only-20261015/) | 20261015 | unknown-model | `runs/production/yuai-intent-source-only-20261015` | 3166 | 2 |
| [`20261015__unknown-model__yuai-skill-source-only-20261015`](sessions/20261015__unknown-model__yuai-skill-source-only-20261015/) | 20261015 | unknown-model | `runs/production/yuai-skill-source-only-20261015` | 3648 | 1 |
| [`20261017__unknown-model__yuai-s03-redraw-20261017`](sessions/20261017__unknown-model__yuai-s03-redraw-20261017/) | 20261017 | unknown-model | `runs/production/yuai-s03-redraw-20261017` | 162 | 1 |
| [`20261017__unknown-model__yuai-s04-redraw-20261017`](sessions/20261017__unknown-model__yuai-s04-redraw-20261017/) | 20261017 | unknown-model | `runs/production/yuai-s04-redraw-20261017` | 221 | 0 |

## 局部修订与试验（Revision / Experiment）

同次制作中的局部改版、试听候选、参数修正或对照试验。

| session | 日期 | 模型 | 本机 run 目录 | run 文件数 | session 内归档文件 |
|---|---|---|---|---|---|
| [`20261017__unknown-model__yuai-chuang-clarity-20261017`](sessions/20261017__unknown-model__yuai-chuang-clarity-20261017/) | 20261017 | unknown-model | `runs/production/yuai-chuang-clarity-20261017` | 32 | 1 |
| [`20261017__unknown-model__yuai-first-phrase-firmness-r02-20261017`](sessions/20261017__unknown-model__yuai-first-phrase-firmness-r02-20261017/) | 20261017 | unknown-model | `runs/production/yuai-first-phrase-firmness-r02-20261017` | 52 | 1 |
| [`20261017__unknown-model__yuai-first-phrase-firmness-r03-20261017`](sessions/20261017__unknown-model__yuai-first-phrase-firmness-r03-20261017/) | 20261017 | unknown-model | `runs/production/yuai-first-phrase-firmness-r03-20261017` | 27 | 1 |
| [`20261017__unknown-model__yuai-s03-breath-surface-20261017`](sessions/20261017__unknown-model__yuai-s03-breath-surface-20261017/) | 20261017 | unknown-model | `runs/production/yuai-s03-breath-surface-20261017` | 118 | 1 |
| [`20261018__unknown-model__yuai-first3-apsp-context-20261018`](sessions/20261018__unknown-model__yuai-first3-apsp-context-20261018/) | 20261018 | unknown-model | `runs/production/yuai-first3-apsp-context-20261018` | 60 | 0 |
| [`20261018__unknown-model__yuai-s03-P-writeback-20261018`](sessions/20261018__unknown-model__yuai-s03-P-writeback-20261018/) | 20261018 | unknown-model | `runs/production/yuai-s03-P-writeback-20261018` | 49 | 0 |
| [`20261018__unknown-model__yuai-s03-Q-writeback-after-R-rejection-20261018`](sessions/20261018__unknown-model__yuai-s03-Q-writeback-after-R-rejection-20261018/) | 20261018 | unknown-model | `runs/production/yuai-s03-Q-writeback-after-R-rejection-20261018` | 49 | 0 |
| [`20261018__unknown-model__yuai-s03-R-writeback-20261018`](sessions/20261018__unknown-model__yuai-s03-R-writeback-20261018/) | 20261018 | unknown-model | `runs/production/yuai-s03-R-writeback-20261018` | 48 | 0 |
| [`20261018__unknown-model__yuai-s03-le-breath-envelope-20261018`](sessions/20261018__unknown-model__yuai-s03-le-breath-envelope-20261018/) | 20261018 | unknown-model | `runs/production/yuai-s03-le-breath-envelope-20261018` | 44 | 0 |
| [`20261018__unknown-model__yuai-s03-xiayule-brec-20261018`](sessions/20261018__unknown-model__yuai-s03-xiayule-brec-20261018/) | 20261018 | unknown-model | `runs/production/yuai-s03-xiayule-brec-20261018` | 46 | 0 |
| [`20261018__unknown-model__yuai-s03s04-joint-context-20261018`](sessions/20261018__unknown-model__yuai-s03s04-joint-context-20261018/) | 20261018 | unknown-model | `runs/production/yuai-s03s04-joint-context-20261018` | 59 | 0 |
| [`20261018__unknown-model__yuai-s04-clear-context-20261018`](sessions/20261018__unknown-model__yuai-s04-clear-context-20261018/) | 20261018 | unknown-model | `runs/production/yuai-s04-clear-context-20261018` | 82 | 0 |

## 历史记录（Legacy Record）

只有报告/审计/反馈记录，没有独立脚本产物；多因被知识包按路径+SHA 绑定而保留原位。

| session | 日期 | 模型 | 本机 run 目录 | run 文件数 | session 内归档文件 |
|---|---|---|---|---|---|
| [`20261015__unknown-model__yuai-process-feedback-20261015`](sessions/20261015__unknown-model__yuai-process-feedback-20261015/) | 20261015 | unknown-model | `runs/review/yuai-process-feedback-20261015` | 11 | 0 |
| [`20261015__unknown-model__yuai-v02-two-pass-audit-20261015`](sessions/20261015__unknown-model__yuai-v02-two-pass-audit-20261015/) | 20261015 | unknown-model | `runs/review/yuai-v02-two-pass-audit-20261015` | 28 | 2 |
| [`20261016__unknown-model__yuai-phrase-handdraw-20261016`](sessions/20261016__unknown-model__yuai-phrase-handdraw-20261016/) | 20261016 | unknown-model | `runs/production/yuai-phrase-handdraw-20261016` | 1468 | 2 |
| [`20261017__unknown-model__yuai-first-phrase-firmness-20261017`](sessions/20261017__unknown-model__yuai-first-phrase-firmness-20261017/) | 20261017 | unknown-model | `runs/production/yuai-first-phrase-firmness-20261017` | 55 | 1 |
| [`20261017__unknown-model__yuai-first3-continuity-20261017`](sessions/20261017__unknown-model__yuai-first3-continuity-20261017/) | 20261017 | unknown-model | `runs/production/yuai-first3-continuity-20261017` | 123 | 1 |
| [`20261017__unknown-model__yuai-s03-F-writeback-20261017`](sessions/20261017__unknown-model__yuai-s03-F-writeback-20261017/) | 20261017 | unknown-model | `runs/production/yuai-s03-F-writeback-20261017` | 126 | 0 |
| [`20261017__unknown-model__yuai-s03-author-comparison-20261017`](sessions/20261017__unknown-model__yuai-s03-author-comparison-20261017/) | 20261017 | unknown-model | `runs/review/yuai-s03-author-comparison-20261017` | 23 | 0 |
| [`20261017__unknown-model__yuai-track-comparison-20261017`](sessions/20261017__unknown-model__yuai-track-comparison-20261017/) | 20261017 | unknown-model | `runs/review/yuai-track-comparison-20261017` | 20 | 1 |
| [`20261018__unknown-model__yuai-apsp-context-link-20261018`](sessions/20261018__unknown-model__yuai-apsp-context-link-20261018/) | 20261018 | unknown-model | `runs/review/yuai-apsp-context-link-20261018` | 21 | 0 |
| [`20261018__unknown-model__yuai-first4-full-parameter-audit-20261018`](sessions/20261018__unknown-model__yuai-first4-full-parameter-audit-20261018/) | 20261018 | unknown-model | `runs/review/yuai-first4-full-parameter-audit-20261018` | 302 | 0 |
| [`20261018__unknown-model__yuai-s03-context-mechanism-20261018`](sessions/20261018__unknown-model__yuai-s03-context-mechanism-20261018/) | 20261018 | unknown-model | `runs/research/yuai-s03-context-mechanism-20261018` | 15 | 0 |
| [`20261018__unknown-model__yuai-s03-core-surface-20261018`](sessions/20261018__unknown-model__yuai-s03-core-surface-20261018/) | 20261018 | unknown-model | `runs/research/yuai-s03-core-surface-20261018` | 110 | 0 |
| [`20261018__unknown-model__yuai-s03-frame-voice-contrast-20261018`](sessions/20261018__unknown-model__yuai-s03-frame-voice-contrast-20261018/) | 20261018 | unknown-model | `runs/research/yuai-s03-frame-voice-contrast-20261018` | 70 | 0 |
| [`20261018__unknown-model__yuai-voice-remap-dialog-20261018`](sessions/20261018__unknown-model__yuai-voice-remap-dialog-20261018/) | 20261018 | unknown-model | `runs/review/yuai-voice-remap-dialog-20261018` | 38 | 0 |
| [`20261018__unknown-model__yuai-xiayule-author-recheck-20261018`](sessions/20261018__unknown-model__yuai-xiayule-author-recheck-20261018/) | 20261018 | unknown-model | `runs/review/yuai-xiayule-author-recheck-20261018` | 13 | 0 |

## 跨歌曲流程：对齐 P0/P1（2026-10-31）

本歌的锁定歌词（syllable_id）、GAME 归一化（
ote_id）、确定性字—音符映射（mapping.v1.json）与 baseline 工程
属于跨歌曲流程实验，记录在 [experiments/alignment/phoneme-alignment-p0p1-20261031/](../../../experiments/alignment/phoneme-alignment-p0p1-20261031/)，
本机产物在 
uns/production/phoneme-alignment-p0p1-20261031/yuai/。歌词未经用户逐字确认（verification 非 user-confirmed），
未做音素写回（属 P2），听感未验证。

## 交付索引

见 [`releases/README.md`](releases/README.md)：本机候选交付物与逐条确认状态。
**没有用户试听确认的版本不算正式交付**；大文件仍在本机被忽略的目录里，不随 Git 发布。

## 因知识契约保留原位的文档

下列文档被 `docs/knowledge` 知识包按路径+SHA 引用，属字节保护范围，
按整理计划保留在 `docs/reports/` 原位（不搬进 songs/）：

- `docs/reports/yuai/apsp-context-link-audit-20261018.json`
- `docs/reports/yuai/apsp-context-link-audit-20261018.md`
- `docs/reports/yuai/chuang-uang-clarity-accepted-20261017.json`
- `docs/reports/yuai/chuang-uang-clarity-candidate-20261017.json`
- `docs/reports/yuai/chuang-uang-clarity-feedback-20261017.json`
- `docs/reports/yuai/design-process-feedback-20261015.json`
- `docs/reports/yuai/design-process-rejection-20261015.md`
- `docs/reports/yuai/first-phrase-firmness-candidate-20261017.json`
- `docs/reports/yuai/first-phrase-firmness-feedback-20261017.json`
- `docs/reports/yuai/first-phrase-firmness-r01-feedback-20261017.json`
- `docs/reports/yuai/first-phrase-firmness-r02-20261017.json`
- `docs/reports/yuai/first-phrase-firmness-r02-feedback-20261017.json`
- `docs/reports/yuai/first-phrase-firmness-r03-20261017.json`
- `docs/reports/yuai/first-phrase-firmness-r03-accepted-20261017.json`
- `docs/reports/yuai/first3-apsp-context-candidate-20261018.json`
- `docs/reports/yuai/first3-apsp-context-candidate-20261018.md`
- `docs/reports/yuai/first3-apsp-provenance-recheck-20261018.json`
- `docs/reports/yuai/first4-full-parameter-audit-20261018.json`
- `docs/reports/yuai/first4-full-parameter-audit-20261018.md`
- `docs/reports/yuai/fourth-phrase-clear-context-candidate-20261018.json`
- `docs/reports/yuai/fourth-phrase-clear-context-candidate-20261018.md`
- `docs/reports/yuai/fourth-phrase-dark-feedback-20261018.json`
- `docs/reports/yuai/fourth-phrase-dark-feedback-20261018.md`
- `docs/reports/yuai/fourth-phrase-redraw-20261017.json`
- `docs/reports/yuai/fourth-phrase-redraw-20261017.md`
- `docs/reports/yuai/from-source-production-record-20261015.json`
- `docs/reports/yuai/learned-conditions-carryover-20261016-index.json`
- `docs/reports/yuai/new-skill-source-only-v02-20261015.json`
- `docs/reports/yuai/phrase-handdraw-first14-preview-20261017.json`
- `docs/reports/yuai/phrase-handdraw-source-only-pause-20261017.json`
- `docs/reports/yuai/same-project-review-workflow-request-20261018.json`
- `docs/reports/yuai/source-intent-G-whole-candidate-20261016.json`
- `docs/reports/yuai/source-intent-pilots-20261016.json`
- `docs/reports/yuai/third-fourth-joint-context-accepted-20261018.json`
- `docs/reports/yuai/third-fourth-joint-context-accepted-20261018.md`
- `docs/reports/yuai/third-fourth-joint-context-candidate-20261018.json`
- `docs/reports/yuai/third-fourth-joint-context-candidate-20261018.md`
- `docs/reports/yuai/third-phrase-F-native-writeback-20261017.json`
- `docs/reports/yuai/third-phrase-F-native-writeback-20261017.md`
- `docs/reports/yuai/third-phrase-F-writeback-not-accepted-20261017.json`
- `docs/reports/yuai/third-phrase-P-native-writeback-20261018.json`
- `docs/reports/yuai/third-phrase-P-native-writeback-20261018.md`
- `docs/reports/yuai/third-phrase-P-still-problem-full-audit-request-20261018.json`
- `docs/reports/yuai/third-phrase-P-tentative-feedback-20261018.json`
- `docs/reports/yuai/third-phrase-Q-native-after-R-rejection-20261018.json`
- `docs/reports/yuai/third-phrase-Q-native-after-R-rejection-20261018.md`
- `docs/reports/yuai/third-phrase-Q-rejected-context-question-20261018.json`
- `docs/reports/yuai/third-phrase-R-native-writeback-20261018.json`
- `docs/reports/yuai/third-phrase-R-native-writeback-20261018.md`
- `docs/reports/yuai/third-phrase-R-rejected-proximity-clarification-20261018.json`
- `docs/reports/yuai/third-phrase-airy-clarification-20261017.json`
- `docs/reports/yuai/third-phrase-author-comparison-20261017.json`
- `docs/reports/yuai/third-phrase-author-comparison-20261017.md`
- `docs/reports/yuai/third-phrase-breath-surface-candidate-20261017.json`
- `docs/reports/yuai/third-phrase-consistency-residual-feedback-20261017.json`
- `docs/reports/yuai/third-phrase-context-mechanism-20261018.json`
- `docs/reports/yuai/third-phrase-context-mechanism-20261018.md`
- `docs/reports/yuai/third-phrase-continuity-feedback-20261017.json`
- `docs/reports/yuai/third-phrase-continuity-revision-20261017.json`
- `docs/reports/yuai/third-phrase-continuity-revision-insufficient-20261017.json`
- `docs/reports/yuai/third-phrase-core-surface-contrasts-20261018.json`
- `docs/reports/yuai/third-phrase-core-surface-contrasts-20261018.md`
- `docs/reports/yuai/third-phrase-frame-voice-contrast-20261018.json`
- `docs/reports/yuai/third-phrase-frame-voice-contrast-20261018.md`
- `docs/reports/yuai/third-phrase-le-breath-envelope-candidate-20261018.json`
- `docs/reports/yuai/third-phrase-le-breath-envelope-candidate-20261018.md`
- `docs/reports/yuai/third-phrase-le-breath-feedback-20261018.json`
- `docs/reports/yuai/third-phrase-le-breath-feedback-20261018.md`
- `docs/reports/yuai/third-phrase-project-airy-fourth-accepted-20261017.json`
- `docs/reports/yuai/third-phrase-redraw-20261017.json`
- `docs/reports/yuai/third-phrase-xiayule-airy-feedback-20261018.json`
- `docs/reports/yuai/third-phrase-xiayule-airy-feedback-20261018.md`
- `docs/reports/yuai/third-phrase-xiayule-brec-candidate-20261018.json`
- `docs/reports/yuai/third-phrase-xiayule-brec-candidate-20261018.md`
- `docs/reports/yuai/third-phrase-xiayule-brec-rejected-20261018.json`
- `docs/reports/yuai/third-phrase-xiayule-brec-rejected-20261018.md`
- `docs/reports/yuai/v02-two-pass-failure-record-20261015.json`
- `docs/reports/yuai/voice-remap-dialog-audit-20261018.json`
- `docs/reports/yuai/voice-remap-dialog-audit-20261018.md`
- `docs/reports/yuai/xiayule-author-focused-recheck-20261018.json`
- `docs/reports/yuai/xiayule-author-focused-recheck-20261018.md`

## 全局未归属条目

有 7 个 scratch 条目无法从正文与目录确证歌曲归属，统一登记在
[`migration/20261030-reorganization/uncertain-items.tsv`](../../../migration/20261030-reorganization/uncertain-items.tsv)，
**不在每首歌重复列出**，以免暗示它们属于本歌。
