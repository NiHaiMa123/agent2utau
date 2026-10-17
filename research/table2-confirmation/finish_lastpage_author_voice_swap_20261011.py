"""Bound author-voice research delivery and finite output observations."""
import csv
import json
from pathlib import Path
import shutil
import subprocess
import sys

import numpy as np
import soundfile as sf
import yaml

from assemble_lastpage_accepted_baseline_20261011 import ROOT,ENTRIES,load,save,sha,ref,check
from agent2utau.analysis.f0 import extract_f0
from agent2utau.resources.config import load_config
from shfc_pcm_checks import level,interval_indices
from observe_stage_2e_paths import f0_compare,stats

RUN=ROOT/'runs/experiments/lastpage-author-voice-swap-20261011'
PRIOR=ROOT/'runs/experiments/lastpage-author-pitch-ablation-20261011'
REPORT=ROOT/'docs/reports/lastpage'
NAME='author-voice-swap-20261011'
FEEDBACK_NAME='author-pitch-feedback-20261011'
CHANNELS=['breathiness','voicing','tension']


def read(p):
    with np.load(p,allow_pickle=False) as z:return {k:z[k].copy() for k in z.files}


def package():
    assert load(RUN/'evaluation/fresh-independent-check.json')['status']=='passed' and not (RUN/'delivery').exists()
    (RUN/'delivery').mkdir();sr=44100;start,end=[round(x*sr) for x in [212,220.5]]
    execution=load(RUN/'fresh/execution.json')['rows'];rows=[];outputs={}
    for l in ['A','B']:
        joined=np.zeros(end-start,np.float64)
        for ctx in [0,1]:
            r=next(r for r in execution if r['context']==ctx and r['variant']==l)
            wave=np.load(RUN/f'fresh/context{ctx}/{l}/raw.npy',allow_pickle=False);i=round(r['wave_start_s']*sr)
            lo,hi=max(start,i),min(end,i+len(wave));joined[lo-start:hi-start]+=wave[lo-i:hi-i].astype(np.float64)
            pcm=wave.astype(np.float64)*1.5;assert np.max(np.abs(pcm))<1
            p=RUN/f'evaluation/PCM-contexts/context{ctx}-{l}.wav';p.parent.mkdir(parents=True,exist_ok=True);sf.write(p,pcm,sr,subtype='PCM_24')
            if l=='A':assert sha(p)==sha(PRIOR/f'evaluation/PCM-contexts/context{ctx}-A.wav')
            rows.append(dict(context=ctx,variant=l,wave_start_s=r['wave_start_s'],samples=len(wave),PCM=ref(p)))
        joined*=1.5;assert np.isfinite(joined).all() and np.max(np.abs(joined))<1
        p=RUN/f'delivery/{l}_two_phrases.wav';sf.write(p,joined,sr,subtype='PCM_24');outputs[l]=ref(p)
        if l=='A':assert sha(p)==sha(PRIOR/'delivery/A_two_phrases.wav')
    p=RUN/'delivery/own_original_comparator.wav'
    source=ROOT/load(RUN/'feedback/pitch-feedback.json')['own_comparator']['path'];shutil.copyfile(source,p)
    assert sha(p)==sha(source);outputs['own_original_comparator']=ref(p)
    d=yaml.safe_load((RUN/'score/A.ustx').read_text(encoding='utf-8-sig'))
    assert d['expressions']['dyn']['default_value']==0 and not any(c['abbr']=='dyn' and c['xs'] for c in d['voice_parts'][0]['curves'])
    save(RUN/'evaluation/delivery-check.json',dict(outputs=outputs,contexts=rows,preview_s=[212,220.5],samples=end-start,sample_rate=sr,
        fixed_gain=1.5,subtype='PCM_24',DYN='author absent curve/default0dB unity',A_PCM_and_WAV_bytes_exact_previous=True,
        own_comparator_unchanged=True,normalization_compression_BGM=False,agent_heard=False,measurement_validated=False))
    print('Same-gain B, exact accepted author A and unchanged own comparator packaged.',flush=True)


