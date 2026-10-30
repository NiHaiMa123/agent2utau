# R写入同一工程供OpenUtau查看

用户“你都在项目里修改，我在opentuau里查看”，明确要求修订直接在同一工作工程落地。已将紧前[声线R](../../20261018__unknown-model__yuai-s03-frame-voice-contrast-20261018/reports/third-phrase-frame-voice-contrast-20261018.md)写回 `projects/latest/yuai_first14_single_track_baishuo_comparison.ustx`，新SHA `f1a78827d58f551c3f052d68d3efb4f202be8e2bff614b78a4ab2eb418ffd126`。这是查看候选的授权，不是R听感接受或虚实改善；[工作方式记录](../../../reports/legacy/same-project-review-workflow-request-20261018.md)已单独保存。

仅第三句采用Bright41/Classic59帧声线曲线cl01/cl05；CLR/时长speaker保持Normal，音高线、263音素几何、138音符、模型分组、VOIC/BREC/TENC及参考轨载荷保持。我们主唱开启、参考主唱/和声静音的播放设置保持；前两句和已接受第四句实际输入、预测和PCM精确于R研究基底。曲线块外原字节保持。

上一轮主试听的R用了整句固定增益0.8252184716。原生DYN从5换为−12（约−1.2dB），合并该增益并保留原有有限第三句区间；理论量化误差约−0.03138dB，当前新原生第三句与已交付R匹配音频实际RMS差-0.0316103dB，归一相关0.999999880。并非PCM完全相同，量化/边缘尾差保留。没有逐字归一化、外部效果或音频替换；新工程渲染本身包含该电平，不能只用外置试听代替工程修改。

完整22原生pitch/263音素精确于R，两阶段7短句实际输入、speaker、预测、F0和人工增量精确于R；仅输出DYN变化，邻句PCM精确、无削波。当前原生第三句有新FCPE/RMVPE绑定，Agent未听过，当前工程效果待用户在OpenUtau确认。旧严格音乐流程缺口未升级，未追加听觉标签或通用规律。

备份、知识接入、增益计划、完整研究/核查副本、实际输入、新原生音频及原位收据位于`runs/production/yuai-s03-R-writeback-20261018`。后续修改仍沿用当前同一USTX；研究副本用于保护和执行核查，交付时应把当前任务候选落实同一工程，不能再次只交音频而让工程停在旧版。OpenUtau中已打开文件需重新加载磁盘上的同一文件；没有控制实时UI或确认其内存状态。

Skill40及安装一致、作者原件和旧R产物SHA保持，单Agent、自动CI未运行。第五句/s15以后未启动；此轮先由用户查看第三句，未获新指示不继续叠加参数或改变上下文。
