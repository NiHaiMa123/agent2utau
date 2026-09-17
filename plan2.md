# agent2utau — Plan 2：GAME 主转谱 + 自动证据裁决 + Phrase-Level 审核

> 修订日期：2026-09-17
>
> 核心原则：**先把 written score 唱对，再做泠鸢演唱风格。**
>
> 当前阶段：**E1 Remote CI 已 PASS；M2.3.2A/B/C 已冻结。D 主体工作流 `0bbb098` 与 Final Integrity Patch `5c54284` 已完成，exact-audio binding、run-level authoritative decision state、decision snapshot、render-failure gate、prev/back 均已通过；`5c54284` 对应 remote CI run `35227944705` = success，175 passed。最新 review 发现 run-level authority 仍有一个 P0：`plan_batch()` 对 generation-1 review item 仍使用 batch-local 顺序号 `ri-{k+1:04d}`，因此 full/subset/reordered batch 可让不同 target 获得相同 `review_item_id` 并覆盖 package/decision。故撤回 D FROZEN。当前唯一最高优先级 = **M2.3.2D Stable Review Identity Final Patch**；不新增 D2/D3。完成 stable target identity + collision guard，并顺手完成 `verify_package()` 的 `audio_package_hash` 重算校验，最终 acceptance SHA remote CI green + local real-render smoke 后，D 才重新 FROZEN；在此之前不要开始 M2.4。**

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
→ M2.4 对 machine-safe / valid human-selected candidate 执行可回滚 repair
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
- third-F0 cache freshness比较当前 runtime version；
- SAFE target 必须绑定 B winner；
- separation-sensitive 会降低 confidence / 可阻止 resolution；
- 189s / 202s 永久 no-false-repair regression。

B 不新增 B4。

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

# 3. E1 Remote CI / Freeze Gate ✅ PASS

```text
.github/workflows/ci.yml
trigger: push + pull_request
runner: ubuntu-latest
Python: 3.11
core gate: pytest -q
```

从 C2 起，任何 stage 想标记：

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

D 已验证 baseline：

```text
D main: 0bbb09851033563749d41bb603a43bdfa79fa471
D Final Integrity Patch: 5c542844224ccf9caa675450606819c7ca95f8fc
remote CI: 35227944705
pytest: 175 passed / 0 failed
local smoke: rb-int1
```

**注意：`5c54284` 的 remote green 证明已有 tests 通过，但 stable review identity 尚未被 tests 建模，因此不能据此冻结 D。**

---

# 4. 全局不可破坏 contract

## 4.1 Missing evidence

```text
missing / low-confidence evidence
!= support
!= opposition
```

缺失 evidence 必须 neutral。

## 4.2 Evidence independence

```text
raw feature
→ within-group fusion
→ finalized group_scores
→ supporting_independence_groups
→ score / margin / gates
```

禁止从 raw feature 重新构造第二套 resolution truth。

## 4.3 Virtual GAME evidence

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

## 4.4 Candidate 0

```text
Candidate 0 永不被 adjudication / review / repair 原地覆盖
```

任何变化必须先成为独立 candidate / corrected-score artifact，并提供 rollback。

## 4.5 Review identity vs package identity

这两个概念必须彻底分离：

```text
review_item_id / target_key
= “这是哪个 unresolved target / 问题”
= 跨 batch / subset / reorder / generation 稳定

audio_package_hash
= “这次用户实际听到了什么”
= phrase / options / score patch / render bytes / model bytes material change 时变化
```

禁止把 batch 顺序号当逻辑 target identity。

---

# 5. M2.3.2D — 已完成主体能力，但当前 NOT FROZEN

## 5.1 D main workflow ✅ IMPLEMENTED @ 0bbb098

现有模块：

```text
src/agent2utau/review/build.py
src/agent2utau/review/render.py
src/agent2utau/review/decisions.py
```

CLI：

```text
review-batch
review
review-decide
review-status
```

已经通过的主体能力：

- 只有 finalized `needs_phrase_review` 进入 D；
- split parent + virtual children / merge partner 组成 atomic target group；
- 无关 unresolved 不做 Cartesian product；
- phrase window 默认 3–12s，优先 LRC / silence，避免 target note 中间硬切；
- baseline + 最多 3 个真实机器 candidate；
- pitch candidate 来自 frozen B hypotheses；
- structure candidate 来自 C / virtual-B；
- acoustic seed 明确标记 provenance，不冒充 GAME truth；
- blind OPTION labels；
- 同一 item 使用同一 phrase context / tempo / singer / renderer；
- shared gain，不做 per-option independent loudness normalization；
- `equivalent` / `none_correct` 语义；
- generation 1 → 2 regeneration 上限；
- D 不修改 Candidate 0，不执行 repair。

