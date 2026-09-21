# agent2utau — Plan 2：GAME 主转谱 + 自动证据裁决 + Phrase-Level 审核

> **ARCHIVED EXECUTION PLAN（2026-09-21）**：本文件保留 written-score adjudication 的历史、冻结 contract 与审计证据；不再作为后续表现调校的当前执行计划。已验证且仍在使用的规则已汇总到 `pipeline.md`；新的 PITD / vibrato / DYN / BREC / VOIC / TENC / Yousa style 路线以 `plan.md` 为准。

> 修订日期：2026-09-19
>
> 核心原则：**先把 written score 唱对，再做泠鸢演唱风格。**
>
> 当前阶段：**M2.5 HUMAN REVIEW PILOT = QUALITY HOLD / G5N.5 boundary-stability + token-bound landmark assignment（IMPLEMENTED, rlv13）。** G5N.5 已落地：Whisper anchor 资格改为 5-context perturbation boundary stability（jitter≤0.12s、n_valid≥3、stable/unstable/insufficient 持久化、仍属同一 measurement family）；onset/energy landmarks 经 `_assign_onsets` 单调一对一 DP 绑定到 token 后才参与 support/contradiction；`_adjudicate_lyric_evidence` 重写为 per-token reliable-family 裁决并持久化 `anchor_conflicts[]`（每项 ambiguity 可重建）。真实 rlv13 重扫：`2/21 eligible`——`roster=[note_0440,note_0441]`（首次 current-contract post-loop-verified roster），`n_timing_supported=4`、`n_alignment_fail=7`；0231/0305 order_conflict、0325 ambiguous 均为同 token 可靠家族真实冲突，无 audit-only Whisper veto 残留。6 个包已 rlv13 重建且 package_state=valid。但 `roster_size_ok=False`（roster<3）且 `signal_qc.auto_review_ready=False` → **review surface 仍未发射，`pilot_authority.ok=false`、`review_ready=false`**——禁止用户试听、禁止 bulk written-timing repair、禁止记录 calibration decision、禁止 M2.5 freeze，维持 QUALITY HOLD。

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


---

# 6. Pre-M2.5 Freeze Integrity Patch ✅ FROZEN SUMMARY

> Full historical specification and acceptance evidence moved to `docs/plan2_history.md`.

Frozen integrity guarantees that remain authoritative:

```text
B identity safety
- structure-ambiguous aggregate GAME run_tones cannot become finalized pitch support
- C identity/span change invalidates old B and requires identity-safe rebuild/rerun

C missing-evidence neutrality
- missing/insufficient boundary or GAME evidence is neutral
- absence of evidence cannot become keep/H0 support by complement/default

M2.4 Candidate-0 binding
- repair plan binds semantic notes hash + exact baseline_game.json file sha256
- apply verifies both
- metadata/provenance/byte changes stale the old plan

Legacy repair-plan fail-closed
- unsupported/legacy schema or missing either Candidate-0 binding is rejected
- no silent migration/backfill

Permanent safety
- 189s / 202s false-repair regressions remain mandatory
- Candidate 0 remains immutable
- FINAL PASS/FROZEN requires remote CI on the exact acceptance SHA
```

Historical freeze:

```text
Pre-M2.5 Freeze Integrity Patch
PASS @ 8a2d660
CI 35294735189
248 passed
```

---

# 7. M2.4 — SAFE single-note pitch repair ✅ HISTORICAL FROZEN SUMMARY

> Full M2.4 engine specification, acceptance matrix, test history, and rollback details are archived in `docs/plan2_history.md`.

Still-authoritative M2.4 contract:

```text
scope
- v1 only changes single-note written pitch
- no note identity/timing/count/lyrics/PITD change

authorization
- machine-safe consumes finalized frozen-B SAFE result only
- human-selected consumes repair_authorized_decision() snapshot only
- stale/malformed/legacy authority = no repair

lifecycle
- planning and apply are separate
- planning performs zero score mutation
- apply is copy-on-write from immutable Candidate 0
- repair identity is deterministic/idempotent
- conflicts block; no silent precedence

freshness
- plan_hash tamper-evident
- Candidate-0 semantic hash + full-file hash both required
- material source/authority change stales the plan

rollback/audit
- corrected score + repair manifest must reconstruct every change
- rollback rebuilds from Candidate 0 + manifest, never inverse guessing
- zero-repair / partial-repair are valid outcomes
```

Historical freeze:

```text
M2.4 SAFE repair
ce083c9
CI 35289803217
226 passed
```

---

# 8. M2.4 Frozen Acceptance Summary

Any future regression touching M2.4 must preserve:

```text
[✓] pitch-only patch shape
[✓] machine-safe frozen-B authority
[✓] human decision exact-package authority
[✓] Candidate-0 immutability
[✓] dual Candidate-0 binding
[✓] plan/apply separation
[✓] conflict fail-closed
[✓] idempotency
[✓] rollback coverage
[✓] 189s / 202s permanent no-false-repair cases
[✓] exact-SHA remote CI gate
```

Do not reopen M2.4 merely to make M2.5 calibration easier.

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


---

# 10. M2.5+ 后续阶段边界

## 10.1 M2.5 — PROBABLE structure repair ← CURRENT / QUALITY HOLD — G5N

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


---

#### G5N B2 semantic adjudication + lyric-evidence recovery（rlv8 已实现；correctness 待 G5N.1 收口）

G5M 已完成 21-item honest-roster scan，并诚实得到 `0/21 eligible`。该结果关闭了“继续机械重选 pilot”这条路，但**不能把所有失败项解释成永久不可审核，更不能把所有 B2 自动解释成 written-score error**。

##### G5M 结果的正确语义

当前 inventory：

```text
21 total
13 lyric_evidence fail
  11 low_confidence
  2 no_chars

8 unresolved B2
0 unresolved B1

roster_candidates = []
review_ready = false
```

其中：

```text
B2 exists
→ 证明 source acoustic landmark 落在当前 legal carrier range 外

B2 exists
!= 证明 written score 一定错
!= 证明该 item 永久不可 human review
```

G5L 已明确：

```text
early B2
→ may be consonant preutterance / anticipation
→ only early direction may use this hypothesis

late B2
→ may be post-boundary acoustic delay / carrier-too-short /
   written-timing mismatch
→ MUST NOT be called anticipation

120ms
→ triage prior only
→ never final semantic authority
```

因此 G5N 要解决的是 **B2 的语义归因**，而不是继续调 closed-loop 参数。

##### Lane A — recover the 13 lyric-evidence failures

当前：

```text
11 × low_confidence
2 × no_chars
```

禁止：

```text
MIN_REVIEW_CHAR_PROB 0.25 → 直接降低阈值来凑 roster
把单个低概率字静默当成可信 timing truth
把 no_chars 当永久无歌词
```

需要逐项区分：

```text
A1. evidence-window / LRC / phrase-boundary coverage bug
A2. source separation / vocal quality 导致 aligner 失败
A3. Whisper attention/DTW 对该唱法本身低置信
A4. 单个 char outlier，但整句顺序/边界有其他独立证据
A5. 真正无法可靠绑定歌词
```

优先检查：

```text
note_0391 / note_0404
→ no_chars
→ first investigate phrase/LRC/evidence-window coverage

note_0231 min_probability=0.193
note_0325 min_probability=0.211
→ 不得直接降 0.25 threshold
→ 用第二独立 evidence 判断该低值是否只是单字 aligner outlier
```

允许新增的独立 evidence：

```text
second forced-align / CTC family
manual small-subset char landmark annotation for calibration
phoneme boundary evidence
LRC + known lyric sequence constrained alignment
```

原则：

```text
second evidence confirms sequence/timing
→ item may regain lyric-evidence eligibility

evidence remains contradictory/unavailable
→ fail-closed
```

任何 source lyric evidence contract/material method 改变：

```text
version/provenance must bump
old package/pilot/verdict stale if review semantics change
```

##### Lane B — adjudicate the 8 unresolved B2 items

当前 8 项不是一个同质问题。

代表性实测：

```text
note_0012:
  圆 early 318.7ms → written_timing_suspect
  另有多个 8–119ms early/late conflicts

note_0044:
  却 early 23.8ms
  遮 late 65.7ms

note_0246 / note_0248:
  夜 early 37.3ms
  等 early 7.7ms
  晨 late 24.3ms

note_0061:
  晨 late 142.6ms + 其他 conflicts

note_0188 / note_0192:
  可人陪这本 shared phrase conflict

note_0379:
  4 B2, 28–84ms range
```

这些不能继续统一成：

```text
B2 → written_timing_diagnosis → permanent pilot reject
```

必须增加 B2 adjudication result，例如：

```text
b2_semantic =
  benign_preutterance
  benign_post_boundary_delay
  measurement_ambiguous
  written_timing_error
  structure_timing_error
  unresolved
```

只有：

```text
benign_preutterance
benign_post_boundary_delay
```

并且有独立 evidence 支持、不会污染 target split 判断时，才允许该 conflict 不再作为 ordinary pilot blocker。

```text
written_timing_error / structure_timing_error
→ route upstream
→ 不允许 review-only lyric overlay cosmetically hide it

measurement_ambiguous / unresolved
→ fail-closed
```

##### Required B2 evidence

最终 adjudication 不得只消费 overhang ms。至少结合：

