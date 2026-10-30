# 最后一页：自己的条件下反向声线E

2026-10-12。状态own_bright_cute_delivered_pending_listening。用户“下一步”授权执行冻结单候选，自己两完整句“想把你抱进身体里面／不敢让你看见”15字270–284、context28/29，Normal75/Classic25改为Bright40/Cute60恒定UI配比。其它音符tone/tuning/PITD/note.pitch/vibrato、歌词/音素/CLR完整时钟、VOIC/TENC/BREC/SHFC与DYN保持。E是参考里/看焦点证据后选择的命名声线候选，作者整句配比有时变，**不声称精确复制作者整句声线**；没有搬运作者音高/时钟/控制节点或数组。旧Normal75/Bright25阴性保持。

## 原生和重新预测

当前YousaV1.65c acoustic与variance配置均核对Bright/Cute/Normal/Whisper/Classic顺序，不能从工程通用cl01标签猜名称。完整34part副本只替换28/29的五色曲线，32其它part及已有抱C结构保持；原生roundtrip、phone/音高导出、两阶段speaker实际tensor精确重建。

最初独立预检以数学实数0.4/0.6重建时被严格等式拒绝，失败检查器和日志保留，尚未启动fresh模型。离线PE读取已绑定本机Core的PhraseSpeakerEmbedByFrame及采样lambda：先double采样乘promoted0.01f再cast float32，Sum后不足1补该帧默认speaker，再dot。UI40/60采样得0.3999999761581421/0.5999999642372131，和0.9999999403953552，余量5.960464477539063e−08加至本段phone默认Bright，最终权重0.40000003576278687/0.5999999642372131。独立421/305帧、两阶段embedding逐元素精确通过；未改UI/剂量/工程/预算或放宽容差。metadata reader在本批ignored run编译，未加载或修改安装程序集。

两句各A/A_repeat/E/E_repeat共8次新variance、8套acoustic/vocoder，固定variance11/acoustic101。原A的三预测/三最终通道/raw PCM与历史28/29精确，所有重复输入/预测/mel/raw精确；E仅speaker及其三预测后最终发声特征响应变化，人工增量保持并重算合法clip，裁剪0。vocoder F0输入保持不证明实际F0完全固定。原生缓存4套技术上下文另列，不计作fresh样本；2条件、同输入重复不增加独立样本量，非留出。

## 有限观测与组装

77窗口包括15字元音/15–85%主体/首尾60ms、可定位辅音和两完整上下文，8次新FCPE/RMVPE检测，没有跨无声插值；共同有声配对不足3帧保留unknown。完整独立句波形RMS差：context28 +1.206dB；context29 +1.024dB。下表是代理，RMS不等于感知响度、实感或生理参数；F0检测尚未本任务真值校准，不能因电平提高宣布改善。

|字/ID|元音RMS差dB|FCPE差p50/max(c)|RMVPE差p50/max(c)|
|---|---:|---:|---:|
|想/270|+0.924|1.868/20.925|1.081/17.312|
|把/271|+1.221|0.492/6.941|0.438/11.499|
|你/272|+5.460|1.742/22.800|2.792/40.831|
|抱/273|+1.622|0.523/10.732|0.436/7.695|
|进/274|+2.125|1.981/9.507|0.609/8.193|
|身/275|+0.919|1.092/7.186|0.751/9.674|
|体/276|+0.886|0.436/5.034|0.253/2.469|
|里/277|+0.744|0.637/2.973|0.598/4.143|
|面/278|+1.584|1.754/54.214|1.138/19.754|
|不/279|+0.930|0.614/2.110|0.366/2.032|
|敢/280|+0.903|0.627/3.391|0.740/3.178|
|让/281|+1.390|0.359/2.222|0.338/2.338|
|你/282|+2.640|0.744/3.571|0.565/4.435|
|看/283|+0.887|0.506/19.195|0.231/23.080|
|见/284|+0.336|0.386/8.759|0.307/9.447|


完整245.577秒研究人声由32旧贡献及2新E贡献按原时钟组装，原DYN0dB曲线与gain1逐项核对，固定1.5、44100Hz mono PCM24，峰值0.680658，无归一化/压缩/BGM。独立重建34贡献、原A全PCM、量化误差、两预览与抱C通过；28/29贡献支撑并集外PCM精确保持。两句89ms自然重叠保留，本轮两句均改变，隔离句观测与整曲混合预览范围明确，没有交叉淡化或重定时。原“看”局部偏实反馈保持，但E中看的新听感及副作用待评。

冻结旧协议baseline_preview字段实际上指整曲carrier；新交付显式裁209.4–218.0秒8.6秒，两端原PCM截取精确，未重写旧协议。单独作者参考沿用已有fresh作者A、当前1.65c、固定11/101、212–220.5秒8.5秒；与自己的音乐/时钟有差异，只作描述对照，E−自己的A才是声线干预对照，历史1.56不可用。

- [E两句](../../../../../runs/experiments/lastpage-own-bright-cute-20261012/delivery/E_two_phrases.wav)、[自己的原A](../../../../../runs/experiments/lastpage-own-bright-cute-20261012/delivery/A_two_phrases.wav)。
- [白烁单独参考A](../../../../../runs/experiments/lastpage-author-interaction-20261012/delivery/A_two_phrases.wav)。
- [完整研究E工程](../../../../../runs/experiments/lastpage-own-bright-cute-20261012/delivery/lastpage_own_bright_cute_E.ustx)、[完整研究E人声](../../../../../runs/experiments/lastpage-own-bright-cute-20261012/delivery/lastpage_own_bright_cute_E_vocal.wav)，未采用为原歌曲。

新反馈0，Agent未听，全部measurement_validated=false、通用规律0。表1PER:S1与PARAM:C20.01–05引用、表2RESP:LASTPAGE-OWN-BRIGHT-CUTE-01及15字响应CSV追加本例，没有新增逐字听觉标签。下一步只接E相对自己A是否更实/连贯、看是否受影响及破音/咬字/响度反馈，不自动扫配比/加量/采用。原歌曲/音频/Skill/作者原件、unknown106、旧阴性及接受抱C保持，单Agent，CI仅手动。

[15字CSV](../../../reports/legacy/own-bright-cute-probe-20261012-words.csv)、[JSON](../../../../../docs/reports/lastpage/own-bright-cute-probe-20261012.json)、[审计](own-bright-cute-probe-20261012-audit.json)。
