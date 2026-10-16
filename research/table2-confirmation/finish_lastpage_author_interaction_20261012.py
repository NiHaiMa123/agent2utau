"""Package D and explicitly reuse the three sealed factorial reference corners."""
import csv
import json
from pathlib import Path
import shutil
import subprocess
import sys

import numpy as np
import soundfile as sf

from assemble_lastpage_accepted_baseline_20261011 import ROOT,ENTRIES,load,save,sha,ref,check
from agent2utau.analysis.f0 import extract_f0
from agent2utau.resources.config import load_config
from shfc_pcm_checks import level,interval_indices
from observe_stage_2e_paths import f0_compare,stats

RUN=ROOT/'runs/experiments/lastpage-author-interaction-20261012'
CONTROL=ROOT/'runs/experiments/lastpage-author-control-neutral-20261011'
VOICE=ROOT/'runs/experiments/lastpage-author-voice-swap-20261011'
REPORT=ROOT/'docs/reports/lastpage'
NAME='author-interaction-20261012'
CHANNELS=['breathiness','voicing','tension']
OLD={'A':CONTROL,'B':VOICE,'C':CONTROL}


def read(path):
    with np.load(path,allow_pickle=False) as z:return {k:z[k].copy() for k in z.files}


def package():
    assert load(RUN/'evaluation/fresh-independent-check.json')['status']=='passed' and not (RUN/'delivery').exists()
    (RUN/'delivery').mkdir();sr=44100;start,end=[round(x*sr) for x in [212,220.5]];joined=np.zeros(end-start,np.float64);rows=[];outputs={}
    execution=load(RUN/'fresh/execution.json')['rows']
    for ctx in [0,1]:
        r=next(r for r in execution if r['context']==ctx and r['variant']=='D');wave=np.load(RUN/f'fresh/context{ctx}/D/raw.npy',allow_pickle=False)
        i=round(r['wave_start_s']*sr);lo,hi=max(start,i),min(end,i+len(wave));joined[lo-start:hi-start]+=wave[lo-i:hi-i].astype(np.float64)
        pcm=wave.astype(np.float64)*1.5;assert np.max(np.abs(pcm))<1
        p=RUN/f'evaluation/PCM-contexts/context{ctx}-D.wav';p.parent.mkdir(parents=True,exist_ok=True);sf.write(p,pcm,sr,subtype='PCM_24')
        rows.append(dict(context=ctx,variant='D',wave_start_s=r['wave_start_s'],samples=len(wave),PCM=ref(p)))
    joined*=1.5;assert np.isfinite(joined).all() and np.max(np.abs(joined))<1
    p=RUN/'delivery/D_two_phrases.wav';sf.write(p,joined,sr,subtype='PCM_24');outputs['D']=ref(p)
    for label,folder in OLD.items():
        p=RUN/f'delivery/{label}_two_phrases.wav';source=folder/f'delivery/{label}_two_phrases.wav';shutil.copyfile(source,p);assert sha(p)==sha(source);outputs[label]=ref(p)
        for ctx in [0,1]:
            p=RUN/f'evaluation/PCM-contexts/context{ctx}-{label}.wav';source=folder/f'evaluation/PCM-contexts/context{ctx}-{label}.wav';shutil.copyfile(source,p);assert sha(p)==sha(source)
            r=next(r for r in load(folder/'evaluation/delivery-check.json')['contexts'] if r['context']==ctx and r['variant']==label)
            rows.append(dict(context=ctx,variant=label,wave_start_s=r['wave_start_s'],samples=r['samples'],PCM=ref(p),reused=True,source=ref(source)))
    save(RUN/'evaluation/delivery-check.json',dict(outputs=outputs,contexts=rows,preview_s=[212,220.5],sample_rate=sr,samples=end-start,
        fixed_gain=1.5,subtype='PCM_24',DYN='all corner scores have absent DYN curve/default0dB unity',
        old_A_B_C_reused_original_bytes=True,new_D_deliveries=1,normalization_compression_BGM=False,agent_heard=False,measurement_validated=False))
    print('D and unchanged A/B/C packaged separately at common fixed gain.',flush=True)


