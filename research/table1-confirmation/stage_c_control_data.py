"""Explicit parameter enumeration for the frozen sources reviewed in Stage C.

Per-field values are code/config facts or labelled unknowns. Group profiles
provide shared execution conditions, never a shared perceptual recipe.
"""

FILES = {
    'note': 'OpenUtau.Core/Ustx/UNote.cs',
    'curve': 'OpenUtau.Core/Ustx/UCurve.cs',
    'format': 'OpenUtau.Core/Format/USTx.cs',
    'expr': 'OpenUtau.Core/Ustx/UExpression.cs',
    'phrase': 'OpenUtau.Core/Render/RenderPhrase.cs',
    'dyn': 'OpenUtau.Core/Render/Renderers.cs',
    'ds': 'OpenUtau.Core/DiffSinger/DiffSingerRenderer.cs',
    'utils': 'OpenUtau.Core/DiffSinger/DiffSingerUtils.cs',
    'variance': 'OpenUtau.Core/DiffSinger/DiffSingerVariance.cs',
    'pitch': 'OpenUtau.Core/DiffSinger/DiffSingerPitch.cs',
    'speaker': 'OpenUtau.Core/DiffSinger/DiffSingerSpeakerEmbedManager.cs',
    'phone': 'OpenUtau.Core/Ustx/UPhoneme.cs',
    'phoner': 'OpenUtau.Core/DiffSinger/DiffSingerBasePhonemizer.cs',
    'track': 'OpenUtau.Core/Ustx/UTrack.cs',
    'project': 'OpenUtau.Core/Ustx/UProject.cs',
    'part': 'OpenUtau.Core/Ustx/UPart.cs',
    'classic': 'OpenUtau.Core/Classic/ResamplerItem.cs',
    'crender': 'OpenUtau.Core/Classic/ClassicRenderer.cs',
    'world': 'OpenUtau.Core/Classic/WorldlineRenderer.cs',
    'growl': 'OpenUtau.Core/Classic/Hifisampler/HifiGrowl.cs',
    'voicevox': 'OpenUtau.Core/Voicevox/VoicevoxRenderer.cs',
    'enunu': 'OpenUtau.Core/Enunu/EnunuRenderer.cs',
    'vogen': 'OpenUtau.Core/Vogen/VogenRenderer.cs',
    'config': 'OpenUtau.Core/DiffSinger/DiffSingerConfig.cs',
    'prefs': 'OpenUtau.Core/Util/Preferences.cs',
    'fx': 'OpenUtau.Core/Ustx/UMixFx.cs',
    'fxchain': 'OpenUtau.Core/SignalChain/MixFxSource.cs',
    'compressor': 'OpenUtau.Core/SignalChain/Effects/SimpleCompressor.cs',
    'reverb': 'OpenUtau.Core/SignalChain/Effects/Freeverb.cs',
    'fxpresets': 'OpenUtau.Core/SignalChain/Effects/FxPresets.cs',
    'graph': 'OpenUtau.Core/ExpressionGraph/UExpressionGraph.cs',
    'nodes': 'OpenUtau.Core/ExpressionGraph/GraphNodeTypes.cs',
    'masked': 'OpenUtau.Core/Ustx/UMaskedCurve.cs',
}

