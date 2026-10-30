# 花海（huahai）制作索引

本目录按「歌曲 → 日期/模型 → 制作 session → 脚本/报告/音频」组织。
每个 session 的 `manifest.json` 记录制作日期、模型归属证据、状态与听感状态；
`workspace/` 放本次制作的原始 run 数据（被 .gitignore 忽略；历史 run 因含
硬编码绝对路径与 OpenUtau 工程引用，暂留原址，见 migration 的 deferred 清单）。

## 制作 session

| session | 日期 | 模型 | 状态 | 听感 | 本地 run 目录 | 归档文件数 |
|---|---|---|---|---|---|---|

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
