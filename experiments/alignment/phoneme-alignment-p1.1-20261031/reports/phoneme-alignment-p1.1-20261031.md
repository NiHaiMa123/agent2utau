# P1.1 修复报告：对齐安全性、失败门禁、观测分级与历史核查

日期：2026-10-31 ｜ 执行模型：MiniMax-M3.1-Flash（单 Agent）｜ 依据：[根目录 plan.md](../../../plan.md)「五点五、P1.1」A～G
新 run：`runs/production/phoneme-alignment-p1.1-20261031/`（本机，Git 忽略） ｜ 基线 run：`runs/production/phoneme-alignment-p0p1-20261031/`（只读，未覆盖）

**本轮完成后即停止，未进入 P2。**

---

## 0. 一句话结论

P1.1 的 A～G 全部落地并有回归证据：结果状态机与退出码可用、`+` 延音不再被静默丢弃（最后一页 `n0060` 已成为 `unresolved_note_ids` 并附四个有限候选）、句边界与候选可达性有硬约束、观测证据分级且弱证据降权、公开歌词改为待复核候选、GAME 可复现性查到了根因层面、历史 41 个删除文件逐项查证并建立字节不变归档。
**但三首歌仍全部是 `incomplete`（批处理退出码 3）**：映射没有达到 100%，也没有任何音素层面的验证。

---

## 1. 修复前后对照（同一批冻结输入）

固定输入来自 P0/P1 run，按 SHA256 复制进新 run，**不重新生成 GAME / HFA / 歌词**。

| 歌曲 | 状态 | 字已映射 | unresolved 字 | 音符已归属 | 歧义窗口 | 候选 | USTX 逐 note 一一对应 |
|---|---|---|---|---|---|---|---|
| 年轮 | incomplete | **343**/349（P0/P1 为 345） | 6（原来 4） | 389/400 | 15（全为 agent_choice） | 96（原 71） | ✅ |
| 最后一页 | incomplete | **318**/318 | 0 | 368/368 | 5 agent_choice + **1 no_valid_candidate** | 31（原 46） | ❌（缺 `n0060`，已登记） |
| 雨爱 | incomplete | **366**/371 | 5 | 413/425 | 7（全为 agent_choice） | 44（原 6） | ✅ |

变化说明：年轮少映射 2 字、多 2 个 unresolved，是**新加的句区间硬约束与弱证据降权收紧后的结果**，不是回归——硬约束不允许无证据跨句，弱证据（positional）不再能把字拉离原唱位置。候选数上升是修掉窗口游标 bug 后的正常结果（见 §3.3）。

---

## 2. A｜结果状态与错误退出码

新增 `src/agent2utau/alignment/status.py`：

| 状态 | 含义 | 退出码 |
|---|---|---|
| `valid` | 全部强约束通过，无未处理必需身份 | 0 |
| `incomplete` | 无非法写回，但存在 unresolved / 待人工处理 / 无法表示的音符 | **3**（`--allow-incomplete` 时为 0，且状态仍写 `incomplete`） |
| `invalid` | 语义错误：非法音符时钟、非法延音、映射违反硬约束、原生不一致 | **2** |

- `pipeline.run_alignment()` 现在返回 `status`，并把**时钟硬问题并入门禁**（此前 `clock_problems` 生成但不参与判定）。
- CLI 的 `status` 与进程退出码一致；`--diagnostic-only` 的运行永远不会是 `valid`。
- 批处理 `build_p1_1_artifacts.py` 聚合并返回真实退出码（本次 3），不再常量返回 0。
- **非法 duration / overlap = hard fail；正常 silence gap = info**（年轮 17、最后一页 17、雨爱 12 条 gap 全部只登记不阻断）。

注入故障测试（`tests/contracts/test_alignment_cli_exit_codes.py`，真实命令行 + 真实退出码）：

