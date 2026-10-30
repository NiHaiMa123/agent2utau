# 年轮 v3：按 B 站手工作业方式整曲重制（2026-10-30）

- 目录：`runs/production/nianlun-from-scratch-v3-20261030`（v1、v2 目录全部保留未改）
- 触发：用户判定 v1「差到我无法给出具体的建议」，v2 之后仍判「现在这个完全不行」，并要求按 B 站《DiffSinger/全流程 若我不曾见过太阳 翻调 从 midi 到成品》那套「人对着参考原唱一条条手调」的流程重做。
- 本轮结论：**画线方式换成照源直描**（中心线 = 原唱双检测器一致 F0 迹线），并补上音素对齐、音节细分、逐音符发声层；复检契约从「10 处动作未达成 / 66 处不可区分」变成「0 处未达成 / 0 处不可区分」。
- **听感仍未验证**：`musical_quality=unverified`、`listening=unknown`。本机没有可用的听感工具，下面的数字只证明「画线与渲染与源一致」，不证明「好听」。

---

## 一、B 站流程 → v3 的落地映射

| B 站流程里的做法（关键帧实证） | v3 的落地 | 本轮实测 |
|---|---|---|
| 先把参考曲（网易云 Hi-Res）与干声准备好，人声分离 | 沿用 v1/v2 的 MelBand Roformer 干声 + FCPE∧RMVPE 双检测器 F0 | 源观测与 v2 同源同种子 |
| OpenUtau 导 MIDI → 音素对齐（lao→lao/s/ting） | **音素对齐落地**：用 `phoneme_overrides.offset` 把每个音节的元音起点移到源里 F0 锁定点 | 87 个音节被移动，中位对齐误差 **142.3ms → 5.6ms** |
| 音符块内画音高线（照参考原唱的曲线） | **中心线 = 源迹线直描**：去尖刺→线性补齐→50ms 中值平滑→25ms 节点采样；节点斜率用单调限制（Fritsch–Carlson）防过冲 | 设计 vs 源迹线：逐句 p90 偏差 **约 20–27c**（v2 为 57.4c） |
| 六参数轨（DYN/PITD/ENE/BREC/TENC/GENC），按维度分遍精调，ENE 为主 | 本声库 YousaV1.65c **没有 ENE/GENC**（`use_energy_embed=false`、`use_falsetto_embed=false`），只能用 VOIC/BREC/TENC/DYN 四个可用轨 | 四条曲线**逐音符**取值（585 个唱字各有断点），不再按段落套值 |
| 颤音描原唱 F0 纹路 | **涟漪组件**：对每个 ≥0.24s 的唱字做局部线性去趋势 + 频谱锐度检测 + 最小二乘拟合，取实测主频/幅度/相位/进入退出点写成 `oscillation` 组件 | 18 个唱字写出涟漪组件（其余 567 字源里没有可测的周期成分） |
| 一个音节拆成多个音符块 | **音节细分**：源轮廓偏离名义音高 >420c 的字，在级差点拆成「字 + 延长块」，各自带音高 | 31 处细分；同时把 PITD 越界从 18 帧降到 0 帧 |
| 渲染 → 回听 → 改参数 → 再渲染（闭环） | **数值化闭环**：渲染后逐音符测 F0/RMS/HNR 与源的差；再用剂量-响应探针（一次只改一个参数档位）测本声库的参数权限 | 渲染 vs 源：逐音符 F0 中位偏差 **4.2c**（p90 15.4c）；探针测得 dyn **+0.083dB/单位**、voic +0.013dB HNR/单位、brec −0.018dB HNR/单位（且 +6.1Hz 亮度/单位）、tenc −0.013dB HNR/单位 |
| 混音时把成品人声放到与参考同一相对响度 | **回改**：按原唱干声/伴奏的相对 RMS（−19.19dB vs −17.88dB，差 −1.31dB）设混音增益 | 成品混音比例 **−1.35dB**（与人声 +0.8dB / 伴奏 −4dB 对应），与原唱差 0.04dB |
| 和声同音源多轨 | 本轮未做（源干声里没有可分离的和声轨，判断不出） | — |

不可迁移的部分：视频用的是 **AIkie秋绘** 声库（带 ENE/GENC），本机只有 **YousaV1.65b/c**（DiffSinger 型），所以「ENE 为主」的精调轴在本轮没有对应参数，只能用 VOIC/BREC/TENC/DYN 近似，报告里如实标注。

---

## 二、v3 相对 v2 的七项改动

