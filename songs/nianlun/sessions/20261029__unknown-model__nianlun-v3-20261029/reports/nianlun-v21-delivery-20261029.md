# 年轮翻唱 最终交付（v21，2026-10-29）

对象：`runs/production/nianlun-v3-20261029`
素材：`E:\data\music\年轮 - 张碧晨.flac`（274.5s）
交付：`demo/nianlun_v3/nianlun_v21_mix.mp3`、`nianlun_v21_vocal.mp3`

---

## 一、技术验收

| 项目 | 要求 | 实测 | 结果 |
|---|---|---|---|
| **native 读回误差** | < 0.501c | **0.0000c**（38414 帧，0 帧超限） | **通过** |
| 编译 native_max_error | < 0.501c | 0.500000c | 通过 |
| 满幅样本（削波） | 0 | **0** | 通过 |
| 混音峰值 | < 1.0 | 0.9500 | 通过 |
| 动态 IQR | — | **10.2 dB**（原唱 8.7，v2 7.7） | 优于对照 |
| 碎字（<100ms） | — | **0**（v2 有 34 个） | 通过 |
| 歌词正确性 | — | **51/51 句** | 通过 |
| 逐元音覆盖 | 349/349 | **349/349**（30 页接触表全部打开 + 5 单元单独放大 + 349 条量化审计） | **通过** |
| 264 项测试 | 通过 | 通过 | 通过 |
| 听感 | 人耳 | **未验证** | 未完成 |

---

## 二、逐单元审计结果（349 条记录）

| 判定 | 数量 |
|---|---|
| keep | **342** |
| watch | 7 |
| unknown | 0 |

**判定依据（与图审同一套判据）**：
- \|body_dev\|（音符内部与自身音高的中位偏差）：中位 **8.0c**，p90 21c，**最大 41c，无一个 >60c**
- 字腹内部摆动：中位 **73c**，p90 126c，**最大 133c**
- 反向预兆（大跳前 ±120ms）：**1 个单元**（p2:f0:v6，已查明为旋律阶梯所致）

7 个 watch 全部是「大跳陡度」（500–711c / 40ms）。经归因确认：
**102 个大跳中，最终线与裸旋律的反向步进数完全相同（102 = 102）**——
即所有陡度和反向都来自**谱面音符本身**，PITD 层无法也不应改变。

---

## 三、本轮修掉的缺陷

| 版本 | 图审/审计发现 | 修正 |
|---|---|---|
| v20 | 大跳处有 9–13 次反向步进 | 边界单调化 |
| **v21** | 量化确认：反向来自 before_pitd（音符阶梯），非 PITD | 记录为谱面固有形态，不再强行消除 |

同时修正了两处**测量口径错误**（这两处错误会让人误判为严重缺陷）：
1. body dev 最初用「整个单元支撑」的中位数比较起始音符 → 得到 -685c 的假缺陷
   （单元支撑可能横跨多个音符）。改为**只在该单元归属的音符内**测量 → 中位 8c、最大 41c。
2. 字腹 swing 曾报告 546c，实际是读到了旧的 `pitch_final.json` 缓存；
   重新导出后实测**最大 133c**。

---

## 四、与白烁的对比（学画法，不复制数值）

| 指标 | 白烁 雨爱 | 本版 年轮 |
|---|---|---|
| 载体 | note.pitch 直线 + 细节全在 PITD | 同 |
| PITD 网格 | 15.6ms | 5 tick（约 5ms） |
| p50 | -5c | +0c |
| p99 | +410c | +59c |
| 逐点 \|dy\| 中位 | 11c | 1c |
| 逐点 \|dy\| 最大 | 1346c | **58c** |
| 大跳 10–90% 时间 | 中位 53ms | 约 90ms |

**本版比白烁更平滑、更保守**。代价是极端表情（±300c 手调）明显少于白烁。

---

## 五、工程配置

- 349 字 / 51 句 / 58 原生短语 / 387 音符
- 最短字 0.20s，**0 个 <100ms**
- 歌词修正 ASR 9 处错字
- 音色：`cl01=50 (Bright) + cl05=50 (Classic)`（5 候选谱形距离实测选出，4.69dB）
- 发声层：dyn/voic/brec 各 51、tenc 42
- 曲线：pitd 51 / cl01 51 / cl05 51 / dyn 51 / voic 51 / brec 51 / tenc 42

---

## 六、诚实的边界

1. **听感完全未验证**。`musical_quality = unverified`，我没有音频感知工具。
2. **覆盖口径**：349 个单元全部出现在已打开的 30 页接触表（每页 12 个），
   并各有 1 条量化审计记录；5 个单元另行放大。接触表单格尺寸较小，
   逐周期形态类细部仍需进一步放大。
3. **本版明显比白烁保守**（p99 +59 vs +410，最大 \|dy\| 58 vs 1346）。
   听感可能"起伏不够"。
4. **102 个大跳仍有反向步进**，但已证明与裸旋律完全一致（102=102），
   属谱面固有形态；若要改变需修改音符切分，不在 PITD 层。
5. **音色按谱形距离选**，不等于听觉最优。
6. 复用了用户授权的观测（分离/GAME/双F0/ASR）。

---

## 七、复现

```
songs/nianlun/sessions/20261029__unknown-model__nianlun-v3-20261029/scripts/v16_contact_sheets.py     30 页接触表（349 单元）
songs/nianlun/sessions/20261029__unknown-model__nianlun-v3-20261029/scripts/v21_per_unit_audit.py     349 条逐单元量化审计
songs/nianlun/sessions/20261029__unknown-model__nianlun-v3-20261029/scripts/v20_pitd.py               曲线生成 + 边界单调化
songs/nianlun/sessions/20261029__unknown-model__nianlun-v3-20261029/scripts/v21_compile_plan.py       编译计划
  agent2utau compile-functions    -> native_max_error 0.5c
songs/nianlun/sessions/20261029__unknown-model__nianlun-v3-20261029/scripts/v21_assemble.py           音色层 + 发声层
songs/nianlun/sessions/20261029__unknown-model__nianlun-v3-20261029/scripts/finalize.py               连续 PITD 写回 + 全域扩展 + 相位对齐
songs/nianlun/sessions/20261029__unknown-model__nianlun-v3-20261029/scripts/v21_fix_leaps.py          大跳窗口单调化
songs/nianlun/sessions/20261029__unknown-model__nianlun-v3-20261029/scripts/v15_authoritative.py      权威读回验证 -> 0.0000c
songs/nianlun/sessions/20261029__unknown-model__nianlun-v3-20261029/scripts/v21_body_swing.py         字腹摆动复核
songs/nianlun/sessions/20261029__unknown-model__nianlun-v3-20261029/scripts/v21_check_global.py       大跳反向归因
  agent2utau render-project
```
