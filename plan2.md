# agent2utau — Plan 2：GAME 主转谱 + 自动证据裁决 + Phrase-Level 审核

> 修订日期：2026-09-17
>
> 核心原则：**先把 written score 唱对，再做泠鸢演唱风格。**
>
> 当前阶段：**E1 Remote CI 已 PASS；M2.3.2A/B/C 全部冻结。C 冻结代码 = `c0d2648a1b86344d455430c0553d70e1726ec017`，remote CI run `35210458722` = success，133 passed。M2.3.2D 工作流已实现并通过本机 integration smoke（见 §8.8）：实现代码 = `0bbb098`，remote CI run `35223120342` = success，162 passed。本机 smoke 批次 `rb-smoke1`/`rb-smoke2`（run `diag-20260917-181538-6aec`）覆盖 pitch-only / structure-unresolved / split+virtual-B / 189s / 202s 五类，79/79 项检查通过（时长、hash、context 隔离、无削波），decision 持久化/resume/stale/regen（gen2 → manual_followup_required）端到端验证。46 条 review 的完整人工聆听不是 freeze 前置条件 —— 当前优先级 = 人工完成 review 批次 + M2.4 SAFE Repair。**

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
→ C structure adjudication
→ identity 固定后运行冻结版 B pitch/octave adjudicator
→ finalized machine unresolved 才进入 D phrase-level review
→ D 只产生 human adjudication artifact，不直接改谱
→ M2.4 对 machine-safe / human-selected candidate 执行可回滚 repair
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
8. 单 extractor / 同 mechanism 的多个 feature 不能伪装成多张独立票。
9. structure 未定时 pitch 只能 provisional；note identity 先定，再 final pitch。
10. Candidate 0 永不被 adjudication / review / repair 原地覆盖。
11. 所有 change 必须先成为独立 candidate artifact，再经过 gate。
12. 0 automatic repair 是合法结果。
13. 所有修改必须局部、可解释、可审计、可 rollback、可 A/B。
14. 人工 review 解决“哪个完整音乐结果听起来对”，不要求用户识别 MIDI / Hz / octave。

---

# 3. 已冻结阶段

## 3.1 M2.3.2A / A2 / A3 / A4 ✅ FROZEN

Frozen contract：

- pitch / structure / identity / separation 正交；
- pitch / structure lanes 可共存；
- raw flags 不覆盖 calibrated result；
- structure candidate 不直接进入人工；
- SAFE eligible 不等于 repair；
- separator provenance 绑定实际 model path / bytes / config。

A4 historical baseline：

```text
421 notes
338 keep_baseline
76 pitch needs
51 structure needs
44 both
0 phrase review at A-stage
0 direct repair
```

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

B 不新增 B4。

## 3.3 M2.3.2C1 / C2 ✅ FROZEN @ c0d2648

关键 commits：

```text
676a26eab4dacd8e394eee4529e91e52d219b7db  C1 structure adjudication
f220012cfc26bba04cf6c4d1368c9a8e43069fc0  C2 structure correctness/lifecycle
58c88471791616ed59aabd94bde8f15330d3eefb  C2 evidence-independence/final-order patch
c0d2648a1b86344d455430c0553d70e1726ec017  C2 identity-aware virtual GAME correspondence
```

Frozen C contract：

- all-baseline independent structure discovery；
- H0 keep / H1 split / H2 merge / H3 portamento；
- two plateaus alone 不等于 split；
- dual-F0 relative delta + boundary agreement 显式计算；
- F0 changepoint 本身不能证明 written-note boundary；
- RMVPE voiced-drop 不算 independent non-F0 family；
- split / portamento / ornament 必须真实竞争；
- `run_note_counts==0` 不代表 merge；
- C change identity/span 后 old B invalidate + fresh packet + frozen B rerun；
- Candidate 0 不修改；C 本身不执行 structure repair；
- virtual acoustic seed 不等于 GAME evidence；
- virtual GAME correspondence 是 operation-aware / identity-aware；
- parent-spanning long GAME note 不得同时给两个 split children pitch vote；
- virtual GAME denominator 永远保留 total stochastic GAME runs；
- ordinary Candidate 0 的 frozen-B path 不因 virtual adapter 改变。

C freeze acceptance：