## 5.2 D Final Integrity Patch ✅ MAIN BODY DONE @ 5c54284

已经修正：

### Exact-audio binding

```text
plan_hash = pre-render score/context/config identity

audio_package_hash
= plan_hash
+ SOURCE original/separated WAV hashes
+ every OPTION WAV hash
+ OpenUtau/bridge executable hashes
+ voicebank/material model hashes
+ render provenance
```

Human decision 绑定 `audio_package_hash`，不是 pre-render `plan_hash`。

### Reviewability gate

以下任一情况必须拒绝 review / review-decide：

```text
render_error
missing SOURCE/OPTION WAV
missing recorded sha256
actual WAV hash mismatch
sample-rate/length inconsistency
unrendered package
```

### Run-level authority

```text
runs/<diag>/review/
  decisions.json      # append-only revisions
  packages.json       # current package index
  review_state.json   # atomic derived materialization
```

`latest_batch.json` 只能是 UI convenience pointer，绝不是 truth source。

已实现 resolver：

```text
current_valid_decision
all_current_valid_decisions
pending_items
regeneration_queue
rebuild_state
```

### Cross-generation lifecycle

```text
gen1 none_correct
→ pending_regeneration
→ gen2 package
→ pending_review
→ gen2 selection / none_correct
```

一个 1-item gen2 batch 不得删除其它 item 已有效的 decision。

### Decision snapshot

`human_selected_candidate` revision 已 snapshot：

```text
selected_option_id
candidate_id
selected_score_patch
selected_provenance
selected_wav_sha256
plan_hash
audio_package_hash
batch_id
generation
revision lineage
```

### CLI

```text
[i/N]
reviewed/pending
p = previous/back
append new revision, never edit old revision
```

Local real-render smoke `rb-int1` 已验证：

```text
5 items
hash recompute from bytes
bridge deterministic rerender bit-identical
gen1-reject → gen2-select
missing-wav refusal
```

但下节 stable identity P0 未解决，所以：

```text
M2.3.2D = OPEN
M2.4 = BLOCKED
```

不新增 D2 / D3。继续作为 **D Final Integrity Patch 的最后 correctness completion**。

---

# 6. M2.3.2D Stable Review Identity Final Patch ← CURRENT HIGHEST PRIORITY

## 6.1 P0 — `review_item_id` 必须是 stable target identity

### 已确认的生产代码问题

当前 `plan_batch()` generation-1 path 仍是：

```python
items = sorted(items, key=item_priority)
...
if only_items:
    items = ...
if max_items:
    items = items[:max_items]
...
for k, it in enumerate(items):
    it["item_id"] = ov.get("item_id") or f"ri-{k + 1:04d}"
```

因此 `review_item_id` 取决于**当前 batch 中的相对顺序**。

错误示例：

```text
full batch:
A → ri-0001
B → ri-0002
C → ri-0003

later subset batch containing only C:
C → ri-0001
```

而当前 run-level authority 使用：

```text
packages[item_id] = current package
ReviewLog revisions keyed by review_item_id
```

所以第二个 batch 可把 C 静默覆盖到 A 的 logical key 上；随后 `ReviewLog.append("ri-0001", ...)` 还可能 supersede A 的 human decision。

这会导致：

```text
不同 target
→ 相同 review_item_id
→ package collision
→ revision lineage corruption
→ M2.4 可能读取错误人工授权
```

这是 D freeze blocker。

---

## 6.2 Required identity model

新增明确的 stable target identity：

```text
target_key
review_item_id
```

推荐：

```python
target_key = canonical_hash({
    "identity_schema": "review-target-v1",
    "packets": sorted(target_group.packet_ids),
    "parent_ids": sorted(target_group.parent_ids),
    "operation_class": target_group.type,
})

review_item_id = "ri-" + target_key[:16]
```

实现可使用等价 canonical representation，但必须满足下面语义。

### 必须进入 identity 的内容

至少：

```text
真实 target packet ids
真实 parent note ids / merge partner identity
必要的 operation class（pitch / split / merge / compound 等）
identity schema version
```

### 不应进入 stable identity 的内容

不得把这些 material package details 塞进 `review_item_id`：

