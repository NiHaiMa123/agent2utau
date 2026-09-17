# agent2utau — Plan 2：GAME 主转谱 + 自动证据裁决 + Phrase-Level 审核

> 修订日期：2026-09-17
>
> 核心原则：**先把 written score 唱对，再做泠鸢演唱风格。**
>
> 当前阶段：**E1 Remote CI 已 PASS；M2.3.2A/B/C/D 已冻结。Migration Integrity Final Patch 由 `905f144` 完成（本机 195 passed；remote CI run `35238843522` on `905f144` = success，195 passed，无 skip）：(P0) `ensure_review_authority()` 在所有 authority 入口（ReviewLog/load_packages/register_package/rebuild_state/resolvers）之前执行 schema gate —— 任何非 d3 / 缺 schema / identity_schema 错误 / 不可解析 / 混合 schema 的 authoritative file 触发 Strategy A：整个 `review/` 原样 rename 进 `review_d2_audit/<snapshot>/`（不覆盖），随后创建全新 d3 authority；legacy ri-NNNN 从不映射到 d3 target，d2 decision 永不授权 M2.4；rename-first + tmp-write 保证 crash 后只剩 absent 或 clean-partial d3，调用幂等。(§6.4) 三文件自描述 `schema=d3 + identity_schema=review-target-v1`。(§6.6 P1) `review_item_id == "ri-"+target_key[:16]` 在 register/append/resolver 三处强制。(§6.7) `repair_authorized_decision()` 是 M2.4 唯一入口：d3 + human_selected_candidate + valid package + bytes 级 verify_package + decision/package/manifest 三方 target_key 与 audio_package_hash 一致 + 完整 snapshot，否则 None。本机验证：真实 run 的 legacy authority 自动归档 `review_d2_audit/snapshot-20260917-151133/`；rb-d3-render2 重渲染 3 items（同 stable id）；verify_package 含重算通过；split item 的 human_selected_candidate 通过 M2.4 gate；Candidate 0 sha256 不变。**当前最高优先级 = M2.4 SAFE Repair（§8）。**

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
- third-F0 cache freshness 比较当前 runtime version；
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

D 已验证代码 baseline：

```text
D main:                     0bbb09851033563749d41bb603a43bdfa79fa471
D exact-audio/run-authority: 5c542844224ccf9caa675450606819c7ca95f8fc
D stable identity:           2a997a2e65e7557655f2c3498c99b247c491238e
remote CI:                   35233024292
pytest:                      186 passed / 0 failed
local real-render smoke:     rb-d3-*
```

**注意：`2a997a2` 的 green 证明 stable identity / collision / audio hash recompute regressions 通过，但没有证明旧 d2 authoritative state 会被 fail-closed 隔离。因此不能据此最终冻结 D。**

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

## 4.5 Review target identity vs audio package identity

```text
review_item_id / target_key
= “这是哪个 unresolved target”
= 跨 full/subset/reorder/max-items/generation 稳定

audio_package_hash
= “这次用户实际听到了什么”
= phrase/options/score patch/source/render/model/audio bytes material change 时变化
```

不得用 batch-local sequence number 作为逻辑 identity。

## 4.6 Review authority 必须 fail-closed

任何 human decision 能进入 M2.4 之前，必须能证明：

```text
review schema == d3
identity schema == review-target-v1
review_item_id 与 target_key 数学一致
current package 与 decision target_key 一致
current package 与 decision audio_package_hash 一致
verify_package(actual bytes) == valid
semantics == human_selected_candidate
```

只要有一项缺失 / legacy / mixed / malformed：

```text
不得猜
不得兼容性放行
不得当作 valid decision
不得授权 repair
```

---

# 5. M2.3.2D — 主体实现状态

## 5.1 D main workflow ✅ IMPLEMENTED @ 0bbb098

模块：

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

已实现：

- 只有 finalized `needs_phrase_review` 进入 D；
- split parent + virtual children / merge partner 组成 atomic target group；
- 无关 unresolved 不做 Cartesian product；
- phrase window 默认 3–12s，优先 LRC / silence，避免 target note 中间硬切；
- baseline + 最多 3 个真实 machine candidates；
- pitch candidate 来自 frozen B hypotheses；
- structure candidate 来自 C / virtual-B；
- acoustic seed 明确 provenance，不冒充 GAME truth；
- blind OPTION labels；
- 同一 item 使用同一 phrase context / tempo / singer / renderer；
- shared gain，不做 per-option independent loudness normalization；
- `equivalent` / `none_correct`；
- generation 1 → 2 regeneration 上限；
- D 不修改 Candidate 0，不执行 repair。

## 5.2 Exact-audio + run-level authority ✅ IMPLEMENTED @ 5c54284

