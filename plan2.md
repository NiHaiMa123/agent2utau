# agent2utau — Plan 2：GAME 主转谱 + 自动证据裁决 + Phrase-Level 审核

> 修订日期：2026-09-16
>
> 核心原则：**先把 written score 唱对，再做泠鸢演唱风格。**
>
> 当前阶段：**E1 Remote CI 已 PASS；M2.3.2B 已冻结；M2.3.2C2 主体 correctness 已通过，但仍不可冻结。当前唯一算法优先级 = C2 Virtual GAME Correspondence Final Patch。不要新增 C3。**

---

# 1. 最终流程

```text
原曲
→ decode / separation
→ GAME 多次同配置转谱
→ formal sequence alignment
→ 选择真实 GAME medoid run 作为 Candidate 0
→ multi-run uncertainty graph
→ RMVPE + FCPE + third-F0 + periodicity / spectral evidence
→ orthogonal pitch / structure / identity / separation states
→ structure 未定：C structure adjudication
→ note identity 确定后：在真实/候选 note identity 上运行冻结版 B pitch/octave adjudicator
→ finalized machine unresolved 才进入 D phrase-level A/B/C review
→ 只修高置信、已 finalized 的局部错误
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

# 2. 固定架构原则

1. GAME 是默认 melody transcription 基座，但不是 truth。
2. Candidate 0 必须来自真实 GAME run，不得由 consensus median 合成。
3. GAME 多 runs 是同一模型 stochastic samples，不是多个独立模型。
4. Consensus 是 correspondence / uncertainty graph，不是最终 note skeleton。
5. F0 measurement 与 written-score interpretation 分离。
6. RMVPE / FCPE / third-F0 是 evidence，不从零替代 GAME 重建整首谱。
7. 能机器测量的 MIDI / Hz / cents / octave 不交给人工猜。
8. 单 extractor 或同一 extractor 的多个派生 feature 不能伪装成多张独立票。
9. structure 未定时，pitch adjudication 只能 provisional；note identity 先定，再 final pitch。
10. Candidate 0 永不被 adjudication 原地覆盖；所有 change 先作为 candidate artifact。
11. 0 automatic repair 是合法结果。
12. 所有修改必须局部、可解释、可审计、可 rollback、可 A/B。

---

# 3. 已冻结阶段

## 3.1 M2.3.2A / A2 / A3 / A4 ✅ FROZEN

A4 baseline：

```text
421 notes
338 keep_baseline
76 pitch needs
51 structure needs
44 both
0 phrase review at A-stage
0 direct repair
```

冻结 contract：

- pitch / structure / identity / separation 正交；
- pitch / structure lanes 可共存；
- raw flags 不覆盖 calibrated result；
- structure candidate 不直接进入人工；
- SAFE eligible 不等于 repair；
- separator provenance 绑定实际 model path / bytes / config。

## 3.2 M2.3.2B1 / B2 / B3 ✅ FROZEN

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
- raw feature 只用于 audit，不能绕过 group gate；
- ACF 处理 T / 2T / T/2 octave ambiguity；
- harmonic evidence 避免 lower-octave harmonic-set superset bias；
- third-F0 cache freshness 比较当前 `librosa.__version__`；
- `safe_retune_gate(..., target_midi=B.winning_hypothesis)`；
- separation-sensitive 会降低 confidence / 可阻止 resolution；
- 189s / 202s 永久 no-false-repair regression。

Frozen B baseline：

```text
60 resolved_keep
7 provisional resolved_change → C
15 unresolved
0 repair_candidate
```

B 不新增 B4。

---

# 4. E1 Remote CI / Freeze Gate ✅ PASS

已建立：

```text
.github/workflows/ci.yml
trigger: push + pull_request
runner: ubuntu-latest
Python: 3.11
core gate: pytest -q
```

当前最新已验证代码 acceptance SHA：

```text
58c88471791616ed59aabd94bde8f15330d3eefb
GitHub Actions run: 35106410775
job: pytest
conclusion: success
127 passed
```

从 C2 开始，任何 stage 想标记：

```text
FROZEN / PASS / accepted
```

必须同时满足：

```text
local regression green
+ current acceptance SHA 对应 GitHub Actions workflow exists
+ core pytest job == success
+ 不允许拿旧 SHA 的 green run 充数
+ 不允许 skipped core regression 伪造 green
```

依赖本地 OpenUtau / Yousa voicebank / E:\ 路径 / 大模型文件的验证单列为 local/integration acceptance，不得假装被 lightweight CI 覆盖。

如果 frozen A/B regression 在 remote CI 中失败，则对应 frozen contract 自动 reopen。

---

# 5. Evidence independence contract

逻辑 family / group：

```text
GAME stochastic
RMVPE
FCPE
waveform mechanism group
musical context (soft)
```

相关 waveform feature：

```text
pYIN
ACF
harmonic
subharmonic
```

必须：

```text
raw feature
→ within-group fusion
→ finalized group_scores
→ supporting_independence_groups
→ score / margin / resolution gates
```

禁止重新从 raw feature 反推一套第二 gate。

`opposing_independence_groups` 当前仍可作为 audit-only；除非未来实现正式 group-level opposition，不得用于新增 resolution truth。

## 5.1 Missing evidence rule

全系统统一：

```text
missing / low-confidence evidence
!= support
!= opposition
```

缺失 evidence 必须是 neutral。

特别禁止：

```text
extractor 无可用 evidence
→ 用 1 - support 自动给相反 hypothesis 满分
```

## 5.2 Virtual GAME evidence rule

对于真实 Candidate 0 note：

```text
GAME stochastic support
= 全部 GAME runs 上真实 note identity/tone distribution
```

对于 C 构造的 virtual note：

```text
candidate_written_pitch / acoustic seed
!= GAME evidence
```

Virtual GAME evidence 必须同时满足：

```text
真实 GAME run member note
+ 与 virtual identity 有结构 correspondence
+ pitch 来自该真实 member note
```

仅仅时间覆盖 virtual span，不等于 note identity correspondence。

---

# 6. Cache / provenance contract

至少覆盖：

```text
source_audio_sha256
separator_actual_model_path
separator_model_sha256
separator_config_sha256
GAME model hashes/config
RMVPE model hash/config
FCPE model hash/config
third-F0 vocal_sha256
third-F0 implementation/runtime version/config/schema
pitch adjudicator schema/config
structure adjudicator schema/config
```

任一 input / model / implementation / runtime / config / schema material change：

```text
→ invalidate affected dependent artifact
```

---

# 7. M2.3.2C 状态

## C1 ✅ IMPLEMENTED / ❌ NOT FROZEN

commit：

```text
676a26eab4dacd8e394eee4529e91e52d219b7db
```

C1 建立：

- all-baseline independent structure discovery；
- H0 keep / H1 split / H2 merge / H3 portamento；
- 第一阶段只 adjudicate，不修改 Candidate 0；
- unresolved 清 pending，避免 loop；
- provisional-B lifecycle 初版。

C1《年轮》：

```text
315 discovery entries
47 TRUE_SPLIT_CANDIDATE
287 resolved_keep
4 unresolved
0 merge
0 repair
106 local tests
```

47 只是 calibration set，不是 47 个已确认 GAME 错误。

## C2 主体 ✅ IMPLEMENTED / ❌ NOT FROZEN

主要 commits：

```text
f220012cfc26bba04cf6c4d1368c9a8e43069fc0  C2 structure correctness/lifecycle
7a160cedcb1e200be578b89950555260003d24db  CI cpu torch fix
58c88471791616ed59aabd94bde8f15330d3eefb  C2 final correctness patch
```

C2 已完成并通过 review 的部分：

- per-extractor pre/post plateau center / delta / boundary / stability；
- dual-F0 relative-delta agreement，octave-offset invariant；
- `two plateaus != split support`；
- split vs portamento competition；
- boundary-local energy evidence；
- RMVPE voiced-drop 只增强 RMVPE family，不再冒充 independent non-F0 boundary；
- `run_note_counts==0` 不再作为 merge evidence；
- consensus 保存真实 per-run `member_notes[start,end,tone]`；
- structure change 会生成 virtual note spans 并调用 frozen B；
- virtual acoustic seed 与 GAME evidence 已拆分；无 GAME correspondence 时 GAME group neutral；
- `final_structure_status` 在第一次 production SAFE gate 调用时就生效；
- virtual note separation sensitivity 会重算/保守继承；
- H0 使用显式 `_one_note_support()`；missing extractor = neutral；
- `split_candidate_stats.json` + discovery stats；
- Candidate 0 不修改；0 repair。

58c8847《年轮》结果：

```text
111 resolved_keep
27 TRUE_SPLIT_CANDIDATE
24 unresolved
0 merge

