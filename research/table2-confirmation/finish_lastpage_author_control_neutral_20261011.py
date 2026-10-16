"""Package and bind the finite author manual-control group contrast."""
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

RUN=ROOT/'runs/experiments/lastpage-author-control-neutral-20261011'
PRIOR=ROOT/'runs/experiments/lastpage-author-voice-swap-20261011'
REPORT=ROOT/'docs/reports/lastpage'
NAME='author-control-neutral-20261011'
FEEDBACK_NAME='author-voice-feedback-20261011'
CHANNELS=['breathiness','voicing','tension']


def read(p):
    with np.load(p,allow_pickle=False) as z:return {k:z[k].copy() for k in z.files}


def package():
    assert load(RUN/'evaluation/fresh-independent-check.json')['status']=='passed' and not (RUN/'delivery').exists()
    (RUN/'delivery').mkdir();sr=44100;start,end=[round(x*sr) for x in [212,220.5]]
    execution=load(RUN/'fresh/execution.json')['rows'];rows=[];outputs={}
    for l in ['A','C']:
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
    source=ROOT/load(RUN/'feedback/voice-feedback.json')['audio']['own_original_comparator']['path'];shutil.copyfile(source,p)
    assert sha(p)==sha(source);outputs['own_original_comparator']=ref(p)
    d=yaml.safe_load((RUN/'score/A.ustx').read_text(encoding='utf-8-sig'))
    assert d['expressions']['dyn']['default_value']==0 and not any(c['abbr']=='dyn' and c['xs'] for c in d['voice_parts'][0]['curves'])
    save(RUN/'evaluation/delivery-check.json',dict(outputs=outputs,contexts=rows,preview_s=[212,220.5],samples=end-start,sample_rate=sr,
        fixed_gain=1.5,subtype='PCM_24',DYN='author absent curve/default0dB unity',A_PCM_and_WAV_bytes_exact_previous=True,
        own_comparator_unchanged=True,normalization_compression_BGM=False,agent_heard=False,measurement_validated=False))
    print('Same-gain C, exact accepted author A and unchanged own comparator packaged.',flush=True)

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
        det={'A':{},'C':{}};pcm={};features={}
        for l in ['A','C']:
            p=RUN/f'evaluation/PCM-contexts/context{ctx}-{l}.wav';pcm[l],_=sf.read(p,dtype='float64');features[l]=read(RUN/f'fresh/context{ctx}/{l}/inputs.npz')
            for name,fn in [('FCPE',extract_f0),('RMVPE',rmvpe)]:
                if l=='A':
                    b=next(b for b in reused if b['context']==ctx and b['detector']==name)
                    check([b['input'],b['output']]);assert sha(p)==b['input']['sha256'];r=read(ROOT/b['output']['path'])
                    det[l][name]=r;bindings.append(dict(b,reused=True,current_input=ref(p)))
                else:
                    r=fn(p);out=RUN/f'observations/F0/context{ctx}-C-{name}.npz';out.parent.mkdir(parents=True,exist_ok=True)
                    np.savez_compressed(out,**{k:r[k] for k in ['f0_hz','voiced','times']});det[l][name]=r
                    bindings.append(dict(context=ctx,variant=l,detector=name,input=ref(p),output=ref(out),reused=False,clock={k:r[k] for k in ['sr','hop','frame_ms']}))
                    calls+=1;print('New F0',calls,'/4',ctx,name,flush=True)
        t=(f['position_ms']+(np.arange(features['A']['f0'].size)-f['head_frames'])*f['frame_ms'])/1000
        for w in [w for w in old['windows'] if w['context']==ctx]:
            ix=interval_indices(w['interval_s'],origin,len(pcm['A'])) if w['role']!='whole_context' else (0,len(pcm['A']))
            r={k:w[k] for k in ['context','role','interval_s','note_index','lyric']}
            r.update(sample_indices=ix,status='computed_proxy_only' if ix else 'unknown_outside_wave',variants={},C_minus_A={})
            if ix:
                mask=(t>=w['interval_s'][0])&(t<w['interval_s'][1])
                for l in ['A','C']:r['variants'][l]=dict(level=level(pcm[l][slice(*ix)]),features={ch:stats(features[l][ch].ravel()[mask]) for ch in CHANNELS})
                a,b=[r['variants'][l]['level']['rms'] for l in ['A','C']]
                r['C_minus_A']=dict(RMS_ratio_db=float(20*np.log10(b/a)) if a and b else None,
                    F0={name:f0_compare(det['A'][name],det['C'][name],w['interval_s'],origin) for name in ['FCPE','RMVPE']},solidity='pending human feedback')
            rows.append(r)
    assert calls==4 and len(rows)==32
    for m in models:assert sha(Path(m['path']))==m['sha256']
    check(load(RUN/'protected-before.json'))
    save(RUN/'observations/results.json',dict(windows=rows,detector_bindings=bindings,new_F0_calls=4,reused_A_F0_arrays=4,
        new_word_labels=0,actual_output_F0_truth='unknown; detectors not calibrated here',agent_heard=False,measurement_validated=False))
    print('Finite C output observations and exact-PCM A F0 reuse bound.',flush=True)