| 注入 | 期望 | 实测 |
|---|---|---|
| 负长音符 | invalid / 2 | ✅ 2 |
| 相邻 overlap | invalid / 2 | ✅ 2 |
| 丢字（字多于音） | incomplete / 3 | ✅ 3 |
| 1 个 unresolved 字 | incomplete / 3 | ✅ 3 |
| 非法延音（间隙） | incomplete / 3 + `unresolved_note_ids` | ✅ 3 |
| 干净输入（有 HFA 锚点） | valid / 0 | ✅ 0 |
| 无任何时间证据 | incomplete / 3（句界未确立） | ✅ 3 |

---

## 3. B｜`+` 延音不再被静默丢弃

### 3.1 合法性的判定来自真实 Core，不是阈值猜测

用真实 OpenUtau Core 做了三个探针（`scripts/probe_extender_gap.py`，工程在 `runs/.../probes/`）：

| 探针 | Core 输出 | 结论 |
|---|---|---|
| `+` 紧贴前音 | `invalidPhonemes: []`，乐句覆盖到 42010 | **合法** |
| `+` 与前音隔 160 ms | `invalidPhonemes: [{phoneme:"error", error:"Unrecognized phoneme \"+\""}]`，乐句止于 41674（该音**没有进入乐句**） | **非法** |
| `+` 另起一个 part | 同样报 `Unrecognized phoneme "+"`，该 part **没有乐句** | **非法** |

结论：**间隙中的 `+` 无法被表示**，而且是 OpenUtau 自己把它丢出乐句——这正是"静默丢弃"在原生层的表现形式。

### 3.2 现在的行为

`baseline.rows_to_segments` 不再 `continue` 掉非法延音，而是：

1. 记录 `unresolved_notes`：note_id、syllable_id、tone、原始时钟、间隙秒数与 tick、原因码 `extender_not_touching`；
2. 生成**四个有限候选**（每个都写明效果与是否需要授权）：

| 候选 | 效果 | 状态 |
|---|---|---|
| `close_gap` | 把该音提前 160 ms 贴上前音 | candidate，**需要授权**（改歌曲时钟） |
| `merge_into_character` | 两音合并为一音 | candidate，**需要授权**（改音符数与音高） |
| `split_new_part` | 该音另起一个 part | **illegal_by_core**（有探针证据） |
| `repeat_character` | 重复唱一遍该字 | **forbidden_without_human**（绝不自动） |

3. `baseline_status=incomplete`，`unresolved_note_ids=["n0060"]`，禁止当作完整基线进入 P2。
4. **没有通过拉长上一音符跨过间隙来掩盖问题**，也没有自动把 `+` 变成新唱字。

**最后一页 `n0060` 的实际结果：未修复，作为 unresolved 登记**（映射成立、工程无法表示、四个候选待人工/Agent 选择）。这是本轮唯一一条"映射有、工程无"的音符，且已被状态机与逐 note 核对同时抓到，不再静默。

---

## 4. C｜分句/连音硬约束与候选可达性

- **句区间**：每个歌词句按其字的时间锚点算出可审计区间与锚点覆盖率，写进 `mapping.v1.json` 的 `lines[]`；锚点覆盖率 < 0.5 的句标记 `review_required`（不把发行版换行当成音乐边界）。映射时若某音的起点落在本句区间 ±0.6 s 之外，该转移被判为非法（`inf`），即**不允许无证据跨句**。
- **连音合法性**：一个字只能拥有原始序号连续、无休止、且间隙 ≤1 tick 的音符；间隙超限即非法，由 §3 的流程登记。
- **窗口可达性**：每个歧义窗口现在带 `decision` 字段：
  - `agent_choice`（有 ≥1 个合法且与全局最优不同的替代），
  - `no_agent_decision_needed`（窗口内只有最优解，不给模型假选项），
  - `no_valid_candidate`（窗口内无合法解 → 明确列 `review_required`，不产生"看似已解决"的空窗）。
  实测：年轮 15 个窗口全部 `agent_choice`；最后一页 6 个里 **w02「冷却海潮声」是 `no_valid_candidate`**（正是 §3 那条非法延音所在句）；雨爱 7 个全部 `agent_choice`。