```text
batch id
batch 内顺序
priority rank
max_items
phrase window
OPTION 顺序
candidate pitch
score patch
rendered WAV hash
OpenUtau/model hash
generation number
```

这些变化应该通过：

```text
plan_hash / audio_package_hash
```

使旧 decision stale，而不是制造一个“全新的 target”。

### 核心语义

```text
同一个 unresolved target
+ different batch/subset/order/generation
→ SAME review_item_id

不同 unresolved target
→ DIFFERENT review_item_id
```

---

## 6.3 Generation lifecycle

Generation 1 与 Generation 2 必须使用同一个 stable `review_item_id`：

```text
ri-<stable-target>
  rev1 / gen1 / package A
  rev2 / gen2 / package B
```

不得：

```text
gen1 → ri-0003
gen2 → ri-0001
```

`none_correct` 的 lifecycle 仍保持：

```text
gen1 decision = human_rejected_all
→ new gen2 package for SAME target id
→ prior rejection preserved as audit / consumed routing state
→ gen2 pending_review
```

---

## 6.4 Collision guard — 禁止 silent overwrite

`register_package()` 必须保存：

```text
target_key
review_item_id
```

如果已有：

```text
packages[review_item_id]
```

但其 stable `target_key` 与新 manifest 不同：

```text
raise hard error
```

不得：

```text
latest wins silently
```

同样，`ReviewLog.append()` / M2.4-facing resolver 应能验证：

```text
decision.target_key
== current package.target_key
== manifest.target_key
```

否则 decision 无效，不得授权 repair。

---

## 6.5 Manifest / package / decision contract

每个 review manifest 至少新增：

```text
target_key
review_item_id
```

`packages.json` current record 至少保存：

```text
target_key
review_item_id
batch_id
generation
plan_hash
audio_package_hash
package_state
manifest path
```

每个 decision revision snapshot 至少保存：

```text
target_key
review_item_id
revision_id
supersedes_revision_id
batch_id
review_generation
plan_hash
audio_package_hash
selected_option_id
candidate_id
selected_score_patch
selected_provenance
selected_wav_sha256
semantics
```

M2.4 只允许消费：

```text
semantics == human_selected_candidate
AND current package valid
AND decision.audio_package_hash == current package.audio_package_hash
AND decision.target_key == current package.target_key
AND review_item_id matches stable target identity
```

---

## 6.6 Schema migration / old d2 review state

Stable identity 会改变 generation-1 `review_item_id`，同时 `plan_hash` / `audio_package_hash` 也应随之改变。

推荐 bump：

```text
REVIEW_SCHEMA: d2 → d3
review target identity schema: review-target-v1
```

旧 d2：

```text
ri-0001 / ri-0002 / ...
```

不得被自动当成新的 stable target truth。

允许两种安全实现：

```text
A. 保留 d2 artifact 仅 audit，d3 packages/review state 重新生成；

或

B. 只有能证明 old target_group 与 new target_key 精确一致时做显式 migration，
   且 package 必须重新 render/re-hash；旧 human decision 默认 stale，不能直接授权 M2.4。
```

当前项目还没有正式完成 46 条人工 review，因此优先选择简单、安全的 A。

禁止按旧顺序号猜测对应关系。

---

## 6.7 P1 — `verify_package()` 必须重算最终 `audio_package_hash`

当前 `verify_package()` 已逐项验证：

```text
actual OPTION WAV bytes ↔ option.wav_sha256
actual SOURCE bytes ↔ source_reference.sha256
```

但 final hardening 还应加入：

```text
actual/revalidated source hashes
+ actual/revalidated OPTION hashes
+ manifest.plan_hash
+ manifest.render_provenance
→ recompute audio_package_hash
→ MUST equal manifest.audio_package_hash
```

否则：

```text
return invalid_package
```

这样 M2.4 的授权边界是完整自校验的，而不是只相信 manifest 预先存好的 package hash。

这项为 P1，但应和 stable identity patch 同一轮完成。

---

# 7. D Stable Identity Acceptance Matrix

在重新标记 D FROZEN 前，至少全部通过。

## 7.1 Stable identity

```text
1. full batch 中 target A 的 review_item_id 可复现
2. A 单独 subset batch 的 review_item_id 与 full batch 完全相同
3. `--max-items` 不改变已包含 target 的 identity
4. priority reorder 不改变 target identity
5. batch_id 改变不改变 target identity
6. phrase window 改变不改变 target identity
7. option/candidate mapping 改变不改变 target identity
8. gen1 → gen2 继承同一 review_item_id
9. 两个不同 target 单独生成时 review_item_id 必须不同
10. pitch target 与另一个 pitch target 不得因都是 batch index 1 而碰撞
11. split/merge target 的 parent/partner identity 被稳定编码
12. target_key deterministic / canonical / order-independent
```

