# agent2utau — Plan 2：GAME 主转谱 + 自动证据裁决 + Phrase-Level 审核

> 修订日期：2026-09-17
>
> 核心原则：**先把 written score 唱对，再做泠鸢演唱风格。**
>
> 当前阶段：**E1 Remote CI 已 PASS；M2.3.2A/B/C/D 已冻结。D Final Integrity Patch 由 `5c54284` 完成（本机 175 passed；remote CI run `35227944705` on `5c54284` = success，175 passed，无 skip）：(P0-1) `plan_hash`(pre-render) 与 `audio_package_hash`(post-render，含全部实际 WAV bytes + OpenUtau exe/bridge exe/voicebank material hash) 分离，decision 经 `verify_package` 门绑定 `audio_package_hash`；(P0-2) run 级权威状态 `runs/<diag>/review/{decisions.json(append-only), packages.json, review_state.json(atomic)}` + resolver(`current_valid_decision`/`all_current_valid_decisions`/`pending_items`/`rebuild_state`)，跨 generation 连续性成立；(P1) decision snapshot + review CLI index/total/prev/back。本机 real-render smoke `rb-int1`（5 items：pitch-only、structure-unresolved、split/virtual-B、189.84s/202.52s permanent）通过：audio_package_hash 可由 bytes 重算一致、bridge 确定性重渲染 bit-identical、gen1-reject→gen2-select 跨 batch 生命周期、missing-wav 拒绝 review-decide 全部验证。46 个 phrase_review 分路的人工 review 仍是 D 的待办（不构成 freeze blocker）。**当前最高优先级 = M2.4 SAFE Repair（§8），只允许消费 `human_selected_candidate` 且 `audio_package_hash` 与当前有效包一致的 decision。**

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
→ D 输出 exact-audio-bound human adjudication artifact
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

当前 C-freeze routing snapshot：

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

当前 D implementation baseline：

```text
implementation commit: 0bbb09851033563749d41bb603a43bdfa79fa471
current doc HEAD: ef0377df6d462c5c2a3ab5267905c9adba473935
HEAD CI run: 35223361700
result: success
pytest: 162 passed
```

**注意：remote CI green 只能说明已有测试通过；不能覆盖下面尚未建模的 D integrity blocker。**

---

# 4. 全局不可破坏 evidence / provenance contract

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

---

# 5. M2.3.2D — 已实现主体，当前 NOT FROZEN

实现 commit：

```text
0bbb09851033563749d41bb603a43bdfa79fa471
```

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

已经通过 review 的主体能力：

- 只有 finalized `needs_phrase_review` 进入 D；
- split parent + virtual children / merge partner 可组成 atomic target group；
- 无关 unresolved 不做笛卡尔积；
- phrase window 3–12s，优先 LRC / silence，避免 target note 中间硬切；
- baseline + 最多 3 个真实机器 candidate；
- pitch candidate 来自 frozen B hypotheses；
- structure candidate 来自 C / virtual-B；
- acoustic seed 明确标记 provenance，不冒充 GAME truth；
- blind OPTION labels；
- 同一 item 使用同一 phrase context / tempo / singer / renderer；
- shared gain，不做 per-option 独立 loudness normalization；
- append-only decision revisions；
- `equivalent` / `none_correct` 语义；
- generation 1 → 2 regeneration 上限；
- D 不修改 Candidate 0，不执行 repair。

本机已有 smoke 记录：

```text
run: diag-20260917-181538-6aec
batches: rb-smoke1 / rb-smoke2
5 item types including pitch / structure / split / 189s / 202s
79/79 smoke checks reported green
```

但下面的 integrity 问题属于 D 的冻结条件，因此：

```text
M2.3.2D = FROZEN @ 5c54284 (Final Integrity Patch, remote CI 35227944705)
M2.4 human-selected repair = UNBLOCKED
```

**不新增 D2。所有修复都属于 D Final Integrity Patch。**

---