- **候选不越界**：候选的 syllable_id 与 note_id 都被限制在自己的窗口内（代码内显式过滤），并附带 `legal` 与 `illegal_sustain_note_ids`。
- **不能靠 DP 代价差宣称准确**：本报告只给覆盖与 unresolved 事实，逐条人工复核见 §9。

### 4.1 修掉的两个真 bug（都是 P1.1 的"逐 note 核对"抓出来的）

1. **最优路径回溯的 cursor 错位**：skip 分支会重复写入 cursor，导致"第 i 个字的音符游标"取错位置，窗口枚举因此大面积返回空解（年轮曾有 9 个窗口 `no_valid_candidate`）。修正后年轮 15 个窗口全部有合法候选，雨爱候选数 6→44。
2. **逐 note 核对按下标比对**：part 内少一个音就会让后面全部错位。改为按 part 内的歌词序列做序列对齐，再比对音高；tone 比较改用建谱器自己的口径（见 §6）。

---

## 5. D｜HFA/ASR 证据分级与歌词来源安全

- 新增匹配等级：`exact_token` / `exact_text` / `residual_text` / `positional` / `missing`，每条记录带来源、时间窗与匹配区间。
- **修了 `used` 跟踪 bug**：回退匹配加入 `matched` 后没有同步更新 `used`，会把已匹配的观测误报成 unused。现在 `observation_unused` 计数与实际一致（最后一页 80 条为真正未被使用的观测）。
- **弱证据降权**：分级对应权重 `exact=1.0 / residual=0.35 / positional=0.25`；代价函数用 `time_scale × weight` 作为分母，弱证据一旦要把字拉离原唱位置，代价迅速超过 unresolved 阈值，从而降级为 review/unresolved，而不是硬拉。
- **公开歌词只作候选来源**：`canonical.apply_canonical()` 默认 `apply=False`，只产出 diff；《年轮》两处「份→分」现在是 `pending_review`，**不再自动改写锁定歌词**，锁定正文仍以录音事实为准。

各歌锚点等级分布：

| 歌曲 | exact_token | exact_text | positional | missing（字） | 观测侧未用 |
|---|---|---|---|---|---|
| 年轮 | 0 | 343 | 6 | 6 | — |
| 最后一页 | 0 | 315 | 3 | 203 | 80（另有 130 条 residual 匹配、3 条 positional） |
| 雨爱 | 371 | 0 | 0 | 0 | 0 |

最后一页 203 字只有"缺观测"，其中 130 条是 residual 匹配、3 条 positional——**这些字的时间证据是弱的**，不得当作真值；该歌 100% 覆盖里有相当比例靠的是单调性与弱锚点，报告如实标注。

---

## 6. E｜GAME 可复现性调查与观测冻结

### 6.1 冻结

三首歌的 GAME / HFA / 歌词输入按 SHA256 固定进新 run（`run_summary.json` 的 `frozen_inputs`），**本轮没有重新生成任何 GAME 输出**。P0/P1 的 run 保持只读。

### 6.2 实验（`scripts/probe_game_reproducibility.py`，同一份冻结人声，18 个切片）

| 配置 | 3 次事件数 | 3 次签名 | 结论 |
|---|---|---|---|
| 同一 session 连续推理 | 468 / 474 / 470 | 三个不同 | **不稳定**（会话内随机状态推进） |
| 每次新建 session | 468 / 468 / 468 | 完全相同 | 进程内稳定 |
| 新建 session + 单线程 | 468 / 468 / 468 | 完全相同 | 与线程数无关 |

