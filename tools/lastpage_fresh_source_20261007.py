"""Fresh recording analysis. No historical song projects or author data."""
from pathlib import Path
import hashlib, json, shutil, sys
ROOT = Path('E:/project/agent2utau')
OUT = ROOT / 'runs/lastpage_fresh_source_20261007'
SOURCE = Path('E:/data/music/江语晨+-+最后一页.mp3')
def sha(p):
    with Path(p).open('rb') as f: return hashlib.file_digest(f, 'sha256').hexdigest()
def dump(name, obj):
    (OUT / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding='utf-8')
def guarded():
    import os
    allowed=str(OUT.resolve()).casefold()
    banned=[str(ROOT/'runs').casefold(),str(ROOT/'research').casefold(),str(ROOT/'docs').casefold(),'e:\\data\\project_opentuau',str(ROOT/'data/lyrics').casefold()]
    def hook(event,args):
        if event!='open' or not isinstance(args[0],(str,bytes,os.PathLike)): return
        p=str(Path(args[0]).absolute()).casefold()
        if any(p==v or p.startswith(v+'\\') for v in banned) and not p.startswith(allowed+'\\'):
            raise PermissionError('Fresh-only task rejects historical input: '+p)
    sys.addaudithook(hook)
def prepare():
    OUT.mkdir(parents=True, exist_ok=False)
    src = OUT / 'input.mp3'
    shutil.copyfile(SOURCE, src)
    from agent2utau.audio.decode import decode, probe_duration
    decode(src, OUT/'source.wav')
    dump('input_binding.json', dict(source=str(SOURCE), source_sha256=sha(SOURCE),
        copy_sha256=sha(src), decoded_sha256=sha(OUT/'source.wav'),
        duration=probe_duration(OUT/'source.wav'), key_shift=0, tempo_factor=1,
        prohibited_inputs=['historical LastPage projects','Baishuo author projects'],
        historical_audio_or_curve_reuse=False))
    print('PREPARED', flush=True)
def stems():
    guarded()
    from agent2utau.audio.separate import separate
    result=separate(OUT/'source.wav', OUT/'stems')
    dump('separation.json', result)
    print('STEMS_READY', result['backend'], flush=True)
def asr():
    guarded()
    from agent2utau.analysis.lyrics import transcribe
    binding=json.loads((OUT/'separation.json').read_text(encoding='utf-8')) if (OUT/'separation.json').exists() else {'vocals':str(OUT/'source.wav')}
    result=transcribe(binding['vocals'])
    result['input_sha256']=sha(binding['vocals'])
    result['input_path']=binding['vocals']
    dump('fresh_asr_vocals.json' if (OUT/'separation.json').exists() else 'fresh_asr.json',result)
    for s in result['segments']: print(s['start'],s['end'],s['text'],flush=True)
def game():
    guarded()
    import soundfile as sf, numpy as np
    from agent2utau.transcription.game_onnx import GameOnnx
    binding=json.loads((OUT/'separation.json').read_text(encoding='utf-8'))
    wav,sr=sf.read(binding['vocals'], dtype='float32')
    if wav.ndim>1: wav=wav.mean(axis=1)
    model=Path('E:/software/OpenUtau-win-x64_dpV2/OpenUtau-win-x64/Dependencies/game')
    notes=GameOnnx(model).infer(wav,language='zh',seed=20261007)
    dump('fresh_game.json',dict(model=str(model), model_hashes={p.name:sha(p) for p in model.glob('*.onnx')},notes=notes))
    print('GAME_READY',len(notes),flush=True)
def f0():
    guarded()
    import numpy as np
    from agent2utau.analysis.f0 import extract_f0
    from agent2utau.analysis.rmvpe import infer_rmvpe
    binding=json.loads((OUT/'separation.json').read_text(encoding='utf-8'))
    for name,fn in [('fcpe',extract_f0),('rmvpe',lambda p:infer_rmvpe(p,Path('E:/software/OpenUtau-win-x64_dpV2/OpenUtau-win-x64/Dependencies/rmvpe/rmvpe.onnx')))]:
        result=fn(binding['vocals'])
        np.savez_compressed(OUT/(name+'.npz'),**{k:v for k,v in result.items() if isinstance(v,np.ndarray)})
        dump(name+'_provenance.json',dict(input_sha256=sha(binding['vocals']),metadata={k:v for k,v in result.items() if not isinstance(v,np.ndarray)}))
        print('F0_READY',name,flush=True)