def observe():
    assert not (RUN/'observations/start.json').exists()
    import torch
    import torchfcpe
    import librosa
    import onnxruntime as ort
    torch.set_num_threads(1);torch.set_num_interop_threads(1)
    rm=Path(load_config()['openutau_dir'])/'Dependencies/rmvpe/rmvpe.onnx';fc=Path(torchfcpe.__file__).parent/'assets/fcpe_c_v001.pt'
    models=[dict(path=str(p),sha256=sha(p)) for p in [rm,fc]]
    old=load(PRIOR/'observations/results.json');old_start=load(PRIOR/'observations/start.json')
    assert all(any(m==p for p in old_start['models']) for m in models)
    reused=[b for b in old['detector_bindings'] if b['variant']=='A'];assert len(reused)==4
    save(RUN/'observations/start.json',dict(models=models,new_F0_calls_planned=4,A_F0_arrays_reused=4,
        reused_A_bindings=reused,source=ref(Path(__file__)),packages=dict(torch=torch.__version__,ort=ort.__version__,librosa=librosa.__version__),ground_truth_calibration=False))
    opts=ort.SessionOptions();opts.intra_op_num_threads=opts.inter_op_num_threads=1;opts.execution_mode=ort.ExecutionMode.ORT_SEQUENTIAL
    session=ort.InferenceSession(str(rm),sess_options=opts,providers=['CPUExecutionProvider'])
    def rmvpe(path):
        wave,sr=sf.read(path,dtype='float32');wave=librosa.resample(wave,orig_sr=sr,target_sr=16000)
        f0,uv=[np.asarray(x[0]) for x in session.run(None,dict(waveform=wave[None,:].astype(np.float32),threshold=np.array(.03,np.float32)))];n=min(len(f0),len(uv))
        return dict(f0_hz=f0[:n].astype(np.float32),voiced=~uv[:n].astype(bool),times=(np.arange(n)*.01).astype(np.float32),sr=16000,hop=160,frame_ms=10.)
    rows=[];bindings=[];calls=0
    for ctx in [0,1]:
        f=load(RUN/f'native-inputs/A/phrase_{ctx:03}.json');pack=load(RUN/'evaluation/delivery-check.json')
        origin=next(r['wave_start_s'] for r in pack['contexts'] if r['context']==ctx and r['variant']=='A')
        det={'A':{},'B':{}};pcm={};features={}
        for l in ['A','B']:
            p=RUN/f'evaluation/PCM-contexts/context{ctx}-{l}.wav';pcm[l],_=sf.read(p,dtype='float64');features[l]=read(RUN/f'fresh/context{ctx}/{l}/inputs.npz')
            for name,fn in [('FCPE',extract_f0),('RMVPE',rmvpe)]:
                if l=='A':
                    b=next(b for b in reused if b['context']==ctx and b['detector']==name)
                    check([b['input'],b['output']]);assert sha(p)==b['input']['sha256'];r=read(ROOT/b['output']['path'])
                    det[l][name]=r;bindings.append(dict(**b,reused=True,current_input=ref(p)))
                else:
                    r=fn(p);out=RUN/f'observations/F0/context{ctx}-B-{name}.npz';out.parent.mkdir(parents=True,exist_ok=True)
                    np.savez_compressed(out,**{k:r[k] for k in ['f0_hz','voiced','times']});det[l][name]=r
                    bindings.append(dict(context=ctx,variant=l,detector=name,input=ref(p),output=ref(out),reused=False,clock={k:r[k] for k in ['sr','hop','frame_ms']}))
                    calls+=1;print('New F0',calls,'/4',ctx,name,flush=True)
        t=(f['position_ms']+(np.arange(features['A']['f0'].size)-f['head_frames'])*f['frame_ms'])/1000
        for w in [w for w in old['windows'] if w['context']==ctx]:
            ix=interval_indices(w['interval_s'],origin,len(pcm['A'])) if w['role']!='whole_context' else (0,len(pcm['A']))
            r={k:w[k] for k in ['context','role','interval_s','note_index','lyric']}
            r.update(sample_indices=ix,status='computed_proxy_only' if ix else 'unknown_outside_wave',variants={},B_minus_A={})
            if ix:
                mask=(t>=w['interval_s'][0])&(t<w['interval_s'][1])
                for l in ['A','B']:r['variants'][l]=dict(level=level(pcm[l][slice(*ix)]),features={ch:stats(features[l][ch].ravel()[mask]) for ch in CHANNELS})
                a,b=[r['variants'][l]['level']['rms'] for l in ['A','B']]
                r['B_minus_A']=dict(RMS_ratio_db=float(20*np.log10(b/a)) if a and b else None,
                    F0={name:f0_compare(det['A'][name],det['B'][name],w['interval_s'],origin) for name in ['FCPE','RMVPE']},solidity='pending human feedback')
            rows.append(r)
    assert calls==4 and len(rows)==32
    for m in models:assert sha(Path(m['path']))==m['sha256']
    check(load(RUN/'protected-before.json'))
    save(RUN/'observations/results.json',dict(windows=rows,detector_bindings=bindings,new_F0_calls=4,reused_A_F0_arrays=4,
        new_word_labels=0,actual_output_F0_truth='unknown; detectors not calibrated here',agent_heard=False,measurement_validated=False))
    print('Finite B output observations and exact-PCM A F0 reuse bound.',flush=True)


