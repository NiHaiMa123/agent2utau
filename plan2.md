# agent2utau — Plan 2：GAME 主转谱 + 证据驱动校正 + 分阶段演唱建模

> 修订日期：2026-09-16
>
> 核心原则：**先把“唱对”解决，再把“唱得像泠鸢”解决。**
>
> 当前工程原则：**GAME 负责给出真实可用的乐谱候选；多次 GAME consensus 只作为 uncertainty / evidence graph，不直接生成最终谱面。先把 residual errors 筛到很少，再决定 repair 做多重。**

---

## 1. 项目目标

输入原曲后，自动完成：

```text
原曲
→ 人声/伴奏分离
→ GAME 转谱
→ 多次 GAME 自一致性分析
→ RMVPE + FCPE 双 F0 校验
→ 歌词时间证据
→ 局部 residual-error triage
→ 只修强证据错误
→ 歌词映射
→ OpenUtau / DiffSinger 渲染
→ PITD / 演唱细节
→ 最后再做泠鸢风格迁移
```

旧主旋律生成：

```text
歌词字窗口
→ F0 中位数
→ heuristic split
→ MIDI note
```

已经确认能力不足，只保留为显式 fallback，不再作为默认 melody transcription。

---

## 2. 当前已经完成的基础设施

仓库已经真正接入：

- 官方 GAME 1.0.3-medium ONNX；
- 官方 RMVPE ONNX；
- FCPE；
- GAME `encoder → segmenter → bd2dur → estimator`；
- OpenUtau AudioSlicer 等价切片；
- GAME 多次同配置推理；
- `diagnose --repeats N`；
- GAME USTX + DiffSinger render；
- RMVPE / FCPE evidence packets；
- lyric-boundary matching；
- voiced-island structural F0；
- 正式 order-preserving sequence alignment；
- `1↔1 / gap / 1↔2 / 2↔1` 显式关系；
- 多 run stochastic consensus；
- octave benchmark evidence packet。

forced char `known_boundaries` 路径已经降级为实验用途，不进入默认主链。

---

# Part A — 当前已经确认的事实

## 3. GAME 本身比旧 heuristic 强很多

早期错误诊断曾得到：

```text
A raw ≈ 419 notes
B zh  ≈ 417 notes
C forced-char-boundary ≈ 760 notes
```

最初在 C 上看到的：

```text
76 suspicious
54 wrong_pitch
```

不能代表 GAME raw 错误率，因为 C 把大量字符起点强行变成 GAME boundary，改变了 segmentation 和 estimator。

因此：

- GAME raw 是主转谱来源；
- lyric char start 不是天然 note boundary；
- F0 不是从零主转谱器；
- correction 目标是修 GAME 的少量 residual errors，而不是重建整首 MIDI。

---

## 4. GAME 存在真实 stochasticity

同一个 separated vocal、同一参数，多次 GAME ONNX 会出现局部结构差异。

《年轮》实测单次 raw GAME 约：

```text
418–425 voiced notes / run
```

因此：

```text
single GAME run != deterministic truth
```

但这不是缺点，反而可以作为 uncertainty evidence。

多次都一致：更可信。
多次出现 split/merge/pitch 多解：局部不确定。

---

## 5. M2.2A 正式 sequence alignment 已完成

旧临时方案：

```text
150 ms onset greedy clustering
```

已经废弃为正式依据。

当前 `diagnostic/seqalign.py` 使用：

```text
order-preserving DP
+ onset cost
+ IoU / overlap cost
+ duration cost
+ capped weak pitch cost
+ gap
+ split
+ merge
```

显式输出：

```text
1 ↔ 1   same-note candidate
1 ↔ 0   missing in one run
0 ↔ 1   extra in one run
1 ↔ 2   split disagreement
2 ↔ 1   merge disagreement
```

随后对所有 unordered run pairs 建立 relation，再形成多 run consensus evidence。

测试已经覆盖：

- stable event；
- low presence；
- pitch disagreement；
- split/merge；
- 两个独立事件不误合并；
- 80 ms 快速相邻 notes；
- run-order independence。

---

## 6. 最新正式 consensus 结果

《年轮》新鲜 5+5 runs：

```text
raw note counts: 418–425
zh note counts:  418–429
```

raw consensus evidence graph：

```text
397 events
348 GAME_STABLE
2   GAME_VARIABLE
47  GAME_UNSTABLE
43  events 存在 split/merge structure variance
```