```text
local: 133 passed
remote SHA: c0d2648a1b86344d455430c0553d70e1726ec017
GitHub Actions run: 35210458722
pytest: success
133 passed / 0 failed
189s no false repair
202s no false repair
Candidate 0 unchanged
0 repair
```

当前《年轮》C-freeze rerun：

```text
428-note medoid run4
50 virtual notes over 25 TRUE_SPLIT candidates
246 parent_spanning
4 child_identity_match

final routing snapshot:
311 keep
21 resolved_change_candidate
50 auto_resolved
46 phrase_review
0 repair
```

C 不新增 C3/C4；除非 future regression 证明 frozen contract 被破坏，否则不得因 D/M2.4 的新需求重新改 C algorithm。

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

当前冻结代码 acceptance：

```text
c0d2648a1b86344d455430c0553d70e1726ec017
GitHub Actions run: 35210458722
job: pytest
conclusion: success
133 passed
```

文档 freeze commit `1a31dc83bdbae96c00bee7fe30d869134dd0a979` 自身的 CI run `35210740276` 也为 success。

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

依赖本地 OpenUtau / Yousa voicebank / E:\ 路径 / 大模型文件的验证单列为 local/integration acceptance，不得假装被 lightweight CI 覆盖。

任何 frozen A/B/C regression 在后续 remote CI 中失败，则对应 frozen contract 自动 reopen。

---

# 5. Evidence / provenance 不可破坏 contract

## 5.1 Missing evidence

全系统统一：

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

真实 Candidate 0：

```text
GAME support = 全 stochastic runs 上真实 note identity/tone distribution
```

C 构造 virtual note：

```text
candidate_written_pitch / acoustic seed != GAME evidence
```

GAME virtual vote 必须来自：

```text
真实 GAME run member note
+ operation-aware structural correspondence
+ 真实 member tone
```

Virtual GAME support 必须保留：

```text
n_total_runs
n_child_present
child_presence_rate
conditional_tone_support
effective_game_support
```

禁止 matched-runs-only 重新归一化为 1.0。

## 5.4 Audit naming clarification

当前 `virtual_correspondence.conditional_tone_support` / `effective_game_support` 是相对于 virtual `candidate_written_pitch` seed 的 audit 值。

它们 **不等于** frozen B 对最终 winner hypothesis 实际计算的 GAME support。

D / M2.4 后续读取时必须区分：

```text
seed_conditional_tone_support   # correspondence audit
seed_effective_game_support     # correspondence audit
winner_game_support             # B winner hypothesis actual value
winner_game_opposition          # B winner hypothesis actual value
```

实现 D 时如果修改 schema，优先把旧字段 alias/rename 为上面的明确名称；不得改变 frozen B scoring。

## 5.5 Cache / provenance

至少覆盖：

```text
source_audio_sha256
separator actual model path/hash/config
GAME model hashes/config
RMVPE model hash/config
FCPE model hash/config
third-F0 vocal sha / implementation / runtime version / config / schema
pitch adjudicator schema/config
structure adjudicator schema/config
review package schema/render profile
```

material input / model / implementation / runtime / config / schema change：

```text
→ invalidate affected dependent artifact
```

---

# 6. M2.3.2D — Phrase-Level Human Review ← CURRENT

## 6.1 目标

D 只解决：

> **A/B/C machine lanes 已经算完，但仍无法安全决定的音乐语义。**

D 不要求用户判断：

```text
MIDI
Hz
cents
octave 编号
RMVPE / FCPE 谁对
GAME 哪个 run 对
```

D 给用户的是**完整 phrase 中的可听候选结果**。

D 本身：

```text
只生成 review package
只记录 human adjudication
不直接修改 Candidate 0
不直接执行 repair
```

真正写回 corrected score 统一交给 M2.4。

## 6.2 Phrase-review 可达条件

只有同时满足：

```text
pitch lane not pending
pitch lane not provisional
pitch lane not invalidated_waiting_rerun
structure lane not pending
C/B machine lifecycle finalized
AND 至少一条 finalized lane == unresolved
```

才允许：

```text
needs_phrase_review
```

禁止：

```text
machine lane 还没跑完
→ 为了省事直接丢给人听
```

## 6.3 Atomic target group

人工 review 的最小裁决单元不是“整句所有 unresolved 的笛卡尔积”，而是：

```text
target_group
```

一个 target_group 可以是：

