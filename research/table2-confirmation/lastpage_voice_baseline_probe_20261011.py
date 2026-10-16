"""One explicit voice-baseline candidate across two complete own contexts."""
import copy
import csv
import json
from pathlib import Path
import shutil
import subprocess
import sys

import numpy as np
import soundfile as sf
import yaml

from assemble_lastpage_accepted_baseline_20261011 import ROOT, ENTRIES, load, save, sha, ref, check
from agent2utau.evaluation.controlled_probe import tensors, noise_adapter
from agent2utau.expression.variance_expectation import gaussian_frame_noise
from agent2utau.resources.config import load_config
from shfc_path_backend import model_feed

RUN = ROOT / 'runs/experiments/lastpage-voice-baseline-20261011'
BASE = ROOT / 'runs/lastpage_loudness_skill_v02_20261007'
CURRENT = ROOT / 'runs/production/lastpage-accepted-baseline-20261011'
PREVIOUS = ROOT / 'runs/research/lastpage-li-kan-author-reference-20261011'
REPORT = ROOT / 'docs/reports/lastpage'
NAME = 'voice-baseline-probe-20261011'
CHANNELS = ['breathiness','voicing','tension']
INDICES = [28,29]


def native(args, label):
    exe = Path(load_config()['openutau_dir']) / 'a2u-shfcprobe-20261008.exe'
    print('Native:',label,flush=True)
    p = subprocess.run([str(exe),*args],cwd=exe.parent,capture_output=True,
                       encoding='utf-8',errors='replace',timeout=1200)
    (RUN/'logs'/f'{label}.log').write_text(p.stdout+p.stderr,encoding='utf-8')
    assert p.returncode==0,p.stdout[-1500:]+p.stderr[-1500:]
    r=json.loads(p.stdout.strip().splitlines()[-1])
    assert not r.get('errors') and r.get('ok',True),r
    save(RUN/'native-inputs'/f'{label}-result.json',r)


