# 将虚实与“压低声音唱”分开：单个BREC隔离D

用户反馈“b更虚，但是c感觉像是压低声音唱的”，见[原话与范围](phonation-sentence-bc-virtuality-c-voice-feedback-20261017.md)。B/C的虚实相对方向可辨，但C还带有额外发声听感。记录该描述，不改写为已证明降调、生理压嗓、张力增大或自然度评分，也没有得到偏好C/自然实声接受。A和B都比C虚仍不能补出未听的A/B排序。

本轮不继续按组合强度加码或把C当合格实声锚点。仅新增研究D：**保留C完整VOIC包络（峰/平台200），只撤回BREC−80包络，恢复为零人工增量**。零BREC保留模型预测气声，并非无气声。音高、16phone时钟、8音符、两阶段声线、VOIC、TENC/DYN及其它输入全部保持。唯一假设是检验减气声处理是否参与该额外听感；结果未听，不宣布病因。

## 试听：先C，后D

同一句“下雨了，雨陪我哭泣”，中间停0.8秒。C直接保留上轮已听PCM；新D用一个固定整句衰减匹配C整体RMS，没有逐字压平强弱、EQ、压缩或BGM。RMS相同不保证感知响度完全相同。

![先C后D](E:/project/agent2utau/runs/research/phonation-sentence-brec-isolation-20261017/C-then-D.wav)

[反向D后C](E:/project/agent2utau/runs/research/phonation-sentence-brec-isolation-20261017/D-then-C.wav) · [D单独](E:/project/agent2utau/runs/research/phonation-sentence-brec-isolation-20261017/D-RMSmatched.wav)。先分别判断D的“压低声音唱”感觉是否变化，以及C/D的相对虚实；不要求同时作最佳版本或整句接受判断。

## 实际核验

冻结用户反馈/knowledge_context/逐ID决策和单因素协议后才生成D。研究副本仅删除C的一条BREC曲线，其余工程字段精确；两组原生最终音高和全16phone保持。新原生variance/acoustic探针核对：variance输入和预测、两阶段speaker、vocoder F0、VOIC/TENC及所有非BREC声学输入精确。breathiness输入恢复预测，元音外新增0帧，三通道模型特征裁剪0帧；原生默认随机状态，不冒称共同声学噪声的严格因果试听。

原生D波形无文件削波；原始裁切逐PCM精确保留，新D固定衰减系数约0.39681451，两版整句RMS差小于0.001dB。C原PCM、两顺序拼接均精确。新D独立提取FCPE/RMVPE，8/8元音有足够可靠主体；这些指标不分类“压着唱”或宣布自然度改善。实际音高输入相同也不反驳用户听到的发声特征。

## 记录与后续

当前研究目录`runs/research/phonation-sentence-brec-isolation-20261017`保存原文观察、B/C的1轴部分标签、独立核验、协议/知识、原生输入、D原始与主试听、实际F0与逐phone观察、C/D待评packet和交付SHA。额外发声描述独立保存，不塞进现有六轴自然度字段；旧模板/报告/pending保留原时态。

Skill虚实连续性页补入“相对更不虚不等于自然实声基准，组合带额外特征先拆因素”的规则，不记录固定剂量；40资源安装一致、125本地引用及仓库/安装quick_validate通过。当前雨爱工程、所有既有试听和先前实际输入SHA保持，单Agent、CI未运行，s15以后暂停。

下一步仅接C/D在虚实与该发声描述上的分别反馈。即使D减轻该特征，也只支持本句/剂量下BREC处理参与，不扩大为唯一病因；若仍在，VOIC/当前声线基底/条件交互等继续保持候选，不能直接宣布VOIC病因。歌曲修复、跨句一致性和通用虚实刻度仍未通过，不自动扩大实验。