# 6. M2.3.2D Final Integrity Patch ← CURRENT HIGHEST PRIORITY

## 6.1 P0 — Human decision 必须绑定“实际听到的 exact audio package”

### 当前问题

当前 `package_hash` 在 render 前由以下信息生成：

```text
schema
review_item_id / generation
song sha
diagnostic run
Candidate 0 hash
phrase window
context note ids
candidate score_patch / provenance
render_profile_hash
```

而真正 render 后才产生：

```text
SOURCE_PHRASE_original_mix.wav sha256
SOURCE_PHRASE_separated_vocal.wav sha256
OPTION_0.wav sha256
OPTION_1.wav sha256
...
```

这些实际听觉资产的 hash 当前没有参与 decision 所绑定的 package identity。

因此存在错误语义：

```text
score/options 不变
但 OpenUtau / DiffSinger / model / render output 改变
→ 用户实际听到的 WAV 改变
→ package_hash 却可能不变
→ 旧 human decision 被错误认为仍有效
```

### Required design

明确拆成两层：

```text
plan_hash
= pre-render score/context/config identity

audio_package_hash
= plan_hash
+ source-reference WAV hashes
+ every reviewable OPTION WAV hash
+ actual render provenance
```

**Human decision 必须绑定最终 `audio_package_hash`，不得绑定 pre-render `plan_hash`。**

`audio_package_hash` 至少绑定：

```text
review schema version
review_item_id / generation
song/source sha
Candidate 0 / context score hash
phrase start/end
option mapping
exact candidate score patches
candidate provenance
render profile
ustx template sha
SOURCE original clip sha256
SOURCE separated-vocal clip sha256
每个 OPTION WAV sha256
actual OpenUtau executable/version/hash
actual singer/voicebank identity + critical config/model hashes
actual DiffSinger acoustic model hash
actual duration/pitch/variance model hashes when used
actual vocoder hash
phonemizer identity/version
sample rate / tempo / renderer config
review render implementation/schema version
```

如果完整 voicebank tree hash 成本过高，可以使用稳定 manifest：

```text
singer.yaml/config hashes
acoustic ONNX hash
dsdur/dspitch/dsvariance hashes
vocoder hash
其它实际参与 render 的 model/config hash
```

但不能只记录逻辑名称 `YousaV1.65b`。

### Reviewability gate

一个 review package 只有在以下条件全部成立时才可进入人工：

```text
所有 required SOURCE assets 存在
所有展示给用户的 OPTION render success
所有 WAV 可读
所有 WAV sha256 已记录
所有 options 使用一致 sample rate / phrase length
manifest 的 audio_package_hash 已在 render 完成后生成
```

如果任一 option：

```text
render_error
missing wav
hash missing
length/sample-rate invalid
```

则：

```text
package_state = invalid / render_failed
不得 review
不得 review-decide
不得产生 human_selected_candidate
不得授权 M2.4
```

不能“catch render exception 后照样生成可选择 manifest”。

### Stale rule

以下任一 material change 必须改变 `audio_package_hash`：

```text
source bytes
separated vocal bytes
Candidate 0 / context revision
candidate score patch
option mapping
phrase window
voicebank/model bytes
acoustic/vocoder bytes
phonemizer/runtime material version
OpenUtau executable/version
render implementation/profile
最终 OPTION WAV bytes
```

旧 decision：

```text
保留 audit
但 state = stale
不得授权 repair
```

---

## 6.2 P0 — 跨 batch / generation 必须有唯一 authoritative review state

### 当前问题

当前每个 batch 各自拥有：

```text
review_batches/<batch>/decisions.json
```

generation 1 reject 后生成 generation 2：

```text
rb-001/decisions.json
rb-001-g2/decisions.json
```

这形成两套独立 revision history。

同时：

```text
latest_batch.json
```

只指向最后生成的 batch，不能代表整首歌所有 review items 的最终 human state。

错误风险：