已经成立：

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

Human decision 绑定 `audio_package_hash`。

Authoritative state：

```text
runs/<diag>/review/
  decisions.json      # append-only revisions
  packages.json       # current package index
  review_state.json   # derived state
```

`latest_batch.json` 只是 UI pointer。

Resolver：

```text
current_valid_decision
all_current_valid_decisions
pending_items
regeneration_queue
rebuild_state
```

Decision snapshot 包含：

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

## 5.3 Stable Review Identity ✅ IMPLEMENTED @ 2a997a2

当前生产代码已经：

```text
target_key = canonical hash(
  identity_schema=review-target-v1,
  packets,
  parent_ids,
  operation_class
)

review_item_id = "ri-" + target_key[:16]
```

并在 subset / `max_items` 过滤之前赋 identity。

已实现/验证：

- full batch ↔ subset 同 target ID 一致；
- reorder / max-items 不改变 target identity；
- gen1 → gen2 同 target ID；
- pitch / split / merge operation-aware；
- `register_package` same-id different-target hard fail；
- decision snapshot `target_key`；
- decision↔package target mismatch → stale；
- `verify_package` 重新读取实际 SOURCE/OPTION bytes 并重算最终 `audio_package_hash`；
- local real-render smoke 中 Candidate 0 unchanged。

Acceptance evidence：

```text
code SHA: 2a997a2e65e7557655f2c3498c99b247c491238e
remote CI: 35233024292
result: success
pytest: 186 passed / 0 failed
```

**d2 → d3 authority migration 已由 `905f144` fail-closed（remote CI `35238843522` = success，195 passed）→ M2.3.2D = FROZEN。**

---

# 6. M2.3.2D Migration Integrity Final Patch ← CURRENT HIGHEST PRIORITY

不新增 D2 / D3 / D4。不要重写 D 主体。只完成本节。

## 6.1 P0 — 旧 d2 review state 绝不能成为 d3 repair authority

### 已确认的问题

当前代码把新文件默认 schema 写成 `d3`，但读取已有文件时仍可能直接：

```python
json.loads(existing_decisions_or_packages)
```

如果磁盘上已经存在旧 d2：

```text
decisions.json schema=d2
packages.json schema=d2
review_state.json schema=d2
ri-0001 / ri-0002 / ...
```

旧 revision/package 没有可靠 `target_key`。

若 loader/resolver 继续兼容读取，旧：

```text
human_selected_candidate
+ matching old audio_package_hash
```

理论上仍可能被 `all_current_valid_decisions()` 视为有效。

这是 P0：旧 `ri-0001` 是 batch-local 顺序号，**不能证明它等于任何 d3 stable target**。

---

## 6.2 Required behavior — schema gate 必须位于所有 authority 入口之前

新增统一 helper，例如：

```text
ensure_review_authority_v3(run_dir)
```

名字可不同，但 contract 必须统一。

至少这些入口不得绕过 schema gate：

```text
ReviewLog.__init__ / ReviewLog load
load_packages
rebuild_state
current_valid_decision
all_current_valid_decisions
pending_items
regeneration_queue
generate/register review package
review / review-decide
未来 M2.4 human-decision resolver
```

原则：

```text
先验证 authority schema
再读取 decision/package
```

不得：

```text
先加载 d2
→ 再尝试“尽量兼容”
```

---

## 6.3 本项目采用 Migration Strategy A：完整归档，d3 clean start

当前 46 个 phrase_review 尚未完成正式人工 adjudication，因此不要做高风险 d2→d3 decision mapping。

对于 authoritative review 目录：

```text
runs/<diag>/review/
```

若发现任何 legacy authoritative file：

```text
schema != d3
missing schema
identity schema != review-target-v1
```

或出现 mixed state：

```text
decisions=d2 + packages=d3
packages=d2 + state=d3
任何 authoritative files schema 不一致
```

必须 fail-closed。

推荐行为：

```text
1. 停止 authority resolution；
2. 将整个旧 review authority 原样归档到：
   runs/<diag>/review_d2_audit/<unique-or-deterministic-snapshot>/
3. 不修改归档内容；
4. 创建全新的 d3 review authority；
5. 重新生成 d3 packages / audio_package_hash；
6. 旧 human decision 仅 audit，不自动迁移，不授权 M2.4。
```

也允许实现为：

```text
legacy/mixed detected
→ hard fail with explicit migration command
```

但自动归档方案优先，因为当前项目没有需要保留为有效授权的正式 46-item d2 decisions。

### 绝对禁止

```text
ri-0001(d2) → 根据位置猜 d3 target
按 batch 顺序映射
只给旧 decision 补一个 target_key
复用旧 d2 decision 直接授权 M2.4
覆盖/删除旧 audit artifact
```

