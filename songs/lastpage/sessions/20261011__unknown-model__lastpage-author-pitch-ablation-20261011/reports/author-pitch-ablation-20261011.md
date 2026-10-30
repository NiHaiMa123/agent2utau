# 最后一页：白烁工程副本的音高因素拆分

2026-10-11。状态：author_pitch_ablation_delivered_pending_listening。

用户明确要求“这一段你复制白烁的项目，然后逐步更改内容，比如音高线，pitch这些，看下是什么影响的”。本轮据此在新研究目录复制上轮已绑定的白烁主轨part2参考工程，不改作者原件、自己的歌曲或Skill。作者历史1.56不在本机，沿用上轮1.65c；不是历史原声复原或自己的制作候选。

## 四版有限设计

|版本|PITD|note pitch|比较|
|---|---|---|---|
|A|保留|保留|新固定种子基线|
|P|原网格ys全部0|保留|P−A|
|N|保留|各点y=0，snap_first=false，x/shape保留|N−A|
|PN|原网格ys全部0|同N|PN−P、PN−N|

音符tone/tuning、延续音、歌词、时长、位置、音素时钟、全部非音高曲线与两阶段speaker保持。所有内置vibrato length原为0。N取消相对偏移和首点自动接前音；原生音符过渡仍在，不称作固定绝对音高。PITD可能补偿note基底，两因素需检查交互，PN不能单独解释一个病因。本轮没有把我们的曲线重定时到作者工程，也没有移调。

完整42音符/3原生句保留；上述字段中和覆盖此part，原生缓存技术渲染覆盖4版×3句=12上下文。真正固定种子研究仅前两句“想把你抱进身体里面／不敢让你看见”，4版×2句×2同输入重复=16套新variance/acoustic/vocoder波形，只有2个独立上下文，重复不扩大样本量。

## 技术检查与试听边界

独立检查确认原生读回、音符身份、实际音素时钟、5tick before-PITD/final拆分和两阶段speaker。人工TENC/BREC/VOIC/SHFC保持，作者已有SHFC继续作用在对应条件路径；音高修改允许variance pitch、三个预测及最终发声输入、acoustic f0和vocoder F0共同响应，不能解释为仅声码器变化。全部重新预测，使用variance11/acoustic101；16套波形的同输入重复在输入/预测/mel/vocoder F0/PCM均精确。实际特征裁剪按版本/句逐项登记，不把裁剪状态或数值变化当听觉结论。

44100Hz mono PCM24、全部固定声增益1.5，作者无DYN曲线且声明默认0dB，fresh raw采用unity包络；按原生前导时钟在44100网格拼接、叠加句尾，无归一化/压缩/BGM。新预览212.0–220.5秒，较旧参考220.35末端稍延长以包含第二句释放，不加入第三句。原生完整缓存技术WAV与真正交付fresh PCM分开。16次FCPE/RMVPE观测、整句及15字末音素/主体窗口的电平/最终特征只作代理；检测器未经本次真值校准，发声实感、破音病因及自然度均待人工。

准备打包时误把DYN默认单位写为100，断言拦截；实际工程默认0dB且无曲线，unity波形操作正确、无需重合成。失败脚本与首次打包PCM原字节在新run的logs/rejected-packaging保留，修正说明后重新打包。作者原A的VOIC输入已有模型下限裁剪，替换版按各自新预测合法裁剪；不是本轮人工VOIC干预、文件削波或听觉改善。各版数量见下面表格，不能据此宣称单通道病因。

**先确认新A仍然偏实。** 之前认可的参考由原生缓存随机性及PCM16出口产生，本轮A是固定种子fresh/PCM24；未声称二者PCM相同。若新A本身偏虚，应停止曲线因素解释，先检查基线执行差异。旧参考音频原字节另交付。再比较P/N/PN对实感、音高/旋律、字头/破音及音量的影响；缺失细分反馈保留unknown。Agent未听，本轮新反馈0、未采用、通用规律0、measurement_validated=false。

表1引用PER:S1、改变PARAM:C03.01/C02.02/C02.04、保留C01.01；表2新增RESP:LASTPAGE-AUTHOR-PITCH-ABLATION-01有限开发记录，不更新旧标签或普遍规则。先前Bright25与VOIC阴性结果保持收口；原Normal75/Classic25、范围200及抱C保持。

32个观测窗口覆盖2个整句及15字末音素/主体，各4组比较；整句P−A的双检测器绝对音分差中位约16–18c，N−A约1c，局部连接可能更大。整句RMS差约−0.28～+0.37dB；这些结果不证明实感差异。47项既有固定噪声/PCM/原生前置契约本机通过，CI保持workflow_dispatch。

|句|版本|BREC裁剪帧|VOIC裁剪帧|TENC裁剪帧|
|---|---|---:|---:|---:|
|0|A|0|40|0|
|0|P|0|41|0|
|0|N|0|35|0|
|0|PN|0|36|0|
|1|A|0|45|0|
|1|P|0|42|0|
|1|N|0|41|0|
|1|PN|0|41|0|

- [A独立人声](../../../../../runs/experiments/lastpage-author-pitch-ablation-20261011/delivery/A_two_phrases.wav)
- [P独立人声](../../../../../runs/experiments/lastpage-author-pitch-ablation-20261011/delivery/P_two_phrases.wav)
- [N独立人声](../../../../../runs/experiments/lastpage-author-pitch-ablation-20261011/delivery/N_two_phrases.wav)
- [PN独立人声](../../../../../runs/experiments/lastpage-author-pitch-ablation-20261011/delivery/PN_two_phrases.wav)
- [previous_liked_reference独立人声](../../../../../runs/experiments/lastpage-author-pitch-ablation-20261011/delivery/previous_liked_author_reference.wav)

[JSON](../../../../../docs/reports/lastpage/author-pitch-ablation-20261011.json)、[窗口CSV](../../../reports/legacy/author-pitch-ablation-20261011-windows.csv)、[审计](author-pitch-ablation-20261011-audit.json)。单Agent，CI仅手动。下一步接本批试听，逐组解释后才选后续有限替换。
