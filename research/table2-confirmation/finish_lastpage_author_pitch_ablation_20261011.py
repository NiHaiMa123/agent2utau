"""Package, observe, and seal the explicitly authorized four-version research."""
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
from agent2utau.resources.config import load_config
from agent2utau.analysis.f0 import extract_f0
from shfc_pcm_checks import level, interval_indices
from observe_stage_2e_paths import f0_compare, stats

RUN=ROOT/'runs/experiments/lastpage-author-pitch-ablation-20261011'
AUTHOR=ROOT/'runs/research/lastpage-li-kan-author-reference-20261011'
NAME='author-pitch-ablation-20261011'
REPORT=ROOT/'docs/reports/lastpage'
LABELS=['A','P','N','PN']
CHANNELS=['breathiness','voicing','tension']


def read(p):
    with np.load(p,allow_pickle=False) as z:return {k:z[k].copy() for k in z.files}


def package():
    assert load(RUN/'evaluation/fresh-independent-check.json')['status']=='passed'
    assert not (RUN/'delivery').exists()
    (RUN/'delivery').mkdir()
    sr=44100;lo=round(212*sr);hi=round(220.5*sr)
    execution=load(RUN/'fresh/execution.json')['rows'];outputs={};rows=[]
    for label in LABELS:
        joined=np.zeros(hi-lo,np.float64)
        for ctx in [0,1]:
            r=next(r for r in execution if r['variant']==label and r['context']==ctx)
            f=load(RUN/f'native-inputs/{label}/phrase_{ctx:03}.json')
            wave=np.load(RUN/f'fresh/context{ctx}/{label}/raw.npy',allow_pickle=False)
            start=round(r['wave_start_s']*sr)
            a,b=max(lo,start),min(hi,start+len(wave))
            assert a<b
            joined[a-lo:b-lo]+=wave[a-start:b-start].astype(np.float64)
            pcm=wave.astype(np.float64)*1.5;assert np.max(np.abs(pcm))<1
            p=RUN/f'evaluation/PCM-contexts/context{ctx}-{label}.wav';p.parent.mkdir(parents=True,exist_ok=True)
            sf.write(p,pcm,sr,subtype='PCM_24')
            rows.append(dict(context=ctx,variant=label,wave_start_s=r['wave_start_s'],samples=len(wave),
                end_s=r['wave_start_s']+len(wave)/sr,phone_end_s=f['phones'][-1]['endMs']/1000,PCM=ref(p)))
        joined*=1.5;assert np.isfinite(joined).all() and np.max(np.abs(joined))<1
        path=RUN/f'delivery/{label}_two_phrases.wav';sf.write(path,joined,sr,subtype='PCM_24')
        outputs[label]=ref(path)
    source=AUTHOR/'delivery/baishuo_current165c_reference_vocal.wav'
    target=RUN/'delivery/previous_liked_author_reference.wav';shutil.copyfile(source,target);assert sha(source)==sha(target)
    outputs['previous_liked_reference']=ref(target)
    doc=yaml.safe_load((RUN/'score/A.ustx').read_text(encoding='utf-8-sig'))
    assert not any(c['abbr']=='dyn' and c['xs'] for c in doc['voice_parts'][0]['curves'])
    assert doc['expressions']['dyn']['default_value']==0
    assert doc['tracks'][0]['volume']==0 and doc['tracks'][0]['pan']==-100
    save(RUN/'evaluation/delivery-check.json',dict(outputs=outputs,contexts=rows,preview_s=[212,220.5],
        sample_rate=sr,samples=hi-lo,subtype='PCM_24',fixed_gain=1.5,
        dynamics='No authored DYN curve, declared default0 dB; unity envelope on fresh raw waveform. No normalization/compression.',
        clock='Each native position_ms minus 8 float32 frame periods; round origin to 44100 grid, sum tails in float64.',
        preview_tail='Extends prior 220.35 end to 220.50 to include complete second phrase release; third native phrase deliberately excluded.',
        previous_reference_unchanged=True,agent_heard=False,measurement_validated=False))
    print('Five separate listening files packaged.',flush=True)


