# 最后一页：里字DYN强弱包络H

2026-10-12，状态H_DYN_delivered_pending_listening。用户“下一步”执行冻结单个H；G“不行”保留并在7ID知识receipt明确拒绝，不采用G、不增大VOIC。F仅为已获聚合改善的工作比较基底，不冒称发布歌或整曲验收。

## 本次改变与实际原生执行

自己的里277：最后40ms l准备、i入口DYN−4dB，自己主体锚点+1.5dB后回收，再下降阶段−1.5dB并恢复0；UI0/−40/−40/+15/0/−15/0，原整数5tick网格/逐段smoothstep及整数UI编译。声线Bright40/Cute60、全部音高/音乐阶段、歌词/音素/CLR完整时钟、TENC/BREC/VOIC/SHFC精确F。DYN只变输出增益，没有改变声库发声特征，也没有搬运作者曲线/能量数据。

全34part副本只改context28 dyn值、节点xs保持；原生roundtrip声明/曲线精确，phone/完整pitch/两阶段speaker/全部variance和acoustic输入、原生预测与F精确。现有levelprobe-v15程序集与原构建DLL字节相同并绑定源码，调用当前Core真实ExportDynamics/ApplyDynamics；安装/旧build不改、未部署新桥。47原资源SHA保持，4现有DYN工具文件单列绑定。

**新的固定种子variance/acoustic/vocoder合成0**：F原11/101 raw/预测/输入明确封存复用，Core实际处理H/H_repeat两份贡献精确；另ones得到逐样本gain。处理重复不是2个独立合成或条件。2句native缓存技术导出另列，未对native内部神经推理计数作未核实的0声明。独立由实际原生曲线重建振幅/5tick终点/逐样本插值，gain及raw*gain float32逐元素精确，不以Python另一条包络代替工程。增益最小0.630957365、最大1.188502192，不触发特殊最小静音。

实际gain≠1共28020样本，支撑212.915626412–213.582270403s；原生插值比计划准备早约1.665ms、比元音末尾早约3.146ms，另一个独立PCM门禁限制在一5tick加一样本边界内。l最后约41.665ms受影响，咬字需试听；没有裁切回设计边界伪造精准支撑。其它14元音/面及第二句完整PCM保持，原音符/音素/模型条件不变。

## 阶段响应与试听边界

|阶段|F RMS dBFS|H RMS dBFS|H−F dB|
|---|---:|---:|---:|
|li_preparation|-24.046|-26.403|-2.357|
|li_entry|-16.222|-20.222|-4.000|
|li_build|-18.713|-20.025|-1.312|
|li_recover|-20.277|-19.479|+0.798|
|li_release|-20.425|-21.149|-0.724|
|li_descending|-22.866|-23.703|-0.837|


入口约−20.222、展开−20.025、主体−19.479，再回收−21.149/−23.703dBFS，五阶段均值呈先增加后降低；这是这次有限包络的数字电平响应，不证明每个瞬时短窗严格单调，也不证明发力/自然度或更像作者。全里RMS相对F约−1.230dB，因为入口减轻；不是整字归一化或音量补偿策略。

83窗包含原15字/辅音/两整句77窗口加里5阶段及l准备1窗。2次新H FCPE/RMVPE，6旧F数组绑定复用；共同有效帧不足3则unknown、不跨无声插值，原raw/mel/发声特征精确F。未改PCM元音仍有检测器约百分之几音分的上下文响应，不能当音高改变；检测器未校准真实发力或F0真值。原生数据/数学通过与听觉效果分开。

## 同增益PCM交付

完整245.577秒研究H由34贡献重建，只有context28有限gain-mask内样本改变；context29独立贡献和完整混合窗口/看、抱C及其它32贡献精确F，原89ms重叠保留且共享padding改变0。F整曲PCM重建/正反组装/H量化、掩码外样本与预览通过，44100Hz mono PCM24、固定1.5，峰值0.680706，无文件削波、归一化、压缩或BGM。

- [H新版两句](../../../../../runs/experiments/lastpage-own-li-dyn-20261012/delivery/H_two_phrases.wav)、[F基线](../../../../../runs/experiments/lastpage-own-control-neutral-20261012/delivery/F_two_phrases.wav)：209.4–218.0秒8.6秒，里约3.56–4.19秒，l准备约3.52秒。
- [白烁单独参考](../../../../../runs/experiments/lastpage-author-interaction-20261012/delivery/A_two_phrases.wav)：沿用当前1.65c已有fresh作者A，212–220.5秒8.5秒，音乐/时钟不同，只作描述参考，H−F才是DYN对照。
- [完整研究H工程](../../../../../runs/experiments/lastpage-own-li-dyn-20261012/delivery/lastpage_own_li_dyn_H.ustx)、[完整研究H人声](../../../../../runs/experiments/lastpage-own-li-dyn-20261012/delivery/lastpage_own_li_dyn_H_vocal.wav)：未采用为原歌。

本批11项相关PCM契约与独立native/处理/83窗PCM门禁通过，知识receipt/sourceSHA明确消费G否定；新增H加入当前表2索引近10系列及表1PER:S1/EVT:L2/ACO:L1/PARAM:C10.01。下步只接H相对F是否有所需强弱/发力层次，及实感/挤尖/l咬字副作用；新反馈0、Agent未听、全部measurement_validated=false、通用规律0。不自动扫剂量/改音高/加发声通道，原歌曲/音频/Skill/作者原件/旧阴性/抱C/source_unknown106保持，单Agent、CI仅手动。

[15字CSV](../../../reports/legacy/own-li-DYN-probe-20261012-words.csv)、[阶段CSV](../../../reports/legacy/own-li-DYN-probe-20261012-stages.csv)、[JSON](../../../../../docs/reports/lastpage/own-li-DYN-probe-20261012.json)、[审计](own-li-DYN-probe-20261012-audit.json)。