## 7.2 Collision / authority

```text
13. A 已 register 后，生成 unrelated C subset 不得覆盖 A package
14. A 已 decision 后，生成 unrelated C subset 不得 supersede A revision
15. packages.json 可同时保留 A/C current records
16. all_current_valid_decisions 仍返回 A 的有效 decision
17. same review_item_id + different target_key → hard failure
18. same target_key + same review_item_id + new audio package → allowed current-package update
19. decision.target_key mismatch → current_valid_decision returns None / invalid
20. latest_batch.json 仍不得成为 authority
```

## 7.3 Cross-generation

```text
21. gen1 none_correct → pending_regeneration
22. gen2 package SAME stable target id → pending_review
23. gen1 revision history保留
24. gen2 select 成为 authoritative latest revision
25. one-item gen2 batch 不影响其它 45 items
26. generation 2 none_correct → manual_followup_required
27. 不得出现 unbounded review generation loop
```

## 7.4 Exact audio integrity

```text
28. plan_hash material score/context change → hash changes
29. OPTION WAV byte change → audio_package_hash changes
30. SOURCE byte change → audio_package_hash changes
31. OpenUtau/model material change → audio_package_hash changes
32. missing WAV → verify_package fail
33. WAV recorded hash mismatch → verify_package fail
34. source recorded hash mismatch → verify_package fail
35. recomputed audio_package_hash != manifest.audio_package_hash → fail
36. valid unchanged package → recompute matches
```

## 7.5 Decision snapshot / repair authorization

```text
37. human_selected_candidate snapshots score_patch/provenance/wav hash
38. baseline/equivalent never authorize repair
39. human_rejected_all never authorize repair
40. manual_followup_required never authorize repair
41. stale decision never authorize repair
42. invalid/unreviewable package never authorize repair
43. current_valid_decision requires target_key + audio_package_hash both match
```

## 7.6 Permanent safety

```text
44. Candidate 0 hash before/after D unchanged
45. D itself仍执行 0 repair
46. frozen A/B/C regressions green
47. 189s / 202s 仍不得 auto repair
48. no disabled/skipped core regression used to fake green
```

## 7.7 Real production-path regressions

必须直接调用真实：

```text
collect_review_items
→ plan_batch
→ generate_batch/register_package
→ ReviewLog/rebuild_state
```

而不是在测试里手工写死 stable IDs。

至少包含：

```text
49. full-batch A/B/C → decide A → subset C → A untouched
50. full-batch A/B/C → reorder priorities → identities unchanged
51. full-batch → max_items → same included target IDs
52. gen1 reject C → only C gen2 → C same ID + A/B state survive
53. collision guard actually raises on forged same-ID different-target package
```

## 7.8 Local integration acceptance

在用户本机真实 OpenUtau/Yousa 环境重跑至少：

```text
A. pitch-only review item
B. structure split/virtual-B review item
C. 189s 或 202s permanent ambiguous item
```

验证：

```text
stable target id 可跨 full/subset batch 复现
manifest target_key 正确
all WAV 可播放
verify_package 包括 final audio_package_hash recompute
review decision save/resume/back 正常
Candidate 0 unchanged
```

## 7.9 Remote CI gate

Final D acceptance 必须：

```text
FINAL implementation SHA
→ GitHub Actions workflow exists
→ pytest job success
→ all D stable-identity regressions included
→ no skipped/disabled core regression
```

只有全部通过后才允许：

```text
M2.3.2D = FROZEN
M2.4 = UNBLOCKED
```

---

# 8. M2.4 — SAFE Repair Engine（BLOCKED UNTIL D RE-FREEZE）

D 重新冻结后再实现。

M2.4 可处理两类输入：

```text
A. machine-safe finalized repair_candidate
B. D human_selected_candidate + current valid stable-target/audio package decision
```

不得处理：

```text
pending
provisional
unresolved without human selection
stale review decision
human_no_preference
human_rejected_all
manual_followup_required
invalid/unreviewable package
target-key mismatch
audio-package mismatch
```

第一版优先：

```text
single-note written-pitch retune
```

每个 repair 必须写入独立 corrected-score artifact，不得覆盖 Candidate 0，并记录：

