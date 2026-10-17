"""Current-source joint English realignment and fresh native pronunciation test."""
from pathlib import Path
import sys,copy,subprocess,json
import soundfile as sf
import yaml
from source import ROOT,RUN,save,load,ref,sha

def english():
    sys.path.insert(0,str(ROOT/'external/HubertFA'))
    from onnx_infer import InferenceOnnx
    from tools.g2p import BaseG2P
    mapping=dict(qi=['zh/q','zh/i'],de=['zh/d','zh/e'],rainie=['en/r','en/ey','en/n','en/iy'],love=['en/l','en/ah','en/v'])
    class G2P(BaseG2P):
        def __init__(self):super().__init__(None)
        def _g2p(self,t):
            words=t.split();seq=['SP'];indices=[-1]
            for i,w in enumerate(words):seq+=mapping[w]+['SP'];indices+=[i]*len(mapping[w])+[-1]
            return seq,words,indices
    a=InferenceOnnx(ROOT/'external/hfa_model/1201_hfa_model/model.onnx');a.load_config();a.init_decoder();a.load_model();g=G2P();source,sr=sf.read(RUN/'inputs/source_vocals.wav',dtype='float32');source=source.mean(axis=1)
    spans=[(71.55,75.1),(182.55,186.2)]
    for i,(lo,hi) in enumerate(spans):
        p=RUN/f'source-alignment/english-joint-inputs/context{i}.wav';p.parent.mkdir(parents=True,exist_ok=True);sf.write(p,source[round(lo*sr):round(hi*sr)],sr,subtype='PCM_24')
        seq,words,indices=g('qi de rainie love');a.dataset.append((p,seq,words,indices))
    a.infer('AP,EP',pad_times=1,pad_length=5);a.export(RUN/'source-alignment/english-joint-outputs',output_format=['textgrid'])
    rows=[]
    for (lo,hi),p in zip(spans,a.predictions):
        words=[dict(text=w.text,start=w.start+lo,end=w.end+lo,phones=[dict(label=z.text,start=z.start+lo,end=z.end+lo) for z in w.phonemes]) for w in p[2]]
        rows.append(dict(source_span_s=[lo,hi],words=words))
        print([(w['text'],round(w['start'],3),round(w['end'],3),w['phones']) for w in words if w['text'] in ['rainie','love']],flush=True)
    save(RUN/'observations/HFA-English-joint.json',dict(rows=rows,original_split_observation=ref(RUN/'observations/HFA.json'),fresh_calls=2,
        no_old_alignment_read=True,reason='Avoid resetting/inserted SP between English name syllables; retain source observations separately'))

def probe():
    from agent2utau.openutau.build import build_project
    from agent2utau.resources.config import load_config
    p=RUN/'native-tests/english.ustx';build_project('Current English hint contract',[dict(start_sec=1,part_start_sec=0,
        notes=[dict(start=1,dur=.5,tone=71,lyric='Rai[en/r en/ey]'),dict(start=1.5,dur=.5,tone=71,lyric='nie[en/n en/iy]'),dict(start=2,dur=1,tone=71,lyric='Love[en/l en/ah en/v]')])],p)
    d=yaml.safe_load(p.read_text(encoding='utf8'));colors=['','Yousa_Bright','Yousa_Cute','Yousa_Normal','Yousa_Whisper','Yousa_Classic']
    d['expressions']['clr'].update(options=colors,max=5,default_value=3);d['tracks'][0]['voice_color_names']=colors
    for n in d['voice_parts'][0]['notes']:n['phoneme_expressions']=[dict(index=i,abbr='clr',value=3) for i in range(8)]
    p.write_text(yaml.safe_dump(d,allow_unicode=True,sort_keys=False),encoding='utf8')
    exe=Path(load_config()['openutau_dir'])/'a2u-bridge.exe';out=RUN/'native-tests/english-phones.json'
    result=subprocess.run([str(exe),'export-phonemes','--project',str(p),'--out',str(out)],cwd=exe.parent,capture_output=True,encoding='utf8',errors='replace')
    (RUN/'native-tests/english-native.log').write_text(result.stdout+result.stderr,encoding='utf8');assert result.returncode==0,result.stdout[-1500:]
    obj=load(out);save(RUN/'native-tests/english-result.json',json.loads(result.stdout.strip().splitlines()[-1]))
    print('Native English phones',[(f['phoneme'],f['start_ms'],f['end_ms']) for part in obj['parts'] for phrase in part['phrases'] for f in phrase['phones']],flush=True)

if __name__=='__main__':{'english':english,'probe':probe}[sys.argv[1]]()