```text
direction: early / late
phoneme context: initial/final, consonant/vowel onset semantics
source acoustic landmark family
second independent landmark family where available
neighbor char onset/offset
carrier start/end/duration
inter-note gap / overlap
whether required correction would rewrite written-note timing
rendered phoneme/preutterance behavior
same conflict across A/B target options
```

如果要把某个 20–80ms conflict 标为 benign，必须有**独立物理/音素证据**，不能因为“数值小”直接通过。

##### Phrase-level conflict 的语义修正

`0188/0192` 和 `0246/0248` 在同一 phrase 内重复出现相同 B2 集合，能够证明：

```text
conflict is target-independent
→ 不是某一个 split option 偶发制造的
```

但两个 target 共享同一个：

```text
SOURCE phrase
Candidate-0 context
lyric alignment
carrier timing
```

因此这种重复**不是独立第二证据**，不能自动升级成：

```text
double-confirmed written timing error
```

字段建议明确拆成：

```text
phrase_level_target_independent_conflict = true
```

其作用是：

```text
ordinary target-only pilot blocker
+ route to semantic adjudication
```

而不是最终 written-score verdict。

##### Priority probes

先用最小范围验证 B2 是否存在 benign phoneme-timing 类：

```text
Priority 1: note_0044
  only 2 B2: early 23.8ms / late 65.7ms

Priority 2: note_0246
Priority 3: note_0248
  B2 only 7.7–37.3ms / 24.3ms
```

原因：

```text
small overhang
+ source lyric evidence already good
+ ideal for testing phoneme-aware adjudication
```

不要优先拿：

```text
note_0012 圆 early 318.7ms
note_0061 晨 late 142.6ms
0188/0192 systematic phrase conflicts
```

去定义 benign semantics；这些应继续保留为 harder written-timing/structure cases。

##### G5N acceptance

G5N 关闭至少要求：

```text
A. lyric evidence
   [ ] no_chars root cause resolved or explicitly proven unavailable
   [ ] low-confidence items have independent-evidence adjudication
   [ ] no threshold relaxation solely to recover roster
   [ ] evidence provenance/version persisted

B. B2 semantics
   [ ] B2 no longer equals automatic written-timing error
   [ ] early/late consume phoneme-aware evidence
   [ ] small-overhang benign classification requires independent support
   [ ] phrase-level repetition treated as target-independent, not independent duplicate proof
   [ ] genuine written/structure errors route upstream
   [ ] ambiguous cases remain fail-closed

C. pilot eligibility
   [ ] rerun all 21 through revised current contract
   [ ] eligibility_inventory regenerated and committed
   [ ] only semantically resolved items may enter honest roster
   [ ] no unresolved B1/B2/lyric evidence blocker in roster

D. authority
   [ ] exact roster packages rebuilt if contract/material semantics changed
   [ ] exact payload/QC/state binding rebuilt
   [ ] pilot_authority.ok == true
   [ ] review_ready == true
   [ ] git_evidence.complete == true
   [ ] plan_invariants.ok == true
   [ ] FINAL SHA remote CI success
   [ ] maintainer/ChatGPT pre-human audit PASS
```

如果处理后仍然：

```text
0 eligible
```

这是允许的结果；必须继续 upstream diagnosis，而不是放宽 gate。

在 G5N 关闭前：

```text
DO NOT ask user to listen
DO NOT lower MIN_REVIEW_CHAR_PROB merely to create candidates
DO NOT treat every B2 as written-score error
DO NOT treat phrase-level duplicate targets as independent proof
DO NOT record calibration decisions
DO NOT freeze M2.5
```

##### G5N 实现记录（rlv8，PARTIAL — 需通过 G5N.1 correctness patch）

- **Lane A `_adjudicate_lyric_evidence`**：每个 lyric-evidence fail 得到显式归因 —
  `A1_coverage_suspect` / `A3_aligner_unreliable` / `A4_outlier_resolved` /
  `A4_outlier_unresolved` / `A5_instrumental_no_lyrics` / `A5_unbindable`。
  第二独立证据族 = `onset_strength_peak_v1`：低概率字的 whisper 位置必须在
  ±50ms 内存在 onset landmark 才算 confirmed。全部低概率字 confirmed 且存在
  高概率邻字 → recovered（threshold 0.25 不变）。真实结果：0231/0311/0325
  恢复（春 +28ms / 是 +5ms / 着 −17ms）；0391/0404 落 184–205.75s 器乐段 →
  A5；0076/0264/0305/0440 landmark 偏移 60–200ms 不确认 → A3/A4 unresolved。
- **Lane B `_b2_semantic`**（下沉进 `_classify_routes`，ctx+edges 参数）：
  逐字持久化 `b2_semantic` + `b2_evidence`（pinyin_initial / initial_class /
  second_family confirms|contradicts|unavailable / energy_edge_onset /
  gap_before|after_carrier / carrier_start|end / would_rewrite_written_timing /
  shared_bound_conflict）。规则：obstruent+early+confirms → benign_preutterance；
  late+confirms+≤150ms → benign_post_boundary_delay；大 overhang+confirms →
  written_timing_error；glide 永不能 consonant-preutter；unknown 音素 fail-closed；
  contradicts → measurement_ambiguous；无第二证据 → unresolved。
  真实分布：`圆`318.7ms confirmed → written_timing_error；`遮`/`可`/`人` late
  confirmed → benign_post_boundary_delay；其余全部 ambiguous/unresolved →
  fail-closed。
- **phrase-level** → `phrase_level_target_independent_conflict=true`：
  同 phrase 跨 target 的重复 B2 集合是 ONE finding（共享 source phrase /
  Candidate-0 context / lyric alignment / carrier bounds），路由到语义裁决，
  不作双重证实。
- **音素表**：`_PINYIN_INITIAL` 收录全部已观测 B2/低概率字符（可审计、表外
  fail-closed）；obstruent 可辅音先行、sonorant ≤60ms、glide 不可。
- **结果**：21 项 rlv8 重扫 → **0/21 eligible**（10 lyric-fail、1 B1、10
  unresolved-B2-semantic、4 phrase-level）。3 项恢复歌词证据但路线仍不合格。
  roster=[] → `pilot_authority.ok=false`、`review_ready=false` —— 全部
  fail-closed，无试听请求。
- 测试：N1–N10（benign 双向、contradiction→ambiguous、written_timing_error、
  unknown/glide fail-closed、A4 recovery、A5 instrumental、target-independent、
  benign 出 roster 路径）+ M1–M10/L1–L10 全回归 = 383 tests PASS。
---


---

#### G5N.1 Correctness patch（rlv9 lifecycle correctness 已闭合；identity authority 转入 G5N.2）

rlv8 的方向正确，但当前 `0/21 eligible` 不能直接作为最终证据，因为 eligibility / semantic adjudication 仍有四个 correctness 缺口。G5N.1 只修这些缺口，**禁止重新回到 parameter chasing**。

##### Blocker 1 — timing corroboration 不能冒充 lyric identity recovery

当前 Lane A：

```text
Whisper char probability < 0.25
+ onset_strength_peak_v1 在 ±50ms 内命中
+ phrase 内至少一个 high-confidence char
→ A4_outlier_resolved / recovered=true
```

这个逻辑最多证明：

```text
该时间附近存在独立 waveform onset
```

不能证明：

```text
这个 onset 的 lexical / phoneme identity
== Whisper 给出的那个汉字
```

因此 `onset_strength_peak_v1` 必须降级为 **timing corroboration only**。

允许的新状态：

```text
timing_corroborated_identity_unverified
```

只有 identity-bearing 第二证据成立后，低置信 char 才能真正 `lyric_recovered=true`。允许的 identity-bearing evidence 包括：

```text
- second forced-align / CTC alignment family using known lyric sequence
- phoneme-aware forced alignment with explicit char/phoneme identity
- maintainer/manual small-subset char landmark annotation used as calibration truth
```

禁止：

```text
waveform onset detector alone
→ recover lyric identity
```

rlv8 的 `0231 / 0311 / 0325` 暂时只能记为：

```text
timing corroborated
identity recovery NOT YET authoritative
```

除非补充 identity-bearing evidence。

##### Blocker 2 — benign B2 必须使用真正的 phoneme-aware semantic evidence

当前 late-side rule 实际接近：

```text
energy_edge_v1 also beyond carrier bound
+ known initial class
+ overhang <= 150ms
→ benign_post_boundary_delay
```

这仍然过弱。`onset_strength_peak_v1` 与 `energy_edge_v1` 都来自同一 source waveform 的 onset/energy family；它们可以确认“偏移真实存在”，但不足以独立证明“这是正常 phoneme boundary delay”。

因此 benign verdict 至少要求：

```text
1. direction
2. identity-aware phoneme context
3. source acoustic displacement evidence
4. carrier / inter-note geometry
5. neighbor phoneme/char timing consistency
6. at least one semantic/phoneme-boundary evidence family
   independent from simple waveform-onset confirmation
```

可用的 semantic/phoneme evidence：

```text
- identity-aware forced phoneme alignment
- singer/phonemizer phoneme timing or preutterance semantics
- rendered phoneme boundary behavior under unchanged written timing
- equivalent explicit phoneme-duration evidence
```

`gap_before_carrier_s / gap_after_carrier_s / carrier span / neighbor timing` 不得只记录在 JSON；如果声称它们参与 adjudication，就必须实际进入 verdict logic，并有 regression 证明。

规则：

```text
second waveform detector confirms same-side displacement
→ acoustic conflict confirmed
!= benign semantics confirmed
```

