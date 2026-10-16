# 表1具体控制核查：阶段C续审

2026-10-09。48个导航分组已有352条具体字段/执行项（首批184、第二批136、编辑/扩展续审32条，前320个PARAM ID保持）。**C为reviewed_with_explicit_gaps：固定范围审查完成，非默认本机执行与开放扩展仍有确认缺口；D–F未执行**。固定31节点、导出/播放/pan law、本机静态矩阵及偏好/预设/网格写入分别核查。

完整记录：[CSV](control-details.csv)、[JSON](control-details.json)。每项包含PARAM ID、旧C分组、字段、引擎、默认/范围、单位、换算、采样/裁剪、读取锚点、作用阶段、重算、支持/未确认状态和局限。范围须区分上游默认、工程声明和模型clip，缺值不能猜成可用。

## 本轮实际证据

- 原44+第二批25冻结源码SHA一致；编辑续审21份中4份重复重查一致、新增17份，共86份唯一来源。绑定单列，不覆盖旧snapshot；每行有SHA/锚点/行号，不等于非默认执行测试。
- 本机Core/四配置/发布工程六绑定重查一致；另对Core与App离线读取PE完整类型成员和选定IL，保存SHA、版本、MVID、方法token与指令位置。[本机能力矩阵](local-capability-review.json)有明确的存在/缺失/未执行边界；不加载目标DLL，不启动OpenUtau，不读live偏好/权重/音频。
- 原生输入/PCM证据沿用已绑定实验，不扩大条件。本轮没有新的导出音频、推理或试听；静态公式与调用路径不证明听感。

## 已明确的易混项