def finish():
    assert load(RUN/'evaluation/delivery-independent-check.json')['status']=='passed'
    plan=load(RUN/'design/protocol.json');feedback=load(RUN/'feedback/pitch-feedback.json');delivery=load(RUN/'evaluation/delivery-check.json')
    fresh=load(RUN/'evaluation/fresh-independent-check.json');obs=load(RUN/'observations/results.json')
    table=ROOT/'docs/knowledge/acoustic-manifestations-20261009/control-details.csv'
    with table.open(encoding='utf-8') as f:ids={r['id'] for r in csv.DictReader(f)}
    assert {f'PARAM:C20.0{i}' for i in range(1,6)}.issubset(ids)
    supplement=dict(record_id='RESP:LASTPAGE-AUTHOR-VOICE-SWAP-01',comparison='B-A',perception='PER:S1',
        control_refs=[f'PARAM:C20.0{i}' for i in range(1,6)],scope='one full speaker-composition factor under two seen author contexts; both-stage dependency allowed',
        prior_pitch_feedback=ref(RUN/'evaluation/pitch-feedback-supplement.json'),new_candidate_feedback='pending',adoption=False,measurement_validated=False,general_rule_validated=False)
    save(RUN/'evaluation/table2-supplement.json',supplement)
    report=dict(status='author_voice_swap_delivered_pending_listening',protocol=plan,pitch_feedback=feedback,table2_supplement=supplement,
        native=load(RUN/'evaluation/native-independent-check.json'),fresh=fresh,delivery=delivery,observations=ref(RUN/'observations/results.json'),
        table_source=ref(table),agent_heard=False)
    save(REPORT/(NAME+'.json'),report)
    rows=[]
    for w in obs['windows']:
        v=w['B_minus_A'];rows.append(dict(context=w['context'],note_index=w['note_index'],lyric=w['lyric'],window=w['role'],RMS_ratio_db=v.get('RMS_ratio_db'),
            FCPE_abs_cents_p50=v.get('F0',{}).get('FCPE',{}).get('abs_cents_p50'),RMVPE_abs_cents_p50=v.get('F0',{}).get('RMVPE',{}).get('abs_cents_p50')))
    with (REPORT/(NAME+'-windows.csv')).open('x',encoding='utf-8',newline='') as f:
        wr=csv.DictWriter(f,fieldnames=list(rows[0]));wr.writeheader();wr.writerows(rows)
    md='''# 最后一页：作者条件下仅换成自己的声线

状态：author_voice_swap_delivered_pending_listening。用户“都比我们的实”的1条聚合回复已单独绑定四版A/P/N/PN；它们均保持相对自己的实感优势，但四版排序、差别大小、副作用及逐字标签unknown。[音高拆分反馈](author-pitch-feedback-20261011.md)保留有限结论，不能宣布音符主音/所有pitch无关。

继续用户明确要求的作者工程副本逐因素研究。本轮一个新候选B：仅把作者cl01..cl05混合改为明确Normal75/Classic25，总量100；CLR/音素、作者完整PITD/note.pitch、notes tone/tuning、歌词、时长、所有人工TENC/BREC/VOIC/SHFC保留。作者原混合有时变与默认声色余量，不将里/看的Bright40/Cute60代称整句。以前在自己工程将Classic25换成Bright25的阴性不是这次作者条件下替换实验。

先以原生独立检查确认两阶段B精确Normal75/Classic25、非speaker原始条件/人工增量与整个音素/音高精确保持。声线改变允许三预测与最终三通道、mel/波形随之响应，不要求新预测保持旧speaker值。A原生材料为已绑定显式复用，不冒称新导出；B完整42音符/3句原生缓存技术单列。真正研究前两句，每句A/A_repeat/B/B_repeat，共8套新variance11/acoustic101/vocoder波形，只有2个独立上下文。新A全部输入/预测/mel/F0/raw与刚获相对实感支持的上轮A精确；重复均精确。

三份独立音频：B为作者条件+自己声线，A为作者原mix、原WAV字节精确重现，自己的原比较音频原字节另保留。A/B皆212–220.5秒、44100 mono PCM24、固定1.5、原DYN默认0dB/无曲线unity、按原生前导时钟拼接；无归一化/压缩/增益补偿/BGM。自己的旧比较在209.4–218秒，时钟、音乐、控制不同，仅作原主观差距定位，因果比较是B−A。

B新增4次双F0观测，A PCM字节精确且检测器模型SHA相同，显式复用4份已绑定A F0数组；共32窗口覆盖2整句及15字末音素/主体。电平、F0、特征与裁剪数量均代理，不能代替实感或生理病因。作者A已有VOIC下限裁剪，B按新预测合法裁剪，逐项列明，不以裁剪计数推断改善。

试听判别：B是否变虚、更接近自己的版本，或仍像A一样实；字头、破音、咬字、音量等副作用未报unknown。若B变虚，只支持声线在这些作者条件下有贡献，不能认定唯一病因或通用配比；若仍实，说明单换声线不足，下一项再按反馈选择非声线控制因素。当前B未采用、反馈待评，不自动继续下一因素、扫比例或加量。原自己的制作版/抱C、Bright25与VOIC阴性/作者原件/Skill保持；表1PER:S1和PARAM:C20.01–05、表2RESP:LASTPAGE-AUTHOR-VOICE-SWAP-01有限记录，measurement_validated=false、通用规律0，Agent未听，单Agent/CI仅手动。

|句|版|BREC裁剪帧|VOIC裁剪帧|TENC裁剪帧|
|---|---|---:|---:|---:|
'''
    for r in fresh['rows']:
        c=r['feature_clipping'];md+=f'|{r["context"]}|{r["variant"]}|{c["breathiness"]}|{c["voicing"]}|{c["tension"]}|\n'
    md+='\n'
    for l,p in delivery['outputs'].items():md+=f'- [{l}独立人声](../../../{p["path"]})\n'
    md+=f'\n[JSON]({NAME}.json)、[窗口CSV]({NAME}-windows.csv)、[审计]({NAME}-audit.json)。\n'
    (REPORT/(NAME+'.md')).write_text(md,encoding='utf-8',newline='\n')
    status='当前状态author_voice_swap_delivered_pending_listening：2026-10-11“都比我们的实”计1聚合回复，绑定作者A/P/N/PN均优于自己两句；细部两曲线非保持该优势必要条件，四版排序/副作用/逐字标签unknown，不排除主音或其它条件。继续用户授权逐因素副本研究，仅将作者声线换为自己Normal75/Classic25，音素/完整音高/人工控制保持、三预测允许响应。B新原生3句缓存技术另列，研究2句×A/B及重复=8套固定种子新波形；新A与上轮获支持A全部输入/预测/mel/raw/WAV精确，独立隔离/重复/PCM及B4次新双F0+A4数组显式复用通过。B待评未采用，Agent未听、通用规律0；原歌曲/音频/作者原件/Skill和旧阴性保持，单Agent/CI仅手动。'
    for n in ENTRIES:
        p=ROOT/n;lines=p.read_text(encoding='utf-8').splitlines();ix=[i for i,l in enumerate(lines) if '当前状态author_pitch_ablation_delivered_pending_listening：' in l];assert len(ix)==1,n
        rel='docs/reports/lastpage/'+NAME+'.md'
        if '/' in n:rel=('../../' if n.startswith('research/') else '../../../')+rel
        lines[ix[0]]=('- ' if lines[ix[0]].startswith('- ') else '')+status+f' 见[作者条件单组声线对照]({rel})。'
        if n=='plan.md':
            for i,l in enumerate(lines):
                if l.startswith('下一工作进入逐首更新，先《最后一页》：'):lines[i]='下一工作进入逐首更新，先《最后一页》：作者四版音高拆分均比自己的实，反馈已绑定；本次仅换自己的Normal75/Classic25声线到作者工程副本，A精确保留、新B技术交付。下一步接B相对A及原自己版的虚实/副作用反馈，再选后续有限因素；不把曲线移除结果扩大为全部音高无关，不自动扫比例或采用作者制作路线。'
        p.write_text('\n'.join(lines)+'\n',encoding='utf-8',newline='\n')
    check(load(RUN/'protected-before.json'))
    for p,h in load(RUN/'native-inputs/runtime.json').items():assert sha(Path(p))==h
    gate=subprocess.run([sys.executable,'tools/repository/check_repository.py','--worktree'],cwd=ROOT,capture_output=True,encoding='utf-8')
    (RUN/'logs/repository-gate.log').write_text(gate.stdout+gate.stderr,encoding='utf-8');assert gate.returncode==0,gate.stdout+gate.stderr
    audit=dict(status='passed_with_explicit_auditory_gaps',new_feedback_submissions=1,new_per_word_labels=0,new_waveforms=8,new_native_cached_contexts=3,new_F0_calls=4,reused_A_F0_arrays=4,
        protected_references=len(load(RUN/'protected-before.json')),gate=gate.stdout.strip(),
        checks=[ref(RUN/f'evaluation/{k}-independent-check.json') for k in ['native','fresh','delivery']],
        sources=[ref(ROOT/'research/table2-confirmation'/n) for n in ['lastpage_author_voice_swap_20261011.py','check_lastpage_author_voice_swap_20261011.py','finish_lastpage_author_voice_swap_20261011.py','check_lastpage_author_voice_delivery_20261011.py']],
        originals_preserved=True,agent_heard=False,measurement_validated=False)
    save(RUN/'evaluation/audit.json',audit);save(REPORT/(NAME+'-audit.json'),audit)
    documents=[ref(p) for stem in [NAME,FEEDBACK_NAME] for p in sorted(REPORT.glob(stem+'*'))]
    save(RUN/'completion-manifest.json',dict(status=report['status'],files=[ref(p) for p in sorted(RUN.rglob('*')) if p.is_file()],documents=documents,entries=[ref(ROOT/n) for n in ENTRIES]))
    print(json.dumps(dict(status=report['status'],outputs=delivery['outputs'],gate=audit['gate']),ensure_ascii=False),flush=True)


if __name__=='__main__':{'package':package,'observe':observe,'finish':finish}[sys.argv[1]]()