raw consensus vs zh consensus：

```text
390 matched
14 pitch disagreements > 1 semitone
```

结论：

> GAME 主体旋律很稳定，真正需要关注的是几十个局部结构不确定区域，而不是整首重写。

---

## 7. M2.2B 双 F0 已完成并证明必要

此前最强 octave candidate：

```text
~189.84 s
GAME ≈ MIDI 58.1
RMVPE ≈ MIDI 69.96
```

单看 RMVPE，会认为 GAME 低了约一个八度。

加入 FCPE 后：

```text
GAME   ≈ 58.1
FCPE   ≈ 58.03
RMVPE  ≈ 69.96
```

即：

```text
RMVPE vs FCPE ≈ 1193 cents
GAME ≈ FCPE
```

正确工程结论不是“GAME 已被证明正确”，而是：

> **这是 extractor conflict；目前没有足够证据修改 GAME。进入 AMBIGUOUS，禁止 SAFE repair。**

这个案例已经证明：

> **任何单一 F0 extractor 都不能独自推翻 GAME。**

否则这里会产生一次错误的 octave repair。

---

# Part B — 最重要的架构修正

## 8. Consensus 是 uncertainty / evidence graph，不是最终 note skeleton

这是当前最重要的新约束。

正式 alignment 会把不同 run 的结构分歧合并到一个局部 event，例如：

```text
run A:
A4 ─────────────

run B:
A4 ───── | B4 ─────
```

可能形成：

```text
run_note_counts = [1, 1, 1, 1, 2]
structure_varies = true
```

因此一个 consensus event 的语义是：

> **“多次 GAME 对这一局部 musical region 的对应关系与不确定性描述。”**

而不是：

> “这个 event 就是一颗最终 MIDI note。”

所以：

```text
397 consensus events != 最终谱面 397 notes
```

禁止把：

```text
start_median
duration_median
tone_median
```

直接拼成一首合成 MIDI / USTX。

`event_as_note()` 只可用于 diagnostic / cross-consensus comparison，不得直接作为最终可渲染 score source。

---

## 9. 最终可渲染 baseline 必须来自真实 GAME run

正式主链改为：

```text
GAME raw run #1 ─┐
GAME raw run #2 ─┤
GAME raw run #3 ─┤
GAME raw run #4 ─┤→ consensus evidence graph
GAME raw run #5 ─┘
                    ↓
           选择一个真实 GAME run
           作为 concrete baseline score
                    +
           consensus uncertainty evidence
                    ↓
          只修改局部 residual errors
                    ↓
              corrected score
```

推荐 baseline 选择方法：**GAME medoid run**。

即在多次 run 中选择：

```text
对其他 runs 的总 alignment cost 最小
或
与 consensus structure 支持度最高
```

的那一次真实 GAME 输出。

这样：

- 初始谱面中的每一颗 note 都来自真实 GAME 推理；
- 不会生成不存在于任何 run 的“median 合成结构”；
- correction 仍然有清晰 Candidate 0；
- 所有修改都可局部 audit / rollback。

---

## 10. Union-find 只负责 uncertainty region，不负责决定唯一结构

当前所有 pairwise alignment relation 通过 union-find 形成 component，可以保证 run-order independent，但存在天然的 transitive bridging 风险：

```text
A1 ↔ B1
B1 ↔ C2
C2 ↔ D2
```

最终可能形成同一个 connected component，即使 A1 与 D2 直接关系并不强。

因此：

- STABLE `1↔1` component 可以直接作为高置信 evidence；
- 包含 split/merge/transitive bridge 的 component 只表示 **local ambiguity region**；
- 不要求把 component 压缩成唯一 note；
- 后续 structure repair 必须回到具体 GAME runs + F0 + onset/energy evidence 决策。

这比继续把 consensus graph 复杂化成“唯一正确谱”更符合项目目标。

---

# Part C — F0 Evidence

## 11. RMVPE + FCPE 的职责

双 F0 用于：

- wrong-pitch evidence；
- octave evidence；
- boundary / plateau evidence；
- split / missed-split evidence；
- 后续 PITD；
- render 与 reference 比较。

禁止恢复：

```text
F0 median → 从零生成全曲 note
```

---

## 12. 双 F0 判定规则

### 两个 extractor 一致反对 GAME

例如：

```text
GAME   A5
RMVPE  A4
FCPE   A4
```

且：

