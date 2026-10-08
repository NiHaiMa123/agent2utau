# 最后一页 v02：3:04 TENC 单因素检验

状态：一个 A / A-repeat / B 实验完成，**实际 TENC 输入及声学响应已验证；口型改善和用户反馈成因仍 unknown**。未修改三份发布工程或 Skill，未开展参数搜索、整曲修复或 P2。

## 输入与干预

当前工程 `projects/latest/lastpage_loudness_v02.ustx` SHA256：
`a17d4bebdd3c5951f2b10138777a8fee8925ab5beb6bb70705342d1b6ba466af`。
反馈音频 v02 mix WAV SHA256：
`35f301641b4cacbf5baff0c52ae7db8b8e72291a2d1573b85ae8d6aee0463789`。

用户的 3:04 是近似时刻。本次锚定 part22/note5 的“抱” bao，完整声母 zh/b 为 183.602083–183.811458 秒，元音 zh/ao 为 183.811458–184.125000 秒。当前自身决策记录中，该字 TENC 有独立有限事件：183.821458–184.113000 秒，最大 UI +14；前后字事件不重叠。

B 仅将该事件的 52 个非零存储节点归零，保留原零端点和全部其他字段。原生采样实际改变 24 帧，183.833902–184.100931 秒，位于声明支撑内；最大 tension 特征差为 0.7。未动 BREC、VOIC、DYN、音高、音素、时值、speaker 或其他字的 TENC。B 是本机诊断副本，不是新的发布候选。

## 条件与执行

新建独立命名诊断桥，避免覆盖现有桥。桥导出原生采样控制增量及重采样后的 variance 预测，并以真实 acoustic/variance/linguistic cache key 验证输入。当前 A 导出与 v02 原输入逐项相同。B 先以相同绝对时钟的单上下文副本建立正常缓存，再从完整 B 工程导出；完整工程中所有非 tension 输入、音素、时钟及 variance 条件和预测逐项相同。

固定 YousaV1.65c、两阶段 Normal75/Classic25、variance seed11、acoustic seed101、native steps20/实际depth0.6、原权重、CPU 单线程执行。随机节点通过独立输入适配，所有 initializer 序列化字节不变；没有换种子、挑结果或改模型权重。每个 A、A-repeat、B 都实际重新执行 variance、acoustic 和 vocoder。linguistic encoder 输入及缓存哈希固定并显式复用。

原生 float32 预测加控制增量及裁剪精确还原当前输入。新合成中 B 也只改变 tension，variance 预测和所有其他 acoustic 输入精确相同。A 新波形与当前 v02 的 phrase22 原始波形逐样本相同；A-repeat 的输入、预测、mel、波形都与 A 相同，波形最大差 0。

保持原生 ApplyDynamics，固定 vocal1.5/backing0.7，不归一化、压缩或事后匹配响度。拼接明确复用另外 33 个未修改的当前自身短语及当前伴奏，保留邻接重叠贡献和原顺序。A 的 181.8–187.2 秒片段与已交付 mix 的 PCM24 逐样本相同。未重新生成整曲。

软件、Core、诊断桥、原桥依赖、配置、模型、embedding、缓存及输入文件哈希保存于本机 run；六份研究/发布工程和 36 份 Skill 文件保持原哈希。Core 与 P0 记录相同。首次调用现有桥遇到未支持命令，独立桥部署先遇到 runtime/deps 解析错误；按仓库既有依赖部署方式解决，未修改音频阈值或实验设计。

## 实际结果

分析窗口是完整 zh/ao 元音，未只选变化最大的帧。

| 指标 | A-repeat 对 A | B 对 A |
|---|---:|---:|
| 27 帧 native log-mel RMS 差 | 0 | 0.075359 |
| 去除每帧平均电平后的 log-mel 谱形 RMS 差 | 0 | 0.074480 |
| 元音 RMS 电平变化 | 0 dB | +0.190462 dB |
| 元音波形差 RMS | 0 | 0.012492 |
| FCPE 31 帧绝对音高差 p50 / p95 | 0 | 0.219 / 0.649 cents |
| RMVPE 31 帧绝对音高差 p50 / p95 | 0 | 0.190 / 0.541 cents |

两个实测 F0 方法均约 494–495 Hz，A-repeat 精确相同。A/B F0 只有很小的分析差异，未改变模型 F0 输入。谱形变化超过此次无变化重复的零差异，因而**“当前 TENC 偏移实际影响该语境的谱响应”得到支持**；变化不是单纯整体电平代理。但本实验没有给出听觉显著性阈值，不能把数值非零当成明显改善，也不能称共振峰或生理舌位已被识别。

高 F0 下共振峰估计保持 unknown；未用 F1/F2 或 log-mel 直接证明“假音/真音”。没有有效机器音频感知评价，Agent 未试听，`agent_perception=false`、`listening_pending=true`、`naturalness_accepted=false`。用户原反馈的唯一病因仍未验证，音素/预测基底/pitch 条件仍可能共同参与。

## 交付与验收

本机输出目录 `runs/lastpage_tenc_probe_20261008/`：原生 A/B 导出、有限干预记录、适配器与绑定、三份全新状态、原生 DYN、双 F0 和片段 PCM 校验。`delivery/A_B_mix.wav` 与 `A_B_vocal.wav` 都是 A 5.4 秒、静音 0.6 秒、B 5.4 秒；同时提供 A、A-repeat、B 独立片段。音频、模型、数组、诊断 USTX 和个人路径均不入 Git。

