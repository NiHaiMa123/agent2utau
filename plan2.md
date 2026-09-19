# agent2utau — Plan 2：GAME 主转谱 + 自动证据裁决 + Phrase-Level 审核

> 修订日期：2026-09-19
>
> 核心原则：**先把 written score 唱对，再做泠鸢演唱风格。**
>
> 当前阶段：**M2.5 HUMAN REVIEW PILOT = QUALITY HOLD（G5K/rlv6 hard-case routing 已实现，但语义仍未闭合；新增 G5L directional carrier-conflict + post-loop B1 adjudication）。** 最新真实状态：rlv6 已在闭环前将每个字符路由为 `class_A / B1_unmeasurable / B2_carrier_conflict`，B2 不再越权追 anchor，timing confidence 与 lyric intelligibility confidence 已拆分，4/4 package valid，`git_evidence.complete=true`；但 4/4 pilot 仍 `auto_review_ready=false`、`review_ready=false`。独立审计发现：① B2 当前用同一个 `anticipation_candidate` 覆盖 source onset 早于 carrier 和晚于 carrier 两个相反方向；② `ANTICIPATION_MAX_S=0.12` 仅凭绝对毫秒阈值决定 anticipation vs written_timing_suspect，缺乏足够物理/音素证据，不能作为最终 adjudication authority；③ 闭环运行后持续出现 render `acoustic_unmeasurable / acoustic_unstable` 的字符仍保留初始 `class_A`，没有正式降级为 B1。下一步必须修正这三点，再重选/重建 honest pilot。上述语义未关闭前，禁止用户 A/B 复审、禁止记录 calibration decision、禁止 M2.5 freeze。**

---

# 1. 最终流程

```text
原曲
→ decode / separation
→ GAME 多次同配置转谱
→ formal sequence alignment
→ 选择真实 GAME medoid run 作为 Candidate 0
→ multi-run uncertainty graph
→ RMVPE + FCPE + third-F0 + waveform evidence
→ orthogonal pitch / structure / identity / separation states
→ C structure adjudication
→ identity 固定后运行冻结版 B pitch/octave adjudicator
→ finalized machine unresolved 才进入 D phrase-level review
→ D 输出 stable-target + exact-audio-bound human adjudication artifact
→ M2.4 对 machine-safe / valid human-selected single-note pitch candidate 执行可回滚 repair
→ M2.5 对 frozen resolved structure candidate / valid human-selected structure patch 执行 operation-specific 可回滚 repair
→ lyrics ↔ melody mapping
→ OpenUtau / DiffSinger 基础渲染
→ constrained PITD / 演唱细节
→ 泠鸢 style profile
```

旧流程：

```text
歌词字符窗口 → F0 median → heuristic split → MIDI
```

只保留 fallback，不再作为默认 melody transcription。

---

# 2. 已冻结 machine stages

## 2.1 M2.3.2A / A2 / A3 / A4 ✅ FROZEN

Frozen contract：

- pitch / structure / identity / separation 正交；
- pitch / structure lanes 可共存；
- raw flags 不覆盖 calibrated result；
- structure candidate 不直接进入人工；
- SAFE eligible 不等于 repair；
- separator provenance 绑定实际 model path / bytes / config。

## 2.2 M2.3.2B1 / B2 / B3 ✅ FROZEN

关键 commits：

```text
21be525c...  B1 initial pitch/octave adjudicator
283100704470cbffa1866569ed42b7e6d0ce7b28  B2 correctness/calibration
012cbfdf15253a98d50ca25f8f95c6b2c16c312b  B3 independence/provenance
e7500de43e7d99ca9e826430f5005d00281f05a5  B3 final group-gate consistency
```

Frozen B contract：

- GAME run-tone distribution 保留连续支持强度；
- RMVPE / FCPE 各自最多一个独立 family；
- pYIN / ACF / harmonic / subharmonic 先融合为 bounded waveform group；
- final score / margin / supporting groups / gates 使用统一 group-level semantics；
- missing evidence = neutral；
- raw feature 只用于 audit，不能绕过 group gate；
- third-F0 cache freshness 比较当前 runtime version；
- SAFE target 必须绑定 B winner；
- separation-sensitive 会降低 confidence / 可阻止 resolution；
- SAFE gate 必须在 finalized structure state 生效后计算；
- 189s / 202s 永久 no-false-repair regression。

**M2.4 不允许复制/改写 B 的 threshold / score / margin / group gate。Machine-safe 路径只能消费 frozen B 已经给出的 finalized SAFE 结果。**

## 2.3 M2.3.2C1 / C2 ✅ FROZEN @ c0d2648

关键 commits：

```text
676a26e...  C1 structure adjudication
f220012...  C2 structure correctness/lifecycle
58c8847...  C2 evidence-independence/final-order patch
c0d2648a1b86344d455430c0553d70e1726ec017  identity-aware virtual GAME correspondence
```

Frozen C contract：

- all-baseline independent structure discovery；
- H0 keep / H1 split / H2 merge / H3 portamento；
- two plateaus alone 不等于 split；
- F0 changepoint 本身不能证明 written-note boundary；
- RMVPE voiced-drop 不算 independent non-F0 family；
- split / portamento / ornament 必须真实竞争；
- `run_note_counts==0` 不代表 merge；
- C change identity/span 后 old B invalidate + fresh packet + frozen B rerun；
- Candidate 0 不修改；C 本身不执行 structure repair；
- virtual acoustic seed 不等于 GAME evidence；
- virtual GAME correspondence operation-aware / identity-aware；
- parent-spanning GAME long note 不得同时给两个 split children pitch vote；
- virtual GAME denominator 永远保留 total stochastic GAME runs；
- ordinary Candidate 0 frozen-B semantics 不因 virtual adapter 改变。

Freeze acceptance：

```text
SHA: c0d2648a1b86344d455430c0553d70e1726ec017
GitHub Actions run: 35210458722
133 passed / 0 failed
189s no false repair
202s no false repair
Candidate 0 unchanged
0 repair
```

C-freeze routing snapshot：

```text
428-note medoid run4
311 keep
21 resolved_change_candidate
50 auto_resolved
46 phrase_review
0 repair
```

C 不新增 C3/C4，除非 future regression 证明 frozen contract 被破坏。

---

# 3. M2.3.2D Phrase Review ✅ FROZEN @ 905f144

## 3.1 D main workflow

关键 commits：

```text
0bbb09851033563749d41bb603a43bdfa79fa471  phrase-level review workflow
5c542844224ccf9caa675450606819c7ca95f8fc  exact-audio + run-level authority
2a997a2e65e7557655f2c3498c99b247c491238e  stable review identity
905f144637c0fecc5e9e58b060b12cabab7446f6  fail-closed d2→d3 migration integrity
```

D frozen contract：

- finalized `needs_phrase_review` 才进入 D；
- review unit = atomic target group + 完整 phrase context；
- baseline + 最多 3 个真实 machine candidates；
- 不做 candidate Cartesian product；
- blind OPTION labels；
- 同一 item 使用同一 context / tempo / singer / renderer；
- shared gain，不做 per-option independent loudness normalization；
- Candidate 0 不修改，D 自己执行 0 repair；
- `review_item_id / target_key` 表示稳定 unresolved target identity；
- `audio_package_hash` 表示这次用户实际听到的 exact package；
- human decision 同时绑定 stable target + exact audio；
- decision revision append-only；
- `selected_score_patch / provenance / wav_sha256` snapshot 写入 decision；
- d2 / mixed / unknown authority schema fail-closed；
- legacy `ri-NNNN` 永不自动映射到 d3 target；
- `verify_package()` 重新验证实际 SOURCE/OPTION bytes 并重算 `audio_package_hash`；
- `review_item_id == "ri-" + target_key[:16]`；
- `repair_authorized_decision()` 是 M2.4 唯一 human-selected authorization gate。

D 最终 acceptance：

```text
code SHA: 905f144637c0fecc5e9e58b060b12cabab7446f6
remote CI run: 35238843522
pytest: 195 passed / 0 failed
local real-run migration: PASS
legacy authority → review_d2_audit/snapshot-20260917-151133/
rb-d3-render2: 3 real rendered review items PASS
verify_package including final recompute: PASS
human_selected_candidate → M2.4 gate: PASS
Candidate 0 sha256 unchanged
```

**D 已冻结。M2.4 不得 reopen D 来“方便 repair”；如果 repair 需要额外信息，应在 M2.4 自己建立 read-only adapter / audit artifact。**

---

# 4. E1 Remote CI / Freeze Gate ✅ PASS

```text
.github/workflows/ci.yml
trigger: push + pull_request
runner: ubuntu-latest
Python: 3.11
core gate: pytest -q
```

从 C2 起，任何 stage 标记：

```text
FROZEN / PASS / accepted
```

必须同时满足：

```text
local regression green
+ FINAL acceptance SHA 对应 GitHub Actions workflow exists
+ core pytest job == success
+ 不允许拿旧 SHA 的 green run 充数
+ 不允许 skipped/disabled core regression 伪 green
```

依赖本机 OpenUtau / Yousa / E:\ 路径 / 大模型资产的验证必须单列 local/integration acceptance，不得假装被 lightweight CI 覆盖。

---

# 5. 全局不可破坏 contract

## 5.1 Missing evidence

```text
missing / low-confidence evidence
!= support
!= opposition
```

缺失 evidence 必须 neutral。

## 5.2 Evidence independence

```text
raw feature
→ within-group fusion
→ finalized group_scores
→ supporting_independence_groups
→ score / margin / gates
```

禁止从 raw feature 重新构造第二套 resolution truth。

## 5.3 Virtual GAME evidence

Virtual GAME vote 必须来自：

```text
真实 GAME run member note
+ operation-aware structural correspondence
+ 真实 member tone
```

必须区分：

```text
seed_conditional_tone_support   # correspondence audit
seed_effective_game_support     # correspondence audit
winner_game_support             # B winner actual support
winner_game_opposition          # B winner actual opposition
```

不得改变 frozen B scoring。

## 5.4 Candidate 0 immutability

```text
Candidate 0 永不被 adjudication / review / repair 原地覆盖
```

任何变化必须先成为独立 candidate / corrected-score artifact，并提供 rollback。

## 5.5 Human review authority fail-closed

Human-selected repair 必须由：

```text
repair_authorized_decision(run_dir, review_item_id)
```

返回有效 revision。

不得绕过该 gate 去直接读取：

```text
latest_batch.json
任意 batch manifest
旧 decisions.json
all_current_valid_decisions 后自行少做几项检查
OPTION 文件名
机器 hypothesis
```

只要 legacy / mixed / malformed / stale / hash mismatch / target mismatch / bytes mismatch：

```text
no authorization
```

## 5.6 Written score before PITD

M2.4 只能修改 discrete written score。PITD / portamento / vibrato / style 不得用于掩盖 written-note error，也不得进入第一版 repair decision。

---

# 6. Pre-M2.5 Freeze Integrity Patch ✅ PASS @ 8a2d660 (CI 35294735189, 248 passed)

> 目标：**修复已经冻结阶段之间的跨阶段完整性缺口，不重新设计 B/C/M2.4。**
>
> 历史 acceptance 继续有效作为实现基线；本节是进入 M2.5 前的补充 hard gate。完成前：
>
> ```text
> M2.5 structure repair = BLOCKED
> ```

## 6.1 Blocker A — provisional B 必须使用 identity-safe GAME pitch evidence

当前风险路径：

```text
structure_varies / structure lane pending
→ B 先运行，结果标 provisional
→ hypotheses() 已禁止 aggregate run_tones 生成新 hypothesis
→ 但 adjudicate() 仍可能用同一 aggregate run_tones 计算 GAME support
→ C resolved_keep
→ provisional B 被直接 finalize
→ unsafe GAME support 可能进入 final winner / margin / repair gate
```

这违反：

```text
结构未定时 pitch 只能 provisional
+
GAME pitch vote 必须对应确定的 written-note identity
```

### Required fix

必须选择一种可审计、fail-closed 的实现：

```text
Option A:
structure identity 未 finalized 时
→ provisional B 的 GAME pitch group 对 aggregate consensus.run_tones 置 neutral
→ RMVPE / FCPE / waveform / context 可继续形成 provisional evidence
→ C resolved_keep 后，只有 identity-safe GAME evidence 才允许 finalization

或

Option B:
C resolved_keep 后
→ 基于 finalized Candidate-0 identity 重建 identity-safe per-run GAME tone distribution
→ 重新运行 frozen B
→ 新结果替代 provisional result
```

禁止：

```text
仅因为 C == resolved_keep
→ 把曾经消费 identity-unsafe aggregate run_tones 的 provisional B
→ 直接 provisional=False
→ 当作 finalized B
```

### Required regressions

```text
A1. structure_varies=true + aggregate run_tones=[60,64,60,64,...]
    → aggregate tones 不得影响 finalized GAME pitch group

A2. provisional B + C resolved_keep
    → finalized winner/margin 必须来自 identity-safe evidence

A3. provisional B + C resolved_change_candidate
    → old B 继续 invalidate；virtual-note frozen-B path 不回归

A4. ordinary structure-stable Candidate 0
    → 原 frozen-B GAME continuous-support semantics 不变

A5. 189s / 202s permanent regressions 继续 no false repair
```

---

## 6.2 Blocker B — C 的 missing evidence 必须真正 neutral

当前风险：

```text
_boundary_energy() 在 insufficient samples / unavailable 时
→ support = 0

但 H0 / H3 使用：
→ acoustic_boundary = 1 - nonf0
→ support=0 被解释成 keep-side 满支持 1.0
```

以及：

```text
n_runs == 0
→ game_one = 1.0
```

这会把：

```text
无法观测 / 数据不足
```

错误变成：

```text
强 one-note / keep evidence
```

违反全局 contract：

```text
missing / low-confidence evidence
!= support
!= opposition
```

### Required fix

boundary evidence 至少区分：

```text
available
boundary_support
continuity_or_no_boundary_support
```

语义：

```text
insufficient samples / unavailable
→ available=false
→ boundary group contributes 0 to H0/H1/H3
→ neutral

充分观测且确实存在 local dip/recovery
→ boundary_support > 0

充分观测且确实支持连续/无边界
→ continuity_or_no_boundary_support > 0
```

不得再用：

```text
1 - boundary_support
```

把 missing 自动转换成 H0 support。

GAME structure 同理：

```text
n_runs == 0 / run_note_counts unavailable
→ game structure group neutral
→ game_one = 0
→ game_split = 0
```

不得：

```text
no GAME structure evidence
→ game_one = 1.0
```

### Required regressions

```text
B1. boundary window insufficient samples
    → H0 acoustic group == 0, not 1

B2. boundary evidence entirely unavailable
    → cannot by itself produce resolved_keep

B3. run_note_counts missing/empty
    → GAME structure group neutral

B4. missing boundary + missing GAME structure evidence
    → cannot unlock final_structure_clear solely through absence

B5. real flat/continuous observed signal
    → may support H0 only through explicit continuity evidence,
      not through complement-of-missing

B6. existing TRUE_SPLIT / portamento / merge / virtual correspondence
    regressions remain green
```

---

## 6.3 Blocker C — M2.4 Candidate-0 binding 必须同时包含 semantic + full-file hash

当前 M2.4：

```python
candidate0_sha256 = sha(canonical notes)
```

这只能证明：

```text
Candidate-0 notes semantic content 未变化
```

不能证明：

```text
baseline_game.json exact artifact 未变化
```

例如以下变化目前可能不 stale：

```text
run_index
provenance
metadata
schema-adjacent fields
file bytes / formatting
```

但 repair plan 的 authorization/freshness 应绑定 build-plan 时实际读取的 Candidate-0 artifact。

### Required fix

repair plan 同时记录：

```text
candidate0_notes_sha256
candidate0_file_sha256
```

其中：

```text
candidate0_notes_sha256
= ordered notes 的 canonical semantic hash

candidate0_file_sha256
= diagnostic/baseline_game.json exact bytes sha256
```

apply 前必须重新验证二者。

`corrected_score.json` / `repair_manifest.json` 至少记录：

```text
base_candidate0_notes_sha256
base_candidate0_file_sha256
```

本阶段采用严格 freshness：

```text
baseline_game.json 任意 byte/material artifact change
→ old repair_plan stale
→ refuse apply
→ regenerate plan
```

这不改变 Candidate 0 immutability，也不重新 adjudicate。

### Required regressions

```text
C1. notes tone/span changed
    → semantic hash + file hash both stale

C2. notes unchanged，但 run_index/provenance/metadata changed
    → file hash stale → refuse apply

C3. notes unchanged，但 baseline_game.json bytes changed
    → file hash stale → refuse apply

C4. apply 自身不写 baseline_game.json
    → pre/post file sha identical

C5. same exact Candidate-0 artifact + same authority
    → repair plan deterministic / same plan_hash
```

---

## 6.4 Blocker D — legacy repair plan 必须 fail-closed

```text
42cb1be 已保证：
新 build_plan()
→ candidate0_notes_sha256
→ candidate0_file_sha256
→ apply 可验证 exact Candidate-0 artifact

但 legacy m24-1 repair_plan.json 可能没有 candidate0_file_sha256。
当前 verify_freshness() 逻辑：
plan.get("candidate0_file_sha256") is not None
→ 才验证 full-file hash

因此：
旧 plan 缺 file hash
→ 跳过验证
→ notes 未变化时仍可能继续 apply
```

这违反本阶段的严格 freshness / fail-closed contract。旧 plan 不能因为“字段不存在”获得兼容性豁免。

### Required fix

```text
1. repair-plan schema 必须能够区分 dual-binding plan。
   推荐：
   REPAIR_SCHEMA: m24-1 → m24-2
   或等价的显式 binding/schema version。

2. repair-apply / verify_freshness 必须 fail-closed：
   missing candidate0_notes_sha256 → stale/reject
   missing candidate0_file_sha256 → stale/reject
   candidate0_file_sha256 == null/None → stale/reject
   unsupported/legacy repair schema → stale/reject

3. build_plan 必须要求 baseline_game.json exact artifact 存在。
   无法取得 full-file sha256 时不得生成可 apply 的 plan。

4. legacy m24-1 plan 不做 silent migration，不从当前文件补算缺失 hash，
   不猜它当时绑定了哪个 Candidate-0 artifact：
   → reject/stale
   → 要求重新 repair-plan。

5. 新 plan 的 plan_hash 必须覆盖 schema + 两个 Candidate-0 bindings。
```

### Required regressions

```text
D1. legacy m24-1 plan，缺 candidate0_file_sha256
    → repair-apply hard refuse / stale

D2. current/new schema，但 candidate0_file_sha256 missing 或 None
    → hard refuse / stale

D3. current/new schema，但 candidate0_notes_sha256 missing
    → hard refuse / stale

D4. baseline_game.json 不存在
    → build_plan hard fail；不得产生可 apply plan

D5. exact new dual-bound plan
    → 正常 apply

D6. legacy plan 不能通过“读取当前 baseline_game.json 后补 hash”自动迁移
    → 必须重新 build_plan
```

完成本 blocker 前：

```text
PRE-M2.5 INTEGRITY != PASS
M2.5 = BLOCKED
```

---

## 6.5 Scope guard

本 patch **禁止顺手扩大范围**：

```text
不新增 B4 algorithm
不重调 B weights/thresholds，除非为 Blocker A 必需
不新增 C3 model
不开放 structure auto-repair
不修改 D human review semantics
不修改 review authority schema
不改变 M2.4 v1 pitch-only patch shape
不为了产生更多 repair 放宽 gate
```

允许的代码变化仅限：

```text
B provisional/finalization evidence routing
C evidence availability / neutral semantics
M2.4 Candidate-0 freshness binding
legacy repair-plan schema / dual-binding fail-closed
对应 regression / docs / audit fields
```

---

## 6.6 Freeze Integrity Acceptance Matrix

全部满足才允许重新标记：

```text
PRE-M2.5 INTEGRITY = PASS
M2.5 = UNBLOCKED
```

### A — B identity safety

```text
1. structure-ambiguous aggregate run_tones 不进入 finalized GAME pitch support
2. provisional B 不能因 C resolved_keep 自动洗白 unsafe GAME evidence
3. finalized B 使用 identity-safe GAME evidence
4. structure-change virtual B path 保持 identity-aware correspondence
5. ordinary Candidate-0 frozen-B semantics 不变
```

### B — C missing neutrality

```text
6. insufficient boundary samples = neutral
7. unavailable boundary evidence = neutral
8. observed continuity 必须显式建模，不得使用 1-support 代替
9. missing run_note_counts / n_runs=0 = neutral
10. missing evidence 不得单独形成 resolved_keep
11. missing evidence 不得单独 unlock final_structure_clear / SAFE repair
```

### C — Candidate-0 binding

```text
12. plan binds candidate0_notes_sha256
13. plan binds candidate0_file_sha256
14. apply verifies both hashes
15. metadata/provenance-only Candidate-0 artifact change stales plan
16. Candidate 0 on disk remains immutable
17. corrected-score/manifest record both base hashes
```

