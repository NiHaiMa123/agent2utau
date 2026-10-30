# 第三句：播放选择修正与声线R对照

2026-10-18，按用户在[前四句完整参数审计](../../20261018__unknown-model__yuai-first4-full-parameter-audit-20261018/reports/first4-full-parameter-audit-20261018.md)后的“继续”执行。采用 singing-expression-editor 的声线基底/连续性流程，单Agent；未改Skill或启用CI，未启动第五句/s15以后。旧P的初步改善与“还是有问题”并存，旧严格音乐流程缺口不升级。

## 当前同一工程只修正保存的播放选择

`projects/latest/yuai_first14_single_track_baishuo_comparison.ustx` 保存为我们的主唱开启、白烁主唱及和声静音。原保存状态是我们的主唱静音、白烁主唱开启；不能据此倒推用户当时的实时播放路径。只替换两处mute布尔值，其它原字节保持，包括全部音符/曲线/音素、参考载荷、声库标识、轨道音量和平移。新SHA `81798b0e41a1940b0f256aebaf0c788c42ac9b743ff4bc71febadfe0cd81af7b`，旧文件和两标量定位在本轮run保存。OpenUtau内存中的旧工程需重新加载同一文件，不能把磁盘修正冒称已控制实时UI。

当前工程中的第三句仍是P，没有把未听R写成正式修复。两处来源选择修正与声线实验分别记账。

## 唯一新条件R的范围

以P当前主唱为基线，第三句两个原生短句的variance/acoustic帧声线从Normal65%+Classic35%改为Bright41%+Classic59%。这一混合条件来自上轮已验证的当前换库参考结论；本轮不加载作者音高/节点/音素数组，不移植作者演唱内容。R是一个**复合speaker混合因素**，不是Bright身份和Classic配比各自的单因素因果验证，也不代表独立设计/跨曲迁移或复原作者历史声音。

CLR仍为本工程逐phone的Normal，时长模型speaker及原有音素时序保持。仅cl01/cl05在第三句两侧无唱声余量内有限建立/恢复，26.25–31.9秒平台覆盖两个原生上下文及其padding；前两句和第四句声线不变。因此本轮仅测帧声线，不是参考的完整CLR/时长/上下文方案。当前138音符、22短句分组及原生音高、263音素几何和全部人工VOIC/BREC/TENC/DYN保持；DYN仍5。暂不重组AP/SP/EP，不加和声或改尾字时长。

声线变化会改变模型预测，已按新输入重新获取对应原生variance/acoustic缓存，不要求新预测等于P。两阶段384维embedding通过独立五基底解混，所选段全部帧为Bright41%+Classic59%；时长/linguistic原始输入、F0、gender、velocity、步数、depth及人工增量保持。最终三通道由各自新预测+原有增量独立重建，裁剪0帧。前两句及第四句两阶段输入、预测和PCM精确；模型和embedding实际文件SHA绑定。Normal的duration speaker与帧混合分开，不混淆CLR序号与clNN索引。

## 试听与增益

主试听约44.75秒：**先现版P的前四句，停0.8秒，再R的前四句**，仅第三句不同。R原始第三句RMS比P高约1.66862dB；主试听对整个第三句只乘一次固定0.82521847，保留字内强弱，匹配误差约-0.0000000dB。未逐字归一化、EQ/压缩或混伴奏。R研究USTX仍为原生同增益/DYN5，不能把R匹配音频冒称其未经处理的工程声音；若后续采用需单独落实并核查增益条件。

![现版P→声线R：完整连续语境](../../../../../runs/research/yuai-s03-frame-voice-contrast-20261018/current-then-R-context.wav)

[P→R完整第三句，电平匹配](../../../../../runs/research/yuai-s03-frame-voice-contrast-20261018/current-then-R-third.wav) · [P→R完整第三句，原始同增益](../../../../../runs/research/yuai-s03-frame-voice-contrast-20261018/current-then-R-raw-third.wav) · [R单独连续版，电平匹配](../../../../../runs/research/yuai-s03-frame-voice-contrast-20261018/R-matched-context.wav)。两类对照和顺序PCM均逐样本核验，第一二句/第四句保持，无削波。

新R匹配PCM的FCPE/RMVPE已重新提取；P复用与当前第三句PCM字节精确对应的既有双F0，未伪装新推理。两版各8/8元音有可靠主体，逐字共同可靠主体覆盖8/8。声学代理仅作描述，不由预测VOIC、周期性或谱倾斜宣布更实/更清亮。没有音频感知工具，Agent没有听过本组。

## 当前状态

局部执行核查完成；实感/气声、暗或压低/挤压感、第三句与邻句一致性及采用全部pending。新增一组已见句开发对照，不增加听觉标签，不宣称虚实评价器已完善或唯一病因已确定。待用户反馈后再选择下一层；不会自动加码、把R写回或同时改模型上下文。

本轮材料在`runs/research/yuai-s03-frame-voice-contrast-20261018`：前置知识/意图、单独routing收据、P/R研究副本、原生pitch/phones、新实际两阶段输入/embedding/预测、同增益/整句匹配PCM、双F0、共同主体描述、待评包及SHA保护核查。Skill40文件和安装副本保持，原作者工程/旧P产物保持。没有生产代码变化，不增加镜像测试；本机原生检查及仓库门禁单列。