def finish():
    assert load(RUN/'evaluation/delivery-independent-check.json')['status']=='passed'
    plan=load(RUN/'design/protocol.json');feedback=load(RUN/'feedback/voice-feedback.json');delivery=load(RUN/'evaluation/delivery-check.json')
    fresh=load(RUN/'evaluation/fresh-independent-check.json');obs=load(RUN/'observations/results.json')
    table=ROOT/'docs/knowledge/acoustic-manifestations-20261009/control-details.csv'
    with table.open(encoding='utf-8') as f:ids={r['id'] for r in csv.DictReader(f)}
    assert {'PARAM:C11.01','PARAM:C12.01','PARAM:C13.01','PARAM:C14.01'}.issubset(ids)
    supplement=dict(record_id='RESP:LASTPAGE-AUTHOR-CONTROL-NEUTRAL-01',comparison='C-A',perception='PER:S1',
        changed_control_refs=['PARAM:C11.01','PARAM:C12.01','PARAM:C13.01'],written_SHFC_neutral_ref='PARAM:C14.01',SHFC_active_intervention_frames=0,
        scope='three-active-manual-channel grouped neutralization, not independent-channel attribution',
        prior_feedback=ref(RUN/'evaluation/voice-feedback-supplement.json'),candidate_feedback='pending',adoption=False,measurement_validated=False,general_rule_validated=False)
    save(RUN/'evaluation/table2-supplement.json',supplement)
    report=dict(status='author_control_neutral_delivered_pending_listening',protocol=plan,voice_feedback=feedback,table2_supplement=supplement,
        native=load(RUN/'evaluation/native-independent-check.json'),fresh=fresh,delivery=delivery,observations=ref(RUN/'observations/results.json'),table_source=ref(table),agent_heard=False)
    save(REPORT/(NAME+'.json'),report)
    scalar=[]
    for w in obs['windows']:
        v=w['C_minus_A'];scalar.append(dict(context=w['context'],note_index=w['note_index'],lyric=w['lyric'],window=w['role'],RMS_ratio_db=v.get('RMS_ratio_db'),
            FCPE_abs_cents_p50=v.get('F0',{}).get('FCPE',{}).get('abs_cents_p50'),RMVPE_abs_cents_p50=v.get('F0',{}).get('RMVPE',{}).get('abs_cents_p50')))
    with (REPORT/(NAME+'-windows.csv')).open('x',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(scalar[0]));writer.writeheader();writer.writerows(scalar)
    md='''# 最后一页：作者条件下取消人工发声控制组

2026-10-11。状态：author_control_neutral_delivered_pending_listening。

上轮原话“B比原版好点，但还是不如A”计1聚合回复，绑定作者A、仅换自己Normal75/Classic25的B、自己的原比较版；“原版”按上轮音频标注作语境解释，不冒称用户重新明确命名。相对偏好A>B>自己的比较版，未细分各字实感/破音/咬字/响度或绝对验收。声线组成及其预测/电平等响应对这两句有贡献，但单换声线仍未完全重现自己的较弱结果；不声明唯一生理病因。[上轮反馈](author-voice-feedback-20261011.md)另行追加，封存pending报告不改。

继续用户明确要求的作者工程副本逐步替换。本轮C是一个控制组中和：保持作者A全部notes tone/tuning/PITD/note.pitch/内置vibrato、歌词、时长、音素/CLR和两阶段声线，仅在原xs网格将TENC=0、BREC=0、VOIC=100、SHFC=0设置为已读工程声明默认值。**焦点两句原SHFC实际都为0**，所以只在这两句实际取消TENC/BREC/VOIC三人工增量；不是四个独立试验，也不能得出SHFC作用。完整42音符/3句副本保留，第三句仅原生缓存技术，不用于所交付因果试听。

## 依赖与交付检查

原生独立读回确认中和值和原网格，整个音素/音高/两阶段speaker精确；选中两句variance全部输入、预测与vocoder F0精确不变。C三人工增量均0，最终输入按相同合法范围从同一预测重建，只有这三声学通道变化。A原生证据显式复用，C新原生3句缓存技术另列；研究两句A/A_repeat/C/C_repeat共8套新variance11/acoustic101/vocoder波形。同输入重复精确；新A全部输入/预测/mel/raw/PCM及WAV字节精确重现上轮作者A。

44100 mono PCM24，A/C同212–220.5秒及固定声增益1.5；DYN无曲线、声明默认0dB，采用unity包络。按原生前导时钟在44100网格叠加句尾、保留完整第二句释放，无归一化、压缩、增益补偿或BGM。自己的原比较版原字节另保留，只作主观差距定位，因果对照为C−A。电平变化也属于控制组实际响应，不把更响自动解释为更实。

C新4次FCPE/RMVPE，A因PCM和检测器模型SHA相同显式复用4份旧F0数组；32窗口覆盖2整句及15字末音素/主体。实际输出F0、电平和最终特征只为有限代理，检测器未经本次真值校准；固定vocoder F0输入不保证两份输出检测完全相同。模型特征下限裁剪按A/C逐项列明，保持合法执行，不将计数当听觉改善。

## 试听与适用范围

先比较C与精确原作者A：取消这组后实感是否下降、仍实或变化不明显，以及是否出现破音/咬字/音量副作用。若有影响，下一轮才冻结单通道拆分；若仍有相对自己的优势，只支持这组不是维持该优势的必要条件，不排除主音、时钟、声线交互或更小差别。当前未听反馈pending，未采用；不自动追加通道/剂量或修制作版。表1PER:S1、PARAM:C11/12/13.01三实际控制及C14.01无实际SHFC干预，表2RESP:LASTPAGE-AUTHOR-CONTROL-NEUTRAL-01开发记录，measurement_validated=false、通用规律0、Agent未听。

原歌曲/音频/作者原件/Skill保持，原Normal75/Classic25及抱C、Bright25与有限VOIC阴性保持。这里新“C”是作者控制组研究版，不覆盖旧3:04抱C的局部接受ID。单Agent、CI仅workflow_dispatch。

|句|版|BREC裁剪帧|VOIC裁剪帧|TENC裁剪帧|
|---|---|---:|---:|---:|
'''
    for row in fresh['rows']:
        c=row['feature_clipping'];md+=f'|{row["context"]}|{row["variant"]}|{c["breathiness"]}|{c["voicing"]}|{c["tension"]}|\n'
    md+='\n'
    for label,r in delivery['outputs'].items():md+=f'- [{label}独立人声](../../../{r["path"]})\n'
    md+=f'\n[JSON]({NAME}.json)、[32窗口CSV]({NAME}-windows.csv)、[审计]({NAME}-audit.json)。\n'
    (REPORT/(NAME+'.md')).write_text(md,encoding='utf-8',newline='\n')
    status='当前状态author_control_neutral_delivered_pending_listening：2026-10-11“B比原版好点但不如A”计1聚合回复，原版按上轮标注推定自己比较版，A>B>自己的相对偏好支持声线有贡献但未完全复现原差距，细分标签unknown。继续用户授权副本逐步替换，新C仅按默认值中和TENC/BREC/VOIC/SHFC，焦点两句SHFC原0，实际取消三人工增量；作者声线/全音高/音素保留，variance输入和预测精确。C新原生3句缓存另列，研究两句8套固定种子A/C及重复，A所有输入/预测/mel/raw/WAV与旧作者A精确、重复/依赖/PCM通过；C4次新双F0+A4数组显式复用。C待评未采用、不得解释单通道或SHFC作用，Agent未听/通用规律0，原歌/音频/Skill/作者原件及旧阴性/抱C保持，单Agent/CI仅手动。'
    for n in ENTRIES:
        p=ROOT/n;lines=p.read_text(encoding='utf-8').splitlines();matches=[i for i,l in enumerate(lines) if '当前状态author_voice_swap_delivered_pending_listening：' in l];assert len(matches)==1,n
        rel='docs/reports/lastpage/'+NAME+'.md'
        if '/' in n:rel=('../../' if n.startswith('research/') else '../../../')+rel
        ix=matches[0];lines[ix]=('- ' if lines[ix].startswith('- ') else '')+status+f' 见[作者控制组中和]({rel})。'
        if n=='plan.md':
            for i,l in enumerate(lines):
                if l.startswith('下一工作进入逐首更新，先《最后一页》：'):lines[i]='下一工作进入逐首更新，先《最后一页》：作者声线替换反馈按语境为A>B>自己比较版，已追加绑定。新作者研究C只取消三人工发声增量（SHFC焦点原0），作者声线/完整音高/音素保持，A精确保留、C技术交付；下一步接C−A实感及副作用反馈，再冻结有依据的单通道拆分或其它有限条件，不自动加量、扫因素或采用作者制作路线。'
        p.write_text('\n'.join(lines)+'\n',encoding='utf-8',newline='\n')
    check(load(RUN/'protected-before.json'))
    for p,h in load(RUN/'native-inputs/runtime.json').items():assert sha(Path(p))==h
    gate=subprocess.run([sys.executable,'tools/repository/check_repository.py','--worktree'],cwd=ROOT,capture_output=True,encoding='utf-8')
    (RUN/'logs/repository-gate.log').write_text(gate.stdout+gate.stderr,encoding='utf-8');assert gate.returncode==0,gate.stdout+gate.stderr
    audit=dict(status='passed_with_explicit_group_attribution_and_auditory_gaps',new_feedback_submissions=1,new_word_labels=0,new_waveforms=8,new_native_cached_contexts=3,
        SHFC_active_intervened_frames=0,new_F0_calls=4,reused_A_F0_arrays=4,protected_references=len(load(RUN/'protected-before.json')),gate=gate.stdout.strip(),
        checks=[ref(RUN/f'evaluation/{k}-independent-check.json') for k in ['native','fresh','delivery']],
        sources=[ref(ROOT/'research/table2-confirmation'/n) for n in ['lastpage_author_control_neutral_20261011.py','check_lastpage_author_control_neutral_20261011.py','finish_lastpage_author_control_neutral_20261011.py','check_lastpage_author_control_delivery_20261011.py']],
        group_only_not_single_channel_cause=True,originals_preserved=True,agent_heard=False,measurement_validated=False)
    save(RUN/'evaluation/audit.json',audit);save(REPORT/(NAME+'-audit.json'),audit)
    docs=[ref(p) for stem in [NAME,FEEDBACK_NAME] for p in sorted(REPORT.glob(stem+'*'))]
    save(RUN/'completion-manifest.json',dict(status=report['status'],files=[ref(p) for p in sorted(RUN.rglob('*')) if p.is_file()],documents=docs,entries=[ref(ROOT/n) for n in ENTRIES]))
    print(json.dumps(dict(status=report['status'],outputs=delivery['outputs'],gate=audit['gate']),ensure_ascii=False),flush=True)


if __name__=='__main__':{'package':package,'observe':observe,'finish':finish}[sys.argv[1]]()
