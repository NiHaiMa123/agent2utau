# 第二轮整理验收记录（phase2）

分支：`chore/reorg-phase2`（从 `e96f445` 开出）；上游基线 `e96f445`；
第一轮结束基线 `7dcd9cd`（1563 个跟踪文件）。

## 一、命令与退出码（本次实际运行）

| 命令 | 结果 | 退出码 |
|---|---|---|
| `python -m pytest -q` | 264 passed in 11.32s | 0 |
| `python tools/repository/check_repository.py --worktree` | `{"audio_payloads": 0, "author_projects": 3, "zip_members": 5, "skill_links": 129, "checks": "passed", "worktree_files": 1593}` | 0 |
| `git diff --check` | 无空白错误 | 0 |
| `git diff --cached --check` | 无空白错误 | 0 |
| `git ls-files \| Measure-Object -Line` | 1593 | — |

## 二、文件总数与零丢失

- 第一轮结束基线 `7dcd9cd`：1563 个跟踪文件
- 本轮执行时：1593 个跟踪文件（净变化 +30）
- 基线中在新索引里找不到同名路径的文件：12 个；其中能在本轮映射表中找到无损新路径的：12 个；**仍无法定位的：0 个**

逐项未定位清单：无

## 三、P0/P1/P2 各项结论

| 项 | 结论 | 说明 |
|---|---|---|
| P0-A 知识包 17 项 | done | 5 项被 SHA 锁定/历史快照 → 恢复 34061cd 原字节；12 项活动索引保留路径修复；无正文语义变化 |
| P0-B 失效链接 | done | 活动文档坏链 14 处全部修复；余下 826 处全在受保护历史快照内，只登记 |
| P1-C session 归并 | done | 59 个 session 保持数量不减少；按本机 run 结构分为 26 主制作 / 12 局部修订 / 21 历史记录；manifest 补回真实产物指针 |
| P1-D 交付索引 | done | 新建 songs/README.md 与 4 个 songs/*/releases/README.md；只索引不搬动 |
| P1-E 未来命名 | done | 规范写入 docs/guides/repository-layout.md 第 2、5 节；历史 unknown-model 不追溯 |
| P2-F tests/experiments/benchmarks 边界 | done | 7 个未归属 scratch 全部判定归位；experiments 各目录 README 改为列真实入口；benchmark protocol 补齐字段 |
| P2-G 目录规范 | done | docs/guides/repository-layout.md 重写为长期规范；docs/README 与根 README 对齐 |
| 本机 72GB 大目录 | deferred | 按任务书不强制物理搬迁；已在 songs/*/releases 与 manifest.original_run_path 索引 |
| 历史 AI 模型归属 | 不做 | 用户已决定不追溯；历史 manifest 保持 unknown-model |

## 四、受保护字节

- `research/baishuo/baishuo-projects.zip` sha256 `5bb41fcd67aa4cb9…` —— 与 7dcd9cd 基线一致：是
- `research/baishuo/projects/最后一页-有参by白烁.ustx` sha256 `5b064bb96262cf57…` —— 与 7dcd9cd 基线一致：是
- `research/baishuo/projects/花海+4-有参by白烁.ustx` sha256 `710dbc6ba98a3c20…` —— 与 7dcd9cd 基线一致：是
- `research/baishuo/projects/雨爱-有参by白烁.ustx` sha256 `01b08438ad3c8636…` —— 与 7dcd9cd 基线一致：是

## 五、链接审计分类（当前）

| 分类 | 数量 |
|---|---|
| 可在 GitHub 打开（ok） | 1622 |
| 仅本机存在（local-only，不随 Git 发布） | 169 |
| 外部链接（未做网络检查） | 238 |
| 历史冻结证据内的失效链接（只登记不修改） | 826 |
| **活动文档中的失效链接** | **0** |

## 六、工作树与提交

- 变更条目：135
- 分支：`chore/reorg-phase2`（**未推送**；未经授权不推送执行分支）
- 未改 Git 历史、未 force push、未删除任何旧文件/失败版本/被否决反馈。
