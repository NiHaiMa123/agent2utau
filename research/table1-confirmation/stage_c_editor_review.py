"""Finite editor/preference review; source references are not execution tests."""
import hashlib
import json
import re
from collections import Counter

PREFS = 'OpenUtau.Core/Util/Preferences.cs'
PRESETS = 'OpenUtau.Core/Util/NotePresets.cs'
NOTES = 'OpenUtau/ViewModels/NotesViewModel.cs'
STATES = 'OpenUtau/Views/NoteEditStates.cs'
EXP = 'OpenUtau.Core/Commands/ExpCommands.cs'
NOTE = 'OpenUtau.Core/Ustx/UNote.cs'
DEFAULTS = 'OpenUtau/ViewModels/NoteDefaultsViewModel.cs'
FX = 'OpenUtau/ViewModels/MixFxViewModel.cs'
HIFI = 'OpenUtau.Core/Classic/Hifisampler/HifiSampler.cs'

# Explicit authored classification. Completeness is checked against declarations.
# "display" is an intended UI role, not a proof of absence of every DSP reader.
CLASSES = {
    'display_or_session': '''MainWindowSize PianorollWindowSize UndoLimit ShowPrefs ShowTips
        ThemeName DegreeStyle UseTrackColor Language SortingOrder RecentFiles SkipUpdate
        RecentSingers FavoriteSingers RecentPhonemizers PlayPosMarkerMargin PlaybackAutoScroll
        ReverseLogOrder ShowPortrait ShowIcon ShowGhostNotes NoteHoverGlow ReduceAnimations
        ShowPlaybackNoteHighlight ShowPlaybackNoteBounce ShowVibrato ShowPitch ShowFinalPitch
        ShowWaveform ShowPhoneme ShowExpressions ShowPhonemizerTags ShowNoteParams Beta Channel
        RememberMid RememberUst RememberVsqx UseWayland RecentOpenSingerDirectory
        RecentOpenProjectDirectory RecoveryPath DetachPianoRoll DiffSingerLangCodeHide''',
    'resource_or_runtime': '''SingerSearchPaths ClearCacheOnQuit PreRender NumRenderThreads
        DefaultRenderer WorldlineR OnnxRunner OnnxGpu DiffSingerTensorCache AdditionalSingerPath
        InstallToAdditionalSingersPath LoadDeepFolderSinger PreferCommaSeparator ResamplerLogging
        DefaultResamplers DefaultWavtools OtoEditor VLabelerPath SetParamPath WinePath
        VoicebankPublishUseIgnore VoicebankPublishIgnores''',
    'render_or_segmentation': '''MergePhrasesSec DiffSingerDepth DiffSingerSteps
        DiffSingerStepsVariance DiffSingerStepsPitch DiffSingerVarianceLocalPitchPatch
        DiffSingerMergeNearbyPhrases SkipRenderingMutedTracks''',
    'playback_only': '''PlaybackDevice PlaybackDeviceNumber PlaybackDeviceIndex AudioBackEnd
        UseSystemDefaultAudioDevice Metronome MetronomeVolume MetronomeHighFrequency
        MetronomeLowFrequency LockStartTime PlayTone''',
    'editing_driver_or_scope': '''SingerPhonemizers EditTool RealTimePitchGeneration
        RealTimePitchMode LyricHelper LyricsHelperBrackets DefaultSnapCurve PhoneticAssistant
        LockUnselectedNotesPitch LockUnselectedNotesVibrato LockUnselectedNotesExpressions
        LyricLivePreview LyricApplySelectionOnly''',
    'observation_backend': 'GameBackend',
    'fx_preset_library': 'MixFxUserPresets',
    'declared_but_no_checked_export_reader': 'MixFxApplyOnExportMixdown',
    'legacy_migration': 'Theme PreferPortAudio',
}
NOTES_BY_CLASS = {
    'display_or_session': '显示/会话意图；已读引用单列。未穷尽整个App所有reader，不据名称证明零声学影响。',
    'resource_or_runtime': '资源选择/安装/缓存/执行环境可影响所用实现或复现；不是连续听感剂量。',
    'render_or_segmentation': '可能改变预测输入、分句或请求；沿用具体控制行，非默认执行未全验证。',
    'playback_only': '监听/节拍/预览或播放边界；不自动写入导出或模型发声参数。',
    'editing_driver_or_scope': '编辑行为/范围候选；命令真正写入的字段单列，无reader时保留unknown。',
    'observation_backend': 'GAME观测推理后端；不能作歌声渲染音色参数。',
    'fx_preset_library': '命名完整FX快照库；选用后写track.MixFx，库本身不作为独立DSP通道。',
    'declared_but_no_checked_export_reader': 'UI可保存，但已核查mixdown固定applyMixFx=true；不能当有效出口开关。',
    'legacy_migration': '旧字段迁移至ThemeName/AudioBackEnd；不当成并列当前旋钮。',
}