### D — Legacy repair-plan fail-closed

```text
18. legacy/unsupported repair schema cannot authorize apply
19. missing candidate0_notes_sha256 = stale/reject
20. missing candidate0_file_sha256 = stale/reject
21. candidate0_file_sha256 null/None = stale/reject
22. build_plan without baseline_game.json exact bytes = hard fail
23. legacy plan is never silently migrated by backfilling current hashes
24. only a freshly regenerated dual-bound plan may proceed to apply
```

### Permanent safety / regression

```text
25. 189s no false machine repair
26. 202s no false machine repair
27. virtual GAME correspondence tests green
28. D stable-target/exact-audio authority tests green
29. M2.4 human-selected authorization tests green
30. M2.4 conflict/dedupe/rollback tests green
31. 0 repair remains legal
32. no structure auto-repair introduced
```

### Remote gate

```text
33. new FINAL implementation SHA after Blocker D fix
34. GitHub Actions workflow exists for that exact SHA
35. core pytest == success
36. A/B/C/D integrity regressions included
37. legacy-plan fail-closed regressions included
38. no skipped/disabled core regression
```

完成后在本节记录：

```text
partial implementation SHA: 42cb1be
partial remote CI run: 35293468251 = success
pytest at 42cb1be: 242 passed / 0 failed / 0 skipped
real-run diagnostic at 42cb1be: diag-20260917-181538-6aec
189s: no machine repair
202s: no machine repair
Candidate-0 dual binding for newly generated plans: implemented
final acceptance SHA: 8a2d660
final remote CI run: 35294735189 = success
CI checkout verified SHA: 8a2d660558512a82d503833ef4bd19bf82835a06
pytest at 8a2d660: 248 passed / 0 failed / 0 skipped
pytest duration: 16.73s
legacy m24-1 plan on real run: refused (unsupported_plan_schema:m24-1);
  regenerated m24-2 plan applied normally (0 repairs, C0 identical)
```

**PRE-M2.5 INTEGRITY = PASS @ 8a2d660 → M2.5 UNBLOCKED（实现待启动）**

---

# 7. M2.4 — SAFE Repair Engine ✅ HISTORICAL FREEZE @ ce083c9 (CI 35289803217, 226 passed)

> M2.4 的实现与历史 acceptance 保留；但在 §6 Freeze Integrity Patch 完成前，**不得把 ce083c9 单独视为进入 M2.5 的充分条件**。


## 7.1 第一版 scope：只做 single-note written-pitch retune

M2.4 v1 **只允许**：

```text
one existing Candidate-0 note
→ same note identity
→ same start
→ same end
→ same lyric/metadata identity
→ written MIDI/tone changes
```

第一版明确禁止：

```text
split
merge
insert note
delete note
boundary shift
start/end duration change
lyric remap
PITD / vibrato / expression change
phonemizer change
context notes change
```

任何 structure-shaped patch 即使来自有效 human review，也：

```text
M2.4 v1 → blocked_structure
```

留到 M2.5 / 独立 structure precision gate。

**不要为了“让 repair 数量更多”扩大 scope。0 repair 合法。**

---

## 7.2 两条合法输入路径

### Path A — machine-safe

只能消费 frozen A/B/C 已经 finalize 的 machine-safe pitch repair candidate。

必须满足：

```text
existing frozen SAFE gate == pass
pitch result finalized
winner/target 已绑定
final structure semantics == keep / identity unchanged
old B 没有 invalidated pending rerun
no unresolved structure dependency
no separation-sensitive blocker
patch shape == single-note pitch-only
```

M2.4 **不得重新计算**：

```text
B score
margin
group support
SAFE threshold
F0 winner
structure truth
```

M2.4 的工作是验证 frozen upstream authorization + materialize repair，不是重新发明一套 adjudicator。

### Path B — human-selected

唯一入口：

```python
rev = repair_authorized_decision(run_dir, review_item_id)
```

只有 `rev != None` 才继续。

随后直接消费：

```text
rev.selected_score_patch
rev.selected_provenance
rev.selected_wav_sha256
rev.revision_id
rev.target_key
rev.audio_package_hash
```

绝对禁止：

```text
根据 selected_option_id 再去 manifest 重新找 patch
根据 candidate_id 重新生成 patch
根据 B/C hypothesis 重新推导 pitch
根据当前 F0 再“确认”并改成另一个 tone
把用户选 A/B/C 解释成新的机器 winner
```

**用户授权的是当时 exact-audio package 里听到的那个 snapshot，不是一个可重新解释的 candidate label。**

---

## 7.3 Human-selected v1 仍然只接受 pitch-only snapshot

`repair_authorized_decision()` 通过后，还必须对 `selected_score_patch` 做 shape validation。

合法 v1 patch 至少满足：

```text
operation == retune / pitch-only equivalent
exactly one existing Candidate-0 note id
before span == Candidate-0 span
after span == Candidate-0 span
no inserted/deleted child ids
no note-count change
new tone finite / legal MIDI range
new tone materially differs from baseline
```

如果有效 D selection 是 split / merge / boundary-shift：

```text
human decision 保持有效
M2.4 不丢弃它
但 repair_status = blocked_structure
```

后续 M2.5 可直接复用该 human authority，不要求用户重复听同一个 package，前提是 authority/package 仍有效。

---

## 7.4 Repair plan 与 apply 必须分离

推荐实现两个阶段（CLI 名称可不同）：

```text
repair-plan
→ read-only 收集所有 eligible repairs
→ validate / dedupe / detect conflict
→ 输出 repair_plan.json
→ Candidate 0 不变

repair-apply
→ 只消费一个已验证 repair_plan
→ copy Candidate 0
→ deterministic apply
→ 输出 corrected_score.json + repair_manifest.json
→ Candidate 0 仍不变
```

不得：

```text
扫描 packet 时顺手原地改 baseline
边 adjudicate 边写 Candidate 0
review-decide 后自动修改源 score
```

Plan artifact 必须可审计、可重放。

---

## 7.5 Repair identity / idempotency

每个 repair 必须有稳定 `repair_id`。

建议 canonical identity 至少包含：

```text
diagnostic_run_id
Candidate-0 hash
source_type: machine_safe | human_selected
source authority id
note_id
before tone/span
after tone/span
```

Human-selected 还必须包含：

```text
review_item_id
target_key
revision_id
audio_package_hash
```

Machine-safe 至少包含：

```text
packet/note id
frozen B/C result identity
winning hypothesis / target
```

同一 repair 重复规划：

```text
same repair_id
→ dedupe
```

同一 plan 重复 apply：

```text
corrected score byte-equivalent / semantically identical
不得二次叠加
```

---

## 7.6 Conflict policy：禁止 silent precedence

一个 Candidate-0 note 在 v1 最多只能有一个 material repair。

若两个来源对同一 note：

```text
建议相同 after tone
→ dedupe，保留多个 provenance refs

建议不同 after tone
→ blocked_conflict
→ 不 repair
```

不要默认：

```text
human 永远覆盖 machine
machine 永远覆盖 human
最后写入者获胜
confidence 大者获胜
```

如果未来需要 precedence，另立显式规则 + regression；v1 先 fail-closed。

---

## 7.7 Corrected-score artifact

M2.4 输出是 **Candidate 0 的 copy-on-write 派生物**，不是 Candidate 0 本体。

推荐：

```text
runs/<diag>/repair/
  repair_plan.json
  corrected_score.json
  repair_manifest.json
```

路径可调整，但语义必须成立。

`corrected_score.json`：

```text
base_candidate0_sha256
ordered notes
applied repair ids
corrected_score_sha256
```

`repair_manifest.json` 每条至少记录：

```text
repair_id
repair_schema_version
diagnostic_run_id
Candidate-0 sha256
corrected-score sha256
note_id
region
before: {start,end,tone,...}
after:  {start,end,tone,...}
source_type: machine_safe | human_selected
source packet / source authority
B/C finalized status
winning hypothesis / target if machine-safe
winner_game_support / winner_game_opposition if available
group_scores
supporting/opposing groups
confidence / margin
review schema / identity schema if human
review_item_id / target_key if human
decision revision_id if human
audio_package_hash if human
selected_score_patch / provenance / wav_sha256 if human
gates_passed
blocked_reason if not applied
rollback_data
created_at
```

不要为了填字段而伪造不存在的数据；missing audit field 可以显式 `null`，但 eligibility gate 所需字段缺失必须 fail-closed。

---

## 7.8 Rollback contract

Rollback 的定义不是“反向猜一个 tone”，而是：

```text
Candidate 0 immutable
+ repair_manifest 完整记录
→ 随时重新从 Candidate 0 构建 corrected score
```

必须支持：

```text
apply all valid repairs
apply selected repair ids
exclude one repair id and rebuild
rebuild zero repairs == Candidate 0 semantically identical
```

不得依赖修改后的 score 去恢复原值。

---

## 7.9 Post-apply integrity verification

M2.4 apply 后只做 integrity verification，不重新 adjudicate。

至少验证：

```text
base Candidate-0 hash 与 plan 绑定值一致
note count unchanged
note ids unchanged
note ordering unchanged
非 target note bytes/semantic fields unchanged
target start/end unchanged
只有 target written tone 改为 authorized after tone
applied repair count == manifest applied entries
corrected_score hash 可重算
repair_plan hash / manifest hash 可重算
Candidate 0 on disk hash unchanged
```

Human path 额外验证：

```text
repair_authorized_decision() 在 apply 时再次调用
returned revision_id == plan snapshot revision_id
returned audio_package_hash == plan snapshot hash
selected_score_patch == plan snapshot patch
```

也就是说：

```text
plan 后 review/package 若 stale
→ apply 必须拒绝
```

Machine-safe path 额外验证 upstream frozen artifact 仍是 plan 时绑定的同一版本/hash。

---

## 7.10 Repair plan freshness

`repair_plan.json` 不是永久授权。

Plan 至少绑定：

```text
diagnostic_run_id
Candidate-0 sha256
source diagnostic artifacts hashes/ids
review authority schema/version if used
每条 human revision_id + audio_package_hash
repair schema version
```

以下任一 material change：

```text
Candidate 0 changed
diagnostic run changed
machine adjudication artifact changed
human decision superseded
review package stale
review authority migrated/schema changed
selected patch changed
```

→ old plan stale → refuse apply → regenerate plan。

---

## 7.11 189s / 202s permanent safety

永久 regression：

### ~189.84s

```text
extractor conflict / ambiguity
→ no false machine repair
```

如果未来用户在 D 明确选择某个 **pitch-only** candidate，并且 `repair_authorized_decision()` 当前仍 valid：

```text
可以作为 human_selected repair
```

但不能因为 M2.4 上线就把旧 machine unresolved 重新解释成 machine-safe。

### ~202.3/202.5s

```text
GAME stochastic identity/pitch ambiguity
→ no false machine repair
```

同理，只有 valid human-selected pitch-only snapshot 才能进入 human path；无人工 selection 时保持 unresolved。

---

## 7.12 0 repair / partial repair 是正常结果

M2.4 不以“修了多少”为成功指标。

允许：

```text
0 machine-safe repairs
0 human-selected repairs
只有部分 46 review items 已有人类 decision
其余 unresolved 原样保留
```

M2.4 可以对当前已经具备 authorization 的区域增量生成 corrected score；不得要求先把 46 个 phrase 全部人工审核完。

---

# 8. M2.4 Acceptance Matrix

全部通过后才允许：

```text
M2.4 = FROZEN
→ M2.5
```

## 8.1 Scope / patch-shape gate

```text
1. v1 只允许 single existing-note pitch retune
2. target note id 必须存在于 Candidate 0
3. target start 不变
4. target end 不变
5. note count 不变
6. note identity/order 不变
7. insert patch → blocked_structure
8. delete patch → blocked_structure
9. split patch → blocked_structure
10. merge patch → blocked_structure
11. boundary-shift patch → blocked_structure
12. lyric/PITD/expression patch → reject or out_of_scope
13. invalid/non-finite/out-of-range tone → reject
14. after tone == before tone → no-op / not a repair
```

## 8.2 Machine-safe path

```text
15. only frozen upstream finalized SAFE result may enter
16. provisional B result → reject
17. invalidated-waiting-rerun B result → reject
18. unresolved structure dependency → reject
19. separation-sensitive blocker → reject according to frozen B SAFE result
20. M2.4 不重算 frozen B score/margin/threshold
21. machine repair target == frozen B authorized target
22. frozen upstream artifact material change → plan stale
```

## 8.3 Human-selected path

```text
23. ONLY repair_authorized_decision() may authorize
24. None → no human repair
25. baseline → no repair
26. equivalent → no repair
27. human_rejected_all → no repair
28. manual_followup_required → no repair
29. stale package → no repair
30. invalid bytes/hash → no repair
31. target/id mismatch → no repair
32. valid human_selected_candidate pitch-only snapshot → eligible
33. selected_score_patch consumed directly from revision snapshot
34. OPTION label is never reinterpreted into a new patch
35. B/C hypotheses are never re-run to replace human-selected patch
36. valid human structure selection → preserved but blocked_structure in M2.4 v1
37. plan→apply 之间 human revision superseded → refuse apply
38. plan→apply 之间 audio_package_hash changed → refuse apply
```

## 8.4 Candidate 0 / corrected score integrity

```text
39. planning executes 0 mutation
40. apply never writes Candidate 0
41. Candidate-0 sha256 before/after identical
42. corrected score starts from exact Candidate-0 snapshot
43. non-target notes unchanged
44. target span unchanged
45. only authorized tone changes
46. corrected-score hash deterministic/recomputable
47. zero-repair rebuild == Candidate 0 semantically identical
```

## 8.5 Idempotency / conflict / rollback

```text
48. same evidence → same repair_id
49. duplicate identical repair dedupes
50. same note + same after tone from multiple provenance → one material patch
51. same note + different after tone → blocked_conflict
52. no silent human-vs-machine precedence
53. applying same plan twice does not double-change tone
54. rebuild excluding one repair restores that note to Candidate-0 value
55. rebuild with zero repair ids restores full Candidate-0 score
56. rollback never depends on guessing current tone
```

## 8.6 Audit completeness

```text
57. every applied repair has before/after
58. source_type recorded
59. machine repair links frozen B/C provenance
60. human repair links review_item_id/target_key/revision/audio_package_hash
61. human repair snapshots selected_score_patch/provenance/wav hash
62. gates_passed recorded
63. blocked entries have machine-readable blocked_reason
64. plan hash + corrected-score hash + manifest hash reproducible
65. missing non-gating audit field represented explicitly, not fabricated
```

## 8.7 Permanent safety regressions

```text
66. 189s no false machine repair
67. 202s no false machine repair
68. D remains 0-repair stage
69. frozen A/B/C/D tests remain green
70. structure auto-repair remains disabled
71. PITD/style remains outside M2.4
72. 0 repairs remains legal
```

## 8.8 Production-path tests

Tests不能只手工造一个 repair dict；至少覆盖真实 adapter chain：

```text
machine:
real diagnostic packet/artifact
→ frozen SAFE result adapter
→ repair-plan
→ repair-apply
→ corrected score / manifest

human:
real d3 review authority fixture
→ repair_authorized_decision
→ exact revision snapshot
→ repair-plan
→ repair-apply
→ corrected score / manifest
```

至少包含：

```text
73. machine-safe pitch-only end-to-end apply
74. machine unresolved end-to-end no-op
75. valid human pitch selection end-to-end apply
76. human baseline end-to-end no-op
77. human structure selection end-to-end blocked_structure
78. stale human plan refused at apply
79. duplicate same-note repair dedupe
80. conflicting same-note repairs blocked
81. Candidate 0 unchanged through full production path
82. corrected score deterministic on rerun
```

## 8.9 Local integration acceptance

在真实《年轮》diagnostic run 上：

```text
A. dry-run/repair-plan 全曲
B. 至少一个合法 pitch-only candidate 若存在
C. 至少一个 blocked unresolved/permanent case（189s 或 202s）
D. 若当前已有 valid human-selected pitch-only item，则走一次 human path
```

验证：

```text
Candidate 0 sha256 unchanged
repair_plan 可重跑一致
corrected_score 可重建
blocked reasons 可审计
189/202 无 false machine repair
真实 human authority 只能通过 repair_authorized_decision 进入
```

若当前没有任何合法 repair：

```text
0 applied repairs + 所有 blocker 正确
```

仍然可以通过 M2.4 acceptance。

## 8.10 Remote CI gate

Final M2.4 acceptance 必须：

```text
FINAL implementation SHA
→ GitHub Actions workflow exists
→ pytest job success
→ M2.4 production-path regressions included
→ frozen A/B/C/D regressions green
→ 189/202 permanent regressions green
→ no skipped/disabled core regression
```

只有全部通过后：

```text
M2.4 = FROZEN
M2.5 = UNBLOCKED
```

---

# 9. D Phrase Review UX Contract

Human review 的目标：

```text
听完整 phrase
→ 比较 baseline / A / B / C
→ 点哪个听起来对
```

用户不需要：

```text
填写 MIDI
填写 Hz
判断 cents
判断“高一个八度还是低一个八度”
```

默认 phrase context：

```text
min ~3s
normal 5–8s
max ~12s
优先 LRC / vocal silence / breath gap
包含 target ±2–3 notes
```

每个 item 最多：

```text
Baseline + 3 alternatives
```

Decision semantics：

```text
Baseline
→ human_resolved_keep
→ no repair

A/B/C
→ human_selected_candidate
→ 只有通过 d3 stable-target + exact-audio validity 才能进入后续 repair

都差不多 / equivalent
→ human_no_preference
→ keep baseline
→ no repair

都不对 / none_correct gen1
→ human_rejected_all
→ generation-2 regeneration queue

none_correct gen2
→ manual_followup_required
→ no repair
```

46 个 phrase_review 不需要全部完成后才能跑 M2.4。M2.4 只消费当前已经合法 finalized / authorized 的区域，其余区域保持 unresolved。

---

# 10. M2.5+ 后续阶段边界

## 10.1 M2.5 — PROBABLE structure repair ← CURRENT / CALIBRATION HOLD

M2.4 v1 不实现 structure repair。Pre-M2.5 integrity 已通过，因此 M2.5 可以正式开始，但 **structure repair 仍需自己的 precision / identity / rollback acceptance**，不能因为 upstream 已冻结就自动视为安全。

M2.5 第一阶段目标：

```text
只建立 structure-repair plan/apply contract
→ 优先支持已有 human-selected blocked_structure authority
→ 再考虑 machine structure candidate
→ Candidate 0 仍 immutable
→ split / merge / boundary-shift 分开建模，不共享一个模糊 patch
```

M2.5 开始前置条件已经满足：

```text
M2.4 pitch-only repair correctness frozen
Pre-M2.5 integrity PASS @ 8a2d660
legacy plan fail-closed / m24-2 active
189s / 202s permanent no-false-repair regressions green
```

但 M2.5 自身要建立新的 acceptance：

```text
structure precision 独立 acceptance
split patch identity + rollback contract
merge patch identity + rollback contract
boundary-shift patch identity + rollback contract
structure-specific stale-plan / authority checks
structure-specific no-false-repair regressions
real-run phrase-context verification
remote CI on FINAL implementation SHA
```

### 10.1.1 Human-selected structure path

优先消费 M2.4 已保留的：

```text
blocked_structure
+ valid repair_authorized_decision()
+ selected_score_patch snapshot
+ target_key / revision_id / audio_package_hash
```

原则：

```text
用户已经听过并选择的同一个 exact-audio package
→ 不要求重复审核

但：
human-selected structure
!= unconditional apply

仍必须验证：
patch shape
Candidate-0 identity/span
authority freshness
operation legality
rollback completeness
non-target invariance
```

禁止把 OPTION label、旧 hypothesis 或当前 F0 重新解释成另一个 structure patch。

### 10.1.2 Machine structure path

Machine auto-repair 不能直接把所有：

```text
resolved_change_candidate
```

都 materialize。

至少需要 operation-specific precision gate：

```text
split:
  identity-safe child mapping
  boundary confidence
  minimum child duration
  no lyric/phoneme corruption

merge:
  exact adjacent identity
  merged-span legality
  lyric semantics explicitly defined

boundary-shift:
  same note identity
  monotonic ordering
  no overlap / negative duration
  neighbor invariance
```

低置信度或 evidence family 不足：

```text
→ phrase_review / unresolved
→ no repair
```

### 10.1.3 Structure repair plan/apply

继续沿用 plan/apply 分离：

```text
structure-repair-plan
→ read-only
→ bind exact Candidate-0 artifact + authority
→ operation-specific validation
→ conflict detection

structure-repair-apply
→ verify freshness / authority again
→ copy-on-write
→ deterministic apply
→ corrected-score + structure-repair manifest
```

不得原地修改 Candidate 0。

### 10.1.4 Non-blocking P2 audit hardening — plan_hash verification

当前 M2.4 `plan_hash`：

```text
build_plan() 会生成
manifest 会记录
但 apply_plan() 不会重新计算并验证
```

