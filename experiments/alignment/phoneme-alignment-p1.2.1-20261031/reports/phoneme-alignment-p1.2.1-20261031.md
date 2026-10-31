# P1.2.1 报告：局部门禁小补丁（真实上下文、fail-closed 校验、统一未决清单）

日期：2026-10-31 ｜ 执行模型：MiniMax-M3.1-Flash（单 Agent）｜ 依据：[根目录 plan.md](../../../plan.md)「五点七、P1.2.1」A～E
新 run：`runs/production/phoneme-alignment-p1.2.1-20261031/`（本机，Git 忽略）｜ 对照基线：`3b467b2` / `runs/production/phoneme-alignment-p1.2-20261031/`
**本轮只补门禁缺口；P1.2 的 A～E 未重复实现；未启动 P2。**

---

## 0. 一句话结论

四个门禁漏洞都补上了，并各有失败注入回归：**放行数从 14 变成 13**——被拦下的是 P1.2 误放行的 `yuai-short_vowel`（它的真左邻「我」是 unresolved）。三首歌的**映射一字未改**（0 处变化），状态仍全部 `incomplete`（退出码 3），但"为什么"现在有了统一、可版本化、可追责的来源。

---

## 1. P1.2.1-A｜相邻上下文改为真正的片段外唱字

**已证实的问题：** P1.2 的 `context = [syllables[0], syllables[-1]]` 取的是**段内首尾字**，不是相邻唱字。于是 `yuai-short_vowel`（`s0027～s0030`）被判为 ready，而它真正的左邻 `s0026「我」` 是 **unresolved**——一段未解的字相邻，却因为"上下文"取错而放行。

**现在的做法**（`gate.py::_context_of`）：

- 用 `mapping["mapping"]` 的**稳定歌词顺序**定位目标段的首尾位置，向前后各取一个真实相邻唱字；越界则该侧为空并标记 `at_song_boundary`；
- **不**通过 ID 字符串加减，也不假设首尾字在同一句；
- JSON 里把 `target_syllable_ids` 与 `context_syllable_ids` 分开，并列出真实相邻 ID 与它们的状态、note_ids、是否 review；
- 相邻唱字的 `unresolved` / `review_required` / 非法延音 / 未审未归属音符同样参与阻断（`context_unresolved_syllable`、`context_review_required_syllable` 等）。

**实例回归**：`yuai-short_vowel` **ready → blocked**，阻断项 `context_unresolved_syllable: s0026`（左邻「我」unresolved，右邻 `s0031「清」`正常）。原有 14/16 **不再作为新结果**。

---

## 2. P1.2.1-B｜缺少真实校验记录一律 fail-closed

**已证实的问题：** P1.2 只遍历"存在"的校验记录；缺失、空列表、`present=false` 的目标音都没被逐个检查，旧单测甚至用 `verification_notes=[]` 当"干净数据"来断言放行。

**现在的做法**：目标段的每个 note **加上**门禁要求的上下文 note，都必须**恰好一条**完整记录（`note_id`、`present=true`、目标/实际起点 tick、时长、tone、歌词、part/索引），并逐值与账本比对：

| 异常 | 阻断码 |
|---|---|
| 没有记录 | `verification_missing` |
| 同一 note 两条记录 | `verification_duplicate` |
| 缺必要字段 | `verification_incomplete_record` |
| `present=false` | `verification_note_absent` |
| 起点 tick 偏差 > 1 | `verification_start_mismatch` |
| 时长/音高/歌词不符 | `verification_duration_mismatch` / `_tone_mismatch` / `_lyric_mismatch` |
| 全局 `one_to_one=false` | `verification_failed` |
| 校验与本段输入不是同一份 | `verification_identity_mismatch` |

**失败注入测试**（`tests/unit/test_alignment_gate.py`、`test_alignment_pipeline_state.py`）覆盖：0 条记录、遗漏 1 个音、`present=false`、缺字段、同 ID 两条、错误歌词、全局 `one_to_one=false`、起止 tick 不匹配、校验身份不符；**同时构造完整合法数据证明正常片段依旧放行**（没有把全部片段一律标 blocked 来刷安全门禁）。

---

## 3. P1.2.1-C｜未决事项统一落盘，所有入口共享

新增**单一版本化**清单 `experiments/alignment/pending_decisions.json`（提交入库，schema_version=1），并新增 `src/agent2utau/alignment/pending.py` 负责加载与校验：

| decision_id | 类型 | 目标 | 状态 | 依据 |
|---|---|---|---|---|
| `lastpage:n0060` | note | `n0060` | pending | GAME 把「淹」的辅音段切成独立事件；HFA 显示原唱「淹」从 43.607 s 起唱 |
| `nianlun:s0059` | syllable | `s0059` | pending | 原始 canonical diff **unit_index=9, position=5** → 真实 syllable_id `s0059` |
| `nianlun:s0203` | syllable | `s0203` | pending | 原始 canonical diff **unit_index=31, position=5** → 真实 syllable_id `s0203` |

两条「份/分」的 syllable_id 是**从原始 diff 推出的**，不是猜位置（推算过程见报告 §7）。

规则：

- `gate.evaluate_segment()` 通过**显式参数**接收同一份清单，**不再有隐式可变模块全局字典**；
- **清单缺失 = 错误**，不是"没有未决事项"；清单与 frozen 输入 SHA 不匹配 → 拒绝加载；诊断模式可输出 blocked 清单与明确错误码；**显式授权的空清单 `[]` 允许**，但必须带来源/哈希并有测试；
- 未决 note/syllable 触及**目标段或真实上下文**即 blocked；未决 note 若不属于任何字，则按**时间窗**阻断（防止"摘掉归属"绕过决策）；
- 清单只用于**放行**，不自动批准、不自动改词、不自动改音符。