# scope | local support / evidence | stage | condition | sampling | dependency
PROFILES = {
    'note': ('current_route', 'prior_native_pitch_clock_bound; nondefault_field_paths_upstream_checked',
             'score/phonemizer/variance/acoustic/vocoder', '音符有效；原生时钟及当前音符身份',
             '音符事件→TempoMap→5tick目标→模型帧；细部见各项', '重建音素/目标/variance/acoustic/vocoder及拼接'),
    'pitchcurve': ('current_route', 'prior_native_target_pitch_bound',
                   'target/variance/acoustic/vocoder', '当前DiffSinger支持；工程描述有效',
                   'UCurve整数线性取样→5tick→模型帧，非每工程点一模型帧', '重建目标与variance/acoustic/vocoder；核对note基底'),
    'vibrato': ('current_route', 'structure_present; local_nonzero_field_response_not_probed',
                'before_PITD_pitch', 'length>0且原生颤音启用；不能与人工周期重复',
                '归一音符位置/原生时钟→5tick目标', '重建before-PITD及完整目标/预测/渲染'),
    'dyn': ('current_route', 'prior_native_DYN_PCM_application_bound',
            'post_vocoder_amplitude', '当前DYN读取；原生采样与最终导出增益保持',
            '5tick节点先转振幅；PCM逐样本在振幅域插值', '重算DYN/输出/混音；输入模型条件不因增益本身改变'),
    'phonation': ('current_route', 'prior_fresh_acoustic_input_bound',
                  'acoustic_after_variance_prediction', '声库use_*与对应predict_*启用；预测存在',
                  '工程→5tick→模型帧，预测重采样→增量→feature clip；float顺序保持',
                  '人工增量变化重建声学/声码器及输出；条件变化另重建variance'),
    'shfc': ('current_route', 'prior_fresh_variance_acoustic_vocoder_inputs_bound',
             'variance_pitch/acoustic_condition/vocoder_branch', '当前pitch_controllable=true；工程合法范围单独核对',
             '5tick→模型帧；variance半音/acoustic Hz与vocoder目标分路', '重建variance/acoustic/vocoder，检查邻字/拼接/DYN'),
    'embed': ('current_route', 'current_config_enabled; default_input_seen; nondefault_mapping_not_reprobed',
              'acoustic_condition', '声库对应embedding启用且模型输入匹配',
              '5tick→模型帧及指定非线性换算', '重建声学/vocoder，核对当前预测与其他条件'),
    'disabled': ('current_route', 'current_config_disabled; not_an_available_control',
                 'conditional_model_input', '需要训练模型、预测和引擎共同支持；配置开关不能创造能力',
                 '启用路径的取样说明不是当前执行', '若换能力需重新验证全资源及依赖，当前不执行'),
    'speaker': ('current_route', 'prior_two_stage_speaker_inputs_bound',
                'duration_by_phone/pitch_variance_acoustic_by_frame', 'CLR索引/色名/subbank/speaker须匹配',
                'CLR按phone；clNN按5tick到帧，帧权重归一/默认补足', '重建duration/pitch/variance/acoustic/vocoder与完整时钟'),
    'predictpitch': ('current_route', 'config_use_expr_enabled; not_used_as_current_manual_line_generator',
                     'optional_pitch_prediction', 'use_expr/model支持；与当前人工目标制作分开',
                     '5tick→pitch模型帧；预测输出还须显式转写才改目标', '重建预测；若采用结果再重建目标/variance/acoustic/vocoder'),
    'phone': ('current_route', 'prior_native_phone_clock_vocabulary_bound; all_nondefault_edits_not_probed',
              'phonemizer/duration/context', '音素/字典/语言/延音身份有效；不拿HFA作音乐裁判',
              'tick事件→原生ms→累计时长量化为帧；无统一边界真值', '重建音素/时钟/两阶段speaker/目标及全部预测渲染'),
    'classic': ('other_engine', 'not_current_DiffSinger_control; other_engine_source_only',
                'Classic_sample/resampler/wavtool', '采样声库及具体音素器/重采样器支持；同名不能移植',
                '按phone/oto/ms、旗标及采样器实现，部分最终再DYN', '换样本/参数需重算对应采样/拼接/输出'),
    'other': ('other_engine', 'not_current_route; upstream_engine_path_checked',
              'engine_specific', '指定其它renderer及其配置有效；未做本机这些引擎的实际输入验证',
              '依字段及引擎，不能默认与DiffSinger等价', '重建该引擎条件/渲染与输出，切换引擎重新审计'),
    'upstream': ('upstream_local_unknown', 'fixed_upstream_only; installed_member_path_not_confirmed',
                 'version_specific', '仅所绑定上游代码明确；DLL哈希相同不证明拥有此新能力',
                 '按对应实现；未作为当前本机可用项', '采用前须核查安装版本/字段/实际读取；本轮不采用'),
    'resource': ('current_route', 'current_resource_config_SHA_rechecked; not_all_model_file_hashes_rechecked_here',
                 'resource_contract/all_model_stages', '配置需与权重/词表/embedding/声码器成套匹配',
                 '资源/配置；不是每帧艺术旋钮', '换资源须重载和全依赖重新验证，不在本轮修改'),
    'inference': ('current_route', 'prior_inference_settings_bound; live_preferences_not_loaded',
                  'inference_execution', '模型连续加速/variable-depth能力及实际ONNX输入匹配',
                  '每次推理设置，不能当声学表现值', '重建相应推理/缓存及输出，同输入公平比较'),
    'presentation': ('current_route', 'field_or_pipeline_present; current_nondefault_output_path_not_reprobed',
                     'mix/playback/export', '实际播放/导出通道读取；纯人声实验固定增益',
                     '输出振幅/通道/时间；具体pan law和导出顺序仍需路径补查', '重建混音/导出及峰值检查，不冒充模型条件变化'),
    'metadata': ('editing_metadata', 'no_direct_DSP_claim; parameter_driver_if_edit_changes_inputs',
                 'editor/serialization', '显示/选择本身不改声；落点/预设/函数写入需追踪实际字段',
                 '编辑操作/标签；真正改动映射至已有控制', '纯显示无；写入后按目标参数重建'),
}


