# 最后一页（lastpage）制作索引

本目录按「歌曲 → 日期/模型 → 制作 session → 脚本/报告/音频」组织。
每个 session 的 `manifest.json` 记录制作日期、模型归属证据、状态与听感状态；
`workspace/` 放本次制作的原始 run 数据（被 .gitignore 忽略；历史 run 因含
硬编码绝对路径与 OpenUtau 工程引用，暂留原址，见 migration 的 deferred 清单）。

## 制作 session

| session | 日期 | 模型 | 状态 | 听感 | 本地 run 目录 | 归档文件数 |
|---|---|---|---|---|---|---|
| `20261011__unknown-model__lastpage-accepted-baseline-20261011` | 20261011 | unknown-model | historical_unverified | unknown | — | 4 |
| `20261011__unknown-model__lastpage-author-control-neutral-20261011` | 20261011 | unknown-model | historical_unverified | unknown | — | 5 |
| `20261011__unknown-model__lastpage-author-pitch-ablation-20261011` | 20261011 | unknown-model | historical_unverified | unknown | — | 3 |
| `20261011__unknown-model__lastpage-author-voice-swap-20261011` | 20261011 | unknown-model | historical_unverified | unknown | — | 3 |
| `20261011__unknown-model__lastpage-conditioned-voicing-20261011` | 20261011 | unknown-model | historical_unverified | unknown | — | 2 |
| `20261011__unknown-model__lastpage-conditioned-voicing-rejected-compile-20261011` | 20261011 | unknown-model | historical_unverified | unknown | — | 2 |
| `20261011__unknown-model__lastpage-li-kan-author-reference-20261011` | 20261011 | unknown-model | historical_unverified | unknown | — | 2 |
| `20261011__unknown-model__lastpage-voice-baseline-20261011` | 20261011 | unknown-model | historical_unverified | unknown | — | 3 |
| `20261012__unknown-model__lastpage-author-interaction-20261012` | 20261012 | unknown-model | historical_unverified | unknown | — | 4 |
| `20261012__unknown-model__lastpage-author-interaction-feedback-20261012` | 20261012 | unknown-model | historical_unverified | unknown | — | 2 |
| `20261012__unknown-model__lastpage-own-bright-cute-20261012` | 20261012 | unknown-model | historical_unverified | unknown | — | 4 |
| `20261012__unknown-model__lastpage-own-control-neutral-20261012` | 20261012 | unknown-model | historical_unverified | unknown | — | 6 |
| `20261012__unknown-model__lastpage-own-li-dyn-20261012` | 20261012 | unknown-model | historical_unverified | unknown | — | 3 |
| `20261012__unknown-model__lastpage-own-li-tenc-stages-20261012` | 20261012 | unknown-model | historical_unverified | unknown | — | 3 |
| `20261012__unknown-model__lastpage-own-li-voic-stages-20261012` | 20261012 | unknown-model | historical_unverified | unknown | — | 3 |
| `20261013__unknown-model__lastpage-li-condition-review-20261013` | 20261013 | unknown-model | historical_unverified | unknown | — | 1 |
| `20261013__unknown-model__lastpage-own-li-entry-pitch-20261013` | 20261013 | unknown-model | historical_unverified | unknown | — | 4 |
| `20261013__unknown-model__lastpage-skill-whole-song-20261013` | 20261013 | unknown-model | historical_unverified | unknown | — | 1 |
| `20261013__unknown-model__lastpage-texture-listening-preparation-20261013` | 20261013 | unknown-model | historical_unverified | unknown | — | 2 |
| `20261014__unknown-model__lastpage-v04-acceptance-skill-20261014` | 20261014 | unknown-model | historical_unverified | unknown | — | 2 |
| `20261014__unknown-model__lastpage-v04-dynamic-envelope-20261014` | 20261014 | unknown-model | historical_unverified | unknown | — | 1 |
| `20261014__unknown-model__lastpage-whole-song-v03-delivery-audit-20261014` | 20261014 | unknown-model | historical_unverified | unknown | — | 1 |
| `20261027__unknown-model__zuihouyiye-from-scratch-20261027` | 20261027 | unknown-model | historical_unverified | unknown | `runs/production/zuihouyiye-from-scratch-20261027` | 64 |

## 因知识契约保留原位的文档

下列文档被 `docs/knowledge` 的知识包按路径与 SHA 引用，属于字节保护范围，
按整理计划保留在 `docs/reports/` 原位，由本索引引用：

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