```text
1 个 pitch-only unresolved note
1 个 structure candidate parent + 其 virtual children
1 个共享同一 boundary 的 split/merge operation
1 个因同一 C operation 强耦合的局部 note cluster
```

不同来源、彼此独立的 unresolved regions，即使落在同一句，也默认是 **不同 review items**，可以共享同一 phrase audio context，但不得自动做 candidate Cartesian product。

只有满足以下之一才允许合并为同一个 target_group：

```text
同一 C structure operation
共享同一 boundary / parent identity
一个候选的成立会直接改变另一个候选的 note identity
```

这样避免：

```text
2 options × 3 options × 2 options → 12 个音频
```

的组合爆炸。

## 6.4 Phrase window 生成

默认 review phrase：

```text
3–12 s
常规目标 5–8 s
```

优先边界顺序：

```text
1. LRC / lyric line boundary（若现有时间戳可靠）
2. vocal silence / breath gap
3. energy valley / phrase break
4. fixed context fallback
```

必须满足：

```text
完整包含 target_group
target 前后尽量各 >= 0.75 s 可听上下文
不得在 target note 正中硬切
不得为了缩短长度裁掉决定旋律走向的前后 note
```

fallback：

```text
window = target span + 1.5 s pre + 1.5 s post
然后 clamp 到 3–12 s
```

若 LRC line > 12 s：

```text
以 target 为中心，在最近 silence / breath gap 切成 <= 12 s 子句
```

多个 review items 使用完全相同 phrase window 时，应复用 source/render context，不重复生成无意义资产。

## 6.5 Candidate 来源

每个 review item 最多：

```text
1 baseline + 3 alternatives
```

Candidate 必须来自已有可审计机器 hypothesis，不允许随意猜一个 MIDI：

### Pitch-only unresolved

```text
Baseline = Candidate 0 target pitch
A/B/C = frozen B hypotheses 中最有意义且互不重复的候选
```

候选优先级：

```text
winner
runner-up
明确 octave alternative / extractor-conflict alternative
```

### Structure unresolved / change candidate

```text
Baseline = Candidate 0 structure
Alternative = C 的 H1/H2/H3 等真实 candidate structure
```

structure alternative 中 child note pitch：

```text
优先使用 fresh virtual-B finalized result
```

如果 virtual B 自身 unresolved：

```text
允许为同一个 structure candidate 生成少量 top pitch variants
但总候选仍 <= 4
```

禁止：

```text
consensus median 合成整句新谱
随机 semitone 探索
把 acoustic seed 当成 GAME truth
为凑满 A/B/C 人工制造没有 provenance 的 candidate
```

## 6.6 Candidate beam / 去重

如果一个 target_group 内多个 child 都有 pitch alternatives，不做完整笛卡尔积。

使用 bounded beam：

```text
beam width <= 3 alternatives
```

候选 joint ranking 可以使用已有 machine evidence 排序，但 human review 不展示“置信度高低”作为暗示。

必须 dedupe：

```text
note identities 相同
+ written pitches 相同
+ timing 相同
→ 视为同一 candidate
```

如果最终只有：

```text
Baseline + A
```

就只生成两个，不强行凑 B/C。

## 6.7 Review context score

第一版 D 使用最保守、最可解释的上下文：

```text
phrase 内 target_group 之外全部保持同一 context snapshot
```

默认 context snapshot：

```text
Candidate 0
```

也就是说：

```text
Baseline 与 A/B/C 只有 target_group patch 不同
其它 note / tempo / lyric timing / render settings 完全相同
```

未来若要把已经通过 M2.4 的 corrected notes 作为 context：

```text
必须 version/hash 绑定 context score
所有 options 使用同一 context revision
```

禁止 candidate A/B 各自带不同的邻域“顺手优化”。

## 6.8 Neutral render profile

D 的目标是判断 written score，不是判断泠鸢 style。

因此 review render 必须使用固定 neutral profile：

```text
同一 OpenUtau version
同一 Yousa voicebank version/hash
同一 Chinese phonemizer
同一 DiffSinger acoustic/vocoder
同一 tempo map
同一 sample rate
同一 renderer config
同一 dynamics / expression defaults
不加入 personalized 泠鸢 style
不加入候选特有复杂 PITD
```

允许的最小 pitch transition 仅用于避免渲染器机械断裂；所有 options 必须使用完全相同规则。

PITD 不得掩盖 written-note 差异。

## 6.9 Lyrics / phoneme 临时映射