def controls():
    out = []
    def add(group, field, unit, default, limits, transform, source, anchor,
            profile, caveat, abbr='', published=False):
        p = PROFILES[profile]
        out.append(dict(group_id=f'C{group:02}', field=field, storage_unit=unit,
                        default_or_baseline=default, declared_or_code_limits=limits,
                        transform=transform, source_path=FILES[source], source_anchor=anchor,
                        scope=p[0], current_support=p[1], stage=p[2], condition=p[3],
                        sampling_interpolation_clip=p[4], recalculate=p[5],
                        limitation=caveat, abbreviation=abbr,
                        published_descriptor_requested=published,
                        local_code_path_status='see_current_support_not_inferred_from_upstream',
                        dose_or_auditory_direction_validated=False))

    add(1,'notes[].tone','MIDI半音','工程逐音符','整数；编辑范围未以本次源码验证',
        'AdjustedTone=tone+tuning/100；phone选择用tone，最终目标用AdjustedTone','note','public int tone;',
        'note','移调是显式改tone/PITD等字段的操作，key标签不移调')
    add(1,'notes[].tuning','cents','0/工程逐音符','整数；未发现此声明处的独立钳位',
        'tuning/100进入AdjustedTone','note','public int tuning;', 'note','音素器note.tone与AdjustedTone不是同一个字段')
    for field,unit,tr,anchor in [
        ('pitch.data[].x','相对音符ms','ms点经项目时钟转tick','public class PitchPoint'),
        ('pitch.data[].y','0.1半音','y*10+AdjustedTone*100进入绝对cents','public class PitchPoint'),
        ('pitch.data[].shape','io/l/i/o/sp枚举','按每段形状插值；sp仅上游确认','public enum PitchPointShape'),
        ('pitch.snap_first','bool','相邻且连续时首点接Prev.AdjustedTone，否则首点0','if (pitch.snapFirst)')]:
        add(2,'notes[].'+field,unit,'工程逐音符','点顺序及合法枚举；非统一cents范围',tr,'note',anchor,
            'upstream' if field.endswith('shape') else 'note','相对点线和PITD叠加；本机sp支持未确认')
    add(3,'voice_parts[].curves[pitd].xs/ys','part相对ticks/cents','0',
        '上游默认±1200；发布描述另读','目标=before-PITD+PITD','phrase','pitchesBeforeDeviation',
        'pitchcurve','before-PITD仅编码；实测F0不由输入精确保证','pitd',True)
    for g,name,unit,default,limits,tr in [
        (4,'length','音符%','默认依NotePresets；工程逐音符','[0,100]','start=1-length/100'),
        (5,'period','ms','默认依NotePresets','[5,500]','Hz=1000/period'),
        (6,'depth','cents峰幅','默认依NotePresets','[5,200]','sin(phase)*depth，峰峰为2depth'),
        (7,'in','颤音区%','默认依NotePresets','[0,100]；设in会将out缩至<=100-in','入口线性幅度包络'),
        (7,'out','颤音区%','默认依NotePresets','[0,100]；设out会将in缩至<=100-out','退出线性幅度包络'),
        (8,'shift','周期%','默认依NotePresets','[0,100]','phase+=(shift/100)*2π'),
        (8,'drift','depth相关%','默认依NotePresets','[-100,100]','周期cents中心加depth/100*drift')]:
        add(g,'notes[].vibrato.'+name,unit,default,limits,tr,'note','public float '+('@' if name in ['in','out'] else '')+name,
            'vibrato','软件范围不是推荐剂量；输入单位与听觉自然度分开')
    add(9,'notes[].vibrato.vol_link','%','依NotePresets','[-100,100]',
        '按同相位和in/out包络乘振幅；负值相位+50%；幅度100平台可0.2～1.2',
        'note','public float volLink','upstream','原生新上游才确认；当前实验没有启用')
    add(10,'curves[dyn].xs/ys','ticks/0.1dB','0','上游[-240,120]；发布描述另读',
        'value==描述min则0振幅，否则10^(value*0.1/20)','phrase','x == c.Min ? 0',
        'dyn','最低值特殊静音而非普通-24dB；不改变发声预测','dyn',True)
    for g,name,default,limits,tr,clip in [
        (11,'voic','100','上游[0,100]；发布[0,200]','pred+(value-100)*12/100','[-96,0]'),
        (12,'brec','0','上游/发布[-100,100]','pred+value*12/100','[-96,0]'),
        (13,'tenc','0','上游/发布[-100,100]','pred+value/20','[-10,10]')]:
        add(g,'curves['+name+'].xs/ys','ticks/模型条件增量控制',default,limits,
            tr+'，final clip'+clip,'utils','VarianceDeltaFunctions','phonation',
            'feature不是PCM dB/闭合商/撕裂度；预测基底不因人工零增量消失',name,True)
    add(14,'curves[shfc].xs/ys','ticks/cents','0','上游±1200；发布±12；诊断工程显式±1200',
        'variance pitch+=SHFC/100；当前acoustic F0*=2^(SHFC/1200)，vocoder保留目标F0',
        'ds','float[] shiftedF0','shfc','-4存储是-4c而非-4半音；预测及邻字变化，不独立锁定PCM F0','shfc',True)
    add(15,'curves[genc].xs/ys','ticks/[-100,100]控制','0','上游[-100,100]；发布无此显式描述',
        'range[-5,+5]：gender=-value*12/5/100；-100→+2.4，+100→-2.4',
        'ds','var positiveScale','embed','模型gender张量量，不是实测F1/F2半音移动','genc')
    add(16,'curves[velc].xs/ys','ticks/log2速度控制','100','建议描述[0,200]',
        'velocity=2^((value-100)/100)，0→0.5/100→1/200→2','ds','//velocity','embed',
        '未显式声明的工程不把name存在当新控制已写入；非音素时长倍率','velc')
    add(17,'curves[ene].xs/ys','ticks/条件增量','0','建议描述[-100,100]',
        '启用时clip(pred+value*12/100,-96,0)','ds','if(singer.dsConfig.useEnergyEmbed)',
        'disabled','本机use_energy_embed/predict_energy均false；不是当前响度旋钮','ene')
    for field in ['dsconfig.use_falsetto_embed','dsvariance/dsconfig.predict_falsetto']:
        add(18,field,'能力配置bool','false','只读配置事实；无已确认独立缩写',
            '当前没有确认的执行控制路径','config','public class DsConfig','disabled',
            '本机yaml有字段不保证此版本解析或已训练能力；不能直接打开')
    add(19,'phoneme_expressions[clr].index/value','phone索引/色名枚举','0为空默认','发布options长度6/索引0～5',
        'ToPhonemizerNote按index取color，subbank suffix选speaker','note','attr.voiceColor',
        'speaker','CLR options名不自动证明帧阶段embedding；索引0不是每phone复制','clr',True)
    for n in range(1,6):
        add(20,f'curves[cl{n:02}].xs/ys','ticks/%','0','0～100',
            'subbank映射到speaker；总权重>1归一，否则余量填该帧默认speaker',
            'speaker','var spkSum','speaker','5色具体名称/索引以当前资源和USTX绑定，曲线全零不静音',f'cl{n:02}',True)
    add(21,'curves[pexp].xs/ys','ticks/预测表达控制','100','建议[0,100]',
        'pitch模型expr=clip(value/100,0,1)','pitch','//expressiveness','predictpitch',
        '不自动作用于人工已编译目标；不恢复自动生成路线','pexp')
    add(21,'pitch retake note-index selection','显式note index集合','无/按请求','有效note范围；上游实现',
        'retake mask送pitch预测，输出需另采用','pitch','retakeNoteIndexes','upstream',
        '选择范围/重新生成不是新的声学量；本机新retake路径未确认')
    for field,unit,default,limits,tr,src,anchor in [
        ('notes[].position','part相对ticks','工程','整数','part.position+note.position→ms','note','public int position;'),
        ('notes[].duration','ticks','工程','Validate至少10tick','end=position+duration','note','duration = Math.Max(10, duration);'),
        ('voice_parts[].position','project ticks','0/工程','整数','所有子事件整体偏移','part','public int position = 0;'),
        ('voice_parts[].duration','ticks','工程','与note内容须一致','part长度/编辑边界','part','public int duration;'),
        ('tempos[].position','project ticks','0/工程','事件序列','BPM段起点影响timeAxis','project','public class UTempo'),
        ('tempos[].bpm','BPM','120/工程','此定义处无可靠独立UI范围','tick-ms随tempo段改变','project','public double bpm;')]:
        add(22,field,unit,default,limits,tr,src,anchor,'note','按实际TempoMap；5tick不是固定ms')
    for field,tr,src,anchor in [
        ('notes[].lyric','优先hint/字典/合法token决定符号','note','public string lyric'),
        ('notes[].lyric [phonetic hint]','hint解析且拒绝不在词表的token','phoner','string[] ParsePhoneticHint'),
        ('phoneme_overrides[].phoneme','按index替换指定符号','phone','public string? phoneme;'),
        ('track.phonemizer / note.phonemizer','选择语言/音素器；note override为版本能力','note','PhonemizerOverride')]:
        add(23,field,'字符串/身份','工程或默认','当前词表/音素器有效集合',tr,src,anchor,
            'upstream' if field.endswith('note.phonemizer') else 'phone','选择合法token不保证实际口型/咬字自然')
    add(23,'dsconfig.languages / use_lang_id','词表文件/bool','当前true','language ID由词表映射',
        '按音素前缀映射language张量，不是任意换ID的风格旋钮','phoner','//Load language id','resource','改语言需完整匹配词表和模型')
    add(24,'phoneme_overrides[].offset','ticks','null=原音素起点','有效几何需原生核查',
        '按index移动音素事件，影响相邻实际时长','phone','public int? offset;','phone','不以输入offset当实际发音起点真值')
    for field,tr in [('notes[].lyric +','延续note组并保留音素组上下文'),
                     ('AP token','非唱呼吸模型符号，需当前词表支持'),('SP token','静音模型符号及上下文，需词表支持'),
                     ('phrase grouping / split','改变整句预测上下文，不仅是切音频')]:
        add(24,field,'符号/分组','Agent显式决定','当前音素器/词表及原生分句',tr,
            'phoner','g2pBuilder.AddSymbol','phone','AP/SP=工程token，不是实际吸气/静音标签')
    add(25,'phoneme_expressions[vel].value','百分数控制','100','上游[0,200]',
        'phonemizer attr.consonantStretchRatio=2^(1-value/100)','note','attr.consonantStretchRatio',
        'classic','DiffSingerBase本次未找到此属性读取，不能说本机g/uo时长已可控','vel')
    for g,name,default,limits in [(26,'vol','100','[0,200]'),(26,'atk','100','[0,200]'),(26,'dec','0','[0,100]')]:
        add(g,'phoneme_expressions['+name+'].value','%控制',default,limits,
            'UPhoneme采样包络/ResamplerItem读取；模型发声输入不读该音素包络',
            'phone','public class UPhoneme','classic','DiffSinger SupportsPhonemeEnvelope=false；不是本机DYN',name)
    for name,tr in [('preutter_delta','preutter=max(0,autoPreutter+delta)'),('overlap_delta','overlap=autoOverlap+delta'),
                    ('attack_time_delta','淡入包络点时间加delta并受相邻点限制'),('release_time_delta','淡出包络起点提前delta并受限制')]:
        add(27,'phoneme_overrides[].'+name,'ms','null/0','合法几何受UPhoneme检查',tr,
            'phone','public class UPhonemeOverride','classic','采样oto/包络时间，不是本机模型phone offset')
    for name,unit,tr in [('Offset','ms','采样开始区定位'),('Consonant','ms','固定/伸缩区域分界'),
                         ('Cutoff','ms，符号有意义','末端裁切/有效长度约定'),('Preutter','ms','相对note提前发声'),
                         ('Overlap','ms','与前样本重叠'),('Alias','字符串','样本符号选择'),
                         ('FRQ','源音频频率分析','提供重采样源F0/原录音调制')]:
        add(28,'oto/frq.'+name,unit,'声库原件','采样器/声库约定，非通用合法范围',tr,
            'classic','public class ResamplerItem','classic','不同采样器细节需专属核查，不修改声库')
    for name,default,limits,tr in [('alt','0','[0,16]','alternate索引参与音素器alias选择'),
                                  ('shft','0','[-36,36]','toneShift半音提示/指定引擎查询条件')]:
        add(29,'phoneme_expressions['+name+'].value','整数',default,limits,tr,
            'note','attr.toneShift' if name=='shft' else 'attr.alternate','classic','SHFT不是SHFC；实际音素器是否读另审',name)
    for name,tr in [('renderer','选择IRenderer和支持集'),('resampler','Classic默认采样器'),('wavtool','Classic拼接器')]:
        add(30,'tracks[].renderer_settings.'+name,'实现名称','声库/首选项默认','安装可用实现集合',tr,
            'track','public string '+name+';','resource','更换实现须重审控制含义；具体插件集合开放')
    add(30,'phoneme_expressions[eng].value','Options索引','默认引擎','随可用重采样器枚举',
        '逐phone选择采样器','format','"resampler engine"','classic','当前DiffSinger没有逐phone采样器路径','eng')
    for name,flag,default,limits in [('gen','g','0','[-100,100]'),('bre','B','0','[0,100]'),
                                  ('lpf','H','0','[0,100]'),('norm','P','86','[0,100]')]:
        add(31,'phoneme_expressions['+name+'].value','采样器flag控制',default,limits,
            '通过'+flag+'旗标传具体resampler，换算不是通用模型公式',
            'classic','flags = phone.flags','classic','flag名称不证明引擎支持；NORM会改变增益可比性',name)
    for name,tr in [('mod','phone.modulation*100传resampler'),('mod+','源frq调制保留路径，叠入目标依实现')]:
        add(32,'phoneme_expressions['+name+'].value','%','0','[0,100]',tr,
            'classic' if name=='mod' else 'phrase','modulation =' if name=='mod' else 'modPlus',
            'classic','非本机DiffSinger源录音旋钮',name)
    add(33,'phoneme_expressions[dir].value','off/on','off','Options0/1',
        'Classic直接采样分支；VOICEVOX另一F0分支，不能统一解释',
        'format','"direct"','other','需具体renderer读取；非通用自然开关','dir')
    for name,unit,tr in [('clry','色名Options','第二样本/色映射'),('xsy','%曲线','准备第二样本后交叉合成')]:
        add(34,('phoneme_expressions' if name=='clry' else 'curves')+'['+name+']',unit,
            '默认/0','XSY[0,100]；CLRY随subbank',tr,'format','"voice color y"' if name=='clry' else '"cross synthesis',
            'upstream','Classic/Worldline上游能力；不是当前DiffSinger speaker混合',name)
    add(35,'curves[grwc].xs/ys','ticks/%','0','[0,100]',
        'Hifisampler高频方波音高调制强度（最高100c），RMS匹配','growl','MaxVibratoCents',
        'upstream','当前DiffSinger不支持；80Hz/400Hz是调用参数/默认，不是人体机制','grwc')
    for name,unit,tr in [('name','字符串','显示名称'),('abbr','字符串','读取查找键'),('type','Numerical/Options/Curve/MaskedCurve','决定输入形态'),
                         ('min','控制单位','描述最低值；DYN最低值有特殊语义'),('max','控制单位','描述上限'),('default_value','控制单位','缺值默认'),
                         ('custom_default_value','控制单位','自定义默认回退'),('is_flag','bool','采样flag输出声明'),('flag','协议字符串','采样器flag名'),
                         ('options','字符串数组','Options索引映射'),('skip_output_if_default','bool','默认flag是否省略'),('track_expressions','描述覆盖','track优先于project')]:
        add(36,'expressions[].'+name,unit,'项目/轨道定义','声明范围≠引擎支持≠模型clip',tr,
            'track' if name=='track_expressions' else 'expr','TryGetExpDescriptor' if name=='track_expressions' else 'public class UExpressionDescriptor',
            'metadata' if name=='name' else 'resource','任意新增abbr不会自动送模型；OPE当前无读取证据')
    for name,unit,default,limits,tr in [('volc','%','100','[0,200]','VOICEVOX volume*=value*.01'),
                                       ('smoc','平滑宽度控制','0','[0,10]','LoadRenderedPitch平滑参数'),
                                       ('repm','版本/Options模式','unknown','建议描述被注释','路径/可用UI仍需版本配置')]:
        add(37,'VOICEVOX.'+name,unit,default,limits,tr,'voicevox', 'abbr='+name.upper() if name=='volc' else 'SMOC' if name=='smoc' else 'REPM',
            'other','不移植至Yousa；列入支持集合也不代表可用滑块',name)
    for name,tr in [('GENC','0.5+0.005*value'),('TENC','0.5+0.005*value'),('BREC','0.5+0.005*value'),('VOIC','0.01*value')]:
        add(38,'Worldline.'+name,'归一化合成条件','依表达默认','依表达/引擎',tr,
            'world','phraseSynth.SetCurves','other','同缩写的公式与DiffSinger预测增量不同')
    add(38,'ENUNU.extensions.styles','配置定义style/表达','声库配置','开放扩展集合',
        '由style配置定义支持键；不能穷尽未来自定义项','enunu','supportedExp','other','本轮未装载其它库styles；具体集合仍缺')
    add(38,'Vogen renderer selection','模型实现选择','声库/renderer','已调查renderer集合',
        '换引擎不是新的连续艺术控制','vogen','class VogenRenderer','other','未声称Vogen支持DiffSinger全部表达')
    for field,tr in [('acoustic','声学模型文件'),('dur','duration模型'),('linguistic','对应阶段语言编码器'),('pitch','pitch模型'),
                     ('variance','发声预测模型'),('vocoder','声码器与mel/F0契约'),('speakers','embedding文件名/顺序'),
                     ('hidden_size','embedding维数需匹配模型'),('phonemes','token词表'),('languages','语言映射'),
                     ('use_lang_id','每音素语言输入能力'),('augmentation_args.random_pitch_shifting.range','GENC换算/训练能力条件'),
                     ('use_key_shift_embed','gender条件能力'),('use_speed_embed','velocity条件能力'),
                     ('use_energy_embed','energy能力'),('use_breathiness_embed','breathiness能力'),('use_voicing_embed','voicing能力'),
                     ('use_tension_embed','tension能力'),('use_continuous_acceleration','steps/depth ONNX输入分支'),
                     ('use_variable_depth','限制扩散depth分支'),('max_depth','当前声学上限0.6')]:
        add(39,'dsconfig(stage).'+field,'成套资源/能力配置','实际yaml，不能用类默认代替',
            '模型契约约束，非独立歌唱滑块',tr,'config','public class DsConfig','resource','当前只重查配置/DLL SHA；未重新推理/重哈希每个大模型')
    add(39,'vocoder.pitch_controllable','bool','当前true','训练声码器能力',
        '决定acoustic条件F0与vocoder目标F0分路是否有效','ds','if (vocoder.pitch_controllable)',
        'resource','配置必须对应实际模型能力；不能推断实测F0精确')
    for field,unit,default,limits,tr in [
        ('DiffSingerSteps','步数','上游默认20；旧实验20','当前输入整数；本分支直接发送','声学ONNX steps'),
        ('DiffSingerDepth','比例','上游默认1；旧实验0.6','启用variable-depth时min(偏好,max_depth)','当前max_depth=0.6；未读取live偏好'),
        ('DiffSingerStepsVariance','步数','上游默认20；本机旧运行绑定另查','模型配置分支','variance推理steps/speedup'),
        ('DiffSingerStepsPitch','步数/新版本浅扩散请求','上游默认10','源码AddPitchSamplingInputs；<1为版本能力','依continuous/depth输入选择分支')]:
        add(40,'Preferences.'+field,unit,default,limits,tr,
            'pitch' if field=='DiffSingerStepsPitch' else 'prefs', 'AddPitchSamplingInputs' if field=='DiffSingerStepsPitch' else field,
            'inference','11/101是封存实验随机种子，不是步数；更多步不保证更好听')
    add(40,'diagnostic variance/acoustic random seed','整数执行条件','封存实验11/101','不是已确认正常UI旋钮',
        '诊断推理随机输入固定供公平对比；实际证据在封存报告','variance','varianceModel',
        'inference','本轮未新增随机seed控制接口，不根据seed搜音色')
    for field,tr,profile in [('DiffSingerTensorCache','缓存推理结果/执行状态','inference'),
                             ('DiffSingerVarianceLocalPitchPatch','局部预测缓存重用新能力','upstream'),
                             ('DiffSingerMergeNearbyPhrases','附近句合并改变上下文','upstream')]:
        add(41,'Preferences.'+field,'bool','上游true/false/false（按顺序）','版本能力',tr,
            'prefs',field,profile,'cached export不等于全新成声；本轮不清旧缓存')
    for name in ['headFrames','tailFrames']:
        add(41,'DiffSingerUtils.'+name,'模型帧','8','源码常量，非正常独立UI控制',
            'frameMs=1000*hop_size/sample_rate；padding改变完整输入','utils','public const int '+name,
            'resource','当前44100/512约11.610ms/frame；不能任意改padding配方')
    for field,unit,tr,src,anchor in [('Volume','dB','轨道输出增益；pan law/实际出口另查','track','public double Volume'),
                                    ('Pan','通道位置控制','通道平衡；确切law未在此字段定义证实','track','public double Pan'),
                                    ('Mute','bool','轨道静音呈现','track','public bool Mute'),('Solo','bool','播放/混音solo选择','track','public bool Solo'),
                                    ('wave_part.position','project ticks','伴奏/录音相对歌声时钟','part','public int position = 0;')]:
        add(42,'tracks[].'+field,unit,'工程','字段/呈现路径需分别核查',tr,src,anchor,'presentation','字段存在不证明每种导出路径相同')
    for group,field,unit,default,tr,anchor in [
        (43,'Enabled','bool','false','null/false旁路整个链','public bool Enabled'),
        (43,'EqEnabled','bool','true','控制EQ模块旁路','public bool EqEnabled'),
        (43,'EqPreset','字符串','vocal_air','UI/预设加载来源；实际EQ由值决定','public string EqPreset'),
        (43,'EqLowDb','dB','0','低频滤波增益','public double EqLowDb'),
        (43,'EqMidFreq','Hz','3000','中频EQ频点；非元音F2直接控制','public double EqMidFreq'),
        (43,'EqMidDb','dB','1.5','中频滤波增益；Q固定0.707','public double EqMidDb'),
        (43,'EqHighDb','dB','3','高频滤波增益','public double EqHighDb'),
        (44,'CompEnabled','bool','true','压缩模块旁路','public bool CompEnabled'),
        (44,'CompPreset','字符串','gentle','名称还用于选择attack/release，不只是UI标签','public string CompPreset'),
        (44,'CompThresholdDb','dB','-18','静态软膝压缩门槛','public double CompThresholdDb'),
        (44,'CompRatio','比例','2','运行时max(1,ratio)','public double CompRatio'),
        (44,'CompMakeupDb','dB','2.5','压缩后补偿增益','public double CompMakeupDb'),
        (45,'ReverbEnabled','bool','true','混响模块旁路','public bool ReverbEnabled'),
        (45,'ReverbPreset','字符串','small_room','还选Width/Wet/Dry内部值，不只是显示','public string ReverbPreset'),
        (45,'ReverbSize','标量','0.30','comb反馈=size*.28+.7；有效范围需UI/稳定性另查','public double ReverbSize'),
        (45,'ReverbDamp','标量','0.7','damping=damp*.4；非声道共振控制','public double ReverbDamp'),
        (45,'ReverbWet','标量','1','链层clip[0,2]乘preset Wet','public double ReverbWet'),
        (45,'ReverbPreDelayMs','ms','0','Configure钳位[0,200]，只延迟湿声','public double ReverbPreDelayMs')]:
        add(group,'tracks[].mix_fx.'+field,unit,'上游类默认'+default,'类声明未通用钳位；各运行点另列',tr,
            'fx',anchor,'upstream','当前安装MixFx路径未确认；不用于封存纯声比较')
    for g,field,unit,default,tr,source,anchor in [
        (44,'preset.AttackMs','ms','按preset','Configure系数exp(-1/(max(.05,attackMs)*.001*sr))','compressor','this.atkCoef'),
        (44,'preset.ReleaseMs','ms','按preset','Configure系数exp(-1/(max(.05,releaseMs)*.001*sr))','compressor','this.relCoef'),
        (44,'algorithm.kneeDb','dB','6','代码软膝参数，不是独立当前UI滑块','compressor','double kneeDb = 6.0'),
        (45,'preset.Width','标量','按preset','运行时clip[0,1]','reverb','this.width ='),
        (45,'preset.Dry','标量','按preset','Configure max(0,dry)','reverb','this.dry ='),
        (45,'preset.Wet','标量','按preset','与ReverbWet相乘','fxchain','rParams.Wet * userWet')]:
        add(g,'MixFx.internal.'+field,unit,default,'内部/preset值；并非全部可直接编辑',tr,source,anchor,'upstream','需同时绑定preset表和值，避免误把内部参数作UI旋钮')
    add(46,'Preferences.MixFxApplyOnExportMixdown','bool','上游默认true（当前未确认）','版本配置',
        '控制混音导出是否含MixFx，须核实具体导出路径','prefs','MixFxApplyOnExportMixdown',
        'upstream','试听与导出可能因该选择不同；本机流程没有启用MixFx')
    for field,unit,tr in [('sample_rate','Hz','模型/声码器须匹配；不是任意改配置实现重采样'),
                         ('hop_size','samples/frame','决定模型帧时钟'),('win_size','samples','特征窗口契约'),('fft_size','samples','FFT契约'),
                         ('num_mel_bins','bins','mel维数契约'),('mel_fmin','Hz','mel下限契约'),('mel_fmax','Hz','mel上限契约'),
                         ('mel_base','枚举','特征数值契约'),('mel_scale','枚举','特征频率尺度契约')]:
        add(46,'acoustic/vocoder.'+field,unit,'当前资源配置','成套模型契约',tr,'config','public class DsConfig','resource','不是正常导出格式/音色旋钮；不在本轮改模型配置')
    add(46,'export format / external playback gain','PCM编码/位深/声道/电平','当前固定PCM输出，外部设备unknown',
        '本仓库输出路径与实际播放设备分开','播放/外部转换属于呈现环境；OpenUtau独立导出UI集合尚缺',
        'dyn','public static void ApplyDynamics','presentation','此引用仅原生输出阶段锚；位深/监听不由该方法定义，详细导出机制待补')
    for field,unit,tr,source,anchor in [('rpit','MIDI*100绝对cents/空mask','已渲染预测pitch存储供graph读取','format','"rendered pitch (masked'),
                                         ('pito','MIDI*100绝对cents/空mask','用户pitch override供graph读取','format','"pitch override (masked'),
                                         ('expression_graph','节点/边/驱动','驱动已有pitch/表达，不是新增生理量','graph','class UExpressionGraph'),
                                         ('graph node parameters','算术/时间/LFO等节点字段','需按node类型枚举；本轮具体node字段未穷尽','nodes','class'),
                                         ('masked curve defined/undefined','显式mask','空值与0不同，只有graph读取','masked','class UMaskedCurve')]:
        add(47,field,unit,'版本定义','RPIT/PITO默认[2400,10800]/6000；其他按node',tr,source,anchor,'upstream',
            '当前显式Agent函数与新上游graph分开；图全部node参数尚有枚举缺口',field if field in ['rpit','pito'] else '')
    add(47,'Agent functions/anchors/slopes/envelope/quantization','秒/cents/cents每秒/Hz等','显式计划',
        '各函数schema与合法支持','编译为已列目标pitch/控制；不是OpenUtau独立新通道','curve','public const int interval = 5;',
        'metadata','Skill保持；具体函数schema独立绑定，1tick写入不等于原生采样')
    for field,unit,tr,source,anchor in [('key','0～11音名','标记调性，不自动移动tone','project','public int key'),
                                      ('time_signatures','拍号/位置','拍格/小节组织，非同BPM下直接音高操作','project','timeSignatures'),
                                      ('TrackName','字符串','组织/显示','track','public string TrackName'),
                                      ('TrackColor','字符串','显示','track','public string TrackColor')]:
        add(48,field,unit,'项目/轨道','有效标签',tr,source,anchor,'metadata','纯显示不当声学因素；拍号与tempo分开')
    add(48,'snap/grid/zoom/preset/editor preferences','编辑选择/填值','用户设置','UI字段集合仍有枚举缺口',
        '纯显示不进DSP；预设/网格编辑若写参数则追踪到具体控制','prefs','class Preferences',
        'metadata','未把所有UI字段伪称已枚举；任意外部插件/flags开放')
    counts = {}
    for r in out:
        g = r['group_id']
        counts[g] = counts.get(g, 0) + 1
        r['id'] = f'PARAM:{g}.{counts[g]:02}'
    assert set(counts) == {f'C{i:02}' for i in range(1,49)}
    assert len({r['id'] for r in out}) == len(out)
    return out
