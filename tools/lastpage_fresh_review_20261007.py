"""Current design/wave diagnostics and review artifacts only."""
from lastpage_fresh_synthesis_20261007 import *
def plotting():
    import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
    from matplotlib import font_manager
    font_manager.fontManager.addfont('C:/Windows/Fonts/msyh.ttc');plt.rcParams['font.family']='Microsoft YaHei'
    return plt

def pitch_atlas():
    guarded();plt=plotting();plans=read(OUT/'agent_function_plans.json');score=read(OUT/'chosen_score.json');raw=read(OUT/'final_pitch.json');words=score['words'];windows=[]
    for pi,p in enumerate(plans):
        a=min(e['onset'] for e in p['entries'])-.25;b=max(words[e['word']]['music_end'] for e in p['entries'])+.15
        for x in np.arange(a,b,1.08):windows.append((pi,float(x),float(x+1.1)))
    dest=OUT/'final_pitch_atlas';dest.mkdir(exist_ok=True)
    for page in range((len(windows)+5)//6):
        own=windows[page*6:page*6+6];lims=[]
        for pi,a,b in own:
            y=target(plans[pi],np.linspace(a,b,1101))/100;lims.append((np.floor(min(y)-.6),np.ceil(max(y)+.6)))
        hs=[(hi-lo)*.44 for lo,hi in lims];height=sum(hs)+.48*len(hs)+.3;fig=plt.figure(figsize=(18,height),dpi=100);top=height-.25
        for (pi,a,b),(lo,hi),hh in zip(own,lims,hs):
            top-=hh;ax=fig.add_axes([.06,top/height,.88,hh/height]);top-=.48;t=np.linspace(a,b,1101);ax.plot(t,target(plans[pi],t)/100,color='#df7d24',lw=1.4)
            ph=raw['phrases'][pi];nt=np.asarray(ph['times_ms'])/1000;mask=(nt>=a)&(nt<=b);ax.plot(nt[mask],np.asarray(ph['final_cents'])[mask]/100,'.',ms=1.5,color='#336ec7')
            for e in plans[pi]['entries']:
                if e['onset']>b or e['body_end']<a:continue
                w=words[e['word']];ax.axvline(e['onset'],color='gray',lw=.45);ax.text(max(a,e['onset']),.97,f"{w['word']}{w['char']}",transform=ax.get_xaxis_transform(),fontsize=8,va='top')
                ax.plot([max(a,e['arrival']),min(b,e['body_end'])],[e['tone']/100]*2,color='gray',lw=.65,alpha=.5)
            ax.set_xlim(a,b);ax.set_ylim(lo,hi);ax.set_yticks(np.arange(lo,hi+.1));ax.grid(alpha=.2);ax.set_title(f'Current independent plan / actual native · context {pi} · 1440px/s, 44px/st',fontsize=9)
        fig.savefig(dest/f'page_{page:02}.png');plt.close(fig)
    dump('final_pitch_atlas_manifest.json',dict(pages=(len(windows)+5)//6,windows=windows,scale_x_px_per_s=1440,scale_y_px_per_st=44))
    print('PITCH_REVIEW_PAGES',(len(windows)+5)//6,flush=True)

def corrected_source_focus():
    guarded();plt=plotting();obs=read(OUT/'source_observations.json');fc=np.load(OUT/'fcpe.npz');rm=np.load(OUT/'rmvpe.npz');windows=[(181.91,183.01),(182.98,184.08),(209.34,210.44),(210.42,211.52)]
    bounds=[]
    for a,b in windows:
        vals=[]
        for f in [fc,rm]:
            m=(f['times']>=a)&(f['times']<=b)&f['voiced'];vals.extend((69+12*np.log2(f['f0_hz'][m]/440)).tolist())
        bounds.append((np.floor(min(vals)-.3),np.ceil(max(vals)+.3)))
    height=sum((hi-lo)*.44+.48 for lo,hi in bounds)+.3;fig=plt.figure(figsize=(18,height),dpi=100);top=height-.3
    for k,(a,b) in enumerate(windows):
        vals=[]
        for f in [fc,rm]:
            m=(f['times']>=a)&(f['times']<=b)&f['voiced'];vals.extend((69+12*np.log2(f['f0_hz'][m]/440)).tolist())
        lo,hi=bounds[k];hh=(hi-lo)*.44;top-=hh
        ax=fig.add_axes([.06,top/height,.88,hh/height]);top-=.48
        for f,col in [(fc,'#367ec8'),(rm,'#df7d24')]:
            m=(f['times']>=a)&(f['times']<=b)&f['voiced'];ax.plot(f['times'][m],69+12*np.log2(f['f0_hz'][m]/440),'.',ms=2,color=col)
        for w in obs['words']:
            if w['start']>b or w['end']<a:continue
            v=w['vowel'];ax.axvspan(max(a,v['start']),min(b,v['end']),alpha=.08,color='green');ax.text(max(a,w['start']),.97,f"{w['word']}{w['char']}",transform=ax.get_xaxis_transform(),va='top',fontsize=9)
        ax.set_xlim(a,b);ax.set_ylim(lo,hi);ax.grid(alpha=.2);ax.set_title('Corrected NEW HFA/current unconstrained GAME and dual F0 evidence',fontsize=9)
    fig.savefig(OUT/'corrected_source_focus.png');plt.close(fig)

def math_checks():
    guarded();plans=read(OUT/'agent_function_plans.json');checks=[]
    # Independent scalar evaluation, not numpy's clipped vector path.
    import bisect,math
    def sq(z):z=max(0,min(1,z));return 10*z**3-15*z**4+6*z**5
    def scalar(p,t):
        ns=p['center_nodes'];j=min(max(bisect.bisect_right([n[0] for n in ns],t)-1,0),len(ns)-2);a,b=ns[j:j+2];u=max(0,min(1,(t-a[0])/(b[0]-a[0])));dt=b[0]-a[0]
        v=(2*u**3-3*u**2+1)*a[1]+(u**3-2*u**2+u)*dt*a[2]+(-2*u**3+3*u**2)*b[1]+(u**3-u**2)*dt*b[2]
        for a,peak,b,h in p['finite']:
            if a<t<b:v+=h*(sq((t-a)/(peak-a)) if t<=peak else 1-sq((t-peak)/(b-peak)))
        for a,at,rel,b,d0,dm,d1,f0,f1,phase in p['periodic']:
            if a<t<b:
                d=d0+(dm-d0)*sq((t-a)/(rel-a)) if t<=rel else dm+(d1-dm)*sq((t-rel)/(b-rel));z=t-a
                v+=sq((t-a)/(at-a))*sq((b-t)/(b-rel))*d*math.sin(phase+2*math.pi*(f0*z+(f1-f0)*z*z/(2*(b-a))))
        return v
    for p in plans:
        t=np.arange(*p['support'],.0037);e=max(abs(target(p,t)-np.asarray([scalar(p,float(x)) for x in t])));assert e<1e-8
        for c in p['finite']:assert c[0]<c[1]<c[2]
        for c in p['periodic']:assert c[0]<c[1]<=c[2]<c[3]
        checks.append(dict(context=p['context'],independent_error_c=float(e),C1_center_shared_values_slopes=True))
    dump('independent_math_check.json',checks);print('INDEPENDENT_MATH',max(c['independent_error_c'] for c in checks),flush=True)

if __name__=='__main__':globals()[sys.argv[1]]()
