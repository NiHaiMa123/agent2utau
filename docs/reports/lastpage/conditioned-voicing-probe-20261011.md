# 最后一页：有限VOIC候选与两完整句交付

2026-10-11。状态：conditioned_voicing_delivered_pending_listening。用户“下一步”授权执行上轮准备的单候选。已否决的Bright25路线收口；本轮原Normal75/Classic25保持。

第一句“想把你抱进身体里面”中五个元音叠加有限VOIC，15字台账完整；想/抱/身/体输入保持，第二句“不敢让你看见”作为完整保持对照。补偿参考−44、比例0.5、特征增量上限3是Agent的有限设计，不是听觉阈值、逐字负标签或白烁拟合。原音高/音素/人工气声与张力/SHFC/DYN和两阶段speaker保持。自选慢线性建立、保持和退出，原5tick整数网格、元音内零边界，同元音延续不重启。

编译第一次被范围200拒绝：你272原VOIC190叠加25需要215。失败快照保留；仅新工程明确设上限215，原定五剂量未改，原生roundtrip表达声明与曲线精确保留。独立读回证明仅五元音152帧voicing改变，实际增量在五段支撑并集内，非目标辅音/AP/SP输入保持；模型特征裁剪0。精确核查原生乘12再除100的float32顺序，检查器初始算术误差、语法和输出日志修正记录保留，未放宽断言。

两完整上下文各A/A_repeat/B/B_repeat，固定variance11/acoustic101，8次新variance及8套acoustic/vocoder波形；原生缓存4套技术参考另列，不混计。原A完整预测/输入/波形与旧seeded记录精确；重复、两阶段speaker、三预测、variance输入、vocoder F0精确，fresh仅第一句最终voicing改变；第二句fresh输入/mel/raw PCM完全相同。

| 字/ID | 增量VOIC | 元音RMS差dB | FCPE差p50/max(c) | RMVPE差p50/max(c) |
|---|---:|---:|---:|---:|
| 把/271 | +10 | +0.519 | 0.056/0.751 | 0.062/0.834 |
| 你/272 | +25 | +1.504 | 0.226/2.748 | 0.201/1.951 |
| 进/274 | +25 | +1.460 | 0.503/2.856 | 0.734/5.448 |
| 里/277 | +11 | +0.642 | 0.070/0.596 | 0.063/0.431 |
| 面/278 | +12 | +0.702 | 0.088/0.641 | 0.097/0.687 |

上述数值是有限技术响应，RMS不是感知响度或收实验收，检测F0不是已校准真值。共77窗口包含15字主体/入口/退出、可定位声母和两完整上下文，30/50ms窗、5ms步；8次双F0检测只取共同有声、有限正值帧，不跨无声插值。其它输入不变也不保证第一句其它字或声母的声学输出完全不变，邻域/副作用仍须试听。

完整245.577秒人声由32句旧贡献及2句新B贡献组装，实际仅context28贡献改变；context29 B=A。44100Hz mono PCM24、原生DYN及固定增益1.5，峰值0.661376，无归一化/压缩/BGM。独立重建全部34贡献与PCM量化、原基线重建、正反组装、预览截取及原抱C通过。输出outside context28贡献支撑精确。

两句原生波形有89ms重叠，context29头部padding含上一句的新尾帧；整曲该padding的3764个样本变化。其变化结束214.309456秒，早于第二句首个真实AP开始214.313542秒；第二句所有真实音素至尾部、六个元音及“看”的整曲PCM精确保持。原“整段context29混合窗口精确”的组装断言被拒绝且失败WAV保留，本轮明确独立贡献与共享padding的范围，未裁切波形或另改控制。已有“看”偏实标签保持，不扩大为全句验收。

- [候选B两句](../../../runs/experiments/lastpage-conditioned-voicing-20261011/delivery/B_same_lyrics_vocal.wav)：209.4–218.0秒，里约3.56秒、看约6.93秒。
- [原A两句](../../../runs/research/lastpage-li-kan-author-reference-20261011/delivery/agent_acceptedC_same_lyrics_vocal.wav)。
- [白烁独立参考](../../../runs/research/lastpage-li-kan-author-reference-20261011/delivery/baishuo_current165c_reference_vocal.wav)：原件不变，沿用上轮当前1.65c参考，非历史1.56录音。
- [完整B人声](../../../runs/experiments/lastpage-conditioned-voicing-20261011/delivery/lastpage_conditioned_voicing_B_vocal.wav)、[完整B工程](../../../runs/experiments/lastpage-conditioned-voicing-20261011/delivery/lastpage_conditioned_voicing_B.ustx)：仅第一句改变，未采用、未宣称整曲修复。

反馈任务是第一句是否更实/连贯，是否出现破音、咬字/响度副作用；第二句为保持对照。Agent未听，新反馈0，未报维度unknown。试听后接受或收口，不自动加量或追加候选。表1PER:S1与PARAM:C11.01绑定本例，表2补充RESP:LASTPAGE-CONDITIONED-VOIC-01登记B−A；这是1个受影响完整上下文/5元音的开发对照，重复不增加独立条件，不是新留出或通用规律。全部measurement_validated仍false。源unknown106、抱C及原歌曲/音频/Skill/作者原件保持；单Agent、CI仅手动。

47项相关契约测试通过，独立native/fresh/PCM与双F0数组检查通过。详见[15字台账](conditioned-voicing-probe-20261011-words.csv)、[JSON](conditioned-voicing-probe-20261011.json)、[审计](conditioned-voicing-probe-20261011-audit.json)。