def scaffold():
    guarded()
    import soundfile as sf
    from pypinyin import lazy_pinyin,Style
    binding=json.loads((OUT/'separation.json').read_text(encoding='utf-8'))
    raw=json.loads((OUT/'fresh_asr.json').read_text(encoding='utf-8'))
    eligible=[s for s in raw['segments'] if 12<s['start']<100 or s['start']>126]
    base=['雨停滞天空之间','像泪在眼眶盘旋','这也许是最后一次见面','沿途经过的从前','还来不及再重演','拥抱早已悄悄冷却',
          '海潮声淹没了离别时的黄昏','只留下不舍的体温','星空下拥抱着快凋零的温存','爱只能在回忆里完整',
          '想把你抱进身体里面','不敢让你看见','嘴角那颗没落下的泪','如果这是最后的一页','在你离开之前','能否让我把故事重写']
    texts=base+base+base[10:]
    assert len(eligible)==len(texts),(len(eligible),len(texts))
    wav,sr=sf.read(binding['vocals'],dtype='float32');wav=wav.mean(axis=1) if wav.ndim>1 else wav
    dest=OUT/'hfa_inputs';dest.mkdir(exist_ok=True);rows=[]
    for i,(s,text) in enumerate(zip(eligible,texts)):
        a=max(0,s['start']-.45);b=min(len(wav)/sr,s['end']+.65)
        py=lazy_pinyin(text,style=Style.NORMAL,strict=False)
        path=dest/f'line_{i:02}.wav';sf.write(path,wav[round(a*sr):round(b*sr)],sr,subtype='FLOAT')
        path.with_suffix('.lab').write_text(' '.join(py),encoding='utf-8')
        rows.append(dict(line=i,text=text,pinyin=py,start=a,end=b,asr=s,
            lyric_source='Fresh unconstrained ASR with Agent lexical/semantic correction and repeated lyric agreement; no lyric archive read',
            identity_verified_by_listening=False))
    dump('lyric_scaffold.json',rows)
    print('Fresh lyric contexts',len(rows),sum(len(r['text']) for r in rows),flush=True)
def hfa():
    guarded()
    import subprocess,os
    env=os.environ.copy();env.update(PYTHONIOENCODING='utf-8',HF_HUB_OFFLINE='1',OMP_NUM_THREADS='1')
    cmd=[sys.executable,str(ROOT/'external/HubertFA/onnx_infer.py'),'-m',str(ROOT/'external/hfa_model/1201_hfa_model/model.onnx'),'-wf',str(OUT/'hfa_inputs'),'-l','zh','-np','AP,EP','-o',str(OUT/'hfa')]
    with (OUT/'fresh_hfa.log').open('w',encoding='utf-8') as log:
        result=subprocess.run(cmd,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
    dump('hfa_execution.json',dict(command=cmd,returncode=result.returncode,model_sha256=sha(ROOT/'external/hfa_model/1201_hfa_model/model.onnx')))
    assert result.returncode==0
    print('FRESH_HFA_READY',flush=True)
def repair_scaffold():
    guarded()
    import soundfile as sf
    rows=json.loads((OUT/'lyric_scaffold.json').read_text(encoding='utf-8'));binding=json.loads((OUT/'separation.json').read_text(encoding='utf-8'))
    wav,sr=sf.read(binding['vocals'],dtype='float32');wav=wav.mean(axis=1) if wav.ndim>1 else wav
    archive=OUT/'first_alignment_draft';archive.mkdir(exist_ok=False)
    shutil.copyfile(OUT/'lyric_scaffold.json',archive/'lyric_scaffold.json');shutil.copytree(OUT/'hfa',archive/'hfa');shutil.copyfile(OUT/'source_observations.json',archive/'source_observations.json')
    for i,a in [(26,182.12),(32,209.49)]:
        row=rows[i];row['old_start']=row['start'];row['start']=a
        row['repair_reason']='Previous sustained vowel was falsely assigned to next xiang onset; independent current unconstrained GAME and source dual F0 establish later new low note.'
        path=OUT/f'hfa_inputs/line_{i:02}.wav';sf.write(path,wav[round(a*sr):round(row['end']*sr)],sr,subtype='FLOAT')
    dump('lyric_scaffold.json',rows)
    print('Scaffold excludes preceding sustained vowels in two contexts',flush=True)
if __name__=='__main__': globals()[sys.argv[1]]()