virtual B:
47 resolved_keep
6 unresolved
1 resolved_change

22 split candidates fully machine-adjudicated
5 split candidates have unresolved virtual note → phrase review
0 repair
Candidate 0 unchanged
```

Remote CI：

```text
58c88471791616ed59aabd94bde8f15330d3eefb
127 passed
GitHub Actions green
```

但 **C2 仍不可 FROZEN**。最后 blocker 见下一节。

---

# 8. C2 Virtual GAME Correspondence Final Patch ← CURRENT / FINAL BLOCKER

**不要新增 C3。** 这是 C2 freeze 前最后一个 correctness patch。

## 8.1 P0 — 时间覆盖 != child note identity correspondence

58c8847 当前 virtual child 的 GAME correspondence 大致为：

```text
real GAME member note overlaps >= 60% of virtual child span
→ member tone 加入 child vtones
```

这个条件仍然过宽。

例如 C 提出：

```text
parent: 0.0–0.4
→ child A: 0.0–0.2
→ child B: 0.2–0.4
```

某 GAME run 实际只有：

```text
one long note: 0.0–0.4, tone=60
```

该 long note 对 child A / B 的 virtual-span coverage 都是 100%。

如果只用 coverage：

```text
同一颗 GAME one-note answer
→ 被当成 child A 的 GAME pitch vote
→ 又被当成 child B 的 GAME pitch vote
```

这是错误的 note-identity 语义。

该 long note 真正表示的是：

```text
这个 GAME run 不支持 split boundary
```

它可以作为 **GAME structure evidence against split**，但不能同时伪装成两个 child 的独立 pitch identity evidence。

## 8.2 Operation-aware correspondence contract

Virtual correspondence 必须知道 C change 的类型。

### Split candidate

对于：

```text
1 parent note
→ child A + child B
```

某个 GAME run 只有在该 run 中存在真实的、结构上分别对应 A/B 的 member notes 时，才允许产生 child pitch evidence。

至少要求：

```text
真实 internal boundary 与 candidate split boundary compatible
+ child note start/end/IoU/span compatibility
+ A/B 对应不同真实 member note identities
```

更优先复用 formal sequence alignment 已有的：

```text
split op / per-run member correspondence / internal boundary relation
```

而不是重新用单纯 overlap 猜 identity。

强制：

```text
一颗跨越 candidate split boundary 的 long GAME note
不得同时贡献给两个 children 的 pitch vote
```

### Merge candidate

对于：

```text
note A + note B
→ virtual merged note
```

真实 GAME run 中一颗跨越 combined span、明确缺少中间 boundary 的 long note，反而可以是合法的 merged identity evidence。

因此 split / merge correspondence 不能共用一个无语义的 overlap rule。

## 8.3 P0 — stochastic denominator 必须保留 total GAME runs

当前 virtual packet 若只有部分 runs 找到 member tone，不能写成：

```text
n_runs = len(vtones)
```

然后 frozen B 对这些 matched tones 重新归一化为 100%。

例如：

```text
5 total GAME runs
1 run 真正产生 child identity，tone 正确
4 runs 不产生该 child identity
```

错误语义：

```text
vtones = [correct]
n_runs = 1
GAME tone support = 1/1 = 1.0
```

正确语义必须保留：

```text
n_total_runs = 5
n_child_present = 1
child_presence_rate = 1/5
conditional_tone_support = 1/1
```

GAME child support 必须同时反映：

```text
identity presence
×
pitch agreement given identity present
```

可以实现为：

```text
effective_game_support
= child_presence_rate * conditional_tone_support
```

或经过校准的等价 formulation。

但禁止把 matched-run denominator 缩小后制造虚假的 GAME=1。

## 8.4 Frozen B compatibility

这次 patch 属于 **C → frozen B adapter semantics**，不得改变普通 Candidate 0 上 frozen B 的行为。

允许：

```text
virtual packet 增加：
  game_total_runs
  game_present_runs
  game_presence_rate
  real run-tone-by-run mapping
  correspondence provenance