def observe():
    assert not (RUN/'observations/start.json').exists()
    import torch
    import torchfcpe
    import librosa
    import onnxruntime as ort
    torch.set_num_threads(1);torch.set_num_interop_threads(1)
    rm=Path(load_config()['openutau_dir'])/'Dependencies/rmvpe/rmvpe.onnx'
    fc=Path(torchfcpe.__file__).parent/'assets/fcpe_c_v001.pt'
    models=[dict(path=str(p),sha256=sha(p)) for p in [fc,rm]]
    inputs=[ref(RUN/f'evaluation/PCM-contexts/context{ctx}-{l}.wav') for ctx in [0,1] for l in LABELS]
    save(RUN/'observations/start.json',dict(models=models,inputs=inputs,planned_F0_calls=16,
        source=ref(Path(__file__)),packages=dict(torch=torch.__version__,librosa=librosa.__version__,ort=ort.__version__),
        ground_truth_calibration=False,agent_heard=False))
    opts=ort.SessionOptions();opts.intra_op_num_threads=opts.inter_op_num_threads=1;opts.execution_mode=ort.ExecutionMode.ORT_SEQUENTIAL
    session=ort.InferenceSession(str(rm),sess_options=opts,providers=['CPUExecutionProvider'])
    def rmvpe(path):
        wav,sr=sf.read(path,dtype='float32');wav=librosa.resample(wav,orig_sr=sr,target_sr=16000)
        out=session.run(None,dict(waveform=wav[None,:].astype(np.float32),threshold=np.array(.03,np.float32)))
        f0,uv=[np.asarray(x[0]) for x in out];n=min(len(f0),len(uv))
        return dict(f0_hz=f0[:n].astype(np.float32),voiced=~uv[:n].astype(bool),times=(np.arange(n)*.01).astype(np.float32),sr=16000,hop=160,frame_ms=10.)
    phones=load(RUN/'native-inputs/A-phones.json')['parts'][0]['phrases']
    doc=yaml.safe_load((RUN/'score/A.ustx').read_text(encoding='utf-8-sig'));notes=doc['voice_parts'][0]['notes']
    execution=load(RUN/'fresh/execution.json')['rows'];bindings=[];rows=[];calls=0
    for ctx in [0,1]:
        origin=next(r['wave_start_s'] for r in execution if r['context']==ctx and r['variant']=='A')
        pcm={};det={};features={}
        for label in LABELS:
            path=RUN/f'evaluation/PCM-contexts/context{ctx}-{label}.wav'
            pcm[label],_=sf.read(path,dtype='float64');features[label]=read(RUN/f'fresh/context{ctx}/{label}/inputs.npz');det[label]={}
            for name,fn in [('FCPE',extract_f0),('RMVPE',rmvpe)]:
                r=fn(path);det[label][name]=r
                p=RUN/f'observations/F0/context{ctx}-{label}-{name}.npz';p.parent.mkdir(parents=True,exist_ok=True)
                np.savez_compressed(p,**{k:r[k] for k in ['f0_hz','voiced','times']})
                bindings.append(dict(context=ctx,variant=label,detector=name,input=ref(path),output=ref(p),clock={k:r[k] for k in ['sr','hop','frame_ms']}))
                calls+=1;print('F0',calls,'/16',ctx,label,name,flush=True)
        windows=[dict(role='whole_context',interval_s=[origin,origin+len(pcm['A'])/44100],note_index=None,lyric=None)]
        for ix,note in enumerate(notes[:26]):
            if note['lyric'] in ['+','AP','EP']:continue
            ps=[p for p in phones[ctx]['phones'] if ix in p['owner_primary_indices']]
            if not ps:continue
            # Last phone carries the syllable nucleus in this bound Chinese inventory;
            # preserve token identity rather than treating it as a phonation label.
            p=ps[-1];s,e=p['start_ms']/1000,p['end_ms']/1000
            for role,a,b in [('last_phone',s,e),('core15_85',s+.15*(e-s),e-.15*(e-s))]:
                windows.append(dict(role=role,interval_s=[a,b],note_index=ix,lyric=note['lyric'],phoneme=p['phoneme']))
        f=load(RUN/f'native-inputs/A/phrase_{ctx:03}.json')
        times=(f['position_ms']+(np.arange(features['A']['f0'].size)-f['head_frames'])*f['frame_ms'])/1000
        for w in windows:
            ix=interval_indices(w['interval_s'],origin,len(pcm['A'])) if w['role']!='whole_context' else (0,len(pcm['A']))
            r=dict(context=ctx,**w,sample_indices=ix,variants={},comparisons={},status='computed_proxy_only' if ix else 'unknown_outside_wave')
            if ix:
                mask=(times>=w['interval_s'][0])&(times<w['interval_s'][1])
                for l in LABELS:
                    r['variants'][l]=dict(level=level(pcm[l][slice(*ix)]),final_features={ch:stats(features[l][ch].ravel()[mask]) for ch in CHANNELS})
                for l,base in [('P','A'),('N','A'),('PN','P'),('PN','N')]:
                    a,b=[r['variants'][k]['level']['rms'] for k in [base,l]]
                    r['comparisons'][l+'-'+base]=dict(RMS_ratio_db=float(20*np.log10(b/a)) if a and b else None,
                        F0={name:f0_compare(det[base][name],det[l][name],w['interval_s'],origin) for name in ['FCPE','RMVPE']})
            rows.append(r)
    assert calls==16
    for m in models:assert sha(Path(m['path']))==m['sha256']
    check(inputs);check(load(RUN/'protected-before.json'))
    save(RUN/'observations/results.json',dict(windows=rows,detector_bindings=bindings,actual_F0_calls=calls,
        detector_truth_and_solidity='unknown; observations are proxies, not auditory or physiological truth',
        word_labels_added=0,agent_heard=False,measurement_validated=False))
    print('Bound output F0/feature/level observations complete.',flush=True)