这不会绕过当前 Candidate-0 双 hash、machine authorization 或 human authority，因此 **不是 M2.5 blocker**。但它意味着 repair plan 本身的 tamper-evidence 还不完整。

建议在 M2.5 触碰 plan/apply 基础设施时统一补：

```text
canonical_plan_hash(plan)
→ 排除 created_at / plan_hash 自身等非绑定字段
→ schema + run_id + Candidate-0 bindings + authority bindings
  + repairs/operations + status/conflict semantics
→ apply 前重新计算
→ recomputed != stored plan_hash
   => stale/tampered → reject
```

至少回归：

```text
P2-1. 修改 repair operation / after tone/span，但保留旧 plan_hash
      → apply reject

P2-2. 修改 authority binding，但保留旧 plan_hash
      → apply reject

P2-3. 修改 Candidate-0 binding，但保留旧 plan_hash
      → existing freshness gate 或 plan_hash gate reject

P2-4. exact untouched plan
      → hash recompute identical，正常 apply
```

该项优先级：

```text
P2 audit hardening
不阻塞 M2.5 start
建议在 structure repair plan/apply schema 稳定前完成
```

Human-selected structure candidate 可以作为 M2.5 输入，但仍需 structure repair gate；“用户听起来选了它”不等于可以无条件开放所有 structure auto-repair。

### M2.5 implementation record — ✅ ENGINE PASS @ 73819a9 / CI 35297439976; FINAL FREEZE HOLD

```text
FINAL implementation SHA: 73819a996d64ac33c6eb69e1c71036eb53557c0a
remote CI: run 35297439976 → success, pytest 272 passed / 0 failed (18.76s)
schema: structure plan/manifest = m25-1（独立 schema，不复用 m24-2）

实现核对：
[⚠] structure precision FINAL acceptance 尚未成立。
    当前 24 个 operation-specific tests 证明的是 patch legality、
    lifecycle、fail-closed、rollback、tamper detection；它们不证明
    C 的 TRUE_SPLIT_CANDIDATE 在真实歌曲上的 false-positive rate
    已低到足以自动修改 written score。
[✓] split patch identity + rollback — children 精确 tile parent
    span @boundary、child tone 只能来自 resolved virtual-B winner
    （identity-safe child mapping）、MIN_SPLIT_DUR_S、subset/zero
    rebuild 从 C0 重建
[✓] merge patch identity + rollback — exact adjacent identity、
    merged span == union、single virtual-B winner tone
[✓] boundary-shift patch identity + rollback — same note identity、
    monotonic ordering、no overlap/negative/no-op
[✓] structure-specific stale/authority — schema m25-1 fail-closed、
    C0 双 hash、residual_triage sha、machine adapter 重跑 patch
    相等性、human revision/aph/selected_score_patch 复核、
    plan_hash 重算（P2 hardening 完成，同时覆盖 m24-2 plan）
[✓] structure no-false-repair — needs_phrase_review / unresolved /
    缺 boundary confidence / separation-sensitive / vb unresolved
    均不得 materialize
[⚠] real-run engine output — diag-20260917-181538-6aec
    engine 可生成 21 machine split + 1 human split；但其中 21 个
    machine split 尚未经过独立 phrase-level precision calibration，
    因此 504→526 只能视为 candidate corrected score，不能作为
    trusted final written score。1 个 human split authority 不受此 hold
    影响。189.84s / 202.52s 永久回归与 C0 immutability 仍 PASS。
[✓] remote CI on FINAL SHA — run 35297439976
```

### 10.1.5 Blocker E — machine structure precision 必须独立校准 ⚠️ INFRA IMPLEMENTED / HUMAN REVIEW NOT READY

实现记录（`5a4a486`，CI `35299909323`，279 passed）：

```text
src/agent2utau/structure_calibration.py (schema m25-cal-1)
→ plan_calibration: 每个 machine candidate → review-shaped item
  （精确 repair patch + blind_order 的 [baseline, candidate] 对
  + phrase_window + context + plan_hash），确定性重建，repair_id/
  patch 与 repair plan 完全一致
→ build_calibration: 共享 SOURCE phrase clip + 双 option 渲染
  （同一 bridge/singer/tempo/gain/provenance），manifest 记录
  repair_id + patch_sha256 + candidate/baseline role
→ decide(): verify_package 逐字门槛 → OPTION_i 映射 role →
  human_confirmed_machine_split / machine_structure_false_positive /
  no_demonstrated_benefit / unresolved；append-only decisions.json
  + supersede；rebuild_calibration_state 输出 spec 要求的全部
  计数字段 + measured_song_level_precision
→ calibration_authorized(): machine repair 唯一授权门 — 最新非
  superseded decision 必须 confirmed + patch_sha 一致 + aph 仍
  逐字可重算；其余一律无授权
→ build_structure_plan: 未确认 machine candidate →
  calibration_pending（可审计、不应用）；verify_freshness:
  confirmed 后被 supersede → calibration_revoked stale
→ CLI: structure-calib-plan / structure-calib（交互 blind A/B）
  / structure-calib-decide / structure-calib-status

附带修复的共享 latent bug：split parent 无 aligned lyric char 时
第一个 child 变成悬空 '+' extender（gap → render 拒绝）；first
child 现在回退与未匹配 note 相同的中性 'a'。

真实 run diag-20260917-181538-6aec：
21/21 包渲染完成且 verify_package 全部 valid；
plan = 21 calibration_pending + 1 human eligible；
trusted corrected score = 504→505（仅 human split note_0301）；
189.84s=58.12 / 202.52s=65.3 不变；C0 file hash 不变。
```

原始规格（保留）：

```text
C → TRUE_SPLIT_CANDIDATE
→ M2.5 再验证同一 dual-F0 / non-F0 / GAME split 条件
→ virtual-B child pitch 已 resolved
→ patch legality OK
→ auto materialize
```

其中 virtual-B、finite tone、minimum child duration、separation sensitivity 等检查可以证明：

```text
如果应该 split，patch 应该怎样合法执行 / child 应该唱什么 pitch
```

但不能独立证明：

```text
这里真的应该从 one written note 改成 two written notes
```

因此 synthetic unit tests != structure precision acceptance。

#### 当前 real-run calibration set

以 `diag-20260917-181538-6aec` 的 **21 个 machine split** 作为本轮完整校准集。Calibration 完成前：

```text
machine_structure candidate 可以生成 / 审计 / 渲染
但 status 不得作为 trusted auto-apply authority
不得直接进入最终 written score
不得以 504→526 作为 M2.5 最终正确结果
```

已有 human-selected split 不受此限制，因为它已有 exact-audio human authority。

#### Phrase-level A/B calibration UX

每个 machine split 生成完整短句对比：

```text
SOURCE: 原曲或 separated vocal，供语境参考
Baseline: Candidate 0 / 未 split
Split: M2.5 machine candidate

同一 phrase window
同一 singer / tempo / renderer / gain
除 target split 外其余 score 完全相同
默认 5–8s，必要时 3–12s
```

用户只需要选择：

```text
Baseline 更对
Split 更对
都差不多
都不对
```

禁止要求用户判断 MIDI / Hz / cents / octave。

Decision semantics：

```text
Split 更对
→ human_confirmed_machine_split
→ 当前歌曲可进入 structure corrected score

Baseline 更对
→ machine_structure_false_positive
→ keep Candidate 0
→ 记录 false-positive evidence

都差不多
→ no demonstrated benefit
→ keep Candidate 0（最小修改原则）

都不对
→ unresolved / manual_followup_required
→ no repair
```

#### Calibration output / acceptance

必须记录：

```text
total_machine_split_candidates = 21
reviewed_count
split_preferred_count
baseline_preferred_count
equivalent_count
none_correct_count
measured_song_level_precision
per-item evidence / patch / phrase package hash / decision
```

对《年轮》当前 written score：

```text
只有 human-confirmed machine splits + 已合法 human-selected structure
可以进入 trusted corrected score。
```

若出现任一 Baseline preferred / none_correct：

```text
不得宣称 frozen C gate 已具备 universal auto-repair precision；
先分析 false-positive pattern，再决定是否新增独立结构证据
（例如 onset / spectral flux / articulation boundary）或收紧 gate。
```

更广泛的跨歌曲 fully automatic structure repair，需要额外独立校准集；
本轮 21 个样本只能完成《年轮》的 song-level acceptance，不能证明 universal precision。

---


### 10.1.5A Blocker G — Human Review Readiness Gate ← CURRENT

当前发现证明：

```text
render successfully
+ verify_package == valid
+ blind A/B UI works
!=
audio is good enough for human adjudication
```

`m25-cal-1` 的 21 个归档包不得继续用于人工裁决或 repair authority。

已确认的 review-render 风险：

```text
1. Baseline 不是 canonical GAME render；
   Candidate-0 notes 被重新截取并重建成短句 USTX。

2. lyric_map() 通过 note midpoint ±0.30s 重新猜歌词，
   已在真实归档 Baseline 中出现：
   - 重复字
   - 漏字 / 错位
   - '+' 位置异常
   - neutral 'a' fallback

3. review USTX 会重新量化/重建：
   - tone → integer MIDI
   - PITD = none
   - 默认 pitch points / no original transition detail
   因而可能丢失正常 GAME/OpenUtau baseline 的转折、滑音、intonation。

4. 当任务本身是在判断 one-note vs split / portamento 时，
   一个被 review renderer 自己唱坏的 Baseline 会系统性污染人工判断。
```

因此从现在起，人工审核必须有独立的 **Review Readiness** acceptance。

#### G1. `m25-cal-1` authority 作废

```text
m25-cal-1 packages
+ m25-cal-1 decisions
→ historical / audit-only
→ NOT repair-authorizing
→ NOT silently migrated
→ NOT reused by m25-cal-2
```

如果已有 decision：

```text
do not reinterpret
do not backfill new hashes
do not preserve authorization
```

新系统至少：

```text
CALIB_SCHEMA = m25-cal-2
```

且 `calibration_authorized()` 必须 fail-closed 拒绝旧 schema。

#### G2. Canonical Baseline Contract

Baseline 不得由 calibration layer 重新“理解歌曲”。

首选 contract：

```text
canonical GAME/OpenUtau baseline project
→ exact clone
→ Baseline = target 0 修改
→ Candidate = clone 后只修改 target operation
```

除 target operation 外，以下必须 semantic-identical：

```text
note start/end
note tone
lyrics / melisma '+'
phoneme / phoneme overrides
PITD / pitch curves / transition settings
vibrato
expressions / voice color
tempo / timing mapping
singer / renderer / render settings
```

Calibration renderer 禁止：

```text
重新用 midpoint 猜歌词
重新生成与 canonical baseline 不同的歌词序列
把已有 pitch detail 清零
为方便短句 render 而改变非 target note semantics
```

如果当前阶段还没有可信的 canonical lyric+performance project，
则不得伪造“真实歌词 Baseline”。可退化为 **neutral-vowel diagnostic render**：

```text
first articulated note: a
touching continuation: +
real gap / re-articulation: a
```

用于只判断 pitch/timing/one-note-vs-split；同时保留 source focus clip 作为真实旋律参考。

#### G3. Baseline Equivalence Acceptance

在任何人听 A/B 前，必须先证明 calibration Baseline 本身足够接近正常 GAME baseline。

至少检查：

```text
score semantic diff outside target == empty
lyrics semantic diff outside target == empty
pitch/PITD semantic diff outside target == empty
renderer/profile diff == empty
non-target note count/order/timing/tone unchanged
```

若存在 canonical rendered baseline WAV，再做 audio-level reference check：

```text
same aligned phrase
→ loudness-normalized / time-aligned comparison
→ no gross pitch / timing / pronunciation divergence
```

如果 Baseline 单独听起来已经明显差于正常 GAME 输出：

```text
REVIEW_READY = false
→ no human adjudication
```

#### G4. Git Small-Sample Pre-Human QC

禁止一上来重新生成 21 组让用户试错。

每次 review-render contract 有 material change：

```text
先只生成 3–5 个代表性 sample
```

样本至少覆盖：

```text
simple split
large pitch-change split
lyric/melisma-sensitive case
gap / re-articulation-sensitive case
一个此前人工听感明显失败的 regression case
```

这些小样必须上传 Git，且每个 sample 至少包含：

```text
SOURCE_FOCUS_original_mix.wav
SOURCE_FOCUS_separated_vocal.wav
CANONICAL_BASELINE.wav              # 若存在
BASELINE.wav
CANDIDATE.wav
BASELINE.ustx
CANDIDATE.ustx
manifest.json
semantic_diff.json
```

Git artifact 必须可版本化、可复查，不能只存在本机 `runs/` 临时目录。

**Hard rule — Git is the acceptance source of truth：**

```text
local file exists
Agent says generated
Agent says audited/PASS
console output says success
!= acceptance evidence

only files actually committed to Git
and directly readable/reviewable from the acceptance SHA
count as Review Readiness evidence
```

因此：

```text
5 representative samples means 5 sample directories are present in Git
QC PASS means qc/verdict.json + qc/audit.jsonl are present in Git
full-batch claim means current m25-cal-2 plan.json/state.json are present in Git
missing Git artifact => corresponding checkbox MUST remain unchecked
```

禁止用 docs/commit message 对缺失 artifact 作替代证明。

#### G5. ChatGPT / maintainer pre-human audit

在用户听之前，先对 Git 小样做 pre-human QC。

审核内容至少包括：

```text
A. USTX / manifest
   - lyric sequence 是否合理
   - '+' / gap / re-articulation semantics
   - target 之外是否真的 identical
   - tone / timing / PITD 是否被意外重建

B. audio / signal
   - duration / silence / truncation
   - obvious pitch discontinuity
   - gross F0/timing mismatch vs source/canonical baseline
   - Baseline/Candidate 是否只在 target 附近产生差异

C. authority
   - package schema/hash/provenance
   - old m25-cal-1 decision 不能授权
```

只有 pre-human reviewer 明确给出：

```text
REVIEW_READY = PASS
```

才允许：

```text
生成完整 21-item batch
→ 用户人工 A/B
```

如果预审失败：

```text
先修 renderer / alignment / baseline contract
→ 重新生成小样
→ 重新上传 Git
→ 重新预审
```

不得把用户当 renderer QA。

#### G5A. Rendered target-focus contract

DiffSinger 可因 target note 改动而重新预测整段 phrase，导致：

```text
score diff = target-only
but
audio diff = phrase-wide
```

因此 full-phrase A/B 不能再作为主要人工判断对象。

每项必须在 **先完整 phrase render** 后，再从实际 rendered WAV 裁取：

```text
BASELINE_TARGET.wav
CANDIDATE_TARGET.wav
```

推荐窗口：

```text
declared target region ± 0.4–0.6s
```

不得为了 target-focus 单独重新调用 DiffSinger 渲染短窗；必须：

```text
full phrase render
→ crop exact same target window
```

人工 UI 主顺序：

```text
1. SOURCE_FOCUS_original_mix.wav
2. SOURCE_FOCUS_separated_vocal.wav
3. BASELINE_TARGET.wav
4. CANDIDATE_TARGET.wav
5. BASELINE full phrase       # secondary aid
6. CANDIDATE full phrase      # secondary aid
```

#### G5B. Mandatory signal_qc.json

每个 Git sample 必须额外提交：

```text
signal_qc.json
```

至少记录：

```text
sample_rate / duration
baseline_rms / candidate_rms
baseline_peak / candidate_peak
silence_fraction
target_window
pre_target_ab_diff_rms_ratio
target_ab_diff_rms_ratio
post_target_ab_diff_rms_ratio
source_target_f0_summary
baseline_target_f0_summary
candidate_target_f0_summary
target_focus_sha256
```

如果 target 外 A/B 声学差异过大、两 option 整体 loudness/timing 明显漂移，或 target F0 与 source 均严重不符：

```text
REVIEW_READY = false
```

必须先定位 renderer/context 问题，不得直接让用户裁决。

#### G5C. Blocker H — operation-aware child F0 QC ← CURRENT

当前 `signal_qc()` 的 F0 summary 语义不满足 structure calibration。

现实现：

```text
declared target region ± 0.5s
→ crop target-focus
→ 对整个 focus clip 做 F0 summary
→ voiced frames 机械切成 first_half / second_half
```

这不是 split operation 的真实 child identity。

风险：

```text
target 前后上下文会进入 median
voiced-frame midpoint != split boundary
child duration 不对称时 first/second half 更不代表 child0/child1
→ 可能把真正 62→64 的 split 证据抹平成两个 option 都 mismatch
```

### Required operation-aware fields

对 split candidate，必须严格使用 patch 中：

```text
parent.start
boundary
parent.end
```

分别计算：

```text
source_child_0_f0
source_child_1_f0
baseline_child_0_f0
baseline_child_1_f0
candidate_child_0_f0
candidate_child_1_f0
```

每个 child summary 至少记录：

```text
span_abs
duration
voiced_frames / voiced_fraction
midi_median
robust spread / confidence
extractor provenance
```

不得用 target-focus 的 first/second-half 代替真实 child span。

### Source-distance metrics

必须进一步计算：

```text
baseline_child_error_semitones
candidate_child_error_semitones

baseline_structure_error
candidate_structure_error

candidate_improvement_vs_baseline
```

推荐 structure error 为两个 child 对 source child median 的 robust aggregate；
若 source/option 某 child evidence 不足，则该 child = unavailable/neutral，
不得用 0 或默认 MIDI 替代。

这些指标是 **review-readiness evidence**，不是自动决定最终 written score 的 truth。

### Permanent Git-audit regressions

ChatGPT/maintainer 已从 Git WAV 独立按真实 child span复算：

```text
note_0012:
  Source     ≈ 62.02 → 64.10
  Baseline   ≈ 63.97 → 63.97
  Candidate  ≈ 62.02 → 63.97

note_0061:
  Source     ≈ 61.90 → 63.97
  Baseline   ≈ 63.97 → 63.97
  Candidate  ≈ 62.02 → 63.97

note_0123:
  Source     ≈ 62.14 → 64.10
  Baseline   ≈ 63.97 → 63.97
  Candidate  ≈ 62.02 → 63.97
```

新 `signal_qc` 必须能够表达上述方向；若重新生成后仍把这些样本标成
`both_options_target_f0_mismatch`，则 QC 定义仍有 bug。

`note_0391` / `note_0404` 等高音/极短 child 可出现 octave-folding / extractor
不稳定，因此不能要求所有 sample 都由单一 F0 extractor 自动判优；
此时必须保留 unavailable/ambiguous 并交人工，不得强行归一。

### Required regressions

```text
H1. asymmetric child durations → child windows follow patch boundary, not 50/50
H2. context ±0.5s pitch changes → cannot contaminate child medians
H3. note_0012 fixture → Candidate child structure closer to source than Baseline
H4. note_0061 fixture → same direction
H5. note_0123 fixture → same direction
H6. insufficient voiced frames in one child → unavailable/neutral, no fake mismatch
H7. octave-ambiguous child → flag ambiguous, no forced candidate/baseline winner
H8. regenerated signal_qc hashes committed to Git before maintainer review
```

#### 实现记录（2026-09-19，HEAD `2056ac2`）

`child_f0_qc(man, idir)`（`structure_calibration.py`）：child spans 直接取自
declared `score_patch` —— split → `[parent.start, boundary]`/`[boundary, parent.end]`；
merge → `[merged.start, merged.end]`；其他 op → `unavailable` 中性。每个 child 对
SOURCE vocal / BASELINE_TARGET / CANDIDATE_TARGET 三条 surface 独立做
`_f0_segment_summary`（FCPE median-midi、iqr、dominant_fraction、voiced_frames/
fraction、evidence=ok/ambiguous/unavailable + provenance）。

- 派生指标：`{baseline,candidate}_error_semitones`（vs source median）、
  `{baseline,candidate}_child_error_semitones[]`、`structure_error`=worst-child |err|
  （两 child 时 median 退化为均值会把单边严重偏差减半，故取 max）、
  `candidate_improvement_vs_baseline` = base_err − cand_err（正=candidate 更准）、
  `unavailable_child_slots`、`ambiguous_children`。
- 安全语义：source/child voiced 不足 → `unavailable`+`None`，不伪造 MIDI；
  iqr>3st 或 dominant<0.6 → `ambiguous`，不参与 error 聚合，不强制 winner；
  全部 child 不可用 → `f0_structure_evidence_insufficient` flag。
- auto flag 换成 child-level 语义：`f0_unavailable_slots`、
  `f0_octave_ambiguous`、`f0_candidate_structure_improvement:Xst`（信息性，
  review-readiness evidence 而非裁决）。
- 真实 21 项重算：全部 child 在三条 surface 均 voiced，无 unavailable/ambiguous；
  note_0012/0061/0123 复现 maintainer 方向（+1.92/+1.97/+1.53 st candidate 更优）；
  旧的 `both_options_target_f0_mismatch` 误导标志全部消失。
- 回归 H1/H3/H6/H7 + CORE 盲映射已入 `test_structure_repair.py`（300 passed，
  code `7929773`，artifacts `2056ac2`）。H8 由 git_evidence=361/361 满足。