```

如必须扩展 `adjudicate()` 对 virtual packet 的 GAME family 读取方式：

```text
ordinary Candidate 0 path 必须 bit-for-bit / regression-equivalent 保持原 frozen contract
```

不得借机重调 B threshold / weight / margin。

## 8.5 Required correspondence audit

每颗 virtual note 至少记录：

```text
virtual_id
operation: split | merge | boundary_shift
parent_id(s)
span
candidate_written_pitch
GAME total run count
per-run matched member note id/span/tone
per-run correspondence class
  child_identity_match
  parent_spanning_note
  absent
  ambiguous
child_presence_rate
conditional_tone_support
effective GAME support
correspondence rule/version
```

这样后续才能解释：

```text
为什么某个 GAME run 给了 child pitch 票
为什么某个 long note 只算 anti-split structure evidence而不算 child pitch
```

---

# 9. C2 Freeze Acceptance Matrix

C2 freeze 前必须全部满足。

## 9.1 Existing C2 correctness

```text
1. all-baseline discovery 仍存在，GAME stable-but-wrong 可进入 C
2. two plateaus alone 不等于 full split support
3. relative pitch-delta direction / magnitude / boundary-time agreement 显式计算
4. small/inconsistent delta 不误判 TRUE_SPLIT
5. true two-note synthetic 可判 TRUE_SPLIT
6. large portamento 仍可让 H3 赢
7. F0-only changepoint 无独立 boundary 时不得 high-confidence split
8. energy evidence 为 boundary-local
9. RMVPE voiced-drop 不算 independent non-F0 boundary
10. missing extractor evidence = neutral
11. run_note_counts==0 不作为 merge support
12. C first stage 不自动写 Candidate 0
```

## 9.2 Virtual-note B correctness

```text
13. structure change -> virtual identities/spans
14. old B invalidated
15. 每个 virtual span 重新生成 evidence
16. frozen B 在 virtual note 上执行
17. old winner/confidence/margin/group_scores 不复用
18. candidate pitch seed 与 GAME evidence 字段分离
19. 无真实 GAME child correspondence 时 GAME group neutral
20. RMVPE-derived seed 不得产生 fake GAME vote
21. separation sensitivity 在 virtual span 重算或保守继承
22. virtual B 未 finalized 时不得提前 phrase_review
```

## 9.3 FINAL blocker — identity-aware GAME correspondence

```text
23. split child correspondence 不能只看 virtual-span overlap
24. 一颗 parent-spanning GAME long note 不得同时给 child A 和 child B pitch vote
25. split child pitch vote 必须来自该 run 中真实 child-like note identity
26. 优先使用 formal alignment / internal-boundary correspondence，而不是纯 overlap heuristic
27. merge correspondence 与 split correspondence operation-aware，不共用错误语义
28. GAME total stochastic run count 在 virtual packet 中保留
29. child presence denominator = total GAME runs，不得缩成 matched runs
30. conditional tone support 与 identity presence 分开记录
31. effective GAME support 同时反映 presence × pitch agreement（或等价 calibrated formulation）
32. ordinary Candidate 0 frozen-B GAME semantics 不变
```

## 9.4 Final-gate semantics

```text
33. C resolved_keep + unchanged span 可 finalize provisional B
34. material span/identity change 必须 rerun B
35. final_structure_status 在第一次 SAFE gate 调用就生效
36. raw structure_varies 保留 audit，但不永久阻塞 finalized keep
37. production-order regression PASS
```

## 9.5 Required new regressions

```text
38. 5 runs: 4 个 one-long-note 跨 split boundary + 1 个 true split
    → long notes 不得同时成为 child A/B pitch evidence
    → child GAME support 不得因 matched denominator 缩小变成 1.0

