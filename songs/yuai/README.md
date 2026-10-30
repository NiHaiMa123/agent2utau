# 雨爱（yuai）制作索引

本目录按「歌曲 → 日期/模型 → 制作 session → 脚本/报告/音频」组织。
每个 session 的 `manifest.json` 记录制作日期、模型归属证据、状态与听感状态；
`workspace/` 放本次制作的原始 run 数据（被 .gitignore 忽略；历史 run 因含
硬编码绝对路径与 OpenUtau 工程引用，暂留原址，见 migration 的 deferred 清单）。

## 制作 session

| session | 日期 | 模型 | 状态 | 听感 | 本地 run 目录 | 归档文件数 |
|---|---|---|---|---|---|---|
| `20261014__unknown-model__yuai-from-source-20261014` | 20261014 | unknown-model | historical_unverified | unknown | — | 2 |
| `20261015__unknown-model__yuai-intent-source-only-20261015` | 20261015 | unknown-model | historical_unverified | unknown | — | 3 |
| `20261015__unknown-model__yuai-process-feedback-20261015` | 20261015 | unknown-model | historical_unverified | unknown | — | 1 |
| `20261015__unknown-model__yuai-skill-source-only-20261015` | 20261015 | unknown-model | historical_unverified | unknown | — | 2 |
| `20261015__unknown-model__yuai-v02-two-pass-audit-20261015` | 20261015 | unknown-model | historical_unverified | unknown | — | 3 |
| `20261016__unknown-model__yuai-phrase-handdraw-20261016` | 20261016 | unknown-model | historical_unverified | unknown | — | 3 |
| `20261017__unknown-model__yuai-chuang-clarity-20261017` | 20261017 | unknown-model | historical_unverified | unknown | — | 2 |
| `20261017__unknown-model__yuai-first-phrase-firmness-20261017` | 20261017 | unknown-model | historical_unverified | unknown | — | 2 |
| `20261017__unknown-model__yuai-first-phrase-firmness-r02-20261017` | 20261017 | unknown-model | historical_unverified | unknown | — | 2 |
| `20261017__unknown-model__yuai-first-phrase-firmness-r03-20261017` | 20261017 | unknown-model | historical_unverified | unknown | — | 2 |
| `20261017__unknown-model__yuai-first3-continuity-20261017` | 20261017 | unknown-model | historical_unverified | unknown | — | 2 |
| `20261017__unknown-model__yuai-s03-F-writeback-20261017` | 20261017 | unknown-model | historical_unverified | unknown | — | 1 |
| `20261017__unknown-model__yuai-s03-author-comparison-20261017` | 20261017 | unknown-model | historical_unverified | unknown | — | 1 |
| `20261017__unknown-model__yuai-s03-breath-surface-20261017` | 20261017 | unknown-model | historical_unverified | unknown | — | 2 |
| `20261017__unknown-model__yuai-s03-redraw-20261017` | 20261017 | unknown-model | historical_unverified | unknown | — | 2 |
| `20261017__unknown-model__yuai-s04-redraw-20261017` | 20261017 | unknown-model | historical_unverified | unknown | — | 1 |
| `20261017__unknown-model__yuai-track-comparison-20261017` | 20261017 | unknown-model | historical_unverified | unknown | — | 2 |
| `20261018__unknown-model__yuai-apsp-context-link-20261018` | 20261018 | unknown-model | historical_unverified | unknown | — | 1 |
| `20261018__unknown-model__yuai-first3-apsp-context-20261018` | 20261018 | unknown-model | historical_unverified | unknown | — | 1 |
| `20261018__unknown-model__yuai-first4-full-parameter-audit-20261018` | 20261018 | unknown-model | historical_unverified | unknown | — | 1 |
| `20261018__unknown-model__yuai-s03-P-writeback-20261018` | 20261018 | unknown-model | historical_unverified | unknown | — | 1 |
| `20261018__unknown-model__yuai-s03-Q-writeback-after-R-rejection-20261018` | 20261018 | unknown-model | historical_unverified | unknown | — | 1 |
| `20261018__unknown-model__yuai-s03-R-writeback-20261018` | 20261018 | unknown-model | historical_unverified | unknown | — | 1 |
| `20261018__unknown-model__yuai-s03-context-mechanism-20261018` | 20261018 | unknown-model | historical_unverified | unknown | — | 1 |
| `20261018__unknown-model__yuai-s03-core-surface-20261018` | 20261018 | unknown-model | historical_unverified | unknown | — | 1 |
| `20261018__unknown-model__yuai-s03-frame-voice-contrast-20261018` | 20261018 | unknown-model | historical_unverified | unknown | — | 1 |
| `20261018__unknown-model__yuai-s03-le-breath-envelope-20261018` | 20261018 | unknown-model | historical_unverified | unknown | — | 1 |
| `20261018__unknown-model__yuai-s03-xiayule-brec-20261018` | 20261018 | unknown-model | historical_unverified | unknown | — | 1 |
| `20261018__unknown-model__yuai-s03s04-joint-context-20261018` | 20261018 | unknown-model | historical_unverified | unknown | — | 1 |
| `20261018__unknown-model__yuai-s04-clear-context-20261018` | 20261018 | unknown-model | historical_unverified | unknown | — | 1 |
| `20261018__unknown-model__yuai-voice-remap-dialog-20261018` | 20261018 | unknown-model | historical_unverified | unknown | — | 1 |
| `20261018__unknown-model__yuai-xiayule-author-recheck-20261018` | 20261018 | unknown-model | historical_unverified | unknown | — | 1 |

## 因知识契约保留原位的文档

下列文档被 `docs/knowledge` 的知识包按路径与 SHA 引用，属于字节保护范围，
按整理计划保留在 `docs/reports/` 原位，由本索引引用：

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

## 未确定归属（保留原址）

- `scratch/check_phones_structure.py`（正文与目录都无法确证归属，按计划不动）
- `scratch/check_polyphones.py`（正文与目录都无法确证归属，按计划不动）
- `scratch/read_test_polyphones.py`（正文与目录都无法确证归属，按计划不动）
- `scratch/test_compile_phrase0.py`（正文与目录都无法确证归属，按计划不动）
- `scratch/test_compile_phrase0_full.py`（正文与目录都无法确证归属，按计划不动）
- `scratch/test_modified_phones.json`（正文与目录都无法确证归属，按计划不动）
- `scratch/test_polyphones.json`（正文与目录都无法确证归属，按计划不动）

## 其它入口

- `assets/`：歌词与来源信息（非媒体）
- `reports/legacy/`：无法定位到具体 session 的历史报告
- `releases/`：明确选出的交付版索引/音频/USTX
