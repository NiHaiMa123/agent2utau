"""Append collective v04 voice-AB acceptance and narrowly update Skill methods."""
import copy,csv,json,os,subprocess,sys
from pathlib import Path
from assemble_lastpage_accepted_baseline_20261011 import ROOT,ENTRIES,load,save,ref,sha,check
from agent2utau.knowledge import collect_context,validate_context

PRIOR=ROOT/'runs/production/lastpage-v04-dynamic-envelope-20261014'
RUN=ROOT/'runs/research/lastpage-v04-acceptance-skill-20261014'
REPORT=ROOT/'docs/reports/lastpage'
KNOW=ROOT/'docs/knowledge/acoustic-manifestations-20261009'
SKILL=ROOT/'skills/singing-expression-editor'
INSTALLED=Path('C:/Users/Administrator/.codex/skills/singing-expression-editor')
FILES=['SKILL.md','references/loudness-and-high-note-comfort.md','references/local-acceptance-to-whole-song-phonation.md']
NAME='v04-DYN-acceptance-and-skill-20261014'
INDEX='table2-v04-DYN-accepted-index-20261014'
ID='RESP:LASTPAGE-V03-DYN-RECOVERY-01'

def prepare():
    assert not RUN.exists()
    seal=load(PRIOR/'completion-manifest.json');refs=seal['files']+seal['documents']+seal['entries']+seal['implementation']+seal['published']+[seal['tests']]
    check(refs)
    old=load(PRIOR/'protected-before.json')+refs+[ref(PRIOR/'completion-manifest.json')];check(old)
    mutable=ENTRIES+['docs/knowledge/acoustic-manifestations-20261009/active-knowledge-sources.json']+[(SKILL/p).relative_to(ROOT).as_posix() for p in FILES]
    protected=list({r['path']:r for r in old if r['path'] not in mutable}.values());RUN.mkdir(parents=True)
    save(RUN/'protected-before.json',protected)
    copies=[]
    for name in mutable:
        src=ROOT/name;p=RUN/'before'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(src.read_bytes());copies.append(dict(original=ref(src),snapshot=ref(p)))
    for relative in FILES:
        src=INSTALLED/relative;p=RUN/'before/installed-skill'/relative;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(src.read_bytes())
        assert sha(src)==sha(SKILL/relative);copies.append(dict(installed_original=dict(path=str(src),sha256=sha(src)),snapshot=ref(p)))
    save(RUN/'before/snapshot-manifest.json',copies)
    media=load(PRIOR/'evaluation/delivery-check.json');check(list(media['outputs'].values()))
    clips=media['AB_clips']
    for pair in clips:check([pair[k] for k in ['A','B','AB']])
    feedback=dict(date='2026-10-14',verbatim='可以，然后把这个经验记录到表中，以及更新skill',submissions=1,
        referent='v04 B in the immediately preceding three A→B voice comparisons, inferred from presentation and acceptance request',
        accepted_scope='Collective acceptance of presented voice-envelope revision at the three reported ranges',
        original_feedback_intervals_s=[[86,88],[183,190],[196,199]],presented_voice_pairs=clips,
        actual_changed_contexts=[11,22,23,25],accepted_project=media['outputs']['project'],
        full_vocal_artifact=media['outputs']['vocal'],full_song_listening_or_acceptance='not explicitly stated; do not add a full-song verdict',
        new_individual_word_labels=0,force_naturalness_texture_pitch_break_dimensions='not separately rated by this reply',
        model_phonation_regenerated=False,post_vocoder_output_envelope_locally_accepted=True,
        prior_H_G_I_negative_conditions_retained=True,remaining_ni224_lower_energy_observation_retained=True,
        source_unknown106_held=True,agent_heard=False,measurement_validated=False,general_rule_validated=False,
        skill_update_authorization='User explicitly requests updating Skill in this message',additional_generation_authorized_or_executed=False)
    save(RUN/'feedback/accepted.json',feedback)
    supplement=dict(record_id=ID,append_only_feedback=True,latest_acceptance=feedback,local_adoption=True,
        full_song_adoption=False,mechanism_claim='Finite native output-envelope acceptance; not a universal DYN force/texture rule',
        table1_refs=['ACO:L1','EVT:L2','PER:S1','PARAM:C10.01'],measurement_validated=False,general_rule_validated=False)
    save(REPORT/(NAME+'.json'),dict(status='v04_three_region_voice_envelope_accepted_skill_update_authorized',table2_supplement=supplement,
        original_execution=ref(REPORT/'v04-native-DYN-voice-recovery-20261014.json'),new_models=0,new_waveforms=0,new_metrics=0,agent_heard=False))
    (REPORT/(NAME+'.md')).write_text('''# v04人声包络接受与Skill更新

2026-10-14，用户：“可以，然后把这个经验记录到表中，以及更新skill”。绑定此前三组同公共增益纯人声A→B的v04 B、工程及音频SHA（见同名JSON），记录一次聚合接受；不拆成三次独立提交或25个逐字标签。接受1:26–1:28、3:03–3:10及3:16–3:19问题范围内的这版包络调整，没有单独补造整曲、发力/自然度/磨砂/破音各维度结论。

表2经验：当前声线、音高、音素和原始预测/波形固定时，采用有音乐目的的正向原生DYN承托可以成为人声音量调整的局部有效选择；让弱字得到承托，强字少加或保持，连接连续、句尾回收。四上下文的实际节点、剂量、支撑、318观察与原生/PCM技术结果仍由原执行报告绑定。旧H先削弱字核的阴性不能扩为“所有DYN都无效”，本次接受也不能扩为所有弱声都靠增益解决。

Skill只更新可复用方法：整曲换声线/音高/人工发声控制后复核当前全曲真实包络；用可靠元音核早中晚与短窗观察，区分原始弱声、原生DYN、音乐强弱与感知力度；按乐句设计承托/回收并保护强字与气口，原生包络和交付PCM一致；接受范围和阴性按原条件回填。具体曲名、时码、固定混合、节点和剂量不写入通用默认。

本轮明确授权更新并同步Skill，保留更新前仓库/安装版本快照。表1机制定义及measurement_validated不升级；39条表2来源行保留，接受作为新来源追加。旧工程、音频、作者、原技术报告/receipt/封存run保持。新生成/模型/检测器/数组解码/声学复测均0，Agent未听；单Agent，CI仅手动。整曲其余听感仍待完整评价，不自动开新批次。
''',encoding='utf8')
    idx=copy.deepcopy(load(KNOW/'table2-v04-DYN-delivery-index-20261014.json'));row=next(r for r in idx['rows'] if r['id']==ID)
    row.setdefault('feedback_sources',[]).append(ref(REPORT/(NAME+'.json')))
    row['latest_acceptance_record']=feedback;row['effective_current_status']='local_three_region_DYN_accepted; broader song verdict unknown'
    row['local_adoption']=True;row['full_song_adoption']=False
    idx.update(status='v04_three_region_voice_envelope_accepted',prior_index=ref(KNOW/'table2-v04-DYN-delivery-index-20261014.json'),generator=ref(Path(__file__)))
    save(KNOW/(INDEX+'.json'),idx)
    with (KNOW/(INDEX+'.csv')).open('x',encoding='utf-8-sig',newline='') as f:
        rows=[dict(id=r['id'],source_path=r['source']['path'],source_sha256=r['source']['sha256'],
            latest_local_acceptance=True if r['id']==ID else '',full_song_accepted=False,measurement_validated=False) for r in idx['rows']]
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    (KNOW/(INDEX+'.md')).write_text('# v04包络接受索引\n\n39行保持，DYN响应行新增一次三范围聚合接受。旧技术、剂量、阴性、原始source_record均保持，不刷新历史报告；最新接受见同名JSON与公开报告。表1定义/验证状态不变。\n',encoding='utf8')
    registry=load(KNOW/'active-knowledge-sources.json');registry['response_indices']=[(KNOW/(INDEX+'.json')).relative_to(ROOT).as_posix()]
    (KNOW/'active-knowledge-sources.json').write_text(json.dumps(registry,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('v04 collective acceptance appended;39 rows preserved;Skill versions snapshotted.',flush=True)

def finish():
    assert not (RUN/'completion-manifest.json').exists();check(load(RUN/'protected-before.json'))
    updated=[]
    for relative in FILES:
        assert sha(SKILL/relative)==sha(INSTALLED/relative)
        updated.append(dict(repository=ref(SKILL/relative),installed=dict(path=str(INSTALLED/relative),sha256=sha(INSTALLED/relative)),
            old_snapshot=ref(RUN/'before/skills/singing-expression-editor'/relative)))
    save(RUN/'evaluation/skill-sync.json',dict(status='passed',files=updated,method_only=True,no_song_numbers_as_defaults=True))
    packet=collect_context(['ACO:L1','EVT:L2','PER:S1'],['PARAM:C10.01'],[ID,'RESP:LASTPAGE-OWN-LI-DYN-LAYERS-01'])
    record=next(r for r in packet['records'] if r['id']==ID)['record'];assert record['latest_acceptance_record']['verbatim']==load(RUN/'feedback/accepted.json')['verbatim']
    original=load(KNOW/'table2-v04-DYN-delivery-index-20261014.json');current=load(KNOW/(INDEX+'.json'))
    assert len(original['rows'])==len(current['rows'])==39
    for a,b in zip(original['rows'],current['rows']):
        assert a['id']==b['id'] and a['source']==b['source'] and a.get('source_record')==b.get('source_record')
        if a['id']!=ID:assert a==b
    decisions=[dict(id=r['id'],decision='reject' if r['id']=='RESP:LASTPAGE-OWN-LI-DYN-LAYERS-01' else 'use',
        reason='Retain rejected early weakening shape; use latest accepted finite positive phrase-envelope method and definitions.',
        condition_match='Only the presented three regions accepted; actual conditions and output support remain bound.',
        limitations='No complete-song or force/texture subdimension verdict, universal gain dose or measurement truth.') for r in packet['records']]
    save(RUN/'evaluation/knowledge-roundtrip.json',dict(packet=packet,receipt=validate_context(packet,decisions),old_rows_and_source_records_exact=True))
    env=dict(os.environ);env['PYTHONUTF8']='1';env['PYTHONIOENCODING']='utf-8'
    validator=Path('C:/Users/Administrator/.codex/skills/.system/skill-creator/scripts/quick_validate.py')
    outputs=[]
    for key,cmd in [('repository-skill',[sys.executable,'-X','utf8',str(validator),str(SKILL)]),
                    ('installed-skill',[sys.executable,'-X','utf8',str(validator),str(INSTALLED)]),
                    ('repository-gate',[sys.executable,str(ROOT/'tools/repository/check_repository.py'),'--worktree'])]:
        p=subprocess.run(cmd,cwd=ROOT,env=env,capture_output=True,encoding='utf8');log=RUN/'logs'/(key+'.log');log.parent.mkdir(parents=True,exist_ok=True);log.write_text(p.stdout+p.stderr,encoding='utf8');assert p.returncode==0,(key,p.stderr)
        outputs.append(dict(check=key,passed=True,log=ref(log)))
    save(RUN/'evaluation/validation.json',dict(checks=outputs,new_runtime_tests='not needed: documentation/feedback-only; existing164 execution tests preserved',new_audio_or_model_execution=0))
    save(REPORT/(NAME+'-audit.json'),dict(status='passed',feedback=ref(RUN/'feedback/accepted.json'),source_index=ref(KNOW/(INDEX+'.json')),
        knowledge_roundtrip=ref(RUN/'evaluation/knowledge-roundtrip.json'),skill_sync=ref(RUN/'evaluation/skill-sync.json'),validation=ref(RUN/'evaluation/validation.json'),
        previous_seal=ref(PRIOR/'completion-manifest.json'),originals_SHA_exact=True,old_source_records_exact=True,updated_skill_files=updated,
        scope='append acceptance and method only',new_audio=0,new_models=0,new_measurements=0,new_user_submissions=1,general_rule_validated=False))
    status='当前状态v04_three_region_DYN_accepted_recorded_skill_updated：2026-10-14用户“可以，然后把这个经验记录到表中，以及更新skill”，记录为此前三组纯人声A/B的v04包络聚合接受，一次反馈、不补逐字/分维度或整曲验收。表2DYN响应追加原话及三组音频/工程SHA，39行及原技术/阴性/unknown保持；DYN承托弱字、强字少加/保持、句内连续和回收写入Skill方法，并同步安装版。具体时码、节点、剂量留在表2，不设通用默认；表1/measurement_validated与通用规律不升级。旧v03/v04音频工程/封存/作者保持，本轮新模型/音频/测量0；Agent未听，整曲其它区域仍待完整评价。单Agent/CI仅手动。'
    for name in ENTRIES:
        f=ROOT/name;lines=f.read_text(encoding='utf8').splitlines(keepends=True);found=0;link=Path(os.path.relpath(REPORT/(NAME+'.md'),f.parent)).as_posix()
        for i,line in enumerate(lines):
            if '当前状态v03_volume_feedback_recorded_native_DYN_v04_delivered_pending_listening：' in line:
                lines[i]=('- ' if line.startswith('- ') else '')+status+f' 见[v04接受与方法更新]({link})。\n';found+=1
            if line.startswith('下一工作进入逐首更新，先《最后一页》：'):
                lines[i]='下一工作进入逐首更新，先《最后一页》：v04三处人声包络已获聚合接受并回填表2，Skill方法已更新同步；保留这版，后续接完整整曲的其余反馈。未提出新问题时不自动重生成、加剂量或开下一首。\n'
        assert found==1,name;f.write_text(''.join(lines),encoding='utf8')
    check(load(RUN/'protected-before.json'))
    docs=[REPORT/(NAME+s) for s in ['.md','.json','-audit.json']]+[KNOW/(INDEX+s) for s in ['.md','.json','.csv']]+[KNOW/'active-knowledge-sources.json']
    save(RUN/'completion-manifest.json',dict(status='accepted_feedback_and_skill_update_complete',files=[ref(p) for p in sorted(RUN.rglob('*')) if p.is_file()],
        documents=[ref(p) for p in docs],entries=[ref(ROOT/n) for n in ENTRIES],implementation=ref(Path(__file__)),
        skill_files=[ref(SKILL/p) for p in FILES],installed_skill_files=[dict(path=str(INSTALLED/p),sha256=sha(INSTALLED/p)) for p in FILES],
        protected_count=len(load(RUN/'protected-before.json')),old_song_artifacts_unchanged=True,new_audio_or_models=0,new_measurements=0,new_feedback=1,general_rule_validated=False))
    print('v04 acceptance and Skill update complete;39 prior source records exact;old audio/project SHA held.',flush=True)

if __name__=='__main__':{'prepare':prepare,'finish':finish}[sys.argv[1]]()