```text
45 个 item 已在 gen1 完成
1 个 item reject → 生成 gen2
→ latest_batch 只包含那 1 个
→ M2.4 没有统一来源可查询全部 46 个 item 的当前有效 decision
```

### Required design

建立 **run-level authoritative decision state**。推荐：

```text
runs/<diag>/review/
  decisions.json            # canonical append-only revision log
  review_state.json         # derived latest state，可重建
  batches/
    <batch-id>/...
```

若不迁移现有目录，也必须新增等价的 run-level canonical store / resolver；禁止把 `latest_batch.json` 当 authoritative truth。

每条 revision 至少保存：

```text
revision_id
review_item_id
batch_id
review_generation
audio_package_hash
selected option
candidate_id
semantics
selected_score_patch snapshot
selected_provenance snapshot
selected_wav_sha256
created_at
supersedes_revision_id / superseded metadata
```

同一个 `review_item_id` 的历史必须跨 batch/generation 连续：

```text
gen1 none_correct
→ gen2 package created
→ gen2 selected candidate
```

最终 authoritative state：

```text
gen2 selected candidate
```

但 gen1 rejection 保留 audit。

### Required state semantics

```text
no decision                 → pending_review
gen1 none_correct           → pending_regeneration
new gen2 package, unreviewed→ pending_review
gen2 none_correct           → manual_followup_required
valid baseline              → human_resolved_keep
valid candidate             → human_selected_candidate
equivalent                  → human_no_preference
package hash mismatch       → stale
```

M2.4 只能通过一个明确 API / resolver 获取：

```text
current_valid_decision(review_item_id)
all_current_valid_decisions(run_id)
```

不得自己遍历“最新 batch”猜最终状态。

### Atomicity

run-level decision append / state materialization 必须：

```text
atomic write
append-only revision history
crash 后可恢复
derived state 可从 revision log 重建
```

---

## 6.3 P1 — Selected decision 必须 snapshot exact candidate

当前 `human_selected_candidate` revision 不应只保存：

```text
OPTION_2 / candidate_id / package_hash
```

还必须 snapshot：

```text
selected_score_patch
selected_provenance
selected_wav_sha256
selected_option_id
```

这样 M2.4 的授权输入是一个自包含 evidence artifact，而不是以后重新解释某个可变 manifest。

M2.4 仍必须验证：

```text
snapshot.audio_package_hash == current package hash
selected_wav_sha256 存在且与 package 一致
review decision 非 stale
```

---

## 6.4 P1 — Review CLI 补齐 previous/back

第一版 review loop 已支持：

```text
播放 source / vocal / options
选择
quit + resume
review-decide 修改 decision
```

仍需补：

```text
previous/back
显示 index / total / reviewed / pending
返回上一条后允许重新试听并生成新 revision
```

可以使用：

```text
p = previous
n = next/pending
```

具体键位不限，但不能只靠用户另开 `review-decide` 才能修正上一条。

此项是 UX/P1，不得阻塞 P0 修复，但 D freeze 前一并完成。

---

# 7. D Final Integrity Acceptance Matrix

以下全部满足后才允许重新写：

```text
M2.3.2D = FROZEN
```

## 7.1 已有主体 contract 保持 green

```text
1. 只有 finalized unresolved 才进入 D
2. pending/provisional machine lane 不进入 D
3. atomic target grouping 正确
4. 无关 unresolved 不做 Cartesian product
5. phrase 完整包含 target，默认 3–12s
6. phrase 不硬切 target note
7. baseline + <=3 machine-provenance alternatives
8. pitch candidate 来自 frozen B hypotheses
9. structure candidate 来自 frozen C / virtual-B
10. acoustic seed 不冒充 GAME truth
11. options 除 target patch 外共享 context
12. 同 render clock/sample-rate/tempo/singer/phonemizer
13. 不做 per-option independent time warp
14. 不做 per-option independent loudness normalization
15. shared gain 可复现
16. neutral profile，不加入泠鸢 style / complex PITD
17. Candidate 0 不修改
18. D 不执行 repair
19. 189s/202s package 可生成且不自动 repair
```

