# agent2utau — Plan 2：GAME 主转谱 + 自动证据裁决 + Phrase-Level 审核

> 修订日期：2026-09-19
>
> 核心原则：**先把 written score 唱对，再做泠鸢演唱风格。**
>
> 当前阶段：**M2.5 HUMAN REVIEW PILOT = QUALITY HOLD（G5N.1/rlv9 correctness patch 已实现并通过回归；CURRENT blocker = honest roster 为空——需上游 written-timing/structure 裁决或第三独立测量族）。** rlv9 已完成 21 项重扫：onset-peak 降级为 timing-corroboration（3 项 rlv8 假 lyric 恢复全部撤销）、`_onset_span_evidence` 独立语义族接入 `_b2_semantic`（rlv8 的 3 个假 benign 全部回退 ambiguous/unresolved）、post-loop `B1_*` 全部进 hard gate、phrase-level 改为审计事实 + sub-resolution 判 neutral。真实 rlv9 inventory 仍为 `0/21 eligible`——但该 0 来自修正后的 evidence semantics 而非 gate bug；`n_lyric_recovered=0`、`roster_candidates=[]`、`plan_invariants.ok=true`、`pilot_authority.ok=false`、`review_ready=false`。下一步在上游：对已确认 `written_timing_error` 的字（如 `圆`）走书面裁决，或对 ambiguous/unresolved 项补第三独立测量族；roster≥3 前禁止用户试听、禁止记录 calibration decision、禁止 M2.5 freeze。

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

#### G5N.1 Correctness patch（当前唯一 blocker）

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

##### G5N.1 实现记录（rlv9，2026-09-20）

四个 correctness 缺口全部按规则修复；真实 rlv9 inventory 仍为 `0/21 eligible`，但该 0 现在来自修正后的 evidence semantics：

1. **Lyric identity vs timing corroboration 分离**。`_adjudicate_lyric_evidence` 中 `onset_strength_peak_v1` 降级为 `timing_corroboration_only`；恢复额外要求每个低概率字有 identity-bearing 证据（`_onset_span_evidence` 的音素类一致：obstruent→frication_like，sonorant/glide→voiced onset），不满足输出 `timing_corroborated_identity_unverified` 且 `recovered=False`。`MIN_REVIEW_CHAR_PROB=0.25` 未动。真实结果：rlv8 的 3 项"恢复"（0231/0311/0325）全部撤销——timing corroborated 但 identity unverified，`n_lyric_recovered=0`。
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

B. G5N / G5N.1 lyric evidence
   [✓] no_chars root cause resolved or explicitly proven unavailable
       (0391/0404 → A5_instrumental_no_lyrics, LRC 间奏段无歌词行)
   [✓] low-confidence timing corroboration is NOT treated as lyric identity proof
       (onset-peak → timing_corroboration_only; unverified → no recovery)
   [✓] identity recovery uses an identity-bearing second evidence family
       (_onset_span_evidence phoneme-class consistency required)
   [✓] no threshold relaxation solely to create pilot items
       (MIN_REVIEW_CHAR_PROB=0.25 unchanged; n_lyric_recovered=0)
   [✓] evidence provenance/version persisted (rlv9 impl + per-char evidence fields)

C. G5N / G5N.1 B2 semantics
   [✓] B2 is not treated as automatic written-score error
   [✓] same-family waveform agreement confirms displacement, not semantic benignness
   [✓] benign classifications use identity-aware phoneme evidence + geometry/neighbor consistency
   [✓] sub-resolution displacement is neutral unless stronger evidence establishes a real conflict
       (measurement_below_resolution)
   [✓] phrase-level repetition remains audit-only after all shared conflicts resolve benign
   [✓] genuine written/structure errors route upstream (written_timing_error lane)
   [✓] measurement_ambiguous / unresolved remain fail-closed

D. Honest pilot roster
   [✓] all 21 candidates rerun under revised current contract (rlv9 inventory)
   [✓] eligibility_inventory committed/auditable
   [✓] roster contains only semantically resolved reviewable items (empty → vacuous)
   [✓] no unresolved pre-loop OR post-loop B1/B2/lyric-evidence blocker in roster
       (post_loop_gate verified/b1_block/needs_render enforced)
   [✓] every proposed roster item has current-contract render/post-loop evidence
       (final_eligible requires verified post-loop)
   [✓] pilot size evidence-driven; do not lower gates to fill count (roster=[])

E. Exact review authority
   [ ] state/plan are rebuilt after the final artifact commit
   [ ] selected packages rebuilt if semantics/contract changed
   [ ] verify_package PASS for every selected item
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
### M2.5 — PROBABLE structure repair — ← QUALITY HOLD / G5N.1（rlv8 已实现但 correctness 未闭合：lyric identity evidence、benign-B2 semantics、post-loop B1 gate、phrase/sub-resolution lifecycle；review_ready=false）
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
78. lyric-evidence recovery 禁止为了凑 pilot 单纯降低 `MIN_REVIEW_CHAR_PROB`；no_chars / low-confidence 必须通过 coverage 修复或独立 evidence adjudication，仍不确定则 fail-closed。
79. waveform onset/energy detector 只能 corroborate acoustic timing；没有 identity-bearing second evidence 时，不得把低置信 Whisper char 升级为 authoritative lyric identity。
80. honest-roster eligibility 必须消费 current-contract post-loop final_class；任何 `B1_*` unresolved subtype 都必须 hard-block，不能只看 pre-loop route。
81. `phrase_level_target_independent_conflict` 是 audit/routing fact，不是永久 blocker；shared conflicts 全部被独立证据裁决为 benign 后，不得因“重复出现”再次单独阻塞。
82. 如果定义某 timing displacement 低于 detector resolution，则该 displacement 本身必须 neutral / below-resolution，不能同时作为 measurable semantic error 的 hard blocker。