**同一判定**：CLI、session 脚本、直接调用库都走同一个函数与同一份清单；契约测试 `tests/contracts/test_alignment_pending_decisions.py` 分别验证缺清单、清单 SHA 失配、空但已授权清单、`n0060`、「份/分」以及无关片段不被误拦。

---

## 4. P1.2.1-D｜USTX 校验失败反馈到整曲状态与局部门禁

**已证实的问题：** `pipeline.run_alignment()` 算了 `verification`，但 `hard_problems` 没包含 `one_to_one=false` 的错误。

**现在的做法**：

- 校验的 missing/extra、时钟偏移、时长变化、tone/歌词不一致、非法延音、part/顺序异常 → 稳定错误码（`verification:*`）并入 `hard_problems` → **status=invalid，退出码 2**；
- **例外**：已明确列入 `unresolved_notes`、诊断 USTX 有意排除的非法 note，**仍只能是 incomplete**，不会因"预期缺失"被升级为 invalid，也不会伪称 valid；
- **没有 baseline_ustx 或没有跑校验时，状态不得假定 valid** → 记 `no_ustx_verification`，状态最多是 incomplete（诊断输出与生产验收就此分开）；
- 局部门禁要求 `baseline_verification` 与同一 USTX/输入 hash 对应（`ustx_sha256`/`lyrics_sha256`/`notes_sha256`），并输出 `verification_passed`，不能"有文件就算验收"。

**命名区分**：本轮是**纯 YAML 账本核对**，**不是** OpenUtau 原生音素导出。报告与产物里统一写作 `native_phoneme_export=false`，不把 YAML 对照说成原生验收。

---

## 5. P1.2.1-E｜重新计算 16 个短句并交付 P2 可用清单

新 run `runs/production/phoneme-alignment-p1.2.1-20261031/`：

| 指标 | P1.2 | P1.2.1 |
|---|---|---|
| 段数 | 16 | **16**（segment_id 与目标字不变） |
| 放行 | 14 | **13** |
| 阻断 | 2 | **3** |
| 变化的段 | — | `yuai-short_vowel`（ready → blocked） |

逐段结果：

| 段 | P1.2 | P1.2.1 | 阻断原因 |
|---|---|---|---|
| `yuai-short_vowel` | ready | **blocked** | `context_unresolved_syllable: s0026`（真左邻「我」未解） |
| `lastpage-pending-n0060` | blocked | blocked | `pending_note_decision: n0060` |
| `yuai-melisma` | blocked | blocked | `unassigned_voiced_note_in_window: n0084` |
| 其余 13 段 | ready | ready | — |

新 run 同时写入：`local_gate.json`（含真实 context、`verification_complete`、`pending_decisions_sha256`、放行证据摘要、逐段阻断详情）、`run_summary.json`、每首歌的 `baseline_verification.json` 摘要与 `verification_identity`。

**映射未变**：三首歌重跑后与 P1.2 逐 `syllable_id → note_ids` 比对，**0 处变化**——本轮只改门禁与状态口径，没有碰 GAME/HFA、歌词、映射、取整与未归属分类。

---

## 6. 实际执行的数字

```
pytest -q                                    → 391 passed
  新增：局部门禁 24 项（真实上下文 5、fail-closed 校验 11、共享未决清单 7、整曲状态反馈 4）
  原有：P1.2 的 362 项与 P1.1/P1.2 的全部回归保持通过
CLI 退出码测试                                → 通过（valid=0 / incomplete=3 / invalid=2 一致）
tools/repository/check_repository.py          → passed（索引与 --worktree 双模式）
P1.2.1 三歌重跑                              → 全部 incomplete（退出码 3），verification_passed=true，
                                                hard_problems=0，映射变化 0
局部门禁重算                                  → 13 ready / 3 blocked
```

**运行环境**：Windows ｜ OpenUtau 0.1.570.9011 ｜ 声库 YousaV1.65c ｜ ONNX Runtime 1.30.0 ｜ Python 3.12（.venv）

**真实原生执行边界**：`native_phoneme_export=false`、`listening=unknown`——本轮没有做任何音素导出、patch 写回、渲染或试听；只用既有 P1.1/P1.2 的原生探针结论。

**历史保护**：`docs/archive/legacy-scratch/` 原 SHA 字节未动；没有删除旧 run、测试、歌曲 session 或知识包；没有重组目录；没有启动多 Agent 或无关 CI。

---

## 7. 「份/分」真实 syllable_id 的推导

不是猜位置，而是从原始 diff 复算：

```
P0/P1 nianlun lyrics_canonical_diff.json:
  substitutions = [{unit_index: 9, position: 5, 份→分}, {unit_index: 31, position: 5, 份→分}]
按锁定歌词的行顺序累加 syllable_id:
  unit 9  pos 5  →  s0059   (行「是有缘却无分」)
  unit 31 pos 5  →  s0203   (行「是有缘却无分」)
```

推导脚本与输入 SHA 记录在 `pending_decisions.json` 的 `source` 字段。

---

## 8. 仍然待你决定（与 P2 无关的段落不阻断）

1. `lastpage:n0060` 的归属（合并进「淹」/ 提前贴上前音 / 另行处理）；
2. `nianlun:s0059`、`s0203` 的「份/分」用字；
3. 生产 tone 取整口径（证据支持四舍五入，生产规则未改）；
4. 分句是否改用发行版；
5. 30 个未归属 voiced 音符仍待人工逐条复核（`reviewed` 全为 false）。

**P2 未启动。** 下一轮 P2 只能使用本轮新出具的 `ready_for_p2_native_baseline` 清单（13 段），不得沿用 P1.2 的「14/16」。