##### Blocker 3 — post-loop B1 必须进入 honest-roster hard gate

当前 inventory 会读取：

```text
post_loop_final_class
```

但 eligibility disqualifier 主要依据 pre-loop route。真实 rlv8 artifact 仍存在：

```text
note_0061: 一 → B1_cross_option_unstable
note_0379: 惜 / 本 → B1_detector_relock
```

这些必须明确 hard-block pilot，即使该 item 的所有 B2 后续都被 adjudicate 为 benign。

Required fix：

```text
for each current-contract package:
  inspect post_loop_final_class / char_routes
  any unresolved B1_* subtype
  → add unresolved_post_loop_B1:<chars/subtypes>
  → eligible=false
```

如果 item 尚未在 current contract 下 render，因此没有 post-loop evidence：

```text
cannot claim final eligibility
→ eligible_candidate_needs_render / rebuild_required
→ render + closed-loop + post-loop adjudication before roster
```

禁止仅凭 render-free pre-loop inventory 宣布最终 human-review eligibility。

##### Blocker 4 — phrase-level conflict / sub-resolution lifecycle

**A. phrase-level target-independent conflict**

`phrase_level_target_independent_conflict=true` 是 audit/routing fact：

```text
same source phrase / Candidate-0 context shows same conflict
→ conflict is not created by one target option
```

它本身不是永久 disqualifier。

最终规则：

```text
shared B2 contains any
  written_timing_error / structure_timing_error /
  measurement_ambiguous / unresolved
→ phrase-level blocker remains

all shared B2 semantically resolved benign
+ no other blocker
→ keep phrase_level_target_independent_conflict=true for audit
→ DO NOT add an extra disqualifier solely because it repeated
```

**B. sub-resolution conflict**

当前：

```text
B2_SUBRESOLUTION_S = 15ms
overhang <= 15ms
→ measurement_ambiguous
→ hard blocker
```

如果实现声称该范围低于 detector resolution，就不能同时把它当作可分辨的真实 timing conflict。

建议显式状态：

```text
measurement_below_resolution
```

其语义：

```text
cannot establish a material carrier conflict at current resolution
→ neutral for semantic error claim
→ not by itself a hard review blocker
```

前提仍需：

```text
no contradictory higher-resolution / identity-aware evidence
no legality/ordering violation
no post-loop B1 or other QC blocker
```

典型 regression：

```text
note_0311 替 0.4ms
note_0246/0248 等 7.7ms
```

不能仅因为小于 detector resolution 而永久留在 `measurement_ambiguous`。

##### Required regression matrix

至少新增：

```text
N11. onset peak confirms timing but no identity-bearing second family
     → lyric identity remains unverified; cannot recover eligibility

N12. second identity-aware aligner confirms low-confidence char identity+timing
     → lyric recovery may pass without lowering 0.25

N13. late B2 + same-side second waveform detector only
     → cannot by itself become benign_post_boundary_delay

N14. benign late verdict requires phoneme-aware semantic evidence
     + geometry/neighbor consistency

N15. post-loop B1_cross_option_unstable blocks roster
N16. post-loop B1_detector_relock blocks roster

N17. render-free candidate with no current post-loop evidence
     → cannot be final eligible

N18. phrase-level target-independent flag + all shared B2 benign
     → audit flag remains, no extra phrase-level hard blocker

N19. phrase-level flag + any unresolved/non-benign shared B2
     → remains blocker

N20. < detector-resolution B2 with no stronger contradictory evidence
     → measurement_below_resolution / neutral, not hard semantic error

N21. state rebuilt AFTER final artifact commit
     → git_evidence.complete=true
     → missing_count=0
     → no required uncommitted authority files
```

##### Re-run / acceptance order

修完 G5N.1 后必须重新执行：

```text
1. bump lyric implementation / semantic contract if material behavior changed
2. regenerate affected source evidence / current-contract packages
3. rerun all 21 eligibility inventory
4. require post-loop evidence for every proposed roster item
5. commit artifacts
6. rebuild plan/state AFTER artifact commit
7. verify git_evidence.complete=true
8. run FINAL SHA remote CI
9. maintainer/ChatGPT audit
10. only if honest roster + authority gates pass → user listening
```

允许最终仍为：

```text
0/21 eligible
```

但这个 0 必须来自修正后的 evidence semantics，而不是 gate bug / evidence-type overclaim。

在 G5N.1 关闭前：

```text
DO NOT ask user to listen
DO NOT promote timing corroboration into lyric identity
DO NOT call same-family onset agreement semantic independence
DO NOT ignore post-loop B1
DO NOT permanently block a phrase solely because benign conflicts repeat
DO NOT treat below-resolution displacement as a measurable error
DO NOT freeze M2.5
```

##### G5N.1 实现记录（rlv9，工程 gate 已闭合；identity-evidence claim 经审计降级）

G5N.1 的 roster lifecycle / post-loop B1 / phrase-level / sub-resolution 三类 correctness 缺口已闭合；原 Blocker 1 的“identity-bearing evidence”实现经 maintainer/ChatGPT 审计后被降级为 phoneme-class consistency，因此真正 lyric identity authority 转入 G5N.2。真实 rlv9 inventory 仍为 `0/21 eligible`，且 `n_lyric_recovered=0`，所以当前没有因该语义过声明而误放行 roster：

1. **Lyric identity vs timing corroboration 分离**。`onset_strength_peak_v1` 已正确降级为 `timing_corroboration_only`；`_onset_span_evidence` 只能检查预期 phoneme class 与局部波形的一致性，不能独立识别具体 token identity，因此不得作为最终 identity authority。好消息是 rlv8 的 3 项假恢复（0231/0311/0325）已全部撤销，当前均为 timing corroborated / identity unverified，`n_lyric_recovered=0`，未发生错误放行。
2. **Benign B2 语义独立证据**。新增 `_onset_span_evidence`（独立于 onset detector）：conflict span 的 hf_ratio/mean_db/min_db/periodicity/frication_like/pre_onset_gap/voiced_continuation。`_b2_semantic` 规则：
   - early benign_preutterance 需：obstruent + frication-like span + second family confirms + 邻居一致
   - late benign_post_boundary_delay 需：confirms + 真 pre-onset 低能 gap + 非 voiced continuation + 非 unknown 音素 + 邻居一致
   - voiced continuation / 无 gap / contradicts / unknown → `measurement_ambiguous` 或 `unresolved`，fail-closed
   - `_classify_routes` 改两阶段：先全表分类再算 `prev/next_class_a` 邻居一致性
   真实纠正：rlv8 的 3 个假 benign 全部撤销——`可`/`人`/`我`（0379）pre-onset 持续浊音→`measurement_ambiguous`；`遮`（0044）无真实 pre-onset gap + 前邻也是 B2（系统性偏移非局部延迟）→`measurement_ambiguous`；`却`（0044）second family contradicts→`measurement_ambiguous`。
3. **Post-loop B1 hard gate**。inventory 每项消费 `post_loop_final_class`：任意 `B1_*`（含 `B1_cross_option_unstable`/`B1_detector_relock`/`B1_render_unmeasurable`）→ `unresolved_post_loop_B1:*` disqualifier + `post_loop_gate=b1_block`；无 current-contract post-loop 证据 → `needs_render`，`final_eligible=False`，仅进 `roster_pending_render` 不进 `roster_candidates`；全 class_A + current contract → `verified` 才可 final。
4. **Phrase-level / sub-resolution 生命周期**。`phrase_level_target_independent_conflict` 保留为审计事实；共享 B2 全部 benign 时不再单独阻塞，任一非良性则仍 disqualify。`B2_SUBRESOLUTION_S` 内位移 → `measurement_below_resolution`（neutral，不阻塞）。

真实 rlv9 inventory（21 项）：`n_eligible=0`、`n_lyric_recovered=0`、`n_unresolved_B2=8`、`n_phrase_level=4`、`roster_candidates=[]`、`roster_pending_render=[]`。4 项历史 pilot 已重渲 rlv9（全部 valid，post-loop 语义持久化：`一`→B1_cross_option_unstable、`惜`/`本`→B1_detector_relock）。`plan_invariants.ok=true`、`pilot_authority.ok=false`、`review_ready=false`——未请求试听。

回归：N11–N21（timing-corroboration 非 identity、identity-bearing 恢复、late 同族≠benign、benign 需 phoneme+邻居、post-loop B1×2、verified→final、phrase benign→audit-only、phrase unresolved→阻塞、sub-resolution→neutral、post-loop gate 字段）+ M6/M10b 语义更新。
---

#### G5N.2 Lyric-constrained forced alignment（✅ IMPLEMENTED @ rlv10；语义纠偏后降为 timing/alignment evidence）

G5N.2 的工程实现本身保留：

```text
known lyric sequence
+ separated source vocal
→ MMS_FA CTC forced alignment
→ per-token acoustic span / confidence / provenance
```

rlv10 已完成：

```text
identity_align.py
MMS_FA / pypinyin / source+lyric hashes
21-item inventory rebuild
4 historical pilot package rebuild
404 tests PASS
git_evidence.complete=true
plan_invariants.ok=true
```

但 G5N.2 的旧解释存在一个 contract error：

```text
known token is injected as forced-alignment target
→ aligner finds an acoustic path for that target
!= an independent recognizer identified that Han character
```

因此以下旧语义全部废止为 acceptance authority：

```text
family-B same token
→ identity_verified

family-A + family-B same token
→ independent lexical identity agreement

low Whisper char probability
→ lexical identity unknown
```

