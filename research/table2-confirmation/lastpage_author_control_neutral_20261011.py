"""Author-copy group neutralization after bounded speaker preference feedback."""
import copy
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

PRIOR=ROOT/'runs/experiments/lastpage-author-voice-swap-20261011'
MODELS=ROOT/'runs/experiments/lastpage-author-pitch-ablation-20261011/fresh/models'
RUN=ROOT/'runs/experiments/lastpage-author-control-neutral-20261011'
REPORT=ROOT/'docs/reports/lastpage'
NAME='author-control-neutral-20261011'
FEEDBACK_NAME='author-voice-feedback-20261011'
CHANNELS=['breathiness','voicing','tension']
NEUTRAL={'tenc':0,'brec':0,'voic':100,'shfc':0}


def runtime():
    check(load(RUN/'protected-before.json'))
    for p,h in load(RUN/'native-inputs/runtime.json').items():assert sha(Path(p))==h


def prepare():
    assert not RUN.exists() and not (REPORT/(FEEDBACK_NAME+'.json')).exists()
    seal=load(PRIOR/'completion-manifest.json');check(seal['files']+seal['documents']+seal['entries'])
    protected=load(PRIOR/'protected-before.json')+seal['files']+seal['documents']+[ref(PRIOR/'completion-manifest.json')]
    check(protected);RUN.mkdir(parents=True);(RUN/'logs').mkdir();(RUN/'score').mkdir();save(RUN/'protected-before.json',protected)
    for n in ENTRIES:
        p=RUN/'before'/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((ROOT/n).read_bytes())
    outputs=load(PRIOR/'evaluation/delivery-check.json')['outputs']
    feedback=dict(verbatim='B比原版好点，但还是不如A',submissions=1,response_record='RESP:LASTPAGE-AUTHOR-VOICE-SWAP-01',
        audio=outputs,interpretation='A preferred to speaker-swap B; B slightly better than own original comparator',
        original_referent='own_original_comparator: contextual inference from three labeled delivered files, not explicitly renamed by user',
        perceived_axis='overall better in ongoing solidity comparison; explicit separate solidity/articulation/level dimensions unknown',
        relative_order=['A','B','own_original_comparator'],unique_physiological_cause='unknown',new_word_labels=0,
        side_effects_and_absolute_acceptance='unknown',adoption=False,agent_heard=False,measurement_validated=False)
    check(list(outputs.values()));save(RUN/'feedback/voice-feedback.json',feedback)
    supplement=dict(record_id=feedback['response_record'],append_only_feedback=True,feedback=feedback,
        prior_report=ref(REPORT/'author-voice-swap-20261011.json'),table1_refs=['PER:S1']+[f'PARAM:C20.0{i}' for i in range(1,6)],
        inference='speaker composition changes perceived preference under author conditions; own composition alone does not fully reproduce inferior own result; output level also changed, no matched-loudness phonation claim',
        adoption=False,measurement_validated=False,general_rule_validated=False)
    save(RUN/'evaluation/voice-feedback-supplement.json',supplement);save(REPORT/(FEEDBACK_NAME+'.json'),supplement)
    (REPORT/(FEEDBACK_NAME+'.md')).write_text('''# 最后一页：作者声线替换反馈

用户原话“B比原版好点，但还是不如A”，计1条聚合回复，绑定作者原声线A、换成Normal75/Classic25的B及自己的原比较版。根据上轮三份音频标注，将“原版”按语境解释为自己的原比较版；用户没有再次显式命名，该解释保留为contextual inference。相对偏好为A优于B、B略优于自己的比较版；“好点”在本轮虚实语境下，不补造逐字实感、绝对自然度、无破音或咬字/响度副作用标签。

单组声线替换保留作者音高/音素/人工控制，A精确复现；因此声线组成及其预测/输出响应对这两句的相对偏好有贡献。B仍略优于自己的比较版，说明单换声线未完全重现自己的较弱结果；其余音乐、发声控制、时长/上下文仍未隔离。B整句电平代理比A约低1.72/1.11dB，未匹配响度，不把偏好差全归为独立的生理虚实通道或唯一病因。B不是制作版修复，不采用，作者A也不是整曲/通用配比验收。

下一组C保留作者A声线与完整音高，按声明默认值中和TENC=0、BREC=0、VOIC=100、SHFC=0曲线。焦点两句SHFC实际原为0，所以该因素没有实际干预覆盖，真正取消的是三人工增量；先检验这一组作用，不解释单个通道。原封存报告/run不改，表1PER:S1与C20、表2RESP:LASTPAGE-AUTHOR-VOICE-SWAP-01追加，Agent未听、measurement_validated=false、通用规律0。详见[反馈JSON](author-voice-feedback-20261011.json)和[下一组](author-control-neutral-20261011.md)。
''',encoding='utf-8',newline='\n')
    a=yaml.safe_load((PRIOR/'score/A.ustx').read_text(encoding='utf-8-sig'));c=copy.deepcopy(a)
    for k,v in NEUTRAL.items():
        assert a['expressions'][k]['default_value']==v
        curve=next(q for q in c['voice_parts'][0]['curves'] if q['abbr']==k);curve['ys']=[v]*len(curve['xs'])
    (RUN/'score/A.ustx').write_bytes((PRIOR/'score/A.ustx').read_bytes())
    (RUN/'score/C.ustx').write_text(yaml.safe_dump(c,allow_unicode=True,sort_keys=False),encoding='utf-8')
    for kind in ['roundtrip.ustx','phones.json','pitch.json']:
        p=RUN/f'native-inputs/A-{kind}';p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(PRIOR/f'native-inputs/A-{kind}',p)
    coverage=[]
    for ctx in [0,1]:
        for kind in ['phrase','variance']:
            p=RUN/f'native-inputs/A/{kind}_{ctx:03}.json';p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(PRIOR/f'native-inputs/A/{kind}_{ctx:03}.json',p)
        f=load(RUN/f'native-inputs/A/phrase_{ctx:03}.json');assert not np.any(f['tone_shift_cents'])
        coverage.append(dict(context=ctx,SHFC_nonzero_frames=0,nonzero_manual_frames={k:int(np.count_nonzero(v)) for k,v in f['expression_deltas'].items()}))
    save(RUN/'native-inputs/runtime.json',load(PRIOR/'native-inputs/runtime.json'))
    save(RUN/'design/protocol.json',dict(id='LASTPAGE-AUTHOR-CONTROL-NEUTRAL-01',status='frozen_before_execution',
        authorization='ongoing explicit user request for author-copy gradual factor research, after new A>B>own preference feedback',
        trigger=ref(RUN/'feedback/voice-feedback.json'),A=ref(RUN/'score/A.ustx'),C=ref(RUN/'score/C.ustx'),neutral_UI=NEUTRAL,actual_A_coverage=coverage,
        purpose='test whether authored manual phonation-control group is required for author-context relative advantage',
        fixed=['author full note/PITD/tuning/pitch/vibrato','phone clock/CLR','author two-stage speaker','DYN unity/gain1.5','seeds11/101'],
        permitted_changes=['three manual deltas/final acoustic channels','mel/wave'],
        grouping='written four curves neutralized across full part; selected two phrases have SHFC0 already, so real three-channel group only, variance conditions/predictions must remain exact',
        budget=dict(new_candidate=1,new_native_cached_contexts=3,reused_A_native_contexts=2,new_seeded_waveforms=8,independent_contexts=2,new_F0_calls=4,reused_A_F0_arrays=4),
        model_adapters=[ref(MODELS/'variance.onnx'),ref(MODELS/'acoustic.onnx')],
        alternatives_not_selected=['copy own controls onto different author clock','neutralize speaker and controls jointly','increase rejected doses or normalize level'],
        expected='A-C indicates combined manual-group effect only; if response supported then split active channels in a later frozen contrast, no individual causal attribution now',
        stops=['unexpected phone/pitch/speaker/variance change in selected contexts','A/repeat mismatch','nonfinite or file clipping','no new factor until feedback'],
        adoption=False,author_research_only=True,agent_heard=False,measurement_validated=False))
    runtime();print('Speaker preference bound; one three-active-channel group protocol frozen.',flush=True)