| 项 | 本次区分 | 固定源码入口 |
|---|---|---|
| notes[].tone | AdjustedTone=tone+tuning/100；phone选择用tone，最终目标用AdjustedTone；移调是显式改tone/PITD等字段的操作，key标签不移调 | [读取/声明](https://github.com/openutau/OpenUtau/blob/5c3c83bbeced96718e85e4a96d127de3287cd14b/OpenUtau.Core/Ustx/UNote.cs#L19) |
| voice_parts[].curves[pitd].xs/ys | 目标=before-PITD+PITD；before-PITD仅编码；实测F0不由输入精确保证 | [读取/声明](https://github.com/openutau/OpenUtau/blob/5c3c83bbeced96718e85e4a96d127de3287cd14b/OpenUtau.Core/Render/RenderPhrase.cs#L188) |
| curves[dyn].xs/ys | value==描述min则0振幅，否则10^(value*0.1/20)；最低值特殊静音而非普通-24dB；不改变发声预测 | [读取/声明](https://github.com/openutau/OpenUtau/blob/5c3c83bbeced96718e85e4a96d127de3287cd14b/OpenUtau.Core/Render/RenderPhrase.cs#L475) |
| curves[voic].xs/ys | pred+(value-100)*12/100，final clip[-96,0]；feature不是PCM dB/闭合商/撕裂度；预测基底不因人工零增量消失 | [读取/声明](https://github.com/openutau/OpenUtau/blob/5c3c83bbeced96718e85e4a96d127de3287cd14b/OpenUtau.Core/DiffSinger/DiffSingerUtils.cs#L18) |
| curves[shfc].xs/ys | variance pitch+=SHFC/100；当前acoustic F0*=2^(SHFC/1200)，vocoder保留目标F0；-4存储是-4c而非-4半音；预测及邻字变化，不独立锁定PCM F0 | [读取/声明](https://github.com/openutau/OpenUtau/blob/5c3c83bbeced96718e85e4a96d127de3287cd14b/OpenUtau.Core/DiffSinger/DiffSingerRenderer.cs#L265) |
| curves[genc].xs/ys | range[-5,+5]：gender=-value*12/5/100；-100→+2.4，+100→-2.4；模型gender张量量，不是实测F1/F2半音移动 | [读取/声明](https://github.com/openutau/OpenUtau/blob/5c3c83bbeced96718e85e4a96d127de3287cd14b/OpenUtau.Core/DiffSinger/DiffSingerRenderer.cs#L332) |
| curves[velc].xs/ys | velocity=2^((value-100)/100)，0→0.5/100→1/200→2；未显式声明的工程不把name存在当新控制已写入；非音素时长倍率 | [读取/声明](https://github.com/openutau/OpenUtau/blob/5c3c83bbeced96718e85e4a96d127de3287cd14b/OpenUtau.Core/DiffSinger/DiffSingerRenderer.cs#L343) |
| phoneme_expressions[clr].index/value | ToPhonemizerNote按index取color，subbank suffix选speaker；CLR options名不自动证明帧阶段embedding；索引0不是每phone复制 | [读取/声明](https://github.com/openutau/OpenUtau/blob/5c3c83bbeced96718e85e4a96d127de3287cd14b/OpenUtau.Core/Ustx/UNote.cs#L147) |
| phoneme_expressions[vel].value | phonemizer attr.consonantStretchRatio=2^(1-value/100)；DiffSingerBase本次未找到此属性读取，不能说本机g/uo时长已可控 | [读取/声明](https://github.com/openutau/OpenUtau/blob/5c3c83bbeced96718e85e4a96d127de3287cd14b/OpenUtau.Core/Ustx/UNote.cs#L141) |
| tracks[].mix_fx.CompPreset | 名称还用于选择attack/release，不只是UI标签；本机整体MixFx读取路径存在；上游与本机独立开关/live刷新有差异，未做非默认输出验证 | [读取/声明](https://github.com/openutau/OpenUtau/blob/5c3c83bbeced96718e85e4a96d127de3287cd14b/OpenUtau.Core/Ustx/UMixFx.cs#L19) |
| tracks[].mix_fx.ReverbPreset | 还选Width/Wet/Dry内部值，不只是显示；本机整体MixFx读取路径存在；上游与本机独立开关/live刷新有差异，未做非默认输出验证 | [读取/声明](https://github.com/openutau/OpenUtau/blob/5c3c83bbeced96718e85e4a96d127de3287cd14b/OpenUtau.Core/Ustx/UMixFx.cs#L20) |
| Preferences.MixFxApplyOnExportMixdown | 字段声明默认true；已核查正常mixdown导出固定applyMixFx=true，无此偏好读取；首批按声明推定导出开关的说法已修正；不把该字段列为当前有效出口开关 | [读取/声明](https://github.com/openutau/OpenUtau/blob/5c3c83bbeced96718e85e4a96d127de3287cd14b/OpenUtau.Core/Util/Preferences.cs#L317) |

## 导出、播放与声像的实际区别

| 入口 | 实际顺序与选择 | 本机边界 |
|---|---|---|
| UI/桥接混音导出 | voice与已加载wave → 每轨fader（Volume/Pan/Muted）→ MixFx → WaveMix → ExportAdapter → WAV16/44100/stereo | 本机IL读路径已核查；整体FX配置决定旁路，没有新输出测试 |
| UI/桥接分轨导出 | voice请求 → dry slot source → ExportAdapter → ToMono(1,0) → WAV16/44100/mono | 跳过Muted；无track Volume/Pan/MixFx、无导入伴奏；renderer DYN仍在 |
| UI播放 | 范围/指定track → mixdown → PlaybackMix节拍overlay → MasterAdapter → audio output | 本机FX为WrapWith静态组装；上游WrapLive不存在；live设备/OS音量未知 |

入口依据：[PARAM:C46.14](https://github.com/openutau/OpenUtau/blob/5c3c83bbeced96718e85e4a96d127de3287cd14b/OpenUtau.Core/PlaybackManager.cs#L558)、[PARAM:C46.15](https://github.com/openutau/OpenUtau/blob/5c3c83bbeced96718e85e4a96d127de3287cd14b/OpenUtau.Core/PlaybackManager.cs#L590)、[PARAM:C46.20](https://github.com/openutau/OpenUtau/blob/5c3c83bbeced96718e85e4a96d127de3287cd14b/OpenUtau.Core/PlaybackManager.cs#L379)。主UI音频导出文件过滤为WAV，所核查路径没有可选MP3/FLAC、采样率或位深；输入支持多种格式不等于可以按同样格式导出。

声像公式：angle=(clip(pan,-100,100)+100)/200×π/2；L=cos(angle)，R=sin(angle)。mono在slot复制到两侧后，中心每侧1/√2（约-3.0103dB），L²+R²=1。对已有stereo输入，fader是对原左右各乘此系数，不做声像交叉混合；不能宣称任意stereo总功率都恒定。见[PARAM:C42.07](https://github.com/openutau/OpenUtau/blob/5c3c83bbeced96718e85e4a96d127de3287cd14b/OpenUtau.Core/Util/MusicMath.cs#L247)及本机LOCAL:07。

轨道Volume低区采用分段规则：db<=-24静音；-24<db<-16先变为2db+16；否则直接db，再10^(effective_db/20)。动态fader每个交错sample最多变化0.0005，初始SetScaleToTarget直接设置。它与DYN的0.1dB存储及最低值特殊静音是不同入口。见[PARAM:C42.06](https://github.com/openutau/OpenUtau/blob/5c3c83bbeced96718e85e4a96d127de3287cd14b/OpenUtau.Core/PlaybackManager.cs#L542)、[PARAM:C42.08](https://github.com/openutau/OpenUtau/blob/5c3c83bbeced96718e85e4a96d127de3287cd14b/OpenUtau.Core/SignalChain/Fader.cs#L44)。

solo/mute主要由App的JudgeMuted写派生Muted：Solo优先，随后Mute或任一其它Solo使Muted=true。桥接Load不实例化该UI；UTrack.AfterLoad只有!Solo且Mute时置Muted，因此不能把UI多轨solo效果自动推广到桥接加载上下文。已核查两种导出都读取派生Muted，不是单独每次重新求Solo。见[PARAM:C42.09](https://github.com/openutau/OpenUtau/blob/5c3c83bbeced96718e85e4a96d127de3287cd14b/OpenUtau/ViewModels/TrackHeaderViewModel.cs#L214)。

本轮修正首批C46.01：MixFxApplyOnExportMixdown虽有默认true声明，已读取的上游和本机正常mixdown都固定传applyMixFx=true，没有读该偏好。它不能列为当前有效的导出FX开关；每轨Enabled/null仍决定整体旁路。无既有音频/实验输入变动。

导入wave的skip/trim/fadein/fadeout存储为ticks，经项目timeAxis换ms再截断到sample数；不是存储ms。截取后的PCM是副本，线性淡入/淡出可重叠相乘。GetStereoSamples/GetSamples将非44100输入做Wdl重采样，ExportAdapter本身不是任意选采样率的导出控件。见[PARAM:C42.12](https://github.com/openutau/OpenUtau/blob/5c3c83bbeced96718e85e4a96d127de3287cd14b/OpenUtau.Core/Ustx/UPart.cs#L537)、[PARAM:C42.13](https://github.com/openutau/OpenUtau/blob/5c3c83bbeced96718e85e4a96d127de3287cd14b/OpenUtau.Core/Ustx/UPart.cs#L549)、[PARAM:C46.18](https://github.com/openutau/OpenUtau/blob/5c3c83bbeced96718e85e4a96d127de3287cd14b/OpenUtau.Core/Format/Wave.cs#L65)。

内部float transport与最终编码分开：ExportAdapter为44100/2 float，正常WAV最终CreateWaveFile16；分轨ToMono选左侧，不是两侧平均。上游WriteMono16Wav的cache编码又是独立路径。MasterAdapter的3ms播放边沿淡变/等待策略不进入ExportAdapter；当前播放调用没有传有限endMs，终止由playback boundary管理，不能声称导出也自动加同一淡出。

项目自身桥接的render --mixdown选择混音入口，否则分轨（[桥接源码](../../../bridge/OuBridge/Program.cs)）；[固定增益mix](../../../src/agent2utau/audio/mix.py)显式线性增益、拒绝peak>=1并输出PCM24。封存fresh实验还需按各自实际输入/PCM绑定追踪，不能用UI WAV16替代原实验编码，也未重跑歌曲。

Windows NAudio实现中默认设备模式为WASAPI shared，手动设备模式为WaveOutEvent；50ms延迟/两buffers属于代码常量。NAudio实现存在不证明本次live选它；设备格式、驱动/OS重采样、增强、音量及外部播放器增益均unknown，未开启监听。

## 图节点逐类型与端口fallback

完整数据见[节点登记](graph-node-review.json)。31种固定类型与源码常量集合逐一相等，每种类型都有具体参数/端口行；该检查不穷尽未来扩展。连接优先，未连接输入依次取同名文本参数的Invariant float解析值、端口默认。输出节点未连接时不会进入输出plan，填写value不等于驱动。数值端口无全局NaN/Infinity拒绝，不从编辑Number类的通用min/max推断运行钳位。

| type | 角色/输出口 | 输入口fallback | 显式参数（新节点默认） |
|---|---|---|---|
| [constant](https://github.com/openutau/OpenUtau/blob/5c3c83bbeced96718e85e4a96d127de3287cd14b/OpenUtau.Core/ExpressionGraph/GraphNodeTypes.cs#L136) | Input/out | 无 | value=0 |
| [curve_input](https://github.com/openutau/OpenUtau/blob/5c3c83bbeced96718e85e4a96d127de3287cd14b/OpenUtau.Core/ExpressionGraph/GraphNodeTypes.cs#L138) | Input/out | 无 | abbr=unset |
| [curve_output](https://github.com/openutau/OpenUtau/blob/5c3c83bbeced96718e85e4a96d127de3287cd14b/OpenUtau.Core/ExpressionGraph/GraphNodeTypes.cs#L140) | CurveOutput/无输出口 | value=0 | abbr=unset |
| [masked_curve_input](https://github.com/openutau/OpenUtau/blob/5c3c83bbeced96718e85e4a96d127de3287cd14b/OpenUtau.Core/ExpressionGraph/GraphNodeTypes.cs#L143) | Input/value,mask | fallback=0 | abbr=unset |
| [phoneme_input](https://github.com/openutau/OpenUtau/blob/5c3c83bbeced96718e85e4a96d127de3287cd14b/OpenUtau.Core/ExpressionGraph/GraphNodeTypes.cs#L159) | Input/out | 无 | abbr=unset; interpolation=step |
| [phoneme_output](https://github.com/openutau/OpenUtau/blob/5c3c83bbeced96718e85e4a96d127de3287cd14b/OpenUtau.Core/ExpressionGraph/GraphNodeTypes.cs#L177) | PhonemeOutput/无输出口 | value=0 | abbr=unset |
| [pitch_input](https://github.com/openutau/OpenUtau/blob/5c3c83bbeced96718e85e4a96d127de3287cd14b/OpenUtau.Core/ExpressionGraph/GraphNodeTypes.cs#L179) | Input/out | 无 | source=pitch_bend |
| [pitch_output](https://github.com/openutau/OpenUtau/blob/5c3c83bbeced96718e85e4a96d127de3287cd14b/OpenUtau.Core/ExpressionGraph/GraphNodeTypes.cs#L184) | PitchOutput/无输出口 | value=0 | 无额外参数 |
| [add](https://github.com/openutau/OpenUtau/blob/5c3c83bbeced96718e85e4a96d127de3287cd14b/OpenUtau.Core/ExpressionGraph/GraphNodeTypes.cs#L187) | Process/out | a=0; b=0 | 无额外参数 |
| [subtract](https://github.com/openutau/OpenUtau/blob/5c3c83bbeced96718e85e4a96d127de3287cd14b/OpenUtau.Core/ExpressionGraph/GraphNodeTypes.cs#L188) | Process/out | a=0; b=0 | 无额外参数 |
| [multiply](https://github.com/openutau/OpenUtau/blob/5c3c83bbeced96718e85e4a96d127de3287cd14b/OpenUtau.Core/ExpressionGraph/GraphNodeTypes.cs#L189) | Process/out | a=1; b=1 | 无额外参数 |
| [divide](https://github.com/openutau/OpenUtau/blob/5c3c83bbeced96718e85e4a96d127de3287cd14b/OpenUtau.Core/ExpressionGraph/GraphNodeTypes.cs#L190) | Process/out | a=0; b=1 | 无额外参数 |
| [min](https://github.com/openutau/OpenUtau/blob/5c3c83bbeced96718e85e4a96d127de3287cd14b/OpenUtau.Core/ExpressionGraph/GraphNodeTypes.cs#L191) | Process/out | a=0; b=0 | 无额外参数 |
| [max](https://github.com/openutau/OpenUtau/blob/5c3c83bbeced96718e85e4a96d127de3287cd14b/OpenUtau.Core/ExpressionGraph/GraphNodeTypes.cs#L192) | Process/out | a=0; b=0 | 无额外参数 |
| [mix](https://github.com/openutau/OpenUtau/blob/5c3c83bbeced96718e85e4a96d127de3287cd14b/OpenUtau.Core/ExpressionGraph/GraphNodeTypes.cs#L256) | Process/out | a=0; b=0; factor=0.5 | 无额外参数 |
| [abs](https://github.com/openutau/OpenUtau/blob/5c3c83bbeced96718e85e4a96d127de3287cd14b/OpenUtau.Core/ExpressionGraph/GraphNodeTypes.cs#L267) | Process/out | value=0 | 无额外参数 |
| [map_range](https://github.com/openutau/OpenUtau/blob/5c3c83bbeced96718e85e4a96d127de3287cd14b/OpenUtau.Core/ExpressionGraph/GraphNodeTypes.cs#L270) | Process/out | value=0 | in_min=0; in_max=1; out_min=0; out_max=1; clamp=false |
| [clamp](https://github.com/openutau/OpenUtau/blob/5c3c83bbeced96718e85e4a96d127de3287cd14b/OpenUtau.Core/ExpressionGraph/GraphNodeTypes.cs#L283) | Process/out | value=0 | min=unset; max=unset |
| [lfo](https://github.com/openutau/OpenUtau/blob/5c3c83bbeced96718e85e4a96d127de3287cd14b/OpenUtau.Core/ExpressionGraph/GraphNodeTypes.cs#L289) | Input/out | 无 | shape=sine; rate=5; unit=hz; phase=0; amplitude=1; offset=0 |
| [time](https://github.com/openutau/OpenUtau/blob/5c3c83bbeced96718e85e4a96d127de3287cd14b/OpenUtau.Core/ExpressionGraph/GraphNodeTypes.cs#L314) | Input/out | 无 | unit=seconds |
| [smooth](https://github.com/openutau/OpenUtau/blob/5c3c83bbeced96718e85e4a96d127de3287cd14b/OpenUtau.Core/ExpressionGraph/GraphNodeTypes.cs#L222) | Process/out | value=0 | attack_ms=20; release_ms=20 |
| [random_range](https://github.com/openutau/OpenUtau/blob/5c3c83bbeced96718e85e4a96d127de3287cd14b/OpenUtau.Core/ExpressionGraph/GraphNodeTypes.cs#L237) | Input/out | min=0; max=1 | rate=5; seed=0; unit=hz |
| [slew](https://github.com/openutau/OpenUtau/blob/5c3c83bbeced96718e85e4a96d127de3287cd14b/OpenUtau.Core/ExpressionGraph/GraphNodeTypes.cs#L236) | Process/out | value=0; speed=100 | speed=100; easing=linear |
| [compare](https://github.com/openutau/OpenUtau/blob/5c3c83bbeced96718e85e4a96d127de3287cd14b/OpenUtau.Core/ExpressionGraph/GraphNodeTypes.cs#L197) | Process/out | a=0; b=0 | operator=less |
| [and](https://github.com/openutau/OpenUtau/blob/5c3c83bbeced96718e85e4a96d127de3287cd14b/OpenUtau.Core/ExpressionGraph/GraphNodeTypes.cs#L193) | Process/out | a=0; b=0 | 无额外参数 |
| [or](https://github.com/openutau/OpenUtau/blob/5c3c83bbeced96718e85e4a96d127de3287cd14b/OpenUtau.Core/ExpressionGraph/GraphNodeTypes.cs#L194) | Process/out | a=0; b=0 | 无额外参数 |
| [not](https://github.com/openutau/OpenUtau/blob/5c3c83bbeced96718e85e4a96d127de3287cd14b/OpenUtau.Core/ExpressionGraph/GraphNodeTypes.cs#L195) | Process/out | value=0 | 无额外参数 |
| [if_else](https://github.com/openutau/OpenUtau/blob/5c3c83bbeced96718e85e4a96d127de3287cd14b/OpenUtau.Core/ExpressionGraph/GraphNodeTypes.cs#L214) | Process/out | condition=0; then=1; else=0 | 无额外参数 |
| [note_position](https://github.com/openutau/OpenUtau/blob/5c3c83bbeced96718e85e4a96d127de3287cd14b/OpenUtau.Core/ExpressionGraph/GraphNodeTypes.cs#L321) | Input/out | 无 | 无额外参数 |
| [phrase_notes](https://github.com/openutau/OpenUtau/blob/5c3c83bbeced96718e85e4a96d127de3287cd14b/OpenUtau.Core/ExpressionGraph/GraphNodeTypes.cs#L328) | Input/index,count | 无 | 无额外参数 |
| [note_envelope](https://github.com/openutau/OpenUtau/blob/5c3c83bbeced96718e85e4a96d127de3287cd14b/OpenUtau.Core/ExpressionGraph/GraphNodeTypes.cs#L338) | Input/out | 无 | attack_ms=0; release_ms=0 |

curve/pitch按phrase 5tick网格计算；phone outputs整part按各phone自身位置，禁止依赖pitch_input。curve和phone输出最后clip到目标descriptor范围；pitch_output覆盖绝对cents目标，该读取点没有同一descriptor钳位。pitch_input的notes/pitch_bend是绝对cents，vibrato/MOD+是相对贡献；将这些相加需显式保留音符基底。

phoneme_input在phone输出网格直接按index读，在curve/pitch网格按step/linear/单调cubic插值；端点保持、同tick末音素获胜。Smooth/Slew状态限本次grid；LFO/随机桶按项目绝对时钟避免句拆分重置。这些是数学驱动规则，不是新的声学表现维度或自然度结论。

本机Core不存在ExpressionGraph命名空间、UMaskedCurve、项目图库/default字段及track图属性。RPIT/PITO/图节点仅登记上游机制，本机当前不采用，不通过读写USTX猜成已生效。

## 本机静态支持矩阵

方法token/IL偏移、DLL SHA/MVID及版本见[JSON](local-capability-review.json)。离线PEReader只读元数据/方法体，没有加载目标程序集、运行初始化、加载模型或打开音频。完整类型/成员缺失结论限绑定Core/App；方法IL存在也不保证分支当前启用。

| 能力 | 核查状态 | 结论 |
|---|---|---|
| LOCAL:01 expression graph / masked curves | absent_in_bound_core | Core完整TypeDefinition无graph命名空间及UMaskedCurve；本机当前没有所绑定上游图驱动类型 |
| LOCAL:02 project/track graph references | absent_in_bound_core | 项目图库/default及track图属性缺失；不能借现有USTX默认加载宣称graph生效 |
| LOCAL:03 PitchPointShape.sp | enum_and_helper_branch_present | sp=4存在；通用InterpolateShape分支与io同SinEasingInOut；非默认整曲执行未测，不宣称新的样条算法 |
| LOCAL:04 MixFx independent module switches | absent_in_bound_core | Enabled整体存在；EqEnabled/CompEnabled/ReverbEnabled缺失，不可照搬新上游独立开关 |
| LOCAL:05 MixFx Enabled / parameter read path | IL_read_path_present | WrapWith读整体启用、EQ值及压缩/混响preset与值后Configure；null/disabled旁路；不证明副作用/自然度 |
| LOCAL:06 MixFx WrapLive | absent_in_bound_core | 本机只有WrapWith静态组装；上游播放跟随MixFx live的路径不存在 |
| LOCAL:07 track fader / pan law | IL_read_path_present | RenderMixdown读Muted/Volume/Pan→Fader→WrapWith→WaveMix；PanToChannelVolumes公式与固定上游一致 |
| LOCAL:08 volume nonlinear low range / smoothing | IL_read_path_present | db<=-24为0；db<-16先2db+16；Fader每交错sample追target最大0.0005；初始SetScaleToTarget |
| LOCAL:09 UI/bridge mixdown WAV path | IL_read_path_present | 正常mixdown调用wait=true/applyMixFx=true；ExportAdapter 44100/2 float transport，CreateWaveFile16最终编码 |
| LOCAL:10 MixFxApplyOnExportMixdown preference | declared_but_not_read_in_export_path | 偏好字段存在，所核查mixdown闭包不读，直接固定applyMixFx=true；不标可用效果器导出开关 |
| LOCAL:11 track export dry mono path | IL_read_path_present | RenderTracks无fader/FX/wave输入；RenderToFiles跳过Muted并ToMono(1,0)→CreateWaveFile16；DYN属renderer仍保留 |
| LOCAL:12 UI solo/mute aggregation | IL_read_path_present_UI_scope | App JudgeMuted按Solo→false、Mute→true、其它Solo→true，否则false；桥接无UI实例不能假定加载同样聚合 |
| LOCAL:13 MasterAdapter playback edge/readiness | IL_read_path_present | 本机HoldWhenUnready/3ms边沿fade存在；仅播放adapter，export不用；真实设备未播放 |
| LOCAL:14 Windows NAudio device branch | IL_read_path_present_device_unknown | App.Init含WASAPI Shared(0)/50ms和WaveOut/50ms/两buffers；live选用后端/设备/OS音量unknown |
| LOCAL:15 import sample rate conversion | IL_read_path_present | GetStereoSamples/GetSamples含44100目标Wdl重采样；未进行新的文件解码 |
| LOCAL:16 DiffSingerVarianceLocalPitchPatch | member_and_IL_read_present_execution_unknown | 偏好成员及选中读取者存在；不等于当前启用、所有模型兼容或旧实验使用该路径 |
| LOCAL:17 DiffSingerMergeNearbyPhrases | member_and_IL_read_present_execution_unknown | 偏好成员及选中读取者存在；不等于当前启用、所有模型兼容或旧实验使用该路径 |
| LOCAL:18 pitch sampling new branch | member_and_IL_present_execution_unknown | AddPitchSamplingInputs/ComputePitchSpeedup成员存在；低于1步请求和非默认模型响应本轮未执行 |
| LOCAL:19 wave trim/fade ticks | IL_read_path_present | GetTrimmedSamples读skip/trim/fadein/fadeout并timeAxis换ms；PCM拷贝及逐帧增益路径存在，未解码新文件 |
| LOCAL:20 playback range/loop/metronome | selected_IL_read_paths_present | PlayOrPause/Render及嵌套闭包含范围/loop、PlaybackMix overlay、节拍音量/频率读取；实际会话未知 |
| LOCAL:21 UI WAV export command route | IL_call_paths_present | App主窗口音频导出命令分别调用mixdown与分轨；未打开导出对话框或写音频 |
| LOCAL:22 cache mono16 writer | IL_path_present_not_all_renderer_routes | WriteMono16Wav成员及44100/16/1 WaveFormat构造路径存在；仅此helper，不代表fresh诊断编码 |
| LOCAL:23 SkipRenderingMutedTracks | IL_read_path_present | PrepareRequests筛选闭包读取该偏好；影响是否发起voice请求，输出Muted门仍另存在 |

首批184个ID保持；已核查支持列和说明可纠正，不改变其身份。分类仍为当前路线/其它引擎/仅上游或版本差异/编辑元数据四栏，scope行数不等于有效艺术旋钮数。成员存在、已选IL路径、非默认执行和听觉效果是独立层级；当前未把任意新能力或未听输出记为通过。


## 编辑/预设与纯UI的有限审查

冻结SerializablePreferences的103个public字段逐项分类，WindowSize/EditTool另8个序列化属性见[偏好JSON](editor-preferences-review.json)及[CSV](editor-preferences-review.csv)。保留声明默认、绑定Core成员存在/缺失、已读源码引用和具体控制链接。引用搜索只覆盖这次显式冻结源码；一个字段声明/引用存在不等于分支执行，也不证明所有App消费者已穷尽。未读取本机live偏好。

| 编辑入口 | 实际写入与限制 |
|---|---|
| 滑音预设/重置 | CreateNote/Reset生成(start,0)、(start+length,0)两点；start/length为ms。自定义PitchPoints库存在，但这两个reader只读start/length。 |
| 颤音默认/自动启用 | period/depth/in/out/shift/drift/vol_link初始化读默认，UVibrato新对象length仍0；toggle/resize/reset才按默认length或auto门控写。481阈值是ticks。 |
| 网格新建/拖动/批量量化 | 写position/duration；不同操作floor、floor+1与Math.Round不等价。所读AddNote位置即使关闭IsSnapOn仍floor；不能概括为关闭就全自由。 |
| DefaultSnapCurve | 所读reader控制选择起点；Update只读IsSnapOn。没有证据说该偏好让所有曲线点写入吸附。 |
| 选择锁/编辑工具 | 限制对象/选择手势；下游写已有note/curve/phone值，不新增DSP通道。完整手势及未读consumer保留unknown。 |
| FX命名预设 | UI BuildUMixFx/Changed/Apply写track.MixFx，Revert还原；具体值与名字分开。本机缺新三开关/WrapLive，不能声称上游live DSP实际支持。 |

LyricLivePreview/LyricApplySelectionOnly在所读源码中只有声明，保持未确认；RealTimePitchMode确认迁移/保存，不凭开关名称宣称自动写PITD。纯显示/会话项按角色单列，资源/后端/分句/播放项不会混成“纯UI无声学影响”。

## 第三方扩展的范围边界

本轮只登记冻结上游ExeResampler/ResamplerManifest、ENUNU styles/style_format契约和hifisampler的选定e/A/P读取点。当前声库仍是已绑定DiffSinger/Yousa，未选择/执行其它引擎或外部exe。

- resampler manifest的expressions默认空、expressionFilter=false；键转小写分组取首。SupportsFlag全放行只表示允许传入，不能证明外部程序解析或旗标有效。外部集合须绑定具体exe SHA/同名yaml及reader，不穷尽未来插件。
- ENUNU键名/范围来自所选配置；styles含name/type/min/max/default_value/flag，style_format含format/index。parser仅接所读字符串值，未绑定声库不造默认自定义键。
- hifisampler本身SupportsFlag返回true；本轮额外确认e存在性、A默认0/clip±100的pitch梯度增益、P默认86/0旁路auto gain。其它路径不因“支持”返回值成为确认；当前DiffSinger不采用这些参数。

## C收口与试听衔接

C现在以reviewed_with_explicit_gaps收口：48入口均有具体项/状态，固定节点、偏好与选定扩展接口的审查范围明确；all_controls_enumerated与all_local_paths_confirmed仍false。未验证的本机非默认执行、开放插件、设备呈现及声音效果逐项保留，不通过升级安装或新合成消除unknown。下一步D确认观测协议，再在E核对已有用户标签/覆盖；新的因果试听按后续表2冻结设计推进。没有人工试听就不确认可感知差别、改善或自然度。


DYN是输出振幅；VOIC/BREC/TENC是预测上的模型条件增量；SHFC影响条件音区与预测，GENC输入不是实测共振峰。人工控制进入时间仍是函数/驱动的设计量，没有新增一个“自然度”或“口型”独立旋钮。字段和公式不支持统一剂量/听觉方向。

## 分组展开及范围

| 旧组 | 条目数 | 导航名称 |
|---|---:|---|
| C01 | 2 | 音符中心 tone、tuning、全曲移调 |
| C02 | 9 | 音符 pitch 点X/Y、插值形状、snap_first |
| C03 | 1 | PITD |
| C04 | 4 | vibrato length |
| C05 | 2 | vibrato period |
| C06 | 2 | vibrato depth |
| C07 | 4 | vibrato in/out |
| C08 | 4 | vibrato shift/drift |
| C09 | 2 | vibrato vol_link |
| C10 | 1 | DYN |
| C11 | 1 | VOIC |
| C12 | 1 | BREC |
| C13 | 1 | TENC |
| C14 | 1 | SHFC |
| C15 | 1 | GENC |
| C16 | 1 | VELC |
| C17 | 1 | ENE |
| C18 | 2 | falsetto embedding / prediction |
| C19 | 1 | CLR、speaker/subbank |
| C20 | 5 | cl01…clNN声线曲线 |
| C21 | 2 | PEXP、生成/重生成pitch、retake |
| C22 | 9 | 音符/part position、duration、tempos |
| C23 | 6 | 歌词、语言、多音字、phonetic hint、phoneme override |
| C24 | 6 | 音素offset/时长、延音+、AP/SP、分组/分句 |
| C25 | 1 | VEL声母速度 |
| C26 | 3 | VOL/ATK/DEC |
| C27 | 4 | preutterDelta、overlapDelta、attackTimeDelta、releaseTimeDelta |
| C28 | 7 | oto Offset/Consonant/Cutoff/Preutter/Overlap、alias、frq |
| C29 | 2 | ALT、SHFT |
| C30 | 4 | ENG、renderer、resampler、wavtool |
| C31 | 5 | GEN(g)、BRE(B)、LPF(H)、NORM(P) |
| C32 | 2 | MOD、MOD+ |
| C33 | 1 | DIR |
| C34 | 2 | CLRY、XSY |
| C35 | 4 | GRWC、Hifisampler粗糙效果 |
| C36 | 12 | 自定义flags与表达声明、默认值、范围、类型、track覆盖 |
| C37 | 3 | VOICEVOX VOLC、SMOC、REPM、style |
| C38 | 7 | ENUNU styles/custom expressions、Vogen/Worldline声学控制 |
| C39 | 22 | 声库、speaker embeddings、duration/pitch/variance/acoustic模型、vocoder、字典/subbank配置 |
| C40 | 5 | DiffSinger steps/depth、pitch/variance步骤、speedup、随机输入/seed |
| C41 | 5 | 完整短语上下文、AP/SP、合并/拆分、padding、渲染缓存 |
| C42 | 13 | track volume、pan、mute/solo、导入伴奏位置/音量、多轨 |
| C43 | 8 | MixFx EQ总/模块开关、lowDb/midFreq/midDb/highDb、preset |
| C44 | 8 | MixFx压缩 threshold/ratio/makeup、preset、开关 |
| C45 | 9 | MixFx混响 size/damp/wet/pre-delay、preset、开关 |
| C46 | 29 | 导出格式/采样率/位深、声道、重采样、播放/监听增益 |
| C47 | 116 | 表达图、RPIT/PITO、曲线插值/函数时间形状/量化 |
| C48 | 11 | key/拍号、snap/grid、预设、显示、轨名/颜色、UI偏好 |

按当前路线、其它引擎、仅上游/本机未知与编辑元数据分别计数；当前路线包含禁用能力、资源契约和推理设置，**不能把该类行数当成有效艺术旋钮数**。同一分组可能含多种状态，须读逐项current_support/condition。

## 保留的C确认缺口

| 范围 | 缺口 | 需要什么 |
|---|---|---|
| C47 | 固定31节点的类型/参数/输入fallback已枚举；本机graph/masked类型缺失，不能执行 | 若以后采用须用户选择支持版本并另验证；本轮不升级安装或合成 |
| C46/C42 | 主UI两类WAV导出/播放及本机IL已分开；真实设备、OS增益/重采样及非默认输出未验证 | 按实际呈现链显式绑定设备/输出；本轮不播放或导出歌曲 |
| C35/C38/C36 | 冻结resampler manifest/ENUNU styles接口及hifisampler e/A/P reader已登记；未选第三方配置/其它旗标仍开放 | 未来采用才绑定具体实现/配置及reader；当前不穷尽插件，不当作当前DiffSinger支持 |
| C48 | 全部冻结偏好字段及预设/网格主要写入已审；未穷尽全App消费者/手势，LyricLivePreview等仅声明 | 具体unknown保留，不从名字补造作用；已有输入驱动关联足以进入D，无需执行歌曲填表 |
| C01/C02/C04–09/C19–24/C39–41 | 本机成员和部分IL已补，不等于所有非默认执行/模型路径通过 | 已有native记录仍限原条件；进一步静态核查或授权最小读取，不新增合成填表 |
| C43–45 | 本机MixFx存在但独立三模块开关/WrapLive不存在；每内部算法非默认输出尚未验证 | 本机和冻结上游分栏；不能照搬上游新UI功能或宣称听觉改善 |

原48类清单及表1/表2基线不改；不创建参数搜索/自动修复器，不改Skill/歌曲/音频。当前[计划](../../../plan.md)的下一步为D，D/E/F尚未执行。文件与保护绑定见[审计](table1-execution-audit.json)。
