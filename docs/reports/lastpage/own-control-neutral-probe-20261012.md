# 最后一页：E声线下自己的三人工控制组中和F

2026-10-12，状态own_control_neutral_delivered_pending_listening。用户“下一步”授权执行冻结F，前序E反馈“比白烁的更实，但是就有那种前顶的感觉，声音挤得很细很尖”保持原词，不采用E。此次只检查自身人工控制组在E声线下的贡献，没有预先判定TENC/VOIC/BREC单通道病因。

## 固定干预与实际执行

自己的context28/29两完整句“想把你抱进身体里面／不敢让你看见”15字270–284，E完整34part副本只中和两part的TENC0、BREC0、VOIC100，各自原整数5tick曲线xs保持，原正/负人工增量一起取消；三预测基底仍保留，不是三最终模型特征归零。SHFC焦点原0精确保留，没有实际干预。Bright40/Cute60声线及本机percent/default余量、自己notes.tone/tuning/PITD/note.pitch/vibrato、歌词/CLR/音素完整时钟与DYN保持，32其它part及旧接受抱C精确保留。

原生roundtrip读回曲线、phone/完整音高、两阶段speaker embedding、variance全部输入/原生预测逐元素精确E，三人工delta0。两句F/F_repeat共4次新variance及4套新acoustic/vocoder波形，固定variance11/acoustic101，fresh variance输入/三预测逐元素精确E，只有三最终发声输入改变；所有重复输入/预测/mel/raw PCM精确，特征裁剪0。2句原生缓存技术结果另列，E raw/input/波形封存显式复用，未新执行E或作者。两个独立上下文，不将重复或15字窗口当新增独立样本/留出。

## 观测与交付边界

77窗口覆盖两整句、15元音全段/15–85%主体/首尾60ms与可定位辅音，F新FCPE/RMVPE4次，E已有4数组按输入PCM SHA精确复用。无跨无声插值，少于3共同有效帧unknown；原vocoder F0输入精确不保证实际F0完全一致，双检测尚未任务真值校准。独立整句RMS差：context28 -0.218dB；context29 -0.122dB。

|字/ID|F−E元音RMS差dB|FCPE差p50/max(c)|RMVPE差p50/max(c)|
|---|---:|---:|---:|
|想/270|-0.000|0.009/0.035|0.010/0.126|
|把/271|-0.006|0.027/0.585|0.030/0.298|
|你/272|-4.585|0.836/24.060|1.008/34.322|
|抱/273|+0.216|0.266/0.812|0.144/1.551|
|进/274|-1.642|1.308/8.588|1.314/7.389|
|身/275|+0.003|0.021/0.132|0.030/0.310|
|体/276|+0.086|0.366/1.282|0.382/2.459|
|里/277|-0.836|0.262/2.468|0.120/0.534|
|面/278|+0.013|0.129/0.638|0.105/1.037|
|不/279|-0.000|0.011/0.051|0.008/0.041|
|敢/280|-0.701|0.284/0.941|0.122/0.762|
|让/281|+0.014|0.068/0.456|0.036/0.366|
|你/282|-0.872|0.408/1.496|0.357/1.309|
|看/283|-0.002|0.005/0.049|0.006/0.192|
|见/284|+0.037|0.118/1.695|0.079/1.128|


第一句你272下降约4.585dB、进274约1.642dB、里277约0.836dB；这些是有限电平响应，不代表用户感知响度/虚实或前顶改善。输入归零不保证其它字波形不响应，声母/邻域和副作用仍须试听。没有补偿增益、归一化、压缩或BGM；固定呈现1.5，不能把听感差自动归于响度或某一通道。

完整245.577秒研究F人声由32旧贡献与2新F贡献按原时钟组装，44100Hz mono PCM24、原生DYN0dB/gain1，峰值0.680706。独立重建34贡献、封存E全PCM、F量化与209.4–218.0秒8.6秒预览通过；28/29支撑并集外和抱C PCM精确保持。两句原89ms重叠保持，没有波形重定时/交叉淡化；隔离上下文指标与整曲混合预览分开。F研究工程未采用为原歌曲，原“看”偏实标签保留但F的新标签unknown。

- [F新版两句](../../../runs/experiments/lastpage-own-control-neutral-20261012/delivery/F_two_phrases.wav)。
- [E原对照](../../../runs/experiments/lastpage-own-bright-cute-20261012/delivery/E_two_phrases.wav)：上轮有前顶/挤细尖，原字节保持。
- [作者单独参考](../../../runs/experiments/lastpage-author-interaction-20261012/delivery/A_two_phrases.wav)：沿用当前1.65c固定11/101作者A，212–220.5秒8.5秒；音乐/时钟不同，只作描述对照，F−E才是人工控制组干预对照。
- [自己的原A](../../../runs/experiments/lastpage-own-bright-cute-20261012/delivery/A_two_phrases.wav)、[完整研究F工程](../../../runs/experiments/lastpage-own-control-neutral-20261012/delivery/lastpage_own_control_neutral_F.ustx)、[完整研究F人声](../../../runs/experiments/lastpage-own-control-neutral-20261012/delivery/lastpage_own_control_neutral_F_vocal.wav)。

下一步只接F相对E前顶/挤细尖是否减轻、实感是否保留，以及看/破音/咬字/响度反馈。新反馈0、未报维度unknown，Agent未听、未采用，measurement_validated=false、通用规律0，不自动扫配比/加量/扩展新因素。表1PER:S1与PARAM:C11.01/C12.01/C13.01及表2RESP:LASTPAGE-OWN-CONTROL-NEUTRAL-01追加，四原词保持尚未严格映射的听觉描述。原歌曲/音频/Skill/作者原件、旧阴性、接受抱C及source_unknown106保持，单Agent、CI仅手动。

[15字CSV](own-control-neutral-probe-20261012-words.csv)、[JSON](own-control-neutral-probe-20261012.json)、[审计](own-control-neutral-probe-20261012-audit.json)。
