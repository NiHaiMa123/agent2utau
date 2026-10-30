# 第二轮整理（收尾）· 交付说明

依据：`PROJECT_REORGANIZATION_PLAN_20261030.md`（第二轮收尾版，提交 e96f445）。
本目录是**一次性任务书对应的验收记录**，长期规范见 [`docs/guides/repository-layout.md`](../../../docs/guides/repository-layout.md)。

## 做了什么

| 项 | 结论 | 详见 |
|---|---|---|
| **P0-A** 知识包 17 项字节差异 | 5 项被 SHA 锁定/历史快照 → **恢复 34061cd 原字节**；12 项活动索引保留路径修复（无正文语义变化） | [knowledge-diff-audit.md](knowledge-diff-audit.md) |
| **P0-B** 失效链接 | 活动文档坏链 **14 处全部修复**；余下 826 处全在受保护历史快照内，只登记不改 | [links-audit.md](links-audit.md) |
| **P1-C** session 空壳/过度拆分 | 59 个 session **数量不减少**，按本机 run 结构分类为 26 主制作 / 12 局部修订 / 21 历史记录；manifest 补回真实产物指针与 `session_kind` | [session-consolidation.tsv](session-consolidation.tsv) |
| **P1-D** 交付索引 | 新建 [`songs/README.md`](../../../songs/README.md) 与 4 个 `songs/*/releases/README.md`；只索引、不搬动大文件 | [release-index-audit.md](release-index-audit.md) |
| **P1-E** 未来命名/manifest | 写入长期规范第 2、5 节；**历史 unknown-model 原样接受，不追溯** | [repository-layout.md](../../../docs/guides/repository-layout.md) |
| **P2-F** tests/experiments/benchmarks 边界 | 7 个未归属 scratch 全部判定归位（5 → experiments/alignment，2 → 最后一页 session）；experiments 各 README 改为列真实入口；benchmark protocol 补齐任务书要求字段 | `../../../../experiments/` |
| **P2-G** 目录规范 | `docs/guides/repository-layout.md` 重写为长期规范；根 README / docs/README 对齐 | — |
| 本机 72GB 大目录 | **deferred**：按任务书不强制物理搬迁，已在 releases 索引与 `manifest.original_run_path` 建立索引 | — |

## 本轮明确**没有**做的事

- 没有追溯历史 AI 模型归属（用户已决定：过去哪版是哪个 AI 做的，不用查）。
- 没有把 59 个 session 合成一个漂亮数字。
- 没有搬动 `runs/`、`demo/`、`projects/`、`models/`、`external/` 里的任何文件。
- 没有删除、覆盖任何历史成果、失败候选、被否决反馈或原始实验记录。
- 没有改生产代码、算法、声学结论；没有触发 OpenUtau 渲染或 F0/ASR 再分析。

## 目录

```
phase2/
  README.md                     本文件
  knowledge-diff-audit.md       17 项逐项 diff / 判定 / 最终 SHA
  links-audit.md                链接分类、已修与未修
  session-consolidation.tsv     old_path / new_path / 理由 / 状态
  release-index-audit.md        交付索引与本机可用性
  verification.md               命令、退出码与具体验证结果
  tools/                        本轮使用的审计与整理脚本（可复跑）
```

第一轮的验收记录仍在 [`../verification.md`](../verification.md)，保留作历史证据（其中的 1568 计数已过期：实际基线为 1563）。