---

## 6.4 d3 authoritative files 必须自描述 schema

新的 authoritative artifacts 至少：

```text
decisions.json
packages.json
review_state.json
```

顶层应明确：

```json
{
  "schema": "d3",
  "identity_schema": "review-target-v1"
}
```

如果未来 schema bump：

```text
unknown future schema
```

也必须 fail-closed，不能按 d3 猜。

`review_state.json` 是 derived artifact，可重建；但它的 schema mismatch 也不能静默与另一版本 authority 混用。

---

## 6.5 Migration / archive 必须安全、原子、可重复

要求：

```text
旧 review authority bytes 保留
archive destination 不得覆盖已有 audit
中途 crash 不得留下“半 d2 / 半 d3 authority”被 resolver 视为有效
第二次启动必须 idempotent
```

建议：

```text
archive → fsync/atomic rename or equivalent
→ create clean d3 authority
```

如果无法保证自动迁移原子性：

```text
宁可 hard fail
```

也不要继续读取 legacy authority。

---

## 6.6 P1 — stable ID 数学一致性校验

当前有 full `target_key` collision guard，但 authority boundary 还应显式验证：

```text
expected_review_item_id = "ri-" + target_key[:16]
```

必须满足：

```text
manifest.review_item_id == expected_review_item_id
package.review_item_id == expected_review_item_id
decision.review_item_id == expected_review_item_id
```

否则：

```text
register/append → hard fail
resolver → stale/invalid/None
M2.4 → no authorization
```

这不是用 truncated id 代替 full `target_key`；full `target_key` 仍是 collision truth，16-char id 只是稳定可读 key。

---

## 6.7 M2.4-facing resolver 的最终 gate

最终只允许返回：

```text
schema == d3
identity_schema == review-target-v1
semantics == human_selected_candidate
current package_state == valid
verify_package(actual bytes) == valid
review_item_id == "ri-" + target_key[:16]
decision.target_key == package.target_key == manifest.target_key
decision.audio_package_hash == package.audio_package_hash
selected_score_patch snapshot exists
selected_provenance snapshot exists
selected_wav_sha256 snapshot exists
```

任何 legacy / malformed / stale / mismatch：

```text
current_valid_decision → None
all_current_valid_decisions → exclude
M2.4 → refuse
```

---

# 7. D Migration Integrity Acceptance Matrix

全部通过后才允许再次标记 D FROZEN。

## 7.1 Legacy d2 fail-closed

```text
1. existing d2 decisions.json + human_selected_candidate → 不得出现在 all_current_valid_decisions
2. existing d2 packages.json → 不得作为 current d3 package authority
3. d2 decision + matching d2 audio_package_hash 也不得授权 repair
4. d2 review_state.json 不得被当成 authoritative current state
5. missing-schema legacy file → fail-closed
6. unknown future schema → fail-closed
7. mixed d2/d3 authority → fail-closed
8. 不允许按 ri-0001 顺序号猜 target mapping
```

## 7.2 Archive / clean-start lifecycle

```text
9. legacy review authority 被完整保留为 audit
10. archive 不覆盖已有 audit snapshot
11. migration 后新 review/ authority 是纯 d3
12. d3 packages 必须重新生成，不复用旧 d2 authorization
13. old decisions remain audit-only
14. second startup idempotent
15. crash/interrupted migration 不得产生可被 resolver 接受的 mixed authority
```

如果采用显式 hard-fail migration command，则对应验收为：

```text
legacy detection 必须阻止所有 resolver / review-decide / M2.4-facing access
直到 migration 明确成功
```

## 7.3 d3 identity integrity

```text
16. decisions/packages/review_state 顶层 schema == d3
17. identity_schema == review-target-v1
18. review_item_id == "ri-" + target_key[:16]
19. manifest forged id + real target_key → reject
20. package forged id + real target_key → reject/stale
21. decision forged id + real target_key → reject/stale
22. same short id + different full target_key → collision hard fail
23. full/subset/reorder/max-items identity regressions仍 green
24. gen1→gen2 identity regressions仍 green
```

## 7.4 Exact-audio / authority regressions

```text
25. verify_package actual SOURCE hash mismatch → fail
26. verify_package actual OPTION hash mismatch → fail
27. recomputed audio_package_hash mismatch → fail
28. valid unchanged package → recompute success
29. stale package hash decision → exclude
30. target_key mismatch decision → exclude
31. baseline/equivalent/rejected/manual_followup → never authorize repair
32. only valid human_selected_candidate can pass human authorization gate
```

## 7.5 Production-path regressions

测试必须走真实：

