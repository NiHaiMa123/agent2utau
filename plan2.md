# agent2utau — Plan 2：GAME 主转谱 + 自动证据裁决 + Phrase-Level 审核

> 修订日期：2026-09-16
>
> 核心原则：**先把 written score 唱对，再做泠鸢演唱风格。**
>
> 当前阶段：**E1 Remote CI 已 PASS；M2.3.2B 已冻结；M2.3.2C2 主体已实现但不可冻结。当前唯一算法优先级 = C2 Final Correctness Patch。不要新增 C3。**

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

最新已验证 acceptance SHA：

```text
d6798a9c70e18d43e12a6b91473b30845a34818a
GitHub Actions run: 35101379093
job: pytest
conclusion: success
119 passed
```

因此 E1 已 PASS，不再是当前 blocker。

从 C2 开始，任何 stage 想标记：

```text
FROZEN / PASS / accepted
```

必须同时满足：

```text
local regression green
+ current acceptance SHA 对应的 GitHub Actions workflow exists
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

### 5.1 Missing evidence rule

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

实现 commit：

```text
f220012cfc26bba04cf6c4d1368c9a8e43069fc0
7a160cedcb1e200be578b89950555260003d24db  # CI cpu torch fix
```

C2 已完成：

- per-extractor pre/post plateau center / delta / boundary / stability；
- dual-F0 **relative delta** agreement，octave-offset invariant；
- `two plateaus != split support`；
- split vs portamento competition；
- boundary-local energy evidence；
- `run_note_counts==0` 不再作为 merge evidence；
- consensus 增加真实 per-run `member_spans`；
- structure change 会生成 virtual note spans 并调用 frozen B；
- `final_structure_clear` 概念加入 SAFE gate；
- `split_candidate_stats.json` + discovery stats。

最新《年轮》C2 baseline：

```text
discovery: 315 → 118 (rate ≈ 0.28)
119 resolved_keep
  └─ 79 portamento
23 TRUE_SPLIT_CANDIDATE
16 unresolved
0 merge
0 repair
189.84s baseline octave auto-resolved
202.32 / 202.51 unresolved → phrase review candidate
```

remote CI：119 passed / green。

但 **C2 仍不可 FROZEN**，原因见下一节。

---

# 8. C2 Final Correctness Patch ← 当前唯一算法 P0

**不要新增 C3。** 以下修复属于 C2 freeze 前 final patch。

## 8.1 P0 — Virtual note 不得把 RMVPE-derived pitch 冒充 GAME evidence

当前实现存在 evidence-independence bug：

```text
virtual split span
→ structural RMVPE plateau center
→ 写入 vrec.game_tone
→ frozen B 在无 consensus 时把 game_tone 当 GAME support=1

同一 RMVPE 信息又同时进入：
RMVPE family
```

结果等价于：

```text
RMVPE evidence
→ fake GAME vote
+ real RMVPE vote
```

这是禁止的。

### 必须拆分概念

Virtual note packet 至少区分：

```text
candidate_written_pitch / seed_pitch
GAME evidence distribution
```

`candidate_written_pitch` 可以来自新 span 的 acoustic estimate，用于提出 hypothesis；**它不是 GAME evidence**。

Frozen B 不能再因为存在 candidate seed 就自动：

```text
GAME support = 1.0
```

### Virtual GAME evidence 合法来源

优先扩展 consensus/audit 保存真实：

```text
member_notes:
  run_id
  start
  end
  tone
```

对于 C 提出的 virtual split/merge identity：

```text
从真实 GAME run notes 与 virtual span 的 correspondence
→ 构造 GAME support distribution
```

如果一个 virtual identity 完全由 acoustic evidence 发现，而 GAME runs 没有对应真实 note：

```text
GAME group = unavailable / neutral
```

禁止伪造 GAME=1。

### Regression

必须覆盖：

```text
A. virtual pitch seed 来自 RMVPE，但无真实 GAME member note
   → GAME group neutral
   → RMVPE 只能算一次 family

B. 真实 GAME split runs 存在对应 note
   → GAME group 使用真实 per-run note tones/support