1. **中心线换成源迹线直描**。v2 是「名义音高平台 + 0.8×源残差 + 70–250ms 斜坡」，v3 直接描原唱的双检测器一致迹线，平台化与压平消失。
2. **字间连接改成边界中心过渡**。v2 把整段连接塞进前一个音的尾部，会把该音自身的旋律抹平（实测：p20 的「承」源里 66→60.9→69.1 的往返被压成一条上行斜坡）；v3 改成在音符边界附近做过渡，两侧轮廓各自保留，只有跳变被平滑。
3. **音素对齐**。探针确认本机 OpenUtau+Yousa 的 `phoneme_overrides` 只有 `offset` 生效（`advance` 完全无效），且 `offset` 移动的是音素**起点**、前一个辅音会自动拉伸补足。87 个音节按此把元音起点移到源里 F0 锁定点。
4. **音节细分**（B 站的「音节拆成多个音符块」）：31 处，附带解决 PITD 预算越界。
5. **发声层降到逐音符**。VOIC/BREC/TENC/DYN 四条 part 级曲线按每个唱字的源实测（谐噪比、谱重心、音高、能量）取值，585 个唱字各有断点；v2 是每句一个值（51 组）。
6. **涟漪写成显式组件**。18 个唱字的原唱 F0 周期成分写成 `oscillation`（频率/幅度/相位/进入退出点全部来自源），其余唱字不写组件——**349 个组件降到 18 个**，模板化的结构问题在量级上消失。
7. **判据改成可区分 + 生成期自检**。每个单元的判据在生成时用「名义音高对照」（把偏离削到 ±25c）先自检：只有能被对照否掉的单元才声明 `must_differ`。结果 must_differ 109 / may_match 240，复检里 **非区分 0 处**（v2 为 66 处），并且判据在生成期自检失败 0 处。

### 过程中的四个实质修正（都写进了脚本注释）

- **双检测器分歧的空档不能直接丢掉**：快速滑音时两个检测器会打架（实测 p18 有 180ms 空档），直接丢掉会让中值滤波把滑音端点当尖刺抹平。改为「去孤立单帧尖刺 → 线性补齐 → 平滑」，全曲只涉及 2 个字、2 处空档。
- **旋律下滑不能拟合成低频涟漪**：初版涟漪检测把「66→60.9 的下滑」拟合成 3Hz 正弦（幅度 800c），污染了中心线。改为要求「频谱峰锐度 ≥2、峰占带内能量 ≥0.2、振幅 ≤ 该字旋律跨度的 35%、该字至少容纳 2.5 个周期」，否则不写组件。
- **三次 Hermite 会过冲**：陡坡处节点斜率按中央差分取会让插值冲出节点值。改为单调斜率限制。
- **判据测量域必须与设计取值域一致**：字边界外源没有 F0 时，只在窗口上测跨度会与设计实际画出来的不一致（实测 4 个单元误判）。改为在「源侧虚拟迹线」上测量，并把该字没有源帧时的回退（源全局电平）也纳入。

---

## 三、同口径数字（v1 / v2 / v3）

| 指标 | v1 | v2 | v3 |
|---|---|---|---|
| 设计 vs 原唱 F0（逐音符，p90） | 311.7c | 57.4c | **约 20–27c** |
| 渲染人声 vs 原唱 F0（逐音符中位 / p90） | 未测 | 未测 | **4.2c / 15.4c** |
| PITD 预算越界帧（±1200c） | — | — | **0** |
| 中心线节点 / 零斜率占比 | 1248 / 75% | 13989 / 28% | 9188 / 43% |
| 动作组件总数 / 固定幅度组件 | 349 / 296 个 \|peak\|=52c | 349 / 0 | **18 / 0** |
| 音素对齐（中位误差） | 未做 | 未做 | **142.3ms → 5.6ms** |
| 复检 inventory_coverage | fail | fail | **pass（0 失败）** |
| 复检动作未达成 | — | 10 处 | **0 处**（12 处 unknown） |
| must_differ 无法与浅对照区分 | 66 处 | 66 处 | **0 处** |
| 实图审覆盖 | 4/349 | 4/349 | **4/349**（p0:f0:v1 / p41:f0:v1 / p50:f0:v1 / p20:f0:v1） |
| 原生回读误差 | 0.49996c | 0.49999c | **0.49999c**（契约 <0.501c） |

---

## 四、复检契约状态（`render/execution-review/review.json`）