39. 5/5 runs 都真正 split，child tone 4/5 一致
    → child identity presence = 5/5
    → GAME pitch support 应体现 4/5，而不是其它值

40. 5 runs 中只有 2 runs 真正存在 child identity，且 2/2 tone 一致
    → conditional tone support = 1.0
    → presence = 0.4
    → effective support 不能等于 1.0

41. merge case：真实 long GAME note 跨 combined span
    → 可成为 merged virtual identity evidence
    → 不应被 split-child rule 错误排除

42. ordinary Candidate 0 B regression outputs 不因 virtual adapter patch 改变
```

## 9.6 Permanent safety regressions

```text
43. 189s no false repair
44. 202s no false repair
45. Candidate 0 unchanged
46. 0 automatic repair 仍是合法结果
47. frozen A/B regressions 全部 green
```

## 9.7 Remote CI hard gate

```text
48. local suite green
49. FINAL C2 acceptance SHA 对应 GitHub Actions run exists
50. pytest job == success
51. core regressions 无 skipped/disabled 伪 green
52. remote run 必须对应最终 C2 acceptance SHA
```

只有 1–52 全部满足后：

```text
M2.3.2C = FROZEN
```

**不要新增 C3。若 correspondence patch 未满足，C2 contract 保持 OPEN。**

---

# 10. M2.3.2D — Phrase-Level Human Review

只处理 finalized B/C 后仍 unresolved 的音乐语义。

可达条件：

```text
pitch lane not pending / provisional / invalidated-waiting-rerun
structure lane not pending
AND 至少一条 finalized lane == unresolved
```

才允许：

```text
needs_phrase_review
```

人工不猜 MIDI / Hz / cents / octave。

默认 review 单位：

```text
3–12s phrase
常规 5–8s
```

优先边界：LRC line / vocal silence / breath gap / phrase context。

Review 包：

```text
SOURCE_PHRASE_original_mix.wav
SOURCE_PHRASE_separated_vocal.wav
BASELINE_PHRASE.wav
CANDIDATE_A_PHRASE.wav
CANDIDATE_B_PHRASE.wav
CANDIDATE_C_PHRASE.wav optional
```

所有 candidates 除目标因素外必须完全一致。

人工只选：

```text
Baseline / A / B / C / 都差不多 / 都不对
```

---

# 11. M2.4 — SAFE Repair Engine

进入条件：

```text
A frozen regressions remote green
B frozen regressions remote green
C frozen + current acceptance SHA remote green
189s no false repair
202s no false repair
phrase review workflow available
Candidate 0 / rollback contract complete
```

第一版优先 single-note written-pitch retune。

每个 repair 必须记录：

```text
region
before / after
B/C result
winning hypothesis
group_scores
supporting/opposing groups
confidence / margin
gates passed
rollback data
```

0 SAFE repairs 合法。

Structure repair 在 C adjudication precision 验证完成前不得自动执行。

---

# 12. Lyrics / USTX / PITD

Written melody 稳定后再做 lyrics mapping：

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

# 13. Evaluation / Audit

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
child presence rate / conditional tone support / effective GAME support
phrase-review count
local regression result
remote CI run id / SHA / conclusion
cache/provenance manifest
```