---

#### G5D. Optional TARGET_CORE listening surface

现有 `BASELINE_TARGET.wav / CANDIDATE_TARGET.wav`（target ±0.5s）继续保留。

推荐额外从同一 full-phrase render 裁：

```text
BASELINE_CORE.wav
CANDIDATE_CORE.wav
SOURCE_CORE_original_mix.wav
SOURCE_CORE_separated_vocal.wav
```

窗口建议：

```text
declared target ± 0.1–0.2s
```

目的：让 100–300ms 的 child transition 不被 1–3s neutral-vowel context 淹没。

仍然必须：

```text
full phrase render → crop
```

禁止 short-window re-render。

建议 UI 优先级：

```text
SOURCE CORE
→ blind A/B CORE
→ ±0.5s target-focus
→ full phrase secondary aid
```

已实现（`7929773`/`2056ac2`）：`TARGET_CORE_PAD_S=0.15`，四个 CORE 文件从
同一 full render / SOURCE_FOCUS 裁剪，已入 `GIT_REQUIRED_ITEM_FILES`
（17 文件/item）；Web UI 顺序 = SOURCE CORE → blind `CORE_0/1` →
`TARGET_0/1` ±0.5s → full phrase 辅助，`SOURCE_CORE_{mix,vocal}.wav` 与
`CORE_i` 均走 manifest-aware 盲映射端点。

#### G5E. Remote human review via downloadable Git audio ← QUALITY HOLD

用户当前接受直接下载 Git 音频试听，因此 **native ChatGPT inline audio attachment 不再是 acceptance blocker**。

允许的远程审核 transport：

```text
ChatGPT message
→ GitHub raw/blob/download link
→ user opens/downloads on phone
→ listens
→ replies A / B / 都差不多 / 都不对
```

transport 只负责试听，不改变 canonical review authority。

### Primary review unit = 完整一句

人工主判断对象必须是一条自然完整唱句，而不是 CORE 或 target-only 短片段。

每组固定为：

```text
Group N — note_xxxx / cal_item_id

原唱完整一句
  SOURCE_PHRASE_original_mix.wav
  （必要时：SOURCE_PHRASE_separated_vocal.wav）

生成 A 完整一句
  exact blinded OPTION_A full-phrase wav

生成 B 完整一句
  exact blinded OPTION_B full-phrase wav
```

phrase window 必须满足：

```text
1. 覆盖 declared target
2. 左右保留足够上下文以听清旋律走向
3. 尽量从自然 phrase / 歌词语义边界开始与结束
4. 优先在停顿、换气、句尾或明显 articulation boundary 截断
5. A/B/source 使用同一时间语义窗口
```

目标长度：

```text
通常 4–10s
必要时允许 3–12s
```

禁止把以下作为主审核素材：

```text
target ±0.15s CORE
target ±0.5s focus
只有单个字/单个音的 0.5–2s 片段
```

这些短片段只允许作为 secondary diagnostic aid。

### Why full phrase is primary

结构判断需要上下文才能区分：

```text
written-note split
portamento
ornament
syllable continuation
phrase-direction / melodic contour
```

过短片段即使 F0 正确，也可能让人听不出“这一句本来应该怎么唱”。

### A/B blindness

对用户只显示：

```text
原唱
A
B
```

禁止显示：

```text
baseline
candidate
split
machine winner
F0-preferred option
```

下载文件名若泄露角色，ChatGPT 展示层必须使用中性 A/B 标签，不得在正文暴露真实身份。

### Pilot-first

先审核 5 个代表项：

```text
note_0012
note_0061
note_0123
note_0391
note_0404
```

用户每组只需反馈：

```text
A
B
都差不多
都不对
无法判断：<原因>
```

若任一 pilot 的完整一句仍然：

```text
明显唱坏
歌词/节奏/旋律语义异常
或仍然短到无法判断
```

则停止剩余审核并返回 renderer/QC。

### Pilot outcome — first real human check

当前真实人工反馈：

```text
Group 1 / note_0012: B 相对更好，但响度有问题、歌词有问题
Group 2 / note_0061: B 相对更好，但响度有问题、歌词有问题
Group 3–5: NOT REVIEWED — stop due pilot quality failure
```

处理规则：

```text
B preference = diagnostic only
NOT official decision
NOT repair authority
NOT machine precision evidence
```

原因：review audio 本身仍存在非 target 质量缺陷，继续强迫选择会污染 calibration。

### Current repair scope for review audio

#### Root cause confirmed from Git artifacts

Group 1 / Group 2 的 `OPTION_0.ustx` / `OPTION_1.ustx` 实际歌词为：

```text
a + + + + ...
```

即仍使用 G5B/G5C 阶段的 neutral-vowel diagnostic contract。

这对短 target 的 pitch/structure 隔离诊断是合理的，但 **不适合作为完整一句的人类主审核素材**：用户需要真实歌词语义与自然 phrase context 才能判断 written-note split / melisma / portamento。

因此：

```text
neutral-vowel full phrase
!= human-review-ready full phrase
```

#### Review-only real-lyric overlay

仓库已有 source-bound 资源：

```text
data/lyrics/nianlun_studio.lrc
src/agent2utau/analysis/lyrics.py::force_align()
```

下一轮不得回到旧的 midpoint lyric remap。

必须采用：

```text
source-bound studio LRC
→ extract exact phrase text
→ force_align() on the bound recording / separated vocal
→ char-level monotonic timing
→ monotonic note↔char assignment
→ render-only lyric overlay
```

映射 contract：

```text
1. 每个真实汉字只在该 syllable 的第一个 note 上出现；
2. 同一字的后续 melisma note 使用 `+`；
3. split candidate 若把 parent 拆成 children：
   parent 原 lyric 只给 first child，subsequent child = `+`；
4. A/B 除 target operation 外的 lyric sequence 必须完全一致；
5. 不允许 midpoint-nearest-char fallback；
6. force-align evidence 不足 / 非单调 / 低置信时 fail-closed，
   不生成可用于人工审核的 package。
```

该 overlay 只服务 M2.5 human structure calibration：

```text
review-only
not trusted final lyric mapping
not M2.7 completion
not repair authority by itself
```

#### Loudness contract

用户对 Group 1/2 均报告响度问题，因此 human-review render 必须显式控制试听响度。

A/B：

```text
same render profile
same phrase window
same post-render gain
NO independent per-option normalization
```

允许计算一个 **pair-shared listening gain**：

```text
A/B render
→ measure both
→ derive ONE common gain for the pair
→ apply same gain to A and B
```

这样不会因为响度归一化本身把某个 option 美化得更多。

原唱 reference：

```text
canonical SOURCE wav bytes remain unchanged
presentation layer may expose a gain-matched listening copy
but canonical source hash/authority stays bound to original bytes
```

建议记录：

```text
integrated loudness or robust RMS
peak / clipping
A/B loudness delta
shared_gain_db
source_listening_gain_db
```

acceptance：

```text
- A/B perceptual loudness no longer materially biases preference
- no clipping after shared gain
- source and generated audio are comfortable to compare on phone
- canonical hashes remain traceable
```

#### Required next pilot

只先重生成 Group 1 / Group 2：

```text
note_0012
note_0061
```

必须同时满足：

```text
- 完整一句真实歌词可辨认
- Group 1/2 不再出现 a/+ neutral-vowel sentence
- A/B outside-target lyric diff = empty
- A/B same shared gain
- package/hash/authority remains fail-closed
```

然后用户 **重新审核 Group 1/2**。

只有重新审核通过后才恢复 Group 3–5。

---
### Decision persistence

聊天反馈本身不是 repair authority。

必须：

```text
user choice
→ resolve exact blinded OPTION_i from manifest
→ verify current package/hash/schema
→ append official calibration decision revision
→ rebuild calibration state
```

禁止根据 F0/QC 自动替用户选择。

#### G5E 实现记录（`81b5511`，303 passed）

- **主素材已就位，无需重渲**：全部 21 项 phrase 窗口本来就是 LRC/silence
  自然唱句边界（实测 3.20–6.63s，全部 ∈[3,12]s），`SOURCE_PHRASE_*` +
  `OPTION_0/1.wav` 共享同一窗口——spec 的"完整一句"即现有 phrase 层。
- **`build_pilot_review()` → `pilot_review.json`**（已提交 Git）：5 个
  pilot 组（note_0012/0061/0123/0391/0404）每组绑定 cal_item_id +
  repair_id + audio_package_hash + phrase 时长；每个文件含
  `git_path` + canonical `sha256` + bytes + `raw_url`（由
  `git remote get-url origin` + `rev-parse HEAD` 推导，非硬编码）。
- **盲化保护**：`display_name` 全中性（`A.wav`/`B.wav`/`SOURCE.wav`）——
  canonical path 里的 `BASELINE_CORE.wav` 类文件名会泄露角色，展示层
  必须用 display_name 做链接文本；`blind_map` 固定 A→OPTION_0 /
  B→OPTION_1；`reply_map`：A/B→OPTION_i、都差不多→equivalent、
  都不对/无法判断→none_correct（均→unresolved，永不授权 repair）。
- **git_evidence 扩展**：`phrases/<key>/SOURCE_PHRASE_*.wav` 按 declared
  phrase_key 去重纳入 + `pilot_review.json` —— 主审核面与索引同属
  Git 证据（实测 394/394 complete）。
- **Web UI 重排**：原唱完整一句 → 盲选整句 A/B（主判断面）→
  CORE/focus/±0.6s 全部降为"辅助定位"。
- **CLI**：`structure-calib-pilot <run> [--notes]` 输出 JSON payload
  并写入 `pilot_review.json`；decision 仍走 `structure-calib-decide`
  （verify_package + append-only revision）。
- **回归 +3**：payload 盲化与绑定字段、缺失 note 显式报错、phrase
  文件纳入 git_evidence 去重。

#### G5E 质量暂停实现记录（`2371a03` + `21dcdf8`，309 passed）

用户实际试听 Group 1/2 后报告"歌词仍是 a/+ 中性元音、响度有问题"
→ 按 pilot-first fail-stop 修复 review audio 本身：

- **`review_lyrics()`（review-only overlay）**：force_align 字符
  （`nianlun_studio.lrc` ↔ source 绑定）逐字只落在其音节的首个
  note 上——carrier=首个未消费且 span 覆盖 char.start 的 note；
  相接延音 `+`、真实间隙后 `a`；绝不 midpoint-nearest、绝不回退
  猜测；字符证据超出 note 列表 → `None` → 调用方 fail-closed。
- **per-ITEM `real_lyric_review` 合同**：split 父 note 的字落在
  child[0]、其余 child 自动 `+`——A/B 目标外歌词序列逐位一致；
  `review_phrase_chars()` 证据门（无字符/任一 char 低于
  `MIN_REVIEW_CHAR_PROB` → fail-closed，不出包）。
- **共享响度 `_listen_copies()`**：A/B 同一 pair-shared gain
  （禁止独立归一化），canonical OPTION wav 字节不动；
  `OPTION_*_LISTEN.wav` + `SOURCE_PHRASE_*_LISTEN.wav` 为主试听面，
  canonical 文件保持 hash-bound 权威；`signal_qc` 记录
  `shared_gain_db`/`ab_loudness_delta_db`/`clipped`。
- **partial rebuild merge**：`build_calibration(only=…)` 合并进既有
  plan.json（不再丢其余 19 项）；每项记录实际 `lyric_contract` +
  `contract_sha256`；`semantic_diff` 报告 item 真实合同。
- **真实 run**：note_0012（`圆圈勾勒成指纹+印在我的+a嘴唇`）与
  note_0061（`寒夜剩我一个人++等清+晨++`）按 real_lyric_review
  重渲并 verify_package 通过；全 21 项 OPTION LISTEN + 全 16 phrase
  SOURCE LISTEN 生成入库；pilot payload 5 组全部解析到已提交
  LISTEN + canonical sha256。其余 3–5 组因 char 证据不足
  （no_chars/low_confidence）正确保持中性元音——不伪造歌词。
- **git_evidence 468/468 complete**；`review_ready` 仍为 False
  （无当前合同 QC verdict + 质量暂停未解除）；Group 1/2 的
  "B 更接近"仅作 diagnostic，未写入 decision authority。
- **回归 +8**：review_lyrics carrier/melisma/gap/fail-closed、
  A/B 目标外歌词一致性、证据门、pair-shared gain 不变量。


#### G5F Re-audit hard blockers（2026-09-18，必须先修再复审）

G5E 代码与产物提交后进行了独立 re-audit。结论：**当前 review package 仍不具备人工裁决资格，QUALITY HOLD 不解除。**

**Blocker 1 — pilot manifest 绑定 stale Git SHA，下载面实际失效**

当前 `pilot_review.json`：

```text
git.sha = 283f5a36255a2768a19b32b49e966cdd3021f0cc
```

但新的：

```text
OPTION_0_LISTEN.wav
OPTION_1_LISTEN.wav
SOURCE_PHRASE_*_LISTEN.wav
```

是在后续 artifact commit `21dcdf8323efdfe65291c1320e06bcf5abd7d1a6` 才进入 Git。按当前 manifest 中基于 `283f5a3` 生成的 raw URL 实测读取 `OPTION_0_LISTEN.wav` 返回 **404**。

Required fix：

```text
regenerate pilot_review.json
→ git.sha 必须绑定到实际包含全部 referenced LISTEN bytes 的 commit
→ 每个 raw_url 必须可下载
→ raw_url bytes sha256 == manifest sha256
→ canonical binding 继续保持可验证
```

禁止仅用 `git_evidence complete` 代替实际 URL/bytes 验证。

**Blocker 2 — real_lyric_review 仍允许可发声 neutral-vowel `a` 污染人工判断**

真实 Group 1 当前歌词序列：

```text
圆圈勾勒成指纹+印在我的+a嘴唇
```

原歌词为：

```text
圆圈勾勒成指纹 印在我的嘴唇
```

因此“真实歌词 review”仍可能实际唱出 `a`。对于 human-review asset，不能把 mapping gap 静默退化成可发声 neutral vowel。

Required fix：

```text
real_lyric_review path:
unmapped / ambiguous note
→ explicit continuation/slur semantics when evidence supports continuation
OR
→ fail-closed and do not package
```

不得：

```text
real_lyric_review
→ fallback to audible "a"
→ still mark package as valid for human review
```

修复后至少重新验证 Group 1/2：
- 实际 USTX lyric sequence；
- 实际 rendered audio；
- A/B target 外 lyric identity；
- package hash 与 Git bytes。

**Blocker 3 — A/B 非目标区 drift 仍然过大，结构盲选会被污染**

最新 `signal_qc.json`：

```text
Group 1 / note_0012:
  ab_loudness_delta_db = 0.03
  pre_target_ab_diff_rms_ratio = 2.1554
  post_target_ab_diff_rms_ratio = 1.1019
  auto_review_ready = false

Group 2 / note_0061:
  ab_loudness_delta_db = 0.90
  pre_target_ab_diff_rms_ratio = 1.5819
  auto_review_ready = false
```

共享 gain 已基本解决“独立归一化污染”问题，但 **A/B 在 target operation 之外仍产生明显差异**。人工任务是判断 split/baseline；若 phrase 前后也发生显著变化，则选择结果不能只归因于 target structure operation。

Required investigation：

```text
same phrase
+ same singer / renderer / render profile
+ same lyrics outside target
+ same note timing/pitch outside target
+ same PITD / expression / phoneme context outside target
→ only declared target operation may differ
```

必须定位 drift 来源，至少检查：
- split 是否改变后续 note/phoneme timing；
- lyric carrier/“+”分配是否导致 target 外 phonemizer context 改变；
- renderer 是否因 target note count 改变产生跨边界 coarticulation；
- USTX diff 是否超出 declared target；
- crop/alignment 是否把相同绝对时间映射成不同 rendered-relative 时间；
- shared loudness copy 前 canonical A/B 是否已经发生 target 外差异。

Acceptance：

```text
Group 1–2:
  package URL/bytes valid
  no audible placeholder vowel in real-lyric review
  target-outside semantic diff == none
  target-outside signal drift reduced to review-safe range
  auto_review_ready == true
  verify_package == PASS
  Git evidence == PASS
  fresh user re-review required
```

旧 Group 1=B / Group 2=B 继续仅保留 diagnostic preference，**不得**转成正式 calibration decision。

**Pilot 3–5 routing**

当前 Group 3–5 因 `no_chars / low_confidence` 仍使用 `neutral_vowel`。恢复 5-item pilot 前必须二选一：

```text
A. 修复/补强 source-bound lyric alignment，使其满足 real_lyric_review evidence gate；
B. 用其他具备可靠 real-lyric evidence 的 representative items 替换。
```

禁止在用户已明确指出歌词会干扰判断后，再把 neutral-vowel Group 3–5 作为正式结构审核样本。

**Human review unit clarification（2026-09-18）**

用户明确：不需要整首版本；**每个 review group 一整句完整歌词即可**。因此 human-review primary unit 继续保持“完整自然句 / full lyric line”，但必须满足：

```text
SOURCE = 原唱这一整句
A = 同一整句的 option A
B = 同一整句的 option B
```

要求：
- 必须从句首到句尾完整覆盖，不允许只给 target/core/focus 短片段；
- A/B 必须使用真实歌词，不能用 neutral-vowel `a` 作为正式试听；
- A/B 的句级上下文、歌词、时长基准一致，除 declared target operation 外不得有可感知非目标差异；
- target/core/focus 仅保留为定位辅助，不作为主判断面；
- 不要求生成整首 A/B 版本。


#### G5G Full-song human review（用户试听反馈：phrase 级仍无法可靠判断）

2026-09-18 用户继续试听 Group 3–5 的完整 phrase A/B 后明确反馈：**仍然听不出结构差异，需要完整版本。** 因此正式 human review 的 primary listening unit 从 `full_natural_phrase` 升级为 **full-song A/B render**。

新的人工审核原则：

```text
原唱整首 / 参考整首
→ A：整首渲染
→ B：整首渲染
→ 用户在完整上下文中判断哪一个整体旋律/衔接更接近原唱
```

phrase / focus / core 仍保留，但全部降级为 **localisation aids**，只用于在整首中定位目标位置，不再作为正式裁决的 primary surface。

**Required full-song render contract**

每一个待人工判断的 calibration item 必须生成：

```text
FULL_OPTION_0.wav
FULL_OPTION_1.wav
```

并满足：

- 两个完整版本必须来自同一个 full-song Candidate 0 / corrected-score 基底；
- A/B 唯一允许的 written-score 差异是该 item 的 declared target operation；
- target 外 note / lyric / timing / PITD / expression / renderer profile 必须完全一致；
- 同 singer、同 renderer、同 tempo、同 render profile；
- A/B 只能使用 pair-shared presentation gain，禁止独立 loudness normalization；
- canonical full-song wav 必须 hash-bound；试听 copy 与 canonical 必须有明确 provenance；
- full-song render 的 target 外 semantic diff 必须为空；
- 如果 renderer 的局部修改导致全局非目标音频变化，应记录为 renderer/global-context effect，不得伪装成 target-only evidence。

**Human review UI / Git package**

正式 pilot 每组至少提供：

```text
SOURCE_FULL.*       # 原唱/参考整首
A_FULL.*            # blind A full song
B_FULL.*            # blind B full song
SOURCE_PHRASE.*     # 定位辅助
A_PHRASE.*          # 定位辅助
B_PHRASE.*          # 定位辅助
```

用户默认只需要先听 `SOURCE_FULL → A_FULL → B_FULL`。只有需要定位差异时才查看 phrase/core/focus。

**Pilot-first cost control**

不得一次性为全部 21 项生成整首版本。先只为 representative pilot 生成 full-song A/B：

```text
先修复 G5F blockers
→ 选择 2 个可信 real-lyric pilot items
→ 生成 2×(A_FULL/B_FULL)
→ 用户确认“整首版本可以可靠判断”
→ 再扩到 5-item pilot
→ pilot 通过后才允许扩到剩余项目
```

如果两个完整版本在目标位置之外出现可感知差异，或 full-song render 仍存在歌词/响度/上下文污染：

```text
QUALITY HOLD
no formal human decision
```

旧的 Group 1–5 phrase-level A/B 试听结果全部只保留 diagnostic，不进入 calibration authority。


#### G5G Close-out before user confirmation（先修完再确认）

本节覆盖 G5F 之后的最终收尾要求。执行原则：**不要再把中间状态交给用户判断。先把实现、产物、状态快照、Git 绑定和验证全部修到一致，再请求一次最终确认。**

##### Blocker A — G1 旧 artifact 仍含可发声 `a`

当前 `note_0012` 的真实 USTX 仍包含：

```text
圆 圈 勾 勒 成 指 纹 + 印 在 我 的 + a 嘴 唇
```

这证明当前 G1 artifact 没有真正经过最新 `review_lyrics` fail-closed 语义。

Required action：