rlv10 的 identity_verified、identity_conflict、n_lyric_recovered=1 保留为 historical/audit 字段，**不得直接授权 roster、review 或 repair**。其中 note_0325 “着”的结果应重新解释为：

```text
known lexical token = 着
MMS acoustic alignment found a plausible span
Whisper/MMS start disagreement = 0.176s
→ alignment/timing evidence
→ NOT independent proof that the sung Han character is 着
```

G5N.2 不再追求“第二个认字模型”。Mandarin 同音字本身也不能仅凭声学可靠地区分为具体汉字；对本项目而言，用户提供/正式歌词就是 lexical source of truth。

---

#### G5N.3 Lexical identity authority + alignment timing correction（← CURRENT）

##### Core authority model

新的单一语义：

```text
official / known lyric sequence
→ lexical identity authority

Whisper char alignment
MMS_FA forced alignment
waveform onset / energy
phoneme-class evidence
→ timing / boundary / alignment evidence only
```

前提是 phrase/LRC coverage 已正确绑定。如果 phrase 本身取错歌词行、处于 instrumental/no-lyric 区间、或文本版本不一致，则必须进入 coverage/text-source diagnosis；不得硬套 known lyrics。

##### Low-confidence Whisper semantics

MIN_REVIEW_CHAR_PROB=0.25 不再表示：

```text
prob < 0.25
→ 不知道唱的是哪个字
```

而表示：

```text
prob < 0.25
→ Whisper-derived token timing/boundary is low-confidence
→ this measurement cannot be sole timing authority
```

因此：

```text
known lyric token remains lexically fixed
low ASR probability alone does NOT disqualify lyric identity
```

但如果当前 review/repair 需要精确边界，而 MMS/Whisper/其他 timing evidence 仍无法给出足够可靠的 token span：

```text
alignment_unresolved / measurement_ambiguous
→ fail-closed for timing-sensitive review/repair
```

##### Family roles

Family A：

```text
Whisper-derived char/token alignment
→ candidate timing measurement
→ probability / DTW confidence describes measurement reliability
```

Family B：

```text
MMS_FA lyric-constrained forced alignment
→ independent acoustic timing measurement under the same known token sequence
→ span / CTC score / boundary uncertainty
```

Family A/B 的独立性只允许用于：

```text
timing agreement
boundary agreement
alignment stability
measurement ambiguity
```

不得再称为：

```text
independent lexical identity agreement
token identity verification
same-token recognition agreement
```

##### Required implementation changes

至少完成：

```text
1. rename semantic verdicts
   identity_verified      → alignment_supported / timing_supported
   identity_unverified    → alignment_unresolved
   identity_conflict      → alignment_order_conflict
   measurement_ambiguous  → measurement_ambiguous (保留)

2. lyric gate separation
   lexical_text_status:
     authoritative_known
     coverage_mismatch
     no_lyrics
     text_version_conflict

   alignment_status:
     supported
     ambiguous
     unresolved
     order_conflict

3. eligibility
   lexical identity is NOT failed by Whisper char probability alone
   timing-sensitive eligibility consumes alignment_status
   coverage/text-source uncertainty still fail-closed

4. rlv10 historical fields
   old identity_* fields remain readable for audit
   but current rlv11 authority must not consume them

5. B2 / written-timing
   MMS token boundaries may strengthen carrier/timing adjudication
   but forced alignment does not by itself prove the written score is wrong
   B2 still requires geometry / neighboring timing / structure semantics

6. post-loop
   B1 no_source_landmark must be re-evaluated using the corrected
   known-token + multi-family timing model before remaining a blocker
```

##### Re-evaluate current 21 items

必须重新生成 **rlv11** inventory。不得简单把 rlv10 的 0/21 复制为新结论。

优先复查：

```text
note_0325
  lexical sequence fixed by known lyrics
  old lyric recovery gate removed
  current blocker unresolved_B1:数 / no_source_landmark
  → rerun timing/alignment diagnosis

note_0231 / note_0311
  old family-A/B disagreement
  → measurement_ambiguous
  → diagnose which timing family is wrong / whether structure carrier is wrong
  → do NOT call lexical identity ambiguous merely because timing differs

remaining low-confidence items
  → keep known token identity
  → classify alignment supported / ambiguous / unresolved
```

0391/0404 remain instrumental/no-lyrics coverage cases and must not receive forced lyric tokens.

##### Required regressions

Replace/extend N22–N31 with current semantics:

```text
N32. known lyric + low Whisper probability
     → lexical_text_status=authoritative_known
     → low probability alone cannot fail lexical identity

N33. MMS forced alignment same token target
     → may produce alignment_supported
     → MUST NOT produce independent identity_verified authority

N34. Whisper/MMS boundary agreement within evidence-derived uncertainty
     → timing_supported may pass timing gate

N35. Whisper/MMS timing disagreement beyond uncertainty
     → measurement_ambiguous
     → lexical token remains known

N36. MMS unavailable / low CTC confidence
     → alignment_unresolved
     → no timing authority invented

N37. phrase/LRC coverage mismatch
     → lexical_text_status=coverage_mismatch
     → fail-closed; do not force known token sequence into wrong phrase

N38. instrumental/no-lyrics phrase
     → lexical_text_status=no_lyrics
     → no forced lyric alignment

N39. rlv10 identity_verified historical artifact
     → cannot directly authorize current roster/review/repair

N40. material aligner/model/lexicon/config/source change
     → timing evidence contract/version bump
     → dependent inventory/package/verdict stale

N41. B1 no_source_landmark with usable MMS span
     → re-adjudicate measurability/timing
     → do not preserve B1 solely because the old onset detector missed a landmark
```

##### G5N.3 acceptance

```text
[✓] lexical identity authority explicitly comes from official/known lyric sequence
    (lexical_text_status=authoritative_known whenever lyric chars bound)
[✓] phrase/LRC coverage/text-version mismatch has its own fail-closed state
    (lyric_coverage:no_lyrics|coverage_mismatch → coverage_diagnosis lane)
[✓] forced alignment is documented and implemented as timing/alignment evidence, not independent Han-character recognition
    (ifa2 verdicts: alignment_supported/unresolved/order_conflict/measurement_ambiguous)
[✓] identity_* current authority fields removed/renamed or made historical-only
    (rlv10 identity_* stays readable in old artifacts; ifa2 authority never consumes them)
[✓] low Whisper char probability alone no longer fails lexical identity
    (low prob → timing-measurement problem; lexical stays authoritative_known)
[✓] timing-sensitive gates consume multi-family alignment uncertainty
    (Whisper/MMS agreement within evidence-derived tolerance → supported;
     onset-peak contradiction demotes supported → ambiguous)
[✓] B1 no_source_landmark is re-adjudicated with MMS timing evidence where available
    (N41: b1_readjudicated via mms_fa_token; 0325 数 → revealed B2 late conflict)
[✓] B2 semantics may consume MMS boundaries without treating forced alignment as written-score truth
    (mms_second_family corroborates displacement only when edge unavailable;
     never when MMS is the primary measurement — no circular evidence)
[✓] all 21 candidates regenerated under rlv11
[✓] rlv11 inventory / packages / plan / state committed
[✓] git_evidence.complete == true
[✓] plan_invariants.ok == true
[✓] empty roster honestly preserves all unresolved blockers
[ ] pilot_authority.ok == true before user listening
[ ] review_ready == true before user listening
[ ] FINAL acceptance SHA remote CI success
[✗] maintainer/ChatGPT pre-human audit PASS
    → FAIL: low-confidence Whisper timing still retains veto authority
    → G5N.3 cannot close; superseded by G5N.4
```

If rlv11 still yields zero eligible items:

```text
accept zero as evidence
continue written-timing / structure diagnosis
do not re-introduce lexical-identity gates
do not lower thresholds to manufacture a roster
```

Until G5N.3 closes:

```text
DO NOT ask user to listen
DO NOT add a third ASR/identity model merely to prove known lyrics
DO NOT call lyric-constrained forced alignment independent lexical recognition
DO NOT use low Whisper probability alone as a lyric-identity blocker
DO NOT record calibration decisions
DO NOT freeze M2.5
```

##### G5N.3 实现记录（rlv11，2026-09-19）

**权威模型重写**：known lyric sequence = lexical identity 唯一权威；Whisper/MMS/onset/phoneme-class 全部降为 timing/boundary evidence。

- **verdict 改名（ifa2）**：`identity_verified→alignment_supported`、`identity_unverified→alignment_unresolved`、`identity_conflict→alignment_order_conflict`、`measurement_ambiguous` 保留。rlv10 `identity_*` 字段留在旧 artifacts 可审计，当前 authority 永不消费。
- **双轨 lyric gate**（`_adjudicate_lyric_evidence` 重写）：
  - `lexical_text_status`：`authoritative_known`（chars 已绑定即成立，与 Whisper 概率无关）/ `no_lyrics`（器乐段，诚实永久）/ `coverage_mismatch`（窗口外有 chars，fail-closed）/ `text_version_conflict`（保留）。
  - `alignment_status`：低概率 token 逐字经 family-B 裁决，取最差；第三家族 onset landmark **矛盾**（|dev|>50ms）把 supported 降级为 ambiguous。
  - `timing_supported`（全部低概率 token `alignment_supported`）→ gate 通过进入路由分类——**timing pass，非 identity recovery**。
  - disqualifier：`lyric_coverage:*` → coverage_diagnosis；`alignment_{unresolved,ambiguous,order_conflict}:*` → measurement_diagnosis。