def finish():
    assert load(RUN/'evaluation/delivery-independent-check.json')['status']=='passed'
    assert '47 passed' in (RUN/'logs/contracts.log').read_text(encoding='utf-8-sig')
    plan=load(RUN/'design/protocol.json');delivery=load(RUN/'evaluation/delivery-check.json')
    native=load(RUN/'evaluation/native-independent-check.json');fresh=load(RUN/'evaluation/fresh-independent-check.json');obs=load(RUN/'observations/results.json')
    table=ROOT/'docs/knowledge/acoustic-manifestations-20261009/control-details.csv'
    with table.open(encoding='utf-8') as f:ids={r['id'] for r in csv.DictReader(f)}
    assert {'PARAM:C03.01','PARAM:C02.02','PARAM:C02.04','PARAM:C01.01'}.issubset(ids)
    supplement=dict(record_id='RESP:LASTPAGE-AUTHOR-PITCH-ABLATION-01',scope='two author-copy development contexts, not own-song repair or holdout',
        comparisons=plan['comparisons'],changed=['PARAM:C03.01','PARAM:C02.02','PARAM:C02.04'],retained=['PARAM:C01.01'],perception='PER:S1',
        candidate_feedback='pending',new_feedback_count=0,author_numeric_inputs_for_research_only=True,adoption=False,measurement_validated=False,general_rule_validated=False)
    report=dict(status='author_pitch_ablation_delivered_pending_listening',protocol=plan,native=native,fresh=fresh,delivery=delivery,
        observations=ref(RUN/'observations/results.json'),table2_supplement=supplement,source=ref(Path(__file__)),table_source=ref(table),agent_heard=False)
    save(RUN/'evaluation/table2-supplement.json',supplement);save(REPORT/(NAME+'.json'),report)
    scalar=[]
    for w in obs['windows']:
        for comp,v in w['comparisons'].items():
            scalar.append(dict(context=w['context'],note_index=w['note_index'],lyric=w['lyric'],window=w['role'],comparison=comp,
                RMS_ratio_db=v['RMS_ratio_db'],FCPE_abs_cents_p50=v['F0']['FCPE']['abs_cents_p50'],RMVPE_abs_cents_p50=v['F0']['RMVPE']['abs_cents_p50']))
    with (REPORT/(NAME+'-windows.csv')).open('x',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(scalar[0]));writer.writeheader();writer.writerows(scalar)
    md='''# 最后一页：白烁工程副本的音高因素拆分

2026-10-11。状态：author_pitch_ablation_delivered_pending_listening。

用户明确要求“这一段你复制白烁的项目，然后逐步更改内容，比如音高线，pitch这些，看下是什么影响的”。本轮据此在新研究目录复制上轮已绑定的白烁主轨part2参考工程，不改作者原件、自己的歌曲或Skill。作者历史1.56不在本机，沿用上轮1.65c；不是历史原声复原或自己的制作候选。

## 四版有限设计

|版本|PITD|note pitch|比较|
|---|---|---|---|
|A|保留|保留|新固定种子基线|
|P|原网格ys全部0|保留|P−A|
|N|保留|各点y=0，snap_first=false，x/shape保留|N−A|
|PN|原网格ys全部0|同N|PN−P、PN−N|

音符tone/tuning、延续音、歌词、时长、位置、音素时钟、全部非音高曲线与两阶段speaker保持。所有内置vibrato length原为0。N取消相对偏移和首点自动接前音；原生音符过渡仍在，不称作固定绝对音高。PITD可能补偿note基底，两因素需检查交互，PN不能单独解释一个病因。本轮没有把我们的曲线重定时到作者工程，也没有移调。

完整42音符/3原生句保留；上述字段中和覆盖此part，原生缓存技术渲染覆盖4版×3句=12上下文。真正固定种子研究仅前两句“想把你抱进身体里面／不敢让你看见”，4版×2句×2同输入重复=16套新variance/acoustic/vocoder波形，只有2个独立上下文，重复不扩大样本量。

## 技术检查与试听边界

独立检查确认原生读回、音符身份、实际音素时钟、5tick before-PITD/final拆分和两阶段speaker。人工TENC/BREC/VOIC/SHFC保持，作者已有SHFC继续作用在对应条件路径；音高修改允许variance pitch、三个预测及最终发声输入、acoustic f0和vocoder F0共同响应，不能解释为仅声码器变化。全部重新预测，使用variance11/acoustic101；16套波形的同输入重复在输入/预测/mel/vocoder F0/PCM均精确。实际特征裁剪按版本/句逐项登记，不把裁剪状态或数值变化当听觉结论。

44100Hz mono PCM24、全部固定声增益1.5，作者无DYN曲线且声明默认0dB，fresh raw采用unity包络；按原生前导时钟在44100网格拼接、叠加句尾，无归一化/压缩/BGM。新预览212.0–220.5秒，较旧参考220.35末端稍延长以包含第二句释放，不加入第三句。原生完整缓存技术WAV与真正交付fresh PCM分开。16次FCPE/RMVPE观测、整句及15字末音素/主体窗口的电平/最终特征只作代理；检测器未经本次真值校准，发声实感、破音病因及自然度均待人工。

准备打包时误把DYN默认单位写为100，断言拦截；实际工程默认0dB且无曲线，unity波形操作正确、无需重合成。失败脚本与首次打包PCM原字节在新run的logs/rejected-packaging保留，修正说明后重新打包。作者原A的VOIC输入已有模型下限裁剪，替换版按各自新预测合法裁剪；不是本轮人工VOIC干预、文件削波或听觉改善。各版数量见下面表格，不能据此宣称单通道病因。

**先确认新A仍然偏实。** 之前认可的参考由原生缓存随机性及PCM16出口产生，本轮A是固定种子fresh/PCM24；未声称二者PCM相同。若新A本身偏虚，应停止曲线因素解释，先检查基线执行差异。旧参考音频原字节另交付。再比较P/N/PN对实感、音高/旋律、字头/破音及音量的影响；缺失细分反馈保留unknown。Agent未听，本轮新反馈0、未采用、通用规律0、measurement_validated=false。

表1引用PER:S1、改变PARAM:C03.01/C02.02/C02.04、保留C01.01；表2新增RESP:LASTPAGE-AUTHOR-PITCH-ABLATION-01有限开发记录，不更新旧标签或普遍规则。先前Bright25与VOIC阴性结果保持收口；原Normal75/Classic25、范围200及抱C保持。

32个观测窗口覆盖2个整句及15字末音素/主体，各4组比较；整句P−A的双检测器绝对音分差中位约16–18c，N−A约1c，局部连接可能更大。整句RMS差约−0.28～+0.37dB；这些结果不证明实感差异。47项既有固定噪声/PCM/原生前置契约本机通过，CI保持workflow_dispatch。

'''
    md+='|句|版本|BREC裁剪帧|VOIC裁剪帧|TENC裁剪帧|\n|---|---|---:|---:|---:|\n'
    for row in fresh['rows']:
        c=row['feature_clipping'];md+=f'|{row["context"]}|{row["variant"]}|{c["breathiness"]}|{c["voicing"]}|{c["tension"]}|\n'
    md+='\n'
    for l,r in delivery['outputs'].items():md+=f'- [{l}独立人声](../../../{r["path"]})\n'
    md+=f'\n[JSON]({NAME}.json)、[窗口CSV]({NAME}-windows.csv)、[审计]({NAME}-audit.json)。单Agent，CI仅手动。下一步接本批试听，逐组解释后才选后续有限替换。\n'
    (REPORT/(NAME+'.md')).write_text(md,encoding='utf-8',newline='\n')
    status='当前状态author_pitch_ablation_delivered_pending_listening：2026-10-11用户明确要求复制白烁片段工程逐步替换，完成研究副本A/P/N/PN有限拆分。P仅PITD=0、N仅note.pitch y=0并关闭snap_first、PN两者；tone/歌词/时长/音素/非音高控制与两阶段speaker保持。完整part3句缓存技术另列，研究2句×4版×2重复=16套固定种子新波形；原生音高/身份/依赖与重复精确、输出PCM及16次双F0代理核查通过。新A是fresh固定种子，先确认仍偏实再解释曲线；旧认可参考原字节单独交付，候选反馈待评、未采用、Agent未听、通用规律0。自己的歌曲/原音频/作者原件/Skill保持，Bright25/VOIC阴性仍收口，单Agent/CI仅手动。'
    for n in ENTRIES:
        p=ROOT/n;lines=p.read_text(encoding='utf-8').splitlines();matches=[i for i,l in enumerate(lines) if '当前状态conditioned_voicing_feedback_closed_joint_conditions_reviewed：' in l]
        assert len(matches)==1,n
        rel='docs/reports/lastpage/'+NAME+'.md'
        if '/' in n:rel=('../../' if n.startswith('research/') else '../../../')+rel
        i=matches[0];lines[i]=('- ' if lines[i].startswith('- ') else '')+status+f' 见[作者副本音高拆分]({rel})。'
        if n=='plan.md':
            for i,l in enumerate(lines):
                if l.startswith('下一工作进入逐首更新，先《最后一页》：'):lines[i]='下一工作进入逐首更新，先《最后一页》：用户已明确授权白烁工程副本逐步替换研究，本批A/P/N/PN前两句已技术交付；下一步先接新A基线实感及三替换版对比反馈，再解释两音高因素与交互，不自动扩展剂量/因素或写入自己的制作工程。'
        p.write_text('\n'.join(lines)+'\n',encoding='utf-8',newline='\n')
    check(load(RUN/'protected-before.json'))
    for p,h in load(RUN/'native-inputs/runtime.json').items():assert sha(Path(p))==h
    gate=subprocess.run([sys.executable,'tools/repository/check_repository.py','--worktree'],cwd=ROOT,capture_output=True,encoding='utf-8')
    (RUN/'logs/repository-gate.log').write_text(gate.stdout+gate.stderr,encoding='utf-8');assert gate.returncode==0,gate.stdout+gate.stderr
    audit=dict(status='passed_with_explicit_auditory_gaps',new_waveforms=16,native_cached_contexts=12,F0_calls=16,new_feedback=0,
        protected_references=len(load(RUN/'protected-before.json')),native=ref(RUN/'evaluation/native-independent-check.json'),
        fresh=ref(RUN/'evaluation/fresh-independent-check.json'),delivery=ref(RUN/'evaluation/delivery-independent-check.json'),
        source_scripts=[ref(ROOT/'research/table2-confirmation'/n) for n in ['lastpage_author_pitch_ablation_20261011.py','check_lastpage_author_pitch_ablation_20261011.py','finish_lastpage_author_pitch_ablation_20261011.py','check_lastpage_author_pitch_delivery_20261011.py']],
        gate=gate.stdout.strip(),local_contract_tests=47,contract_log=ref(RUN/'logs/contracts.log'),
        originals_song_audio_Skill_preserved=True,agent_heard=False,measurement_validated=False)
    save(RUN/'evaluation/audit.json',audit);save(REPORT/(NAME+'-audit.json'),audit)
    save(RUN/'completion-manifest.json',dict(status=report['status'],files=[ref(p) for p in sorted(RUN.rglob('*')) if p.is_file()],
        documents=[ref(p) for p in sorted(REPORT.glob(NAME+'*'))],entries=[ref(ROOT/n) for n in ENTRIES]))
    print(json.dumps(dict(status=report['status'],outputs=delivery['outputs'],gate=audit['gate']),ensure_ascii=False),flush=True)


if __name__=='__main__':{'package':package,'observe':observe,'finish':finish}[sys.argv[1]]()