def prepare():
    assert not RUN.exists()
    assert not (REPORT/(NAME+'.json')).exists()
    sealed=load(PREVIOUS/'completion-manifest.json')
    check(sealed['files']+sealed['documents']+sealed['entries'])
    protected=load(PREVIOUS/'protected-before.json')+sealed['files']+sealed['documents']
    RUN.mkdir(parents=True);(RUN/'logs').mkdir();(RUN/'score').mkdir()
    save(RUN/'protected-before.json',protected)
    for n in ENTRIES:
        p=RUN/'before'/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((ROOT/n).read_bytes())
    own=CURRENT/'delivery/lastpage_accepted_C_baseline.ustx'
    a=yaml.safe_load(own.read_text(encoding='utf-8-sig'));b=copy.deepcopy(a)
    changes=[]
    for ix in INDICES:
        part=b['voice_parts'][ix]
        for abbr,old,new in [('cl01',0,25),('cl05',25,0)]:
            curve=next((c for c in part['curves'] if c['abbr']==abbr),None)
            if curve is None:
                assert old==a['expressions'][abbr]['default_value']==0
                grid=next(c for c in part['curves'] if c['abbr']=='cl03')['xs']
                curve=dict(abbr=abbr,xs=grid.copy(),ys=[old]*len(grid));part['curves'].append(curve)
            assert all(y==old for y in curve['ys']) and curve['xs']
            curve['ys']=[new]*len(curve['xs'])
            changes.append(dict(context=ix,channel=abbr,old=old,new=new))
        assert part['notes']==a['voice_parts'][ix]['notes']
        assert all(next((c for c in part['curves'] if c['abbr']==abbr),None)==next((c for c in a['voice_parts'][ix]['curves'] if c['abbr']==abbr),None)
                   for abbr in ['pitd','voic','tenc','brec','dyn','cl02','cl03','cl04'])
    for ix in range(34):
        if ix not in INDICES:assert a['voice_parts'][ix]==b['voice_parts'][ix]
    assert a['tracks']==b['tracks'] and a['wave_parts']==b['wave_parts']
    full=RUN/'score/lastpage_voice_baseline_B.ustx'
    full.write_text(yaml.safe_dump(b,allow_unicode=True,sort_keys=False),encoding='utf-8')
    for label,doc in [('A',a),('B',b)]:
        d=copy.deepcopy(doc);d['voice_parts']=[d['voice_parts'][i] for i in INDICES]
        d['wave_parts']=[];d['tracks']=[d['tracks'][0]]
        d['tracks'][0]['volume']=0;d['tracks'][0]['pan']=-100
        d['tracks'][0]['mute']=False;d['tracks'][0]['solo']=False
        p=RUN/f'score/native_{label}.ustx'
        p.write_text(yaml.safe_dump(d,allow_unicode=True,sort_keys=False),encoding='utf-8')
    save(RUN/'feedback/feedback.json',dict(verbatim='他这个基本都是实的，我们的基本都是虚的',submissions=1,
      author_audio=ref(PREVIOUS/'delivery/baishuo_current165c_reference_vocal.wav'),
      own_audio=ref(PREVIOUS/'delivery/agent_acceptedC_same_lyrics_vocal.wav'),
      finding='author reference predominantly solid; own comparison predominantly airy',
      scope='delivered two-phrase comparison; not all 318 words or unpresented author song',
      prior_kan283_locally_solid_preserved=True,all_word_labels_not_overwritten=True,
      break_or_other_side_effects='unknown',device='unknown',agent_heard=False,measurement_validated=False))
    geometry=load(BASE/'native_word_geometry.json');decisions=load(BASE/'agent_word_decisions.json')
    word_ids=[w['word'] for w in decisions if w['context'] in INDICES]
    assert word_ids==list(range(270,285))
    save(RUN/'design/protocol.json',dict(id='LASTPAGE-VOICE-BASELINE-01',version=1,status='frozen_before_execution',
      authorization='user ordered iterative song updating, identified predominant airy baseline, requested author comparison; new feedback directs this ongoing correction',
      hypothesis='replacing Classic contribution with Bright may improve predominant solidity under own musical/phonetic conditions',
      action='one independently selected voice-color swap; Normal75 retained, Classic25->Bright25',
      alternatives_not_selected=['Copy author Bright40/Cute60 and authored curves','global VOIC increase','increase rejected BREC or guo SHFC doses','add output gain'],
      base=ref(own),candidate=ref(full),changes=changes,contexts=INDICES,word_ids=word_ids,
      phrases=['想把你抱进身体里面','不敢让你看见'],
      purpose='clear connected solid baseline with normal vowel differentiation and original musical movement',
      fixed=['own notes/pitch/phonetic timing','manual VOIC/BREC/TENC/SHFC','DYN','fixed vocal gain1.5','variance11/acoustic101'],
      permitted_changes=['variance/acoustic speaker embeddings','all three predictions and their derived final channels','whole selected context acoustic response'],
      protection={'kan283':'positive solidity reference; assess deterioration explicitly, no presumed preservation of new timbre',
                  'bao225':'entire accepted-C context22 project/state/PCM retained exactly',
                  'outside_contexts28_29':'all other 32 existing complete wave contributions retained'},
      budget={'candidate_count':1,'native_reference_contexts':4,'seeded_waveforms':8,'contexts':2,'variants':['A','A_repeat','B','B_repeat']},
      listening='complete two-phrase context; provide current A, candidate B and separate already-judged author reference',
      outcome='perceived solidity and connection, kan retained, articulation/break/loudness side effects; missing labels unknown',
      stops=['identity/hash/isolation failure','A or repeat not exact','clipping/nonfinite output','no automatic extra candidate or dose increase after response'],
      scope='developmental two-context voice comparison, not new holdout or universal rule',
      source_unknowns=[106],author_numeric_inputs_in_generation=False,measurement_validated=False))
    cfg=load_config();ou=Path(cfg['openutau_dir']);external={}
    for name in ['OpenUtau.Core.dll','prefs.json','a2u-shfcprobe-20261008.exe','a2u-shfcprobe-20261008.dll','a2u-shfcprobe-20261008.deps.json']:
        external[str(ou/name)]=sha(ou/name)
    for p in (ou/'Singers/YousaV1.65c').rglob('*'):
        if p.is_file() and p.suffix in ['.onnx','.emb','.yaml']:external[str(p)]=sha(p)
    save(RUN/'native-inputs/runtime.json',external)
    for label in ['A','B']:
        p=RUN/f'score/native_{label}.ustx'
        native(['export-phonemes','--project',str(p),'--out',str(RUN/f'native-inputs/{label}-phones.json')],f'{label}-phones')
        native(['render','--project',str(p),'--out',str(RUN/f'native-render/{label}.wav'),'--mixdown','--timeout','15'],f'{label}-render')
        native(['export-render-probe','--project',str(p),'--out',str(RUN/f'native-inputs/{label}'),'--indices','0,1'],f'{label}-probe')
    print('Prepared native A/B complete; fresh seeded execution not started.',flush=True)