- **B1 重裁决（N41）**：`_classify_routes` 新增 `mms` 参数——onset 漏检但 MMS token 已定位 → `source_ref_kind=mms_fa_token`、`b1_readjudicated=true`，按 MMS span 正常分类（class_A 或 B2）。
- **B2 证据强化（防循环）**：`b2_evidence` 新增 `mms_second_family`/`mms_token_start`/`mms_confidence`——edge 不可用时 MMS 边界可作为第二 timing 家族确认位移；但 MMS 是主测量（b1_readjudicated）时绝不兼作第二家族。
- **真实 rlv11 inventory（21 项）**：`n_eligible=0`、`roster=[]`。
  - `n_lexical_coverage_fail=2`（0391/0404 → `lyric_coverage:no_lyrics`）
  - `n_alignment_fail=10`（低概率 token family-B 与 Whisper 边界分歧 → `alignment_ambiguous:*`）
  - `n_timing_supported=1`（0325 `着` family-B 边界一致 → 歌词 gate 通过）
  - `n_b1_readjudicated=1`（0325 `数`：rlv10 的 `unresolved_B1` 实为 onset 漏检——MMS span 定位在 carrier 后 53.7ms → **真身 B2 late carrier conflict**，`unresolved` semantic）
  - `n_unresolved_B2=9`、`n_phrase_level=4` —— 0 更诚实：每个失败都有语义归因
- 4 项历史 pilot 重渲 rlv11（ifa2 合约）；回归 N22–N31 改名重写 + 新增 N32–N41；414 tests PASS。

---

#### G5N.4 Confidence-aware / anchor-based timing adjudication（← CURRENT）

##### Why rlv11 cannot be accepted

G5N.3 correctly established:

```text
known lyrics
→ lexical identity authority

Whisper / MMS / onset
→ timing evidence only
```

但 rlv11 的实际 timing adjudicator 仍然：

```text
low-confidence Whisper token start
→ 与 MMS start 比较
→ |MMS - Whisper| > tolerance
→ measurement_ambiguous
```

这在语义上仍然给了 low-confidence Whisper **timing veto**。

例如真实 rlv11：

```text
note_0123 是
Whisper p = 0.0000086
MMS-Whisper start delta ≈ 0.516s
→ measurement_ambiguous

note_0311 是
Whisper p = 0.000151
delta ≈ 0.548s
→ measurement_ambiguous

note_0440/0441 密
Whisper p ≈ 0.00195
delta ≈ 0.542s
→ measurement_ambiguous
```

这些 Whisper 概率本身已经说明该 token 的 Whisper timing observation 极不可靠。不能再把它当作一个与 MMS 对等、具有 hard-conflict 权力的 family。

因此：

```text
low-confidence Whisper != timing anchor
low-confidence Whisper != contradiction authority
low-confidence Whisper != veto
```

##### Timing evidence authority classes

每个 timing observation 必须显式带 reliability/authority class：

```text
A. anchor_authoritative
   - high-confidence Whisper token with stable DTW/boundary
   - validated high-confidence neighboring token anchor
   - other independently calibrated high-reliability boundary family

B. measurement_support
   - MMS constrained forced-alignment token with sufficient CTC confidence
   - reliable onset / energy / phoneme boundary
   - local interpolation constrained by high-confidence anchors

C. audit_only
   - low-confidence Whisper token timing
   - detector output below its calibrated reliability region
   - historical rlv10/rlv11 timing claims without current authority

D. unavailable
   - missing / low-confidence / unalignable evidence
```

只有 A/B 中达到当前 contract 要求的 evidence 才能参与 pass/conflict。C 只能记录，不能产生 hard blocker。

##### Confidence-aware family-A semantics

Whisper token 不再统一叫 family-A authority。

必须按 token confidence 分层：

```text
Whisper probability >= calibrated anchor threshold
+ sequence/DTW sanity passes
→ whisper_anchor
→ may participate in agreement/conflict

Whisper probability < anchor threshold
→ whisper_audit_only
→ MAY NOT create measurement_ambiguous
→ MAY NOT demote MMS-supported timing
```

**禁止简单把现有 0.25 threshold 改成另一个拍脑袋 threshold。** anchor threshold / reliability rule 必须通过当前数据或 calibration evidence 定义，并与“review char probability threshold”解耦。

##### Anchor-based timing for low-confidence tokens

对于：

```text
high-confidence token L
low-confidence token X
high-confidence token R
```

允许构造局部 timing envelope：

```text
L/R reliable anchors
+ known lexical order
+ monotonicity
+ legal token span
+ MMS X span/confidence
+ optional onset/energy evidence
→ timing envelope for X
```

X 不需要接近它自己的 low-confidence Whisper start。

可支持的判定：

```text
MMS X lies monotonically between reliable neighboring anchors
+ MMS confidence sufficient
+ token duration/span physically valid
+ no reliable acoustic family contradicts
→ timing_supported
```

真正的 ambiguity 必须来自**可靠 evidence 之间**的冲突，例如：

```text
MMS vs reliable onset conflict
MMS vs high-confidence neighbor-derived legal envelope conflict
two calibrated high-reliability timing families disagree
token order / coverage impossible
MMS confidence itself insufficient
```

不得来自：

```text
MMS != low-confidence Whisper
onset != low-confidence Whisper
```

##### Onset / energy semantics correction

rlv11 当前：

```text
onset_ref - low_confidence_whisper_start > 50ms
→ landmark_contradicted
→ ambiguous
```

也必须废止。

新的判断：

```text
if Whisper token is anchor_authoritative:
    onset may corroborate / contradict Whisper
else:
    compare onset against MMS / anchor-derived envelope / other reliable timing
    low-confidence Whisper is audit-only
```

50ms 或其他窗口只允许作为 detector-specific calibrated resolution/uncertainty，不能作为围绕不可靠 Whisper start 的 universal truth。

##### MMS authority limits

G5N.4 不是把 MMS 升级为唯一 truth。

MMS 仍然是：

```text
known-token constrained acoustic timing measurement
```

它必须 fail-closed when：

```text
CTC confidence insufficient
token span invalid
order/monotonicity broken
coverage/text binding suspect
neighbor anchors make the span impossible
reliable independent acoustic timing materially contradicts it
```

MMS 不得单独证明：

```text
written score is wrong
B2 is a true structure error
split/merge should be applied
```

##### rlv12 required artifact model

每个低置信 token 至少持久化：

```text
lexical_text_status

whisper:
  probability
  timing
  authority = anchor | support | audit_only | unavailable
  authority_reason

mms:
  start/end
  confidence
  authority
  authority_reason

acoustic_landmarks:
  onset/energy/phoneme-boundary
  timing
  reliability
  resolution

neighbor_anchors:
  prev/next token
  timing
  confidence
  authority

timing_envelope:
  lo/hi
  source
  uncertainty

timing_verdict:
  supported
  ambiguous
  unresolved
  order_conflict

supporting_families
contradicting_families
audit_only_observations
```

任何 final timing verdict 必须能从这些 authority-tagged evidence 重建，禁止继续用 raw `dev_start_s` 单字段隐式决定。

##### Required real-case re-evaluation

rlv12 必须重点覆盖当前 10 个 alignment fail：

```text
0076 / 0077
0123
0231
0264 / 0266
0305
0311
0440 / 0441
```

特别检查：

```text
0123 是    p≈0.0000086
0311 是    p≈0.000151
0440 密    p≈0.00195
```

这些 case 不允许再仅因 MMS 与 Whisper start 相差约 0.5s 就 hard-fail。

同时保留：

```text
0325 着
→ 已有 timing support
→ regression: G5N.4 不得退化

0325 数
→ B1→B2 re-adjudication 逻辑保留
→ 但其 B2 semantic 仍需独立 written-timing/structure evidence
```

##### Required regressions N42–N53

```text
N42. very-low-confidence Whisper + good MMS + valid neighbor envelope
     → timing_supported
     → Whisper mismatch is audit-only

N43. very-low-confidence Whisper + MMS differs by >500ms
     + no reliable contradiction
     → MUST NOT become ambiguous solely from Whisper delta

N44. high-confidence calibrated Whisper anchor + good MMS agreement
     → timing_supported with two-family support

N45. high-confidence calibrated Whisper anchor vs MMS material disagreement
     → measurement_ambiguous

N46. low-confidence Whisper + reliable onset agrees MMS
     → timing_supported

N47. low-confidence Whisper + reliable onset contradicts MMS
     → measurement_ambiguous

N48. low-confidence Whisper + onset differs from Whisper only
     → Whisper cannot turn onset into contradiction

N49. MMS low confidence / skipped
     → unresolved unless another sufficient reliable timing family exists

N50. MMS violates reliable prev/next monotonic envelope
     → order_conflict / ambiguous fail-closed

N51. no reliable neighboring anchors
     → do not invent interpolation confidence
     → use available calibrated families or unresolved

N52. historical rlv11 alignment_ambiguous caused only by low-confidence Whisper delta
     → stale under rlv12 contract

N53. timing verdict audit records authority classes + supporting/contradicting families
     → verdict reconstructable from artifact
```

##### G5N.4 acceptance

