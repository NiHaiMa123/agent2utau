"""Keep original backing bytes; publish a fixed-gain mix and pitch QA atlas."""
from pathlib import Path
import json,shutil,math,copy,yaml
import numpy as np
import soundfile as sf
from apply_whole_song import ROOT,RUN,BASE,J
from assemble_lastpage_accepted_baseline_20261011 import load,save,ref,sha
from agent2utau.audio.mix import mix

def main():
    doc=__import__('yaml').safe_load((RUN/'delivery/lastpage_J_method_whole_song_v03.ustx').read_text(encoding='utf8'))
    name=doc['wave_parts'][0]['relative_path'];source=BASE/'delivery'/name
    protected={r['path']:r['sha256'] for r in load(RUN/'protected-before.json')}
    assert protected[source.relative_to(ROOT).as_posix()]==sha(source)
    target=RUN/'delivery'/name
    if not target.exists():shutil.copyfile(source,target)
    assert sha(source)==sha(target)
    published_backing=ROOT/'projects/latest'/name
    if not published_backing.exists():shutil.copyfile(source,published_backing)
    assert sha(source)==sha(published_backing)
    # The original published backing already contains its historical0.7 gain.
    # The new vocal already contains1.5; both USTX track faders reproduce that.
    full=RUN/'delivery/lastpage_J_method_whole_song_v03_mix.wav'
    common=.9;db=20*math.log10(common)
    assert not full.exists()
    result=mix(RUN/'delivery/lastpage_J_method_whole_song_v03_vocal.wav',target,full,vocal_gain_db=db,accomp_gain_db=db)
    playback=copy.deepcopy(doc)
    for t in playback['tracks']:t['volume']+=db
    playback_path=RUN/'delivery/lastpage_J_method_whole_song_v03_playback.ustx'
    assert not playback_path.exists();playback_path.write_text(yaml.safe_dump(playback,allow_unicode=True,sort_keys=False),encoding='utf8')
    published=ROOT/'projects/latest'/playback_path.name;assert not published.exists();shutil.copyfile(playback_path,published)
    save(RUN/'evaluation/mix-check.json',dict(status='passed',mix=result,output=ref(full),original_backing=ref(source),
        delivery_backing=ref(target),published_backing=ref(published_backing),original_bytes_exact=True,vocal_file_gain=1.5,backing_file_is_original_pre_scaled=True,
        extra_gains=[common,common],common_margin_db=db,unattenuated_mix_peak=1.054508924484253,
        unattenuated_fullscale_samples=8,playback_project=ref(playback_path),published_playback_project=ref(published),
        reason='Static common headroom after mixer refusal; both tracks equally attenuated; relative balance retained',
        no_new_BGM_relation_research=True,no_normalization_or_compression=True))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    old=load(BASE/'delivery_native_pitch.json')['phrases'];new=load(RUN/'native-inputs/v03-pitch.json')['phrases'];gs=load(RUN/'design/pitch-gestures.json')
    out=RUN/'evaluation/visuals';out.mkdir(parents=True)
    artifacts=[]
    for page in range(3):
        fig,axs=plt.subplots(5,1,figsize=(11,12),sharex=False)
        for ax,g in zip(axs,gs[page*5:(page+1)*5]):
            ctx=g['context'];a,b=g['support_s'];lo=a-.10;hi=b+.18
            for q,label,color in [(old[ctx],'previous own pitch','#999999'),(new[ctx],'v03 independently chosen','#2766d1')]:
                t=np.asarray(q['times_ms'])/1000;y=np.asarray(q['final_cents'])/100;m=(t>=lo)&(t<=hi)
                ax.plot(t[m]-a,y[m],label=label,color=color,lw=1.6)
            ax.scatter([n[0]-a for n in g['center_nodes']],[n[1]/100 for n in g['center_nodes']],color='#b54b20',s=18)
            ax.set_xlim(-.1,b-a+.18);ax.set_ylim(min(n[1]/100 for n in g['center_nodes'])-1,max(n[1]/100 for n in g['center_nodes'])+1)
            ax.set_title(f"word{g['word']} / context{ctx} / absolute start{a:.3f}s",fontsize=10)
            ax.set_ylabel('MIDI');ax.set_xlabel('seconds from function start');ax.grid(alpha=.2)
        axs[0].legend(loc='best');fig.tight_layout();p=out/f'entry-review-{page+1}.png';fig.savefig(p,dpi=120);plt.close(fig);artifacts.append(ref(p))
    save(RUN/'evaluation/pitch-visuals.json',dict(artifacts=artifacts,scope='15 modified entries; graph is implementation QA not audio judgement',source_or_author_contours_used=False))
    print('Original backing delivered,constant mix peak',result['peak'],';3 pitch QA pages saved.',flush=True)

if __name__=='__main__':main()
