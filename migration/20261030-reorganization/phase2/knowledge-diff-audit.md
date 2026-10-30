# P0-A 知识包 17 项改动审计

基线：`34061cd`（第一轮搬迁前）对比当前执行 HEAD。

判定口径：① 仅换行符 ② 仅路径/相对链接调整 ③ 正文数据/语义变化 ④ 未能确认。

处理原则：被 SHA 锁定或属历史快照的，**恢复第一轮前的精确字节**；
活动知识索引的路径修复在确认新链接正确且被使用时保留。

| 文件 | 旧 SHA(34061cd) | 新 SHA(执行时) | 判定 | 处理 |
|---|---|---|---|---|
| `docs/knowledge/acoustic-manifestations-20261009/conditional-responses.md` | `1f0357fbee2e4ee7…` | `8b04a8dfd33504a9…` | ② 仅路径/相对链接调整 | 保留路径修复（活动索引，新链接已验证可解析） |
| `docs/knowledge/acoustic-manifestations-20261009/history/pre-table2-2a-20261010/docs/knowledge/acoustic-manifestations-20261009/conditional-responses.md` | `f30555954cd8d96d…` | `f30555954cd8d96d…` | ② 仅路径/相对链接调整 | **恢复原字节**（SHA 锁定/历史快照） |
| `docs/knowledge/acoustic-manifestations-20261009/history/pre-table2-2b-20261010/docs/knowledge/acoustic-manifestations-20261009/conditional-responses.md` | `f30555954cd8d96d…` | `f30555954cd8d96d…` | ② 仅路径/相对链接调整 | **恢复原字节**（SHA 锁定/历史快照） |
| `docs/knowledge/acoustic-manifestations-20261009/history/pre-table2-2c-20261010/docs/knowledge/acoustic-manifestations-20261009/conditional-responses.md` | `0bdf3e0062e8de6d…` | `0bdf3e0062e8de6d…` | ② 仅路径/相对链接调整 | **恢复原字节**（SHA 锁定/历史快照） |
| `docs/knowledge/acoustic-manifestations-20261009/history/pre-table2-2d-20261010/docs/knowledge/acoustic-manifestations-20261009/conditional-responses.md` | `606fba0e23cca6f2…` | `606fba0e23cca6f2…` | ② 仅路径/相对链接调整 | **恢复原字节**（SHA 锁定/历史快照） |
| `docs/knowledge/acoustic-manifestations-20261009/table2-DYN-delivery-index-20261012.md` | `e0c68e6b06c0ef48…` | `f489b8dbfb5bd3e2…` | ② 仅路径/相对链接调整 | 保留路径修复（活动索引，新链接已验证可解析） |
| `docs/knowledge/acoustic-manifestations-20261009/table2-DYN-feedback-index-20261012.md` | `8734ae009c005df2…` | `285ac3282f666b47…` | ② 仅路径/相对链接调整 | 保留路径修复（活动索引，新链接已验证可解析） |
| `docs/knowledge/acoustic-manifestations-20261009/table2-TENC-delivery-index-20261012.md` | `ff51566427b6cc47…` | `0e26a4103e7e0b2d…` | ② 仅路径/相对链接调整 | 保留路径修复（活动索引，新链接已验证可解析） |
| `docs/knowledge/acoustic-manifestations-20261009/table2-TENC-feedback-index-20261013.md` | `c82a64c04c739e5f…` | `fc097e000616c9b9…` | ② 仅路径/相对链接调整 | 保留路径修复（活动索引，新链接已验证可解析） |
| `docs/knowledge/acoustic-manifestations-20261009/table2-entry-pitch-delivery-index-20261013.md` | `2e9237a4840bd33d…` | `9e982acdb847441f…` | ② 仅路径/相对链接调整 | 保留路径修复（活动索引，新链接已验证可解析） |
| `docs/knowledge/acoustic-manifestations-20261009/table2-entry-pitch-feedback-index-20261013.md` | `4ddf91b63673a572…` | `36b93daf5d6cf25c…` | ② 仅路径/相对链接调整 | 保留路径修复（活动索引，新链接已验证可解析） |
| `docs/knowledge/acoustic-manifestations-20261009/table2-existing-listening-queue-20261011.md` | `c74d98cd97521e53…` | `c74d98cd97521e53…` | ② 仅路径/相对链接调整 | **恢复原字节**（SHA 锁定/历史快照） |
| `docs/knowledge/acoustic-manifestations-20261009/table2-layering-delivery-index-20261012.md` | `df2f80e272618d58…` | `a39d6bd05ef726fb…` | ② 仅路径/相对链接调整 | 保留路径修复（活动索引，新链接已验证可解析） |
| `docs/knowledge/acoustic-manifestations-20261009/table2-layering-feedback-index-20261012.md` | `b244ba9719e9f586…` | `4b93c055d8d38d8a…` | ② 仅路径/相对链接调整 | 保留路径修复（活动索引，新链接已验证可解析） |
| `docs/knowledge/acoustic-manifestations-20261009/table2-li-condition-review-index-20261013.md` | `a53ab9518294acbb…` | `d3904ebfb7216cc2…` | ② 仅路径/相对链接调整 | 保留路径修复（活动索引，新链接已验证可解析） |
| `docs/knowledge/acoustic-manifestations-20261009/table2-supplement-index-20261012.md` | `ce0a76f61d943f2c…` | `373bf3cbe2713ddd…` | ② 仅路径/相对链接调整 | 保留路径修复（活动索引，新链接已验证可解析） |
| `docs/knowledge/acoustic-manifestations-20261009/table2-texture-listening-index-20261013.md` | `a34fbf4662e9c117…` | `59aa73567d7ba462…` | ② 仅路径/相对链接调整 | 保留路径修复（活动索引，新链接已验证可解析） |

