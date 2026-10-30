# songs/ — 歌曲制作总入口

每首歌有完整制作索引与交付索引；新制作的 session 与交付物命名规则见
[docs/guides/repository-layout.md](../docs/guides/repository-layout.md)。

| 歌曲 | 目录 | 制作 session | 主制作 | 局部修订/试验 | 历史记录 | 本机候选交付物 | 用户确认状态 |
|---|---|---|---|---|---|---|---|
| 年轮 | [`nianlun/`](nianlun/) | 4 | 4 | 0 | 0 | 11 | 无已确认整曲交付（v1/v2 被否决；2026-10-30 的 v3 待试听） |
| 雨爱 | [`yuai/`](yuai/) | 32 | 5 | 12 | 15 | 39 | 仅第三/四句局部被确认，非整曲 |
| 最后一页 | [`lastpage/`](lastpage/) | 23 | 17 | 0 | 6 | 81 | 有整曲授权记录（20261013），版本以本机 delivery 为准 |
| 花海 | [`huahai/`](huahai/) | 0 | 0 | 0 | 0 | 0 | 暂无已确认交付 |

## 目录约定

- `sessions/<日期>__<模型>__<run-id>/`：一次制作；`manifest.json` 是它的索引。
- `reports/legacy/`：无法定位到具体 session 的历史报告。
- `releases/`：交付索引（只索引，不搬动大文件）。
- `workspace/`：本机原始 run 数据，被 .gitignore 排除。
