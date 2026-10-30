# experiments/alignment — 音素/歌词对齐

本轮唯一有实际内容的对齐实验入口；歌曲专属的对齐/时钟脚本留在 songs/<song>/sessions/*/scripts。

## 当前已有入口

- `scripts/check_polyphones.py — 合成多音字串的音素切分探针（与任何歌曲无关）`
- `scripts/read_test_polyphones.py — 读取上述导出的音素表`
- `scripts/check_phones_structure.py — 读取音素/单元结构`
- `data/test_polyphones.json、data/test_modified_phones.json — 上述探针的导出数据`
- `phoneme-alignment-p0p1-20261031/ — plan.md P0+P1 的执行记录：锁定歌词（syllable_id）、GAME 归一化（note_id）、确定性字—音符映射与窗口候选、22 个小样本、baseline 工程（无人工 PITD）。生产代码在 `src/agent2utau/alignment/`，契约在 `schemas/alignment_evidence_v1.schema.json`，报告见该目录 `reports/`。

---

边界：只有**跨歌曲可复用**或**有明确对照协议**的方法实验放这里；
属于某首歌的局部修订/试唱/审计留在 `songs/<song>/sessions/<session>/`。
具备受控输入、断言、可重复 pass/fail 的测试才进 `tests/`；生产评价代码留在 `src/agent2utau/evaluation`。
