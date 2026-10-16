"""New current-source lyric judgement and mixed-language HFA observations."""
from pathlib import Path
import sys,json
import numpy as np
import soundfile as sf
from pypinyin import lazy_pinyin
from source import ROOT,RUN,load,save,ref,sha

# Fresh ASR-driven lyric correction and whole-context windows. No old timestamps.
CONTEXTS=[
 (15.9,25.65,['窗外的天气','就像是你多变的表情']),
 (25.8,38.3,['下雨了','雨陪我哭泣','看不清','我也不想看清']),
 (38.2,51.7,['离开你','我安静的抽离','不忍揭晓的剧情','我的泪流在心里','学会放弃']),
 (51.0,62.75,['听雨的声音','一滴滴清晰','你的呼吸像雨滴渗入我的爱里','真希望雨能下不停']),
 (62.0,75.3,['让想念继续','让爱变透明','我爱上给我勇气的','Rainie Love']),
 (74.8,86.7,['窗外的雨滴','一滴滴累积','屋内的湿气像储存爱你的记忆','真希望雨能下不停']),
 (86.4,102.7,['雨爱的秘密','能一直延续','我相信我将会看到','彩虹的美丽']),
 (124.0,133.8,['冷冷的空气','很窒息','我无法呼吸']),
 (133.8,146.5,['一万颗雨滴的距离','很彻底','让爱消失无息']),
 (146.1,159.0,['离开你','我安静的抽离','不忍揭晓的剧情','我的泪流在心里','学会放弃']),
 (161.0,174.4,['听雨的声音','一滴滴清晰','你的呼吸像雨滴渗入我的爱里','真希望雨能下不停']),
 (173.8,186.6,['让想念继续','让爱变透明','我爱上给我勇气的','Rainie Love']),
 (185.6,198.5,['窗外的雨滴','一滴滴累积','屋内的湿气像储存爱你的记忆','真希望雨能下不停']),
 (198.0,212.2,['雨爱的秘密','能一直延续','我相信我将会看到','彩虹的美丽']),
 (212.9,222.3,['屋内的湿气像储存爱你的记忆','真希望雨能下不停']),
 (222.3,238.2,['雨爱的秘密','能一直延续','我相信我将会看到','彩虹的美丽']),
]

def prepare():
    assert not (RUN/'observations/lyric-judgement.json').exists()
    model=ROOT/'external/hfa_model/1201_hfa_model'
    dictionary={line.split('\t')[0]:line.split('\t')[1].split() for line in (model/'opencpop-extension.txt').read_text(encoding='utf8').splitlines() if '\t' in line}
    vocab=load(model/'vocab.json');print('Current HFA vocabulary fields',list(vocab),flush=True)
    words=[];context_rows=[];mapping={};text=[];source,sr=sf.read(RUN/'inputs/source_vocals.wav',dtype='float32');source=source.mean(axis=1) if source.ndim==2 else source
    english=[('Rai','rainie',0,['en/r','en/ey']),('nie','rainie',1,['en/n','en/iy']),('Love','love',0,['en/l','en/ah','en/v'])]
    for ctx,(a,b,lines) in enumerate(CONTEXTS):
        tokens=[];line_ids=[]
        for line in lines:
            lid=len(text);text.append(dict(line=lid,text=line,context=ctx));line_ids.append(lid)
            units=english if line=='Rainie Love' else [(c,None,0,['zh/'+p for p in dictionary[pin]]) for c,pin in zip(line,lazy_pinyin(line))]
            for c,group,syllable,phones in units:
                i=len(words);token=f'w{i:04}';words.append(dict(word=i,char=c,line=lid,context=ctx,token=token,
                    pinyin=lazy_pinyin(c)[0] if not group else None,language='en' if group else 'zh',
                    source_lexical_group=group,syllable_index=syllable,phonemes=phones));mapping[token]=phones;tokens.append(token)
        folder=RUN/'source-alignment/inputs';folder.mkdir(parents=True,exist_ok=True);p=folder/f'context{ctx:02}.wav';sf.write(p,source[round(a*sr):round(b*sr)],sr,subtype='PCM_24')
        p.with_suffix('.lab').write_text(' '.join(tokens),encoding='utf8');context_rows.append(dict(context=ctx,source_span_s=[a,b],line_ids=line_ids,word_ids=[w['word'] for w in words if w['context']==ctx],wav=ref(p),lab=ref(p.with_suffix('.lab'))))
    save(RUN/'source-alignment/dictionary.json',mapping)
    save(RUN/'observations/lyric-judgement.json',dict(origin='Agent correction of fresh ASR in current source/music context',ASR=ref(RUN/'observations/asr.json'),lines=text,words=words,contexts=context_rows,
        corrections=['天晴→天气','不仍介绍→不忍揭晓','相遇低伸→像雨滴渗','无内→屋内','Running Love→Rainie Love (lexical interpretation; exact name/audio pronunciation listening unknown)',
            '雨难→雨能','撑离→抽离','泪尽→累积','出座→储存'],
        excluded_nonsinging_ASR=[dict(span_s=[15.82,16.74],text='詞曲 李宗盛',reason='No coherent sung-word sequence before first GAME-supported lyric; ASR hallucination/credit candidate'),
            dict(span_s=[115.94,117.06],text='优优独播剧场',reason='Interlude not part of lyric music'),dict(span_s=[255.06,260.46],text='优优独播剧场',reason='After sung music ends; no GAME voicing support')],
        English_name_interpretation='Rainie Love, segmented Rai/nie/Love for explicit nucleus handling; not historical lyric alignment',
        old_ASR_HFA_lyrics_read=False,unknowns_not_deleted=True))
    print(len(words),'freshly judged sung units in',len(context_rows),'new HFA contexts.',flush=True)