- `inventory_coverage`：**pass**，0 失败，349 单元 / 1110 区域 / 0 unknown 区域。
- `action_execution`：**347 pass / 12 unknown / 0 fail**。12 处 unknown 全部是判据窗口不足 3 个原生采样点（5ms 级的极短元音），属测不到，不是设计没做到。
- `musical_review`：**needs_review**（intent=unknown、discrimination=unknown）。0 处判负、0 处非区分；unknown 来自上面那 12 个极短元音。
- `local_visual_review`：**4/349**（本轮实际打开图并写下观察的只有 4 个单元，其余保持 pending，不冒充已审）。
- `choice_review`：`review_required`（还有 345 个单元没有实图审）。
- `listening`：**unknown**；`musical_quality`：**unverified**；`phonation`：**unvalidated**。
- `reference_sources`：pass（0 音频载荷、源文件与角色全部登记）。
- `technical_execution_complete` = false（因为 local_visual 未全覆盖 + 12 处 unknown）；`workflow_review_complete` = false（还需要人耳证据）。

---

## 五、边界与未解决（不掩饰）

1. **听感完全未验证**。本机没有可用的听觉评估工具，`listening=unknown`。数值一致 ≠ 好听，这是本报告最不能替代的一环。
2. **渲染比原唱轻 5.26dB**（逐音符 RMS 差中位；p10 −12.9dB / p90 +2.8dB）。这是合成声库自身的响度与原唱不同；混音已按原唱的人声/伴奏相对响度补偿（人声 +0.8dB、伴奏 −4dB，混音比例 −1.35dB vs 原唱 −1.31dB），所以「相对」关系对齐了，绝对电平仍比原唱低。若要绝对电平也一致，只能整体加增益或把 dyn 轨整体抬高（dyn 每单位约 0.083dB），那属于混音决定。
3. **渲染比原唱谐噪比高 0.94dB**（即略「实」一点）。`use_energy_embed=false` 的声库没有 ENE 轴；探针显示 brec 每单位只给 −0.018dB HNR 与 +6.1Hz 亮度，权限有限，BREC/VOIC 只能有限补偿。
4. **无 ENE/GENC**：B 站流程里「ENE 为主」的精调轴在本声库不存在，这是方法上的真实缺口。
5. **12 个极短元音判据测不到**（窗口 <16ms），记 unknown 而不是判负。
6. **实图审只做 4 个单元**（349 个里），图审覆盖仍是主要缺口。
7. **涟漪只有 18 个唱字**：源里绝大多数短字没有可测的周期成分，v3 不硬加；长字上的涟漪是真的被画出来了（见 p41 图）。
8. **和声未做**：源干声里没有可分离的和声轨。
9. **原唱 F0 仍有 2 处双检测器分歧空档**（共 2 个字），按线性滑音补齐，已在 `design/gap_log.json` 记录。

---

## 六、复现命令

```powershell
cd E:\project\agent2utau
$py = ".\.venv\Scripts\python.exe"
$R  = "runs/production/nianlun-from-scratch-v3-20261030"

& $py scratch/build_nianlun_v3_score.py     # 谱面：逐音符发声曲线 + 音素对齐 + 音节细分
& $py scratch/build_nianlun_v3_design.py    # 逐单元条件 + 源清单 + 复检库存
& $py scratch/build_nianlun_v3_plan.py      # 画线 plan + 意图简报冻结 + ledger
& $py scratch/compile_nianlun_v3.py         # compile-functions + 渲染
& $py scratch/mix_review_nianlun_v3.py      # 混音 + 切片 + 复检
& $py scratch/measure_nianlun_v3.py         # 渲染 vs 源的逐音符测量
& $py scratch/check_nianlun_v3_design.py    # 设计层形状自检
& $py scratch/diag_v3_pitd.py               # PITD 预算越界诊断
& $py scratch/probe_v3_params.py            # 参数剂量-响应探针
```

主要产物：

- 谱面 `design/score.ustx`（51 part / 650 note / 585 唱字 / 4 条逐音符曲线 / 音素 override）
- 编译 `compiled/project.ustx`（含逐栅格 PITD），`compiled/pitch.json`、`compiled/phones.json`
- 计划 `design/plan.json`（51 个设计 / 9188 节点 / 18 个涟漪组件）、`design/ledger.json`（349 条 forward 决策）
- 音频 `render/vocal_vocal.wav`、`render/nianlun_lingyuan_cover_mix_v3.wav`
- 复检 `render/execution-review/review.json` + `atlas/`（349 张逐元音局部图）
- 证据 `design/note_features.json`（逐音符源实测）、`design/align_log.json`、`design/split_log.json`、`design/gap_log.json`、`design/selfcheck.json`、`design/param_probe.json`、`render/measurements.json`、`render/mix_balance.json`