跨进程对照（`cross_process_probe.py`，每进程一个新 session，只推理一次）：**464 / 473 / 469，签名互不相同**。

### 6.3 结论（区分已证实与未证实）

- **已证实**：模型哈希未变（五个 onnx 全部与 2026-10-28 记录一致），音频字节相同，切片边界相同，seed=11 相同；
- **已证实**：端口在 `src/agent2utau/transcription/game_onnx.py` 里创建了 `np.random.default_rng(seed)` 却**从未使用**它 → 我们的 seed 完全不控制输出；
- **已证实**：ORT 1.30.0，provider 为 AzureExecutionProvider / CPUExecutionProvider；输出随进程与 session 使用方式变化，与线程数无关；
- **未证实**：ORT 图内随机算子的具体播种机制（进程熵）——本次只做了现象对照，没有读 ORT 源码；
- **未证实**：469（10-28 记录）/ 467（10-31 实跑）/ 464–473（本次）的差异中，有多少来自 ORT 版本漂移（10-28 的 ORT 版本未记录）。
- **下游规则**：GAME JSON 一律按 SHA256 固定复用；回归运行**永不重新生成** GAME。`build.py` 的 tone 取整口径是 `int(tone)`（截断），已抽出 `to_ustx_tone()` 作为唯一口径，避免校验与建谱各算一套。

---

## 7. F｜历史删除核查

`1a3a5bab → 9e5435a7` 之间共 **41 个已跟踪文件被移除**（40 个在 `scratch/`，1 个是仓库根的 `pelican-bicycle.html`），合计 9.9 MB。逐项查证结果（`docs/archive/legacy-scratch/MANIFEST.json`，每条含原路径、原 blob SHA1、SHA256、字节数、持有提交）：

- **40 个 scratch 文件**：其中 **28 个的本地工作副本已经与提交版本不同**（工作副本被后续实验改过），因此"还留在磁盘上"并不等于已保存。已按**提交字节**建立归档副本 `docs/archive/legacy-scratch/<原路径>`（逐字节、不重新编码），并在 manifest 里建立原路径映射。
- **1 个 `pelican-bicycle.html`**：与唱歌项目无关，按用户明确指示删除；字节仍在 Git 历史（`1a3a5bab:pelican-bicycle.html`，blob 见 manifest），manifest 记录了理由与去向。

本轮**没有**再次重组仓库，没有搬迁按路径+SHA 锁定的知识包。

---

## 8. G｜回归协议、环境与产物

### 8.1 运行环境

OpenUtau 0.1.570.9011 ｜ 声库 YousaV1.65c（DiffSinger，DiffSingerChinesePhonemizer，44100/hop 512）｜ ONNX Runtime 1.30.0 ｜ Python 3.12（.venv）｜ Windows ｜ GPU RTX 5080

### 8.2 测试命令与实际输出

```
.venv\Scripts\python.exe -m pytest -q
→ 336 passed in 13.25s
```
新增测试：`tests/unit/test_alignment_status.py`（状态机与退出码）、`test_alignment_baseline.py`（非法延音不得静默丢弃、候选集合、逐 note 核对）、`test_alignment_observations.py`（匹配分级、used 跟踪、弱证据降权）、`test_alignment_lines.py`（跨句拒绝、句区间、窗口决策、候选不越界）、`tests/contracts/test_alignment_cli_exit_codes.py`（5 类故障注入 + 真实退出码）。

仓库门禁：`python tools/repository/check_repository.py` → `{"audio_payloads": 0, "author_projects": 3, "zip_members": 5, "skill_links": 132, "checks": "passed"}`（索引模式与 `--worktree` 模式均通过）。

### 8.3 新产物哈希（SHA256 前 16 位）

