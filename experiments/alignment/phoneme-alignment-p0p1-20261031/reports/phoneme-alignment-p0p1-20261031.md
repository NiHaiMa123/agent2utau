# P0～P1 实施报告：锁定歌词、GAME 归一化与确定性字—音符映射

日期：2026-10-31 ｜ 执行模型：MiniMax-M3.1-Flash（单 Agent）｜ 依据：[根目录 plan.md](../../../plan.md) P0–P1
run-id：`phoneme-alignment-p0p1-20261031` ｜ 本机 run：`runs/production/phoneme-alignment-p0p1-20261031/`（Git 忽略）

## 0. 本轮做了什么 / 没做什么

做了：P0（固定输入、盘点真实命令、稳定 ID、归一化时钟、选样本、出 baseline 工程）与 P1（确定性单调映射 baseline、窗口候选、硬约束校验）。
**没有做**：P2 起的音素基线、patch 写回、跨模型协议与评测；没有画 PITD、没有改 VOIC/BREC/TENC/DYN、没有动混音、没有改任何既有歌曲工程（读旧产物只读复制）。

## 1. P0

### 1.1 真实命令盘点（均为本机实测，非接口存在性推断）

| 命令 | 实测结果 |
|---|---|
| `agent2utau doctor` | OpenUtau **0.1.570.9011**，Core/bridge 就绪，声库 **YousaV1.65c**，phonemizer `DiffSingerChinesePhonemizer`，dsconfig 44100/hop 512，GPU RTX 5080 |
| `agent2utau observe-source` | 年轮原曲实跑 separate+asr+game **成功**（分离 5 分 09 秒，`status=completed`、`source_only=true`、`expression_generated=false`），产出 request/separation/asr/game/manifest + 人声与伴奏分离件；**但复跑不重现，见 §3.7** |
| `agent2utau export-phonemes` | 在 v3 年轮工程副本上：**51 part / 761 phone，ok=true**；在新建 baseline 样本上同样 ok |
| `agent2utau roundtrip` | 副本：**notes 650→650，phrases 51，lyrics_match=true，ok=true** |
| `agent2utau render-project` | baseline 样本渲染成功（5.17 MB wav，peak 0.273），交付审查结论为 `candidate only`（无执行审查合同，符合预期） |

结论：**"命令可用"已实测，但这不等于"一键闭环已完成"**——目前 observe-source 之后的 lyrics→notes→mapping→baseline 全部由本轮新增的 `agent2utau align-lyrics` 与 `alignment` 包完成，音素 patch 与原生写回（P2）尚未实现。

### 1.2 锁定歌词（`lyrics_locked.json`）

每首歌按出现顺序给每个唱字分配 `syllable_id`（`s0001…`），重复字各自独立 id 并带 `occurrence` 计数，`repeated` 标记哪些字在歌里出现过多次。

**歌词正文以公开权威歌词为准，ASR 只提供录音分句与时间提示。** 三首歌都是公开发行曲，取多源逐字比对一致的版本：

| 歌曲 | 权威歌词来源 | 校验方式 | 行 × 字 |
|---|---|---|---|
| 年轮 | 百度百科《年轮》词条（张碧晨版）＋搜狗百科交叉 | 检索通道取得渲染文本，逐字转写并与第二来源比对 | 49 × 349 |
| 最后一页 | 百度百科《最后一页》词条＋Musixmatch／爱曲谱交叉 | 同上 | 42 × 318 |
| 雨爱 | 快懂百科《雨爱》词条＋搜狗百科／中文百科交叉 | 同上 | 69 × 385 |

**公开歌词只定"唱了哪些字"，录音定"怎么分句、重复几次"**：`apply_canonical()` 用全局编辑距离（Needleman-Wunsch，CJK 参与对齐）把权威歌词映射回录音自身的分句，只替换字、不改分句结构；英文单词不参与对齐——写出来是 "Rainie Love"，唱出来是 3 个音节（Rai/nie/Love），音节数只能由录音与 HFA 决定。

实测校正结果（`lyrics_canonical_diff.json`）：

| 歌曲 | 权威字数 vs 录音字数 | 逐字相同 | 被纠正的字 | 未被唱到的公开句 | 保留录音的英文 |
|---|---|---|---|---|---|
| 年轮 | 349 / 349 | 347 | **2 处**（"有缘却无**份**"→"有缘却无**分**"） | 0 | 0 |
| 最后一页 | 318 / 318 | **318（全同）** | 0 | 0 | 0 |
| 雨爱 | 385 / 385 | 365 | 0 | 0 | 20 字（Rai/nie/Love ×2） |

最后一页的"318 字全同"是对此前 ASR＋Agent 纠词结果的**反向验证**：那份文本与公开歌词逐字一致。权威歌词正文不进入 Git（版权），只在本机 run 目录保存文本与出处，仓库里只留 URL、检索时间、文本哈希与差异计数。