- voiced coverage 高；
- stable plateau 明确；
- 两个 extractor IQR 合理；
- aligned note identity 清楚；

才允许进入 hard-suspicious / SAFE candidate。

### extractor conflict

例如当前 189.84s：

```text
RMVPE  A4
FCPE   A3
GAME   A3
```

则：

```text
AMBIGUOUS
```

禁止自动修。

---

## 13. Full-window median 不足以处理 structure-varies 区域

当前每个 GAME note window 内的 RMVPE/FCPE median center 对稳定 note 足够好，但对：

- split；
- merge；
- missed split；
- portamento；
- 快速转音；

可能过于粗糙。

下一阶段增加 **stable plateau evidence**：

```text
local note / uncertainty window
→ 去掉 onset / offset transition
→ 找持续稳定 pitch plateau
→ RMVPE / FCPE plateau comparison
→ changepoint evidence
```

结构问题优先比较 plateau，而不是整段 full-window median。

---

## 14. Structural F0

当前已改为：

```text
raw F0
→ 只填 <=40 ms 短 unvoiced gap
→ 按连续 voiced island 独立 filtering
→ structural F0
```

长 silence 不跨岛过滤。

职责：

- structural F0：note / boundary / plateau evidence；
- raw F0：PITD / vibrato / portamento / intonation。

所有 pitch error / dispersion 对外统一 cents。

`high_dispersion` 只作为 feature，不单独触发 suspicious。

---

# Part D — Lyrics Evidence

## 15. Lyric timestamp 永远不是默认 note boundary

当前《年轮》歌词边界相对 GAME 大量存在 80–300 ms 偏差。

必须区分：

```text
Whisper char start
辅音起点
元音起点
F0 voiced onset
GAME note onset
```

歌词证据只用于：

```text
matching
articulation evidence
weak boundary snap evidence
missing-boundary evidence
lyrics ↔ notes mapping
```

禁止：

```text
char start → 强制新增 GAME boundary
```

只有：

```text
GAME structure/boundary 不稳定
+
F0 changepoint 支持
+
energy/onset 支持
+
lyric articulation 支持
```

才产生 boundary repair candidate。

---

# Part E — 当前最高优先级：M2.3 Residual-Error Triage

## 16. 目标

现在不再继续证明“GAME 会不会错”，而是回答：

> **整首《年轮》约 420 个 GAME notes 中，双 F0 + consensus 后，到底还有多少 region 真正值得修改？**

先筛全曲，再决定 repair engine 要做到多复杂。

---

## 17. 第一步：选 concrete GAME baseline

从 5 次 raw GAME 中选 medoid run：

```text
baseline_run_id
baseline_note_count
sum_pairwise_alignment_cost
consensus_support_ratio
```

输出：

```text
diagnostic/baseline_game.json
```

后续所有 repair 都以这个真实 run 为 Candidate 0。

---

## 18. 第二步：把 baseline notes 映射到 consensus evidence graph

每颗 baseline note 至少得到：

```text
GAME stability
presence_rate
tone agreement
boundary spread
structure relation
run_note_counts
whether transitive / split-merge ambiguity exists
```

不要把 consensus event 变成 note；只给 baseline note 附加 uncertainty evidence。

---

## 19. 第三步：加入 dual-F0 + plateau evidence

每个 baseline note / local uncertainty region 输出：

```text
RMVPE center / IQR / coverage
FCPE center / IQR / coverage
RMVPE vs FCPE cents
GAME vs RMVPE cents
GAME vs FCPE cents
stable plateau(s)
plateau changepoints
voiced transition
energy/onset evidence
lyric evidence
```

---

## 20. 第四步：全曲 triage 分类

统一分成：

```text
GAME_LIKELY_CORRECT
F0_EXTRACTOR_CONFLICT
PITCH_HARD_SUSPICIOUS
STRUCTURE_HARD_SUSPICIOUS
AMBIGUOUS_ORNAMENT
NEEDS_LISTENING_REVIEW
```

### GAME_LIKELY_CORRECT

- consensus 稳定；
- 双 F0 不强烈反对；
- 无结构冲突。

不处理。

### F0_EXTRACTOR_CONFLICT

例如 189.84s。

不修改 GAME，只记录 extractor disagreement。

### PITCH_HARD_SUSPICIOUS

要求：

```text
RMVPE + FCPE 一致
AND 两者共同反对 GAME
AND stable plateau
AND note identity 清楚
```

### STRUCTURE_HARD_SUSPICIOUS