D 发生在正式 lyrics mapping 之前，但 render 仍需要可唱 phoneme。

第一版允许使用现有 lyric/alignment evidence 生成**review-only temporary mapping**：

```text
首 note：当前对应 lyric token
同字分裂后后续 child：+
无可靠 lyric：使用同一中性 fallback syllable / 已有临时 lyric
```

强制：

```text
同一 review item 所有 options 使用语义等价的 lyric/phoneme context
structure split 造成的 + continuation 是结构实现所必需，必须记录在 candidate patch 中
不得因为不同 candidate 使用不同歌词内容而影响试听判断
```

正式 lyrics mapping 仍属于 M2.7。

## 6.10 时间对齐与响度公平

同一 review item 的所有 candidate render：

```text
exact same phrase start/end
exact same sample rate
exact same leading/trailing context
exact same render clock / tempo map
```

禁止每个 candidate 独立做 cross-correlation time-warp，因为这可能把 timing difference 本身抹掉。

允许统一 renderer latency compensation，但必须：

```text
同一个 offset 应用于所有 candidates
记录 offset
```

响度：

```text
禁止每个 candidate 独立 normalize 到不同 gain
```

应：

```text
render 原始结果
→ 计算一份 shared candidate gain（或固定 render gain）
→ 同一个 gain 应用于 Baseline/A/B/C
```

SOURCE original / separated vocal 可以单独做 reference listening gain，但必须记录，不能回写到 candidate 比较。

所有 WAV：

```text
无 clipping
统一 bit depth / sample rate
记录 sha256
```

## 6.11 Review package

每个 phrase context 至少包含：

```text
SOURCE_PHRASE_original_mix.wav
SOURCE_PHRASE_separated_vocal.wav
OPTION_0.wav
OPTION_1.wav
OPTION_2.wav optional
OPTION_3.wav optional
manifest.json
```

默认推荐 **blind option labels**：

```text
OPTION_0 / OPTION_1 / OPTION_2 / OPTION_3
```

manifest 内部保存：

```text
哪一个 = Baseline
哪一个 = candidate A/B/C
```

UI/review 页面默认不显示 machine confidence、winner 名称、RMVPE/FCPE 判断，避免听觉选择被提示词污染。

如第一版 UI 暂时直接显示 Baseline/A/B/C，也必须记录：

```text
blinded = false
```

后续可以升级 blind mode，但不得阻塞第一版 D。

## 6.12 Review item machine-readable schema

建议：

```json
{
  "review_item_id": "...",
  "review_generation": 1,
  "song_sha256": "...",
  "diagnostic_run_id": "...",
  "candidate0_revision": "...",
  "context_score_hash": "...",
  "target_group": {
    "type": "pitch|split|merge|boundary|compound",
    "note_ids": [],
    "parent_ids": [],
    "region": [0.0, 0.0],
    "reason": "..."
  },
  "phrase": {
    "start": 0.0,
    "end": 0.0,
    "boundary_source": "lrc|silence|breath|fallback"
  },
  "render_profile_hash": "...",
  "options": [
    {
      "option_id": "OPTION_0",
      "candidate_id": "...",
      "score_patch": {},
      "provenance": {},
      "wav_sha256": "..."
    }
  ],
  "package_hash": "..."
}
```

`package_hash` 必须绑定：

```text
source hashes
context score
candidate patches
render profile
option mapping
phrase window
schema version
```

## 6.13 Human decision artifact

人工只需要选：

```text
OPTION_0 / OPTION_1 / OPTION_2 / OPTION_3
都差不多
都不对
```

不要让用户填写 MIDI / note name / cents。

每次选择立即写入：

```json
{
  "review_item_id": "...",
  "package_hash": "...",
  "selected": "OPTION_1|equivalent|none_correct",
  "review_generation": 1,
  "created_at": "..."
}
```

必须支持：

```text
逐条保存
中断后继续
只显示 pending items
修改某一条 decision
```

修改 decision 时保留 revision history，不直接覆盖旧记录。

## 6.14 Decision semantics

### 选中 Baseline option

```text
human_resolved_keep
→ 不产生 repair
```

### 选中 A/B/C candidate

```text
human_selected_candidate
→ 记录 exact candidate_id + score_patch + package_hash
→ 只获得进入 M2.4 的资格
→ D 本身仍不改谱
```

### 都差不多