def execute():
    assert (RUN/'native-inputs/B-probe-result.json').exists()
    assert not (RUN/'fresh').exists()
    check(load(RUN/'protected-before.json'))
    for p,digest in load(RUN/'native-inputs/runtime.json').items():assert sha(Path(p))==digest,p
    assert load(RUN/'native-inputs/A-phones.json')['parts']==load(RUN/'native-inputs/B-phones.json')['parts']
    records=[]
    for local,original in enumerate(INDICES):
        fa,va,fb,vb=[load(RUN/f'native-inputs/{s}/{k}_{local:03}.json') for s,k in [('A','phrase'),('A','variance'),('B','phrase'),('B','variance')]]
        for key in ['position_ms','frame_ms','head_frames','tail_frames','phones','vocoder_f0','expression_deltas','tone_shift_cents']:
            assert fa[key]==fb[key],key
        aa,bb=tensors(fa['tensors']),tensors(fb['tensors']);av,bv=tensors(va['tensors']),tensors(vb['tensors'])
        assert aa.keys()==bb.keys() and av.keys()==bv.keys()
        assert all(np.array_equal(av[k],bv[k]) for k in av if k!='spk_embed')
        assert all(np.array_equal(aa[k],bb[k]) for k in aa if k not in ['spk_embed',*CHANNELS])
        for label,ac,vr in [('A',aa,av),('B',bb,bv)]:
            for values,root in [(ac,Path(fa['singer_location'])),(vr,Path(va['variance_speaker_root']))]:
                mix=(.75*np.fromfile(root/'Yousa_Normal.emb',dtype='<f4')+
                     .25*np.fromfile(root/('Yousa_Classic.emb' if label=='A' else 'Yousa_Bright.emb'),dtype='<f4'))
                assert np.array_equal(values['spk_embed'],np.broadcast_to(mix,values['spk_embed'].shape))
        records.append((fa,va,fb,vb))
    (RUN/'fresh').mkdir();model_dir=RUN/'fresh/models';model_dir.mkdir()
    first=records[0]
    adapter_proofs=[noise_adapter(first[1]['variance_model'],model_dir/'variance.onnx',3,24),
                    noise_adapter(first[0]['acoustic_model'],model_dir/'acoustic.onnx',1,128)]
    import onnxruntime as ort
    options=ort.SessionOptions();options.intra_op_num_threads=options.inter_op_num_threads=1
    options.execution_mode=ort.ExecutionMode.ORT_SEQUENTIAL
    variance,acoustic,vocoder=[ort.InferenceSession(str(p),sess_options=options,providers=['CPUExecutionProvider'])
         for p in [model_dir/'variance.onnx',model_dir/'acoustic.onnx',first[0]['vocoder_model']]]
    save(RUN/'fresh/start.json',dict(protocol=ref(RUN/'design/protocol.json'),adapters=adapter_proofs,
       ort_version=ort.__version__,numpy_version=np.__version__,variance_seed=11,acoustic_seed=101,max_waveforms=8))
    rows=[]
    for original,record in zip(INDICES,records):
        prior=load(BASE/f'synthesis/phrase_{original:03}.json')
        variants={}
        for label in ['A','A_repeat','B','B_repeat']:
            f,v=record[:2] if label.startswith('A') else record[2:]
            inp,vin=tensors(f['tensors']),tensors(v['tensors']);frames=inp['f0'].size
            vin['probe_noise']=gaussian_frame_noise(11,3,24,frames)
            out_names=[o.name for o in variance.get_outputs()]
            pred=dict(zip(out_names,variance.run(out_names,model_feed(variance,vin))))
            clipping={}
            for channel in CHANNELS:
                lo,hi=(-10,10) if channel=='tension' else (-96,0)
                delta=np.asarray(f['expression_deltas'][channel],np.float32)[None,:]
                raw=pred[channel+'_pred']+delta
                clipping[channel]=int(np.count_nonzero((raw<lo)|(raw>hi)))
                inp[channel]=np.clip(raw,lo,hi).astype(np.float32)
            inp['probe_noise']=gaussian_frame_noise(101,1,128,frames)
            mel=acoustic.run(['mel'],model_feed(acoustic,inp))[0]
            vm=mel.copy()
            if f['acoustic_mel_base']!=f['vocoder_mel_base']:vm*=np.log(10) if f['acoustic_mel_base']=='10' else 1/np.log(10)
            voc_f0=np.asarray(f['vocoder_f0'],np.float32)[None,:]
            wave=vocoder.run(None,model_feed(vocoder,dict(mel=vm,f0=voc_f0)))[0].reshape(-1)
            assert np.isfinite(wave).all()
            d=RUN/f'fresh/context{original}/{label}';d.mkdir(parents=True)
            np.save(d/'raw.npy',wave);np.savez_compressed(d/'inputs.npz',**inp)
            np.savez_compressed(d/'predictions.npz',**pred)
            variants[label]=dict(wave=wave,inputs=inp,pred=pred,clipping=clipping)
            print(f'Fresh context{original} {label}: variance11/acoustic101/vocoder done',flush=True)
        a,b=variants['A'],variants['B']
        old=np.load(BASE/f'synthesis/phrase_{original:03}.npy',allow_pickle=False)
        assert np.array_equal(a['wave'],old),f'Baseline context{original} not exact'
        with np.load(BASE/f'synthesis/state_{original:03}.npz',allow_pickle=False) as state:
            for channel in CHANNELS:
                assert np.array_equal(a['pred'][channel+'_pred'],state[channel])
                assert np.array_equal(a['inputs'][channel],state['final_'+channel])
        for label in ['A','B']:
            x,y=variants[label],variants[label+'_repeat']
            assert np.array_equal(x['wave'],y['wave'])
            assert all(np.array_equal(x['inputs'][k],y['inputs'][k]) for k in x['inputs'])
            assert all(np.array_equal(x['pred'][k],y['pred'][k]) for k in x['pred'])
        changed=[k for k in a['inputs'] if not np.array_equal(a['inputs'][k],b['inputs'][k])]
        assert set(changed).issubset({'spk_embed',*CHANNELS}) and 'spk_embed' in changed
        assert all(n==0 for x in variants.values() for n in x['clipping'].values()),'Feature clipping; stop effect interpretation'
        rows.append(dict(context=original,frames=int(a['inputs']['f0'].size),samples=len(a['wave']),
           baseline_raw_exact=True,baseline_prediction_and_final_channels_exact=True,both_variant_repeats_exact=True,
           changed_final_inputs=changed,manual_deltas_exact=True,vocoder_F0_exact=True,native_phone_clock_exact=True,
           feature_clipping=0,variance_speaker_A='Normal75/Classic25',variance_speaker_B='Normal75/Bright25',
           acoustic_speaker_A='Normal75/Classic25',acoustic_speaker_B='Normal75/Bright25',
           wave_start_s=prior['wave_start_s'],seed11_101=True))
    check(load(RUN/'protected-before.json'))
    for p,digest in load(RUN/'native-inputs/runtime.json').items():assert sha(Path(p))==digest,p
    save(RUN/'fresh/execution.json',dict(rows=rows,seeded_variance_calls=8,seeded_acoustic_vocoder_waveforms=8,
        baseline_and_repeats_exact=True,one_candidate_only=True,measurement_validated=False))


