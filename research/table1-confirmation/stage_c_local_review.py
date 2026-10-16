"""SHA-bound offline metadata assertions and explicit local support conclusions.

No target assembly is loaded. IL proves the selected branch/call/member only;
it does not prove a UI session, nondefault model execution, or auditory effect.
"""
import hashlib
import json

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def review(metadata_dir, openutau):
    raw = {}
    bindings = []
    for role, name in [('OpenUtau.Core.dll','core-metadata.json'),('OpenUtau.dll','app-metadata.json')]:
        path = metadata_dir / name
        d = json.loads(path.read_text(encoding='utf-8'))
        assert d['mode'] == 'offline_PE_metadata_and_IL_no_target_execution'
        assert d['sha256'] == digest(openutau / role), f'Stale metadata: {role}'
        raw[role] = {t['name']: t for t in d['types']}
        bindings.append(dict(role=role, sha256=d['sha256'], assembly_version=d['version'],
                             mvid=d['mvid'], metadata_sha256=digest(path), type_count=len(d['types'])))
    core = raw['OpenUtau.Core.dll']
    app = raw['OpenUtau.dll']
    entries = []
    def method(types, type_name, method_name):
        matches = [m for m in types[type_name]['methods'] if m['name'] == method_name]
        assert len(matches) == 1, (type_name,method_name)
        assert matches[0]['il'] is not None, (type_name,method_name,'IL not collected')
        return matches[0]
    def proof(types, type_name, method_name, operands=()):
        m = method(types,type_name,method_name)
        selected = [o for o in m['il'] if o['operand'] in operands]
        assert set(operands) <= {o['operand'] for o in selected}, (type_name,method_name,operands)
        return dict(type=type_name, method=method_name, method_token=m['token'],
                    il_sha256=hashlib.sha256(json.dumps(m['il'],sort_keys=True).encode()).hexdigest(),
                    selected_instructions=selected)
    def add(capability, status, conclusion, evidence):
        entries.append(dict(id=f'LOCAL:{len(entries)+1:02}', capability=capability,
                            status=status, conclusion=conclusion, evidence=evidence,
                            nondefault_execution_tested=False, auditory_effect_validated=False))
    absent = ['OpenUtau.Core.ExpressionGraph.UExpressionGraph',
              'OpenUtau.Core.ExpressionGraph.GraphNodeTypes',
              'OpenUtau.Core.ExpressionGraph.ExpressionGraphProgram',
              'OpenUtau.Core.Ustx.UMaskedCurve']
    assert all(n not in core for n in absent)
    assert not any('.ExpressionGraph.' in n for n in core)
    add('expression graph / masked curves','absent_in_bound_core',
        'Core完整TypeDefinition无graph命名空间及UMaskedCurve；本机当前没有所绑定上游图驱动类型',
        dict(queried_types=absent, complete_type_inventory=True))
    for t, field in [('OpenUtau.Core.Ustx.UProject','expressionGraphs'),
                     ('OpenUtau.Core.Ustx.UProject','defaultExpressionGraphs')]:
        assert field not in {f['name'] for f in core[t]['fields']}
    assert 'get_ExpressionGraph' not in {m['name'] for m in core['OpenUtau.Core.Ustx.UTrack']['methods']}
    add('project/track graph references','absent_in_bound_core',
        '项目图库/default及track图属性缺失；不能借现有USTX默认加载宣称graph生效',
        dict(types=['OpenUtau.Core.Ustx.UProject','OpenUtau.Core.Ustx.UTrack'], queried_members=['expressionGraphs','defaultExpressionGraphs','get_ExpressionGraph']))
    shape = core['OpenUtau.Core.Ustx.PitchPointShape']
    sp = next(f for f in shape['fields'] if f['name']=='sp')
    assert sp['constant_type']=='Int32' and sp['constant_bytes']=='04000000'
    interp = method(core,'OpenUtau.Core.MusicMath','InterpolateShape')
    switch = next(o for o in interp['il'] if o['opcode']=='switch')
    assert len(switch['operand']) == 5
    target = switch['operand'][4]
    arm = [o for o in interp['il'] if target <= o['offset'] <= target+11]
    assert any(o['operand']=='OpenUtau.Core.MusicMath::SinEasingInOut' for o in arm)
    add('PitchPointShape.sp','enum_and_helper_branch_present',
        'sp=4存在；通用InterpolateShape分支与io同SinEasingInOut；非默认整曲执行未测，不宣称新的样条算法',
        dict(enum_field=sp, method_token=interp['token'], switch=switch, arm=arm))
    fx = core['OpenUtau.Core.Ustx.UMixFx']
    getters = {m['name'] for m in fx['methods']}
    assert 'get_Enabled' in getters
    missing = ['get_EqEnabled','get_CompEnabled','get_ReverbEnabled']
    assert not set(missing) & getters
    add('MixFx independent module switches','absent_in_bound_core',
        'Enabled整体存在；EqEnabled/CompEnabled/ReverbEnabled缺失，不可照搬新上游独立开关',dict(type=fx['name'], absent_getters=missing))
    wrap = proof(core,'OpenUtau.Core.SignalChain.MixFxSource','WrapWith',[
        'OpenUtau.Core.Ustx.UMixFx::get_Enabled','OpenUtau.Core.Ustx.UMixFx::get_EqLowDb',
        'OpenUtau.Core.Ustx.UMixFx::get_CompPreset','OpenUtau.Core.Ustx.UMixFx::get_ReverbPreset',
        'OpenUtau.Core.SignalChain.Effects.BiquadEQ::Configure',
        'OpenUtau.Core.SignalChain.Effects.SimpleCompressor::Configure',
        'OpenUtau.Core.SignalChain.Effects.Freeverb::Configure'])
    add('MixFx Enabled / parameter read path','IL_read_path_present',
        'WrapWith读整体启用、EQ值及压缩/混响preset与值后Configure；null/disabled旁路；不证明副作用/自然度',wrap)
    assert 'WrapLive' not in {m['name'] for m in core['OpenUtau.Core.SignalChain.MixFxSource']['methods']}
    add('MixFx WrapLive','absent_in_bound_core',
        '本机只有WrapWith静态组装；上游播放跟随MixFx live的路径不存在',
        dict(type='OpenUtau.Core.SignalChain.MixFxSource', absent_method='WrapLive'))
    add('track fader / pan law','IL_read_path_present',
        'RenderMixdown读Muted/Volume/Pan→Fader→WrapWith→WaveMix；PanToChannelVolumes公式与固定上游一致',[
            proof(core,'OpenUtau.Core.Render.RenderEngine','RenderMixdown',[
                'OpenUtau.Core.Ustx.UTrack::get_Muted','OpenUtau.Core.Ustx.UTrack::get_Volume',
                'OpenUtau.Core.Ustx.UTrack::get_Pan','OpenUtau.Core.SignalChain.Fader::SetScaleToTarget',
                'OpenUtau.Core.SignalChain.MixFxSource::WrapWith','OpenUtau.Core.SignalChain.WaveMix::.ctor']),
            proof(core,'OpenUtau.Core.MusicMath','PanToChannelVolumes',[
                -100,100,200,1.5707964,'System.Math::Clamp','System.Math::Cos','System.Math::Sin'])])
    add('volume nonlinear low range / smoothing','IL_read_path_present',
        'db<=-24为0；db<-16先2db+16；Fader每交错sample追target最大0.0005；初始SetScaleToTarget',[
            proof(core,'OpenUtau.Core.PlaybackManager','DecibelToVolume',[-24,-16,2,16,'OpenUtau.Core.MusicMath::DecibelToLinear']),
            proof(core,'OpenUtau.Core.SignalChain.Fader','Mix',[0.0005,'OpenUtau.Core.MusicMath::PanToChannelVolumes'])])
    mix_type = next(n for n,t in core.items() if any(m['name']=='<RenderMixdown>b__0' for m in t['methods']) and 'PlaybackManager+' in n)
    track_type = next(n for n,t in core.items() if any(m['name']=='<RenderToFiles>b__0' for m in t['methods']) and 'PlaybackManager+' in n)
    mix_method = method(core,mix_type,'<RenderMixdown>b__0')
    callidx = next(i for i,o in enumerate(mix_method['il']) if o['operand']=='OpenUtau.Core.Render.RenderEngine::RenderMixdown')
    assert [o['opcode'] for o in mix_method['il'][callidx-3:callidx]] == ['ldc.i4.1','ldc.i4.1','ldloc.0']
    assert not any('MixFxApplyOnExportMixdown' in str(o['operand']) for o in mix_method['il'])
    add('UI/bridge mixdown WAV path','IL_read_path_present',
        '正常mixdown调用wait=true/applyMixFx=true；ExportAdapter 44100/2 float transport，CreateWaveFile16最终编码',[
            proof(core,mix_type,'<RenderMixdown>b__0',['OpenUtau.Core.Render.RenderEngine::RenderMixdown','NAudio.Wave.WaveFileWriter::CreateWaveFile16']),
            dict(argument_instructions=mix_method['il'][callidx-3:callidx+1]),
            proof(core,'OpenUtau.Core.SignalChain.ExportAdapter','.ctor',[44100,'NAudio.Wave.WaveFormat::CreateIeeeFloatWaveFormat'])])
    add('MixFxApplyOnExportMixdown preference','declared_but_not_read_in_export_path',
        '偏好字段存在，所核查mixdown闭包不读，直接固定applyMixFx=true；不标可用效果器导出开关',
        dict(type=mix_type,method_token=mix_method['token'], field_not_read='MixFxApplyOnExportMixdown'))
    dry = method(core,'OpenUtau.Core.Render.RenderEngine','RenderTracks')
    assert not any(any(x in str(o['operand']) for x in ['Fader','MixFx','UWavePart']) for o in dry['il'])
    track_method = method(core,track_type,'<RenderToFiles>b__0')
    mono_idx = next(i for i,o in enumerate(track_method['il']) if o['operand']=='NAudio.Wave.WaveExtensionMethods::ToMono')
    assert [(o['opcode'],o['operand']) for o in track_method['il'][mono_idx-2:mono_idx]] == [('ldc.r4',1),('ldc.r4',0)]
    add('track export dry mono path','IL_read_path_present',
        'RenderTracks无fader/FX/wave输入；RenderToFiles跳过Muted并ToMono(1,0)→CreateWaveFile16；DYN属renderer仍保留',[
            proof(core,track_type,'<RenderToFiles>b__0',['OpenUtau.Core.Render.RenderEngine::RenderTracks',
                'OpenUtau.Core.Ustx.UTrack::get_Muted','NAudio.Wave.WaveExtensionMethods::ToMono','NAudio.Wave.WaveFileWriter::CreateWaveFile16']),
            dict(mono_argument_instructions=track_method['il'][mono_idx-2:mono_idx+1]),
            dict(type='OpenUtau.Core.Render.RenderEngine',method='RenderTracks',method_token=dry['token'],
                 absent_reads=['Fader','MixFx','UWavePart'])])
    add('UI solo/mute aggregation','IL_read_path_present_UI_scope',
        'App JudgeMuted按Solo→false、Mute→true、其它Solo→true，否则false；桥接无UI实例不能假定加载同样聚合',
        proof(app,'OpenUtau.App.ViewModels.TrackHeaderViewModel','JudgeMuted',[
            'OpenUtau.App.ViewModels.TrackHeaderViewModel::get_Solo',
            'OpenUtau.App.ViewModels.TrackHeaderViewModel::get_Mute','OpenUtau.Core.Ustx.UProject::get_SoloTrackExist']))
    add('MasterAdapter playback edge/readiness','IL_read_path_present',
        '本机HoldWhenUnready/3ms边沿fade存在；仅播放adapter，export不用；真实设备未播放',
        proof(core,'OpenUtau.Core.SignalChain.MasterAdapter','Read',[131,132,
            'OpenUtau.Core.SignalChain.MasterAdapter::get_HoldWhenUnready','OpenUtau.Core.SignalChain.MasterAdapter::set_Waited']))
    add('Windows NAudio device branch','IL_read_path_present_device_unknown',
        'App.Init含WASAPI Shared(0)/50ms和WaveOut/50ms/两buffers；live选用后端/设备/OS音量unknown',
        proof(app,'OpenUtau.App.NAudioOutput','Init',[
            'NAudio.Wave.WasapiOut::.ctor','NAudio.Wave.WaveOutEvent::.ctor',
            'NAudio.Wave.WaveOutEvent::set_DesiredLatency','NAudio.Wave.WaveOutEvent::set_NumberOfBuffers',50]))
    add('import sample rate conversion','IL_read_path_present',
        'GetStereoSamples/GetSamples含44100目标Wdl重采样；未进行新的文件解码',
        proof(core,'OpenUtau.Core.Format.Wave','GetStereoSamples',[44100,
            'NAudio.Wave.SampleProviders.WdlResamplingSampleProvider::.ctor']))
    for tname, fname, reader_type in [
        ('OpenUtau.Core.Util.Preferences+SerializablePreferences','DiffSingerVarianceLocalPitchPatch','OpenUtau.Core.DiffSinger.DsVariance'),
        ('OpenUtau.Core.Util.Preferences+SerializablePreferences','DiffSingerMergeNearbyPhrases','OpenUtau.Core.DiffSinger.DiffSingerRenderer')]:
        assert fname in {f['name'] for f in core[tname]['fields']}
        refs = [(tn,m,o) for tn,t in core.items() if tn.startswith(reader_type)
                for m in t['methods'] for o in m['il'] or [] if str(o['operand']).endswith('::'+fname)]
        assert refs, fname
        add(fname,'member_and_IL_read_present_execution_unknown',
            '偏好成员及选中读取者存在；不等于当前启用、所有模型兼容或旧实验使用该路径',
            [dict(type=tn,method=m['name'],method_token=m['token'],instruction=o) for tn,m,o in refs])
    pitch = method(core,'OpenUtau.Core.DiffSinger.DsPitch','AddPitchSamplingInputs')
    add('pitch sampling new branch','member_and_IL_present_execution_unknown',
        'AddPitchSamplingInputs/ComputePitchSpeedup成员存在；低于1步请求和非默认模型响应本轮未执行',
        dict(type='OpenUtau.Core.DiffSinger.DsPitch',method='AddPitchSamplingInputs',method_token=pitch['token']))
    add('wave trim/fade ticks','IL_read_path_present',
        'GetTrimmedSamples读skip/trim/fadein/fadeout并timeAxis换ms；PCM拷贝及逐帧增益路径存在，未解码新文件',
        proof(core,'OpenUtau.Core.Ustx.UWavePart','GetTrimmedSamples',[
            'OpenUtau.Core.Ustx.UWavePart::GetSkipMs','OpenUtau.Core.Ustx.UWavePart::GetTrimMs',
            'OpenUtau.Core.Ustx.UWavePart::fadein','OpenUtau.Core.Ustx.UWavePart::fadeout']))
    playback_refs = [(tn,m,o) for tn,t in core.items() if 'PlaybackManager' in tn
        for m in t['methods'] for o in m['il'] or []
        if any(x in str(o['operand']) for x in ['PlaybackMix::.ctor','get_LoopPlayback','MetronomeVolume','MetronomeHighFrequency','MetronomeLowFrequency'])]
    assert any('PlaybackMix::.ctor' in str(o['operand']) for _,_,o in playback_refs)
    assert any('MetronomeVolume' in str(o['operand']) for _,_,o in playback_refs)
    add('playback range/loop/metronome','selected_IL_read_paths_present',
        'PlayOrPause/Render及嵌套闭包含范围/loop、PlaybackMix overlay、节拍音量/频率读取；实际会话未知',
        [dict(type=tn,method=m['name'],method_token=m['token'],instruction=o) for tn,m,o in playback_refs])
    ui_refs = [(tn,m,o) for tn,t in app.items() if 'Views.MainWindow' in tn
        for m in t['methods'] for o in m['il'] or []
        if o['operand'] in ['OpenUtau.Core.PlaybackManager::RenderMixdown','OpenUtau.Core.PlaybackManager::RenderToFiles']]
    assert {'OpenUtau.Core.PlaybackManager::RenderMixdown','OpenUtau.Core.PlaybackManager::RenderToFiles'} <= {o['operand'] for _,_,o in ui_refs}
    add('UI WAV export command route','IL_call_paths_present',
        'App主窗口音频导出命令分别调用mixdown与分轨；未打开导出对话框或写音频',
        [dict(type=tn,method=m['name'],method_token=m['token'],instruction=o) for tn,m,o in ui_refs])
    add('cache mono16 writer','IL_path_present_not_all_renderer_routes',
        'WriteMono16Wav成员及44100/16/1 WaveFormat构造路径存在；仅此helper，不代表fresh诊断编码',
        proof(core,'OpenUtau.Core.Format.Wave','WriteMono16Wav',[44100,16,'NAudio.Wave.WaveFormat::.ctor']))
    skip_refs = [(tn,m,o) for tn,t in core.items() if 'Render.RenderEngine' in tn
        for m in t['methods'] for o in m['il'] or [] if str(o['operand']).endswith('::SkipRenderingMutedTracks')]
    assert skip_refs
    add('SkipRenderingMutedTracks','IL_read_path_present',
        'PrepareRequests筛选闭包读取该偏好；影响是否发起voice请求，输出Muted门仍另存在',
        [dict(type=tn,method=m['name'],method_token=m['token'],instruction=o) for tn,m,o in skip_refs])
    return dict(schema_version=1,date='2026-10-09',mode='offline_PE_metadata_and_IL_no_target_execution',
        bindings=bindings, rows=entries, all_local_paths_confirmed=False,
        live_preferences_read=False, models_executed=False, audio_read_or_written=False,
        scope='完整Core/App类型成员清单；仅所列方法IL静态核查。未证明所有分支/版本等价或任何听觉效果。')

