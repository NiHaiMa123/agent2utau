"""Explicit review of graph nodes and output paths at the frozen commit.

These are source facts, not new perceptual recipes. The offline DLL review is
kept separate; no node is promoted to installed support from upstream alone.
"""
NODES = 'OpenUtau.Core/ExpressionGraph/GraphNodeTypes.cs'
PROGRAM = 'OpenUtau.Core/ExpressionGraph/ExpressionGraphProgram.cs'
GRAPH = 'OpenUtau.Core/ExpressionGraph/UExpressionGraph.cs'
PLAY = 'OpenUtau.Core/PlaybackManager.cs'
ENGINE = 'OpenUtau.Core/Render/RenderEngine.cs'
MATH = 'OpenUtau.Core/Util/MusicMath.cs'
FADER = 'OpenUtau.Core/SignalChain/Fader.cs'
EXPORT = 'OpenUtau.Core/SignalChain/ExportAdapter.cs'
MASTER = 'OpenUtau.Core/SignalChain/MasterAdapter.cs'
PREFS = 'OpenUtau.Core/Util/Preferences.cs'
WAVE = 'OpenUtau.Core/Format/Wave.cs'

# symbol, serialized type, role, ports with runtime defaults, outputs,
# editor parameters (name, new-node default, unit/range, meaning), operation.
# None = not set by the new-node editor, not a numeric zero.
GRAPH_TYPES = [
    ('Constant', 'constant', 'Input', [], ['out'],
     [('value','0','目标表达单位','每点同一常数')], 'Fill(value，缺失/解析失败为0)'),
    ('CurveInput','curve_input','Input',[],['out'],
     [('abbr',None,'Curve表达缩写','读原绘制曲线，缺曲线用descriptor默认；无缩写/无默认为0')], 'GraphContext.SampleCurve'),
    ('CurveOutput','curve_output','CurveOutput',[('value','0')],[],
     [('abbr',None,'支持的Curve缩写，排除PITD','驱动对应curve，最终clip到descriptor范围；DYN随后换振幅')], '复制value；未连接的output不进入PlanFor输出'),
    ('MaskedCurveInput','masked_curve_input','Input',[('fallback','0')],['value','mask'],
     [('abbr',None,'MaskedCurve缩写','读取已定义值及mask；undefined使用fallback，mask=0')], '有定义返回(value,1)，未定义返回(fallback,0)'),
    ('PhonemeInput','phoneme_input','Input',[],['out'],
     [('abbr',None,'Numerical表达缩写','读音素锚点；缺表达为0'),
      ('interpolation','step','step/linear/cubic','curve/pitch网格上按锚点插值；音素输出网格直接At(index)')], '锚点外保持端值；相同tick末音素获胜；cubic用单调斜率'),
    ('PhonemeOutput','phoneme_output','PhonemeOutput',[('value','0')],[],
     [('abbr',None,'可驱动Numerical表达缩写','排除ALT/SHFT/VEL等先于graph的时钟表达；clip descriptor范围')], '整part按每phone自身tick输出；per-phone output不能依赖pitch_input'),
    ('PitchInput','pitch_input','Input',[],['out'],
     [('source','pitch_bend','pitch_bend/vibrato/mod_plus/notes','bend及notes为绝对cents；vibrato/MOD+为相对贡献')], 'PhrasePitch.Sample：5tick格点、格间线性、格外端值；无Pitch context为0'),
    ('PitchOutput','pitch_output','PitchOutput',[('value','0')],[],[],
     'value作为绝对MIDI*100 cents覆盖完整目标pitches；此读取点无descriptor钳位；未连接output不驱动'),
    ('Add','add','Process',[('a','0'),('b','0')],['out'],[], 'a+b'),
    ('Subtract','subtract','Process',[('a','0'),('b','0')],['out'],[], 'a-b'),
    ('Multiply','multiply','Process',[('a','1'),('b','1')],['out'],[], 'a*b'),
    ('Divide','divide','Process',[('a','0'),('b','1')],['out'],[], 'b==0时0，否则a/b'),
    ('Min','min','Process',[('a','0'),('b','0')],['out'],[], 'min(a,b)'),
    ('Max','max','Process',[('a','0'),('b','0')],['out'],[], 'max(a,b)'),
    ('Mix','mix','Process',[('a','0'),('b','0'),('factor','0.5')],['out'],[], 'a+(b-a)*clip(factor,0,1)'),
    ('Abs','abs','Process',[('value','0')],['out'],[], 'abs(value)'),
    ('MapRange','map_range','Process',[('value','0')],['out'],
     [('in_min','0','输入单位/未声明统一合法范围','映射输入下端'),('in_max','1','输入单位/未声明统一合法范围','映射输入上端'),
      ('out_min','0','输出单位/未声明统一合法范围','输出起点'),('out_max','1','输出单位/未声明统一合法范围','输出终点'),
      ('clamp','false','bool：true/True/1为真，其余假','启用后clip到排序后的out端点')],
     'in_max==in_min时out_min，否则out_min+(x-in_min)*(out_max-out_min)/(in_max-in_min)'),
    ('Clamp','clamp','Process',[('value','0')],['out'],
     [('min',None,'目标单位；缺失/解析失败=-Infinity','下限'),('max',None,'目标单位；缺失/解析失败=+Infinity','上限')], 'max(min,min(max,x))；不自动排序min/max'),
    ('Lfo','lfo','Input',[],['out'],
     [('shape','sine','sine/triangle/square/saw','未知shape回sin'),('rate','5','Hz或cycles/beat；未统一裁剪','频率'),
      ('unit','hz','hz/beat；仅beat启用拍单位','时间尺度'),('phase','0','cycles，1=整周期','周期相位偏移'),
      ('amplitude','1','目标单位，非峰峰','波幅'),('offset','0','目标单位','直流偏移')],
     '从项目绝对秒/beat累计cycles；输出offset+amplitude*wave，不因句拆分重置相位'),
    ('Time','time','Input',[],['out'],[('unit','seconds','seconds/beat','项目绝对秒或absTick/resolution')], '输出绝对时间，不是part从0起计'),
    ('Smooth','smooth','Process',[('value','0')],['out'],
     [('attack_ms','20','ms；tau<=0时瞬时','input>前output采用attack'),('release_ms','20','ms；tau<=0时瞬时','其它方向采用release')],
     '首output=input[0]；amount=1-exp(-max(0,dt_ms)/tau)，y=prev+(input-prev)*amount；状态限本次grid'),
    ('RandomRange','random_range','Input',[('min','0'),('max','1')],['out'],
     [('rate','5','Hz或buckets/beat；非有限/负值设0','时间桶更新频率'),('seed','0','Invariant整数；解析失败0','固定hash种子，非声学推理seed'),
      ('unit','hz','hz/beat','项目绝对秒或beat')], 'bucket=floor(absTime*rate)固定hash；排序端点lo/hi，输出lo+(hi-lo)*random[0,1)'),
    ('Slew','slew','Process',[('value','0'),('speed','100')],['out'],
     [('speed','100','目标单位/s；编辑Slider[0,1000] step1；运行非有限/负值设0','未接speed端口时文本参数fallback'),
      ('easing','linear','linear/cubic','线性或单调Hermite，cubic按1.5缩放时长')],
     '首值直接input；target变时从前output过渡；speed=0保持；状态限grid，cubic保留向新target运动的切线'),
    ('Compare','compare','Process',[('a','0'),('b','0')],['out'],
     [('operator','less','less/less_equal/greater/greater_equal/equal/not_equal','未知值回less；float直接比较')], '比较成立1否则0'),
    ('And','and','Process',[('a','0'),('b','0')],['out'],[], 'a!=0且b!=0为1否则0'),
    ('Or','or','Process',[('a','0'),('b','0')],['out'],[], 'a!=0或b!=0为1否则0'),
    ('Not','not','Process',[('value','0')],['out'],[], 'value==0为1否则0'),
    ('IfElse','if_else','Process',[('condition','0'),('then','1'),('else','0')],['out'],[], 'condition!=0选then否则else'),
    ('NotePosition','note_position','Input',[],['out'],[], '(tick-note.Position)/note.Duration；无覆盖note为0；note结束tick不覆盖'),
    ('PhraseNotes','phrase_notes','Input',[],['index','count'],[], 'phrase中note零起序号/总数；音素网格按owner；无context/匹配为(-1,0)'),
    ('NoteEnvelope','note_envelope','Input',[],['out'],
     [('attack_ms','0','ms；<=0不施加入口斜坡','note开始后线性入口'),('release_ms','0','ms；<=0不施加出口斜坡','note结束前线性退出')],
     'min(1,elapsed_ms/attack,remaining_ms/release) clip[0,1]；无覆盖note为0'),
]