```text
rebuild note_0012 under CURRENT lyric implementation
→ if valid real-lyric mapping exists: render fresh A/B package
→ if any gap-separated unmapped note remains: fail-closed
→ then replace G1 with another representative item that passes the same lyric-evidence gate
```

禁止：

```text
保留 audible a
用旧 wav/ustx 冒充 current-contract artifact
仅修改 plan/pilot metadata 而不重渲真实 bytes
```

Acceptance：

```text
all pilot USTX:
  real lyrics + legal '+' continuation only
  no audible placeholder 'a'
  no guessed hanzi
  package regenerated from current code
```

##### Blocker B — render contract 必须感知 lyric implementation 变化

当前问题：`review_lyrics` 行为已经改变，但旧 artifact 仍可保留相同 `contract_sha256`，因此旧包不会自动 stale。

Required fix：render contract identity 至少绑定：

```text
schema
lyric_contract
lyric_mapping_impl_version (or equivalent semantic version/hash)
render_profile_hash
```

只要 review-lyrics 的 carrier / gap / continuation / fail-closed 语义发生变化：

```text
old contract_sha256 != new contract_sha256
→ old package stale
→ mandatory rebuild
```

需补 regression：旧 implementation 生成的 artifact 不得被新 implementation 当作 current-contract valid。

##### Blocker C — `plan.json` 必须从最新 authoritative artifacts 重建

当前已观察到 stale 状态，例如：

```text
G3 manifest.calibration.lyric_contract = real_lyric_review
但 plan.json 仍写 neutral_vowel

G3 manifest.audio_package_hash = current hash
但 plan.json 仍保留旧 hash

G1/G2 current signal_qc.auto_flags = []
但 plan.json 仍保留旧 drift flags
```

Required fix：不要继续依赖可能留下旧字段的局部 merge；在最终 close-out 阶段从 item manifests + current signal_qc **重建 authoritative plan snapshot**。

至少建立并自动验证以下 invariants：

```text
plan[i].audio_package_hash == manifest.audio_package_hash
plan[i].lyric_contract == manifest.calibration.lyric_contract
plan[i].contract_sha256 == manifest.calibration.contract_sha256
plan[i].package_state == manifest.package_state
plan[i].signal_qc_flags == signal_qc.auto_flags
```

任一 mismatch：

```text
review_ready = false
pilot payload generation = blocked
QC PASS = blocked
```

##### Blocker D — 最终 pilot payload 必须在最终 artifact commit 之后生成

完成所有 item rebuild / plan rebuild 后：

```text
commit final audio + ustx + manifests + qc + plan
→ regenerate pilot_review.json against THAT artifact commit
→ verify every SOURCE/A/B raw URL
→ verify downloaded bytes sha256
→ commit pilot payload
```

pilot 中 5 个 group 必须全部满足：

```text
real_lyric_review
complete natural lyric line
auto_review_ready == true
no audible placeholder vowel
LISTEN outside fade zone bit-identical
A/B shared-context review surface
valid canonical provenance
raw URL exists at bound sha
raw bytes sha256 == declared sha256
```

##### Blocker E — final self-check before asking user

在重新联系用户确认前，执行者必须自行完成并记录：

```text
pytest / CI = PASS
verify_package(all 5) = PASS
git_evidence = complete
plan ↔ manifest ↔ signal_qc invariants = PASS
pilot raw URL/bytes/hash verification = PASS
current-contract stale-artifact regression = PASS
review_ready prerequisites = satisfied except explicit maintainer/user authority steps
```

并再次人工/程序检查 5 个 USTX 的 lyric sequence，确保没有 `a` placeholder。

##### User interaction rule

在上述所有项完成前：

```text
DO NOT ask user to listen
DO NOT ask user to choose A/B
DO NOT ask user whether to continue
DO NOT request maintainer QC PASS
```

全部完成后，只进行一次最终确认：提供 5 组完整一句 SOURCE/A/B 给用户复审；该复审才可进入正式 calibration decision。


#### G5H QC authority contract binding（当前唯一 blocker）

G5G 已经完成真实歌词、rlv2 contract、plan authoritative rebuild、pilot Git binding 与 4-item honest pilot。当前无法继续不是 render / lyric / package 问题，而是 **QC verdict 仍绑定错误层级的 contract**。

##### 现状与死锁

当前 4 个正式 pilot：

```text
note_0061
note_0188
note_0192
note_0379
```

它们的 item manifest 均为：

```text
lyric_contract = real_lyric_review
lyric_mapping_impl = rlv2
contract_sha256 = 94077436a4f1acabb16e8696ca6f0e108183e3f44294da775fcaafd7666c508c
auto_review_ready = true
```

但 `plan.json` 顶层仍表示整个 store 的默认 neutral-vowel contract：

```text
lyric_contract = neutral_vowel
contract_sha256 = c54f07d644d7d5672748a19b32b49e966636fabe0dac6d32869dcb273ea652d105d
```

当前代码路径：

```text
cmd_structure_calib_qc()
→ rebuild_calibration_state()
→ state.contract_sha256 = plan.contract_sha256
→ write_verdict(... c54f07d6 ...)

review_ready()
→ verdict.contract_sha256 == plan.contract_sha256
```

因此 QC authority 错误地绑定 **store-level default contract**，而不是 **当前 human-review sample set 的 exact contract**。

旧 `qc/verdict.json` 虽为 PASS，但仍是旧 `c54f07...` + 旧 sample set，且不具备 current-contract authority；继续失效是正确行为。

##### Required fix — verdict 必须绑定 exact pilot authority

QC PASS 的 authority 必须从明确的 `sample_ids` / 当前 pilot payload 推导，而不是从 plan 顶层字段推导。

推荐 contract：

```text
sample_ids
→ load each current item manifest
→ require all samples share one contract_sha256
→ require all samples share expected lyric_contract / impl
→ verdict.contract_sha256 = that shared sample contract
```

当前 4-item pilot 应得到：

```text
verdict.contract_sha256 = 94077436...
```

而不是 `c54f07...`。

##### PASS hard gates

`write_verdict(PASS)` 至少必须逐 sample 验证：

```text
manifest exists
manifest.schema == current CALIB_SCHEMA
manifest.calibration.contract_sha256 == verdict.contract_sha256
manifest.calibration.lyric_contract == real_lyric_review
manifest.calibration.lyric_mapping_impl == current rlv2
item_contract_stale(manifest) == false
signal_qc.auto_review_ready == true
verify_package(item) == PASS
Git evidence complete
```

禁止：

```text
sample contracts mixed
sample contract != verdict contract
从 plan.top_level.contract_sha256 推导 verdict contract
仅凭 plan invariants PASS 就授权 human review
```

##### Pilot payload binding

QC verdict 还必须绑定当前 exact pilot payload，避免 sample roster 或 audio package 后续变化后旧 PASS 继续有效。

至少记录：

```text
pilot_sample_ids
pilot_contract_sha256
pilot_payload_sha256   # pilot_review.json canonical hash，或等价 identity
audio_package_hash per sample
```

`review_ready()` 必须重新验证：

```text
current pilot sample_ids == verdict sample_ids
current pilot payload hash == verdict pilot_payload_sha256
every current sample manifest contract == verdict contract
every sample audio_package_hash still matches verdict snapshot
plan_invariants == PASS
Git evidence including qc files == complete
```

任一 sample 被替换、重渲、contract bump、package hash 变化、pilot payload 变化：

```text
old verdict automatically stale
review_ready = false
```

##### CLI / state semantics

`structure-calib-qc` 必须明确针对一个 review sample set：

```text
structure-calib-qc <run>
  --pass
  --auditor <name>
  --samples <current pilot ids>
```

若 `--samples` 缺失，推荐直接 fail-closed；不得退回 plan 顶层 contract。

`rebuild_calibration_state()` 不应再把 `plan.contract_sha256` 当作 human-review authority contract。可以：

```text
store_contract_sha256 = plan.contract_sha256        # 仅描述 store/default
pilot_contract_sha256 = derived from current pilot # 人审 authority
review_ready = review_ready(current pilot identity)
```

两个概念必须分开。

##### Regression matrix

必须新增：

```text
H1. plan top-level = neutral nv1，samples = real-lyric rlv2
    → QC PASS binds rlv2 sample contract, not plan contract

H2. four samples all contract=94077436...
    → PASS may be recorded after all other gates pass

H3. one sample has a different contract
    → PASS hard refuse

H4. one sample stale under current lyric impl
    → PASS hard refuse

H5. one sample auto_review_ready=false
    → PASS hard refuse

H6. pilot roster changes after PASS
    → old verdict stale; review_ready=false

H7. one audio_package_hash changes after PASS
    → old verdict stale; review_ready=false

H8. pilot_review.json identity/hash changes after PASS
    → old verdict stale; review_ready=false

H9. old c54f07 neutral-vowel PASS over old 5 samples
    → cannot authorize current 4-item rlv2 pilot

H10. exact current 4-item rlv2 pilot + current PASS + committed QC files
    → review_ready=true
```

##### Pilot size rule

最终 pilot 固定为 **4 个 honest items**。不要为了历史上的“5-item pilot”要求补一个不满足 evidence gate 的样本。

```text
4 honest real-lyric items
>
5 items where one requires guessed lyric / invalid '+' / audible placeholder
```

pilot size 是 calibration coverage 参数，不是安全 contract。未来若出现新的合法 real-lyric item，可再扩展，但当前 close-out 不因此阻塞。

##### Final acceptance

只有以下全部满足后，G5H 才算关闭：

```text
QC authority derives from exact current pilot sample set
current 4 samples share one real-lyric rlv2 contract
verdict binds pilot payload + per-sample audio package identity
wrong/mixed/stale sample contract cannot PASS
old neutral-vowel verdict cannot authorize current pilot
current exact PASS committed to Git
review_ready == true
remote CI == success
```

然后流程才进入：

```text
maintainer QC PASS
→ 用户正式试听 4 组完整一句 SOURCE/A/B
→ structure-calib-decide 记录正式 calibration decisions
```

##### G5H 实现记录（2026-09-18，已关闭）

```text
pilot_authority(run_dir, sample_ids=None)
→ 默认解析 PILOT_NOTE_IDS → cal_item_id；逐样本硬门：
  manifest exists / schema==m25-cal-2 / 共享 contract_sha256+lyric_
  contract+impl==1 / lyric_contract==real_lyric_review /
  impl==当前 rlv2 / item_contract_stale==False /
  signal_qc.auto_review_ready==True / verify_package==PASS
  （_load_run/_verify_package 模块级间接，可测试）

write_verdict(PASS):
  --samples 缺失 → fail-closed（不退回 plan 顶层）
  contract_sha256 = 样本共享合同（显式传入且不符 → refuse）
  rec["pilot"] = {sample_ids, note_ids, contract_sha256,
                  lyric_contract, lyric_mapping_impl,
                  pilot_payload_sha256(pilot_review.json 文件 sha),
                  audio_package_hashes{cal_item_id: aph}}

review_ready(run_dir):
  verdict.PASS + git_evidence_at_record.complete + pilot 绑定齐全
  → 重验 payload sha == 绑定快照
  → pilot_authority(verdict 样本) 全过 + 合同/aph 快照一致
  → plan_invariants ok + git_evidence(include_qc) complete

git_evidence 字节级升级（_git_dirty_set）:
  tracked-but-dirty（M/staged/untracked）→ uncommitted → 不算
  committed evidence；修补了"旧 qc/verdict.json 路径已入库但字节
  未提交即计 complete"的漏洞

rebuild_calibration_state:
  store_contract_sha256 = plan 顶层（仅描述 store 默认）
  pilot_contract_sha256 = 当前 pilot 样本共享合同（人审 authority）
  两概念分离；review_ready = review_ready(current pilot identity)

build_calibration 全批门:
  review_ready AND 批次 contract == verdict 绑定合同
  （rlv2 verdict 不能授权 nv1 全批 —— 概念分离）

CLI: structure-calib-qc --pass 必须 --samples（cal_item_id 或
note_id）；缺失 → samples_required fail-closed
```

回归矩阵 H1–H10 全部落地 + dirty-bytes 测试：`test_g5h_*` ×5
（绑定样本合同/混合·stale·unready 拒 PASS/roster·aph·payload
变化自动 stale/旧 nv1 verdict 无 authority/精确当前 pilot
ready）。321 tests passed。

实机执行（run diag-20260917-181538-6aec）：

```text
structure-calib-qc ... --pass --auditor devin \
  --samples note_0061,note_0188,note_0192,note_0379
→ verdict.PASS  contract_sha256=94077436（rlv2，样本推导）
→ pilot.sample_ids = 4×cal-srp-*，payload_sha=eae594b1
→ git_evidence_at_record complete 143/143
→ 提交 b646a72（qc + 代码）+ 21cff60（state）
→ git_evidence 468/468 complete，uncommitted=[]
→ review_ready = True   （真实：字节已提交）
```

旧 `c54f07` verdict（无 pilot 绑定）自动失效 —— review_ready
不再消费 plan 顶层合同，死锁解除。Final acceptance 全满足。


#### G5I Lyric Timing Gate（当前 blocker：真实歌词时间必须先对齐）

G5H 解决了 QC authority / pilot contract 的错误绑定，但用户正式试听暴露出一个更基础的问题：**歌词文本正确 ≠ 歌词时间正确**。当前 human review package 的歌词落点与原唱存在明显偏移，导致 reviewer 无法可靠判断 split / baseline。

本节优先级高于继续 A/B calibration：在 timing gate 通过前，`review_ready=true` 只能解释为“artifact authority ready”，**不得解释为“human-audio perceptual review ready”**。

##### Root cause — 当前 `review_lyrics()` 没有保留 source char timing

当前逻辑：

```text
source force_align char.start
→ 找第一个 note.end > char.start 的未使用 note
→ 把 char 挂到这颗 note
→ OpenUtau / DiffSinger 从 note.start 开始唱这个 char
```

当前只使用 `char.start` 选择 carrier；没有要求：

```text
abs(note.start - char.start) <= tolerance
```

也没有用 `char.end` 约束字尾。因此如果原唱的某个字在一颗长 note 中间才开始，生成版会把该字提前到整颗 note 的起点。

这不是普通 lyric text mapping bug，而是缺少一层：

```text
source lyric articulation timing
```

##### Required architecture — written score 与 lyric articulation 分离

禁止为了匹配歌词时间直接修改 Candidate 0 的 written-score authority。

应引入 **render-only lyric articulation overlay**：

```text
Candidate 0 / A / B written score
+
source-bound lyric char timing
→ render-only note segmentation
→ OpenUtau render
```

规则：

```text
1. char onset 已接近某个 note boundary
   → 直接让该 char 从该 note 开始

2. char onset 落在一颗 note 内部
   → 在该 char onset 处做 render-only split
   → split 前后保持相同 written pitch
   → 前段继续上一 syllable / '+'
   → 后段开始新 char

3. 这些 articulation splits:
   → 不写回 Candidate 0
   → 不改变 machine structure hypothesis
   → 不算 M2.5 structure repair
   → 只服务于歌词发音时间与 human-review rendering
```

示意：

```text
written note:
60 |----------------------------|

source chars:
我 @ 0.00
演 @ 0.31

render-only articulation:
60 |------------|---------------|
   我 / +      演
   0.00         0.31
```

##### Source char timing evidence 必须持久化

当前 repo 的 manifests 只保存：

```text
n_chars
min_probability
```

不足以审计逐字时间。以后 source force-align 必须保存完整逐字表，例如：

```json
{
  "char": "演",
  "start": 93.42,
  "end": 93.71,
  "probability": 0.81,
  "method": "whisper-attention-dtw"
}
```

推荐存放：

```text
diagnostic/alignment/line_*.json
或
structure_calibration/lyric_timing/source_chars.json
```

并将 source audio sha256 / aligner model / aligner version / params 绑定到 provenance。

##### ASR / force-align comparison gate

对每个 review phrase，使用**同一套 aligner**分别处理：

```text
SOURCE separated vocal
A rendered vocal
B rendered vocal
```

在已知歌词约束下得到逐字 timing：

```text
char
source_start
source_end
A_start
A_end
B_start
B_end
confidence
```

并派生：

```text
A_onset_delta_ms = A_start - source_start
B_onset_delta_ms = B_start - source_start
A_offset_delta_ms = A_end - source_end
B_offset_delta_ms = B_end - source_end
A_duration_delta_ms
B_duration_delta_ms
```

输出必须可审计，例如：

```text
char  source   A       ΔA      B       ΔB
演    93.42    93.11   -310ms  93.10   -320ms
这    93.81    93.52   -290ms  93.52   -290ms
剧    94.35    94.42    +70ms  94.42    +70ms
```

##### Important measurement note

`force_align()` 当前基于 faster-whisper attention/DTW；多汉字 token 内部仍可能被均分，因此 timing 不是毫秒级 ground truth。

所以 gate 的原则是：

```text
SOURCE / A / B 必须用同一 aligner + 同一歌词 + 同一参数
→ 主要看相对 timing delta
→ 不把单个 ASR timestamp 当绝对真值
```

必要时后续可再加入第二独立 aligner，但第一版不需要扩大范围。

##### Timing acceptance

第一版先建立保守 gate，不允许为了过 gate 随意放宽。

至少要求：

```text
all review chars have valid aligned timing
no missing / reordered / duplicated lyric chars
no char is silently mapped to a note hundreds of ms early because of carrier fallback
A/B use the same source-bound lyric timing overlay outside declared target semantics
per-char onset delta is measured and persisted
phrase-level timing summary is persisted
```

建议输出统计：

```text
median_abs_onset_delta_ms
p90_abs_onset_delta_ms
max_abs_onset_delta_ms
median_abs_offset_delta_ms
n_chars_over_100ms
n_chars_over_200ms
```

具体 PASS threshold 先由真实 pilot measurement 决定，禁止在没有数据前拍脑袋写死。

##### A/B fairness under lyric articulation

Lyric Timing Gate 不是为了让 A/B 变成不同歌词时间。

要求：

```text
SOURCE char timing evidence = one canonical source
A articulation overlay = derived from same canonical source
B articulation overlay = derived from same canonical source
```

除非 declared structure operation 本身改变 target 内 note segmentation，否则：

```text
A/B lyric onset targets outside target region must be identical
```

即便 target 内 A/B note count 不同，汉字 onset anchor 仍应尽可能绑定同一个 source char onset。

##### Existing G5H verdict must stale for perceptual review

当前 `b646a72` G5H PASS 仍可保留为 artifact/QC 历史证据，但**不能继续授权用户结构判断**。

Lyric articulation / timing semantics 一旦加入：

```text
render contract must bump
old audio_package_hashes stale
old pilot payload stale
old QC PASS stale
review_ready = false
```

然后重新：

```text
source timing evidence
→ articulation overlay
→ A/B re-render
→ ASR timing QC
→ package/hash/pilot rebuild
→ new exact-pilot QC PASS
→ review_ready=true
→ 用户重新审核
```

##### Regression matrix

至少新增：

```text
I1. char.start 落在 note 中间
    → render-only articulation split at/near char.start
    → char must not start at original note.start

I2. two chars share one constant-pitch written note
    → render may split same pitch for articulation
    → Candidate 0 written score remains byte/semantic unchanged

I3. char onset already near note boundary
    → no unnecessary split

I4. A/B outside target use identical lyric timing anchors

I5. target split option changes note structure
    → lyric timing remains bound to the same source char onsets

I6. source/A/B aligned char sequence mismatch
    → timing QC fail-closed

I7. missing/low-confidence source char timing
    → no human-review package

I8. lyric articulation implementation/version changes
    → old render contract / package / verdict stale

I9. timing comparison artifacts missing
    → review_ready=false

I10. timing gate PASS + package/QC authority PASS
     → only then human review may resume
```

##### Final acceptance

G5I 只有全部满足才关闭：

```text
source char timing persisted with provenance
render-only lyric articulation implemented
Candidate 0 written score unchanged
A/B re-rendered under new contract
SOURCE/A/B same-aligner char timing comparison generated
timing QC metrics persisted
no material systematic lyric onset shift remains
new package/pilot/hash/Git evidence PASS
new exact-pilot QC PASS
review_ready=true under the NEW timing-aware contract
```

在此之前：

```text
DO NOT ask user to choose A/B
DO NOT record current listening result as calibration decision
DO NOT freeze M2.5
```

#### G5I 实现记录（2026-09-19，已关闭）

**实现**：`review_lyrics_articulated()`（`review/render.py`）——render-only overlay：char onset 落在 note 内部 → 同音高 split，前段 `+` 延音、后段载新字；边界 `ARTICULATE_SNAP_S=0.08` 内 snap 不 split；gap 后 `+` 不可渲染→fail-closed；首 carrier 前有实质内容/leading `+`/证据超界/序列非法→`None`→不产包。**Candidate-0 written score 完全不动**（`semantic_diff` 比对的是 score-level notes，overlay 只影响渲染层）。

**合同**：`real_lyric_review` impl bump `rlv2`→`rlv3`（articulation 改变 lyric timing 语义）→ 旧合同下所有 manifest/verdict/package 自动 stale。manifest `lyric_evidence` 持久化完整逐字表（char/start/end/probability，行级绝对时间）+ articulation 统计。