def native():
    runtime();exe=Path(load_config()['openutau_dir'])/'a2u-shfcprobe-20261008.exe';p=str(RUN/'score/C.ustx')
    cmds=[('roundtrip',['roundtrip','--project',p,'--out',str(RUN/'native-inputs/C-roundtrip.ustx')]),
        ('phones',['export-phonemes','--project',p,'--out',str(RUN/'native-inputs/C-phones.json')]),
        ('pitch',['export-pitch','--project',p,'--out',str(RUN/'native-inputs/C-pitch.json')]),
        ('render',['render','--project',p,'--out',str(RUN/'native-render/C.wav'),'--mixdown','--timeout','15']),
        ('probe',['export-render-probe','--project',p,'--out',str(RUN/'native-inputs/C'),'--indices','0,1'])]
    for kind,args in cmds:
        out=RUN/f'native-inputs/C-{kind}-result.json'
        if out.exists():continue
        print('Native C',kind,flush=True)
        p0=subprocess.run([str(exe),*args],cwd=exe.parent,capture_output=True,encoding='utf-8',errors='replace',timeout=1200)
        log=RUN/f'logs/C-{kind}.log';assert not log.exists();log.write_text(p0.stdout+p0.stderr,encoding='utf-8')
        assert p0.returncode==0,p0.stdout[-1000:]+p0.stderr[-1000:]
        r=json.loads(p0.stdout.strip().splitlines()[-1]);assert not r.get('errors') and r.get('ok',True);save(out,r)
    runtime();print('Native C complete; A native evidence reused.',flush=True)