def apply_review(rows, local):
    by_cap = {r['capability']:r for r in local['rows']}
    def assign(row, cap, support=None):
        e = by_cap[cap]
        row['local_evidence_refs'] = e['id']
        row['local_code_path_status'] = e['status']
        if support:
            row['current_support'] = support
    for r in rows:
        r['local_evidence_refs'] = ''
        if r['id']=='PARAM:C48.05':
            r['declared_or_code_limits']='冻结偏好103字段另列；未穷尽任意App/插件消费者'
            r['transform']='显示/会话、资源/运行、播放、编辑驱动分别登记；预设/网格真正写入关联具体控制行'
            r['current_support']='scoped_editor_review_complete_with_explicit_consumer_gaps'
            r['limitation']='导航汇总而非独立DSP参数；详见偏好审查和后续32条编辑/扩展项，未读消费者及live值unknown'
        if r['group_id']=='C47' and 'Agent functions' not in r['field']:
            assign(r,'expression graph / masked curves','installed_graph_or_masked_path_absent')
            if r['field'] in ['rpit','pito']:
                r['limitation'] = '上游masked声明与graph读取；本机缺类型/入口，不作为本机新pitch通道'
        if r['id']=='PARAM:C02.03':
            assign(r,'PitchPointShape.sp','installed_enum_and_helper_branch_present_nondefault_execution_unknown')
            r['transform']='io/sp通用helper同SinEasingInOut；l线性，i/o单侧easing；pitch spline上下文路径另核查'
            r['limitation']='sp枚举及helper已核查，非默认完整路径未执行；不从名称推断任意样条'
        if r['group_id'] in ['C43','C44','C45']:
            if r['field'].endswith(('EqEnabled','CompEnabled','ReverbEnabled')):
                assign(r,'MixFx independent module switches','installed_member_absent')
                r['limitation']='该独立模块开关仅冻结上游存在；本机只有整体Enabled'
            else:
                assign(r,'MixFx Enabled / parameter read path','installed_MixFx_read_path_present_nondefault_response_unknown')
                r['limitation']='本机整体MixFx读取路径存在；上游与本机独立开关/live刷新有差异，未做非默认输出验证'
        if r['id']=='PARAM:C46.01':
            assign(r,'MixFxApplyOnExportMixdown preference','declared_but_not_read_in_bound_export_path')
            r['transform']='字段声明默认true；已核查正常mixdown导出固定applyMixFx=true，无此偏好读取'
            r['limitation']='首批按声明推定导出开关的说法已修正；不把该字段列为当前有效出口开关'
        if r['id']=='PARAM:C47.04':
            r['transform']='具体31类型、参数、端口fallback已展开；本机graph类型缺失'
            r['limitation']='首批导航行保留；具体行追加稳定ID，不重复计成新独立声学通道'
        if r['id']=='PARAM:C46.11':
            r['transform']='UI mixdown固定WAV16/44100/stereo；分轨WAV16/44100/mono；详见追加入口；外部监听增益unknown'
            r['limitation']='原导航行不是DYN方法定义导出格式的证据；实际入口源码和本机IL已补'
            r['source_path']='OpenUtau.Core/PlaybackManager.cs'
            r['source_anchor']='WaveFileWriter.CreateWaveFile16(exportPath,'
            assign(r,'UI/bridge mixdown WAV path','selected_installed_IL_path_present_nondefault_execution_unknown')
        if r['group_id']=='C02' and r['id']!='PARAM:C02.03':
            r['limitation']='相对点线和PITD叠加；sp枚举/helper静态存在，非默认上下文路径未执行'
        if r['field']=='Preferences.DiffSingerVarianceLocalPitchPatch':
            assign(r,'DiffSingerVarianceLocalPitchPatch','member_and_IL_read_present_enabled_state_unknown')
        if r['field']=='Preferences.DiffSingerMergeNearbyPhrases':
            assign(r,'DiffSingerMergeNearbyPhrases','member_and_IL_read_present_enabled_state_unknown')
        if r['field']=='Preferences.DiffSingerStepsPitch':
            assign(r,'pitch sampling new branch','member_and_IL_present_nondefault_execution_unknown')
        if r['field'].startswith('tracks[].') and r['field'].split('.')[-1] in ['Volume','Pan']:
            assign(r,'track fader / pan law','installed_fader_output_path_checked_nondefault_response_unknown')
            r['transform']='详见新增track.volume/pan公式行；mixdown/播放读取，分轨export不经过fader'
            r['sampling_interpolation_clip']='输出逐交错sample增益/声像；模型发声条件不由此改变'
            r['limitation']='track字段不是每种出口共同作用；声像中心mono双声道每侧约-3.0103dB'
        if r['field'].endswith('.Mute') or r['field'].endswith('.Solo') or r['field'].startswith('UI mute/solo'):
            assign(r,'UI solo/mute aggregation','UI_derived_Muted_path_checked_bridge_context_separate')
        for prefix,cap in [
            ('track.volume','volume nonlinear low range / smoothing'),('fader.Scale','volume nonlinear low range / smoothing'),
            ('track.pan','track fader / pan law'),('mixdown PCM','UI/bridge mixdown WAV path'),
            ('mixdown applyMixFx','UI/bridge mixdown WAV path'),('track export PCM','track export dry mono path'),
            ('ExportAdapter','UI/bridge mixdown WAV path'),('wave import resampling','import sample rate conversion'),
            ('MasterAdapter','MasterAdapter playback edge/readiness'),('Preferences.UseSystemDefault','Windows NAudio device branch'),
            ('Preferences.PlaybackDevice','Windows NAudio device branch'),('NAudio playback','Windows NAudio device branch')]:
            if r['field'].startswith(prefix):
                assign(r,cap,'selected_installed_IL_path_present_nondefault_execution_unknown')
        for prefix,cap in [
            ('wave_parts[].relative_path','import sample rate conversion'),
            ('wave_parts[].skip/trim','wave trim/fade ticks'),('wave_parts[].fadein/fadeout','wave trim/fade ticks'),
            ('UI export ','UI WAV export command route'),('renderer cache encoding','cache mono16 writer'),
            ('playback tick/','playback range/loop/metronome'),('PlaybackManager.LoopPlayback','playback range/loop/metronome'),
            ('Preferences.Metronome','playback range/loop/metronome'),('Preferences.SkipRenderingMutedTracks','SkipRenderingMutedTracks')]:
            if r['field'].startswith(prefix):
                assign(r,cap,'selected_installed_IL_path_present_nondefault_execution_unknown')