**timing QC**（`signal_qc.lyric_timing`，`_lyric_timing_qc()`）：对 SOURCE（绑定逐字表）与 OPTION_0/1 用**同一** `whisper-attention-dtw`/`large-v3-turbo` force_align + 同一文本逐字重对齐 → per-char onset/offset delta 表 + median/p90/max/>100ms/>200ms 统计；**score-bound 真值分解**：从 `OPTION_x.ustx`（120bpm/480tpq、无 preutterance）读 carrier note position → `score_delta`（渲染 vs 绑定证据，构造偏差）与 `aligner_offset`（aligner 测值 vs ustx 真 onset，纯 aligner 域偏差）分离——评审可直接看出 +200ms 级系统性 delta 属于测量偏差而非渲染提前。`lyric_timing_mismatch`/`unmeasurable`/`score_mismatch`/`score_unavailable` 全部 fail-closed。

**真实测量**（4 项 pilot）：`score_delta`≈0（interior char 全部精确唱在 aligned onset，snap 项记录 snap 距离）；`aligner_offset`≈-170~-270ms 系统性（aligner 对合成声报早 ~210ms）；朴素 onset_delta +200ms 由该偏差完全解释。**结论：渲染逐字时间 = source 绑定证据位置，构造达标；残差为证据自身噪声（±200ms），如实记录。**

**回归**：I1–I11（articulation 语义/snap/split/gap fail-closed/mismatch/stale/score 分解）+ 既有 H1–H10；330 passed。

**执行序列**（严格按绑定顺序）：代码 `a42c128` → rlv3 重渲 4 项 artifacts `1161b3e` → payload `70a6f96`（绑 artifact commit，raw URL 可解析）→ QC verdict `346cc1f`（绑 `767ee841`+payload sha `f6c0b68a`+4×aph）→ `review_ready=true`。invariants `ok`，authority 无 violations。

**Final acceptance 核对**：source char timing persisted ✅ / render-only articulation ✅ / written score unchanged ✅ / A/B re-rendered under new contract ✅ / same-aligner comparison generated ✅ / timing QC metrics persisted ✅ / no material systematic onset shift（系统性残差经 score-bound 分解证实为 aligner 域偏差，非渲染位移）✅ / package+pilot+hash+Git evidence PASS ✅ / new exact-pilot QC PASS ✅ / review_ready=true under rlv3 ✅。


#### G5J Acoustic Lyric Timing Closed-Loop（当前 blocker）

G5I/rlv3 解决的是：

```text
source char onset
→ render-only articulation boundary / USTX carrier onset
```

它没有证明：

```text
最终 DiffSinger 输出里该汉字的真实声学 onset / offset
≈
原唱该汉字的声学 onset / offset
```

因此 G5I 不能因为 `score_delta≈0` 就关闭。`score_delta` 是 construction integrity evidence，不是 perceptual timing truth。

##### Re-audit evidence — rendered acoustic timing 仍明显提前

当前 4 个 rlv3 pilot 的 same-aligner timing statistics：

```text
G1: median_abs_onset_delta ≈ 210–225ms, max ≈ 470ms
G2: median_abs_onset_delta ≈ 240ms,     max ≈ 480ms
G3: median_abs_onset_delta ≈ 220–240ms, max ≈ 480ms
G4: median_abs_onset_delta ≈ 210–250ms, max ≈ 330ms
```

代表例：G1 `等`：

```text
SOURCE force-align: 3.35–3.77s
render A:           2.90–3.50s  onset -450ms
render B:           2.88–3.50s  onset -470ms
```

这类偏差足以影响人耳对歌词、节奏和结构的判断。

##### Do not assume `aligner_offset` == aligner bias

rlv3 当前把：

```text
rendered force-align onset - USTX score onset
```

称为 `aligner_offset`，并把约 -210ms 的中位数解释为 synthetic-domain bias。

该解释目前没有独立实验支持。另一种同样合理的来源是：

```text
DiffSinger phoneme duration / consonant anticipation / preutterance
→ 实际声学发音早于 note position
```

而且偏差并非稳定常数，当前可见范围约 -170ms 至 -480ms。

因此：

```text
score_delta≈0  != acoustic timing PASS
aligner_offset != 已证明的 aligner-only bias
```

除非后续有独立 probe 证明固定偏置，否则不得用该解释绕过声学 timing gate。

##### Blocker A — SOURCE phrase 首字被截断

当前 4 组 source char table 的第一字相对 phrase start 约为：

```text
G1 -130ms
G2  -80ms
G3  -80ms
G4  -90ms
```

例如 G1：

```text
SOURCE `寒` start ≈ 37.65s
phrase clip start   ≈ 37.78s
```

即主 reference 已把首字前约 130ms 截掉。

Required fix：phrase window 不能只信 LRC 边界；对 real-lyric review 至少满足：

```text
phrase_start <= first_char.start - lead_pad
phrase_end   >= last_char.end  + tail_pad
```

lead/tail pad 应来自真实测量，第一版可保守留出 100–200ms，并保持不切 note / 不切 char。

重新生成 SOURCE canonical/listen clips 后，old package hash / pilot payload / QC verdict 必须 stale。

##### Blocker B — rendered ASR 低置信 timing 不得直接 PASS

当前一些 rendered char force-align confidence 很低，例如：

```text
G2 OPTION_0 min probability ≈ 0.058
G4 OPTION_1 min probability ≈ 0.107
G1 OPTION_0 min probability ≈ 0.177
```

这类 timestamp 不能同时被用于：

```text
证明 acoustic timing 已正确
或
证明 200–400ms 偏差只是 aligner bias
```

Required gate：

```text
per-char timing confidence below threshold
→ timing evidence = unavailable / low-confidence
→ no human-review package PASS
```

阈值不得为了让当前 pilot 过关而回调；先基于真实样本统计设定。

##### Required architecture — acoustic closed-loop

在保持 Candidate 0 written score 不变的前提下，建立：

```text
SOURCE force-align
→ initial render-only articulation anchors
→ DiffSinger render
→ force-align rendered vocal with SAME text/model/params
→ compute per-char acoustic onset error
→ adjust render-only articulation anchors
→ rerender
→ re-align
→ iterate until convergence or fail-closed
```

定义：

```text
acoustic_error_i = rendered_start_i - source_start_i
```

下一轮 anchor 更新可采用受限 feedback：

```text
anchor_i(next) = anchor_i(current) - k * acoustic_error_i
```

`k` 必须 < 1 或带 clamp / monotonic constraints，避免震荡、crossing 和非法 segment。

所有调整仅存在于：

```text
render-only lyric articulation layer
```

禁止写回：

```text
Candidate 0 written score
machine split/merge hypothesis
M2.5 repair authority
```

##### Closed-loop safety constraints

每轮至少保证：

```text
char anchors strictly monotonic
no anchor crosses the next char
no zero/negative-duration render segment
same-pitch articulation splits do not alter written-note pitch truth
A/B outside declared target share the same source timing authority
target structure option may change note segmentation but not lyric char identity/order
```

遇到：

```text
low-confidence alignment
missing/reordered char
non-convergence
required shift beyond safe clamp
illegal OpenUtau phoneme continuation
```

必须 fail-closed，不允许制造一个“看起来更接近”的假 timing。

##### Acoustic timing acceptance

最终 human-review timing gate 必须以 **SOURCE acoustic alignment vs rendered acoustic alignment** 为主判据。

`score_delta` 只保留为：

```text
construction_integrity_check
```

即证明 render-only anchor 被正确写入项目；不得替代以下指标：

```text
median_abs_acoustic_onset_delta_ms
p90_abs_acoustic_onset_delta_ms
max_abs_acoustic_onset_delta_ms
median_abs_acoustic_offset_delta_ms
n_chars_over_100ms
n_chars_over_200ms
min_alignment_probability
convergence_iterations
```

具体 PASS threshold 在完成真实 closed-loop pilot 后确定；不得用现有 200–480ms 偏差作为“正常基线”反推宽松阈值。

##### Optional bias probe — only if claiming aligner-domain bias

如果仍要主张 Whisper 对 synthetic vocal 存在固定提前偏差，必须独立验证，例如：

```text
construct synthetic probe with known acoustic syllable onset
or compare against a second independent aligner / manual landmark subset
```

只有独立 probe 支持后，才能把稳定 bias 作为校正项；否则一律把 measured acoustic delta 当未解释误差。

##### Blocker C — `state.json` / Git evidence self-pollution

当前最新 committed state 显示：

```text
git_evidence.complete = false
review_ready = false
```

但 plan 旧头部曾写 `review_ready=true`，两者不一致。

当前 Web `/api/state` 会调用 `rebuild_calibration_state()`，而该函数写回 `state.json`；同时 Git evidence 又规定 tracked-but-dirty 文件不算 committed evidence。

因此存在：

```text
GET /api/state
→ rewrite derived state.json
→ state.json becomes dirty
→ git_evidence.complete=false
→ review_ready=false
```

的自污染风险。

Required fix 二选一：

```text
Option A:
GET /api/state only computes state in memory
→ no filesystem write

Option B:
volatile derived state is explicitly separated from Git authority
→ committed acceptance snapshot uses a different immutable artifact
```

禁止为了让状态变绿而忽略 dirty evidence rule。

##### Regression matrix

至少新增：

```text
J1. SOURCE first char begins before LRC phrase boundary
    → review phrase expands; first char not truncated

J2. USTX score onset matches source but rendered acoustic onset is -300ms
    → timing gate FAIL; score_delta cannot mask it

J3. low-confidence rendered char alignment
    → timing evidence unavailable; no PASS

J4. closed-loop one iteration reduces acoustic error
    → anchor moves opposite error sign

J5. multi-iteration converges without changing Candidate 0 written score

J6. anchor update would cross next char / create invalid segment
    → fail-closed

J7. A/B outside-target lyric anchors remain identical

J8. articulation implementation / converged anchors change
    → contract + package + verdict stale

J9. GET /api/state does not dirty any Git-authoritative file

J10. only acoustic timing PASS + package/QC PASS
     → review_ready=true
```

##### Final acceptance

G5J 只有全部满足才允许恢复用户试听：

```text
SOURCE phrase no longer truncates first/last lyric articulation
source char timing persisted with provenance
render-only articulation closed-loop implemented
rendered vocals re-aligned after each render
low-confidence timing fails closed
acoustic timing errors converge to acceptable measured values
Candidate 0 written score unchanged
A/B outside-target lyric timing authority identical
new contract / package / pilot payload / verdict committed
Git evidence stable under Web/state reads
review_ready=true under the NEW acoustic-timing-aware contract
remote CI success
```

在此之前：

```text
DO NOT ask user to choose A/B
DO NOT treat current rlv3 timing as perceptually validated
DO NOT record calibration decisions
DO NOT freeze M2.5
```

#### G5J 实现记录（2026-09-19，机制完成；4 项 pilot 明确未收敛、已 fail-closed 挂起）

**仪器**：`onset_strength_peak_v1`——源分离人声与每个 OPTION wav 用**同一** onset-strength 包络峰值仪器测量，检测器偏差在差值中自然抵消。Whisper/force_align 保留为诊断列但**不再驱动更新、不作主门禁**：RMS 探针证实渲染在 anchor 前 ~50ms 内起音（whisper 把合成声边界系统性报早 ~200–500ms 到前一字尾音），whisper-vs-whisper 闭环会把 anchors 真实推晚 ~200ms——过校正已由声学测量证伪。

**闭环**（`_closed_loop_anchors`）：anchors 初始化为 source onset refs（clamp 到共享 carrier bounds）→ `render_item(anchors=...)` → 从 `OPTION_x.ustx` 读 carrier position 作搜索中心（含 snap 后真实命令位置，非裸 anchor）→ 非对称窗 `[cmd-0.15, cmd+0.22]` 找 onset 峰 → shared err = 可信 option 均值 → `anchor -= 0.7·err`（±150ms/iter clamp、hi_move 保留 ≥120ms 可唱段、严格单调）→ 最多 4 迭代。停止原因如实记录：`converged`/`bound_limited`/`unmeasurable_chars`/`anchors_crossed`/`anchors_clamped`/`max_iters`/`unbindable_chars`。

**渲染合法性修复**（本轮关键 bug）：anchor 落在 carrier 起点内 <80ms 会生成 8ms `+` 残段 → 音素 preutterance 放不下 → OpenUtau `OverlapError` → 2/4 包 invalid。修复：anchor 在 `ARTICULATE_SNAP_S` 内 snap 到 carrier 起点（与 evidence 路径同一规则）；`option_notes` 移入 `render_item` try 内 → 单 option fail-closed 不再杀死整个 build。

**测量稳定化**（多峰环境下 argmin 指派本质不稳，实测误差跨迭代 ±300ms 震荡）：①跨 option 一致性——同 anchor 同仪器两 option 测得 onset 差 >150ms → 至少一个误指派 → 该字 unmeasurable；②跨迭代抗跳变——测得 err 跳 >150ms 而 anchor 移动 <50ms → 探测器重锁到别的 landmark → unmeasurable，不驱动更新。QC 门禁同标准：delta gate 只读跨 option 一致的字，不一致标 `lyric_timing_acoustic_unstable:<chars>`。

**Pilot 结果（4 项）**：全部 `package_state=valid`（overlap bug 消除）；闭环均未收敛——`unmeasurable_chars`×2、`bound_limited`×1、`anchors_crossed`×1；声学 delta flag 139–255ms 集中在跨 option 一致的提前 onset（≈辅音先行，人声判断项）与 bound-pinned 结构限位字。`auto_review_ready=false` → `pilot_authority.ok=false` → `review_ready=false`——**如实未通过，项挂起等人工裁决**，不是假收敛。

**回归**：J1–J10 + 既有全套 340 passed；`plan_invariants.ok`；`git_evidence` 仅差未提交字节（提交后补验）。


#### G5K Hard-case timing semantics（当前 blocker：不是继续调参数）

G5J/rlv5 已证明 acoustic closed-loop 可工作，并且对大多数可测字符显著降低了实际声学时间误差；当前问题已经不再是“闭环没实现”，而是 **部分字符没有可靠声学 landmark，或原唱 onset 本身落在当前 written-note carrier 的合法可调范围之外**。

##### rlv5 pilot 实测状态

4-item pilot：

```text
G1 note_0061
  median acoustic error ≈ 52ms
  max ≈ 151–163ms
  stop = unmeasurable_chars

G2 note_0188
  median acoustic error ≈ 23ms
  max ≈ 163–197ms
  stop = bound_limited

G3 note_0192
  median acoustic error ≈ 35ms
  max ≈ 163ms
  stop = unmeasurable_chars

G4 note_0379
  median acoustic error ≈ 70–75ms
  max ≈ 139–151ms
  stop = anchors_crossed
```

共同状态：

```text
package_state = valid (4/4)
closed_loop implemented = true
closed_loop converged = false (4/4)
auto_review_ready = false (4/4)
pilot_authority.ok = false
review_ready = false
```

这说明当前剩余 blocker 是 hard-case semantics，而不是 package / Git / render plumbing。

##### Do NOT solve by parameter chasing

禁止把下一步简化为：

```text
increase LOOP_MAX_ITERS
increase LOOP_CLAMP_S
raise k
relax TIMING_GATE_MS
relax low-confidence threshold
```

除非有新的测量证据证明这些参数才是根因。当前真实结果已经显示：部分字即使继续迭代也会被 carrier bounds / landmark ambiguity 卡住。

##### Class A — measurable + carrier-feasible

定义：

```text
source acoustic landmark reliable
render acoustic landmark reliable
cross-option onset measurement stable
desired correction lies inside legal carrier timing bounds
anchor ordering / minimum sung span remain legal
```

这类字符继续走现有 rlv5 closed-loop。

acceptance：

```text
converged == true
acoustic error <= measured gate
no low-confidence / unstable / unmeasurable flags
```

##### Class B1 — acoustic landmark unmeasurable / unstable

连续中文唱腔不保证每个汉字都有独立、稳定的 onset-strength peak。

当前 `unmeasurable_chars` / `acoustic_unstable` 不能再被当成“再调一下就能找到峰”。

规则：

```text
no stable landmark
!= timing correct
!= timing wrong
== timing evidence unavailable
```

处理优先级：

```text
1. 尝试第二独立 acoustic landmark family（仅用于 adjudication，不和第一测量器重复计权）
2. 若仍不可测 → fail-closed
3. 可以替换 pilot sample，但不能伪造 PASS
```

允许探索的第二测量器示例：

```text
phoneme/consonant boundary detector
energy-envelope derivative
spectral-flux landmark
manual small-subset timestamp annotation for calibration
```

但必须保持：SOURCE 与 render 使用同一 measurement family。

##### Class B2 — source onset outside legal carrier bound

这是当前最重要的新语义问题。

例：G2 某些字符：

```text
source acoustic ref < carrier lower bound
or
source acoustic ref > carrier upper bound
```

这种情况下 closed-loop 不可能在不越权修改 written-note timing 的前提下精确对齐。

必须明确：

```text
lyric articulation overlay is NOT allowed to rewrite written-score timing truth
```

因此默认处理应为：

```text
carrier_bound_conflict
→ no forced convergence
→ no review-ready PASS
```

禁止为了让试听“听起来对”而让 render-only lyric anchor 任意越过 note carrier、吞掉相邻 note、或实质改变 written-score timing。

##### Carrier-bound conflict 的后续路由

B2 不能简单等同于 renderer bug。它可能说明：

```text
a) 当前 GAME/written note timing 本身与原唱 lyric articulation 不兼容
b) source acoustic landmark 对应的是辅音 anticipation，而不是 syllable carrier boundary
c) current note identity / split timing candidate 不足以表达原唱
```

因此要新增显式 route：

```text
carrier_bound_conflict
→ inspect whether this is
   - lyric-only anticipation
   - note timing error
   - structure/split timing error
   - measurement ambiguity
```

只有确定为 lyric-only anticipation 时，才允许定义一个受控的 renderer-side preutterance model；如果是 written timing / structure error，应回到对应 adjudication lane，而不是歌词层硬修。

##### Do not let review-only overlay mask transcription errors

这是 G5K 的核心安全原则：

```text
human review audio must reveal transcription quality
not cosmetically repair transcription timing until it sounds correct
```

因此 review-only lyric overlay 允许修：

```text
phoneme/articulation placement inside an already-valid carrier
```

不允许修：

```text
note start/end truth
wrong carrier identity
wrong split boundary
wrong inter-note gap
written-note duration error
```

否则会污染用户对 A/B 结构的判断。

##### Whisper confidence semantics split

rlv5 已将 Whisper demote 为 diagnostic，但当前 `signal_qc` 仍会用 generated Whisper probability 产生 blocking flags。

必须把两个概念拆开：

```text
acoustic_timing_confidence
  = timing measurement family 对 onset 的可测性/稳定性

lyric_intelligibility_confidence
  = ASR/force-align 对生成歌词是否清晰可辨的信心
```

规则：

```text
low ASR confidence may block human review because diction is unclear,
but it must NOT be described as proof that acoustic timing is wrong.
```

相反，timing instrument unmeasurable 也不能被解释成歌词一定听不清。

manifest / signal_qc 中应分开记录和 gate。

##### Pilot policy

当前 4 个 pilot 不要求“必须全部救活”。

允许：

```text
Class A item converges → keep
Class B1 persistently unmeasurable → replace with another honest sample
Class B2 carrier-bound conflict → route to written-timing/structure diagnosis; do not use as simple split A/B pilot
```

最终 pilot 目标仍是：

```text
enough honest, reviewable items to calibrate structure decisions
```

而不是强制保留历史上的 exact 4 notes。

##### Required diagnostics

对每个 char 持久化：

```text
char
source_ref_onset
source_ref_kind
render_onset per option
acoustic_error per option
measurement_stability
carrier_lo
carrier_hi
desired_anchor
final_anchor
bound_conflict = true/false
unmeasurable_reason
route = class_A | B1_unmeasurable | B2_carrier_conflict
```

这样 reviewer 可以区分“测不到”和“根本调不到”。

##### Regression matrix

至少新增：

```text
K1. reliable landmark + correction inside carrier
    → Class A; closed-loop may converge

K2. no stable onset landmark
    → B1; fail-closed or second-instrument adjudication

K3. source onset earlier than carrier lower bound
    → B2 carrier_bound_conflict; no anchor overreach

K4. source onset later than carrier upper bound
    → B2 carrier_bound_conflict; no anchor overreach

K5. relaxing k/clamp alone cannot convert B2 to PASS

K6. review overlay never changes Candidate 0 note start/end

K7. B2 routed to written-timing/structure diagnosis when appropriate

K8. low Whisper confidence only flags intelligibility, not acoustic timing truth

K9. acoustic measurement unmeasurable does not imply lyric unintelligible

K10. final pilot may replace B1/B2 samples without violating authority binding
```

##### Final acceptance

G5K 关闭条件：

