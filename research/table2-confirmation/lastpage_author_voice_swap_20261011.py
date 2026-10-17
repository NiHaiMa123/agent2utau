"""Append pitch feedback; one authorized author-copy speaker replacement."""
import copy
import csv
import json
from pathlib import Path
import shutil
import subprocess
import sys

import numpy as np
import yaml

from assemble_lastpage_accepted_baseline_20261011 import ROOT,ENTRIES,load,save,sha,ref,check
from agent2utau.evaluation.controlled_probe import tensors
from agent2utau.expression.variance_expectation import gaussian_frame_noise
from agent2utau.resources.config import load_config
from shfc_path_backend import model_feed

PRIOR=ROOT/'runs/experiments/lastpage-author-pitch-ablation-20261011'
RUN=ROOT/'runs/experiments/lastpage-author-voice-swap-20261011'
REPORT=ROOT/'docs/reports/lastpage'
FEEDBACK_NAME='author-pitch-feedback-20261011'
NAME='author-voice-swap-20261011'
CHANNELS=['breathiness','voicing','tension']


def runtime():
    check(load(RUN/'protected-before.json'))
    for p,h in load(RUN/'native-inputs/runtime.json').items():assert sha(Path(p))==h


def prepare():
    assert not RUN.exists() and not (REPORT/(FEEDBACK_NAME+'.json')).exists() and not (REPORT/(NAME+'.json')).exists()
    seal=load(PRIOR/'completion-manifest.json');check(seal['files']+seal['documents']+seal['entries'])
    protected=load(PRIOR/'protected-before.json')+seal['files']+seal['documents']+[ref(PRIOR/'completion-manifest.json')]
    check(protected);RUN.mkdir(parents=True);(RUN/'logs').mkdir();(RUN/'score').mkdir()
    save(RUN/'protected-before.json',protected)
    for n in ENTRIES:
        p=RUN/'before'/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((ROOT/n).read_bytes())
    old=load(PRIOR/'evaluation/delivery-check.json')['outputs']
    own=ROOT/'runs/research/lastpage-li-kan-author-reference-20261011/delivery/agent_acceptedC_same_lyrics_vocal.wav'
    feedback=dict(verbatim='都比我们的实',submissions=1,response_record='RESP:LASTPAGE-AUTHOR-PITCH-ABLATION-01',
        versions={l:old[l] for l in ['A','P','N','PN']},own_comparator=ref(own),
        scope='aggregate two-phrase relative solidity judgment; four displayed author-copy versions vs earlier own comparator',
        finding='A/P/N/PN each perceived more solid than own comparison',
        new_A_relative_solidity_supported=True,ranking_between_four='unknown',equality_with_old_author_reference='unknown',
        individual_word_labels_added=0,absolute_naturalness='unknown',break_articulation_level_side_effects='unknown',
        agent_heard=False,measurement_validated=False,general_rule_validated=False)
    check(list(feedback['versions'].values())+[feedback['own_comparator']]);save(RUN/'feedback/pitch-feedback.json',feedback)
    findings=[
        'All four versions, including new fixed-seed A and PN, retain a perceived relative solidity advantage vs own comparison.',
        'Under these author conditions PITD and note.pitch offsets/snap are not necessary for that advantage; neither removal reproduced the own predominantly airy baseline.',
        'This does not establish equality/ranking among A/P/N/PN or no articulation/break/level side effects.',
        'Tone/tuning, musical stages, phonetic durations, speakers and non-pitch controls remained authored; cannot rule out pitch register or interactions.',
        'Two seen author contexts and repeated waves are not independent holdout evidence or a universal tuning rule.'
    ]
    supplement=dict(record_id=feedback['response_record'],append_only_feedback=True,feedback=feedback,findings=findings,
        prior_frozen_report=ref(REPORT/'author-pitch-ablation-20261011.json'),perception='PER:S1',
        parameter_refs=['PARAM:C03.01','PARAM:C02.02','PARAM:C02.04'],adoption=False,measurement_validated=False,general_rule_validated=False)
    save(RUN/'evaluation/pitch-feedback-supplement.json',supplement)
    save(REPORT/(FEEDBACK_NAME+'.json'),supplement)
    (REPORT/(FEEDBACK_NAME+'.md')).write_text('''# 最后一页：白烁音高拆分反馈

用户原话“都比我们的实”，计1条聚合回复，绑定A/P/N/PN四版与先前自己的两句比较音频SHA。新固定种子A的相对实感得到支持；取消PITD、取消note.pitch相对偏移/首点吸附及两者都取消的版本仍比自己的比较版实。在这两个作者上下文中，这两项细部曲线不是维持该相对优势的必要条件，也未单独重现自己的偏虚基线。

没有补造四版彼此相同/强弱排序、完全无破音/咬字或音量副作用、绝对自然度或15条逐字标签。反馈没有排除音符tone/tuning、音乐阶段、声线、非音高发声控制、时钟与上下文的作用或交互；不能宣布全部pitch无关。原音高拆分报告的pending保留其封存时态，本补充记录后续反馈；原实验/工程/音频/Skill不改。

下一组有限研究：以作者完整曲线A为基线，只把声线混合换为自己的Normal75/Classic25，保留作者所有音乐/音素/非声线控制。作者原mix在时钟上有变化，不以某个字的Bright40/Cute60概括全句。之前在自己工程将Classic25换成Bright25未获实感改善，不等于这次反向声线隔离已试过。两上下文仍是已见开发条件，通用规律0、measurement_validated=false，Agent未听。详见[绑定JSON](author-pitch-feedback-20261011.json)与后续[单组声线替换](author-voice-swap-20261011.md)。
''',encoding='utf-8',newline='\n')
    a=yaml.safe_load((PRIOR/'score/A.ustx').read_text(encoding='utf-8-sig'));b=copy.deepcopy(a)
    part=b['voice_parts'][0];stop=max(n['position']+n['duration'] for n in part['notes'])+5
    for k,value in [('cl01',0),('cl02',0),('cl03',75),('cl04',0),('cl05',25)]:
        c=next(c for c in part['curves'] if c['abbr']==k);c['xs']=[0,stop];c['ys']=[value,value]
    (RUN/'score/A.ustx').write_bytes((PRIOR/'score/A.ustx').read_bytes())
    (RUN/'score/B.ustx').write_text(yaml.safe_dump(b,allow_unicode=True,sort_keys=False),encoding='utf-8')
    # A native exports are explicit bound reuse, not new native execution.
    for kind in ['roundtrip.ustx','phones.json','pitch.json']:
        p=RUN/f'native-inputs/A-{kind}';p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(PRIOR/f'native-inputs/A-{kind}',p)
    for ctx in [0,1]:
        for kind in ['phrase','variance']:
            p=RUN/f'native-inputs/A/{kind}_{ctx:03}.json';p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(PRIOR/f'native-inputs/A/{kind}_{ctx:03}.json',p)
    save(RUN/'native-inputs/runtime.json',load(PRIOR/'native-inputs/runtime.json'))
    save(RUN/'design/protocol.json',dict(id='LASTPAGE-AUTHOR-VOICE-SWAP-01',status='frozen_before_execution',
        authorization='ongoing user request to copy author project and change factors gradually; pitch-factor feedback now received',
        triggering_feedback=ref(RUN/'feedback/pitch-feedback.json'),A=ref(RUN/'score/A.ustx'),B=ref(RUN/'score/B.ustx'),
        action='Replace only authored cl01..cl05 mixtures by explicit constant Normal75/Classic25 (total100), author phone CLR unchanged',
        purpose='test whether own speaker composition alone reproduces predominantly airy result under solid author musical/phonetic/control conditions',
        alternatives_not_selected=['neutralize TENC/BREC/VOIC/SHFC together','change tone/register or retime own curves onto author','raise VOIC or output gain'],
        contexts=[0,1],complete_part_native_contexts=3,fixed=['author notes/tuning/pitch/vibrato','phone identity/clock/CLR','TENC/BREC/VOIC/SHFC','DYN unity/gain1.5','seeds11/101'],
        permitted_changes=['both stage spk_embed','three fresh predictions/final channels','mel/wave'],
        budget=dict(new_candidate=1,new_native_cached_contexts=3,reused_A_native_contexts=2,new_seeded_waveforms=8,independent_contexts=2,same_input_repeats=4,new_F0_calls=4,reused_A_F0_arrays=4),
        model_adapters=[ref(PRIOR/'fresh/models/variance.onnx'),ref(PRIOR/'fresh/models/acoustic.onnx')],
        expected='if B becomes airy vs solid A, speaker contribution supported under these conditions; if B remains solid, speaker alone not sufficient; no universal or unique cause conclusion',
        stops=['unexpected phone/pitch/non-speaker condition change','A not exact or repeat mismatch','nonfinite/file clipping','no automatic next factor until feedback'],
        author_research_only=True,adoption=False,agent_heard=False,measurement_validated=False))
    runtime();print('Pitch feedback bound; one author-to-own speaker protocol frozen.',flush=True)