def editor_controls():
    rows = []
    def add(g, field, unit, default, limits, transform, src, anchor, *, other=False):
        rows.append(dict(group_id=f'C{g:02}', field=field, storage_unit=unit,
            default_or_baseline=default, declared_or_code_limits=limits, transform=transform,
            source_path=src, source_anchor=anchor,
            scope='other_engine' if other else 'editing_metadata',
            current_support='frozen_source_reader_checked_local_nondefault_execution_unverified',
            stage='external_engine_contract' if other else 'editor_to_score_or_curve_or_fx',
            condition='显式选定实现/配置，当前DiffSinger不采用此路径' if other else '用户执行编辑/新建/预设应用；不是读取工程时自动改写',
            sampling_interpolation_clip='按具体字段与命令；声明默认与运行值分开',
            recalculate='按实际写入的音符/音素/曲线重建时钟、目标及相关预测渲染；FX仅后处理',
            limitation='仅冻结源码和已读本机成员；未执行操作/插件/模型，未验证剂量或听觉方向',
            abbreviation='', published_descriptor_requested=False,
            local_code_path_status='upstream_command_read_or_write_only_local_inventory_separate',
            dose_or_auditory_direction_validated=False))
    add(23,'NotePresets.DefaultLyric → notes[].lyric','字符串','a','字典/音素器另约束',
        'UNote字段初始化读DefaultLyric；不是只在界面显示',NOTE,'public string lyric = NotePresets.Default.DefaultLyric;')
    add(24,'NotePresets.SplittedLyric → split note lyric','字符串','+','音素器延音语义另查',
        '切分新音符ChangeNoteLyricCommand写SplittedLyric；不等于自动保证连音',STATES,'new ChangeNoteLyricCommand(part, newNote, NotePresets.Default.SplittedLyric)')
    for field, default, meaning, anchor in [
        ('PortamentoStart','-40','点X=start/start+length，相对音符ms','int start = NotePresets.Default.DefaultPortamento.PortamentoStart;'),
        ('PortamentoLength','80','跨度ms；不是tick或发声进入时间','int length = NotePresets.Default.DefaultPortamento.PortamentoLength;')]:
        add(2,'NotePresets.DefaultPortamento.'+field+' → pitch.data[].x','ms',default,'此reader无独立clamp',
            'UProject.CreateNote生成两点(start,0)、(start+length,0)；'+meaning,
            'OpenUtau.Core/Ustx/UProject.cs',anchor)
    add(2,'NotePresets.DefaultPitchShape → pitch.data[].shape','枚举','io','io/l/i/o/sp；本机差异见LOCAL:03',
        '新建/ResetPitchPoints读shape；新插入pitch point也读；不是修改已有所有段',EXP,'var shape = NotePresets.Default.DefaultPitchShape;')
    add(2,'ResetPitchPointsCommand → notes[].pitch','两点/UPitch','当前默认portamento/shape','替换原note.pitch；可undo',
        '新UPitch两点替换；不是仅清显示缓存，也不清PITD',EXP,'public override void Execute() => Note.pitch = newPitch;')
    add(2,'NotePresets.PortamentoPresets[].PitchPoints','PitchPoint数组','空；内置Standard/Fast/Slow/Snap','命名库/用户数组；非所有调用读取',
        '数组构造器从首尾X导出int start/length；已核查CreateNote/Reset只读start/length，不直接复制PitchPoints',PRESETS,'public PortamentoPreset(string name, List<PitchPoint>points)')
    for name, target, unit, default, limits in [
        ('VibratoLength','length','音符时长%','75','[0,100]；UVibrato新对象_length默认为0'),
        ('VibratoPeriod','period','ms','175','[5,500]'),
        ('VibratoDepth','depth','cents','25','[5,200]'),
        ('VibratoIn','in','颤音长度%','10','[0,100]且in+out<=100'),
        ('VibratoOut','out','颤音长度%','10','[0,100]且in+out<=100'),
        ('VibratoShift','shift','周期%','0','[0,100]'),
        ('VibratoDrift','drift','depth比例%','0','[-100,100]'),
        ('VibratoVolLink','vol_link','%','0','[-100,100]')]:
        group = {'length':4,'period':5,'depth':6,'in':7,'out':7,'shift':8,'drift':8,'vol_link':9}[target]
        add(group,'NotePresets.DefaultVibrato.'+name+' → vibrato.'+target,unit,default,limits,
            '默认设置订阅clamp后保存；UVibrato初始化读对应字段；length仅toggle/auto时写，预设75不等于所有音符自动75',
            DEFAULTS,'NotePresets.Default.DefaultVibrato.'+name+' =')
    for name,default,tr,anchor in [
        ('AutoVibratoToggle','false','启用且duration>=阈值时Resize写默认length；所读Resize/ResetVibratos否则写0','if (NotePresets.Default.AutoVibratoToggle && note.duration >= NotePresets.Default.AutoVibratoNoteDuration)'),
        ('AutoVibratoNoteDuration','481 ticks','阈值按duration ticks；UI保存(int)max(10,value)，非481ms','NotePresets.Default.AutoVibratoNoteDuration = (int)Math.Max(10, autoVibratoNoteLength);')]:
        add(4,'NotePresets.'+name,'bool/ticks',default,'门控/阈值，不新增颤音波形通道',tr,
            STATES if name=='AutoVibratoToggle' else DEFAULTS,anchor)
    add(22,'NotesViewModel.SnapDiv/IsSnapOn → note create position/duration','分母/ticks','userSnapDiv=-2；自动div','snapUnit=resolution*4/SnapDiv（整数除法）',
        'UpdateSnapDiv自动模式按minTicklineWidth/TickWidth选择div，缩放影响后续网格不即时改谱；AddNote位置固定floor，即使IsSnapOn=false；长度lastLength或snapUnit/15',NOTES,'int snappedTick = (int)Math.Floor((double)tick / snapUnit) * snapUnit;')
    add(22,'grid note move/resize → position/duration','ticks','编辑时选择','开启吸附时移动floor；结束点floor+1格；最短snapUnit/15',
        'MoveNoteCommand/ResizeNoteCommand写谱面；不同手势/量化取整不等价',STATES,'newEnd = (int)Math.Floor((double)newEnd / snapUnit + 1) * snapUnit;')
    add(22,'QuantizeNotes.quantize → position/duration','ticks','调用者传入','非零正网格需调用者保证；Math.Round默认ties-to-even',
        '分别Round(pos/q)与Round(end/q)，Move/Resize写入；选择为空用全part',
        'OpenUtau.Core/Editing/NoteBatchEdits.cs','int newPos = (int)Math.Round(1.0 * pos / quantize) * quantize;')
    add(48,'Preferences.DefaultSnapCurve → selection start','bool','true','只确认CurveSelectionState.Begin的起点门控',
        'Begin在DefaultSnapCurve && IsSnapOn时floor；Update仅IsSnapOn；此操作选范围，不直接写curve值',STATES,'if (Preferences.Default.DefaultSnapCurve) {')
    add(48,'Preferences.LockUnselectedNotesExpressions → phone expression edit scope','bool','true','选择非空且phone.Parent不在选择内则跳过',
        '限制所写音素表达对象；不在渲染端冻结声学值',STATES,'if (Preferences.Default.LockUnselectedNotesExpressions && notesVm.Selection.Count > 0')
    add(48,'Preferences.LockUnselectedNotesPitch/LockUnselectedNotesVibrato','bool','true/true','ViewModel getters存在；完整手势调用未穷尽',
        'LockPitchPoints/LockVibrato读取偏好；不是PITD/颤音值；未核查consumer不宣称全部手势受限',
        'OpenUtau/ViewModels/PianoRollViewModel.cs','public bool LockPitchPoints { get => Preferences.Default.LockUnselectedNotesPitch; }')
    add(48,'Preferences.EditTool.BaseTool/PenToolVariation/OverwritePitch','整数/bool','1/0/false','CurrentTool BaseTool=1选Pen/PenPlus；其它BaseTool*10',
        '编辑工具派生选择；最终命令写已有note/curve，工具消费范围未穷尽；不独立创造DSP通道',
        'OpenUtau.Core/Util/EditTool.cs','public EditTools CurrentTool')
    add(48,'Preferences.RealTimePitchMode / legacy migration','枚举','Off=0','Normal=1/Fast=2；非法重置Off',
        'legacy RealTimePitchGeneration且Off迁移Normal，然后清legacy；UI保存模式不等于该偏好自身写PITD',PREFS,'public void MigrateRealTimePitchMode()')
    add(48,'Preferences.LyricLivePreview/LyricApplySelectionOnly','bool','true/true','所读21份新源码未见consumer；仅声明不确认实际作用',
        '保持declared_only；不按名称补造实时写入/选择限制',PREFS,'public bool LyricLivePreview = true;')
    add(43,'FX preset apply/live preview → track.MixFx','UMixFx快照','当前track/所选preset','BuildUMixFx全rack；Revert还原original；Apply保留并Save偏好',
        'Changed替换track.MixFx引用；命名preset加载具体数值，不是仅EqPreset名字触发DSP；本机三开关/WrapLive缺失另栏',FX,'Changed.Subscribe(_ => {')
    add(35,'ResamplerManifest.expressions/expressionFilter','字典/bool','empty/false','键ToLower分组取首；filter=false全部允许',
        'ExeResampler.SupportsFlag放行不证明外部exe解析或有效；需绑定所选exe SHA与同名yaml才登记任意flags',
        'OpenUtau.Core/Classic/ExeResampler.cs','if(Manifest == null || !Manifest.expressionFilter)',other=True)
    add(38,'ENUNU extensions.styles / style_format','自定义键/descriptor/format','empty','styles name/type/min/max/default_value/flag；format/index',
        '按enuconfig/config解析；reader仅接字符串innerValue并TryParse；无所选ENUNU声库不创造键名/范围/效果',
        'OpenUtau.Core/Enunu/EnunuConfig.cs','private void ParseEnunuStyles(',other=True)
    for flag,default,unit,tr,anchor in [
        ('e','不存在','存在旗标','Has(e)传HifiNoteTiming loop；数值不是读取点','consonant, cutoff, length, flags.Has("e"))'),
        ('A','0','整数clip[-100,100]','pitchRender梯度d生成5^(1e-4*A*d)后时间插值乘render；非听感方向','int aFlag = flags.Get("A") ?? 0;'),
        ('P','86','整数','kept窗口peak调用Worldline.ResamplerAutoGain；0旁路，不等于标准感知响度归一','int peakComp = flags.Get("P") ?? 86;')]:
        add(31 if flag=='P' else 35,'hifisampler flag '+flag,unit,default,'HifiFlags同名取首次；仅本轮选定readers，不是所有旗标',tr,HIFI,anchor,other=True)
    return rows