def extra_controls():
    out = []
    def add(group, field, unit, default, limits, transform, source, anchor,
            *, graph=False, scope='current_route', caveat='读取路径/公式核查，未做非默认输出或听觉验证'):
        out.append(dict(group_id=f'C{group:02}', field=field, storage_unit=unit,
            default_or_baseline=default, declared_or_code_limits=limits, transform=transform,
            source_path=source, source_anchor=anchor, scope='upstream_local_unknown' if graph else scope,
            current_support='installed_graph_and_masked_types_absent_offline_PE_checked' if graph else 'frozen_upstream_path_checked_installed_specific_branch_unconfirmed',
            stage='expression_driver_before_renderer' if graph else 'mix/playback/export',
            condition='冻结上游graph有效且输出已连接；本机当前不能用此graph路径' if graph else '依具体入口，UI调用与桥接调用分开；不加载live偏好',
            sampling_interpolation_clip='curve/pitch为phrase 5tick grid；phoneme为自身tick；文本Invariant float，驱动范围按目标' if graph else '44100Hz双通道transport；编码/窗口/增益依入口',
            recalculate='重建graph驱动的音素/目标/模型预测和后续依赖；本机不采用' if graph else '重建相关组装/混音/导出；设备设置只影响监听；不新增合成',
            limitation=caveat, abbreviation='', published_descriptor_requested=False,
            local_code_path_status='offline_capability_review_separate_from_frozen_source',
            dose_or_auditory_direction_validated=False))
    binary = {'Add','Subtract','Multiply','Divide','Min','Max','And','Or'}
    for symbol, name, role, ports, outputs, params, operation in GRAPH_TYPES:
        anchor = f'Binary({symbol},' if symbol in binary else f'new GraphNodeType({symbol},'
        add(47,f'graph.nodes[type={name}].type','节点类型/角色',name,'31种已登记固定类型；非未来插件全集',
            f'role={role}; outputs={outputs}; {operation}',NODES,anchor,graph=True,
            caveat='节点类型本身不是独立音色通道；所有输出最终驱动已有pitch/表达')
        for port, fallback in ports:
            add(47,f'graph.nodes[type={name}].input[{port}]','目标/中间信号单位；speed为单位/s',fallback,
                '先接入连接；未接则同名参数float解析成功值，否则PortDefault；无普遍clamp',
                f'{port}输入参与{operation}；连接优先于本节点同名fallback',NODES,anchor,graph=True,
                caveat='output未连接时即使填写value也不会驱动；NaN/Infinity非全局拒绝')
        for key, default, unit, meaning in params:
            add(47,f'graph.nodes[type={name}].parameters[{key}]',unit,
                '新节点unset' if default is None else f'新节点{default}',
                unit + '；编辑默认和运行缺失fallback分开',f'{meaning}；所属节点：{operation}',NODES,anchor,graph=True,
                caveat='参数存为文本；Number不从GraphNodeParameter默认Minimum/Maximum推断运行合法范围')
    for field,unit,default,limits,tr,src,anchor,meta in [
        ('expression_graph.id','字符串','empty','项目库引用','用于track/default图查找',GRAPH,'public string id',True),
        ('expression_graph.name','字符串','null','显示标签','仅名称，无DSP变换',GRAPH,'public string? name',True),
        ('expression_graph.renderer','renderer slot','null','slot匹配才采用','graph renderer与track slot相同，否则GetEffectiveGraph返回null',PROGRAM,'GetEffectiveGraph',False),
        ('expression_graph.preferred_pitch_curve','pitd/pito','null→PITD','只有有效compile且PITO时使用override','决定绘制/载入rendered pitch的写入目标；本身不移调',PROGRAM,'PrefersPitchOverride',False),
        ('tracks[].expression_graph','graph ID/null','null','override优先，else项目default slot','不匹配renderer不使用；不自动换模型',PROGRAM,'string? id = track.ExpressionGraph;',False),
        ('project.default_expression_graphs[renderer_slot]','graph ID','按项目','slot键','track无override时取default；无有效图则无graph驱动',PROGRAM,'project.defaultExpressionGraphs?.TryGetValue',False),
        ('graph.nodes[].id','整数','0','唯一节点ID','重复ID compile拒绝',PROGRAM,'Two nodes have id',False),
        ('graph.nodes[].x/y','画布坐标','0','float，非音高/时间','只定位编辑画布',GRAPH,'public float x;',True),
        ('graph.links[].from/to','节点ID','0','存在节点；有向无环','缺节点/重复输入连接/cycle拒绝，改变依赖顺序',PROGRAM,'var incoming =',False),
        ('graph.links[].from_port/to_port','端口字符串/null','null','输出未命名取首口，输入必须命名匹配','按节点输出/输入口索引连接；无口则compile拒绝',PROGRAM,'int output = nodes[link.from].type.OutputIndex',False),
    ]:
        add(47,field,unit,default,limits,tr,src,anchor,graph=True)
        if meta:
            out[-1].update(scope='editing_metadata',stage='editor/serialization',
                           recalculate='纯标签/画布无；ID/引用更改另按graph依赖处理')

    for group,field,unit,default,limits,tr,src,anchor in [
        (42,'track.volume → fader.Scale','字段dB/线性振幅','Volume=0→1','db<=-24静音；-24<db<-16变换2db+16，其余db',
         'Scale=10^(effective_db/20)；不是低区直接10^(db/20)，与DYN最小值静音规则另列',PLAY,'public static float DecibelToVolume'),
        (42,'track.pan → channel gains','-100…100位置','0→左右1/sqrt(2)','运行clip[-100,100]',
         'angle=(clip(pan)+100)/200*pi/2；L=cos(angle),R=sin(angle)；mono复制后等功率，中心每声道约-3.0103dB',MATH,'public static (float, float) PanToChannelVolumes'),
        (42,'fader.Scale live smoothing','线性振幅/交错sample','初始SetScaleToTarget','每交错sample最大变化0.0005',
         '动态增益追target；初始组装直接到target；Pan直接使用，无同类渐变；不是毫秒时间常数',FADER,'scale = Math.Min(scaleTarget, scale + 0.0005f);'),
        (42,'UI mute/solo → tracks[].Muted','bool','按UI状态','Solo优先于Mute；否则Mute或任一其它Solo→Muted',
         'JudgeMuted写派生Muted，再VolumeChangeNotification写fader；桥接Load没有UI JudgeMuted，不保证solo合成相同',
         'OpenUtau/ViewModels/TrackHeaderViewModel.cs','public void JudgeMuted()'),
        (42,'Preferences.SkipRenderingMutedTracks','bool','上游false','只减少voice请求，不是混音静音唯一机制',
         'PrepareRequests先过滤Muted；mixdown对Muted Scale=0；分轨export明确跳过Muted',ENGINE,'!Preferences.Default.SkipRenderingMutedTracks'),
        (42,'wave_parts[].relative_path → FilePath/channels','显式音频资源/通道','导入文件','1或2 transport；更多声道转换需独立确认',
         'OpenFile→GetStereoSamples；mono保留1，slot复制到左右；双通道保留左右后fader作平衡缩放',WAVE,'public static float[] GetStereoSamples'),
        (42,'wave_parts[].skip/trim','ticks','0','skip/trim经timeAxis转ms再(int)(ms*sr/1000)*channels；remaining<=0空PCM',
         'skip时钟[position-skip,position]；trim时钟[End,End+trim]；GetTrimmedSamples拷贝，不原地改Samples',
         'OpenUtau.Core/Ustx/UPart.cs','public (double offsetMs, double estimatedLengthMs, int channels, float[] pcm) GetTrimmedSamples'),
        (42,'wave_parts[].fadein/fadeout','ticks','0','timeAxis将[position,position+fadein]/[End-fadeout,End]转ms再转samples',
         '第i帧gain=i/fadeFrames，线性淡入/倒序淡出，重叠相乘；不改变模型发声条件',
         'OpenUtau.Core/Ustx/UPart.cs','int fadeinFrames ='),
        (46,'UI export mixdown destination/format','文件/WAV','用户选择*.wav','该入口固定WAV；无该路径的MP3/FLAC输出/位深选择',
         'OnMenuExportMixdown→PlaybackManager.RenderMixdown；路径是输出资源不是声学控制',
         'OpenUtau/Views/MainWindow.axaml.cs','async void OnMenuExportMixdown'),
        (46,'UI export tracks destination','文件/WAV','工程Export子目录或用户选择','逐voice轨；最终Muted跳过',
         'OnMenuExportWav/To→RenderToFiles；与mixdown不同入口',
         'OpenUtau/Views/MainWindow.axaml.cs','async void OnMenuExportWav('),
        (46,'mixdown PCM encoding/sample_rate/channels','16bit signed PCM / Hz / 通道','44100/2','ExportAdapter float transport→CreateWaveFile16',
         'voice+loaded wave→每轨fader→MixFx→WaveMix→ExportAdapter→WAV16；没有此入口的可调sample rate/bit depth',PLAY,'WaveFileWriter.CreateWaveFile16(exportPath,'),
        (46,'track export PCM encoding/sample_rate/channels','16bit signed PCM / Hz / 通道','44100/1','ExportAdapter→ToMono(1,0)→CreateWaveFile16',
         'RenderTracks仅voice requests→dry slot source；无track volume/pan/MixFx/导入伴奏；保留renderer DYN，导出选左通道',PLAY,'WaveFileWriter.CreateWaveFile16(file,'),
        (46,'mixdown applyMixFx call argument','bool调用参数','固定true','程序参数可旁路；正常UI/桥接mixdown调用固定true',
         '不是Preferences.MixFxApplyOnExportMixdown读取；是否实际作用再看每轨MixFx Enabled/null',PLAY,'wait: true, applyMixFx: true'),
        (46,'ExportAdapter internal format/readiness','32bit float transport/交错sample','44100Hz/2','未ready抛错，不像播放返回静音保持',
         '不等于最终WAV float编码；Read清buffer再Mix；传输双声道最后可ToMono',EXPORT,'waveFormat = WaveFormat.CreateIeeeFloatWaveFormat(44100, 2);'),
        (46,'wave import resampling','Hz','内部44100','输入rate!=44100才Wdl重采样',
         'GetStereoSamples/GetSamples→WdlResamplingSampleProvider(44100)；不是改模型sample_rate来选择导出率',WAVE,'new WdlResamplingSampleProvider(provider, 44100)'),
        (46,'renderer cache encoding','16bit PCM / Hz / 通道','44100/mono','WriteMono16Wav clip[-1,1]，乘short.MaxValue再转short',
         '缓存编码不是UI导出选项；模型/桥接fresh数组输出路线另查，不能说所有渲染均此处编码',WAVE,'public static void WriteMono16Wav'),
        (46,'playback tick/endTick/trackNo','ticks/轨号','-1用当前位置/全项目','区间选择优先；trackNo可限轨；不是谱面时间改写',
         'PlayOrPause→RenderEngine范围→mixdown→PlaybackMix(叠加节拍)→MasterAdapter；选择影响听到的上下文',PLAY,'public void PlayOrPause('),
        (46,'PlaybackManager.LoopPlayback','bool','会话状态','loop模式HoldWhenUnready=false','范围/项目末尾重启，未ready声音可静音过而时钟不停；非loop等待',PLAY,'public bool LoopPlayback'),
        (46,'MasterAdapter.HoldWhenUnready','bool','true','not ready→零buffer；Waited增加或继续advance',
         '播放就绪策略；不用于ExportAdapter；不会给已导出WAV加同一等待空白',MASTER,'public bool HoldWhenUnready'),
        (46,'MasterAdapter edge fade/endPosition','ms/交错sample','3ms；endMs=+Infinity','FadeFrames=132；分母131',
         '播放开始/有限endPosition施加短淡变；export adapter无此fade；当前调用不传有限endMs，结束由playback boundary控制',MASTER,'private const int FadeMilliseconds = 3;'),
        (46,'Preferences.Metronome','bool','上游false','播放叠加；导出走另一链',
         'PlaybackMix叠加节拍；RenderMixdown/RenderToFiles不包含此overlay',PLAY,'playbackMix = new PlaybackMix('),
        (46,'Preferences.MetronomeVolume','%监听','上游60','clip[0,100]后sqrt','节拍gain=sqrt(clip(value/100,0,1))，非人声master gain',PLAY,'MathF.Sqrt(Math.Clamp(Preferences.Default.MetronomeVolume'),
        (46,'Preferences.MetronomeHighFrequency/LowFrequency','Hz','上游2200/1320','仅节拍音','节拍预览/播放频率；不移调歌声',PLAY,'CreateMetronomePreviewTone(Preferences.Default.MetronomeHighFrequency'),
        (46,'Preferences.UseSystemDefaultAudioDevice','bool','上游true','Windows NAudio分支','true→WASAPI shared；false→WaveOutEvent；实际live设备/OS音量未读取',
         'OpenUtau/NAudioOutput.cs','public void Init(ISampleProvider sampleProvider)'),
        (46,'Preferences.PlaybackDevice/PlaybackDeviceNumber','GUID/设备索引','上游empty/0','手动WaveOut路径，默认设备模式不使用此SelectDevice',
         '先number及ProductGuid匹配，再按guid寻找，否则0；只定位监听设备',
         'OpenUtau/NAudioOutput.cs','public void SelectDevice(Guid guid, int deviceNumber)'),
        (46,'NAudio playback latency/buffers','ms/数量','50ms；WaveOut两buffer','代码常量，不是该实现的普通音色滑块',
         'WASAPI shared或WaveOut初始化；实际硬件格式、OS重采样/增强及监听增益unknown',
         'OpenUtau/NAudioOutput.cs','const int PlaybackLatencyMs = 50;'),
    ]:
        add(group,field,unit,default,limits,tr,src,anchor)
    return out