def execute():
    sys.path.insert(0,str(ROOT/'external/HubertFA'))
    from onnx_infer import InferenceOnnx
    from tools.g2p import BaseG2P
    model=ROOT/'external/hfa_model/1201_hfa_model';mapping=load(RUN/'source-alignment/dictionary.json')
    class MixedG2P(BaseG2P):
        def __init__(self):super().__init__(None)
        def _g2p(self,text):
            seq=['SP'];owner=[-1];tokens=text.split()
            for i,w in enumerate(tokens):seq+=mapping[w]+['SP'];owner += [i]*len(mapping[w])+[-1]
            return seq,tokens,owner
    aligner=InferenceOnnx(model/'model.onnx');aligner.load_config();aligner.init_decoder();aligner.load_model()
    g2p=MixedG2P()
    for c in load(RUN/'observations/lyric-judgement.json')['contexts']:
        wav=ROOT/c['wav']['path'];pseq,wseq,idx=g2p(wav.with_suffix('.lab').read_text(encoding='utf8'))
        aligner.dataset.append((wav,pseq,wseq,idx))
    aligner.infer(non_lexical_phonemes='AP,EP',pad_times=1,pad_length=5)
    aligner.export(RUN/'source-alignment/outputs',output_format=['textgrid'])
    judgement=load(RUN/'observations/lyric-judgement.json');results=[];nonlexical=[]
    for c,pred in zip(judgement['contexts'],aligner.predictions):
        offset=c['source_span_s'][0]
        for w in pred[2]:
            row=dict(token=w.text,start=w.start+offset,end=w.end+offset,phones=[dict(label=p.text,start=p.start+offset,end=p.end+offset) for p in w.phonemes],context=c['context'])
            if w.text.startswith('w'):results.append(row)
            else:nonlexical.append(row)
    assert len(results)==len(judgement['words'])
    save(RUN/'observations/HFA.json',dict(words=results,nonlexical=nonlexical,fresh=True,old_HFA_read=False,
        model_resources=[ref(p) for p in sorted(model.iterdir()) if p.is_file()],inputs=ref(RUN/'observations/lyric-judgement.json'),HFA_is_observation_not_music_clock=True))
    print('Fresh mixed-language HFA completed for',len(results),'units.',flush=True)

if __name__=='__main__':{'prepare':prepare,'execute':execute}[sys.argv[1]]()
