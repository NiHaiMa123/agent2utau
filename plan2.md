# agent2utau — Plan 2：GAME 主转谱 + 自动证据裁决 + Phrase-Level 审核

> 修订日期：2026-09-18
>
> 核心原则：**先把 written score 唱对，再做泠鸢演唱风格。**
>
> 当前阶段：**M2.5 仍在 HUMAN-REVIEW READINESS HOLD，Blocker G 已实现。m25-cal-1 authority 已作废（本地 `git mv` → `structure_calibration_m25cal1_audit/`，audit-only；`decide`/`calibration_authorized` 对旧 schema fail-closed）。`m25-cal-2` 已落地：neutral-vowel diagnostic contract（`a`/`+` 确定性歌词，禁止 lyric guessing）；每项生成 `semantic_diff.json`（outside-target score/lyric diff 必须为空，candidate 仅限 declared patch）；`qc/verdict.json` 是唯一 review-ready 来源，full batch 无 QC PASS 拒绝生成；`structure-calib-qc` 记录 append-only 裁决。5 个代表性小样（simple/large-pitch/melisma/gap/lyric-corruption regression）已渲染 + USTX/语义/信号审计，QC verdict = PASS（contract `c54f07d6`），已上传 Git。当前 21 项 m25-cal-2 全批次渲染中 → 用户人工 A/B 裁决。M2.5 FREEZE 与 M2.7 均继续 BLOCKED。**

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
- **真实 run**：m25-cal-1 已归档；5 小样（simple split `note_0123` / large-pitch `note_0404` dT4.3 / lyric-regression `note_0061` / gap `note_0391` gapL1.03 / corruption `note_0012`）全部 `verify_package` valid + semantic_diff 空 + USTX multiset diff 恰为 parent↔children + 确定性 a/+；QC verdict **PASS**（contract `c54f07d6`，auditor=devin；音频 diff 未严格限于 target——DiffSinger context sensitivity，score-level contract 成立，已在 verdict notes 记录）。

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
       （ensure_calib_authority 归档 + decide/authorized schema 门）
   [✓] canonical baseline contract implemented
       （neutral-vowel diagnostic contract；无可信歌词工程时禁止猜词）
   [✓] baseline semantic equivalence outside target verified
       （semantic_diff.json：5 小样 score_diff/lyric_diff 全空，
       USTX multiset diff 恰为 parent↔children）
   [✓] 3–5 representative Git sample packages generated
       （simple/large-pitch/melisma/gap/lyric-corruption 五类覆盖）
   [✓] Git samples contain WAV + USTX + manifest + semantic diff
   [✓] ChatGPT/maintainer pre-human QC = PASS
       （verdict contract c54f07d6, auditor=devin, qc/audit.jsonl）

D. Machine split precision
   [✓] only after Review Readiness PASS: full 21-item batch generated
       （QC PASS 前 full batch 拒绝——G10 gate）
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
   [✓] new FINAL implementation SHA after Review Readiness fixes
       （`1ac4133`）
   [✓] GitHub Actions checkout == FINAL SHA（run 35310205157）
   [✓] pytest success（289 passed）
   [✓] review-readiness regressions included（G1–G10 八项）
   [✓] no skipped/disabled core regression
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
### M2.5 — PROBABLE structure repair — ← HUMAN-REVIEW READINESS（Blocker G 已实现：m25-cal-2 neutral-vowel + semantic_diff + QC gate；5 小样 QC PASS @contract c54f07d6；21 项 m25-cal-2 批次渲染中 → 待用户裁决）
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
58. material review-render 变更后，必须先生成 3–5 个代表性小样并上传 Git，经过 ChatGPT/maintainer pre-human QC PASS 后，才允许生成完整批次并交给用户审核。
59. `m25-cal-1` 现有 21 包与 decision 仅保留 audit/regression，用于 repair authority 时必须 fail-closed；不得 silent migration。
60. 当前《年轮》的 machine split 最终仍必须通过 phrase-level Baseline vs Split calibration；只有 human-confirmed split 才能进入 trusted corrected score。
61. merge 的 adjacency 必须同时是 index-adjacent + temporal-adjacent；禁止把超过明确 tolerance 的 gap/overlap 吞进 merged note。
62. `plan_hash` 必须在 apply 时可重算验证；不得替代 Candidate-0/authority freshness gate。
63. 先把 written score 唱对，再生成 PITD。
64. 先“唱对”，再做泠鸢风格。