```text
[✓] low-confidence Whisper timing is audit-only and has no veto authority
[✓] high-confidence Whisper timing anchor has explicit calibrated authority rule
    (WHISPER_ANCHOR_PROB=0.5 majority rule in the observed bimodal gap)
[✓] review-char confidence and timing-anchor confidence are separate semantics
[✓] onset/energy contradiction logic no longer references low-confidence Whisper as truth
[✓] low-confidence tokens can be timed from MMS + reliable neighbors/acoustic evidence
[✓] anchor-derived timing envelope is monotonic and uncertainty-aware
[✓] MMS remains constrained timing evidence, not single-source truth
[✓] reliable-family conflict remains fail-closed
[✓] N42–N53 regression matrix green
[✓] all 21 candidates regenerated under rlv12
[✓] all 10 rlv11 alignment_fail cases explicitly re-evaluated
[✓] rlv11-only timing verdicts marked stale under rlv12 (impl bump rlv12)
[✓] affected packages rebuilt under rlv12 contract
[✓] state/plan rebuilt after final artifact commit
[✓] git_evidence.complete == true
[✓] plan_invariants.ok == true
[ ] pilot_authority.ok == true before user listening
[ ] review_ready == true before user listening
[ ] FINAL acceptance SHA remote CI success
[✗] maintainer/ChatGPT pre-human audit PASS
    → FAIL: constrained Whisper target probability was promoted to boundary authority via p>=0.5
    → FAIL: high-anchor item-level conflicts are not fully reconstructable as authority-tagged token evidence
    → FAIL: onset peaks may support Whisper/MMS before token-bound monotonic one-to-one assignment
    → G5N.4 low-confidence-veto fix is retained, but closure is superseded by G5N.5
```

If rlv12 still yields zero eligible items:

```text
then zero may be accepted only after confirming
no item is blocked solely by audit_only Whisper timing

remaining blockers must be attributable to:
coverage/text mismatch
reliable measurement conflict
written-timing evidence
structure evidence
post-loop B1/B2/QC
```

Until G5N.4 closes:

```text
DO NOT ask user to listen
DO NOT treat low-confidence Whisper timing as a conflict authority
DO NOT widen tolerances to make MMS agree with Whisper
DO NOT make MMS unconditional timing truth
DO NOT start bulk written-score repair from rlv11 0/21
DO NOT record calibration decisions
DO NOT freeze M2.5
```

##### G5N.4 implementation record (rlv12)

- Timing authority classes implemented in
  `structure_calibration._adjudicate_lyric_evidence`:
  `anchor` (Whisper prob ≥ WHISPER_ANCHOR_PROB=0.5 — majority-rule
  threshold sitting in the observed bimodal gap, decoupled from
  MIN_REVIEW_CHAR_PROB), `measurement_support` (aligned MMS token /
  reliable onset landmark / anchor-derived envelope),
  `audit_only` (low-confidence Whisper timing — recorded in
  `audit_only_observations`, can never veto or demote), `unavailable`.
- Low-confidence token verdict: MMS span inside the anchor-derived
  monotonic envelope (ENVELOPE_SLACK_S boundary smear) + no reliable
  onset contradiction (|onset − MMS.start| ≤ MMS_ONSET_AGREE_S=0.12s,
  the sung-consonant lead-in + detector-hop bound) → `supported`;
  envelope violation → `order_conflict`; reliable onset vs MMS
  contradiction → `ambiguous`; MMS unavailable + onset inside
  envelope → `supported` (onset is itself a calibrated family);
  no reliable family → `unresolved`. Anchor-level A/B conflicts
  (`alignment_adjudicate` verdicts on anchor chars) feed the item
  status — reliable-family conflicts stay fail-closed.
- Per-token artifact model persisted: `whisper{prob,start,end,
  authority,authority_reason}` / `mms{start,end,confidence,authority,
  reason}` / `acoustic_landmarks{kind,time,dev_vs_mms,reliability,
  resolution}` / `neighbor_anchors` / `timing_envelope{lo,hi,sources,
  uncertainty}` / `timing_verdict{+reason}` / `supporting_families` /
  `contradicting_families` / `audit_only_observations` — verdicts are
  reconstructable from the artifact alone (N53).
- Regressions N42–N53 (12 tests): low-conf Whisper has no veto,
  >500ms MMS-vs-Whisper deltas are audit-only, anchor-vs-MMS conflict
  → ambiguous, onset-vs-MMS agree/contradict paths, MMS-unavailable
  onset sufficiency, envelope order conflict, no invented
  interpolation without anchors, rlv11 stale verdicts, artifact
  reconstructability.

#### G5N.5 Boundary-stability + token-bound landmark assignment（← CURRENT）

##### Why rlv12 still cannot be accepted

G5N.4 successfully fixed:

```text
low-confidence Whisper
→ audit_only
→ no timing veto
```

真实结果证明修复有效：

```text
rlv11:
  n_timing_supported = 1
  n_alignment_fail   = 10

rlv12:
  n_timing_supported = 6
  n_alignment_fail   = 5
```

但剩余 5 个 alignment fail 的 low-confidence token 本身已经全部：

```text
timing_verdict = supported
contradicting_families = []
```

item-level `alignment_status=ambiguous` 来自同句其他 token 的所谓 high-confidence Whisper anchor 与 MMS 冲突。

rlv12 当前近似等价于：

```text
Whisper target probability >= 0.5
→ boundary anchor
→ may veto MMS
```

这是新的 contract error。

##### Whisper probability is NOT boundary confidence

当前 source-bound Whisper alignment 使用：

```text
known lyric text
→ tokenizer.encode(text)
→ faster-whisper find_alignment(...)
→ target token probabilities + attention/DTW boundaries
```

因此 probability 是**在已知 target sequence 条件下的 token acoustic compatibility / token probability signal**，不是：

```text
P(this Han character identity is correct)
P(this start timestamp is correct)
P(this boundary is stable)
```

而且多汉字 word 会：

```text
one word span
→ _char_spans(...)
→ evenly split across Hanzi
→ same word probability copied to each char
```

所以以下规则必须废止：

```text
p >= 0.5
→ reliable char boundary anchor
```

也禁止把阈值简单改成 0.4 / 0.6 / 0.8。

Whisper probability 可以保留为：

```text
token acoustic-quality / alignment-quality feature
```

但 **boundary authority 必须由 boundary stability 自己证明。**

##### Perturbation-based Whisper boundary stability

对候选 Whisper timing anchor，必须在同一 source vocal / same known lyric sequence 下生成多个合法 alignment contexts，例如：

```text
base line/phrase window
left-context-expanded window
right-context-expanded window
symmetric expanded window
shifted crop where lyric coverage remains exact
```

不得通过改变歌词内容、token 顺序或偷偷选择最有利的窗口制造稳定性。

每个 token 持久化：

```text
whisper_boundary_stability:
  contexts[]
    context_id
    source_start/end
    lyric_token_index
    start/end
    probability
    valid
    failure_reason

  start_median
  end_median
  start_jitter
  end_jitter
  span_jitter
  n_valid
  stability_status:
    stable
    unstable
    insufficient
```

authority 规则变成：

```text
probability alone
→ NEVER anchor

boundary stability passes evidence-derived criterion
+ token order/coverage remains valid
→ whisper_boundary_measurement may become timing support/anchor family

unstable / insufficient
→ audit_only or unavailable
```

stability criterion 必须 evidence-derived，并持久化其依据；禁止为让当前 5 个 case 通过而手调阈值。

**同一个 Whisper 模型在多个 crop/context 下仍属于一个 measurement family。**
多窗口只证明该 family 内部 boundary stability，不能被计成多个独立 family votes。

##### Token-bound onset / energy assignment

当前 high-anchor conflict path 会在 Whisper boundary 与 MMS boundary 附近分别搜索 onset peak。

这存在歧义：

```text
peak A near Whisper candidate
peak B near MMS candidate
```

如果 A/B 实际属于相邻 token / consonant / phrase event，则不能据此宣称：

```text
same token has two reliable timing families in conflict
```

因此任何 onset/energy peak 在参与 token support/contradiction **之前**必须先完成 token binding。

至少要求：

```text
known lyric token order
+ MMS spans
+ boundary-stable Whisper spans where available
+ phoneme/onset plausibility where available
+ monotonic sequence constraint
→ token ↔ acoustic-landmark assignment
```

assignment contract：

```text
each landmark peak binds to at most one token
each token receives at most one primary onset landmark
unmatched token is allowed
unmatched peak is allowed
assignment must be monotonic in token order
no peak may simultaneously corroborate different token boundaries
no nearest-peak reuse across neighboring tokens
```

推荐实现为 deterministic monotonic DP / bipartite sequence assignment，而不是逐 token 独立 nearest-peak。

assignment cost/authority 至少考虑：

```text
distance to MMS token span/start
distance to stable Whisper boundary if available
token-order legality
minimum inter-token spacing
phoneme-class onset plausibility (diagnostic/support, not lexical identity)
detector edge/blind-zone reliability
```

##### High-anchor conflict semantics

只有先完成：

```text
1. Whisper boundary stability adjudication
2. token-bound landmark assignment
```

之后才允许建立：

```text
whisper_boundary vs MMS
whisper_boundary vs assigned onset
MMS vs assigned onset
```

真正的 hard ambiguity 必须满足：

```text
two or more CURRENT reliable timing families
are bound to the SAME token
and materially disagree beyond evidence-derived uncertainty
```

不得再由：

```text
p >= 0.5 alone
or
two different nearby unbound onset peaks
```

产生 hard blocker。

