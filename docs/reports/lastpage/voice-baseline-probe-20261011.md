# 最后一页：两完整乐句声线基底候选

2026-10-11。状态：one_voice_baseline_candidate_delivered_pending_listening。

最新原话“他这个基本都是实的，我们的基本都是虚的”绑定上一轮两份独立人声，计1条回复；范围为所交付两句，不改写全部318字标签，也不覆盖看283原局部偏实。白烁参考的已感知实感支持研究整体基底方向，但声线、曲线、音高阶段、时钟和执行方式多因素不同，尚未确认哪个因素造成差异。

本轮只一个自行选定候选：Normal75保持，将Classic25替换Bright25。未复制作者Bright40/Cute60或曲线节点。覆盖word270–284共15字、原生context28/29完整两句；自身音高、音素时钟、VOIC/TENC/BREC/SHFC及原生DYN不变。看283作为原正例保护观察点，其新声色是否保住实感待听；抱225完整C所在句原工程/预测/PCM精确保留。

## 执行与交付

原生A/B各两上下文导出/缓存技术执行单列；固定variance11/acoustic101下两上下文各A/A_repeat/B/B_repeat，共8套新波形。A预测/最终三通道/原波形精确重现，A/B重复精确；两阶段speaker精确，非speaker条件及人工增量精确，允许三个预测及其最终输入随speaker响应，特征裁剪0。音符/phones/pitch身份保持。

以32句原贡献和2句新B组装完整版本，正反组装精确；选择句贡献范围外PCM及抱C句PCM精确保持。44100Hz mono PCM24、固定声增益1.5，峰值0.677108，无归一化/压缩/BGM。逐字RMS响应仅代理，不能确认虚实改善。vocoder F0输入保持；本轮未重新测实际输出F0，Agent未听。

- [候选B两句](../../../runs/experiments/lastpage-voice-baseline-20261011/delivery/B_same_lyrics_vocal.wav)：原209.4–218.0秒，里约3.56秒、看约6.93秒。
- [自身原A两句](../../../runs/research/lastpage-li-kan-author-reference-20261011/delivery/agent_acceptedC_same_lyrics_vocal.wav)：原PCM精确截取。
- [白烁独立当前参考](../../../runs/research/lastpage-li-kan-author-reference-20261011/delivery/baishuo_current165c_reference_vocal.wav)：上轮用户评价“基本都是实的”；当前1.65c重渲染，非历史1.56作者录音。
- [完整B人声](../../../runs/experiments/lastpage-voice-baseline-20261011/delivery/lastpage_voice_baseline_B_vocal.wav)、[完整B工程](../../../runs/experiments/lastpage-voice-baseline-20261011/delivery/lastpage_voice_baseline_B.ustx)。完整B仅上述两句采用新基底，其余32句明确保持，不宣称全曲均已调整或接受。

反馈任务：两句是否更实且连贯；看是否退化；是否出现破音、咬字/响度等副作用。未报项unknown，不用数值响应代替改善。该候选待评且未采用；无自动候选搜索或加量。若获支持才记录明确整曲实施范围；阴性/副作用收口当前路线。表1追加版本绑定虚实例证，表2追加一项speaker因素开发对照及其预测/输出/反馈，通用规律0、measurement_validated仍false。

正式引用：PER:S1（支撑/实听感），PARAM:C20.01/05改变、C20.03保持；表2补充RESP:LASTPAGE-VOICE-BASELINE-01按B−A登记。8套波形只有2个独立完整上下文，重复不扩充独立条件数；上一轮“白烁实/自身虚”不是本次B候选反馈。准备阶段原cl01未显式存储，按声明默认0补入候选；首轮准备失败快照保留，原控制和单位不改。

协议/反馈/输入/重复检查在新run封存，原音频/歌曲/Skill与作者原件保持；单Agent、CI仅手动。[JSON](voice-baseline-probe-20261011.json)、[审计](voice-baseline-probe-20261011-audit.json)。