```text
repair_id
region
before / after
source: machine_safe | human_selected
B/C result
winning hypothesis
winner_game_support / opposition
group_scores
supporting/opposing groups
confidence / margin
review_item_id / target_key
decision revision_id
audio_package_hash
selected_score_patch / provenance / wav_sha256
gates passed
rollback data
```

0 SAFE repairs 合法。

Structure repair 仍需额外 precision gate；不得因为 D 用户选中过一个试听 candidate 就无条件开放整类 structure auto-repair。

---

# 9. D Phrase Review UX Contract

Human review 的目标始终是：

```text
听完整 phrase
→ 比较 baseline / A / B / C
→ 点哪个听起来对
```

用户永远不需要：

```text
填写 MIDI
填写 Hz
判断 cents
判断“到底高一个八度还是低一个八度”
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

同一句多个独立 unresolved：

```text
共享 phrase/source context
分别 review target_group
禁止 Cartesian product
```

Decision semantics：

```text
Baseline
→ human_resolved_keep
→ no repair

A/B/C
→ human_selected_candidate
→ 只有通过 stable-target + exact-audio validity 才可进入 M2.4

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

46 个 phrase_review 不需要在 D workflow freeze 前全部人工听完；冻结的是 workflow correctness / identity / integrity。

---

# 10. Lyrics / USTX / PITD

Written melody 稳定后再做正式 lyrics mapping：

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

通过后再加入：

```text
portamento
onset slide
ornament
vibrato
intonation deviation
```

PITD 不得掩盖 written-note error。

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
routing needs / decision
pitch adjudication lifecycle
structure adjudication lifecycle
RMVPE / FCPE / third-F0 evidence
plateau pre/post center + relative delta
boundary-time agreement
energy/onset/spectral/articulation boundary evidence
separation sensitivity
raw feature evidence
group_scores
supporting_independence_groups
winner / runner-up / margin
independent structure discovery stats
virtual candidate notes
virtual-note B results
virtual GAME correspondence provenance
seed conditional/effective GAME support
winner GAME support/opposition
phrase-review target groups
stable target_key / review_item_id
phrase windows / boundary source
review candidates + score patches
render profile hash
review WAV hashes
plan_hash / audio_package_hash
human decision + generation + revision
stale decision status
local integration result
remote CI run id / SHA / conclusion
cache/provenance manifest
```

Score artifacts：

```text
Candidate 0
virtual candidates
review context score
corrected score
retune count
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
### M2.3.2D Stable Review Identity Final Patch — ← CURRENT
### M2.3.2D FROZEN — PENDING stable-identity acceptance
### M2.4 — SAFE repair — BLOCKED until D re-freeze
### M2.5 — PROBABLE structure repair
### M2.6 — Optional second opinion
### M2.7 — Lyrics mapping + base USTX
### M2.8 — PITD + render loop
### M2.9 — 《年轮》M2 验收
### M3 — 泠鸢 style profile

> **原唱决定“唱什么”；泠鸢参考决定“怎么唱”。**

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
24. D 只提供完整 phrase 候选与 human adjudication，不要求用户猜 MIDI。
25. D 的不同候选除 target_group 外必须使用同一 context/render profile。
26. D 不允许 candidate Cartesian explosion；默认一个 target_group 一个 review item。
27. `review_item_id` 必须是 stable target identity，禁止使用 batch-local sequence number 作为逻辑主键。
28. 同一 target 跨 full/subset/reorder/gen1→gen2 必须保持同一 review_item_id。
29. 不同 target 的 stable target_key 不得碰撞；碰撞必须 hard fail，禁止 silent overwrite。
30. human decision 必须同时绑定 stable target_key + exact audio_package_hash；任一 mismatch 都不得授权 repair。
31. `verify_package` 必须验证实际 SOURCE/OPTION bytes，并最终重算 audio_package_hash。
32. stale review 不得授权 repair。
33. “都差不多”不得偷偷选择 machine winner。
34. “都不对”不得要求用户手工报正确音高；最多自动 regeneration 一次。
35. needs_phrase_review 只能在 machine-computable lanes 结束后产生。
36. 189s 永久 extractor-conflict regression。
37. 202s 永久 stochastic pitch/identity regression。
38. 0 repair 是合法结果。
39. 从 C2 起，没有 FINAL acceptance SHA 的 remote CI green，不允许 FROZEN/PASS。
40. 先把 written score 唱对，再生成 PITD。
41. 先“唱对”，再做泠鸢风格。