def native():
    runtime();exe=Path(load_config()['openutau_dir'])/'a2u-shfcprobe-20261008.exe';p=str(RUN/'score/B.ustx')
    cmds=[('roundtrip',['roundtrip','--project',p,'--out',str(RUN/'native-inputs/B-roundtrip.ustx')]),
        ('phones',['export-phonemes','--project',p,'--out',str(RUN/'native-inputs/B-phones.json')]),
        ('pitch',['export-pitch','--project',p,'--out',str(RUN/'native-inputs/B-pitch.json')]),
        ('render',['render','--project',p,'--out',str(RUN/'native-render/B.wav'),'--mixdown','--timeout','15']),
        ('probe',['export-render-probe','--project',p,'--out',str(RUN/'native-inputs/B'),'--indices','0,1'])]
    for label,args in cmds:
        out=RUN/f'native-inputs/B-{label}-result.json'
        if out.exists():continue
        print('Native B',label,flush=True)
        proc=subprocess.run([str(exe),*args],cwd=exe.parent,capture_output=True,encoding='utf-8',errors='replace',timeout=1200)
        log=RUN/f'logs/B-{label}.log';assert not log.exists();log.write_text(proc.stdout+proc.stderr,encoding='utf-8')
        assert proc.returncode==0,proc.stdout[-1000:]+proc.stderr[-1000:]
        r=json.loads(proc.stdout.strip().splitlines()[-1]);assert not r.get('errors') and r.get('ok',True);save(out,r)
    runtime();print('New native B complete, A native evidence explicitly reused.',flush=True)