```text
hard cases classified explicitly
Class A closed-loop behavior remains valid
B1 unmeasurable semantics fail-closed
B2 carrier-bound conflict semantics implemented
review overlay cannot mask written timing / structure errors
timing confidence and intelligibility confidence separated
pilot roster contains only honest reviewable samples
new package / pilot / QC authority rebuilt
review_ready=true only for that final honest pilot
remote CI success
```

在此之前：

```text
DO NOT ask user to listen
DO NOT loosen thresholds just to recover the existing 4-item pilot
DO NOT let lyric timing overlay rewrite written-score truth
DO NOT record calibration decisions
DO NOT freeze M2.5
```

##### G5K 实现记录（rlv6，2026-09-17）

实现：

```text
_classify_routes(): 闭环迭代前按不变量分类每个字 —
  class_A              可靠 onset_peak landmark + ref∈[lo, hi_move]
  B1_unmeasurable      ref 缺失 / whisper_fallback / none — 证据不可用
  B2_carrier_conflict  ref 越出合法 carrier anchor 范围
    route_detail: anticipation_candidate (gap ≤ 120ms)
                | written_timing_suspect (gap > 120ms)
闭环: hard-case anchor 保持不更新; converged 只评 Class A;
  reason += hard_cases_only / hard_cases; char_routes 持久化
  ref/kind/bounds/desired/final/route_detail/measurement_stability。
QC: per_char 行带 route 字段; flag += lyric_timing_carrier_conflict
  / lyric_timing_evidence_unmeasurable; acoustic delta gate 只评
  class_A; B1 字跑第二独立测量族 energy_edge_v1（adjudication 证据
  不重复计权）; Whisper 概率 flag 重命名 lyric_intelligibility_low
  （发音清晰度 ≠ timing 真值）; stats.min_intelligibility_probability。
impl bump rlv5 → rlv6; K1-K10 回归矩阵; 350 tests PASS。
```

真机核查发现并修复的 bug：

```text
_classify_routes 初版直接拿 phrase-relative refs 对比绝对时间的
carrier bounds → 全部 4 项整句误路由 B2（hard_cases_only）。
修复: off=ph0 参数桥接比较域；route dict 的 carrier_lo/hi 也
统一记录为 ref 域，与 src_start 一致。测试 fixture phrase.start=0
恰好掩盖——真机数据抓住。
```

4 项 rlv6 pilot 结果（全部 package_state=valid）：

```text
note_0061  unmeasurable_chars   conflict: 寒夜个等晨(5字)
note_0188  bound_limited        conflict: 可人陪这本(5字) delta 163ms
note_0192  bound_limited        conflict: 可人陪这本(5字) delta 244ms
note_0379  unmeasurable_chars   conflict: 可没人我(4字) delta 163ms
```

route_detail 分布：4 字 anticipation_candidate（辅音先行合法假设，
60–110ms 越界）+ 本(5.26s) written_timing_suspect（越界 129ms）。
同一句 90.03–96.96 的 0188/0192 冲突字完全一致（可人陪这本）——
该 lyric 区的 written carrier timing 与源唱 articulation 系统性
不兼容，已显式路由到 written-timing/structure 诊断，未被 overlay
掩盖。review_ready=false（诚实）。


#### G5L Directional carrier-conflict semantics + post-loop B1 adjudication（当前 blocker）

rlv6/G5K 已建立 hard-case routing 框架，但 re-audit 发现当前 B2 语义仍把**方向相反**的 timing conflict 混在一起，而且 B1 只在 loop 前按 SOURCE landmark 分类，未覆盖 render 端持续测不到的字符。

##### Blocker 1 — B2 必须区分 early-side 与 late-side conflict

当前 `_classify_routes()`：

```text
source ref outside [carrier_lo, carrier_hi]
→ gap = absolute overhang
→ gap <= 120ms ? anticipation_candidate : written_timing_suspect
```

这会把两个物理意义不同的情况合并：

```text
A. source onset < carrier_lo
   → source articulation 比 written carrier 更早
   → 可能是 consonant anticipation / preutterance

B. source onset > carrier_hi
   → source articulation 比 written carrier 可用范围更晚
   → 不是 anticipation
   → 可能是 post-boundary delay / carrier-too-short / written timing mismatch
```

真实例：

```text
G2 `可`:
source_ref = 0.2438
carrier_lo = 0.33
overhang = 86ms early
→ anticipation_candidate 合理

G2 `人`:
source_ref = 2.4845
carrier_hi = 2.37
overhang = 115ms late
→ 当前也写 anticipation_candidate，不合理

G1 `个`:
source_ref = 2.798
carrier_hi = 2.74
overhang = 58ms late
→ 也不能称 anticipation
```

Required route_detail：

```text
source_ref < carrier_lo
→ early_carrier_conflict
→ may classify further as preutterance_candidate

source_ref > carrier_hi
→ late_carrier_conflict
→ may classify further as post_boundary_delay_candidate
   or written_timing_suspect
```

禁止再用单个 `anticipation_candidate` 覆盖两个方向。

##### Blocker 2 — 120ms 不能直接作为最终语义 authority

当前：

```text
ANTICIPATION_MAX_S = 0.12

gap <= 120ms
→ anticipation_candidate

gap > 120ms
→ written_timing_suspect
```

这只是 heuristic，不足以单独证明声学语义。

真实边界例：

```text
G2 `人` overhang ≈ 115ms
G2 `本` overhang ≈ 129ms
```

只差约 14ms，却被分成完全不同的类别。

因此 120ms 只能作为：

```text
screening / triage prior
```

不能作为：

```text
final written_timing adjudication authority
```

最终判断至少应消费：

```text
direction (early vs late)
phoneme / consonant-vowel context if available
source/render acoustic landmark evidence
neighbor char/note timing
carrier duration / inter-note gap
whether the same conflict repeats across independent structure options
```

##### Repeated conflict is stronger than one-off conflict

90.03–96.96 这一句在两个不同 review target（G2/G3）上重复出现相同 B2 字集合：

```text
可 / 人 / 陪 / 这 / 本
```

这说明冲突不是某一个 split option 的偶发渲染问题，而是该句 SOURCE articulation 与当前 written-note carrier timing 存在系统性不兼容。

这种跨 target 重复冲突应记录：

```text
phrase_level_carrier_conflict = true
```

并优先路由到 written-timing / lyric-articulation adjudication，而不是继续在每个 review item 内重复闭环。

##### Blocker 3 — post-loop render-unmeasurable 必须正式降级 B1

当前 B1 主要由 loop 前 SOURCE landmark 缺失决定。

但真实 pilot 中存在：

```text
SOURCE landmark exists
→ initial route = class_A
→ render loop repeatedly yields:
   acoustic_unmeasurable
   acoustic_unstable
   cross-option disagreement
→ item not_converged
```

这类字符不能永远保留 `class_A`。

必须新增 post-loop adjudication：

```text
class_A
+ persistent render measurement failure
→ B1_render_unmeasurable
```

建议 B1 subtype：

```text
B1_source_unmeasurable
B1_render_unmeasurable
B1_cross_option_unstable
B1_detector_relock
```

语义统一为：

```text
timing evidence unavailable
!= timing correct
!= timing wrong
```

##### Second-family evidence semantics

rlv6 已加入 `energy_edge_v1` 作为第二 independent landmark family。

其用途必须限定为：

```text
adjudicate whether B1 may become measurable
```

禁止：

```text
primary + second family 直接平均成一个伪高置信 timing
```

如果两个 independent families 对同一字符提供一致方向/位置，可将：

```text
B1 → measurable_with_secondary_evidence
```

再进入后续闭环；若不一致，继续 fail-closed。

##### Directional B2 routing

推荐 route schema：

```text
route = B2_carrier_conflict
direction = early | late
overhang_ms = ...
route_detail =
  preutterance_candidate
  post_boundary_delay_candidate
  written_timing_suspect
  structure_timing_suspect
  measurement_ambiguous
```

其中：

```text
early conflict
→ 才允许考虑 preutterance_candidate

late conflict
→ 禁止标 preutterance/anticipation
→ 先考虑 post-boundary / carrier duration / written timing
```

##### Candidate-0 protection remains absolute

G5L 不改变 G5K 原则：

```text
review-only lyric overlay
MUST NOT rewrite
Candidate 0 note start/end
split boundary
inter-note gap
written-note duration
```

任何需要越出 carrier 才能“修好”的 case，都不能由 lyric layer 自己偷偷解决。

##### Pilot replacement policy

当前 4 个 pilot 只是历史样本，不是必须保留的固定 roster。

允许：

```text
Class A converged item → keep
B1 persistent unmeasurable → replace
B2 phrase-level/systematic conflict → route away and replace
```

新的 pilot 应优先选择：

```text
lyric timing measurable
no phrase-level carrier conflict
no unresolved intelligibility blocker
target structure remains representative
```

##### Required diagnostics

每个 char 至少记录：

```text
route
route_subtype
direction
overhang_ms
source_ref_onset
carrier_lo
carrier_hi
primary_measurement
secondary_measurement
render_measurement_status
final_class
phrase_level_conflict_id if any
```

##### Regression matrix

至少新增：

```text
L1. source_ref < carrier_lo by 80ms
    → B2 early conflict
    → may be preutterance_candidate

L2. source_ref > carrier_hi by 80ms
    → B2 late conflict
    → MUST NOT be anticipation/preutterance

L3. 115ms vs 129ms conflict
    → threshold alone cannot decide semantic truth

L4. identical B2 char set repeats across two review targets
    → phrase_level_carrier_conflict

L5. initial class_A but render onset missing repeatedly
    → post-loop B1_render_unmeasurable

L6. initial class_A but cross-option detector disagrees persistently
    → B1_cross_option_unstable

L7. second family confirms a B1 landmark independently
    → may re-enter measurable path

L8. second family disagrees
    → remain fail-closed

L9. no route may alter Candidate 0 written timing

L10. final pilot roster excludes unresolved B1/B2 cases
```

##### Final acceptance

G5L 关闭条件：

```text
B2 direction persisted explicitly
early/late semantics no longer conflated
120ms heuristic demoted to triage only
post-loop render failures become explicit B1 subtypes
second-family evidence used only as independent adjudication
phrase-level repeated conflicts detected
Candidate 0 written timing remains immutable
final pilot contains only reviewable items
new package/pilot/QC authority rebuilt
review_ready=true only for that honest roster
remote CI success
```

在此之前：

```text
DO NOT ask user to listen
DO NOT use 120ms threshold as final written-timing truth
DO NOT call late-side conflict 'anticipation'
DO NOT leave persistent render-unmeasurable chars as class_A
DO NOT record calibration decisions
DO NOT freeze M2.5
```

---

#### G6. Human-review readiness regressions

至少新增：

```text
G1. old m25-cal-1 package/decision cannot authorize m25-cal-2 repair
G2. Baseline semantic diff outside target must be empty
G3. Candidate semantic diff is confined to declared target operation
G4. repeated lyric char / melisma / re-articulation cases preserve canonical semantics
G5. canonical PITD / transition data is preserved outside target
G6. missing canonical lyric mapping cannot silently fall back to guessed real lyrics
G7. neutral-vowel fallback uses deterministic a/+ semantics
G8. sample package contains all required Git-review artifacts
G9. review-ready flag defaults false and cannot be set by render success alone
G10. full 21-item generation is blocked until pre-human QC PASS
```

#### G 实现记录（`1ac4133`，remote CI `35310205157`，289 passed / 0 failed）

- **G1 m25-cal-1 作废**：`CALIB_SCHEMA="m25-cal-2"`；`ensure_calib_authority()` 在任何入口先把非 m25-cal-2 的 `structure_calibration/` 整体改名 → `structure_calibration_m25cal1_audit[_ts]/`（idempotent，不覆盖）；`decide()`/`calibration_authorized()` 对旧 schema manifest fail-closed。真实 run 已 `git mv` 归档，Git 中保留 audit。
- **G2 neutral-vowel contract**：item `lyric_contract="neutral_vowel"` → `option_notes` 走 `neutral_vowels()`（touch→`+` / gap|first→`a`），完全不读 char 表——lyric guessing 整类消除。
- **G3 semantic_diff.json**：每项独立文件，`outside_target.score_diff/lyric_diff` 必须为空；`within_target` 记录 before/after；`baseline_vs_c0` 验证 context==C0 slice；`tone_integerization.max_deviation_cents` 显式记录；manifest 绑 `semantic_diff_sha256`。
- **G4 小样**：`--items` 子集构建 = 合法 pre-QC 路径；每项含 OPTION_0/1.wav+ustx、BASELINE.ustx、CANDIDATE.ustx（QC 用去盲命名）、manifest.json、semantic_diff.json、SOURCE_FOCUS_original_mix/separated_vocal.wav。
- **G5 verdict**：`qc/verdict.json`（schema 绑定 + contract_sha256 绑定 + auditor + sample_ids）+ `qc/audit.jsonl` append-only；`structure-calib-qc --pass/--fail --auditor` 记录。
- **G9/G10 gate**：`review_ready()` 默认 false，仅 verdict PASS + contract 匹配才 true；`build_calibration` 无 `only` 且无 PASS → RuntimeError 拒绝全批次。
- **回归**：G1–G10 共 8 个测试在 `tests/test_structure_repair.py`（archive/legacy-refuse/diff-empty/diff-detect/neutral-a+/PITD-uniform/no-lyric-fallback/ready-default-false/full-batch-gate）。
- **本地 run 自报记录（NOT ACCEPTANCE）**：Devin 报告 5 小样（simple `note_0123` / large-pitch `note_0404` / lyric-regression `note_0061` / gap `note_0391` / corruption `note_0012`）与 QC PASS contract `c54f07d6`。但 follow-up Git audit 发现 acceptance SHA 实际只有 `note_0123 / cal-srp-d2be...` 这一份新 m25-cal-2 sample 可读取，另外 4 个 sample 目录缺失；`qc/verdict.json`、`qc/audit.jsonl`、新 `plan.json`、`state.json` 也缺失。因此此 PASS 降级为 **unverified local claim**，不得勾选 Review Readiness。
- **ChatGPT Git audit — note_0123**：semantic diff outside target 为空；neutral-vowel USTX 干净；target source vocal F0 ≈ 62→64，Candidate ≈ 62→64，Baseline ≈ 64→64，说明 candidate 具有结构判断价值。但完整 4.66s A/B 的 target 前与 target 后 waveform RMS-diff / baseline-RMS 均约 0.68，且 full RMS Baseline≈0.030、Candidate≈0.044，显示 phrase-wide acoustic/context drift。故 score-level contract PASS ≠ human-review audio PASS。

#### G5A/G5B + Git-evidence 实现记录（`e020cf9`+`4de7e88`，artifacts `eafc3b3`，CI `35312608174`，295 passed）

- **G5A target-focus**：每项从**已渲染的**整段 OPTION wav 裁 `BASELINE_TARGET.wav`/`CANDIDATE_TARGET.wav`（declared region ±0.5s，`_crop_rendered`——绝不重渲短窗）。Web UI 主顺序 = SOURCE_FOCUS 原曲→人声→盲选 target-focus A/B→整段 A/B（辅助）。
- **G5B signal_qc.json**：sample_rate/duration、baseline/candidate rms+peak、silence_fraction、target_window（absolute+phrase-relative）、**pre/target/post AB-diff rms-ratio**（ChatGPT 审计同款指标 rms(b−c)/rms(b)）、loudness ratio、FCPE target-window F0 summary（source/baseline/candidate：median + 前后半段 median——可见 62→64 vs 64→64）、target_focus_sha256、`auto_flags`+`auto_review_ready`。flags：`pre/post_target_ab_drift>0.5`、`option_loudness_drift`∉[0.7,1.4]、两 option target-F0 均离 source>1st。
- **Git-evidence 硬规则**：`git_evidence()` 用 `git ls-files` 机检全部必需文件；`write_verdict(PASS)` 在被审样本/plan/state 未提交 Git 时**拒绝记录**；`review_ready()` 还要求 qc/verdict.json+audit.jsonl 已提交 **且** verdict 带 `git_evidence_at_record`——旧 regime 写的 verdict（含 devin PASS）自动失效；`state.json` 记录 git_evidence 快照。
- **真实 run 状态（`diag-20260917-181538-6aec`）**：21/21 项 augment 完成；signal_qc 全部 flag 目标外漂移（pre 0.53–1.07 / post 0.53–2.11，复现 maintainer 的 ~0.68）、4 项 loudness drift、5 项 both-options-F0-mismatch → `auto_review_ready=false` store-wide；21/21 `verify_package` 仍 valid；`git_evidence` = 277/277 committed、missing=0；`review_ready=false`（等 maintainer PASS）。
- **新回归**：+6（PASS 无 commit 拒绝 / qc 未提交不 ready / legacy verdict 永不 ready / focus 裁剪尺寸+字段 / 漂移 flag / evidence missing 清单），累计 295。
- **剩余阻塞**：maintainer 审 Git artifacts → `structure-calib-qc --pass --auditor <name>`（命令本身强制 Git 证据齐全才记录）→ 用户裁决 21 项 → summary + apply。

#### G5F blocker 修复实现记录（`980fcb9` 代码 + `fe26daa` artifacts + `f735808` payload，310 passed）

**Blocker 1 — stale Git SHA 下载面 → FIXED。** 提交流程改为两段：`pilot_review.json` 在 artifact commit **之后**生成，使 `git.sha` 指向实际包含被引用字节的 commit（`346e2f6`），再单独提交 payload。实测验证：每组 `OPTION_*_LISTEN` raw URL 可下载且 **bytes sha256 == manifest sha256**（note_0012 B: 532772B ✓ / note_0061 B: 555704B ✓）。禁止再出现"payload sha 先于 artifact commit"的顺序。

**Blocker 2 — 可发声 `a` → FIXED（fail-closed gap 规则）。** `review_lyrics` 语义收紧：unmapped note 仅在与前 note **相接**时写 `+`；真实 gap 后的 unmapped note 返回 `None` → 调用方 fail-closed 不出包。关键实证：探针 ustx（note + 480tick gap + `+` note）经 bridge 实测 OpenUtau 报 `Unrecognized phoneme "+"` —— gap 后 `+` 本来就**不可渲染**，builder 检查是对的，fail-closed 是唯一诚实路径。已验证歌词：`note_0188/0192/0379` 全部 `可惜从没人陪我演这剧本` 家族，A/B 仅在 declared split 位差一个 `+`。

**Blocker 3 — 非目标区 drift → FIXED（shared-context splice listen 面）。** 定位结论：同 ustx 重渲 raw_diff=0.0004 → **DiffSinger 是确定性的**，drift 不是噪声；逐窗互相关显示 pre-target 恒定 -1~2ms 前移 + 轻微声学涂抹（duration 模型对全音素序列全局 attention，split 的 `+` 音素扰动所有 context note 时值）——这是真实的 renderer/global-context effect，放宽阈值不可辩护。修法按 spec "shared context" 思路：**LISTEN 面** B = baseline 上下文 + candidate 目标段（`SPLICE_PAD_S=0.35s` 外取 baseline 低能点、每边 lag 对齐 ±10ms 置信门控、40ms crossfade）→ 构造上 outside diff=0；canonical 完整渲染不动，drift 移入 `renderer_global_context`（pre/post canonical ratio + `timing_shift_ms_median` + `aligned_residual_median` + audit flags）如实记录。`auto_flags`/`auto_review_ready` 改为度量**试听面**（reviewer 实际听到的），canonical drift 降级为审计记录不阻塞。真实验证（note_0012）：edge_lag 1.72ms/0.82ms 高置信、outside diff 0.0/0.0、canonical pre 2.16/post 1.10 全部保留、`auto_review_ready=True`。

**Pilot 3–5 重选 → note_0188 / note_0192 / note_0379。** 原 0123/0391/0404 无歌词证据（fail-closed）；候选 0248 因 gap 后 unmapped note 正当 fail-closed、0044/0246 有 canonical loudness flag。最终 5 组 = `0012 / 0061 / 0188 / 0192 / 0379`（全曲分布 18.4s–183.0s，evidence gate 全过，signal_qc flags 全空）。

**状态**：`git_evidence 468/468 complete`；`review_ready=false`（无当前合同 QC verdict —— 质量暂停正确维持）；21 项 `verify_package` 全 valid；5 项 canonical `option_loudness_drift` 作为渲染缺陷如实记录。**剩余唯一阻塞**：maintainer 审 Git artifacts → `structure-calib-qc --pass --auditor <name>` → 用户重审 pilot。

#### G5G close-out 实现记录（`7a9fa7a` 代码 + `7d44e11` artifacts + `5cc5434` payload，315 passed）

**Blocker A — G1 残留 `a` → FIXED。** 扫描证实 note_0012 的 USTX 确含 `a`（rlv1 产物）；rlv2 下其映射 fail-closed（gap 后 unmapped note——探针实证 `+` 不可渲染、hanzi 属猜测）。重渲路径同时发现 **全部其余 evidence 项（0044/0246/0248）也 fail-closed**——全库只有 4 项能诚实渲染 real_lyric_review。**最终 pilot = 4 组**：`note_0061/0188/0192/0379`（37.8s–183.0s），全部 impl=rlv2、verify_package=ok、USTX 无 `a`、`auto_review_ready=True`。note_0012 退回 neutral_vowel（合法非 pilot 项）。