## 7.2 Exact-audio binding regressions

```text
20. 同 plan/config + 同 audio bytes → audio_package_hash stable
21. 任一 OPTION WAV byte 改变 → audio_package_hash 必须改变
22. original source clip byte 改变 → hash 改变
23. separated-vocal clip byte 改变 → hash 改变
24. OpenUtau executable/version/hash 改变 → hash 改变
25. singer/acoustic/vocoder material hash 改变 → hash 改变
26. phonemizer/render schema material change → hash 改变
27. option mapping 改变 → hash 改变
28. score_patch / phrase/context 改变 → hash 改变
29. human decision 绑定 audio_package_hash，不绑定 pre-render plan_hash
30. old decision 在新 audio_package_hash 下自动 stale
```

## 7.3 Package completeness regressions

```text
31. 所有 reviewable options 都必须存在 WAV + sha256
32. 某 option render_error → package 不可审核
33. missing OPTION WAV → review/review-decide 拒绝
34. source reference missing/hash missing → package 不可审核
35. option sample-rate/length inconsistency → package 不可审核
36. invalid package 不能产生 human-selected repair authorization
```

## 7.4 Cross-generation authoritative-state regressions

```text
37. gen1 select → canonical current state 可查询
38. gen1 none_correct → state = pending_regeneration
39. gen2 package created但未决定 → state = pending_review，不得 repair
40. gen1 reject + gen2 select → canonical latest = gen2 selected
41. gen1 revision 仍保留 audit
42. gen2 none_correct → manual_followup_required
43. 其它 45 个 item 的决定不会因只生成 1-item gen2 batch 而丢失
44. latest_batch.json 不作为 authoritative state
45. resolver 能返回整 run 全部 current valid decisions
46. stale package 不得出现在 valid decisions 集合
47. decision log crash/reload 后状态一致
```

## 7.5 Decision snapshot / UX regressions

```text
48. human_selected_candidate 保存 exact score_patch snapshot
49. 保存 selected provenance + selected WAV sha256
50. revision history append-only
51. 修改 decision 生成新 revision，不覆盖旧 revision
52. interactive review 支持 previous/back
53. progress / resume 正确
54. equivalent → baseline/no repair
55. gen1 none_correct → regeneration queue
56. gen2 none_correct → manual_followup_required
```

## 7.6 Permanent safety

```text
57. 189s no automatic repair
58. 202s no automatic repair
59. Candidate 0 hash D 前后不变
60. frozen A/B/C regressions green
61. 0 repair 仍是合法结果
```

## 7.7 Local real-render acceptance

在最终 patch 后重新跑本机 OpenUtau/Yousa smoke，至少覆盖：

```text
A. pitch-only unresolved
B. split/virtual-B unresolved
C. 189s 或 202s permanent ambiguous case
D. 一个故意 render failure / missing-asset negative case
E. gen1 reject → gen2 select 的跨 batch lifecycle
```

必须人工/脚本确认：

```text
真实 WAV 可播放
phrase context 正确
candidate 只有 target 差异
shared gain / 无 clipping
每个 audio_package_hash 能由实际文件重算一致
negative package 被拒绝 review
cross-generation current state 正确
selected decision snapshot 完整
```

## 7.8 Remote CI hard gate

```text
62. final local suite green
63. FINAL D acceptance SHA 对应 GitHub Actions run exists
64. pytest job == success
65. core regressions 无 skipped/disabled 伪 green
66. remote run 必须对应最终 D acceptance SHA
```

只有 1–66 全过：

```text
M2.3.2D = FROZEN ✅
→ M2.4 SAFE Repair
```

**D workflow freeze 仍不要求用户先听完全部 46 条；冻结的是 package integrity、review semantics、decision authority。**

---

# 8. M2.4 — SAFE Repair Engine（D integrity 完成前 BLOCKED）

进入实现条件：