C. 加/删 acoustic seed 不得改变“是否存在 GAME evidence”
```

---

## 8.2 P0 — `final_structure_clear` 必须在 SAFE gate 计算前生效

当前生产顺序存在 bug：

```text
C resolved_keep
→ safe_retune_gate(rec)   # 此时 final_structure_clear 还没设置
→ apply_structure(rec)
→ final_structure_clear = true
```

所以 raw `structure_varies=true` 的 region 即使 C 已 resolved_keep，第一次生产 gate 仍会失败。

### 强制修正

推荐显式接口：

```text
safe_retune_gate(..., final_structure_status=C.status)
```

或至少保证：

```text
C resolved_keep
→ set final_structure_clear
→ THEN run SAFE gate
```

禁止依赖“之后再算第二次 gate”才能正确。

### Regression

必须增加 **production-order integration regression**：

```text
raw structure_varies=true
+ C resolved_keep
+ B resolved_change
→ 单次真实 production flow
→ SAFE gate 读取 finalized structure semantics
```

不是测试：

```text
gate → apply_structure → gate again
```

因为生产代码并不会自然重跑第二次。

---

## 8.3 P0 — RMVPE voiced-drop 不得冒充独立 non-F0 boundary family

原则：

```text
dual-F0 agreement
+ independent non-F0 boundary
```

才允许 acoustic-only high-confidence split。

当前：

```text
nonf0 = max(boundary_energy, voiced_drop)
```

但 `voiced_drop` 来自 RMVPE track 的 voiced mask，因此它属于 RMVPE mechanism，不是独立 non-F0 family。

### 必须改为

真正独立 boundary group 可来自：

```text
energy envelope
onset strength
spectral flux
re-attack transient
lyric/syllable articulation (if available)
```

RMVPE voiced probability / voiced mask：

```text
可以增强 RMVPE structure family
但不得单独满足 independent_non_f0_required
```

### Regression

```text
GAME stable one-note
+ RMVPE/FCPE delta agree
+ RMVPE voiced drop
+ 无 energy/onset/spectral/articulation boundary
→ 不得仅凭这些判 TRUE_SPLIT
```

---

## 8.4 P1 — Virtual B 必须保留 / 重算 separation sensitivity

当前 virtual note packet 没有可靠携带新 span 的 separation state，可能导致：

```text
parent = separation_sensitive
→ split virtual note
→ separation 字段缺失
→ frozen B 误认为 normal
→ confidence 被无意提高
```

### 强制规则

优先：

```text
按 virtual span 重新计算 mix-vs-separated sensitivity
```

如果暂时无法精确重算：

```text
parent sensitive=true
→ child 至少保守继承 sensitive=true
```

禁止 sensitive parent 由于字段缺失自动变 normal。

Regression：

```text
parent sensitive
→ virtual notes
→ frozen B confidence/gate 仍体现 separation penalty
```

---

## 8.5 P1 — C H0 的 missing extractor evidence 必须 neutral

当前类似：

```text
H0 += (1 - RMVPE_split_support)
H0 += (1 - FCPE_split_support)
```

会导致：

```text
extractor evidence missing
split_support=0
→ H0 获得 +1 强支持
```

这是错误语义。

### 必须显式计算 one-note support

例如：

```text
extractor 可用
+ coverage 足够
+ 单 plateau 稳定
+ span 内无 meaningful changepoint
→ one_note_support > 0
```

而：

```text
extractor missing / low confidence
→ one_note_support = 0 (neutral)
```

不能自动等于 `1 - split_support`。

Regression：

```text
missing RMVPE/FCPE
→ 不增加 H0 score
→ 不算 opposing H1 evidence
```

---

# 9. C2 Freeze Acceptance Matrix

C2 freeze 前必须满足全部要求。

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
9. run_note_counts==0 不作为 merge support
10. merge 只用明确 per-run span/boundary correspondence
11. C first stage 不自动写 Candidate 0
```

## 9.2 Virtual-note B correctness

```text
12. structure change -> virtual identities/spans
13. old B invalidated
14. 每个 virtual span 重新生成 evidence
15. frozen B 在 virtual note 上执行
16. old winner/confidence/margin/group_scores 不复用
17. candidate pitch seed 与 GAME evidence 字段分离
18. 无真实 GAME correspondence 时 GAME group neutral
19. 有真实 GAME correspondence 时只用真实 per-run GAME notes
20. RMVPE-derived seed 不得产生 fake GAME vote
21. separation sensitivity 在 virtual span 重算或保守继承
22. virtual B 未 finalized 时不得提前 phrase_review
```

## 9.3 Final-gate semantics

```text
23. C resolved_keep + unchanged span 可 finalize provisional B
24. material span/identity change 必须 rerun B
25. final_structure_clear 在 SAFE gate 前生效
26. raw structure_varies 保留 audit，但不永久阻塞 finalized keep
27. production-order regression PASS
```

## 9.4 Evidence independence / missingness

```text
28. RMVPE voiced-drop 不算 independent non-F0 boundary family
29. acoustic-only split 至少需要真正跨机制 boundary evidence
30. missing extractor evidence = neutral
31. C H0 不得用 1-missing-support 获得假强证据
32. 同一 evidence family 不得重复计票
```

## 9.5 Permanent safety regressions

```text
33. 189s no false repair
34. 202s no false repair
35. Candidate 0 unchanged
36. 0 automatic repair 仍是合法结果
37. frozen B regressions 全部 green
```

## 9.6 Remote CI hard gate

```text
38. local suite green
39. acceptance SHA 对应 GitHub Actions run exists
40. pytest job == success
41. core regressions 无 skipped/disabled 伪 green
42. remote run 必须对应最终 C2 acceptance SHA
```

只有 1–42 全部满足后：

```text
M2.3.2C = FROZEN
```

**不要新增 C3；如果 final patch 未满足，上述 C2 contract 继续保持 OPEN。**

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
GAME run note counts
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
GAME evidence provenance for each virtual note
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
### M2.3.2C2 — 主体已实现；Final Correctness Patch ← CURRENT
### M2.3.2C — Freeze only after §9 full acceptance + current-SHA remote green
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
11. 无真实 GAME virtual correspondence 时 GAME group 必须 neutral。
12. RMVPE voiced-drop 不算独立 non-F0 family。
13. F0 changepoint 本身不能证明 written-note boundary。
14. Split 与 portamento/ornament 必须真实竞争。
15. `run_note_counts==0` 不代表 merge。
16. Finalized C semantics 优先于 raw historical structure flag。
17. SAFE gate 必须在 finalized structure state 生效后计算。
18. separation-sensitive 不得因 virtual packet 丢字段而消失。
19. Candidate 0 永不被 adjudication 原地覆盖。
20. C 第一阶段只 adjudicate，不自动 structure repair。
21. needs_phrase_review 只能在 machine-computable lanes 结束后产生。
22. 189s 永久 extractor-conflict regression。
23. 202s 永久 stochastic pitch/identity regression。
24. 0 repair 是合法结果。
25. 从 C2 起，没有当前 acceptance SHA 的 remote CI green，不允许 FROZEN/PASS。
26. 先把 written score 唱对，再生成 PITD。
27. 先“唱对”，再做泠鸢风格。