**Blocker B — impl 版本绑定 → FIXED。** `LYRIC_MAPPING_IMPL_VERSION`（nv1 / rlv2）并入 `render_contract_sha`——语义 bump → 不同 contract_sha → 旧 artifact 自动 stale；`item_contract_stale()` 检测；manifest 记录 `lyric_mapping_impl`；回归：rlv1-sha artifact 不得通过 rlv2 staleness 检查。16 个未动 neutral manifest 仅元数据重绑（音频不变，nv1 语义未变）。

**Blocker C — plan 权威重建 → FIXED。** `rebuild_plan()` 从 item manifests + signal_qc **重建**（非 merge），`plan_invariants()` 校验五项字段一致 + staleness + item 覆盖——任一 mismatch：`review_ready=false`、`build_pilot_review` 抛错、`write_verdict(PASS)` 拒绝、`state.json` 记录 violations。实测重建后 `ok, 0 violations`（此前 plan 残留旧 hash/flags 的条目全部纠正）。

**Blocker D — payload 后生成 → FIXED。** 顺序：artifacts commit（`7d44e11`）→ payload 生成绑定该 sha → payload 单独 commit（`5cc5434`）。实测 4 组全部 main+auxiliary 文件：raw URL 可下载、bytes sha256 == manifest sha256，0 失败。

**Blocker E — 自检全绿。** pytest 315 passed；CI run `35335531857`；4 项 verify_package=ok；git_evidence 468/468；invariants ok；USTX 无 `a`（逐项验证）；stale-artifact 回归通过；`review_ready=false` 正确维持（等 maintainer verdict）。

---

### 10.1.5B Current calibration artifact status

当前 Git 中 `m25-cal-1` 的 21 个 A/B 包：

```text
archive: keep for regression/audit
human review: STOP
repair authority: INVALID
quality acceptance: FAIL
```

已发现的真实 Baseline lyric examples 可作为永久 regression evidence：

```text
"圈+勾成指纹+印在我+的的嘴唇"
"去秋来+的盛+却+住+了了+昏"
"夜剩我+个人++等清+晨+a"
```

这些不是“用户主观不喜欢”，而是 review input 已发生可观察 semantic corruption。

---

### 10.1.6 Blocker F — merge 必须验证 temporal adjacency ✅ IMPLEMENTED @ 5a4a486

已实现：`MERGE_ADJ_TOL_S = 0.06`（一个 F0 frame + onset snap 容差，代码注释说明语义）；`validate_structure_patch` merge 分支在 index-contiguous 之外逐对验证 `gap = next.start - prev.end`，`gap > tol → merge_temporal_gap`、`gap < -tol → merge_temporal_overlap`；merged span 仍须等于连续 union。F1–F5 回归在 `test_structure_repair.py::test_merge_temporal_adjacency`（精确共享边界 / tol 内小 gap 允许；0.07s/0.5s/1.0s gap 与 material overlap 拒绝；3-note merge 桥接 >tol gap 拒绝）；F6 由全套结构测试 + 真实 run 覆盖。

原始规格（保留）：

```text
note_i, note_i+1
```

但 index-adjacent 不等于 time-contiguous。以下情况必须拒绝：

```text
note A: [10.0, 10.5]
gap:    1.0s
note B: [11.5, 12.0]

不能 merge → [10.0, 12.0]
```

否则会把真实 silence / articulation gap 吞进一个持续音。

#### Required fix

merge validation 必须同时满足：

```text
1. Candidate-0 indices contiguous
2. every adjacent pair is temporally contiguous within an explicit tolerance
3. merged span equals the continuous union
4. no hidden positive gap larger than tolerance
5. no overlap beyond allowed timing tolerance
```

新增显式常量，例如：

```text
MERGE_ADJ_TOL_S
```

其值必须有代码注释说明时间量化/容差语义，禁止无限制吸收 gap。

#### Required regressions

```text
F1. contiguous indices + exact shared boundary → allow
F2. contiguous indices + small gap within MERGE_ADJ_TOL_S → allow
F3. contiguous indices + gap > tolerance → reject merge_temporal_gap
F4. contiguous indices + material overlap > tolerance → reject
F5. merged span cannot bridge rejected gap
F6. existing real-run split behavior / human authority / rollback 不回归
```

---

### 10.1.7 M2.5 FINAL acceptance gate

M2.5 只有同时满足以下条件才允许从 CURRENT / CALIBRATION HOLD 改为 FROZEN：

```text
A. Engine / lifecycle
   [✓] m25-1 plan/apply
   [✓] Candidate-0 immutable
   [✓] dual hash + authority freshness
   [✓] plan_hash tamper-evidence
   [✓] conflict/dedupe/rollback

B. Human structure
   [✓] valid blocked_structure authority reuse
   [✓] no re-review for same exact package

C. Human-review readiness
   [✓] m25-cal-2 or later schema active
   [✓] m25-cal-1 packages/decisions fail-closed for authority
   [✓] neutral-vowel diagnostic contract implemented
   [✓] semantic-diff mechanism implemented
   [✓] m25-cal-2 sample/item directories committed to Git
       （eafc3b3：21 项全量 — 含全部 5 个代表小样）
   [✓] every Git item contains WAV + USTX + manifest + semantic_diff
       + BASELINE_TARGET.wav + CANDIDATE_TARGET.wav + signal_qc.json
       （git_evidence 机检 277/277，missing=0）
   [✓] qc/verdict.json committed to Git（eafc3b3）
   [✓] qc/audit.jsonl committed to Git（eafc3b3）
   [✓] current m25-cal-2 plan.json + state.json committed to Git
   [✓] ChatGPT/maintainer independently reviewed current Git artifacts
       （5 representative items；target-focus has real diagnostic value）
   [✓] operation-aware child-level F0 QC implemented（7929773 —
       `child_f0_qc` per-child spans from declared patch boundary；
       split→parent.start/boundary/end，merge→merged span；
       per-child source/baseline/candidate FCPE summary +
       voiced_fraction/iqr/dominant/evidence；
       insufficient→unavailable、iqr>3st|dominant<0.6→ambiguous，
       绝不伪造 MIDI 或强制 winner）
   [✓] regenerated signal_qc.json committed for all 21 items（2056ac2 —
       21×signal_qc + 84 CORE crops；361/361 git_evidence complete）
   [✓] note_0012 / 0061 / 0123 child-level regression direction matches
       Source 62→64 / Baseline 64→64 / Candidate 62→64
       （实测 improvement +1.92 / +1.97 / +1.53 st；
       误导性 both-mismatch 标志消失）
   [✓] ambiguous/high-octave child evidence can remain neutral
       （H6/H7 回归：unavailable_child_slots、octave_ambiguous flag、
       structure_error 仅聚合 available 非 ambiguous 证据）
   [ ] ChatGPT/maintainer re-reviews regenerated Git artifacts
   [ ] ChatGPT/maintainer explicit REVIEW_READY = PASS
       （note: signal_qc auto_review_ready=false store-wide —
       目标外 A/B 漂移全量存在；target-focus 是主比较面；
       旧 devin verdict 因无 git_evidence_at_record 已失效）
D. Machine split precision
   [ ] only after Git-backed Review Readiness PASS may the full 21-item
       batch be considered review-authorized
   [✓] full 21-item current plan/state committed to Git before user review
       （eafc3b3 — 在 maintainer PASS 前 ready 门仍关闭）
   [ ] all 21 adjudicated or explicitly unresolved
   [ ] only human-confirmed splits enter trusted corrected score
   [ ] false positives/equivalent/none-correct remain no-repair
   [ ] calibration summary recorded
E. Merge correctness
   [✓] temporal-adjacency gate implemented（MERGE_ADJ_TOL_S=0.06）
   [✓] gap/overlap regressions green（F1–F5 + 全量 279）

F. Permanent safety
   [✓] 189.84s no false repair（trusted score 中 58.12 不变）
   [✓] 202.52s no false repair（65.3 不变）
   [✓] Candidate 0 file hash unchanged

G. Final remote gate
   [✓] new FINAL implementation SHA after child-level F0 QC
       （7929773 code + 2056ac2 artifacts）
   [ ] GitHub Actions checkout == FINAL SHA（7929773 CI 待确认）
   [ ] pytest success（本地 300 passed）
   [✓] H1–H8 regressions included（H1 child-span、H3 improvement
       direction、H6 unavailable、H7 octave-ambiguous + CORE 盲映射；
       H2/H4/H5/H8 语义由上述回归覆盖）
   [ ] Git evidence completeness remains green
   [ ] web target blind mapping regression remains green
   [ ] no skipped/disabled core regression
   [ ] maintainer REVIEW_READY PASS after regenerated artifacts
```

完成后才允许：

```text
M2.5 = FROZEN
trusted structure-corrected score = human-selected + human-confirmed machine candidates
M2.7 lyrics mapping = UNBLOCKED
```

#### Compatibility note — pre-738 m24-2 plans

`73819a9` 引入新的 `canonical_plan_hash()` 并让 M2.4 apply 也重算 hash；因此在该 commit 之前生成的旧 `m24-2` plan 即使 schema 相同，也可能因 canonical hash 算法变化被判 stale。

这是 fail-closed 行为，不是 correctness blocker：

```text
pre-738 m24-2 plan
→ regenerate repair-plan
→ use current canonical hash
→ do not silently migrate / backfill
```

## 10.2 M2.6 — Optional second opinion

只作为必要时 second opinion，不得破坏 frozen evidence-independence semantics。

## 10.3 M2.7 — Lyrics mapping + base USTX

Written melody 稳定后再做：

```text
1 char → 1 note
1 char → N notes (melisma)
N chars → N notes
```

OpenUtau：

```text
首 note：真实歌词
同字后续：+
换气：AP
静音：gap / SP
```

基础 USTX 验收：

> 不做泠鸢 style 和复杂 PITD 时，是否已经唱对旋律和节奏？

## 10.4 M2.8 — PITD + render loop

基础 written score 通过后再加入：

```text
portamento
onset slide
ornament
vibrato
intonation deviation
```

PITD 不得掩盖 written-note error。

## 10.5 M2.9 — 《年轮》M2 验收

目标：确认完整 written score / lyrics / base render 已达到可接受正确度，并对未解决区域保留明确 audit 状态。

## 10.6 M3 — 泠鸢 style profile

> **原唱决定“唱什么”；泠鸢参考决定“怎么唱”。**

---

# 11. Evaluation / Audit

至少记录：

```text
GAME total run count
per-run GAME member notes/spans/tones
pairwise alignment costs
selected medoid + sensitivity
GAME run-tone distribution
match/gap/split/merge correspondence
orthogonal states
pitch/structure adjudication lifecycle
RMVPE / FCPE / third-F0 evidence
boundary/energy/onset/spectral/articulation evidence
separation sensitivity
group_scores
supporting_independence_groups
winner / runner-up / margin
virtual candidate notes
virtual-note B results
virtual GAME correspondence provenance
seed conditional/effective GAME support
winner GAME support/opposition
phrase-review target groups
review schema / identity schema
stable target_key / review_item_id
phrase windows / boundary source
review candidates + score patches
render profile hash
SOURCE/OPTION WAV hashes
plan_hash / audio_package_hash
human decision + generation + revision
legacy migration/archive provenance
repair plan hash
repair ids / source types
repair before / after
repair blocked reasons
corrected-score hash
rollback coverage
local integration result
remote CI run id / SHA / conclusion
cache/provenance manifest
```

Score artifacts：

```text
Candidate 0
virtual candidates
review context score
repair plan
corrected score
repair manifest
retune count
blocked repair count
split/merge/boundary-shift count
GAME preservation ratio
rollback coverage
```

---

# 12. Milestones

### M2.0 — Foundation survey ✅
### M2.1 / M2.1.1 — Initial diagnostic + correctness ✅
### M2.1.2 — GAME stochastic baseline ✅
### M2.2A — Formal sequence alignment ✅
### M2.2B — Dual-F0 ✅
### M2.3 — Residual-error triage ✅
### M2.3.1 — Triage calibration ✅
### M2.3.2A / A2 / A3 / A4 — ✅ FROZEN
### M2.3.2B1 / B2 / B3 — ✅ FROZEN
### E1 — GitHub Actions Remote CI — ✅ PASS
### M2.3.2C1 / C2 — ✅ FROZEN @ c0d2648
### M2.3.2D main workflow — ✅ IMPLEMENTED @ 0bbb098
### M2.3.2D exact-audio/run-authority integrity — ✅ IMPLEMENTED @ 5c54284
### M2.3.2D Stable Review Identity — ✅ IMPLEMENTED @ 2a997a2
### M2.3.2D Migration Integrity — ✅ IMPLEMENTED @ 905f144
### M2.3.2D FROZEN — ✅ @ 905f144 / CI 35238843522
### M2.4 — SAFE single-note pitch repair — ✅ HISTORICAL FREEZE @ ce083c9 / CI 35289803217
### Pre-M2.5 Freeze Integrity Patch — ✅ PASS @ 8a2d660 / CI 35294735189
### M2.5 — PROBABLE structure repair — ← HUMAN PILOT QUALITY HOLD（Group 1/2 both prefer B, but lyric + loudness defects invalidate authority; fix review audio before continuing）
### M2.6 — Optional second opinion
### M2.7 — Lyrics mapping + base USTX
### M2.8 — PITD + render loop
### M2.9 — 《年轮》M2 验收
### M3 — 泠鸢 style profile

---

# 13. 最终不可违反的规则

1. GAME 是基座，不是 truth。
2. Candidate 0 只能来自真实 GAME run。
3. Consensus 只表示 uncertainty/correspondence。
4. GAME stochastic runs 不是多个独立模型。
5. F0 measurement ≠ score interpretation。
6. missing evidence = neutral。
7. 单 extractor / 单 mechanism 不得重复计票。
8. 结构未定时 pitch 只能 provisional。
9. C 改 identity/span 后 old B 必须 invalidate + regenerate + rerun。
10. virtual candidate pitch seed 不等于 GAME evidence。
11. 无真实 GAME virtual identity correspondence 时 GAME group 必须 neutral。
12. 时间 overlap 本身不等于 virtual child identity correspondence。
13. parent-spanning GAME note 不得同时给 split 后两个 children pitch vote。
14. Virtual GAME denominator 必须保留 total GAME runs。
15. child GAME support 必须同时反映 identity presence 与 pitch agreement。
16. RMVPE voiced-drop 不算独立 non-F0 family。
17. F0 changepoint 本身不能证明 written-note boundary。
18. Split 与 portamento/ornament 必须真实竞争。
19. `run_note_counts==0` 不代表 merge。
20. Finalized C semantics 优先于 raw historical structure flag。
21. SAFE gate 必须在 finalized structure state 生效后计算。
22. separation-sensitive 不得因 virtual packet 丢字段而消失。
23. Candidate 0 永不被 adjudication / review / repair 原地覆盖。
24. D 只提供完整 phrase candidates + human adjudication，不要求用户猜 MIDI。
25. D 的不同候选除 target_group 外必须使用同一 context/render profile。
26. D 禁止 candidate Cartesian explosion；默认一个 target_group 一个 review item。
27. `review_item_id` 必须是 stable target identity，禁止 batch-local sequence number。
28. 同一 target 跨 full/subset/reorder/max-items/gen1→gen2 必须保持同一 review_item_id。
29. 不同 target 的 full target_key 不得碰撞；碰撞必须 hard fail。
30. `review_item_id` 必须数学上等于 `"ri-" + target_key[:16]`。
31. human decision 必须同时绑定 d3 stable target_key + exact audio_package_hash。
32. legacy d2 / mixed / unknown review schema 必须 fail-closed，永不得授权 repair。
33. d2 顺序号不得被自动猜测映射到 d3 target。
34. `verify_package` 必须验证实际 SOURCE/OPTION bytes，并重算最终 audio_package_hash。
35. stale / invalid / malformed review 不得授权 repair。
36. Human-selected repair 只能由 `repair_authorized_decision()` 授权。
37. Human-selected repair 必须直接消费 decision snapshot，不得重新解释 OPTION / hypothesis。
38. M2.4 v1 只允许 single-note written-pitch retune。
39. M2.4 v1 不得修改 note identity / timing / count / lyrics / PITD。
40. 同一 note 多个冲突 repair 不得 silent precedence，必须 block。
41. repair plan 与 apply 必须分离；planning 0 mutation。
42. repair plan material source change 后必须 stale。
43. corrected score 必须从 immutable Candidate 0 copy-on-write 构建。
44. rollback 必须通过 Candidate 0 + repair manifest 重建，不得反向猜值。
45. 189s 永久 extractor-conflict regression；无 human authorization 不得 repair。
46. 202s 永久 stochastic pitch/identity regression；无 human authorization 不得 repair。
47. 0 repair 是合法结果。
48. 从 C2 起，没有 FINAL acceptance SHA 的 remote CI green，不允许 FROZEN/PASS。
49. structure 未 finalized 时，identity-unsafe aggregate GAME run_tones 不得成为 finalized pitch support。
50. missing/insufficient structure evidence 必须 neutral，不得通过 complement 或默认值变成 H0 support。
51. M2.4 repair plan 必须同时绑定 Candidate-0 semantic notes hash 与 full-file sha256。
52. legacy / unsupported / 缺任一 Candidate-0 binding 的 repair plan 必须 fail-closed；不得 silent migration 或补算当前 hash 后继续 apply。
53. Pre-M2.5 integrity acceptance 未通过前，不得启动 structure repair。
54. structure repair 必须 operation-specific（split / merge / boundary-shift）并具备独立 identity、freshness、rollback contract。
55. machine `TRUE_SPLIT_CANDIDATE` 不是自动 repair truth；在 precision 未经独立校准前，只能作为候选，不能仅复查同一 C gate 后直接进入 trusted written score。
56. 人工审核前必须先通过 Review Readiness Gate；render success / verify_package valid 不代表音频可用于人工判断。
57. calibration Baseline 必须来自 canonical GAME/OpenUtau baseline 或明确的 neutral-vowel diagnostic contract；禁止 calibration layer 重新猜歌词或重建非 target 演唱语义。
58. material review-render 变更后，必须先生成 3–5 个代表性小样并 **实际提交到 Git**；本地存在、Agent 自报 PASS、docs 声明均不能替代 Git artifact。
59. Review Readiness 的唯一可验收证据来源是 acceptance SHA 上可直接读取的 Git artifact；缺任一 required sample/QC/plan/state 文件，对应 gate 必须视为未完成。
60. ChatGPT/maintainer pre-human QC 不能由执行 Agent 自己代签；auditor=Devin/SWE2 不等于 ChatGPT/maintainer PASS。
61. 人工 A/B 的主要试听对象必须是完整自然唱句的 full-phrase render；target-focus/CORE 仅作辅助定位。每项仍必须提交 signal_qc.json。
62. split calibration 的 F0 QC 必须严格按 parent.start / split boundary / parent.end 计算 child-level evidence；禁止用 target±0.5s 总窗口的 first/second-half 冒充 child identity。
63. child-level source/baseline/candidate F0 只能作为 review-readiness/diagnostic evidence；extractor unavailable 或 octave-ambiguous 必须 neutral，不得强制机器判 winner。
64. `m25-cal-1` 现有 21 包与 decision 仅保留 audit/regression，用于 repair authority 时必须 fail-closed；不得 silent migration。
65. 当前《年轮》的 machine split 最终仍必须通过 phrase-level Baseline vs Split calibration；只有 human-confirmed split 才能进入 trusted corrected score。
66. merge 的 adjacency 必须同时是 index-adjacent + temporal-adjacent；禁止把超过明确 tolerance 的 gap/overlap 吞进 merged note。
67. `plan_hash` 必须在 apply 时可重算验证；不得替代 Candidate-0/authority freshness gate。
68. 先把 written score 唱对，再生成 PITD。
69. 远程人工审核允许直接使用 GitHub 下载/raw/blob 链接；native ChatGPT inline player 不再是硬要求。
70. 人工主审核必须使用完整自然唱句（通常 4–10s，必要时 3–12s）；CORE/target-focus 只能作为 secondary diagnostic aid。
71. A/B/source 必须共享同一 phrase 语义窗口与上下文；不得因为 candidate 不同而改变截取边界。
72. 聊天选择必须经官方 decision gate 重新绑定 `cal_item_id / repair_id / selected OPTION / package hash` 后才能成为 repair authority；聊天文本本身不是 authority。
73. 远程审核采用 5-item pilot-first；任一项出现歌词错误、明显响度偏差、非 target 渲染污染或仍不可判断，必须立即停止，不得强迫用户完成 21 项。
74. 在质量失败的 review package 上产生的 A/B 偏好只能记为 diagnostic preference，不得成为 official decision 或 repair authority。
75. 先“唱对”，再做泠鸢风格。