**仍需用户拍板的是分句**：公开歌词按发行版分行，录音按演唱分行，两者不完全相同（年轮公开 49 行 / 录音 51 句）。本轮以录音分句为准。

### 1.3 GAME 归一化（`notes_normalized.json`）

保留 GAME 原始 `index/start/dur/tone/voiced`，附加 `note_id` 与 tick。tick 使用与 `openutau/build.py` **同一函数**（固定 120 BPM / 480 分辨率，960 tick/秒），且**以全局 start/end 边界一次量化**（duration = end_tick − start_tick），不会因分别舍入产生重叠。

| 歌曲 | 事件总数 | voiced / rest | 覆盖区间 |
|---|---|---|---|
| 年轮 | 469 | 400 / 69 | 18.34–242.69 s |
| 最后一页 | 410 | 368 / 42 | 14.21–238.10 s |
| 雨爱 | 478 | 425 / 53 | 16.22–237.51 s |

时钟原点统一为 `source_t0`（解码后的 source.wav 第 0 采样），GAME/HFA/ASR 同源同起点，无偏移。

### 1.4 输入绑定与模型哈希（`observations_manifest.json`）

每首歌记录：原曲路径与 SHA256、解码 wav、人声/伴奏分离件、锁定歌词、GAME、ASR、HFA 的路径与 SHA256、时钟原点、bpm/resolution、GAME 四个 onnx 的模型哈希、OpenUtau 版本与 Core/bridge/声库 dsconfig 的 SHA256。任何人拿到这份 manifest 都能证明"用的是同一批字节"。

### 1.5 样本与异常

`runs/production/phoneme-alignment-p0p1-20261031/samples/`：**22 个小样本**，覆盖计划要求的 8 类场景——一字一音（3）、多音连字（3）、重复字（3）、字头抢拍（3）、短元音（3）、休止在前（3）、跨句首字（3）、多音字（1，仅最后一页"没"mei/mo 与"重"chong/zhong 命中；年轮与雨爱原唱韵律中未出现一字多读）。每个样本是一份独立小 USTX，可直接喂给原生 phonemizer。

异常清单（`anomalies.json`，按来源分列）：时钟 gap（年轮 17 / 最后一页 17 / 雨爱 12，全部是 GAME 相邻事件之间的真实空隙，不是量化错误）、观测匹配（年轮 62 缺 + 8 位置回退 + 1 残差匹配；最后一页 203 缺 + 3 位置回退 + 130 残差匹配；雨爱 0）、映射硬约束问题 **0**、USTX 问题（最后一页 1）。

### 1.6 baseline 工程

每首歌一份 `baseline.ustx`：只含唱字与 `+` 延音块，默认音高曲线与默认发声，无人工 PITD、无发声参数改动。年轮 391 音符 / 最后一页 367 / 雨爱 413。

## 2. P1

### 2.1 确定性映射

在 **字序号 × 音符序号** 的动态规划上求全局最优单调映射（`src/agent2utau/alignment/candidates.py`）。成本项与阈值全部写死在 `MappingConfig` 里，不随模型变化：

- 锚点误差 `|HFA 锚点 − 音符起点| / 0.35s`（HFA 优先于 ASR；ASR 只是提示，不能改词）
- 时长误差 `|观测时长 − 音符时长| / 0.5s`，**上限 1.0**，且观测短于 0.08 s 时整项不计（HFA 碎片字会带偏映射，这是实测踩到的坑）
- 每多一个连音音符 +0.35；每丢下一个 voiced 音符 +0.8；判定 unresolved +1.5
- **结构硬规则**：一个字只能拥有**原始序号连续**、全部 voiced 的音符——中间隔一个休止就不许跳过去（修正前雨爱出现过一个字吞掉 19 秒后音符的错误）

### 2.2 结果

| 歌曲 | 字数 | 已映射 | unresolved | 音符已归属 | 歧义窗口 | 候选数 |
|---|---|---|---|---|---|---|
| 年轮 | 349 | **345（98.85%）** | 4 | 391/400 | 15（9 个多选项） | 71 |
| 最后一页 | 318 | **318（100%）** | 0 | 368/368 | 6（6 个多选项） | 46 |
| 雨爱 | 371 | **366（98.65%）** | 5 | 413/425 | 7（1 个多选项） | 6 |

覆盖口径按计划要求：**每个字都有去向**（映射或显式 unresolved），`coverage.syllable_mapped + syllable_unresolved == syllable_total`；unresolved 不计入成功，覆盖率与成功率分别记录。

### 2.3 硬约束校验

`src/agent2utau/alignment/validator.py` 逐条检查并全部通过（0 问题）：字序完整无跳字/换字/加字；同一音符不被两个字共享；一字的音符在原始序号上连续；映射在音符序上单调；休止音符从不分配给字；时长相���；unresolved 必须带 reason_code；覆盖算术自洽；候选 id 不重复。`mapping.v1.json` 另受 `schemas/alignment_evidence_v1.schema.json` 约束，并由 `tests/contracts/test_alignment_evidence.py` 实际校验。