def observe():
    assert not (RUN/'observations/start.json').exists()
    import torch
    import torchfcpe
    import librosa
    import onnxruntime as ort
    torch.set_num_threads(1);torch.set_num_interop_threads(1)
    rm=Path(load_config()['openutau_dir'])/'Dependencies/rmvpe/rmvpe.onnx';fc=Path(torchfcpe.__file__).parent/'assets/fcpe_c_v001.pt'
    models=[dict(path=str(p),sha256=sha(p)) for p in [rm,fc]];old_obs={l:load(folder/'observations/results.json') for l,folder in OLD.items()}
    for folder in set(OLD.values()):
        old_models=load(folder/'observations/start.json')['models'];assert all(m in old_models for m in models)
    reused=[b for l,obs in old_obs.items() for b in obs['detector_bindings'] if b['variant']==l];assert len(reused)==12
    save(RUN/'observations/start.json',dict(models=models,new_F0_calls_planned=4,A_B_C_arrays_reused=12,reused_bindings=reused,
        source=ref(Path(__file__)),packages=dict(torch=torch.__version__,ort=ort.__version__,librosa=librosa.__version__),ground_truth_calibration=False))
    options=ort.SessionOptions();options.intra_op_num_threads=options.inter_op_num_threads=1;options.execution_mode=ort.ExecutionMode.ORT_SEQUENTIAL
    session=ort.InferenceSession(str(rm),sess_options=options,providers=['CPUExecutionProvider'])
    def rmvpe(path):
        wave,sr=sf.read(path,dtype='float32');wave=librosa.resample(wave,orig_sr=sr,target_sr=16000)
        f0,uv=[np.asarray(x[0]) for x in session.run(None,dict(waveform=wave[None,:].astype(np.float32),threshold=np.array(.03,np.float32)))];n=min(len(f0),len(uv))
        return dict(f0_hz=f0[:n].astype(np.float32),voiced=~uv[:n].astype(bool),times=(np.arange(n)*.01).astype(np.float32),sr=16000,hop=160,frame_ms=10.)
    rows=[];bindings=[];calls=0;pack=load(RUN/'evaluation/delivery-check.json')
    for ctx in [0,1]:
        f=load(RUN/f'native-inputs/D/phrase_{ctx:03}.json');origin=next(r['wave_start_s'] for r in pack['contexts'] if r['context']==ctx and r['variant']=='D')
        pcm={};features={};det={}
        for l in ['A','B','C','D']:
            p=RUN/f'evaluation/PCM-contexts/context{ctx}-{l}.wav';pcm[l],_=sf.read(p,dtype='float64')
            folder=RUN if l=='D' else OLD[l];features[l]=read(folder/f'fresh/context{ctx}/{l}/inputs.npz');det[l]={}
            for name,fn in [('FCPE',extract_f0),('RMVPE',rmvpe)]:
                if l!='D':
                    b=next(b for b in reused if b['context']==ctx and b['variant']==l and b['detector']==name);check([b['input'],b['output']]);assert sha(p)==b['input']['sha256']
                    det[l][name]=read(ROOT/b['output']['path']);bindings.append(dict(b,reused=True,current_input=ref(p)))
                else:
                    r=fn(p);det[l][name]=r;out=RUN/f'observations/F0/context{ctx}-D-{name}.npz';out.parent.mkdir(parents=True,exist_ok=True)
                    np.savez_compressed(out,**{k:r[k] for k in ['f0_hz','voiced','times']});bindings.append(dict(context=ctx,variant=l,detector=name,input=ref(p),output=ref(out),reused=False,clock={k:r[k] for k in ['sr','hop','frame_ms']}))
                    calls+=1;print('New D F0',calls,'/4',ctx,name,flush=True)
        times=(f['position_ms']+(np.arange(features['D']['f0'].size)-f['head_frames'])*f['frame_ms'])/1000
        for old in [w for w in old_obs['C']['windows'] if w['context']==ctx]:
            w={k:old[k] for k in ['context','role','interval_s','note_index','lyric']};ix=interval_indices(w['interval_s'],origin,len(pcm['D'])) if w['role']!='whole_context' else (0,len(pcm['D']))
            w.update(sample_indices=ix,status='computed_proxy_only' if ix else 'unknown_outside_wave',variants={},comparisons={},interaction={})
            if ix:
                mask=(times>=w['interval_s'][0])&(times<w['interval_s'][1])
                for l in ['A','B','C','D']:
                    w['variants'][l]=dict(level=level(pcm[l][slice(*ix)]),features={ch:stats(features[l][ch].ravel()[mask]) for ch in CHANNELS},
                        feature_means={ch:float(np.mean(features[l][ch].ravel()[mask].astype(np.float64))) if mask.any() else None for ch in CHANNELS})
                for new,base in [('D','C'),('D','B'),('B','A'),('C','A')]:
                    a,b=[w['variants'][l]['level']['rms'] for l in [base,new]]
                    w['comparisons'][new+'-'+base]=dict(RMS_ratio_db=float(20*np.log10(b/a)) if a and b else None,
                        F0={name:f0_compare(det[base][name],det[new][name],w['interval_s'],origin) for name in ['FCPE','RMVPE']})
                d_c=w['comparisons']['D-C']['RMS_ratio_db'];b_a=w['comparisons']['B-A']['RMS_ratio_db']
                fm=w['variants'];w['interaction']=dict(RMS_db_difference_of_differences=(d_c-b_a) if d_c is not None and b_a is not None else None,
                    feature_mean_difference_of_differences={ch:(fm['D']['feature_means'][ch]-fm['C']['feature_means'][ch])-(fm['B']['feature_means'][ch]-fm['A']['feature_means'][ch]) if mask.any() else None for ch in CHANNELS},
                    meaning='four-corner finite numerical response only; not perceptual interaction, physiology or universal rule')
            rows.append(w)
    assert calls==4 and len(rows)==32
    for m in models:assert sha(Path(m['path']))==m['sha256']
    check(load(RUN/'protected-before.json'));save(RUN/'observations/results.json',dict(windows=rows,detector_bindings=bindings,new_F0_calls=4,reused_A_B_C_F0_arrays=12,
        new_word_labels=0,detector_truth='unknown; no calibration here',auditory_interaction='pending',agent_heard=False,measurement_validated=False))
    print('Four-corner finite proxies observed; auditory interaction remains pending.',flush=True)


