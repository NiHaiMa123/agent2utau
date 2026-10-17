# 最后一页：里TENC建立与回收I

2026-10-12。用户“下一步”授权执行已冻结I。此前H“里字不够实，强度也不够大”与G“不行”保留并实际进入11ID知识决策；F仍为工作比较基底，非整曲验收。沿用singing-expression-editor方法，Skill与旧原歌/音频/作者原件/封存实验均不改。

## 单因素执行

F的Bright40/Cute60、全部音高/音符/音素时钟/CLR、BREC0/VOIC100/SHFC0/DYN0保持，仅里元音212.9572917–213.5854167s按自己的音乐节点建立TENC0→+10→+4→0；入口与主音到达前保持，主体锚点展开，自己的回收/降音阶段承接，再在元音结束恢复。smoothstep零切线、原5tick整数采样，非作者节点或曲线复制。

原生独立重建确认42帧张力增量，最大0.500000000模型单位；本机Core IL为sampledUI/20f，独立声线两阶段、完整pitch/phones/variance输入与三预测均精确F，只有最终张力输入改变，BREC/VOIC与vocoder F0保持。实际非零采样仅里元音，声母/邻字人工输入未增加；声学模型上下文仍可能影响邻字波形，不能将输入支撑当PCM支撑。

context28 I/I_repeat两套新的variance/acoustic/vocoder波形，固定11/101，重复全部输入/预测/mel/raw精确，特征裁剪0。context29 fresh贡献复用F，2句原生缓存技术渲染另列，原生内部神经推理次数未计数。2次新双F0检测与6个旧F数组绑定复用，不等于新增独立条件。82窗覆盖15字/辅音/两句及里5音乐阶段。

|阶段|F RMS dBFS|I RMS dBFS|I−F dB|
|---|---:|---:|---:|
|li_entry|-16.222|-16.235|-0.014|
|li_build|-18.713|-18.839|-0.126|
|li_recover|-20.277|-20.474|-0.197|
|li_release|-20.425|-20.470|-0.045|
|li_descending|-22.866|-22.962|-0.097|


整里RMS I−F为-0.093642dB；表中变化是数字能量与模型条件响应，不是听觉力量或实感改善。TENC正增量也不能证明生理发力更强。此前E前顶/挤细/尖、F及作者C组合中和改善的反例保留，本批专门试听这些副作用，不自动加剂量、叠加DYN或采用。

## 交付和验收边界

研究全曲245.577秒按34贡献重建、context28替换；原F全PCM重建、逆序拼接与量化/预览通过，固定1.5、44100Hz mono PCM24，峰值0.680706，无文件满幅削波/归一化/压缩/BGM。context29独立贡献及真实音素/看PCM精确，原89ms共享padding有2031样本变化，具体范围[214.2206575963719, 214.30802721088435]，未越真实音素边界；其它32贡献/抱C及context28贡献外PCM保持。

- [I新版两句](../../../runs/experiments/lastpage-own-li-tenc-stages-20261012/delivery/I_two_phrases.wav)、[F工作基底](../../../runs/experiments/lastpage-own-control-neutral-20261012/delivery/F_two_phrases.wav)：8.6秒，里约3.56–4.19秒。
- [白烁单独参考](../../../runs/experiments/lastpage-author-interaction-20261012/delivery/A_two_phrases.wav)：既有当前1.65c fresh A，音乐/时钟不同，仅描述比较。
- [完整研究I工程](../../../runs/experiments/lastpage-own-li-tenc-stages-20261012/delivery/lastpage_own_li_tenc_I.ustx)、[完整研究I人声](../../../runs/experiments/lastpage-own-li-tenc-stages-20261012/delivery/lastpage_own_li_tenc_I_vocal.wav)：研究副本，未采用为发布歌。

20项本机相关契约与原生/重复/82窗/PCM独立检查通过，保护输入及47资源SHA保持。首次原生probe在ONNX声码器初始化发生0xC0000005，同工程/同输入重试通过，原失败日志与重试另列保存，未换种子/参数/预算。表2新I技术记录与当前索引追加，旧H/G否定仍可检索，旧知识receipt保留当时目录快照。下步只接本批里实感、力量展开/回收及前顶挤细尖、破音/咬字反馈，不自动扫剂量或扩大通道。Agent未听，新反馈0、measurement_validated=false、通用规律0，单Agent、CI仅手动。

[15字CSV](own-li-TENC-stages-probe-20261012-words.csv)、[阶段CSV](own-li-TENC-stages-probe-20261012-stages.csv)、[JSON](own-li-TENC-stages-probe-20261012.json)、[审计](own-li-TENC-stages-probe-20261012-audit.json)。
