# P1.2 报告：行为正确性、未归属音符登记与可进入 P2 的局部门禁

日期：2026-10-31 ｜ 执行模型：MiniMax-M3.1-Flash（单 Agent）｜ 依据：[根目录 plan.md](../../../plan.md)「五点六、P1.2」A～G
新 run：`runs/production/phoneme-alignment-p1.2-20261031/`（本机，Git 忽略）｜ 对照基线：`runs/production/phoneme-alignment-p1.1-20261031/`
**本轮停在 P2 之前，未启动任何 patch。**

---

## 0. 一句话结论

A～E 的缺陷都做了确定性修补并有针对性回归：弱观测不再变成更强的约束、窗口结论与搜索预算无关、USTX 逐 note 核对查绝对 tick 与身份、所有未归属 voiced 音符都有分类与去向、tone 取整拿到了证据。**三首歌仍然全部 `incomplete`（批处理退出码 3）**，但有 **16 个短句里 14 个通过局部门禁**，可以进入 P2 试点；两处仍被阻断，并留给你决定。

---

## 1. P1.2-A｜弱观测降权的真实行为

### 1.1 原实现的问题

P1.1 的代价是 `|anchor − note.start| / (time_scale × weight)`：weight 从 1 降到 0.25，等于把**同样的时差惩罚放大 4 倍**——弱证据反而成了更强的绝对距离约束，与"弱证据影响小"完全相反。

### 1.2 现在的设计

三件事分开（`candidates.py::_assign_cost`）：

| 维度 | 处理 |
|---|---|
| **物理可行性** | 不是代价而是**非法**：休止或真实间隙夹在连音链里 → `inf`，该转移直接不成立 |
| **观测置信度** | 可信观测付 `min(residual / 0.35, 3.0)` 的**稳健有界**代价；弱观测只付其中 `weight` 的一份，且**超出信任窗（1.0 s）后完全不参与判别**，只作为 review 信号 |
| **演唱确认** | 没有任何演唱观测覆盖的音符，附加 `unconfirmed_note_penalty = 0.6`——不靠"硬塞给某个字"来把覆盖率做漂亮 |

时长项同样按置信度处理并封顶（1.0），观测短于 0.08 s 一律不计入。

### 1.3 反事实行为测试（不是 `assert weight<1`）

`tests/unit/test_alignment_evidence_behaviour.py`：

- 精确锚可以决定选择（两个候选音里，精确锚指向的那个被选中）；
- **错误的弱锚不会把映射拖走**：把 positional 锚指到别的字，该字不跟着跑；
- 弱锚不会比精确锚更容易制造 unresolved；
- 同一时间被两个字认领 → `trust=conflict`，权重归零并记 review 信号；
- 观测来自别的句 → 同样是 conflict；
- 弱锚超出信任窗时，其代价与"没有锚"**完全相等**（浮点容差内）。

### 1.4 证据统计按来源与阶段分组

P1.1 报告里《最后一页》的「203 missing / 130 residual / 3 positional」确实是**混合日志**（HFA 与 ASR 混在一起，且"从未匹配"与"匹配到别的字"同档）。现在分开统计：

| 歌曲 | 来源×阶段 | 最终锚点分布（权威口径） |
|---|---|---|
| 年轮 | hfa.observation_missing 3、hfa.observation_positional_fallback 3 | hfa.exact_text **343**、hfa.positional 6 |
| 最后一页 | hfa.observation_missing 3、hfa.observation_positional_fallback 3；asr.observation_missing 200、asr.observation_residual_match 130、asr.observation_unused 80 | hfa.exact_text **315**、hfa.positional 3 |
| 雨爱 | 无缺口 | hfa.exact_token **371** |

**最后一页的 203 并不是"HFA 缺 203 个锚"**：HFA 只缺 3 个，那 200 个缺口来自 ASR，而 ASR 的 130 条残余匹配是弱证据（residual_text，权重 0.35），最终锚点仍以 HFA 精确匹配为主。

---

## 2. P1.2-B｜"无合法候选"的可审计含义

- 合法性判定**前置到转移层**（`+` 间隙、休止、句界、窗口 note budget），枚举只走合法转移。
- 窗口结论改为四态：`legal_alternatives_available` / `only_baseline` / `no_legal_solution_proven` / `search_budget_exhausted`，并记录 `search_complete`。
- **预算稳定性实测**（`probe_window_budget.py`）：默认预算（max_paths 60 / max_options 8）与放大 10 倍（600 / 40）各跑一遍，**三首歌的窗口决策与候选数完全一致**（nianlun 13、lastpage 3、yuai 8 个窗口，决策变化 0）。旧实现里"前 K 个候选都非法"这种预算依赖结论已经消失。
- 交付给模型的候选列表按 `max_options` 截断，但**真实候选数照实记录**（`option_count` / `alternative_count` / `listed_option_count`）。
- 窗口重叠会被标出（`overlaps_with` / `overlapping_syllable_ids`），重叠窗口涉及的字进入 review。