PENDING = [
    dict(group='C47', issue='固定31节点的类型/参数/输入fallback已枚举；本机graph/masked类型缺失，不能执行',
         needed='若以后采用须用户选择支持版本并另验证；本轮不升级安装或合成'),
    dict(group='C46/C42', issue='主UI两类WAV导出/播放及本机IL已分开；真实设备、OS增益/重采样及非默认输出未验证',
         needed='按实际呈现链显式绑定设备/输出；本轮不播放或导出歌曲'),
    dict(group='C35/C38/C36', issue='冻结resampler manifest/ENUNU styles接口及hifisampler e/A/P reader已登记；未选第三方配置/其它旗标仍开放',
         needed='未来采用才绑定具体实现/配置及reader；当前不穷尽插件，不当作当前DiffSinger支持'),
    dict(group='C48', issue='全部冻结偏好字段及预设/网格主要写入已审；未穷尽全App消费者/手势，LyricLivePreview等仅声明',
         needed='具体unknown保留，不从名字补造作用；已有输入驱动关联足以进入D，无需执行歌曲填表'),
    dict(group='C01/C02/C04–09/C19–24/C39–41', issue='本机成员和部分IL已补，不等于所有非默认执行/模型路径通过',
         needed='已有native记录仍限原条件；进一步静态核查或授权最小读取，不新增合成填表'),
    dict(group='C43–45', issue='本机MixFx存在但独立三模块开关/WrapLive不存在；每内部算法非默认输出尚未验证',
         needed='本机和冻结上游分栏；不能照搬上游新UI功能或宣称听觉改善'),
]