def preference_review(source_roots, source_hashes, commit, metadata_dir, controls):
    text = (source_roots[PREFS] / PREFS).read_text(encoding='utf-8')
    body = text.split('public class SerializablePreferences {',1)[1].split('public void MigrateRealTimePitchMode()',1)[0]
    declarations = list(re.finditer(r'public ([\w?<>, ]+) (\w+)\s*(?:=\s*([^;]+))?;', body))
    categories = {name:k for k,v in CLASSES.items() for name in v.split()}
    assert sum(len(v.split()) for v in CLASSES.values()) == len(categories)
    assert {m[2] for m in declarations} == set(categories)
    raw = json.loads((metadata_dir / 'core-metadata.json').read_text(encoding='utf-8'))
    types = {t['name']:t for t in raw['types']}
    local_fields = {f['name'] for f in types['OpenUtau.Core.Util.Preferences+SerializablePreferences']['fields']}
    rows = []
    for m in declarations:
        name = m[2]
        declaration = m[0]
        line = text[:text.index(declaration)].count('\n')+1
        refs = []
        pattern = re.compile(r'Preferences\.Default\.'+name+r'\b')
        for path,root in sorted(source_roots.items()):
            for n,ln in enumerate((root / path).read_text(encoding='utf-8').splitlines(),1):
                if pattern.search(ln):
                    refs.append(dict(path=path,line=n,source_sha256=source_hashes[path],snippet=ln.strip()))
        default = m[3].strip() if m[3] else ('null' if '?' in m[1] or m[1] not in ['int','uint','float','double','bool'] else 'false' if m[1]=='bool' else '0')
        if name=='VoicebankPublishIgnores':
            default = 'C# raw string literal; exact contents bound by source SHA'
        rows.append(dict(id=f'PREF:{len(rows)+1:03}',field=name,type=m[1],
            upstream_initializer_or_language_default=default,category=categories[name],
            role_and_boundary=NOTES_BY_CLASS[categories[name]],
            declaration_path=PREFS,declaration_line=line,source_sha256=source_hashes[PREFS],
            source_url=f'https://github.com/openutau/OpenUtau/blob/{commit}/{PREFS}#L{line}',
            bound_core_field_status='present_not_reader_execution' if name in local_fields else 'absent_in_complete_bound_core_type',
            checked_reference_sites=refs,reference_role='lexical_reference_not_read_write_or_branch_execution_proof',
            control_refs=[r['id'] for r in controls if re.search(r'\b'+name+r'\b',r['field'])],
            live_value='not_read',auditory_effect_validated=False))
    nested = []
    for typename,fields in [
        ('WindowSize',[('Width','1200'),('Height','650'),('PositionX','null'),('PositionY','null'),('State','0')]),
        ('EditTool',[('BaseTool','1'),('PenToolVariation','0'),('OverwritePitch','false')])]:
        path = f'OpenUtau.Core/Util/{typename}.cs'
        source = (source_roots[path] / path).read_text(encoding='utf-8')
        actual = set(re.findall(r'public [\w?]+ (\w+) \{ get; set; \}',source))
        assert actual == {k for k,v in fields}
        t = types[f'OpenUtau.Core.Util.{typename}']
        methods = {m['name'] for m in t['methods']}
        for field,default in fields:
            line = next(n for n,s in enumerate(source.splitlines(),1) if f' {field} {{ get; set; }}' in s)
            nested.append(dict(field=f'{typename}.{field}',upstream_default=default,source_path=path,
                source_line=line,source_sha256=source_hashes[path],
                bound_core_property_status='present_not_executed' if 'get_'+field in methods else 'absent',
                role='window_state' if typename=='WindowSize' else 'editor_driver',live_value='not_read'))
    return dict(schema_version=1,status='reviewed_with_explicit_gaps',upstream_commit=commit,
        scope='All SerializablePreferences public fields at fixed commit plus WindowSize/EditTool serialized properties; reference search only in explicit frozen sources',
        declaration_count=len(rows),all_scoped_declarations_classified=True,rows=rows,nested_properties=nested,
        category_counts=dict(Counter(r['category'] for r in rows)),local_core_sha256=raw['sha256'],
        metadata_sha256=hashlib.sha256((metadata_dir / 'core-metadata.json').read_bytes()).hexdigest(),
        all_consumers_or_plugins_enumerated=False,live_preferences_read=False,
        no_new_audio_or_labels=True)


