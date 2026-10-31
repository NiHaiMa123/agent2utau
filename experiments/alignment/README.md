# experiments/alignment — 音素/歌词对齐

本轮唯一有实际内容的对齐实验入口；歌曲专属的对齐/时钟脚本留在 songs/<song>/sessions/*/scripts。

## 当前已有入口

- `scripts/check_polyphones.py — 合成多音字串的音素切分探针（与任何歌曲无关）`
- `scripts/read_test_polyphones.py — 读取上述导出的音素表`
- `scripts/check_phones_structure.py — 读取音素/单元结构`
- `data/test_polyphones.json、data/test_modified_phones.json — 上述探针的导出数据`
- `phoneme-alignment-p0p1-20261031/ — plan.md P0+P1 的执行记录：锁定歌词（syllable_id）、GAME 归一化（note_id）、确定性字—音符映射与窗口候选、22 个小样本、baseline 工程（无人工 PITD）。生产代码在 `src/agent2utau/alignment/`，契约在 `schemas/alignment_evidence_v1.schema.json`，报告见该目录 `reports/`。
- `phoneme-alignment-p1.1-20261031/ — plan.md「五点五、P1.1」的修复记录：valid/incomplete/invalid 状态机与退出码、非法 `+` 延音不再静默丢弃（附有限候选）、句区间硬约束与窗口可达性、HFA/ASR 证据分级、公开歌词改为待复核候选、GAME 复现性调查（根因层面）、41 个历史删除文件的逐项查证与字节不变归档。报告见该目录 `reports/`，归档映射见 `docs/archive/legacy-scratch/MANIFEST.json`。**本轮停在 P2 之前。**
- `phoneme-alignment-p1.2-20261031/ — plan.md「五点六、P1.2」的记录：弱观测降权改成"置信度与物理可行性分离"（反事实行为测试）、窗口结论与搜索预算无关（10 倍预算对照）、USTX 按 sidecar 账本核对身份与绝对 tick（7 项故障注入）、30 个未归属 voiced note 的分类登记、tone 截断/四舍五入的 F0 交叉验证、16 个短句的局部门禁（14 放行 / 2 阻断）。报告见该目录 `reports/`。**仍停在 P2 之前。**

---

边界：只有**跨歌曲可复用**或**有明确对照协议**的方法实验放这里；
属于某首歌的局部修订/试唱/审计留在 `songs/<song>/sessions/<session>/`。
具备受控输入、断言、可重复 pass/fail 的测试才进 `tests/`；生产评价代码留在 `src/agent2utau/evaluation`。