---

## 3. P1.2-C｜USTX 逐 note 身份、绝对时间与音高

`baseline.py` 现在写一份 **sidecar 账本**（`build_ledger`）：每个音符记录 part_index、note_index、note_id、syllable_id、歌词、绝对起点 tick、终点 tick、时长、音高，以及**建谱器 ±1 tick 贴合的授权改动**（单独记为 `builder_adjustments`，不静默通过）。

核对改为**按位置**（part, note index）比对，绝对 tick 用 `voice_parts[].position + notes[].position` 计算，逐项检查起点、时长、终点、音高、歌词、单调性，以及 `+` 是否有合法前驱。`one_to_one` 只在身份、时钟、音高、歌词、数量全部满足时才为真。

**另经真实 Core 确认**：`+` 接 `+` 是**合法**的（无 `invalidPhonemes`，乐句覆盖三音）；只有**以 `+` 开头的 part** 才非法（`Unrecognized phoneme "+"`，该 part 没有乐句）。P1.1 的判定把"`+` 后面接 `+`"误报为非法，本轮已按真实行为改正。

故障注入测试（`tests/unit/test_alignment_ustx_verification.py`，7 项全过）：错拍、时长改变、part 整体漂移、两个相同 `+` 互换、重复歌词、少一个音——**全部被抓到**。

---

## 4. P1.2-D｜所有未归属 voiced GAME 音符的去向

新增 `unassigned_voiced_notes.json`（每首歌一份）：每个无主的 voiced 音符记录时间、时长、音高、前后音符与休止、邻居唱字、可引用的 HFA/ASR 证据、分类、reason_code 与有限候选；`reviewed` 一律为 `false`，必须人工过。

分类（按证据强度排序）：`rest_or_nonlead` → `candidate_melisma` → `probable_false_positive` → `needs_alignment`；伪音符判定必须有"没有演唱观测覆盖"这一独立证据，且自动判定有单测覆盖。

| 歌曲 | 未归属 | 分类分布 |
|---|---|---|
| 年轮 | 11 | rest_or_nonlead 9、candidate_melisma 2 |
| 最后一页 | 1 | candidate_melisma 1 |
| 雨爱 | 18 | candidate_melisma 10、rest_or_nonlead 4、probable_false_positive 2、needs_alignment 2 |

未归属音符全部进入生产状态门禁（整曲因此是 `incomplete`），但**按 song/segment 分开**：没有触及这些音符、也没有非法 `+` 的短句可独立放行（见 §6）。

---

## 5. P1.2-E｜基础 MIDI 音高取整（只调查，不改规则）

`probe_tone_rounding.py`：用同一批冻结 GAME 音符，比较 `int(tone)`（截断，生产现状）与 `round(tone)`（四舍五入），并用**同一段人声的 FCPE/RMVPE F0**（只取基频，不复制颤音）作参照。

| 指标 | 数值 |
|---|---|
| voiced 音符总数 | 1193 |
| 两种规则结果不同 | **552（46.3%）** |
| 规则不同时：**四舍五入更贴近原唱基频** | **423** |
| 截断更贴近 | 101 |
| 不确定（两路 F0 互相矛盾 48 / 八度冲突 2） | 50 |

分歌：年轮 400 音中 143 个不同（round 106 / truncate 27 / 不确定 21）；最后一页 368 中 144（110 / 33 / 5）；雨爱 425 中 265（207 / 41 / 24）。

**证据导向建议：`round_is_better_supported`——在能判定���音符里，四舍五入与原唱基频一致的比例约为截断的 4 倍。** 但这只是建议：本轮**没有**改动 `to_ustx_tone()`，没有覆盖任何历史 USTX，也没有替你决定生产口径。F0 是参照而非真值（两路 F0 互相矛盾 48 例、八度冲突 2 例一律标 uncertain）。

---

## 6. P1.2-F｜局部门禁与 P2 试点样本

`local_gate.json`：**16 个短句**（nianlun 5 / 最后一页 6 / 雨爱 5，每个 3～5 字），每段给出 `segment_id`、涉及的 `syllable_id`/`note_id`、歌词与时间区间、前后 1 字上下文、输入文件 SHA256、`local_gate`（`ready_for_p2_native_baseline` / `blocked`）与**明确的阻断原因**。

放行条件：片段内与 1 字上下文内没有未解唱字、未审未归属音符、非法 `+`；歌词已核对；候选映射身份稳定；原声源 SHA 固定；音符的真实 USTX tick/音高/时长与账本一致；没有未知的跨句漂移（跨句只作 caution，不单独阻断）。

结果：**14 段放行、2 段阻断**：

| 段 | 状态 | 原因 |
|---|---|---|
| `lastpage-pending-n0060`（潮声淹没了） | blocked | `pending_note_decision`：n0060 的归属仍待你决定 |
| `yuai-melisma`（的声音一滴） | blocked | `unassigned_voiced_note`：片段内有未归属 voiced 音符 |