def finish():
    assert (RUN/'fresh/execution.json').exists() and not (RUN/'completion-manifest.json').exists()
    plan=load(RUN/'design/protocol.json');proof=load(RUN/'fresh/execution.json')
    phrases=load(CURRENT/'design/phrase-ledger.json');geometry=load(BASE/'native_word_geometry.json')
    n=load(CURRENT/'evaluation/assembly-check.json')['samples'];sr=44100
    a=np.zeros(n,np.float64);b=np.zeros(n,np.float64);reverse=np.zeros(n,np.float64);contributions=[]
    windows=[]
    for p in phrases:
        ix=p['context'];original=np.fromfile(ROOT/p['dynamic_wave_path'],dtype='<f4');new=original
        if ix in INDICES:
            gain=np.fromfile(BASE/f'native_dynamics_ones/phrase_{ix:03}.f32',dtype='<f4')
            raw_a=np.load(RUN/f'fresh/context{ix}/A/raw.npy',allow_pickle=False).astype('<f4')
            raw_b=np.load(RUN/f'fresh/context{ix}/B/raw.npy',allow_pickle=False).astype('<f4')
            assert np.array_equal(raw_a*gain,original)
            new=raw_b*gain
        start=round(p['wave_start_s']*sr);lo=max(0,start);hi=min(n,start+len(new))
        a[lo:hi]+=original[lo-start:hi-start];b[lo:hi]+=new[lo-start:hi-start]
        contributions.append((lo,hi,new[lo-start:hi-start]))
        if ix in INDICES:windows.append((lo,hi))
    for lo,hi,x in reversed(contributions):reverse[lo:hi]+=x
    assert np.array_equal(b,reverse)
    old_pcm,rate=sf.read(CURRENT/'delivery/lastpage_accepted_C_baseline_vocal.wav',dtype='int32');assert rate==sr
    d=RUN/'delivery';d.mkdir()
    full=d/'lastpage_voice_baseline_B_vocal.wav'
    peak=float(np.max(np.abs(b*1.5)));assert np.isfinite(b).all() and peak<1
    sf.write(full,b*1.5,sr,subtype='PCM_24');new_pcm,rate=sf.read(full,dtype='int32')
    allowed=np.zeros(n,dtype=bool)
    for lo,hi in windows:allowed[lo:hi]=True
    assert np.array_equal(old_pcm[~allowed],new_pcm[~allowed])
    lo,hi=[round(t*sr) for t in [209.4,218.0]]
    preview=d/'B_same_lyrics_vocal.wav';sf.write(preview,new_pcm[lo:hi],sr,subtype='PCM_24')
    project=d/'lastpage_voice_baseline_B.ustx';shutil.copyfile(RUN/'score/lastpage_voice_baseline_B.ustx',project)
    p225=phrases[22];lo225=round(p225['wave_start_s']*sr);hi225=lo225+p225['samples']
    assert np.array_equal(new_pcm[lo225:hi225],old_pcm[lo225:hi225])
    rows=[]
    for word in plan['word_ids']:
        g=geometry[word];lo,hi=[round(t*sr) for t in g['native_vowel']]
        aa=a[lo:hi];bb=b[lo:hi]
        ra=float(np.sqrt(np.mean(aa**2)));rb=float(np.sqrt(np.mean(bb**2)))
        rows.append(dict(word=word,char=g['char'],vowel_s=g['native_vowel'],
             rms_change_db=float(20*np.log10(max(rb,1e-15)/max(ra,1e-15))),
             intensity_proxy_only=True,new_solidity_label='pending',new_articulation_break_or_other_side_effects='unknown'))
    deliveries=dict(candidate_full=ref(full),candidate_preview=ref(preview),candidate_project=ref(project),
        original_preview=ref(PREVIOUS/'delivery/agent_acceptedC_same_lyrics_vocal.wav'),
        author_reference=ref(PREVIOUS/'delivery/baishuo_current165c_reference_vocal.wav'))
    checks=dict(whole_duration_s=n/sr,fixed_vocal_gain=1.5,peak=peak,native_DYN_preserved=True,
        PCM_outside_selected_contexts_exact=True,accepted_bao_C_PCM_exact=True,reverse_assembly_exact=True,
        source_unknown106_retained=True,kan283='candidate changes voice condition; solidity protection awaiting feedback',
        no_normalization_compression_or_BGM=True,agent_heard=False)
    save(RUN/'evaluation/delivery-check.json',checks)
    report=dict(status='one_voice_baseline_candidate_delivered_pending_listening',protocol=ref(RUN/'design/protocol.json'),
       feedback=ref(RUN/'feedback/feedback.json'),execution=proof,deliveries=deliveries,assembly=checks,word_responses=rows,
       candidate_preferred=False,general_rule_validated=False,measurement_validated=False,
       limitations=['two complete own contexts from an already seen song; no held-out/general claim',
          'speaker intervention changes three predictions and output timbre/level; not isolated voicing physiology',
          'fixed vocoder input F0, output detected F0 not newly measured; Agent has not heard',
          'author reference is current165c, original156 historical audio unavailable'],
       next='Receive whole two-phrase B response, including solidity/articulation/kan; accept/reject this one route before expanding whole-song scope')
    control_table=ROOT/'docs/knowledge/acoustic-manifestations-20261009/control-details.csv'
    atom_table=ROOT/'docs/knowledge/acoustic-manifestations-20261009/atomic-manifestations.csv'
    with control_table.open(encoding='utf-8-sig',newline='') as f:control_ids={r['id'] for r in csv.DictReader(f)}
    with atom_table.open(encoding='utf-8-sig',newline='') as f:atom_ids={r['id'] for r in csv.DictReader(f)}
    assert {'PARAM:C20.01','PARAM:C20.03','PARAM:C20.05'}.issubset(control_ids) and 'PER:S1' in atom_ids
    report['table1_refs']=dict(perception='PER:S1',changed=['PARAM:C20.01','PARAM:C20.05'],
        retained=['PARAM:C20.03'],case_scope='aggregate two-phrase comparative judgment; no word-by-word normality',
        table_sources=[ref(control_table),ref(atom_table)])
    report['table2_supplement']=dict(record_id='RESP:LASTPAGE-VOICE-BASELINE-01',comparison='B-A',
        intervention='speaker compositional swap Classic25->Bright25 with Normal75 fixed',
        contexts=INDICES,words=plan['word_ids'],independent_contexts=2,seeded_same_input_repeats=4,
        waveforms=8,prior_user_comparison_feedback='author-reference vs original-A predominantly solid vs airy',
        candidate_user_feedback='pending',source_feedback_is_not_candidate_feedback=True,
        adoption=False,measurement_validated=False,general_rule_validated=False)
    report['preparation_repair']='Absent cl01 is declared default0; added candidate cl01 explicitly on unchanged cl03 grid. Rejected preparation snapshot preserved; no old file edit.'
    save(RUN/'evaluation/table2-supplement.json',report['table2_supplement'])
    save(REPORT/(NAME+'.json'),report)
    md=f'''# 最后一页：两完整乐句声线基底候选

2026-10-11。状态：one_voice_baseline_candidate_delivered_pending_listening。

最新原话“他这个基本都是实的，我们的基本都是虚的”绑定上一轮两份独立人声，计1条回复；范围为所交付两句，不改写全部318字标签，也不覆盖看283原局部偏实。白烁参考的已感知实感支持研究整体基底方向，但声线、曲线、音高阶段、时钟和执行方式多因素不同，尚未确认哪个因素造成差异。

本轮只一个自行选定候选：Normal75保持，将Classic25替换Bright25。未复制作者Bright40/Cute60或曲线节点。覆盖word270–284共15字、原生context28/29完整两句；自身音高、音素时钟、VOIC/TENC/BREC/SHFC及原生DYN不变。看283作为原正例保护观察点，其新声色是否保住实感待听；抱225完整C所在句原工程/预测/PCM精确保留。

## 执行与交付

原生A/B各两上下文导出/缓存技术执行单列；固定variance11/acoustic101下两上下文各A/A_repeat/B/B_repeat，共8套新波形。A预测/最终三通道/原波形精确重现，A/B重复精确；两阶段speaker精确，非speaker条件及人工增量精确，允许三个预测及其最终输入随speaker响应，特征裁剪0。音符/phones/pitch身份保持。

以32句原贡献和2句新B组装完整版本，正反组装精确；选择句贡献范围外PCM及抱C句PCM精确保持。44100Hz mono PCM24、固定声增益1.5，峰值{peak:.6f}，无归一化/压缩/BGM。逐字RMS响应仅代理，不能确认虚实改善。vocoder F0输入保持；本轮未重新测实际输出F0，Agent未听。

- [候选B两句](../../../{deliveries['candidate_preview']['path']})：原209.4–218.0秒，里约3.56秒、看约6.93秒。
- [自身原A两句](../../../{deliveries['original_preview']['path']})：原PCM精确截取。
- [白烁独立当前参考](../../../{deliveries['author_reference']['path']})：上轮用户评价“基本都是实的”；当前1.65c重渲染，非历史1.56作者录音。
- [完整B人声](../../../{deliveries['candidate_full']['path']})、[完整B工程](../../../{deliveries['candidate_project']['path']})。完整B仅上述两句采用新基底，其余32句明确保持，不宣称全曲均已调整或接受。

反馈任务：两句是否更实且连贯；看是否退化；是否出现破音、咬字/响度等副作用。未报项unknown，不用数值响应代替改善。该候选待评且未采用；无自动候选搜索或加量。若获支持才记录明确整曲实施范围；阴性/副作用收口当前路线。表1追加版本绑定虚实例证，表2追加一项speaker因素开发对照及其预测/输出/反馈，通用规律0、measurement_validated仍false。

正式引用：PER:S1（支撑/实听感），PARAM:C20.01/05改变、C20.03保持；表2补充RESP:LASTPAGE-VOICE-BASELINE-01按B−A登记。8套波形只有2个独立完整上下文，重复不扩充独立条件数；上一轮“白烁实/自身虚”不是本次B候选反馈。准备阶段原cl01未显式存储，按声明默认0补入候选；首轮准备失败快照保留，原控制和单位不改。

协议/反馈/输入/重复检查在新run封存，原音频/歌曲/Skill与作者原件保持；单Agent、CI仅手动。[JSON]({NAME}.json)、[审计]({NAME}-audit.json)。
'''
    (REPORT/(NAME+'.md')).write_text(md,encoding='utf-8',newline='\n')
    status=('当前状态one_voice_baseline_candidate_delivered_pending_listening：2026-10-11“他基本实/我们基本虚”绑定上轮两独立人声，'
      '计1回复，不扩成全318字标签、看283原正例保留。自行选定单个Normal75/Bright25候选，替换原Classic25，'
      '仅context28/29完整两句15字，音高/音素/人工三通道/DYN不变，预测允许响应；8套固定种子新波形，A原波形/预测/输入与重复精确，'
      '两阶段speaker及隔离/特征裁剪0通过。完整B仅2句修改，其余32句及抱C PCM保持；同固定1.5分开交付B/A/白烁参考，'
      '看新声色与虚实/副作用待评，候选未采用、Agent未听、通用规律0。原工程/音频/Skill不改，单Agent/CI仅手动，下一步接本候选反馈，不自动扩展。')
    for name in ENTRIES:
        p=ROOT/name;lines=p.read_text(encoding='utf-8').splitlines()
        ids=[i for i,l in enumerate(lines) if '当前状态feedback_bound_author_reference_compared_and_separately_delivered：' in l]
        assert len(ids)==1,name
        relative='docs/reports/lastpage/'+NAME+'.md'
        if '/' in name:relative=('../../' if name.startswith('research/') else '../../../')+relative
        lines[ids[0]]=('- ' if lines[ids[0]].startswith('- ') else '')+status+f' 见[声线基底候选]({relative})。'
        for i,line in enumerate(lines):
            if name=='plan.md' and line.startswith('下一工作进入逐首更新，先《最后一页》：'):
                lines[i]='下一工作进入逐首更新，先《最后一页》：单个声线基底候选已完成两完整句对照和完整载体交付，下一步接本版本虚实、看283保护与副作用反馈；据结果收口/明确整曲后续范围，不自动追加候选或扫参数。'
        p.write_text('\n'.join(lines)+'\n',encoding='utf-8',newline='\n')
    check(load(RUN/'protected-before.json'))
    for p,digest in load(RUN/'native-inputs/runtime.json').items():assert sha(Path(p))==digest,p
    gate=subprocess.run([sys.executable,'tools/repository/check_repository.py','--worktree'],cwd=ROOT,capture_output=True,encoding='utf-8')
    (RUN/'logs/repository-gate.log').write_text(gate.stdout+gate.stderr,encoding='utf-8')
    assert gate.returncode==0,gate.stdout+gate.stderr
    audit=dict(status='passed_with_explicit_auditory_gaps',protected_files=len(load(RUN/'protected-before.json')),
       actual_seeded_waveforms=8,candidates=1,baseline_and_repeats_exact=True,speaker_both_stages_checked=True,
       manual_control_and_phonetic_pitch_isolation_checked=True,original_32_contexts_and_bao_C_PCM_exact=True,
       feedback_count=1,candidate_feedback_count=0,source_unknown_masks_unchanged=True,author_curve_inputs=False,
       old_song_audio_Skill_unchanged=True,agent_heard=False,measurement_validated=False,
       script=ref(Path(__file__)),gate=gate.stdout.strip(),outputs=deliveries)
    save(RUN/'evaluation/audit.json',audit);save(REPORT/(NAME+'-audit.json'),audit)
    files=[ref(p) for p in sorted(RUN.rglob('*')) if p.is_file()]
    docs=[ref(p) for p in sorted(REPORT.glob(NAME+'*'))]
    save(RUN/'completion-manifest.json',dict(status=audit['status'],files=files,documents=docs,entries=[ref(ROOT/n) for n in ENTRIES]))
    print(json.dumps(dict(status=audit['status'],preview=deliveries['candidate_preview'],peak=peak,gate=audit['gate']),ensure_ascii=False),flush=True)


if __name__=='__main__':
    {'prepare':prepare,'execute':execute,'finish':finish}[sys.argv[1]]()
