# 有限协议：SHFC直接条件与预测依赖分离

2026-10-10，T2D-SHFC-PATHS-01 v1。状态：设计冻结，尚未执行；研究runner/独立检查器待实现。机器执行规格以[JSON](shfc-path-separation-v1.json)为准。

主问题是已有抱C局部响应的路径来源，以及同一固定条件在另一偏实元音中的回退。两个条件均已用于设计，不是独立留出；不重新试果SHFC或增大BREC。

| 条件/任务 | 元音/音高 | Q5四锚点（秒） | 原标签范围 |
|---|---|---|---|
| word225/part22，mechanism_discrimination_known_problem | zh/ao/MIDI71 | 183.731458333, 183.876458333, 184.058000000, 184.113000000 | reported_false_forward；并非全维度验收 |
| word214/part21，cross_vowel_regression_check_reported_solid | zh/ir/MIDI69 | 175.961666667, 176.106666667, 176.291333333, 176.346333333 | reported_solid；并非全维度验收 |

固定-400c、145ms进入/55ms退出，5tick编码。原part-local整数5tick按timeAxis评估Q5，以五成双取整为整数cents；名义支撑外0，原生线性采样另核查。抱锚点保持原接受C名义值，不能仅凭同函数名字认定S与旧C精确；只的相对元音时钟同函数，峰值/实支撑需独立核查，不按结果改幅度。原v02为诊断基底，已接受抱C的制作方案保留。

| 版本 | acoustic F0 | 新variance预测 | 原生可等价编码 |
|---|---|---|---|
| A | unshifted | fresh_unshifted_same_phrase | True |
| S | SHFC_shifted | fresh_SHFC_shifted_same_phrase | True |
| D | SHFC_shifted | fresh_unshifted_same_phrase | False |
| P | unshifted | fresh_SHFC_shifted_same_phrase | False |

D/P只在新研究run交换同条件、同新批次A/S的三通道预测组，再加不变人工增量；不用旧数组、其它字或作者数组。D/P不是生产原生出口，也不能分别归因某一个发声通道。

## 执行前门槛

- 2E首先实现独立研究runner与验证器；现controlled_probe只支持A/A-repeat/B，没有D/P接口，不直接调用为路径分离
- 重新SHA核查当前runtime47项及依赖、原baseline工程、fresh模型和noise适配器；不一致停止，不升级安装
- 先用有限合成数组/故意错误检查器验证D-A仅f0、P-A仅三最终条件、S-D仅预测组、S-P仅f0，非选条件及vocoder F0精确；这些数组不算真实检测器验证
- A/S使用现SHFC native隔离检查；新原生输出是桥接获取条件的缓存，不算本预算的seeded诊断波形
- 每变体两次输入/预测/波形精确；所有weights/noise/speaker/manual/phone时钟与clip计数保存；任何非有限/新裁剪/峰值>=1停止交付
- 独立数值/PCM窗检查通过后方交付试听；F0估计可unknown，不能拿未经验证检测器作自然度门禁

## 有限解释

- S-A若本轮无可感知差别，保留既往C-B局部接受；本轮不支持新的S-A效果解释，停止扩大验证
- D-A有同向可用响应可支持此研究反事实中的直接路径作用，P-A同理预测组；不能归给单一VOIC/BREC/TENC或生理机制
- S可感知而D/P均未感知，只记录联合路径/剂量下的结果，不以未感知宣布分量为零或证明交互
- 数值interaction=metric(S)-metric(D)-metric(P)+metric(A)仅用于同定义连续代理，不用于主观词/未知/检测冲突，也不代表自然度
- word214任一新副作用限定适用范围；2个条件均已参与设计，不能称留出/跨曲迁移或通用规律

## 停止条件

- 不加剂量、不扫时间/元音/seed、不补第三条件、不恢复果SHFC或BREC/VOIC提案
- 缺可靠接口/原生隔离失败/runtime差异/数值重复不精确→技术停止并记录依赖缺口，不转自动搜索
- 新破音/响度下降/咬字或邻字回退→该条件不可用，保留失败；不加增益掩盖
- 无区别/不确定→本协议限定阴性/unknown；不等待总会成功的候选
- 最多本批16套seeded新波形、10组主对照；结束后收集结论，2F留出/2G整句全曲/2H Skill需另明确范围

## 数量、观测与人工试听

每条件A/S/D/P均同输入两次：共8次variance推理、16套seeded acoustic/vocoder波形。原生桥接条件获取另保留技术缓存，不算新因果证据。重复只检查精确复现，不是独立效应复制；初始化/IO失败仅同输入重试一次，失败保留。

两阶段Normal75/Classic25、variance11/acoustic101、steps20/depth0.6、44.1k/512及历史47项runtime期望固定；当前安装需2E重查。模型适配只在新run，权重不改。目标pitch/phones/时钟、原人工发声基底/DYN与1.5/.7增益固定，无响度匹配/归一化/压缩。保留整句、声母/元音核心/入口/退出、前后完整phone，核查完整预测与邻字响应。

30/50ms中心窗RMS/peak、hop5ms、半开样本索引ceil(t*sr)，不足完整窗不补零；零能量保存null/zero。mel与去整体电平谱形只是代理。双F0必须绑定模型/时钟/有效率，冲突unknown；vocoder输入固定不保证实际输出F0固定。没有可靠formant、破音或生理寄存器真值，不能用数字代理宣布自然。

人工试听在2E所有技术隔离/复现检查通过后：每条件固定S-A/D-A/P-A/S-D/S-P五组，共10组主对照；各对照保留双顺序及匿名编码、独立上下文文件，同增益混音复查。记录可感知差别/不确定、可用方向、字头/咬字/破音位置、主观响度/邻字回退。缺时间/设备/盲测信息记unknown；未取得反馈即pending。未做独立留出/跨曲/全曲，不改Skill。
