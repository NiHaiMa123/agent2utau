# agent2utau — Plan 2：GAME 主转谱 + 自动证据裁决 + Phrase-Level 审核

> 修订日期：2026-09-17
>
> 核心原则：**先把 written score 唱对，再做泠鸢演唱风格。**
>
> 当前阶段：**E1 Remote CI 已 PASS；M2.3.2A/B/C/D + M2.4 已冻结。M2.4 acceptance = `ce083c9`，remote CI run `35289803217` = success，226 passed / 0 failed；当前最高优先级 = M2.5 structure repair 的前置评估（M2.4 v1 内 human split 选择以 blocked_structure 形式保权）。M2.4 第一版严格只开放 single-note written-pitch retune；split / merge / boundary-shift 等 structure repair 继续封锁。Human-selected 路径只能通过 `repair_authorized_decision()`，并直接消费 decision revision 中已经审核过的 `selected_score_patch` snapshot，不得重新解释 OPTION、不得重新从 B/C hypotheses 推导一次。**

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

# 6. M2.4 — SAFE Repair Engine ✅ FROZEN @ ce083c9 (CI 35289803217, 226 passed)

## 6.1 第一版 scope：只做 single-note written-pitch retune

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

## 6.2 两条合法输入路径

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

## 6.3 Human-selected v1 仍然只接受 pitch-only snapshot

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

## 6.4 Repair plan 与 apply 必须分离

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

## 6.5 Repair identity / idempotency

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

## 6.6 Conflict policy：禁止 silent precedence

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

## 6.7 Corrected-score artifact

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

## 6.8 Rollback contract

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

## 6.9 Post-apply integrity verification

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

## 6.10 Repair plan freshness

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

## 6.11 189s / 202s permanent safety

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

## 6.12 0 repair / partial repair 是正常结果

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

# 7. M2.4 Acceptance Matrix

全部通过后才允许：

```text
M2.4 = FROZEN
→ M2.5
```

## 7.1 Scope / patch-shape gate

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

## 7.2 Machine-safe path

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

## 7.3 Human-selected path

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

## 7.4 Candidate 0 / corrected score integrity

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

## 7.5 Idempotency / conflict / rollback

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

## 7.6 Audit completeness

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

## 7.7 Permanent safety regressions

```text
66. 189s no false machine repair
67. 202s no false machine repair
68. D remains 0-repair stage
69. frozen A/B/C/D tests remain green
70. structure auto-repair remains disabled
71. PITD/style remains outside M2.4
72. 0 repairs remains legal
```

## 7.8 Production-path tests

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

## 7.9 Local integration acceptance

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

## 7.10 Remote CI gate

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

# 8. D Phrase Review UX Contract

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

# 9. M2.5+ 后续阶段边界

## 9.1 M2.5 — PROBABLE structure repair

M2.4 v1 不实现 structure repair。

M2.5 开始前至少需要：

```text
M2.4 pitch-only repair correctness frozen
structure precision 独立 acceptance
split/merge/boundary-shift patch identity + rollback contract
structure-specific no-false-repair regressions
```

Human-selected structure candidate 可以作为 M2.5 输入，但仍需 structure repair gate；“用户听起来选了它”不等于可以无条件开放所有 structure auto-repair。

## 9.2 M2.6 — Optional second opinion

只作为必要时 second opinion，不得破坏 frozen evidence-independence semantics。

## 9.3 M2.7 — Lyrics mapping + base USTX

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

## 9.4 M2.8 — PITD + render loop

基础 written score 通过后再加入：

```text
portamento
onset slide
ornament
vibrato
intonation deviation
```

PITD 不得掩盖 written-note error。

## 9.5 M2.9 — 《年轮》M2 验收

目标：确认完整 written score / lyrics / base render 已达到可接受正确度，并对未解决区域保留明确 audit 状态。

## 9.6 M3 — 泠鸢 style profile

> **原唱决定“唱什么”；泠鸢参考决定“怎么唱”。**

---

# 10. Evaluation / Audit

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

# 11. Milestones

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
### M2.4 — SAFE single-note pitch repair — ✅ FROZEN @ ce083c9 / CI 35289803217
### M2.5 — PROBABLE structure repair — ← CURRENT
### M2.6 — Optional second opinion
### M2.7 — Lyrics mapping + base USTX
### M2.8 — PITD + render loop
### M2.9 — 《年轮》M2 验收
### M3 — 泠鸢 style profile

---

# 12. 最终不可违反的规则

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
49. 先把 written score 唱对，再生成 PITD。
50. 先“唱对”，再做泠鸢风格。