## 逐项差异片段

17 项的改动全部是**相对链接前缀调整**（例如 `../../../docs/lastpage-…` → `../../lastpage-…`，
或 `../../../docs/knowledge/…` → `../../knowledge/…`），**没有正文数据或语义变化**，
没有触碰声学实验结论。示例：

```diff
-| RESP-001 | ... | [原报告](../../../docs/lastpage-tenc-controlled-probe-20261008.md) |
+| RESP-001 | ... | [原报告](../../lastpage-tenc-controlled-probe-20261008.md) |
```

## 处理结果

- **恢复原字节 5 项**（SHA 锁定或 history 快照）：
  - `docs/knowledge/acoustic-manifestations-20261009/history/pre-table2-2a-20261010/docs/knowledge/acoustic-manifestations-20261009/conditional-responses.md` → `f30555954cd8d96d…`（与 34061cd 一致）
  - `docs/knowledge/acoustic-manifestations-20261009/history/pre-table2-2b-20261010/docs/knowledge/acoustic-manifestations-20261009/conditional-responses.md` → `f30555954cd8d96d…`（与 34061cd 一致）
  - `docs/knowledge/acoustic-manifestations-20261009/history/pre-table2-2c-20261010/docs/knowledge/acoustic-manifestations-20261009/conditional-responses.md` → `0bdf3e0062e8de6d…`（与 34061cd 一致）
  - `docs/knowledge/acoustic-manifestations-20261009/history/pre-table2-2d-20261010/docs/knowledge/acoustic-manifestations-20261009/conditional-responses.md` → `606fba0e23cca6f2…`（与 34061cd 一致）
  - `docs/knowledge/acoustic-manifestations-20261009/table2-existing-listening-queue-20261011.md` → `c74d98cd97521e53…`（与 34061cd 一致）
- **保留路径修复 12 项**（活动知识索引；新链接已在全仓链接审计中验证可解析）：

  - `docs/knowledge/acoustic-manifestations-20261009/conditional-responses.md`
  - `docs/knowledge/acoustic-manifestations-20261009/table2-DYN-delivery-index-20261012.md`
  - `docs/knowledge/acoustic-manifestations-20261009/table2-DYN-feedback-index-20261012.md`
  - `docs/knowledge/acoustic-manifestations-20261009/table2-TENC-delivery-index-20261012.md`
  - `docs/knowledge/acoustic-manifestations-20261009/table2-TENC-feedback-index-20261013.md`
  - `docs/knowledge/acoustic-manifestations-20261009/table2-entry-pitch-delivery-index-20261013.md`
  - `docs/knowledge/acoustic-manifestations-20261009/table2-entry-pitch-feedback-index-20261013.md`
  - `docs/knowledge/acoustic-manifestations-20261009/table2-layering-delivery-index-20261012.md`
  - `docs/knowledge/acoustic-manifestations-20261009/table2-layering-feedback-index-20261012.md`
  - `docs/knowledge/acoustic-manifestations-20261009/table2-li-condition-review-index-20261013.md`
  - `docs/knowledge/acoustic-manifestations-20261009/table2-supplement-index-20261012.md`
  - `docs/knowledge/acoustic-manifestations-20261009/table2-texture-listening-index-20261013.md`