**局部放行 ≠ 整曲放行**：三首歌仍是 `incomplete`。每段还附了两条全局待决事项（tone 取整口径可能让某音高移动 1 个半音；分句按录音而非发行版）。

---

## 7. P1.2-G｜回归、对照与产物

### 7.1 测试

```
.venv\Scripts\python.exe -m pytest -q   →  362 passed
```

新增针对性测试（不是只跑既有 336 项）：弱/强证据的**最终映射差异**（`test_alignment_evidence_behaviour.py`）、**候选搜索预算变化**（`probe_window_budget.py` + 决策稳定性断言）、**真实 USTX 时间/ID 故障注入**（`test_alignment_ustx_verification.py` 7 项）、**未归属音符的状态门禁与分类**（`test_alignment_unassigned.py`）、**局部门禁边界案例**（`test_alignment_gate.py` 7 项）。

仓库门禁：`python tools/repository/check_repository.py` → passed（索引与 worktree 双模式）。

### 7.2 与 P1.1 的逐字对照

| 歌曲 | P1.1 | P1.2 | 变化的字 | 未归属音符 | USTX 一一对应 |
|---|---|---|---|---|---|
| 年轮 | 343/349，6 未解 | **344/349**，5 未解 | 2 | 11 | ✅ 389/389 |
| 最后一页 | 318/318，0 未解 | **318/318**，0 未解 | 3 | 1 | ✅ 366/366 |
| 雨爱 | 366/371，5 未解 | **366/371**，5 未解 | 5 | 18 | ✅ 407/407 |

逐条变化（共 10 个字）都属同一类：**一个没有演唱观测覆盖的连音音符被从字上摘下，改为登记为未归属**，字本身仍被映射且时间不动。唯一一处语义变化值得单独说：

> **《最后一页》`s0049 声` / `s0050 淹`**：P1.1 把 n0059+n0060 都给了「声」（且两者之间有 160 ms 间隙，OpenUtau 无法写成 `+`）；P1.2 把 n0059 留给「声」、n0050+n0061 给「淹」。依据是 HFA 观测：原唱「淹」从 **43.607 s** 起唱，而 GAME 的 n0060 正是 **43.57–43.76 s**——它是「淹」的辅音段，P1.1 把它错记给了「声」。

其余 9 处（年轮 2、雨爱 5、最后一页 2）都是无演唱证据的连音被摘下。**没有出现"覆盖率上升"换来的假改进**：映射覆盖率基本持平（年轮 343→344 是 1 个原本 unresolved 的字被解出），真正变化的是音符归属的正确性与可审计性。

### 7.3 产物与哈希

新 run `runs/production/phoneme-alignment-p1.2-20261031/`：每首歌的 `lyrics_locked.json`、`notes_normalized.json`、`mapping.v1.json`、`anomalies.json`、`baseline_verification.json`、`unassigned_voiced_notes.json`、`comparison_with_p1_1.json`、`baseline.ustx`；全局 `run_summary.json`、`local_gate.json`、`tone_rounding/tone_rounding.json`、`window_budget/window_budget.json`。
合规文本证据已逐字节归档入库：`experiments/alignment/phoneme-alignment-p1.2-20261031/evidence/`（26 个 JSON，2.5 MB，`MANIFEST.json` 记录 run 路径、SHA256 与一致性检查）。

### 7.4 真实原生执行边界

- 本轮真实调用原生 Core：**延音合法性探针**（含"`+` 接 `+`"这一新增探针）。
- **没有**做：baseline 的原生音素导出、patch 写回、渲染、试听。
- `tests_observed`：362 项 pytest 通过；CLI 状态与退出码测试通过；仓库门禁通过；窗口预算稳定性对照通过。
- `native_verified`：仅限三个延音合法性探针与既有 P1.1 记录。
- `listening_status`：**unknown**（本轮无音频产出）。
- `blocked_segments`：2 段（见 §6）。

### 7.5 历史保护

`docs/archive/legacy-scratch/` 原 SHA 字节未动；那 40 个 scratch 文件的本地工作副本中 28 个早已与历史提交不同，本轮**没有覆盖**这些工作副本，也没有删除任何历史 run、测试、歌曲 session 或知识包。

---

## 8. 仍然待你决定（进入 P2 前）

1. **《最后一页》n0060**：合并进「淹」、提前贴上前音、还是另行处理——涉及片段已 blocked。
2. **《年轮》两处「份/分」**：公开歌词与录音用字不一致，锁定正文仍按录音，待复核。
3. **生产 tone 取整口径**：证据支持四舍五入（约 4 倍优势），但生产规则未改。
4. **分句**：当前按录音分句，未采用发行版分行。

以上与 P2 无关的段落不阻断 P2 试点；**P2 未启动。**
