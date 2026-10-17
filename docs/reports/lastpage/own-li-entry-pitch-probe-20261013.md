# 最后一页：里低位进入音高J

2026-10-13。用户“继续”执行冻结J，基于既有原曲GAME/双F0候选及11系列/15字条件复核，实际消费19ID知识。G/H/I阴性、E挤细尖、F聚合改善/工作基底边界保持。此为自己的有限音高路径试验，不搬作者曲线、不加发声剂量，Skill/原歌/音频/作者原件不改。

## 唯一写入因素与完整依赖

保持notes.tone/tuning/positions/durations/note.pitch/vibrato、所有phone符号/时钟/CLR、Bright40/Cute60以及TENC0/BREC0/VOIC100/SHFC0/DYN0。仅context28里/l准备PITD原5tick grid的ys改变，按独立Hermite目标-minus-before-PITD整数编码。212.877291667s以自己F边界值和切线接入，212.957291667s到66、维持90ms，213.140s到68，213.200s接回F自身主体；后68→66与下字保持原目标。notes.tone未修改，因此不声称隔离phone选择用tone或谱面音符已修正；实际最后80ms l也改变pitch，咬字/体到里衔接是试听检查项。

独立多项式、完整谱面恢复等式和native读回通过：60个5tick点改变，最大相对F 310.000000c，目标点最大误差0.493821577c。实际写点与帧支撑/相邻插值段在native检查JSON列明，不以请求窗口掩盖采样边缘。模型pitch有27帧改变；Core SampleCurve实际float32差分→double插值→double0.01缩放再float32、频率换算独立精确重建F/J两条输入路径。

variance输入只pitch改变，两阶段speaker/音素/其它固定输入精确F；三新预测完整重算，再用零人工增量生成新最终输入，acoustic F0/vocoder F0都来自新音高，不是保留旧预测或vocoder F0的SHFC反事实。context28 J/J_repeat两套新variance/acoustic/vocoder，固定11/101，输入/预测/mel/raw全部重复精确，feature clipping0。context29封存F贡献复用，2原生缓存技术上下文另列；原生内部神经执行次数未计数。本轮原生执行未需重试。

初始检查器误将写入前的note.pitch高精度值与原生读回舍入值直接比较，失败源码/说明保留；纠正为写入F/J恢复等式及加载F/J完整notes逐项精确检查。未更改谱面/模型输入或放宽容差，before-PITD亦精确F。

## 有限观测与交付

|阶段|F RMS dBFS|J RMS dBFS|J−F dB|
|---|---:|---:|---:|
|li_preparation|-23.685|-36.041|-12.355|
|li_low_entry|-16.182|-18.013|-1.831|
|li_rise|-17.546|-18.349|-0.803|
|li_rejoin|-19.670|-18.664|+1.006|
|li_retained_body|-20.255|-18.983|+1.272|
|li_retained_release|-20.425|-19.126|+1.299|
|li_descending|-22.866|-22.237|+0.629|


整里J−F RMS为+0.134614dB，音高/预测/谱与电平响应均是有限代理，不证明更实、更强或自然度通过。84窗覆盖两句15字/辅音及7个里/l阶段，2新双F0检测与6旧F绑定明确复用。源F0候选不是实测目标真值，新输出F0也不因输入精确而自动固定或接受。

完整研究人声245.577秒按34贡献组装，仅替换context28贡献，DYN0/gain1、固定1.5、44100Hz mono PCM24，峰值0.680706，无归一化/压缩/BGM/文件满幅削波。F原全PCM重建、逆序拼接、量化和预览通过；context29独立贡献/真实音素/看及抱C/贡献外PCM精确。原89ms共享padding有3911样本变化，范围[214.2206575963719, 214.30947845804988]，未越真实音素边界；模型上下文也可影响context28邻字，不把人工输入支撑等同波形支撑。

- [J新版两句](../../../runs/experiments/lastpage-own-li-entry-pitch-20261013/delivery/J_two_phrases.wav)、[F工作基底](../../../runs/experiments/lastpage-own-control-neutral-20261012/delivery/F_two_phrases.wav)：8.6秒，里3.56–4.19秒，l准备约3.48秒开始。
- [白烁单独参考](../../../runs/experiments/lastpage-author-interaction-20261012/delivery/A_two_phrases.wav)：既有当前1.65c fresh A，只作描述比较，音乐/时钟不同。
- [完整研究J工程](../../../runs/experiments/lastpage-own-li-entry-pitch-20261013/delivery/lastpage_own_li_entry_pitch_J.ustx)、[完整研究J人声](../../../runs/experiments/lastpage-own-li-entry-pitch-20261013/delivery/lastpage_own_li_entry_pitch_J_vocal.wav)：未采用为原发布歌。

20项相关本机契约及native/fresh/84窗/PCM门禁通过，47资源/保护SHA保持。新J响应追加表2当前索引，OBS条件复核保留、近12系列/37行，旧G/H/I否定及当时receipt不改。下步只接J相对F的里实感、发力发展、新低入口音乐是否合适及咬字/挤尖/破音副作用，不自动改音符tone/加发声通道/扫候选。Agent未听、新反馈0、measurement_validated=false、通用规律0，单Agent/CI仅手动。

[15字CSV](own-li-entry-pitch-probe-20261013-words.csv)、[阶段CSV](own-li-entry-pitch-probe-20261013-stages.csv)、[JSON](own-li-entry-pitch-probe-20261013.json)、[审计](own-li-entry-pitch-probe-20261013-audit.json)。