def execute():
    assert load(RUN/'evaluation/native-independent-check.json')['status']=='passed' and not (RUN/'fresh').exists();runtime()
    import onnxruntime as ort
    options=ort.SessionOptions();options.intra_op_num_threads=options.inter_op_num_threads=1;options.execution_mode=ort.ExecutionMode.ORT_SEQUENTIAL
    f=load(RUN/'native-inputs/A/phrase_000.json')
    variance,acoustic,vocoder=[ort.InferenceSession(str(p),sess_options=options,providers=['CPUExecutionProvider']) for p in [MODELS/'variance.onnx',MODELS/'acoustic.onnx',f['vocoder_model']]]
    save(RUN/'fresh/start.json',dict(protocol=ref(RUN/'design/protocol.json'),model_adapters=load(RUN/'design/protocol.json')['model_adapters'],seeds=[11,101],max_waveforms=8,ort=ort.__version__,numpy=np.__version__))
    rows=[]
    for ctx in [0,1]:
        for label in ['A','C']:
            f=load(RUN/f'native-inputs/{label}/phrase_{ctx:03}.json');v=load(RUN/f'native-inputs/{label}/variance_{ctx:03}.json')
            for suffix in ['', '_repeat']:
                ac,va=tensors(f['tensors']),tensors(v['tensors']);n=ac['f0'].size;va['probe_noise']=gaussian_frame_noise(11,3,24,n)
                names=[o.name for o in variance.get_outputs()];pred=dict(zip(names,variance.run(names,model_feed(variance,va))));clipping={}
                for ch in CHANNELS:
                    lo,hi=(-10,10) if ch=='tension' else (-96,0);raw=pred[ch+'_pred']+np.asarray(f['expression_deltas'][ch],np.float32)[None,:]
                    clipping[ch]=int(np.count_nonzero((raw<lo)|(raw>hi)));ac[ch]=np.clip(raw,lo,hi).astype(np.float32)
                ac['probe_noise']=gaussian_frame_noise(101,1,128,n);mel=acoustic.run(['mel'],model_feed(acoustic,ac))[0];vm=mel.copy()
                if f['acoustic_mel_base']!=f['vocoder_mel_base']:vm*=np.log(10) if f['acoustic_mel_base']=='10' else 1/np.log(10)
                vf=np.asarray(f['vocoder_f0'],np.float32)[None,:];wave=vocoder.run(None,model_feed(vocoder,dict(mel=vm,f0=vf)))[0].reshape(-1)
                assert np.isfinite(wave).all() and len(wave)==n*512
                d=RUN/f'fresh/context{ctx}/{label}{suffix}';d.mkdir(parents=True);np.save(d/'raw.npy',wave)
                for name,x in [('inputs',ac),('variance-inputs',va),('predictions',pred),('mel',dict(mel=mel)),('vocoder-f0',dict(f0=vf))]:np.savez_compressed(d/(name+'.npz'),**x)
                rows.append(dict(context=ctx,variant=label+suffix,frames=n,samples=len(wave),feature_clipping=clipping,
                    wave_start_s=(f['position_ms']-f['head_frames']*float(np.float32(f['frame_ms'])))/1000,raw_peak=float(np.max(np.abs(wave)))))
                print('Fresh',ctx,label+suffix,'done',flush=True)
    runtime();save(RUN/'fresh/execution.json',dict(rows=rows,variance_calls=8,acoustic_vocoder_waveforms=8,measurement_validated=False))


if __name__=='__main__':{'prepare':prepare,'native':native,'execute':execute}[sys.argv[1]]()