```text
collect_review_items
→ plan_batch
→ generate/register_package
→ ReviewLog
→ rebuild_state
→ all_current_valid_decisions
```

至少：

```text
33. d2 fixture → startup/migration → no valid decisions → new d3 package → review works
34. full A/B/C → decide A → subset C → A untouched
35. gen1 reject C → gen2 C → same stable id + A/B survive
36. forged same-id/different-target package → hard fail
37. d3 valid human selection → resolver returns exact snapshot
```

## 7.6 Permanent safety

```text
38. Candidate 0 hash unchanged
39. D itself仍执行 0 repair
40. frozen A/B/C regressions green
41. 189s / 202s 仍不得 auto repair
42. no skipped/disabled core regression used to fake green
```

## 7.7 Local integration acceptance

本机至少验证：

```text
A. 一个复制出来的 d2 legacy review fixture：确认 fail-closed / archive / clean d3
B. pitch-only review item
C. split/virtual-B review item
D. 189s 或 202s permanent ambiguous item
```

验证：

```text
old d2 decision 永不成为 valid authority
new d3 package 可正常 render/review
stable id 正确
verify_package 包含 final audio_package_hash recompute
review save/resume/back 正常
Candidate 0 unchanged
```

## 7.8 Remote CI gate

Final D acceptance 必须：

```text
FINAL implementation SHA
→ GitHub Actions workflow exists
→ pytest job success
→ migration + legacy fail-closed regressions included
→ stable-identity/audio-integrity regressions仍 green
→ no skipped/disabled core regression
```

只有全部通过后：

```text
M2.3.2D = FROZEN
M2.4 = UNBLOCKED
```

---

# 8. M2.4 — SAFE Repair Engine（BLOCKED UNTIL D FINAL FREEZE）

当前不要实现 human-selected repair consumption。

D 最终冻结后，M2.4 可处理：

```text
A. machine-safe finalized repair_candidate
B. D human_selected_candidate + current valid d3 stable-target/exact-audio decision
```

不得处理：

```text
pending
provisional
unresolved without human selection
legacy d2 review
mixed/unknown review schema
stale review decision
human_no_preference
human_rejected_all
manual_followup_required
invalid/unreviewable package
target-key mismatch
review_item_id/target_key mismatch
audio-package mismatch
```

第一版优先：

```text
single-note written-pitch retune
```

每个 repair 必须生成独立 corrected-score artifact，不得覆盖 Candidate 0，并记录：

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
review schema / identity schema
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
→ 只有通过 d3 stable-target + exact-audio validity 才可进入 M2.4

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

46 个 phrase_review 不需要在 D workflow freeze 前全部人工听完；冻结的是 workflow correctness / identity / integrity / migration safety。

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
stale/invalid decision status
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
### M2.3.2D Stable Review Identity — ✅ IMPLEMENTED @ 2a997a2 (CI 35233024292)
### M2.3.2D Migration Integrity Final Patch — ✅ DONE @ 905f144 (CI 35238843522)
### M2.3.2D FROZEN — ✅ @ 905f144
### M2.4 — SAFE repair — ← CURRENT
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
24. D 只提供完整 phrase candidates + human adjudication，不要求用户猜 MIDI。
25. D 的不同候选除 target_group 外必须使用同一 context/render profile。
26. D 禁止 candidate Cartesian explosion；默认一个 target_group 一个 review item。
27. `review_item_id` 必须是 stable target identity，禁止 batch-local sequence number。
28. 同一 target 跨 full/subset/reorder/max-items/gen1→gen2 必须保持同一 review_item_id。
29. 不同 target 的 full target_key 不得碰撞；碰撞必须 hard fail。
30. `review_item_id` 必须数学上等于 `"ri-" + target_key[:16]`。
31. human decision 必须同时绑定 d3 stable target_key + exact audio_package_hash。
32. legacy d2 / mixed / unknown review schema 必须 fail-closed，永不得授权 M2.4。
33. d2 顺序号不得被自动猜测映射到 d3 target。
34. `verify_package` 必须验证实际 SOURCE/OPTION bytes，并重算最终 audio_package_hash。
35. stale / invalid / malformed review 不得授权 repair。
36. “都差不多”不得偷偷选择 machine winner。
37. “都不对”不得要求用户手工报正确音高；最多自动 regeneration 一次。
38. needs_phrase_review 只能在 machine-computable lanes 结束后产生。
39. 189s 永久 extractor-conflict regression。
40. 202s 永久 stochastic pitch/identity regression。
41. 0 repair 是合法结果。
42. 从 C2 起，没有 FINAL acceptance SHA 的 remote CI green，不允许 FROZEN/PASS。
43. 先把 written score 唱对，再生成 PITD。
44. 先“唱对”，再做泠鸢风格。