| 文件 | 年轮 | 最后一页 | 雨爱 |
|---|---|---|---|
| lyrics_locked.json | 1995057425878945 | 921ccf91c5d1e864 | 0098f7f99b5ae718 |
| notes_normalized.json | 869f74b14630ed37 | e69f2487fbbc925d | 600db958510c8466 |
| mapping.v1.json | 46fe51cfe44896b3 | 337cbad57fe7f2ad | 6e328709ebc4f311 |
| anomalies.json | 766a33768d33defa | 387c0d47d8f405af | 360cb721e504a999 |
| baseline.ustx | 013b489f0eda1bf7 | 7392284a5946e0b2 | 375efaa87dedac10 |
| baseline_verification.json | 258983fe3dee6683 | aac540da5f441816 | 5a15bec790c213a9 |

冻结输入：年轮 game `64420f088857…` / hfa `772dc07e4a92…`；最后一页 game `cf42217c5b87…` / hfa `3777ec0e988f…`；雨爱 game `af10c93395bb…` / hfa 观测 `f10dc00238e8…`。

### 8.4 所有未解字与 note ID

- 年轮未解字：`s0069`、`s0296`、`s0305`、`s0315`、`s0320`、`s0330`
- 最后一页未解字：无；未解音符：`n0060`（非法延音，附四个候选）
- 雨爱未解字：`s0026`、`s0077`、`s0109`、`s0165`、`s0273`
- 需人工复核：`lastpage` 的 `s0045`～`s0049`（所在句锚点覆盖率不足，句界未确立）

### 8.5 真实原生执行边界

本轮**真实调用过原生 Core** 的部分：三个延音合法性探针（inspect-project，含真实 phonemizer 输出）。**没有**做：baseline 的原生音素导出、patch 写回、渲染、A/B 试听。baseline.ustx 已生成并逐 note 核对，但**尚未经过原生回读验证**，因此不能称为"音素可用"。

**听感：`listening=unknown`，`musical_quality=unverified`**——本轮没有任何音频产出可听。

---

## 9. 人工复核记录（P1.1-C 要求）

逐条看过：年轮 6 个未解字、最后一页 1 个未解音符 + 1 个 `no_valid_candidate` 窗口、雨爱 5 个未解字；难例覆盖：重复副歌（年轮副歌出现两次且映射窗口不同）、同字多音（最后一页「没」mei/mo）、「雨爱」的英文 `Rai nie Love` 三音节（保留录音的音节划分，公开歌词只作候选）、快唱段过切分（年轮/雨爱未解字的共同成因）、短元音、跨句。结论：**DP 代价差不能当作准确率证据**，本报告只陈述覆盖与未解事实。

## 10. 涉及代码文件

新增：`src/agent2utau/alignment/status.py`、`canonical.py`；测试 `tests/unit/test_alignment_{status,baseline,observations,lines}.py`、`tests/contracts/test_alignment_cli_exit_codes.py`；脚本 `experiments/alignment/phoneme-alignment-p1.1-20261031/scripts/{build_p1_1_artifacts,probe_game_reproducibility,probe_extender_gap,audit_deleted_files}.py`；归档 `docs/archive/legacy-scratch/`。
修改：`alignment/{lyrics,notes,observations,candidates,validator,baseline,pipeline,__init__}.py`、`openutau/build.py`（新增 `to_ustx_tone()`，不改既有取整行为）、`transcription/game_onnx.py`（新增可选线程参数，生产默认不变）、`cli.py`（`align-lyrics` 状态与退出码）、`tests/unit/test_alignment_{mapping,canonical}.py`、`experiments/alignment/README.md`。

## 11. 下一轮（P2）前置条件

1. 用户决定 `n0060`（四个候选中选一个，或换方案）与其他未解字/未解音符的处理；
2. 用户确认最后两首歌的句界是否按发行版分行；
3. 确认 `build.py` 的 tone 取整口径（截断 vs 四舍五入）是否维持；
4. 确认《年轮》两处「份→分」是否按公开歌词改（当前是待复核候选）。
以上未决之前不进入 P2 音素基线。
