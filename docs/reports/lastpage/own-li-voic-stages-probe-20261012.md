# 最后一页：知识接入与里字VOIC阶段试听G

2026-10-12。用户授权“补齐，还有发声的强弱开始研究并提供试听”。保持Skill、原歌/音频、作者原件、旧封存报告/run及CI手动；本批明确允许更改生产knowledge/workflow/CLI和相关契约测试/文档，修改前原字节冻结，4个既有路径从旧全量保护声明单独登记，不重写旧SHA或冒称这些代码未变。

## 知识实际接入

新增knowledge-context读取公开表1实体/参数和表2条件记录，来源由active-knowledge-sources目录显式列出，不读作者音频/曲线或研究缓存。此轮实际取回8ID，逐条use/reject/extrapolate及当前条件、理由、限制写入计划，来源SHA/原字段/决策覆盖校验通过，CLI实际返回与本runner的包逐字段精确。compile-functions要求schema2 knowledge_context，在输出目录或原生执行前拒绝缺失、过期、伪造字段或漏决策；旧schema1须显式迁移，历史封存不改。知识只约束依据，没有自动选剂量或证明Agent音乐判断正确；无匹配响应可明确absence_reason并保持unknown。

164项本机测试通过，包含阻止缺/漏知识先调用原生、来源变化/伪造记录/未知ID/遗漏限制/重复决策/非法泛化拒绝及原编译/音频/Skill等测试。15项专项也通过；初始pytest父临时目录缺失的15 setup errors原JUnit保留，修正环境后重跑，无代码失败被掩盖。详见[制作接入](../../guides/knowledge-use-in-production.md)。更新当前来源目录后新计划读新记录，旧receipt冻结当时目录选择及已绑定来源，不刷新旧实验。

## 里277单因素G

以已获“更好了”的F作工作比较基底，Bright40/Cute60声线与自身音符/所有音高/原生音素/CLR完整时钟保持，只有context28里i元音VOIC有序变化：到达213.0622917s前保持100，自己的主体锚点213.224295s到106，213.4152083s回102，213.5302083s前恢复100，元音213.5854167s退出100。逐段smoothstep零切线、原整数5tick网格采样与UI取整，非作者节点/数组搬运。TENC/BREC/SHFC/DYN保持F，固定输出增益1.5；+6UI是单个有限设计，不是通用力度常数。

原生35帧只在里元音改变voicing，最大模型增量0.72000003，独立采样/进入上升与回收非增通过；其它音素人工输入保持，native与fresh variance输入/三预测、两阶段speaker和vocoder F0精确F。context28 G/G_repeat2套新variance/acoustic/vocoder波形、固定11/101，所有重复精确，fresh只final voicing改变，裁剪0。context29保持封存F贡献，没有新fresh执行；2原生缓存技术上下文另列，2次新双F0及6个旧F数组绑定复用，不增加独立条件。82窗口包括原15字/辅音/两句77窗及里的5阶段。

|阶段|F RMS dBFS|G RMS dBFS|G−F dB|
|---|---:|---:|---:|
|li_entry|-16.222|-16.221|+0.001|
|li_build|-18.713|-18.555|+0.157|
|li_recover|-20.277|-20.009|+0.269|
|li_release|-20.425|-20.359|+0.066|
|li_descending|-22.866|-22.859|+0.007|


**实际响应较轻，绝对阶段RMS仍字头较强、后面减弱，没有验证成声能量已形成渐强。** G在主体相对F只约+0.157/+0.269dB，整里约+0.116dB；VOIC输入按计划上升再回收，不足以宣称听觉发力有层次或更像作者。RMS是电平代理，不等于感知发力/响度；没有为制造目标而额外加量、改DYN/音高、归一化或压缩。新听感待接，如果无可感知变化仍保留有限阴性。

## PCM交付和边界

完整245.577秒研究G人声按34贡献重建，只有context28贡献替换，context29继续F、其它32贡献/抱C保持，DYN0dB/gain1、44100Hz mono PCM24、固定1.5，峰值0.680706，无文件削波。原F全PCM重建、G量化/预览和支撑外PCM精确；第二句真实音素与看PCM精确，原89ms共享头padding有432样本微变，终止早于真实AP开始214.313542s，范围列明，未重定时/交叉淡化。

- [G新版两句](../../../runs/experiments/lastpage-own-li-voic-stages-20261012/delivery/G_two_phrases.wav)、[F基线](../../../runs/experiments/lastpage-own-control-neutral-20261012/delivery/F_two_phrases.wav)：209.4–218.0秒8.6秒，里约3.56–4.19秒。
- [白烁单独参考](../../../runs/experiments/lastpage-author-interaction-20261012/delivery/A_two_phrases.wav)：当前1.65c已有fresh A，212–220.5秒8.5秒，只作描述比较，非同音乐/时钟的因果对照。
- [完整研究G工程](../../../runs/experiments/lastpage-own-li-voic-stages-20261012/delivery/lastpage_own_li_voic_G.ustx)、[完整研究G人声](../../../runs/experiments/lastpage-own-li-voic-stages-20261012/delivery/lastpage_own_li_voic_G_vocal.wav)：未采用为原发布歌。

已补当前表2索引的新G行和表1关联，技术交付pending与后续反馈分开。下一步只接G−F里字力度发展/回收、实感/挤尖/咬字反馈，不自动扩大剂量或整曲采用。Agent未听，新反馈0，source_unknown106、旧阴性、接受抱C与未报维度保持，measurement_validated=false、通用规律0，单Agent、CI仅手动。

[15字CSV](own-li-voic-stages-probe-20261012-words.csv)、[阶段CSV](own-li-voic-stages-probe-20261012-stages.csv)、[JSON](own-li-voic-stages-probe-20261012.json)、[审计](own-li-voic-stages-probe-20261012-audit.json)。