def finish():
    assert load(RUN/'evaluation/delivery-independent-check.json')['status']=='passed'
    plan=load(RUN/'design/protocol.json');delivery=load(RUN/'evaluation/delivery-check.json');obs=load(RUN/'observations/results.json')
    fresh=load(RUN/'evaluation/fresh-independent-check.json')
    supplement=dict(record_id='RESP:LASTPAGE-AUTHOR-INTERACTION-01',comparisons=['D-C','D-B'],
        table1_refs=['PER:S1']+[f'PARAM:C20.0{i}' for i in range(1,6)]+['PARAM:C11.01','PARAM:C12.01','PARAM:C13.01'],
        existing_feedback_scope='A/B preference and C≈A are previous separate judgments, not new D feedback',
        new_D_feedback='pending',new_feedback_count=0,adoption=False,measurement_validated=False,general_rule_validated=False)
    table=ROOT/'docs/knowledge/acoustic-manifestations-20261009/control-details.csv'
    with table.open(encoding='utf-8') as f:ids={r['id'] for r in csv.DictReader(f)}
    assert set(supplement['table1_refs'][1:]).issubset(ids)
    save(RUN/'evaluation/table2-supplement.json',supplement)
    report=dict(status='author_interaction_delivered_pending_listening',protocol=plan,native=load(RUN/'evaluation/native-independent-check.json'),fresh=fresh,delivery=delivery,
        observations=ref(RUN/'observations/results.json'),table2_supplement=supplement,table_source=ref(table),agent_heard=False)
    save(REPORT/(NAME+'.json'),report)
    scalar=[]
    for w in obs['windows']:
        for comparison,v in w['comparisons'].items():scalar.append(dict(context=w['context'],note_index=w['note_index'],lyric=w['lyric'],window=w['role'],comparison=comparison,
            RMS_ratio_db=v['RMS_ratio_db'],FCPE_abs_cents_p50=v['F0']['FCPE']['abs_cents_p50'],RMVPE_abs_cents_p50=v['F0']['RMVPE']['abs_cents_p50'],interaction_RMS_db=w['interaction']['RMS_db_difference_of_differences']))
    with (REPORT/(NAME+'-windows.csv')).open('x',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(scalar[0]));writer.writeheader();writer.writerows(scalar)
    md='''# 最后一页：声线与人工控制的第四角D

2026-10-12。状态：author_interaction_delivered_pending_listening。用户“下一步”授权执行已冻结LASTPAGE-AUTHOR-SPEAKER-CONTROL-INTERACTION-01，原冻结文件原字节保持；不自动进入音符/时长变更。

|版|声线|人工控制|
|---|---|---|
|A|作者原mix，含时变/CLR余量|作者原TENC/BREC/VOIC|
|B|明确Normal75/Classic25|作者原TENC/BREC/VOIC|
|C|作者原mix|三人工增量0|
|D（本轮新）|明确Normal75/Classic25|三人工增量0|

所有角都保留相同作者42音符主轨part、notes tone/tuning、完整PITD/note.pitch、歌词、时长、音素/CLR和DYN，焦点两句SHFC原0。D仅以C副本换cl01..cl05为0/0/75/0/25，总量100；完整3句原生缓存技术单列，独立研究仅前两句。D−C检验零人工控制条件下的声线；D−B检验自己的声线条件下取消控制组。三个控制仍是一个组，不能归到单通道。

## 实际执行及独立门禁

当前47安装绑定与旧源输入、模型适配器及歌曲/Skill/作者保护SHA核对；独立原生读回确认完整pitch/phone时钟与A/B/C相同。D两阶段speaker精确Normal75/Classic25，与B一致；D variance完整输入和native预测精确B，人工增量为0精确C。新variance11/acoustic101/vocoder仅两句D/D_repeat，共4套新波形，重复在输入/预测/mel/vocoder F0/PCM精确；fresh预测精确旧B，最终三个通道由该预测零增量/合法裁剪重建。D−B只改三个最终声学通道，D−C只允许speaker及三个预测/最终输入响应。

A/B/C原波形、PCM、F0来源明确封存复用，没有新推理/新反馈，不冒称新A重测；本轮独立条件仍2个，技术重复不增加样本量。D按原生前导时钟在44100网格拼接、保留完整第二句尾部，mono PCM24、固定声增益1.5、无DYN曲线/默认0dB unity，无归一化/压缩/增益补偿/BGM。A/B/C整段和上下文PCM原文件字节复制精确。

D新4次FCPE/RMVPE；A/B/C因PCM与当前检测器模型SHA一致，显式复用12份旧数组。32整句/15字末音素与主体窗口、4组标量比较共128行，登记电平/F0/最终特征及差分之差(D−C)−(B−A)。差分之差是四角有限数值响应，不是已确认的听觉交互、生理机制或通用规律；检测器未经本批真值校准。模型特征裁剪按D逐句列明，旧A/B/C裁剪在各原报告保留，不修改原状态。

## 试听任务及范围

分开听D、C、B：D与C相比是否更虚；D与B相比是否更接近作者，或更接近自己的原版；未报破音/咬字/响度等unknown。此前A>B>自己的按语境偏好、C“很接近A”、A/P/N/PN均比自己的实分别保留，不预先给D排序或扩成逐字标签。若D仍有相对自己的优势，剩余音符主音/音乐阶段/时钟只能作为下一项有限候选；若组合作用明显，再冻结有依据的单通道或条件拆分，不自动修自己的全曲、扫比例/剂量或移植作者制作路线。

本轮仅新增一个研究D，未采用、新反馈0、Agent未听、measurement_validated=false、通用规律0。表1PER:S1、C20声线与C11–13控制、表2RESP:LASTPAGE-AUTHOR-INTERACTION-01追加。源unknown、原歌曲/音频/作者原件/Skill、旧阴性及旧抱C保持；单Agent，CI仅workflow_dispatch。

|句|D的BREC裁剪帧|VOIC裁剪帧|TENC裁剪帧|
|---|---:|---:|---:|
'''
    for r in fresh['rows']:
        c=r['feature_clipping'];md+=f'|{r["context"]}|{c["breathiness"]}|{c["voicing"]}|{c["tension"]}|\n'
    md+='\n'
    for label,p in delivery['outputs'].items():md+=f'- [{label}独立人声](../../../{p["path"]})\n'
    md+=f'\n[JSON]({NAME}.json)、[128窗口比較行]({NAME}-windows.csv)、[审计]({NAME}-audit.json)。\n'
    (REPORT/(NAME+'.md')).write_text(md,encoding='utf-8',newline='\n')
    status='当前状态author_interaction_delivered_pending_listening：2026-10-12用户“下一步”执行冻结第四角D=C+自己Normal75/Classic25，仅一个研究新D。两句D/D_repeat共4套固定种子新波形，原生3句缓存技术另列；原生pitch/phones/F0与A/B/C精确、两阶段speaker及variance预测精确B，人工增量0精确C，fresh预测精确B、重复/PCM门禁通过。A/B/C原字节与12 F0数组显式复用，新D4次双F0、32窗口/128比较行及差分之差仅代理，听觉交互待评、新反馈0/未采用。旧C接近A及声线偏好保留，不扩为D或单通道结论。原歌曲/音频/Skill/作者原件与unknown保持，Agent未听/通用规律0，单Agent/CI仅手动。'
    for n in ENTRIES:
        p=ROOT/n;lines=p.read_text(encoding='utf-8').splitlines();ix=[i for i,l in enumerate(lines) if '当前状态author_controls_feedback_closed_music_timing_reviewed：' in l];assert len(ix)==1,n
        rel='docs/reports/lastpage/'+NAME+'.md'
        if '/' in n:rel=('../../' if n.startswith('research/') else '../../../')+rel
        lines[ix[0]]=('- ' if lines[ix[0]].startswith('- ') else '')+status+f' 见[声线×控制第四角]({rel})。'
        if n=='plan.md':
            for i,l in enumerate(lines):
                if l.startswith('下一工作进入逐首更新，先《最后一页》：'):lines[i]='下一工作进入逐首更新，先《最后一页》：冻结D第四角已技术交付，A/B/C原字节复用。下一步接D−C与D−B实感及副作用反馈，结合前序偏好判断声线×人工控制组交互，再选择有依据的音乐/时钟或单通道有限验证；不把数值差分之差当听觉真值，不自动扫因素/比例或采用作者制作路线。'
        p.write_text('\n'.join(lines)+'\n',encoding='utf-8',newline='\n')
    check(load(RUN/'protected-before.json'))
    for p,h in load(RUN/'native-inputs/runtime.json').items():assert sha(Path(p))==h
    gate=subprocess.run([sys.executable,'tools/repository/check_repository.py','--worktree'],cwd=ROOT,capture_output=True,encoding='utf-8')
    (RUN/'logs/repository-gate.log').write_text(gate.stdout+gate.stderr,encoding='utf-8');assert gate.returncode==0,gate.stdout+gate.stderr
    audit=dict(status='passed_with_explicit_auditory_interaction_gaps',new_waveforms=4,new_variance_calls=4,new_native_cached_contexts=3,new_F0_calls=4,reused_A_B_C_F0_arrays=12,
        new_feedback=0,protected_references=len(load(RUN/'protected-before.json')),gate=gate.stdout.strip(),
        checks=[ref(RUN/f'evaluation/{k}-independent-check.json') for k in ['native','fresh','delivery']],
        sources=[ref(ROOT/'research/table2-confirmation'/n) for n in ['lastpage_author_interaction_20261012.py','check_lastpage_author_interaction_20261012.py','finish_lastpage_author_interaction_20261012.py','check_lastpage_author_interaction_delivery_20261012.py']],
        agent_heard=False,measurement_validated=False)
    save(RUN/'evaluation/audit.json',audit);save(REPORT/(NAME+'-audit.json'),audit)
    save(RUN/'completion-manifest.json',dict(status=report['status'],files=[ref(p) for p in sorted(RUN.rglob('*')) if p.is_file()],
        documents=[ref(p) for p in sorted(REPORT.glob(NAME+'*'))],entries=[ref(ROOT/n) for n in ENTRIES]))
    print(json.dumps(dict(status=report['status'],outputs=delivery['outputs'],gate=audit['gate']),ensure_ascii=False),flush=True)


if __name__=='__main__':{'package':package,'observe':observe,'finish':finish}[sys.argv[1]]()