语义：

```text
human_no_preference
```

默认保守行为：

```text
keep Candidate 0
不 repair
关闭该 review item
```

不得因为“都差不多”自动选择机器 winner。

### 都不对

语义：

```text
human_rejected_all
```

必须：

```text
不 repair
不要求用户猜正确 MIDI
进入 D candidate-regeneration queue
```

允许最多一次自动 regeneration：

```text
review_generation 1 → 2
```

第二代可尝试：

```text
扩展 phrase context
加入尚未展示的真实 B runner-up
加入真实 alternate GAME-run hypothesis
C H3 / alternative structure（若已有 provenance）
重新 separation/render（仅当 separation-sensitive audit 明确需要）
```

仍禁止无 provenance 随机猜音。

如果 generation 2 仍“都不对”：

```text
manual_followup_required
```

但含义是需要后续 agent / music-analysis workflow 继续处理，**不是让用户手工报 MIDI**。

不得无限 review loop。

## 6.15 多 unresolved 同 phrase 的处理

如果同一个 6 秒 phrase 内存在多个独立 target_group：

```text
共享 SOURCE / phrase context
但分别生成 review_item
```

review item X 的 options：

```text
只改 X
其它 unresolved 保持 Candidate 0
```

review item Y 同理。

只有结构上强耦合时才合并。

这样用户仍能在完整句子里判断，但不会出现组合爆炸。

## 6.16 Review priority / batching

当前约有：

```text
46 needs_phrase_review
```

不得要求用户一次性手工处理 46 个散乱文件夹。

生成 batch：

```text
review_batches/<batch_id>/
```

排序优先级建议：

```text
1. octave / large-pitch conflict
2. structure split/merge conflict
3. 189s / 202s permanent ambiguous regions
4. smaller pitch/timing ambiguity
```

同 phrase 的 items 相邻展示，减少 context switching。

第一版 UI/CLI 至少做到：

```text
播放 original
播放 separated vocal
播放各 OPTION
选择结果
自动进入下一条
显示 progress
可返回上一条
```

D 的目标是把人工操作压缩成“听完整句子 → 点一个选项”。

---

# 7. D stale-review / reproducibility contract

任何 human decision 只对**精确的 review package**有效。

以下任一变化：

```text
source audio bytes
Candidate 0 revision
B/C schema material change
candidate score patch
phrase window
voicebank
phonemizer
acoustic/vocoder
OpenUtau version
render profile
option mapping
```

导致：

```text
package_hash change
→ old decision = stale
→ 不得继续授权 M2.4 repair
```

旧 decision 保留 audit，但必须重新 review 新 package。

如果只是无语义 metadata 文档变化、且 package_hash 不变：

```text
decision 继续有效
```

---

# 8. M2.3.2D Acceptance Matrix

D 标记 FROZEN 前至少满足以下全部条件。

## 8.1 Routing / target correctness

```text
1. 只有 finalized unresolved 才能进入 D
2. pending/provisional B 不得进入 D
3. pending C 不得进入 D
4. structure parent + virtual children 可形成 atomic target_group
5. 无关 unresolved 不做 Cartesian product
6. Candidate 0 不被 D 修改
7. D 不直接执行 repair
```

## 8.2 Phrase correctness

```text
8. phrase 完整包含 target_group
9. phrase 长度默认 3–12s
10. target 前后有足够可听 context
11. 优先 LRC/silence/breath 边界
12. fallback 不在 target note 中间硬切
13. 相同 phrase context 可复用 source assets
```

## 8.3 Candidate correctness

```text
14. 每 item 最多 baseline + 3 alternatives
15. pitch candidates 来自 frozen B real hypotheses
16. structure candidates 来自 C explicit hypotheses / virtual notes
17. 不从 consensus median 合成整句 candidate
18. acoustic seed 不冒充 GAME truth
19. candidate dedupe 正确
20. compound pitch alternatives 使用 bounded beam，不全排列
21. candidate provenance 完整
```

## 8.4 Render fairness

```text
22. 所有 options 同 phrase start/end
23. 同 tempo / sample rate / renderer / voicebank / phonemizer
24. 除 target_group score_patch 外其它 score context 完全一致
25. 不做 per-candidate 独立 time warp
26. renderer latency correction 对所有 options 相同
27. 不做 per-candidate independent loudness normalization
28. shared candidate gain 可复现
29. 无 clipping
30. WAV sha256 记录
31. neutral render profile 不加入 personalized Yousa style
32. PITD 不掩盖 written-score difference
```