```text
A/B/C frozen regressions green
D Final Integrity Acceptance 1–66 全过
FINAL D acceptance SHA remote CI green
Candidate 0 / rollback contract complete
```

M2.4 输入分两类：

```text
A. machine-safe finalized repair_candidate
B. run-level authoritative human_selected_candidate
```

对于 human-selected 输入必须同时满足：

```text
current_valid_decision == human_selected_candidate
decision.audio_package_hash == current audio package hash
decision.selected_score_patch snapshot exists
decision.selected_wav_sha256 matches package
not stale
not superseded
```

禁止处理：

```text
pending_review
pending_regeneration
provisional / unresolved without human selection
stale
human_no_preference
human_rejected_all
manual_followup_required
invalid/render_failed package
```

第一版优先：

```text
single-note written-pitch retune
```

每个 repair 必须记录：

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
review_item_id
review revision_id
audio_package_hash
selected_score_patch snapshot
gates passed
rollback data
```

0 SAFE repairs 合法。

Structure repair 在后续专门的 precision/repair stage 前不得因为 D 已能试听就自动开放。

---

# 9. Lyrics / USTX / PITD（M2.4 后）

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

# 10. Evaluation / Audit

至少记录：

```text
GAME total run count
per-run GAME member notes/spans/tones
pairwise alignment / medoid
orthogonal states
pitch/structure adjudication lifecycle
RMVPE / FCPE / third-F0 / waveform evidence
separation sensitivity
group_scores / supporting groups
virtual GAME correspondence provenance
seed GAME support vs winner GAME support
phrase-review target groups
phrase windows / boundary source
review candidates + score patches
plan_hash
actual render provenance
every SOURCE/OPTION WAV sha256
audio_package_hash
review package validity state
human decision revision_id / batch / generation
selected score_patch/provenance snapshot
stale/superseded status
run-level authoritative current decision
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
### M2.3.2D Final Integrity Patch — ✅ DONE @ 5c54284 (CI 35227944705)
### M2.3.2D FROZEN — ✅ @ 5c54284
### M2.4 — SAFE repair — ← CURRENT
### M2.5 — PROBABLE structure repair
### M2.6 — Optional second opinion
### M2.7 — Lyrics mapping + base USTX
### M2.8 — PITD + render loop
### M2.9 — 《年轮》M2 验收
### M3 — 泠鸢 style profile

> **原唱决定“唱什么”；泠鸢参考决定“怎么唱”。**

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
15. Candidate 0 永不被 adjudication / review / repair 原地覆盖。
16. D 只提供完整 phrase 候选与 human adjudication，不要求用户猜 MIDI。
17. D options 除 target_group 外必须使用同一 context/render profile。
18. D 不允许 candidate Cartesian explosion。
19. human decision 必须绑定 **post-render exact audio_package_hash**。
20. pre-render plan_hash 不能作为 human repair authorization。
21. 任一展示 OPTION render 失败时 package 不可审核。
22. WAV/model/OpenUtau material change 必须使旧 decision stale。
23. generation/batch 不能分裂 authoritative decision history。
24. `latest_batch.json` 只能是 UI pointer，不是全局 truth。
25. M2.4 必须从 run-level authoritative resolver 读取 human decision。
26. human_selected_candidate 必须 snapshot exact score_patch + provenance + WAV hash。
27. “都差不多”不得偷偷选择 machine winner。
28. “都不对”不得要求用户手工报音高；最多自动 regeneration 一次。
29. needs_phrase_review 只能在 machine-computable lanes 结束后产生。
30. stale / invalid / superseded review 不得授权 repair。
31. 189s 永久 extractor-conflict regression。
32. 202s 永久 stochastic pitch/identity regression。
33. 0 repair 是合法结果。
34. 从 C2 起，没有 FINAL acceptance SHA 的 remote CI green，不允许 FROZEN/PASS。
35. 先把 written score 唱对，再生成 PITD。
36. 先“唱对”，再做泠鸢风格。