### 被 SHA 锁定的判定依据

全仓搜索这 17 个文件在 34061cd 时的 Blob SHA，命中即视为被按 SHA 绑定：

- `docs/knowledge/acoustic-manifestations-20261009/history/pre-table2-2a-20261010/docs/knowledge/acoustic-manifestations-20261009/conditional-responses.md` ← `docs/knowledge/acoustic-manifestations-20261009/control-inventory-audit.json`、`docs/knowledge/acoustic-manifestations-20261009/history/pre-table2-2a-20261010/docs/knowledge/acoustic-manifestations-20261009/table1-consolidation.json`、`docs/knowledge/acoustic-manifestations-20261009/history/pre-table2-2a-20261010/docs/knowledge/acoustic-manifestations-20261009/table1-execution-audit.json`
- `docs/knowledge/acoustic-manifestations-20261009/history/pre-table2-2b-20261010/docs/knowledge/acoustic-manifestations-20261009/conditional-responses.md` ← `docs/knowledge/acoustic-manifestations-20261009/control-inventory-audit.json`、`docs/knowledge/acoustic-manifestations-20261009/history/pre-table2-2a-20261010/docs/knowledge/acoustic-manifestations-20261009/table1-consolidation.json`、`docs/knowledge/acoustic-manifestations-20261009/history/pre-table2-2a-20261010/docs/knowledge/acoustic-manifestations-20261009/table1-execution-audit.json`
- `docs/knowledge/acoustic-manifestations-20261009/history/pre-table2-2c-20261010/docs/knowledge/acoustic-manifestations-20261009/conditional-responses.md` ← `docs/knowledge/acoustic-manifestations-20261009/history/pre-table2-2c-20261010/docs/knowledge/acoustic-manifestations-20261009/table2-stage-2b-audit.json`、`docs/knowledge/acoustic-manifestations-20261009/history/pre-table2-2c-20261010/snapshot-manifest.json`、`docs/knowledge/acoustic-manifestations-20261009/table2-stage-2b-audit.json`
- `docs/knowledge/acoustic-manifestations-20261009/history/pre-table2-2d-20261010/docs/knowledge/acoustic-manifestations-20261009/conditional-responses.md` ← `docs/knowledge/acoustic-manifestations-20261009/history/pre-table2-2d-20261010/docs/knowledge/acoustic-manifestations-20261009/table2-stage-2c-audit.json`、`docs/knowledge/acoustic-manifestations-20261009/history/pre-table2-2d-20261010/snapshot-manifest.json`、`docs/knowledge/acoustic-manifestations-20261009/table2-stage-2c-audit.json`
- `docs/knowledge/acoustic-manifestations-20261009/table2-existing-listening-queue-20261011.md` ← `docs/knowledge/acoustic-manifestations-20261009/table2-existing-listening-queue-20261011-audit.json`

## 未回滚的部分（按计划）

- 知识包的 `active-knowledge-sources.json` 与各 response index 的**路径修复被保留**：
它们是活动索引，改后链接指向新位置且可解析；回滚会让活动索引指向已不存在的路径。
- 没有整包 `git restore`，没有回滚用户整理后新增的有效知识；只处理经逐项核实的那 17 个文件。
- `.gitattributes` 对知识包的规定保持不变，**没有**因为编辑器/PowerShell 默认换行模式产生 CRLF/LF 意外转换
（恢复动作直接用 `git checkout 34061cd -- <path>` 取回 blob，字节与基线完全一致）。
