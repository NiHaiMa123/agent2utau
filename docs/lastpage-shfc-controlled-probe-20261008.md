# 最后一页：模型音区条件与声码器 F0 隔离检验

用户授权“下一步”后，完成一个预先选定的 SHFC A/A-repeat/B 实验。**原生条件路径与确定性响应已验证；实测 F0 只有近似保持，口型/真假声改善尚待评价**。当前发布 USTX、Skill 和旧交付保持原样，未扫描参数或修整曲。

## 范围与假设

前轮取消“抱”的 +14 TENC，用户回报“没啥区别”；同字原版三段回报“我听着都一样”。后一条没有明确正常/异常标签。不能据此认定模型有病，或给所有同字添加异常标签。

本次仍绑定 LastPage v02 工程SHA `a17d4bebdd3c5951f2b10138777a8fee8925ab5beb6bb70705342d1b6ba466af`，反馈完整mix SHA `35f301641b4cacbf5baff0c52ae7db8b8e72291a2d1573b85ae8d6aee0463789`。目标是part22/note5“抱”，zh/b 183.602083–183.811458秒、zh/ao 183.811458–184.125000秒；完整短语重新处理。

假设：同一元音的模型条件音区影响当前声学谱/发声响应。B在元音183.821458–184.113000秒施加有限SHFC，最大 **-400 cents（-4半音）**，用55ms平滑建立/退出、整型节点量化；只选这一个条件偏移量。测试不以换音符或移调整曲实现。声码器继续接收原F0，其他人工发声控制、音素时值、GENC、speaker、噪声和混音保持。

SHFC会同时改变variance条件pitch和acoustic条件F0，并由新variance预测影响三个发声通道；这些是所选上游因素的下游路径。实验不能将响应进一步归因到单个发声通道，也不能直接证明生理真假声或共振峰异常。[OpenUtau variance路径](https://github.com/openutau/OpenUtau/blob/master/OpenUtau.Core/DiffSinger/DiffSingerVariance.cs)、[renderer路径](https://github.com/openutau/OpenUtau/blob/master/OpenUtau.Core/DiffSinger/DiffSingerRenderer.cs)只作上游机制参考；本机实际输入和缓存验证是此次执行证据。

## 原生核查与失败保留

原项目SHFC描述范围为-12..12，实际存储/采样值按cents传入。初稿误将-4解释为-4半音，原生读回仅为-4c、variance -0.04半音，隔离校验拒绝后未进行确定性合成。该失败的工程、原生缓存导出和空输出保存在本机run的`rejected_4cent/`，没有作为有效试听或新增候选使用。

修正的是单位实现：诊断B明确将**所选SHFC表达**范围声明为-1200..1200并写-400，其余表达范围不变。当前发布工程范围不动。除这两个声明范围字段和part22新增SHFC曲线外，全部工程字段相同。这是原定一个-4半音干预的正确编码，不是看结果后加大控制或换候选。

新建独立命名桥导出acoustic采样tone_shift_cents和variance采样tone_shift_semitones。A/B均以实际native cache key验证；B用单上下文建立正常缓存，再从完整B工程导出。输入验证结果：

- SHFC实际最大-400c，variance实际最大-4半音；24帧非零，183.833902–184.100931秒，处于声明支撑内。
- variance输入只有`pitch`变化；linguistic tokens/durations/languages、encoder缓存、模型和speaker相同。
- acoustic直接条件只有F0变化；BREC/VOIC/TENC人工增量逐帧相同，新的三个预测及最终输入是允许的下游变化。原生float32相加/裁剪精确复现。
- vocoder F0逐帧相同，原note/pitch/phone几何相同，GENC=0、velocity=1、两阶段Normal75/Classic25相同。
- 原生SHFC→variance加法、SHFC→acoustic频率倍率逐帧核查；没有用旧预测或手工改feed冒充原生接口。

## 重新计算与拼接

每份A、A-repeat、B实际执行新variance11/acoustic101/vocoder。随机节点适配后所有initializer字节不变；同一噪声、CPU单线程、steps20、**实际depth0.6**，权重、软件、模型配置/embedding及缓存哈希冻结。linguistic encoder输入/缓存相同并显式复用。

A新波形与当前v02 phrase22逐样本相同，A-repeat输入/预测/mel/波形精确相同，重复波形最大差0。B完整上下文重新预测，三个预测最大绝对变化约17.198、8.526、3.662；影响传播到有限SHFC支撑以外的短语帧，未裁成字内旧状态拼贴，也未将这些全局效应隐藏。相邻短语仍明确复用当前未改的自身波形，无作者输入。

三份新波形执行同一原生ApplyDynamics，乘法精确。保持vocal1.5/backing0.7，不归一化、压缩或事后匹配响度；按原顺序和邻接重叠拼接。A的181.8–187.2秒片段与当前交付mix PCM24逐样本相同。A/B纯人声峰值约0.663/0.666，混音峰值均约0.766，无削波。没有重新导出整曲。

## 响应与实测 F0 的局限

窗口包含完整zh/ao元音，不挑最大反应帧。

| 指标 | A-repeat对A | B对A |
|---|---:|---:|
| 27帧native log-mel RMS差 | 0 | 1.729588 |
| 去除每帧平均电平后的谱形RMS差 | 0 | 1.610630 |
| 元音RMS电平变化 | 0dB | -0.113237dB |
| 元音波形差RMS | 0 | 0.053325 |
| FCPE 31帧绝对F0差p50/p95/max | 0 | 2.457/17.108/44.498c |
| RMVPE 31帧绝对F0差p50/p95/max | 0 | 1.708/26.602/40.384c |

FCPE元音中位数A494.329Hz/B495.807Hz，RMVPE A494.929Hz/B496.107Hz。两方法逐帧有符号差中位数接近0，主体保持相近音区，但局部过渡有40–45c检测差。**固定的是声码器F0输入，不能声称实测输出F0精确相同**；估计器对变化后的谱也可能响应，当前没有独立证据分解真实频率变化与估计偏差。因此这是原生条件路径的有效响应实验，尚非完全固定实测F0的纯共振峰因果证明。

SHFC输入确实改变预测和谱形，响应超过零差异重复，元音平均电平变化很小；数值响应不能代替口型改善。音区、发声预测和谱条件的共同路径尚不能进一步拆分；高F0共振峰与生理真假声均unknown。`agent_perception=false`、`listening_pending=true`、`naturalness_accepted=false`。如果用户仍听不出区别，不将本B用于生产；若有听感改变，也需分清改善、普通音色变化或新伪影。

## 交付与验证

本机`runs/lastpage_shfc_probe_20261008/`保存输入/范围声明、失败单位稿、新桥、原生A/B导出、三份新模型状态、DYN、谱响应、双F0、交付PCM和SHA绑定。`delivery/A_B_vocal.wav`及`A_B_mix.wav`为A5.4秒、静音0.6秒、B5.4秒，同时保存独立A/A-repeat/B。

通用只读探针新增`--mode shfc`，保留旧`manual_cancel`的严格限制；SHFC模式拒绝音素/speaker/输出F0泄漏、错误单位、支持越界或未声明的手工通道变化。新增9项负对照/路径测试，完整pytest **84 passed**。桥编译通过，两个既有平台/过时字段警告保留。发布前审计六份工程/36份Skill、当前旧run绑定文件及前轮TENC实验输出；音频、模型、缓存、数组、诊断USTX及个人路径均不入Git。

这一个实验结束后等待此版本听感反馈，不自动扫SHFC、GENC或更多种子，不修改Skill或整曲。