Score artifacts：

```text
Candidate 0
virtual candidates
corrected score
retune count
split/merge/boundary-shift count
GAME preservation ratio
rollback coverage
```

---

# 14. Milestones

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
### M2.3.2C1 — ✅ IMPLEMENTED / NOT FROZEN
### M2.3.2C2 — 主体 correctness 已通过；Virtual GAME Correspondence Final Patch ← CURRENT
### M2.3.2C — Freeze only after §9 full acceptance + final-SHA remote green
### M2.3.2D — Phrase-level human review
### M2.4 — SAFE repair
### M2.5 — PROBABLE structure repair
### M2.6 — Optional second opinion
### M2.7 — Lyrics mapping + base USTX
### M2.8 — PITD + render loop
### M2.9 — 《年轮》M2 验收
### M3 — 泠鸢 style profile

> **原唱决定“唱什么”；泠鸢参考决定“怎么唱”。**

---

# 15. 最终不可违反的规则

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
13. 一颗 parent-spanning GAME note 不得同时给 split 后两个 children pitch vote。
14. Virtual GAME stochastic denominator 必须保留 total GAME runs。
15. child GAME support 必须同时反映 identity presence 与 pitch agreement。
16. RMVPE voiced-drop 不算独立 non-F0 family。
17. F0 changepoint 本身不能证明 written-note boundary。
18. Split 与 portamento/ornament 必须真实竞争。
19. `run_note_counts==0` 不代表 merge。
20. Finalized C semantics 优先于 raw historical structure flag。
21. SAFE gate 必须在 finalized structure state 生效后计算。
22. separation-sensitive 不得因 virtual packet 丢字段而消失。
23. Candidate 0 永不被 adjudication 原地覆盖。
24. C 第一阶段只 adjudicate，不自动 structure repair。
25. needs_phrase_review 只能在 machine-computable lanes 结束后产生。
26. 189s 永久 extractor-conflict regression。
27. 202s 永久 stochastic pitch/identity regression。
28. 0 repair 是合法结果。
29. 从 C2 起，没有最终 acceptance SHA 的 remote CI green，不允许 FROZEN/PASS。
30. 先把 written score 唱对，再生成 PITD。
31. 先“唱对”，再做泠鸢风格。