def execute():
    assert load(RUN/'evaluation/native-independent-check.json')['status']=='passed' and not (RUN/'fresh').exists()
    runtime()
    import onnxruntime as ort
    opts=ort.SessionOptions();opts.intra_op_num_threads=opts.inter_op_num_threads=1;opts.execution_mode=ort.ExecutionMode.ORT_SEQUENTIAL
    f=load(RUN/'native-inputs/A/phrase_000.json')
    variance,acoustic,vocoder=[ort.InferenceSession(str(p),sess_options=opts,providers=['CPUExecutionProvider'])
        for p in [PRIOR/'fresh/models/variance.onnx',PRIOR/'fresh/models/acoustic.onnx',f['vocoder_model']]]
    save(RUN/'fresh/start.json',dict(protocol=ref(RUN/'design/protocol.json'),adapters_reused=load(RUN/'design/protocol.json')['model_adapters'],
        seeds=[11,101],max_waveforms=8,ort=ort.__version__,numpy=np.__version__))
    rows=[]
    for ctx in [0,1]:
        for l in ['A','B']:
            f=load(RUN/f'native-inputs/{l}/phrase_{ctx:03}.json');v=load(RUN/f'native-inputs/{l}/variance_{ctx:03}.json')
            for suffix in ['', '_repeat']:
                ac,va=tensors(f['tensors']),tensors(v['tensors']);n=ac['f0'].size
                va['probe_noise']=gaussian_frame_noise(11,3,24,n)
                names=[o.name for o in variance.get_outputs()];pred=dict(zip(names,variance.run(names,model_feed(variance,va))))
                clipping={}
                for ch in CHANNELS:
                    limits=(-10,10) if ch=='tension' else (-96,0)
                    raw=pred[ch+'_pred']+np.asarray(f['expression_deltas'][ch],np.float32)[None,:]
                    clipping[ch]=int(np.count_nonzero((raw<limits[0])|(raw>limits[1])));ac[ch]=np.clip(raw,*limits).astype(np.float32)
                ac['probe_noise']=gaussian_frame_noise(101,1,128,n)
                mel=acoustic.run(['mel'],model_feed(acoustic,ac))[0];vm=mel.copy()
                if f['acoustic_mel_base']!=f['vocoder_mel_base']:vm*=np.log(10) if f['acoustic_mel_base']=='10' else 1/np.log(10)
                vf=np.asarray(f['vocoder_f0'],np.float32)[None,:];wave=vocoder.run(None,model_feed(vocoder,dict(mel=vm,f0=vf)))[0].reshape(-1)
                assert np.isfinite(wave).all() and len(wave)==n*512
                d=RUN/f'fresh/context{ctx}/{l}{suffix}';d.mkdir(parents=True)
                np.save(d/'raw.npy',wave)
                for key,x in [('inputs',ac),('variance-inputs',va),('predictions',pred),('mel',dict(mel=mel)),('vocoder-f0',dict(f0=vf))]:np.savez_compressed(d/(key+'.npz'),**x)
                rows.append(dict(context=ctx,variant=l+suffix,frames=n,samples=len(wave),feature_clipping=clipping,
                    wave_start_s=(f['position_ms']-f['head_frames']*float(np.float32(f['frame_ms'])))/1000,raw_peak=float(np.max(np.abs(wave)))))
                print('Fresh',ctx,l+suffix,'done',flush=True)
    runtime();save(RUN/'fresh/execution.json',dict(rows=rows,variance_calls=8,acoustic_vocoder_waveforms=8,measurement_validated=False))


if __name__=='__main__':{'prepare':prepare,'native':native,'execute':execute}[sys.argv[1]]()