##### rlv12 cases requiring exact re-audit

rlv13 必须优先重审当前 5 个 item：

```text
note_0231
  low token 春: already timing_supported
  current item blocker originates from other anchor conflict
  especially 却 (rlv12 Whisper/MMS delta only slightly above old tolerance)
  → audit boundary stability + token-bound onset assignment

note_0305
  low token 也: already timing_supported via onset/envelope
  actual p>=0.5 anchor blocker includes 安
  → do not rely on narrative claiming 得 as an anchor when p<0.5
  → machine-generate exact active-anchor list

note_0325
  low token 着: already timing_supported
  current item blocker includes 一
  → audit 一 boundary stability / assigned onset before ambiguity

note_0440 / note_0441
  low tokens 密/麻/自: timing_supported
  current hard anchor includes 的
  → 自/尊 must not be described as p>=0.5 anchors when they are not
  → audit 的 boundary stability + token-bound landmark
```

G5N.5 不得重新把已通过的 low-confidence tokens 变回 Whisper-delta blockers。

##### Full verdict reconstructability

rlv12 N53 只证明 low-token supported artifact 可重建，不足以证明 item-level high-anchor ambiguity 可重建。

rlv13 每个 item-level timing blocker 必须持久化：

```text
anchor_conflicts[]
  token_index
  char

  whisper:
    probability
    boundary
    boundary_stability
    authority
    authority_reason

  mms:
    span
    confidence
    authority

  assigned_landmark:
    landmark_id
    time
    detector
    assignment_cost
    assignment_reason
    reliability

  support
  contradiction
  uncertainty
  final_verdict
  final_reason
```

必须满足：

```text
item alignment_status
= deterministic reduction of persisted per-token verdicts

no hidden transient peak search
no unpersisted anchor demotion/conflict
no commit-message-only explanation
```

##### Required regressions N54–N67

```text
N54. constrained Whisper p>=0.5 alone
     → MUST NOT grant boundary anchor authority

N55. same token stable across valid crop/context perturbations
     → whisper boundary stability = stable
     → may become one timing family

N56. same token high probability but large boundary jitter
     → unstable
     → audit_only; cannot veto MMS

N57. same token low/moderate probability but boundary-stable
     → probability alone does not disqualify timing stability
     → authority decided by explicit stability contract

N58. multi-context Whisper runs
     → count as ONE family, never N independent votes

N59. onset assignment is monotonic one-to-one
     → one peak cannot bind two neighboring tokens

N60. two nearby peaks corresponding to adjacent tokens
     → cannot fabricate same-token Whisper-vs-MMS contradiction

N61. no plausible peak for token
     → unmatched allowed
     → no fake onset authority invented

N62. detector blind-zone / edge peak
     → cannot become authoritative assignment

N63. stable Whisper + assigned onset agree, MMS conflicts
     → genuine reliable-family ambiguity may fail-closed

N64. unstable Whisper + assigned onset agrees MMS
     → Whisper cannot preserve item-level ambiguity

N65. 0231/0305/0325/0440/0441
     → exact active blocker token list generated from artifacts
     → commit narrative cannot substitute for machine evidence

N66. item-level ambiguous verdict
     → persisted anchor_conflicts[] identifies same-token families,
       measurements, uncertainty and reason

N67. final alignment_status reconstructs exactly from persisted
     low-token verdicts + anchor_conflicts[]
```

##### G5N.5 acceptance

```text
[✓] WHISPER_ANCHOR_PROB no longer grants boundary authority by itself
[✓] probability and boundary stability are separate persisted fields
[✓] Whisper boundary stability is measured under multiple valid alignment contexts
[✓] stability criterion is evidence-derived and provenance-bound
[✓] multi-context Whisper remains one measurement family
[✓] onset/energy landmarks are assigned to tokens before support/conflict
[✓] landmark assignment is monotonic one-to-one with unmatched allowed
[✓] no acoustic peak may corroborate two token identities/boundaries
[✓] high-anchor conflicts require same-token reliable-family disagreement
[✓] anchor_conflicts[] makes every item-level ambiguity reconstructable
[✓] N54–N67 regression matrix green
[✓] 0231 / 0305 / 0325 / 0440 / 0441 explicitly re-audited
[✓] all 21 candidates regenerated under rlv13
[✓] rlv12 p>=0.5 anchor verdicts marked stale under rlv13
[✓] affected packages rebuilt under rlv13 contract
[ ] state/plan rebuilt after final artifact commit
[ ] git_evidence.complete == true
[ ] plan_invariants.ok == true
[✓] no item remains blocked solely by raw Whisper probability or unbound peaks
[ ] pilot_authority.ok == true before user listening
[ ] review_ready == true before user listening
[ ] FINAL acceptance SHA remote CI success
[ ] maintainer/ChatGPT pre-human audit PASS
```

If rlv13 still yields zero eligible items:

```text
zero may be accepted only if every remaining timing blocker is
reconstructably bound to the same token and supported by
current reliable evidence families

only then may work proceed to bulk written-timing / structure diagnosis
```

Until G5N.5 closes:

```text
DO NOT ask user to listen
DO NOT use Whisper target probability as boundary confidence
DO NOT tune 0.5 to another arbitrary probability threshold
DO NOT count crop perturbations as independent families
DO NOT use unbound onset peaks as token conflict evidence
DO NOT start bulk written-score repair from rlv12 0/21
DO NOT record calibration decisions
DO NOT freeze M2.5
```

#### G5N.5 implementation record（rlv13, CURRENT）

```text
code:
  identity_align.whisper_boundary_stability(vocals, text, s0, s1, n)
    — SAME constrained Whisper alignment re-run under 5 legal context
    pads ((0.45,0.45),(0.30,0.55),(0.55,0.30),(0.65,0.40),(0.35,0.60))
    on the SAME separated vocal with the SAME known lyric sequence;
    per-token start/end medians + jitter + n_valid + status
    (stable|unstable|insufficient); contexts[] persisted with
    source windows + failure reasons; ONE measurement family;
    criterion: n_valid>=3 AND start/end jitter<=0.12s (the same
    cross-family agreement bound as MMS↔onset — evidence-derived,
    never tuned per case; observed bimodal: stable ~0.01-0.07s,
    unstable ~0.45s+)
  structure_calibration._assign_onsets(refs, peaks)
    — deterministic monotonic one-to-one DP: each peak binds ≤1
    token, each token ≤1 primary onset, unmatched allowed on both
    sides; refs = MMS start | stable-Whisper start | envelope
    midpoint | raw-whisper-position weak prior (location prior only,
    never authority); a legal match always beats unmatched, ties
    prefer nearer peak
  _adjudicate_lyric_evidence rewritten to per-token reliable-family
    adjudication: fams = boundary-STABLE whisper + aligned MMS +
    token-bound reliable onset (edge-blind peaks excluded);
    pairwise disagreement → ambiguous (all conflict pairs persisted);
    reliable span breaking the neighbour envelope → order_conflict;
    no reliable family → unresolved; audit_only observations keep
    non-stable whisper-vs-mms deltas without veto power
  persisted artifacts per token: whisper{probability, stability,
    jitter, authority, authority_reason}, mms{start,end,confidence,
    authority}, assigned_landmark{id,time,cost,reason,reliability},
    family_measurements[], neighbor_anchors, timing_envelope,
    timing_verdict(+reason), supporting/contradicting_families,
    audit_only_observations; item: token_verdicts, onset_assignment
    (peaks+assign+costs+refs+rule), whisper_stability doc,
    anchor_conflicts[{token,families,measurements,uncertainty,reason}]
  item alignment_status = deterministic reduction over persisted
    token verdicts — every blocker reconstructable from artifacts
  WHISPER_ANCHOR_PROB retired (kept for stale-artifact readability)
  contract bump rlv12→rlv13 — all rlv12 p>=0.5 anchor verdicts stale
tests: N54–N67 (14 new) + rlv13 semantic updates to N8/N11/N22/N25/
    N26/N27/N28/N29/N35/N36/N42/N44/N45b/N46/N48/N49/N52 — 441 pass
real-machine rlv13 rescan (21 items):
  n_timing_supported 0→4 (0264/0266/0440/0441 lyric gate pass),
  n_alignment_fail 7, n_lexical_coverage_fail 2, n_unresolved_B2 10,
  n_phrase_level 6 — every remaining timing blocker reconstructs to
  same-token reliable-family disagreement via anchor_conflicts[]
  (MMS-vs-bound-onset |dev|>0.12s or bound onset breaking the
  neighbour envelope); no audit-only Whisper veto remains
  priority re-audit: 0440/0441 supported (roster), 0231/0305
    order_conflict, 0325 ambiguous — all honest same-token conflicts
  build_calibration consumes the adjudication artifact for the
    low-confidence gate (ev["chars"]=None no longer hard-aborts);
    lyric_evidence.chars serializes the adjudicated known-lyric
    sequence + articulation uses it too
  packages rebuilt under rlv13: 0440/0441 + 0061/0188/0192/0379 —
    all package_state=valid, closed-loop/QC flags recorded honestly
    (not_converged / carrier_conflict / intelligibility_low)
roster: [note_0440, note_0441] — first real current-contract
  post-loop-verified roster; roster_size_ok=False (<3) and
  signal_qc.auto_review_ready=False on the packages → review surface
  NOT emitted; pilot_authority.ok=false; review_ready=false
```

### 10.1.7 M2.5 CURRENT final acceptance gate