例如：

```text
GAME runs 存在 1↔2 / 2↔1 disagreement
AND 双 F0 有明确多个/单个平台
AND onset/energy 支持某个结构
```

### AMBIGUOUS_ORNAMENT

复杂 vibrato / grace / portamento / 快速转音。

不自动修改。

---

## 21. M2.3 输出

```text
runs/<id>/diagnostic/
  baseline_game.json
  consensus_raw.json
  residual_triage.json
  residual_triage_summary.json
  plateau_evidence.json
  review_regions.json
```

summary 必须回答：

```text
baseline note count
likely-correct count
F0 conflict count
pitch hard-suspicious count
structure hard-suspicious count
ambiguous count
人工 review count
```

禁止继续用 feature flag 总数冒充 error count。

---

# Part F — Repair Engine

## 22. 是否需要重型 repair，由 M2.3 数据决定

预期可能出现：

```text
~420 GAME notes
↓
绝大多数 likely correct
↓
少量 needs review
↓
个位数到十几个真实 residual errors
```

如果真实错误很少，就保持 correction layer 很轻。

不要为了“系统完整”实现大量实际用不到的复杂规则。

---

## 23. Candidate 0

永久保留：

```text
Candidate 0 = selected real GAME medoid run
```

不是 synthetic consensus score。

每个局部 repair 都必须：

- before / after；
- evidence；
- reason；
- confidence；
- rollback；
- A/B render。

---

## 24. SAFE repair

第一批仅允许已经真实确认的强证据类型。

可能包括：

```text
wrong pitch retune
octave ±12 semitone
very small boundary correction
```

但必须满足：

```text
aligned note identity clear
GAME baseline known
GAME consensus evidence known
RMVPE + FCPE agree
stable plateau / voiced evidence
repair local only
A/B validation passes
```

189.84s **不属于 SAFE benchmark**；它现在是 extractor-conflict regression case，用于保证系统不会误修。

---

## 25. PROBABLE / AMBIGUOUS repair

### split / merge

只有正式 sequence alignment 已经发现 `1↔2 / 2↔1`，并且 plateau / onset / energy 进一步支持时才产生候选。

### missed split

长 note 内有多个持续稳定 plateau。

修改 boundary 后优先调用 GAME estimator 重估局部 pitch。

### boundary shift

只在原 boundary 周围小窗口搜索。

### false / missing note

风险高，默认 PROBABLE / AMBIGUOUS。

复杂 ornament 不自动修。

---

## 26. Candidate scoring

候选：

```text
C0 real GAME baseline
C1 retune
C2 boundary shift
C3 split
C4 merge
C5 local combined repair
```

证据：

```text
GAME presence consensus
GAME pitch consensus
GAME structural stability
sequence-alignment relation
RMVPE agreement
FCPE agreement
plateau fit
voiced consistency
energy/onset evidence
lyric compatibility
duration plausibility
local melodic continuity
complexity penalty
unsupported-edit penalty
```

必须设置 minimum improvement。

原则：

> **宁可保留 GAME 的小错误，也不要让 correction 制造新错误。**

---

# Part G — Lyrics / USTX / PITD

## 27. Lyrics ↔ corrected melody

melody 稳定后再做：

```text
1 char → 1 note
1 char → N notes（melisma）
N chars → N notes
```

OpenUtau：

```text
首 note：真实歌词
同字后续：+
换气：AP
静音：gap / SP
```

歌词冲突时标 `lyric_alignment_conflict`，不得通过“移动到最近 voiced block”伪修复。

---

## 28. 基础 USTX 验收

第一阶段只含：

- corrected score；
- lyrics；
- timing；
- singer / renderer；
- 必要 phonemizer 设置。

核心验收：

> **不做泠鸢风格和复杂 PITD 时，是否已经唱对《年轮》的旋律和节奏？**

未通过不得进入 style 阶段。

---

## 29. raw F0 → constrained PITD

score 通过后才加入：

- portamento；
- 音头滑入；
- ornament；
- vibrato；
- intonation deviation。

PITD 不得掩盖 written-note 错误。

---

# Part H — Evaluation

## 30. Diagnostic level

至少记录：

- 每次 GAME run note count；
- pairwise alignment cost；
- medoid baseline run；
- `1↔1 / gap / split / merge` 数；
- consensus stability；
- residual triage 分类数量；
- RMVPE/FCPE agreement；
- plateau evidence；
- confirmed errors；
- validator false positive / false negative。

