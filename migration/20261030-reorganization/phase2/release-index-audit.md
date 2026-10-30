# P1-D 交付索引审计

本轮**只建索引，不搬动任何音频/USTX/模型**，也不复制同一份音频到多处。
大文件仍在被 .gitignore 排除的本机目录里，索引给出本机相对路径与确认状态。

| 歌曲 | session（主制作/修订/历史） | 本机候选交付物 | 用户确认状态 |
|---|---|---|---|
| 年轮 | 4（4/0/0） | 0 | **无已确认的整曲交付**。v1/v2 被用户明确否决（“完全不行”）；2026-10-30 的 v3（照源直描重制）已渲染并复检通过，但**等用户试听确认**，因此不写成正式交付。 |
| 雨爱 | 32（5/12/15） | 0 | **仅第三/四句共同上下文被用户确认**（2026-10-18 “好像好了”，记录写明范围限第三/四句局部，非整曲接受）。其它候选版本均未确认。 |
| 最后一页 | 23（17/0/6） | 0 | 存在整曲授权/接受记录（`own-J-acceptance-and-whole-song-authorization-20261013`），但本轮**未逐条比对版本**，故各候选在索引里标“未逐条确认”，不自动选“最佳版本”。 |
| 花海 | 0（0/0/0） | 0 | **暂无已确认正式交付**，也无本机候选目录。 |

## 每首歌的索引入口

- [`songs/nianlun/releases/README.md`](../../songs/nianlun/releases/README.md)
- [`songs/yuai/releases/README.md`](../../songs/yuai/releases/README.md)
- [`songs/lastpage/releases/README.md`](../../songs/lastpage/releases/README.md)
- [`songs/huahai/releases/README.md`](../../songs/huahai/releases/README.md)

## 做法与边界

- 候选来源：本机 `runs/<类别>/<run-id>/delivery/` 与 `compiled*/` 下的实际文件（真实存在才登记）。
- **不自动把写着 FINAL / v20 / v23 的版本选成正式交付**；没有用户试听证据的一律标“未逐条确认”。
- 音频、USTX、模型仍在本机被忽略的目录，不随 Git 发布；索引里标明“仅本机可见”。
- `releases/` 下不放空记录占位：没有候选的歌直接写“暂无”。
