"""Fresh Yuai source production: only allowed source/separation/GAME reused."""
from pathlib import Path
import hashlib,json,shutil,sys
import numpy as np
import soundfile as sf
ROOT=Path(__file__).resolve().parents[3]
RUN=ROOT/'runs/production/yuai-from-source-20261014'

def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def save(p,x):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x',encoding='utf8') as f:json.dump(x,f,ensure_ascii=False,indent=2,allow_nan=False)
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def ref(p):return dict(path=Path(p).relative_to(ROOT).as_posix(),sha256=sha(p))

def prepare():
    assert not RUN.exists();base=ROOT/'runs/yuai_source_skill_v01_20261004'
    sep=load(base/'separation.json');original=base/'source.wav';game=base/'game.json'
    assert sha(original)==sep['source_sha256']
    for field in ['vocals','instrumental']:assert sha(Path(sep[field]))==sep[field+'_sha256']
    notes=load(game);assert isinstance(notes,list) and all(set(n)=={'start','dur','tone','voiced'} for n in notes)
    RUN.mkdir(parents=True);rows=[]
    for role,source,target in [('source_audio',original,'source.wav'),('source_vocals',Path(sep['vocals']),'source_vocals.wav'),
            ('source_backing',Path(sep['instrumental']),'source_backing.wav'),('raw_GAME_events',game,'game.json'),('source_separation_provenance',base/'separation.json','separation-provenance.json')]:
        dest=RUN/'inputs'/target;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,dest);assert sha(source)==sha(dest)
        rows.append(dict(role=role,original=ref(source),copied=ref(dest)))
    info={}
    for name in ['source.wav','source_vocals.wav','source_backing.wav']:
        p=RUN/'inputs'/name;x,sr=sf.read(p,dtype='float32',always_2d=True);assert np.isfinite(x).all()
        info[name]=dict(sr=sr,channels=x.shape[1],samples=len(x),duration_s=len(x)/sr,peak=float(np.max(abs(x))))
    assert len({r['samples'] for r in info.values()})==len({r['sr'] for r in info.values()})==1
    save(RUN/'inputs/allowed-source-manifest.json',dict(status='source_allowlist_bound',user_authorization='用skill，完成从头开始生成雨爱。由雨爱源音频分离和game得到的数据可以沿用。但白烁的和历史数据不能用',
        files=rows,audio_info=info,game_events=len(notes),game_producer_model_binding='unknown in bare raw-event file; reused as explicitly authorized source observation',
        reused_only_source_audio_separation_GAME=True,old_score_expression_voice_predictions_audio_ASR_HFA_F0_read=False,
        author_data_read=False,source_clock_and_original_key_retained=True,single_agent=True,automatic_CI=False))
    catalogue=ROOT/'docs/reports/yuai/from-source-20261014-knowledge-scope.json'
    active=load(ROOT/'docs/knowledge/acoustic-manifestations-20261009/active-knowledge-sources.json')
    save(catalogue,dict(table1=active['table1'],parameters=active['parameters'],response_indices=[],response_packets=[]))
    from agent2utau.knowledge import collect_context,validate_context
    packet=collect_context(['ACO:L1','EVT:L2','PER:S1'],['PARAM:C01.01','PARAM:C02.02','PARAM:C03.01','PARAM:C10.01','PARAM:C11.01','PARAM:C12.01','PARAM:C13.01','PARAM:C14.01'],[],
        absence_reason='User excludes author and historical response data; only current generic mechanism definitions are admitted; decisions solely from fresh Yuai observations.',catalogue_path=catalogue)
    save(RUN/'design/knowledge_context.json',packet)
    decisions=[dict(id=r['id'],decision='use',reason='Use generic definitions/consumer contracts to execute own functions and separate pitch, model features, level and hearing.',
        condition_match='Current source-only independent Yuai/Yousa production; no historical response doses or outcomes used.',limitations='No historical audible control response admitted; field existence is not a dose or musical-quality rule.') for r in packet['records']]
    save(RUN/'design/knowledge-decisions.json',decisions);save(RUN/'evaluation/source-knowledge-receipt.json',validate_context(packet,decisions))
    save(RUN/'inputs/current-method-sources.json',[ref(ROOT/p) for p in ['skills/singing-expression-editor/SKILL.md','docs/workflow.md','configs/ustx_template.yaml','src/agent2utau/openutau/build.py']])
    print('Allowed source copied,',len(notes),'GAME events;',info['source.wav']['duration_s'],'seconds;history-free mechanism gate passed.',flush=True)

def asr():
    import os
    os.environ['HF_HUB_OFFLINE']='1';os.environ['HF_HUB_DISABLE_TELEMETRY']='1'
    from agent2utau.analysis.lyrics import transcribe
    weights=Path('E:/project/dotstts/data/work/models/asr/faster_whisper/0a363e9161cbc7ed1431c9597a8ceaf0c4f78fcf')
    assert (weights/'model.bin').is_file()
    result=transcribe(RUN/'inputs/source_vocals.wav',model=str(weights));save(RUN/'observations/asr.json',result)
    save(RUN/'observations/asr-provenance.json',dict(input=ref(RUN/'inputs/source_vocals.wav'),fresh=True,old_ASR_read=False,backend=result['backend'],
        model_resources=[dict(path=str(p),sha256=sha(p)) for p in sorted(weights.iterdir()) if p.is_file()],
        local_resource_not_historical_transcription=True,initial_named_model_cache_miss='large-v3-turbo alias offline snapshot absent; use explicit existing local ASR model weights'))
    for s in result['segments']:print(s['start'],s['end'],s['text'],flush=True)

def f0():
    import torch
    torch.set_num_threads(1)
    from agent2utau.analysis.f0 import extract_f0
    from agent2utau.analysis.rmvpe import infer_rmvpe
    from agent2utau.resources.config import load_config
    source=RUN/'inputs/source_vocals.wav'
    for name,fn in [('FCPE',lambda:extract_f0(source)),('RMVPE',lambda:infer_rmvpe(source,Path(load_config()['openutau_dir'])/'Dependencies/rmvpe/rmvpe.onnx'))]:
        print('Fresh source',name,flush=True);r=fn();save(RUN/f'observations/{name}-metadata.json',{k:v for k,v in r.items() if not isinstance(v,np.ndarray)})
        np.savez_compressed(RUN/f'observations/{name}.npz',**{k:v for k,v in r.items() if isinstance(v,np.ndarray)})
    save(RUN/'observations/F0-provenance.json',dict(input=ref(source),fresh_calls=2,old_F0_arrays_read=False))
    print('Two fresh source F0 observations completed.',flush=True)

if __name__=='__main__':{'prepare':prepare,'asr':asr,'f0':f0}[sys.argv[1]]()
