"""Append user voice-volume feedback, inspect all current native vowel envelopes."""
import copy,csv,json,math,sys
from pathlib import Path
import numpy as np
import soundfile as sf
from assemble_lastpage_accepted_baseline_20261011 import ROOT,ENTRIES,load,save,ref,sha,check
from agent2utau.knowledge import collect_context,check_plan_knowledge

V03=ROOT/'runs/production/lastpage-skill-whole-song-20261013'
QA=ROOT/'runs/research/lastpage-whole-song-v03-delivery-audit-20261014'
BASE=ROOT/'runs/lastpage_loudness_skill_v02_20261007'
RUN=ROOT/'runs/production/lastpage-v04-dynamic-envelope-20261014'
KNOW=ROOT/'docs/knowledge/acoustic-manifestations-20261009'
REPORT=ROOT/'docs/reports/lastpage'
NAME='v03-voice-volume-feedback-20261014'
INDEX='table2-v03-volume-feedback-index-20261014'
ID='RESP:LASTPAGE-J-METHOD-WHOLE-SONG-01'

def prepare():
    assert not RUN.exists()
    q=load(QA/'completion-manifest.json');main=load(V03/'completion-manifest.json')
    refs=q['files']+q['documents']+q['entries']+[q['implementation']]+q['previous_data_unchanged']+[q['previous_original_completion_manifest']]
    check(refs)
    original=load(V03/'protected-before.json')+refs+[ref(QA/'completion-manifest.json')]
    # Earlier mutable entry/registry identities are documented in snapshots.
    mutable=ENTRIES+['docs/knowledge/acoustic-manifestations-20261009/active-knowledge-sources.json']
    protected=list({r['path']:r for r in original if r['path'] not in mutable}.values());check(protected)
    RUN.mkdir(parents=True);save(RUN/'protected-before.json',protected)
    for name in mutable:
        p=RUN/'before'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((ROOT/name).read_bytes())
    text='1:26-1:28，声音突然变小。3:03-3:10，副歌强度没顶上去，声音相对变小，这里应该是最有情绪的时候。3:16-3:19，也是声音变小。也就是现在音量控制还是有不到位的地方'
    feedback=dict(date='2026-10-14',submissions=1,verbatim=text,
        clarification_verbatim='就是人声小了，和bgm，混音这些没关系',
        problem_scope='Voice itself; volume/prominence and emotional chorus intensity. BGM is not a diagnosis or adjustment target.',
        heard_exact_player='not specified; user identifies the vocal problem rather than choosing mix/vocal player',
        preceding_v03_vocal=ref(V03/'delivery/lastpage_J_method_whole_song_v03_vocal.wav'),
        preceding_v03_mix=ref(V03/'delivery/lastpage_J_method_whole_song_v03_mix.wav'),
        intervals=[dict(seconds=[86,88],label='声音突然变小'),dict(seconds=[183,190],label='副歌强度没顶上去，声音相对变小；这里应该是最有情绪的时候'),dict(seconds=[196,199],label='声音变小')],
        newly_named_word_labels=0,full_song_accepted=False,prior_J_local_acceptance_retained=True,
        prior_bao_C_local_acceptance_retained=True,force_vs_level_mechanism='unknown pending current observations and new listening',
        agent_heard=False,measurement_validated=False,general_rule_validated=False)
    save(RUN/'feedback/v03-volume.json',feedback)
    save(REPORT/(NAME+'.json'),dict(status='v03_vocal_volume_issues_recorded',table2_supplement=dict(record_id=ID,append_only_feedback=True,latest_voice_volume_feedback=feedback)))
    (REPORT/(NAME+'.md')).write_text(f'''# v03人声音量与副歌力度反馈

2026-10-14，用户：

> {text}

进一步明确：“{feedback['clarification_verbatim']}”。记录为一条整曲反馈、三个时间范围；没有逐字命名，不据此给窗口所有字补负标签。时码以此前交付v03完整时钟绑定，两份播放器原文件均保留，用户未明确点选哪份，但问题明确属于人声本身。整曲尚未验收，J与抱C的旧局部接受保留。

当前复核人声原始输出、原生DYN、预测发声、可靠元音早中晚与30/50ms短窗，以及相邻/重复句。音量承托与“最有情绪的副歌”分开描述，不将DYN当作生成声带力度或磨砂质感，不重复否决的VOIC/TENC/BREC剂量。伴奏关系不进入本次问题研究。旧封存、作者、Skill、源unknown保持；单Agent、本机检查，CI手动。
''',encoding='utf8')
    idx=copy.deepcopy(load(KNOW/'table2-whole-song-v03-source-audited-index-20261014.json'))
    row=next(r for r in idx['rows'] if r['id']==ID);row.setdefault('feedback_sources',[]).append(ref(REPORT/(NAME+'.json')))
    row['latest_voice_volume_feedback']=feedback;row['effective_current_status']='voice_volume_issues_pending_revision; no full-song acceptance'
    idx.update(status='v03_voice_volume_issues_recorded',generator=ref(Path(__file__)),prior_index=ref(KNOW/'table2-whole-song-v03-source-audited-index-20261014.json'))
    save(KNOW/(INDEX+'.json'),idx)
    (KNOW/(INDEX+'.md')).write_text('# v03人声音量反馈来源\n\n38行保持，整曲生产行追加一次三时段反馈与“人声本身”澄清。未新增逐字标签或因果规律。\n',encoding='utf8')
    registry=load(KNOW/'active-knowledge-sources.json');registry['response_indices']=[(KNOW/(INDEX+'.json')).relative_to(ROOT).as_posix()]
    (KNOW/'active-knowledge-sources.json').write_text(json.dumps(registry,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    responses=[ID,'RESP:LASTPAGE-OWN-LI-ENTRY-PITCH-01','RESP:LASTPAGE-OWN-LI-DYN-LAYERS-01','RESP:LASTPAGE-OWN-LI-VOIC-STAGES-01','RESP:LASTPAGE-OWN-LI-TENC-STAGES-01','RESP:LASTPAGE-OWN-CONTROL-NEUTRAL-01']
    packet=collect_context(['PER:S1','EVT:L2','ACO:L1'],['PARAM:C10.01','PARAM:C11.01','PARAM:C12.01','PARAM:C14.01'],responses)
    decisions=[]
    for r in packet['records']:
        choice='use';reason='Separate model voice quality, musical force and actual post-vocoder amplitude; inspect native path and all real vowels.'
        if r['id'].startswith('RESP:LASTPAGE-OWN-LI-') and r['id']!='RESP:LASTPAGE-OWN-LI-ENTRY-PITCH-01':
            choice='reject';reason='Keep negative local G/H/I evidence; no force-dose escalation or early DYN weakening copied to current voiced body.'
        elif r['id']=='RESP:LASTPAGE-OWN-LI-ENTRY-PITCH-01':
            reason='Preserve explicitly accepted J music/voice direction and withdrawn transition issue; not a whole-song volume acceptance.'
        decisions.append(dict(id=r['id'],decision=choice,reason=reason,condition_match='Current v03 voice volume feedback at three declared intervals; output envelope inspection and bounded new phrase intention.',
            limitations='No universal force mechanism; short-window levels are proxies. Feedback is one aggregate submission, not per-word negatives.'))
    save(RUN/'design/knowledge_context.json',packet)
    plan=dict(scope='whole_song_envelope_review',source=ref(V03/'delivery/lastpage_J_method_whole_song_v03_vocal.wav'),
        knowledge_context=dict(path='knowledge_context.json',sha256=sha(RUN/'design/knowledge_context.json'),decisions=decisions),new_models=0,new_waveforms=0)
    save(RUN/'design/review-protocol.json',plan);_,receipt=check_plan_knowledge(plan,RUN/'design/review-protocol.json');save(RUN/'evaluation/review-knowledge-receipt.json',receipt)
    print('Voice feedback appended;pre-review knowledge gate passed.',flush=True)

def windows(x,sr,span,length):
    a,b=span;starts=np.arange(a+length/2,b-length/2+.0000001,.005)
    if not len(starts):return dict(count=0,status='vowel shorter than requested window')
    indices=np.round(starts*sr).astype(int);half=round(length*sr/2);cs=np.r_[0.,np.cumsum(x*x,dtype=np.float64)]
    power=(cs[indices+half]-cs[indices-half])/(2*half);db=10*np.log10(np.maximum(power,1e-24))
    return dict(count=len(db),p10_dbfs=float(np.percentile(db,10)),median_dbfs=float(np.median(db)),p90_dbfs=float(np.percentile(db,90)),
        min_dbfs=float(db.min()),min_center_s=float(starts[db.argmin()]),range_p90_p10_db=float(np.percentile(db,90)-np.percentile(db,10)))

def analyze():
    check_plan_knowledge(load(RUN/'design/review-protocol.json'),RUN/'design/review-protocol.json')
    vocal,sr=sf.read(V03/'delivery/lastpage_J_method_whole_song_v03_vocal.wav',dtype='float64')
    geom=load(BASE/'native_word_geometry.json');old_dec=load(BASE/'agent_word_decisions.json');ledger=load(V03/'evaluation/assembly-check.json')['contributions']
    states={};rawall=np.zeros_like(vocal)
    for p in ledger:
        ctx=p['context'];wave=np.load(V03/f'fresh/context{ctx:02}/v03/raw.npy',allow_pickle=False);start=p['start_sample'];a=max(0,start);b=min(len(vocal),start+len(wave));rawall[a:b]+=wave[a-start:b-start]*1.5
        with np.load(V03/f'fresh/context{ctx:02}/v03/inputs.npz',allow_pickle=False) as z:states[ctx]={k:z[k].copy() for k in ['voicing','breathiness','tension']}
    rows=[]
    for g,d in zip(geom,old_dec):
        a,b=g['native_vowel'];ctx=d['context'];p=ledger[ctx];f=load(V03/f'native-inputs/v03/phrase_{ctx:03}.json')
        times=f['position_ms']/1000-f['head_frames']*float(np.float32(f['frame_ms']))/1000+np.arange(states[ctx]['voicing'].size)*float(np.float32(f['frame_ms']))/1000
        m=(times>=a)&(times<b)
        n=g['word'];span=round(a*sr),round(b*sr);x=vocal[span[0]:span[1]]
        thirds=[float(20*np.log10(max(np.sqrt(np.mean(v*v)),1e-12))) for v in np.array_split(x,3)]
        raw_rms=float(20*np.log10(max(np.sqrt(np.mean(rawall[span[0]:span[1]]**2)),1e-12)))
        final_rms=float(20*np.log10(max(np.sqrt(np.mean(x*x)),1e-12)))
        selected=any(a<hi and b>lo for lo,hi in [(86,88),(183,190),(196,199)])
        gain=np.fromfile(V03/f'dynamics/unity/phrase_{ctx:03}.f32',dtype='<f4')
        ia=max(0,round((a-p['origin_s'])*sr));ib=min(len(gain),round((b-p['origin_s'])*sr))
        rows.append(dict(word=n,char=g['char'],context=ctx,native_vowel=[a,b],source_unknown=d['source_unknown'],
            in_feedback_interval=selected,feedback_word_label='unknown: interval-level feedback only',
            thirds_rms_dbfs=thirds,rms_dbfs=final_rms,raw_rms_dbfs=raw_rms,DYN_output_delta_db=final_rms-raw_rms,
            native_gain_min=float(gain[ia:ib].min()),native_gain_max=float(gain[ia:ib].max()),
            final_windows={str(ms):windows(vocal,sr,[a,b],ms/1000) for ms in [30,50]},
            raw_windows={str(ms):windows(rawall,sr,[a,b],ms/1000) for ms in [30,50]},
            actual_features={ch:dict(median=float(np.median(z.reshape(-1)[m])),p10=float(np.percentile(z.reshape(-1)[m],10))) for ch,z in states[ctx].items()},
            musical_intent=d['intent'],provisional_decision='Review reported phrase prominence' if selected else 'Retain existing level/role; window screen is not a negative hearing label'))
    save(RUN/'observations/envelope-review.json',dict(words=rows,all318_checked=True,window_lengths_ms=[30,50],step_ms=5,
        source_audio=ref(V03/'delivery/lastpage_J_method_whole_song_v03_vocal.wav'),BGM_analysis=False,new_model_calls=0,
        feedback_intervals=[r for r in rows if r['in_feedback_interval']],source_unknowns_preserved=True,agent_heard=False,measurement_validated=False))
    print('All318 real vowels/raw-vs-DYN/30&50ms windows reviewed;target rows:',flush=True)
    for r in rows:
        if r['in_feedback_interval']:
            print(r['word'],r['char'],r['context'],'RMS',round(r['rms_dbfs'],2),'thirds',list(map(lambda x:round(x,2),r['thirds_rms_dbfs'])),
                  '30ms',round(r['final_windows']['30']['median_dbfs'],2),'DYN',r['native_gain_min'],r['native_gain_max'],
                  'features', {k:round(v['median'],2) for k,v in r['actual_features'].items()},flush=True)

if __name__=='__main__':{'prepare':prepare,'analyze':analyze}[sys.argv[1]]()