> Historical G/G5A→G5M checklists and implementation narratives are archived in `docs/plan2_history.md`. This section is the single active M2.5 acceptance authority.

M2.5 may move from QUALITY HOLD to FROZEN only when all of the following are true:

```text
A. Engine / frozen safety
   [✓] structure plan/apply engine exists
   [✓] Candidate-0 immutable
   [✓] plan_hash / authority freshness fail-closed
   [✓] split / merge / boundary-shift are operation-specific
   [✓] merge requires index + temporal adjacency
   [✓] rollback / conflict / idempotency remain green
   [✓] 189s / 202s permanent safety green

B. G5N.5 boundary authority
   [✓] known lyric sequence remains lexical identity authority
   [✓] low-confidence Whisper timing remains audit-only under rlv12
   [✓] constrained Whisper probability is separated from boundary confidence
   [✓] no probability threshold alone grants timing-anchor authority
   [✓] boundary stability is measured across valid context/crop perturbations
   [✓] perturbation runs remain one Whisper family
   [✓] stable/unstable/insufficient boundary status persisted per token
   [✓] stability rule is evidence-derived and provenance-bound
   [✓] all rlv12 p>=0.5 anchor verdicts invalidated/re-evaluated under rlv13

C. G5N.5 token-bound acoustic timing / B2 routing
   [✓] B2 remains separate from lexical identity
   [✓] MMS remains constrained timing evidence, not single-source truth
   [✓] onset/energy landmarks are token-bound before support/contradiction
   [✓] landmark assignment is monotonic one-to-one
   [✓] unmatched token/peak is allowed; no evidence is invented
   [✓] one peak cannot support multiple neighboring tokens
   [✓] high-anchor ambiguity requires reliable evidence bound to the same token
   [✓] anchor_conflicts[] persists all item-level conflict evidence
   [✓] item alignment_status reconstructs from persisted per-token evidence
   [✓] B2 consumes only rlv13 current-authority timing evidence
   [✓] measurement_ambiguous / unresolved remain fail-closed

D. Honest pilot roster
   [✓] all 21 candidates rerun under rlv13
   [✓] rlv12 inventory committed/auditable but superseded for anchor authority
   [✓] 0231 / 0305 / 0325 / 0440 / 0441 re-audited under rlv13
   [✓] roster contains only semantically resolved reviewable items (empty remains allowed)
   [✓] no unresolved pre-loop OR post-loop B1/B2/alignment/coverage blocker in roster
   [✓] every proposed roster item has rlv13 current-contract render/post-loop evidence
   [✓] pilot size evidence-driven; do not lower gates to fill count

E. Exact review authority
   [ ] rlv13 state/plan are rebuilt after the final artifact commit
   [✓] selected packages rebuilt under rlv13 if semantics/contract changed
   [✓] verify_package PASS for every selected item
   [ ] signal_qc.auto_review_ready true for every selected item
   [ ] pilot payload binds exact committed bytes/hashes
   [ ] exact-sample QC verdict binds the same roster and contract
   [ ] pilot_authority.ok == true
   [ ] review_ready == true
   [ ] git_evidence.complete == true
   [ ] plan_invariants.ok == true

F. Final remote gate
   [ ] FINAL acceptance SHA has GitHub Actions workflow
   [ ] core pytest job success
   [ ] no skipped/disabled core regression used as fake green
   [ ] maintainer/ChatGPT pre-human audit PASS
```

Only after all gates above pass:

```text
→ expose SOURCE/A/B to user
→ record human calibration decisions
→ use human-confirmed structure repairs
→ freeze M2.5
```

If revised G5N still yields zero eligible items:

```text
review_ready stays false
continue upstream diagnosis
do not relax thresholds or reinterpret unresolved evidence as PASS
```

---

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

## 10.7 Active-plan authority / history

`plan2.md` is the current executable specification.

`docs/plan2_history.md` contains superseded implementation logs, historical blocker text, old acceptance snapshots, and commit/CI narratives.

Authority order:

```text
current plan2.md contract
> current machine-readable Git artifacts/state
> docs/plan2_history.md historical narrative
```

When historical text conflicts with this file, this file wins unless a newer machine-readable artifact proves the active plan itself is stale.

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
### M2.5 — PROBABLE structure repair — ← QUALITY HOLD / G5N.5（rlv12 已消除 low-confidence Whisper timing veto：timing_supported 1→6、alignment_fail 10→5；但 p>=0.5 被错误当作 boundary anchor，且 onset peaks 尚未 token-bound 一对一分配。需 rlv13 boundary-stability + landmark-assignment 重扫；rlv12 的 0/21 仍不能作为 bulk written-timing/structure 最终结论）
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
73. 远程审核采用 honest pilot-first；目标通常 3–5 项，但数量不得凌驾于证据质量。unresolved B1/B2、phrase-level carrier conflict、歌词/响度/非 target 污染或仍不可判断的样本必须退出/替换，不得为凑数量放宽 gate，也不得强迫用户完成 21 项。
74. 在质量失败的 review package 上产生的 A/B 偏好只能记为 diagnostic preference，不得成为 official decision 或 repair authority。
75. 先“唱对”，再做泠鸢风格。
76. rlv7/current-contract 的正式 human pilot 只能由 current artifact evidence 证明可测、可审；历史 pilot 身份没有保留权。最终 roster 必须使 `pilot_authority.ok=true`、`review_ready=true`，并在 FINAL acceptance SHA 上取得 remote CI success 后才允许用户试听。
77. B2 carrier conflict 只表示 source acoustic landmark 越出 legal carrier range；不得自动等同于 written-score error。最终语义必须消费 direction + phoneme/context + independent acoustic evidence；phrase-level 重复 target 只证明 target-independence，不得当作第二份独立 written-error 证据。
78. 禁止为了凑 pilot 单纯降低 `MIN_REVIEW_CHAR_PROB`；但该阈值只表示 Whisper timing/alignment measurement confidence，不得再被解释为 known lyric 的 lexical identity confidence。
79. waveform onset/energy detector 只能 corroborate acoustic timing；official/known lyric sequence 提供 lexical identity，声学 detector 不负责把低置信 Whisper char“升级”为某个汉字。
80. honest-roster eligibility 必须消费 current-contract post-loop final_class；任何 `B1_*` unresolved subtype 都必须 hard-block，不能只看 pre-loop route。
81. `phrase_level_target_independent_conflict` 是 audit/routing fact，不是永久 blocker；shared conflicts 全部被独立证据裁决为 benign 后，不得因“重复出现”再次单独阻塞。
82. 如果定义某 timing displacement 低于 detector resolution，则该 displacement 本身必须 neutral / below-resolution，不能同时作为 measurable semantic error 的 hard blocker。
83. `_onset_span_evidence`、hf_ratio、periodicity、frication/gap 等 waveform-class feature 只能提供 acoustic/phoneme-class consistency；不得单独声明 char/syllable/phoneme token identity verified。
84. lyric-constrained forced alignment 的 token identity 来自已知 target sequence；它可以提供独立 acoustic timing/boundary measurement，但不得被称为对该 Han character 的独立 recognition/identity verification。
85. alignment model/lexicon/config/source/lyric provenance 发生 material change 时必须 version/contract bump，并使依赖该 timing/alignment evidence 的 inventory/package/verdict stale。
86. 只要 phrase/LRC/text-version coverage 已确认正确，known lyric token 的 lexical identity 不得因单个 ASR char probability 低而失效；真正需要 fail-closed 的是 coverage/text conflict 或 timing-sensitive decision 所需的 alignment evidence 仍 unresolved。
87. low-confidence Whisper token timing 只能作为 audit observation；不得因其与 MMS/onset/其他可靠 timing family 不一致而单独制造 measurement_ambiguous 或 hard blocker。
88. timing conflict 只能由具有当前 calibrated authority 的独立 measurement families 建立；evidence reliability 必须先于 agreement/disagreement 计算。
89. 对低置信 token，允许由 **boundary-stable** 邻字 timing anchor + lexical monotonic order + MMS/acoustic timing 构造 uncertainty-aware timing envelope；不得仅凭邻字 Whisper probability 较高就授予 anchor authority，也不得强迫当前 token 贴合自身低置信 Whisper start。
90. MMS forced alignment 不是 timing truth；CTC 低置信、顺序违法、coverage 错配、可靠独立 timing evidence 冲突时必须 fail-closed。
91. constrained Whisper target probability 是 token/alignment quality feature，不是 boundary confidence；任何固定 probability threshold 都不得单独授予 timing-anchor authority。
92. Whisper boundary authority 必须通过合法 context/crop perturbation 下的 boundary stability 证明；多次同模型 perturbation 只属于一个 Whisper measurement family，不得重复计票。
93. onset/energy peak 在参与 token support/conflict 前必须完成 monotonic one-to-one token assignment；未绑定 peak 只能是 audit evidence。
94. 一个 acoustic landmark 最多绑定一个 token；token/peak 均允许 unmatched，禁止 nearest-peak reuse 或为了凑证据强制匹配。
95. hard timing conflict 必须是 CURRENT reliable families 对 **同一 token** 的 bound measurements 发生 material disagreement；相邻 token 的不同 peaks 不得伪造成同-token conflict。
96. item-level alignment verdict 必须可从 committed per-token evidence + anchor_conflicts[] 完整重建；隐藏 transient search、仅 commit message 解释、只持久化 low-token 路径均不构成 acceptance evidence。
