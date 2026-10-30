# 最后一页：声线与人工控制的第四角D

2026-10-12。状态：author_interaction_delivered_pending_listening。用户“下一步”授权执行已冻结LASTPAGE-AUTHOR-SPEAKER-CONTROL-INTERACTION-01，原冻结文件原字节保持；不自动进入音符/时长变更。

|版|声线|人工控制|
|---|---|---|
|A|作者原mix，含时变/CLR余量|作者原TENC/BREC/VOIC|
|B|明确Normal75/Classic25|作者原TENC/BREC/VOIC|
|C|作者原mix|三人工增量0|
|D（本轮新）|明确Normal75/Classic25|三人工增量0|

所有角都保留相同作者42音符主轨part、notes tone/tuning、完整PITD/note.pitch、歌词、时长、音素/CLR和DYN，焦点两句SHFC原0。D仅以C副本换cl01..cl05为0/0/75/0/25，总量100；完整3句原生缓存技术单列，独立研究仅前两句。D−C检验零人工控制条件下的声线；D−B检验自己的声线条件下取消控制组。三个控制仍是一个组，不能归到单通道。

## 实际执行及独立门禁

当前47安装绑定与旧源输入、模型适配器及歌曲/Skill/作者保护SHA核对；独立原生读回确认完整pitch/phone时钟与A/B/C相同。D两阶段speaker精确Normal75/Classic25，与B一致；D variance完整输入和native预测精确B，人工增量为0精确C。新variance11/acoustic101/vocoder仅两句D/D_repeat，共4套新波形，重复在输入/预测/mel/vocoder F0/PCM精确；fresh预测精确旧B，最终三个通道由该预测零增量/合法裁剪重建。D−B只改三个最终声学通道，D−C只允许speaker及三个预测/最终输入响应。

A/B/C原波形、PCM、F0来源明确封存复用，没有新推理/新反馈，不冒称新A重测；本轮独立条件仍2个，技术重复不增加样本量。D按原生前导时钟在44100网格拼接、保留完整第二句尾部，mono PCM24、固定声增益1.5、无DYN曲线/默认0dB unity，无归一化/压缩/增益补偿/BGM。A/B/C整段和上下文PCM原文件字节复制精确。

D新4次FCPE/RMVPE；A/B/C因PCM与当前检测器模型SHA一致，显式复用12份旧数组。32整句/15字末音素与主体窗口、4组标量比较共128行，登记电平/F0/最终特征及差分之差(D−C)−(B−A)。差分之差是四角有限数值响应，不是已确认的听觉交互、生理机制或通用规律；检测器未经本批真值校准。模型特征裁剪按D逐句列明，旧A/B/C裁剪在各原报告保留，不修改原状态。

## 试听任务及范围

分开听D、C、B：D与C相比是否更虚；D与B相比是否更接近作者，或更接近自己的原版；未报破音/咬字/响度等unknown。此前A>B>自己的按语境偏好、C“很接近A”、A/P/N/PN均比自己的实分别保留，不预先给D排序或扩成逐字标签。若D仍有相对自己的优势，剩余音符主音/音乐阶段/时钟只能作为下一项有限候选；若组合作用明显，再冻结有依据的单通道或条件拆分，不自动修自己的全曲、扫比例/剂量或移植作者制作路线。

本轮仅新增一个研究D，未采用、新反馈0、Agent未听、measurement_validated=false、通用规律0。表1PER:S1、C20声线与C11–13控制、表2RESP:LASTPAGE-AUTHOR-INTERACTION-01追加。源unknown、原歌曲/音频/作者原件/Skill、旧阴性及旧抱C保持；单Agent，CI仅workflow_dispatch。

|句|D的BREC裁剪帧|VOIC裁剪帧|TENC裁剪帧|
|---|---:|---:|---:|
|0|0|0|0|
|1|0|0|0|

- [D独立人声](../../../../../runs/experiments/lastpage-author-interaction-20261012/delivery/D_two_phrases.wav)
- [A独立人声](../../../../../runs/experiments/lastpage-author-interaction-20261012/delivery/A_two_phrases.wav)
- [B独立人声](../../../../../runs/experiments/lastpage-author-interaction-20261012/delivery/B_two_phrases.wav)
- [C独立人声](../../../../../runs/experiments/lastpage-author-interaction-20261012/delivery/C_two_phrases.wav)

[JSON](../../../../../docs/reports/lastpage/author-interaction-20261012.json)、[128窗口比較行](../../../reports/legacy/author-interaction-20261012-windows.csv)、[审计](author-interaction-20261012-audit.json)。