执行代码 `src/agent2utau/evaluation/controlled_probe.py` 是只读诊断工具，要求显式原生输入和支撑，拒绝音素、pitch、非选通道、variance 条件或缓存混杂。它不决策音乐、不改工程、不扫描参数。必要测试：`python -m pytest -q`，**75 passed**，其中新增 8 项检验混杂拒绝及电平/谱形区分。

本次单个实验到此停止。下一项只需对这份绑定版本的 A/B 做听感评价；在结果确认前不将局部干预写入通用 Skill 或整曲。

## 用户试听回报（2026-10-08）

用户对上次交付 A/B 回报：“没啥区别”。绑定的 `A_B_mix.wav` SHA256 为 `4e0c8cd5219e9517b073c4fccc2ebcc5485348c259a7366b3af34943a6f485bb`。因此本次取消 +14 TENC **没有获得可感知差异或改善的支持**，不采用 B 修整曲、不据此修改 Skill。此前的数值谱响应仍成立，用户回报不构成统计等价检验，也不能推出所有 TENC 设置均无效。Agent 仍未试听，原问题是否改善未确认。

反馈后只读核查当前交付绑定的自身状态：1:27“果”的 TENC/BREC/VOIC 人工增量都为零，但仍有同类用户反馈；人工 TENC 不能统一解释四处问题。四个字的预测 breathiness/voicing/tension 也没有足以单独判定听感的统一分界；音素与音区存在混杂，不能转而断言 BREC 或 VOIC 是病因。

找到三个可供进一步定位的原版“抱”：约1:14、3:04、3:31，均 zh/b→zh/ao，模型 F0 中位数约495 Hz，同为约71 MIDI。其预测 tension 中位数约1.23、1.13、1.18，breathiness 约-45.90、-45.65、-45.74；语境、完整轨迹、时长、voicing 及控制仍有差别，不冒称完全同条件。只有3:04已有异常标签，其余两处听感 unknown。

下一项收敛为**这三处同字、同音区的原版听感定位**。本机 `runs/lastpage_tenc_feedback_20261008/same_bao_original_vocal.wav` 按1:14、3:04、3:31顺序拼接，每段3.5秒、间隔0.6秒；源于当前已交付人声，PCM精确裁切，原vocal1.5增益不变，不归一化、不改参数、不重新合成。相同音素/音区若仍听出差别，再针对语境/预测/音素衔接设计单因素实验；若三处都同样偏假，则优先检查这类条件的共同模型响应。两种结果目前都未证实，不开始下一次声学干预。

## 同字试听反馈与条件路径复核

用户对上述三段回报：“我听着都一样”。比较文件SHA256：`fed09deada282f08f183fbc755f920bcfaec14be37fbc630c53d97feedd80477`。这只确认用户未感知三段的区别，没有明确三段均异常或均正常，不能自动给另两段补“偏假”标签。该组不能充当正常/异常对照；没有建立独属于3:04的局部漂移证据。

随后只读核查声库配置和当前交付绑定的 part8/22/28 原生导出：GENC 对应的 acoustic `gender` 全部0，`velocity` 全部1，声线两阶段固定Normal75/Classic25；当前 acoustic/variance 配置均未启用独立falsetto特征，实际输入也没有该字段。它们不能解释为这些控制在三处间突然切换，但这不排除模型隐含音色条件的作用。实际 depth 均为float32的0.6；此前报告误写了偏好设置1，现已纠正。三份实际输入和A/B都一直是0.6，未改变实验或重算结果。

路径依据分两层：本机已编译桥的采样代码、当前实际输入/模型配置；以及 [OpenUtau官方renderer源码](https://github.com/openutau/OpenUtau/blob/master/OpenUtau.Core/DiffSinger/DiffSingerRenderer.cs)、[variance源码](https://github.com/openutau/OpenUtau/blob/master/OpenUtau.Core/DiffSinger/DiffSingerVariance.cs)、[音素器源码](https://github.com/openutau/OpenUtau/blob/master/OpenUtau.Core/DiffSinger/DiffSingerBasePhonemizer.cs)。上游master只作机制核对，不冒称和当前Core DLL逐字相同或证明本机音素时长模型故障。

已核查机制：音素器将符号、时长和音符条件送入模型；variance读取pitch条件，acoustic读取tokens/durations、F0、speaker及发声特征。当前vocoder为pitch_controllable，SHFC/toneShift会影响variance的条件pitch和acoustic的条件F0，vocoder仍接收未偏移的F0。当前三处acoustic F0与vocoder F0逐帧相同，说明现有输入没有用这条偏移路径。GENC是另一路声学条件，不能将其等同于音素纠正。

下一项候选因此收敛为**隔离模型的音区条件与最终F0**：保持当前note/pitch/phone时钟、speaker、人工发声事件、噪声和混音，原生SHFC只改变一个有限元音支撑的条件pitch，重建variance/acoustic并保持vocoder F0不变。一个预先选定的有限候选和无变化重复即可；不扫描音区或偷用旧预测。所有下游预测通道的变化应视为所选上游因素的作用路径，不能冒称只改tension；现有`controlled_probe`会拒绝这样的输入，需要在执行前扩展明确的因果路径校验。此处仅完成源码/输入核查和试验设计，未生成新的改参音频；还不能归因音区、音素或声库模型。原版对照复听完成，通用Skill和发布工程保持。