## 8.5 Review artifact correctness

```text
33. manifest.json machine-readable
34. package_hash 绑定 source/context/candidates/render/schema
35. option mapping 可审计
36. decision 绑定 review_item_id + package_hash
37. 每次选择即时持久化
38. review 可 resume
39. decision revision history 保留
40. stale package 自动使旧 decision 失效
```

## 8.6 Decision semantics

```text
41. Baseline -> human_resolved_keep / no repair
42. A/B/C -> human_selected_candidate / only eligible for M2.4
43. 都差不多 -> keep baseline / no repair
44. 都不对 -> no repair + regeneration queue
45. regeneration 最多 1 次（generation <= 2）
46. generation 2 仍 none_correct -> manual_followup_required
47. 用户永远不需要填写 MIDI/Hz/cents
```

## 8.7 Permanent safety / integration

```text
48. 189s review package 可生成且不自动 repair
49. 202s review package 可生成且不自动 repair
50. Candidate 0 hash 在 D 前后不变
51. frozen A/B/C regressions 全 green
52. remote core CI green on FINAL D acceptance SHA
53. core regression 无 skipped/disabled 伪 green
```

## 8.8 Local real-render acceptance

Remote CI 不具备用户本机 OpenUtau/Yousa 资产，因此 D freeze 还必须有本机 integration smoke test。

至少真实生成 3 类 review item：

```text
A. pitch-only unresolved
B. structure split/virtual-note unresolved
C. 189s 或 202s permanent ambiguous case
```

对每类确认：

```text
original/separated reference 正确
options 可播放
phrase window 正确
候选只有 target 差异
无明显响度作弊 / 时间错位 / 截断
manifest/hash 与音频对应
人工 decision 可保存 + resume
```

**D workflow freeze 不要求用户先把全部 46 条 review 完。**

冻结的是：

```text
package generation
render fairness
review UI/CLI
decision persistence
stale invalidation
```

全部实际 review decisions 可以之后逐步完成。

---

# 9. M2.4 — SAFE Repair Engine

进入实现条件：

```text
A/B/C frozen regressions remote green
C frozen acceptance confirmed
189s / 202s no false repair
D review workflow available
Candidate 0 / rollback contract complete
```

M2.4 可以处理两类输入：

```text
A. machine-safe finalized repair_candidate
B. D human_selected_candidate + exact package_hash decision
```

不得处理：

```text
pending / provisional / unresolved without human selection
stale review decision
human_no_preference
human_rejected_all
manual_followup_required
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
review_item_id/package_hash if human-selected
gates passed
rollback data
```

0 SAFE repairs 合法。

Structure repair 在 C adjudication precision + D review workflow 稳定前不得自动执行。

### D 与 M2.4 并行关系

D workflow 冻结后：

```text
machine-safe repair 可以开始进入 M2.4
```

不要求用户先审核完全部 D items。

但：

```text
某个 unresolved region 只有获得有效 human_selected_candidate 才可被 M2.4 修改
```

最终 M2.9 《年轮》验收前：

```text
不得残留未处理的高影响 phrase_review item
```

除非显式标记：

```text
accepted_unresolved / no_change
```

并保留原因。

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
phrase windows / boundary source
review candidates + score patches
render profile hash
review WAV hashes
package hash
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
### M2.3.2D — Phrase-level human review — WORKFLOW FROZEN @`0bbb098`（本机 smoke 通过；46 条人工 review 开放中，不阻塞）
### M2.4 — SAFE repair ← CURRENT
### M2.4 — SAFE repair
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
27. human decision 必须绑定 exact package_hash；stale review 不得授权 repair。
28. “都差不多”不得偷偷选择 machine winner。
29. “都不对”不得要求用户手工报正确音高；最多自动 regeneration 一次。
30. needs_phrase_review 只能在 machine-computable lanes 结束后产生。
31. 189s 永久 extractor-conflict regression。
32. 202s 永久 stochastic pitch/identity regression。
33. 0 repair 是合法结果。
34. 从 C2 起，没有 FINAL acceptance SHA 的 remote CI green，不允许 FROZEN/PASS。
35. 先把 written score 唱对，再生成 PITD。
36. 先“唱对”，再做泠鸢风格。