---

## 31. Score level

记录：

- corrected vs real GAME baseline；
- retune；
- octave repair；
- split / merge；
- boundary shift；
- ambiguous；
- GAME preservation ratio。

GAME preservation ratio 应尽量高。

---

## 32. Render level

比较：

```text
reference F0
real GAME baseline score
corrected score
rendered DiffSinger F0
```

区分：

- transcription error；
- F0 extractor error；
- lyric alignment error；
- PITD error；
- DiffSinger render deviation。

旧 per-note median cents 只能做辅助指标。

---

# Part I — Milestones

## 33. 当前实施顺序

### M2.0 — Foundation survey ✅

GAME / RMVPE / dataset-tools / SlurCutter 等基础调研完成。

### M2.1 — Initial diagnostic ✅

完成并纠正 forced-boundary 误读。

### M2.1.1 — Diagnostic correctness ✅

完成 cents、raw-first、time alignment、lyric evidence-only、voiced-island structural F0 等修复。

### M2.1.2 — GAME stochastic baseline ✅

完成多次 GAME、stochasticity 测量和初版 consensus。

### M2.2A — Formal sequence alignment ✅

完成 DP `match/gap/split/merge`、run-order-independent consensus evidence。

### M2.2B — Dual-F0 evidence ✅

完成 RMVPE + FCPE；189.84s 已成为 extractor-conflict regression case，成功阻止潜在误修。

### M2.3 — Residual-error triage ← 当前最高优先级

必须完成：

1. 从真实 GAME runs 中选择 medoid baseline；
2. consensus 明确只作为 uncertainty/evidence graph；
3. baseline notes 映射 consensus evidence；
4. 增加 stable plateau / changepoint evidence；
5. 双 F0 全曲 triage；
6. 输出 likely-correct / F0-conflict / pitch-hard / structure-hard / ambiguous；
7. 人工只试听 review regions；
8. 得到真实 residual-error distribution。

### M2.4 — SAFE repair

只实现 M2.3 实际确认出来的强证据错误类型。

### M2.5 — PROBABLE candidate system

只有实际需要时才扩展 split / merge / missing-note scorer。

### M2.6 — Optional second opinion

只有 GAME + formal alignment + dual F0 + lyric evidence 仍不足时才接 ROSVOT。

### M2.7 — Lyrics mapping + base USTX

corrected real score → lyrics / melisma → 可编辑工程。

### M2.8 — PITD + render loop

raw F0 → constrained PITD → DiffSinger → 三层评价。

### M2.9 — 《年轮》M2 验收

主要比较：

```text
selected real GAME baseline
vs
corrected score
```

通过后冻结 melody score。

### M3 — 泠鸢 style profile

只有 M2.9 通过后开始。

分析：

- vibrato rate/depth；
- portamento；
- 音头；
- 句尾；
- breath placement；
- dynamics；
- tension / breathiness；
- voice color；
- 音区差异。

原则：

> **原唱决定“唱什么”；泠鸢参考决定“怎么唱”。**

---

# 34. 最终原则

1. **GAME 是默认 melody transcription 基座。**
2. **最终可渲染 baseline 必须来自真实 GAME run，而不是 synthetic consensus。**
3. **推荐选择 medoid GAME run 作为 Candidate 0。**
4. **Consensus 是 uncertainty / evidence graph，不是 note skeleton。**
5. **397 consensus events 不等于 397 个最终 notes。**
6. **包含 split/merge/transitive bridge 的 component 只表示 local ambiguity。**
7. **RMVPE + FCPE 是双 F0 evidence，不是主转谱器。**
8. **双 F0 冲突时禁止 SAFE repair。**
9. **189.84s 当前是 extractor-conflict regression case，不得 octave 修。**
10. **stable plateau 比 full-window median 更适合判断结构问题。**
11. **high dispersion 是 feature，不是错误。**
12. **歌词 char timestamp 不是 note onset。**
13. **自动 repair 只针对 M2.3 筛出的真实 residual errors。**
14. **如果真实错误只有个位数/十几个，就保持 correction layer 轻量。**
15. **Candidate 0 永远可回退。**
16. **所有修改必须局部、可解释、可审计、可 A/B、可 rollback。**
17. **复杂区域宁可 needs_review，不强行自动修。**
18. **先把 written score 唱对，再生成 PITD。**
19. **先“唱对”，再做泠鸢风格。**