def report(review, rows):
    result = ['', '## 编辑/预设与纯UI的有限审查', '',
        f'冻结SerializablePreferences的{review["declaration_count"]}个public字段逐项分类，WindowSize/EditTool另8个序列化属性见[偏好JSON](editor-preferences-review.json)及[CSV](editor-preferences-review.csv)。保留声明默认、绑定Core成员存在/缺失、已读源码引用和具体控制链接。引用搜索只覆盖这次显式冻结源码；一个字段声明/引用存在不等于分支执行，也不证明所有App消费者已穷尽。未读取本机live偏好。', '',
        '| 编辑入口 | 实际写入与限制 |', '|---|---|',
        '| 滑音预设/重置 | CreateNote/Reset生成(start,0)、(start+length,0)两点；start/length为ms。自定义PitchPoints库存在，但这两个reader只读start/length。 |',
        '| 颤音默认/自动启用 | period/depth/in/out/shift/drift/vol_link初始化读默认，UVibrato新对象length仍0；toggle/resize/reset才按默认length或auto门控写。481阈值是ticks。 |',
        '| 网格新建/拖动/批量量化 | 写position/duration；不同操作floor、floor+1与Math.Round不等价。所读AddNote位置即使关闭IsSnapOn仍floor；不能概括为关闭就全自由。 |',
        '| DefaultSnapCurve | 所读reader控制选择起点；Update只读IsSnapOn。没有证据说该偏好让所有曲线点写入吸附。 |',
        '| 选择锁/编辑工具 | 限制对象/选择手势；下游写已有note/curve/phone值，不新增DSP通道。完整手势及未读consumer保留unknown。 |',
        '| FX命名预设 | UI BuildUMixFx/Changed/Apply写track.MixFx，Revert还原；具体值与名字分开。本机缺新三开关/WrapLive，不能声称上游live DSP实际支持。 |', '',
        'LyricLivePreview/LyricApplySelectionOnly在所读源码中只有声明，保持未确认；RealTimePitchMode确认迁移/保存，不凭开关名称宣称自动写PITD。纯显示/会话项按角色单列，资源/后端/分句/播放项不会混成“纯UI无声学影响”。', '',
        '## 第三方扩展的范围边界', '',
        '本轮只登记冻结上游ExeResampler/ResamplerManifest、ENUNU styles/style_format契约和hifisampler的选定e/A/P读取点。当前声库仍是已绑定DiffSinger/Yousa，未选择/执行其它引擎或外部exe。', '',
        '- resampler manifest的expressions默认空、expressionFilter=false；键转小写分组取首。SupportsFlag全放行只表示允许传入，不能证明外部程序解析或旗标有效。外部集合须绑定具体exe SHA/同名yaml及reader，不穷尽未来插件。',
        '- ENUNU键名/范围来自所选配置；styles含name/type/min/max/default_value/flag，style_format含format/index。parser仅接所读字符串值，未绑定声库不造默认自定义键。',
        '- hifisampler本身SupportsFlag返回true；本轮额外确认e存在性、A默认0/clip±100的pitch梯度增益、P默认86/0旁路auto gain。其它路径不因“支持”返回值成为确认；当前DiffSinger不采用这些参数。', '',
        '## C收口与试听衔接', '',
        'C现在以reviewed_with_explicit_gaps收口：48入口均有具体项/状态，固定节点、偏好与选定扩展接口的审查范围明确；all_controls_enumerated与all_local_paths_confirmed仍false。未验证的本机非默认执行、开放插件、设备呈现及声音效果逐项保留，不通过升级安装或新合成消除unknown。下一步D确认观测协议，再在E核对已有用户标签/覆盖；新的因果试听按后续表2冻结设计推进。没有人工试听就不确认可感知差别、改善或自然度。', '']
    return result