### 2.4 窗口候选

歧义窗口按 5～15 字成组，每个候选 `map:<song>:<window>:<option>` 由**代码枚举**产生：窗口内音符预算固定（不抢邻居的音符），用前缀/后缀代价表枚举窗口内的替代分配，并按真实总代价排序、带精确 cost。Agent 之后只需返回 candidate_id 或 unresolved。**雨爱 7 个窗口里只有 1 个有多选项**——说明该歌的映射比另外两首更"干净"，也说明 P3 给模型的问题量很少。

## 3. 已知问题与限制（不得视为已解决）

1. **歌词分句仍以录音为准，未逐句经用户确认。** 正文字符已改用公开权威歌词（年轮纠正 2 字；最后一页 318 字与公开歌词全同），但公开歌词按发行版分行、录音按演唱分行（年轮公开 49 行 / 录音 51 句），本轮以录音分句为准；若用户要求按发行版分行，需要重跑映射。
2. **GAME 在快唱段过切分**：年轮 400 个 voiced 音符对应 349 个字，多出的音符只能部分被连音吸收，剩下 4 个字判为 unresolved；雨爱同类情况 5 个。
3. **最后一页有 1 个 `+` 延音块因 160 ms 间隙无法成链**（`n0060`），baseline 已丢弃该音符并在异常清单登记（映射本身仍然成立）。
4. **多音字只在最后一页命中**，年轮与雨爱的原唱韵律中未出现一字多读；样本覆盖因此只有 1 个多音字样本。
5. **未做音素层面的任何验证**：本轮没有调用声库 phonemizer 生成 baseline 音素，也没有 patch 写回；P2 之前不存在"音素已对齐"的说法。
6. **听感完全未验证**：`musical_quality=unverified`、`listening=unknown`。本轮只产出结构化证据，不产出可听交付物。
7. **GAME 不可复现（实测）**：同一原曲（`source_sha256` 相同）、**逐字节相同的 source.wav 与两个分离件**、**五个 GAME onnx 模型哈希全部相同**、`seed=11` 相同的情况下，两次 `observe-source` 得到的音符事件不同（469 vs 467，前 17 个事件一致后分叉）。推断是 ONNX Runtime 多线程执行的浮点非确定性在 D3PM 分割循环里放大了边界决策差异。**后果：GAME 音符事件必须按 SHA256 固定复用，不能在后续轮次里重新生成**；本轮的 `observations_manifest.json` 已经这样绑定。

## 4. 产物与命令

本机（Git 忽略）：`runs/production/phoneme-alignment-p0p1-20261031/`
```
observations_manifest.json（每首歌一份，在 <song>/ 下）
<song>/lyrics_locked.json  <song>/notes_normalized.json  <song>/mapping.v1.json
<song>/anomalies.json      <song>/baseline.ustx         <song>/observations_manifest.json
<song>/lyrics_canonical_diff.json   公开歌词与录音分句的逐字差异
canonical_lyrics/<song>.json        公开权威歌词正文＋出处（版权原因不入 Git）
samples/index.json  samples/<song>/<sample>.ustx  samples/<song>/<sample>.phones.json
command-inventory/（doctor 探针副本、export-phonemes、roundtrip、render、observe-source 实跑）
run_summary.json  environment.json
```

提交到仓库：`src/agent2utau/alignment/`（lyrics、notes、observations、candidates、canonical、validator、baseline、pipeline）、`schemas/alignment_evidence_v1.schema.json`、`tests/unit/test_alignment_{lyrics,notes,mapping,canonical}.py`、`tests/contracts/test_alignment_evidence.py`、`experiments/alignment/phoneme-alignment-p0p1-20261031/`（scripts + reports + manifest）。

复现命令：

~~~powershell
python -m pip install -e .
agent2utau doctor
agent2utau align-lyrics --lyrics "<song>/lyrics_locked.json" --game "<game.json>" --hfa "<hfa.json>" --out "<dir>" --baseline "<dir>/baseline.ustx"
python experiments/alignment/phoneme-alignment-p0p1-20261031/scripts/build_p0p1_artifacts.py
python experiments/alignment/phoneme-alignment-p0p1-20261031/scripts/build_p0_samples.py
~~~

## 5. 下一轮最小任务（P2）

1. 用户确认三首歌的**分句**是否采用公开歌词的发行版分行（当前采用录音分句）。
2. 用本轮 baseline.ustx 真实调用声库 `export-phonemes`，建立 `phoneme_baseline.json`（P2 第 1 项）。
3. 把 HFA 观测与原生预测做 A/B/C 分类，只对 B 类生成带 id 的局部候选。
4. 任何写回前先在真实 Core 上核实 `phoneme_overrides` 的 offset/duration 语义（**不要凭 YAML 字段名猜**）。
