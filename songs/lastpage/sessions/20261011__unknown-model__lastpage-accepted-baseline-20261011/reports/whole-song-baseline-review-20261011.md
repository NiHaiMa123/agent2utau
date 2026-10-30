# 《最后一页》整曲基线核查与交付

2026-10-11。状态：whole_song_baseline_audited_and_delivered_pending_listening。

已将已接受抱C整曲工作工程对应的34句封存波形组装为完整人声。没有新增控制、重新推理或改写旧歌曲/音频；新工程是工作基线的原字节副本。此版本用于整曲定位与后续纠错，不称作整曲改善或验收通过。

## 核查结果

- 318字、38歌词行、34原生上下文、412音符（332演唱阶段、80 AP/SP）逐项关联；歌词行与原生上下文分别登记。入口动作：{'short_direct': 118, 'bearing_then_push': 51, 'continuous_velocity': 163}；字腹动作：{'finite_return': 276, 'variable_periodic': 52}。动作分布仅是既有设计事实，不证明听感成功。
- 源观测GAME/双F0/歌词时钟字节绑定保持；word106“没”source unknown保持。38行歌词身份仍未经过人工逐行确认。历史验证报告的0.5c以内误差、完整时钟等只是旧技术结论，本轮不重新测F0或确认原曲事实。
- 完整工作工程SHA：`45d2b34e8086ad5f12f4c701d91672b3cc12eadffda2ab9d9e405dfb2fb71816`；发布v02 SHA：`a17d4bebdd3c5951f2b10138777a8fee8925ab5beb6bb70705342d1b6ba466af`。差异限定抱所在context22新增SHFC和声明范围从±12修正为±1200；原音符、时钟、其它曲线保留。旧果B未采用。
- 原34份函数计划是旧center_nodes/entries/finite/periodic/controls格式，不能直接冒充当前schema1编译输入。旧v02的phrase22预测/逐字状态不冒充接受C；本次复用的是C完整上下文。旧word89 DYN +3dB有限包络仍在，未新加响度补偿。
- 首轮检查将最初复制阶段登记误当最终v02绑定而停止；失败快照保留在rejected-preflight下。四份元数据（separation、fresh_center工程、函数计划、逐字决策）最终SHA与原复制SHA不同，已按当前完成清单精确绑定，原复制登记和源观测SHA不改写。
- 旧整曲v02能逐句精确重建float数组及PCM；新整曲181.8–187.2秒与原接受C局部PCM精确。context22贡献以外float/PCM精确保持。逐句raw×原生DYN精确、正反组装精确、PCM24量化及满幅检查通过。
- 新人声245.577143秒、44100Hz、mono PCM24、固定增益1.5；峰值0.661375612、满幅样本0。不研究BGM、不归一化、不压缩。33句沿用v02，1句沿用接受C；34句不是34次新实验。

## 保护范围与纠错入口

抱225保留C整句输入/预测/输出及原局部可用反馈，不能扩成全曲正常；果247原局部可用、124/214原偏实、112原问题/果SHFC否决、295未知和106源未知均保留。已停止的TENC/BREC/果SHFC加量不恢复。旧反馈来自各自旧版本，新整曲接受状态待评。

首轮整曲试听记录具体时间或字，以及字头/腹/尾、邻字/句内问题。先形成一个版本的修改目的、动作与保护范围，再编译及重建受影响完整下游；每轮同时记录未改善和副作用。若多控制同时变化按联合干预记录，不宣布唯一病因；最多两轮初始策略修订后收口当前设计，不自动追加候选。318字逐项有版本动作和待反馈槽，未报字不补“正常”。

表1保留描述候选与音频位置，表2保留版本/上下文/原输入、变化与反馈关系；本次只是34句复用交付记录，新人类反馈0、通用规律0、measurement_validated仍false。Agent未听。72条件/384波形旧成本草案仍暂不执行。

## 交付与绑定

- [完整接受C人声](../../../../../runs/production/lastpage-accepted-baseline-20261011/delivery/lastpage_accepted_C_baseline_vocal.wav)
- [完整工作工程副本](../../../../../runs/production/lastpage-accepted-baseline-20261011/delivery/lastpage_accepted_C_baseline.ustx)
- [318字账本](../../../reports/legacy/whole-song-baseline-review-20261011-words.csv)、[34句账本](whole-song-baseline-review-20261011-phrases.csv)、[JSON](whole-song-baseline-review-20261011.json)、[审计](whole-song-baseline-review-20261011-audit.json)。原试听收口报告与反馈不改写。
