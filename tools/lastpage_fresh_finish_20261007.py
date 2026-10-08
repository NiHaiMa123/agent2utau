"""Current LastPage assembly, actual-input and actual-PCM diagnostics."""
from lastpage_fresh_review_20261007 import *
from lastpage_fresh_source_20261007 import SOURCE
import soundfile as sf
import shutil

def assemble():
    guarded();rec=read(OUT/'synthesis_check.json');info=sf.info(OUT/'source.wav');n=info.frames;sr=info.samplerate
    assert sr==44100 and len(rec['phrases'])==34
    contributions=[];v=np.zeros(n,np.float64)
    for ch in rec['phrases']:
        i=ch['index'];path=OUT/f'synthesis/phrase_{i:03}.npy';assert sha(path)==ch['wave_sha256'];w=np.load(path)
        if (OUT/'native_dynamics_raw').exists():w=np.fromfile(OUT/f'native_dynamics_raw/phrase_{i:03}.f32',dtype='<f4')
        a=round(ch['wave_start_s']*sr);lo=max(0,a);hi=min(n,a+len(w));assert hi>lo
        v[lo:hi]+=w[lo-a:hi-a];contributions.append((lo,hi,w[lo-a:hi-a]))
    rev=np.zeros(n,np.float64)
    for lo,hi,w in reversed(contributions):rev[lo:hi]+=w
    err=float(max(abs(v-rev)));assert err<1e-12
    np.save(OUT/'raw_vocal.npy',v);sf.write(OUT/'raw_vocal.wav',v,sr,subtype='FLOAT')
    dump('assembly_check.json',dict(samples=n,sample_rate=sr,duration=n/sr,reverse_error=err,raw_peak=float(max(abs(v))),all_current_wave_hashes=True,native_dynamics_applied=(OUT/'native_dynamics_raw').exists(),AP_SP_no_post_gain=True))
    print('ASSEMBLED',n,n/sr,'peak',max(abs(v)),flush=True)

def controls_check():
    guarded();doc=load_ustx(OUT/'lastpage_fresh.ustx');plans=read(OUT/'agent_function_plans.json');reports=[]
    for i,(p,part) in enumerate(zip(plans,doc['voice_parts'])):
        r=read(OUT/f'feeds/phrase_{i:03}.json');b=tensors(r['tensors']);nf=b['f0'].size;t=(r['position_ms']+(np.arange(nf)-r['head_frames'])*r['frame_ms'])/1000
        es={};active={};curves={c['abbr']:c for c in part['curves']}
        for ab,k,scale,default in [('tenc','tension',.05,0),('brec','breathiness',.12,0),('voic','voicing',.12,100)]:
            d=np.asarray(r['expression_deltas'][k],np.float32);exp=(control(p,t,ab)-default)*scale;es[k]=float(max(abs(d-exp)));active[k]=int(np.count_nonzero(d))
            # Quantized project vs continuous plan; frame sampler adds native clock interpolation.
            assert es[k]<.16,(i,k,es[k])
        assert all(v==100 for v in curves['voic']['ys'])
        aps=[]
        for q in r['phones']:
            if q['phoneme'] not in ['AP','SP']:continue
            a=q['positionMs']/1000;b0=q['endMs']/1000;m=(t>=a+.03)&(t<=b0-.03)
            if m.any():
                for k in ['tension','breathiness','voicing']:assert max(abs(np.asarray(r['expression_deltas'][k])[m]))==0,(i,q,k)
            aps.append(dict(phone=q['phoneme'],start=a,end=b0,core_frames=int(m.sum())))
        assert np.all(b['gender']==0) and np.all(b['velocity']==1)
        reports.append(dict(context=i,continuous_plan_delta_error=es,nonzero_frames=active,AP_SP_core=aps,DYN_minmax=[min(curves['dyn']['ys']),max(curves['dyn']['ys'])],VOIC_core_retained=True,gender_zero_velocity_unity=True))
    dump('current_control_input_check.json',reports);print('CURRENT_CONTROL_CHECK',max(max(r['continuous_plan_delta_error'].values()) for r in reports),flush=True)

def envelope(y,sr,ms):
    step=round(.005*sr);win=round(ms*.001*sr);cs=np.r_[0,np.cumsum(y*y,dtype=np.float64)];ix=np.arange(0,len(y)-win+1,step)
    return (ix+win/2)/sr,20*np.log10(np.sqrt((cs[ix+win]-cs[ix])/win)+1e-10)

def energy():
    guarded();v=np.load(OUT/'raw_vocal.npy');sr=44100;ts,db=envelope(v,sr,30);t50,d50=envelope(v,sr,50);geo=read(OUT/'native_word_geometry.json');score=read(OUT/'chosen_score.json');stats=[]
    for g in geo:
        a,b=g['native_vowel'];m=(ts>=a+.025)&(ts<=b-.025);m50=(t50>=a+.025)&(t50<=b-.025);z=db[m];z50=d50[m50];assert len(z)>0
        # Flag low interior support separately from intentional onset/release.
        core=(ts>=a+.2*(b-a))&(ts<=b-.2*(b-a));zc=db[core]
        stats.append(dict(word=g['word'],char=g['char'],native_vowel=[a,b],rms30_db_percentiles=np.percentile(z,[0,10,50,90,100]).tolist(),rms50_db_percentiles=np.percentile(z50,[0,10,50,90,100]).tolist(),core_min_to_median_db=float(np.median(zc)-min(zc)),source_unknown=g['word']==106,level_is_energy_proxy=True))
    dump('actual_nucleus_energy.json',dict(wave_sha256=sha(OUT/'raw_vocal.wav'),window_ms=[30,50],step_ms=5,words=stats,no_per_word_normalization=True))
    plt=plotting();dest=OUT/'control_energy_atlas';dest.mkdir(exist_ok=True);plans=read(OUT/'agent_function_plans.json')
    for page in range(6):
        ids=list(range(page*6,min((page+1)*6,34)));fig,axs=plt.subplots(len(ids)*2,1,figsize=(18,len(ids)*3.5),dpi=100)
        for j,i in enumerate(ids):
            p=plans[i];ww=sorted(set(e['word'] for e in p['entries']));a=min(geo[k]['native_vowel'][0] for k in ww)-.22;b=max(geo[k]['native_vowel'][1] for k in ww)+.2
            ax=axs[j*2];m=(ts>=a)&(ts<=b);m50=(t50>=a)&(t50<=b);ax.plot(ts[m],db[m],lw=.65,label='actual PCM 30 ms / 5 ms');ax.plot(t50[m50],d50[m50],lw=.65,label='50 ms');ax.set_ylim(-65,-10);ax.set_xlim(a,b);ax.grid(alpha=.2);ax.legend(fontsize=7,loc='lower right');ax.set_title(f'Context {i}: current actual vocal energy · all nuclei',fontsize=9)
            ac=axs[j*2+1];tt=np.arange(a,b,.005)
            for ab in ['tenc','brec']:ac.plot(tt,control(p,tt,ab),lw=.8,label=ab)
            ac.plot(tt,control(p,tt,'dyn')*.1,lw=.8,label='DYN dB')
            ac.set_xlim(a,b);ac.set_ylim(-15,24);ac.grid(alpha=.2);ac.legend(fontsize=7,loc='lower right')
            for k in ww:
                g=geo[k];x,z=g['native_vowel'];ax.axvspan(x,z,color='green',alpha=.045);ax.text(x,-11,f"{k}{g['char']}",fontsize=7,va='top');ac.axvspan(x,z,color='green',alpha=.05);ac.text(x,23,f"{k}{g['char']}",fontsize=7,va='top')
        fig.tight_layout();fig.savefig(dest/f'page_{page:02}.png');plt.close(fig)
    print('ENERGY_REVIEW_6_PAGES',sorted([(s['core_min_to_median_db'],s['word'],s['char'])for s in stats],reverse=True)[:20],flush=True)

def actual_f0():
    guarded();from agent2utau.analysis.f0 import extract_f0
    from agent2utau.analysis.rmvpe import infer_rmvpe
    for name,fn in [('fcpe',extract_f0),('rmvpe',lambda p:infer_rmvpe(p,Path('E:/software/OpenUtau-win-x64_dpV2/OpenUtau-win-x64/Dependencies/rmvpe/rmvpe.onnx')))]:
        result=fn(OUT/'raw_vocal.wav');np.savez_compressed(OUT/f'actual_{name}.npz',**{k:v for k,v in result.items() if isinstance(v,np.ndarray)});dump(f'actual_{name}_binding.json',dict(wave_sha256=sha(OUT/'raw_vocal.wav'),metadata={k:v for k,v in result.items() if not isinstance(v,np.ndarray)}));print('ACTUAL_F0_READY',name,flush=True)
    plans=read(OUT/'agent_function_plans.json');geo=read(OUT/'native_word_geometry.json');res=[]
    for name in ['fcpe','rmvpe']:
        f=np.load(OUT/f'actual_{name}.npz');t=f['times'];tar=np.full(len(t),np.nan);sung=np.zeros(len(t),bool)
        for g in geo:
            # The owner word chooses the plan. Expanded phrase supports overlap.
            p=next(p for p in plans if any(e['word']==g['word'] for e in p['entries']))
            a,b=g['native_vowel'];m=(t>=a+.04)&(t<=b-.04);sung|=m;tar[m]=target(p,t[m])
        m=sung&f['voiced']&np.isfinite(tar)&(f['f0_hz']>0);c=6900+1200*np.log2(f['f0_hz'][m]/440);e=abs(c-tar[m])
        res.append(dict(extractor=name,sung_frames=int(sung.sum()),comparable=int(m.sum()),unknown=int((sung&~m).sum()),abs_error_c_percentiles=np.percentile(e,[50,95,99,100]).tolist(),technical_diagnostic_only=True,naturalness_accepted=False))
    dump('actual_dual_f0_diagnostic.json',res);print('ACTUAL_DUAL_F0',res,flush=True)

def dynamics():
    guarded();import subprocess
    arc=OUT/'before_local_gain';arc.mkdir(exist_ok=True);assert not any(arc.iterdir()),'Preserve existing gain-stage backup'
    for name in ['lastpage_fresh.ustx','agent_function_plans.json','raw_vocal.wav','raw_vocal.npy','actual_nucleus_energy.json','actual_dual_f0_diagnostic.json','current_control_input_check.json','assembly_check.json']:
        shutil.copyfile(OUT/name,arc/name)
    shutil.move(OUT/'control_energy_atlas',arc/'control_energy_atlas')
    for name in ['actual_fcpe.npz','actual_rmvpe.npz','actual_fcpe_binding.json','actual_rmvpe_binding.json']:shutil.copyfile(OUT/name,arc/name)
    plans=read(OUT/'agent_function_plans.json');geo=read(OUT/'native_word_geometry.json');events=[]
    for w,db in [(89,6.5),(224,3.2),(272,5.0)]:
        a,b=geo[w]['native_vowel'];dt=b-a;p=next(p for p in plans if any(e['word']==w for e in p['entries']))
        ev=dict(word=w,abbr='dyn',parameters=[a+.015,a+.24*dt,b-.22*dt,b-.012,db*10],purpose='Current actual weak high-entry nucleus: bounded local support retaining consonant, AP/SP and next-word level')
        p['controls'].append(ev);events.append(ev)
    dump('agent_function_plans.json',plans)
    doc=load_ustx(OUT/'lastpage_fresh.ustx')
    for p,part in zip(plans,doc['voice_parts']):
        c=next(c for c in part['curves'] if c['abbr']=='dyn');t=(part['position']+np.asarray(c['xs']))/960;c['ys']=np.rint(control(p,t,'dyn')).astype(int).tolist()
    save_ustx(doc,OUT/'lastpage_fresh.ustx');dump('local_gain_choices.json',dict(events=events,before_actual_energy=sha(arc/'actual_nucleus_energy.json'),automatic_normalization=False,unchanged_pitch_and_model_controls=True,source_fit=False))
    d=OUT/'native_dynamics_inputs';d.mkdir(exist_ok=True);raw=[];ones=[]
    for i in range(34):
        r=read(OUT/f'feeds/phrase_{i:03}.json');w=np.load(OUT/f'synthesis/phrase_{i:03}.npy').astype('<f4');path=d/f'raw_{i:03}.f32';unit=d/f'ones_{i:03}.f32';w.tofile(path);np.ones_like(w).tofile(unit)
        clock=dict(phrase=i,position_ms=r['position_ms'],leading_ms=r['head_frames']*r['frame_ms']);raw.append(dict(**clock,input_f32=str(path)));ones.append(dict(**clock,input_f32=str(unit)))
    dump('dynamics_raw_manifest.json',raw);dump('dynamics_ones_manifest.json',ones);u=Path('E:/software/OpenUtau-win-x64_dpV2/OpenUtau-win-x64')
    for label in ['raw','ones']:
        cmd=[str(u/'a2u-levelprobe-v15.exe'),'apply-dynamics','--project',str(OUT/'lastpage_fresh.ustx'),'--manifest',str(OUT/f'dynamics_{label}_manifest.json'),'--out',str(OUT/f'native_dynamics_{label}')];q=subprocess.run(cmd,cwd=u,capture_output=True,text=True,encoding='utf8',errors='replace');(OUT/f'dynamics_{label}.log').write_text(q.stdout+q.stderr,encoding='utf8');assert q.returncode==0,q.stdout+q.stderr
    report=[];syn=read(OUT/'synthesis_check.json')
    for i in range(34):
        w=np.fromfile(d/f'raw_{i:03}.f32',dtype='<f4');g=np.fromfile(OUT/f'native_dynamics_ones/phrase_{i:03}.f32',dtype='<f4');z=np.fromfile(OUT/f'native_dynamics_raw/phrase_{i:03}.f32',dtype='<f4');assert np.array_equal(w*g,z)
        t=syn['phrases'][i]['wave_start_s']+np.arange(len(w))/44100;r=read(OUT/f'feeds/phrase_{i:03}.json')
        for q in r['phones']:
            if q['phoneme'] in ['AP','SP']:
                m=(t>=q['positionMs']/1000+.025)&(t<=q['endMs']/1000-.025);assert np.all(g[m]==1)
        report.append(dict(context=i,native_multiply_exact=True,min_gain=float(min(g)),max_gain=float(max(g)),wave_sha256=sha(OUT/f'native_dynamics_raw/phrase_{i:03}.f32')))
    dump('native_dynamics_check.json',dict(phrases=report,AP_SP_core_unity=True,unit='10 DYN = 1 dB',actual_native_ApplyDynamics=True,first_F0_checker_fault='Overlapping plan supports overwrote another word target; owner-word lookup fixed, wrong report preserved'))
    bridge('export-render-probe',['--project',str(OUT/'lastpage_fresh.ustx'),'--out',str(OUT/'after_dyn_feeds'),'--indices',','.join(map(str,range(34)))],'after_dyn_feed_export')
    for i in range(34):
        for label in ['phrase','variance']:
            x=read(OUT/f'feeds/{label}_{i:03}.json');y=read(OUT/f'after_dyn_feeds/{label}_{i:03}.json');assert x==y,(i,label)
    old=load_ustx(arc/'lastpage_fresh.ustx');new=load_ustx(OUT/'lastpage_fresh.ustx')
    for x,y in zip(old['voice_parts'],new['voice_parts']):
        x['curves']=[c for c in x['curves'] if c['abbr']!='dyn'];y['curves']=[c for c in y['curves'] if c['abbr']!='dyn'];assert x==y
    dump('post_gain_condition_equality.json',dict(all34_actual_acoustic_variance_feeds_exact=True,all_native_note_pitch_phones_nonDYN_controls_exact=True,no_model_resynthesis_needed=True))
    print('NATIVE_DYNAMICS_AND_CURRENT_FEEDS_EXACT',flush=True)

def package():
    guarded();import copy
    d=OUT/'delivery';d.mkdir(exist_ok=True);v=np.load(OUT/'raw_vocal.npy');sep=read(OUT/'separation.json');b,sr=sf.read(sep['instrumental'],dtype='float64');info=sf.info(OUT/'source.wav');assert sr==44100 and len(b)==len(v)==info.frames
    vg,bg=1.5,.7;mix=v[:,None]*vg+b*bg;assert np.isfinite(mix).all() and max(abs(mix).ravel())<.99
    sf.write(d/'lastpage_fresh_mix.wav',mix,sr,subtype='PCM_24');pcm,sr0=sf.read(d/'lastpage_fresh_mix.wav',dtype='int32');sf.write(d/'lastpage_fresh_mix.flac',pcm,sr0,subtype='PCM_24');fp,srf=sf.read(d/'lastpage_fresh_mix.flac',dtype='int32');assert np.array_equal(pcm,fp) and srf==sr
    sf.write(d/'lastpage_fresh_vocal.wav',v*vg,sr,subtype='PCM_24');sf.write(d/'lastpage_fresh_backing.wav',b*bg,sr,subtype='PCM_24')
    # A wave part at recording time zero plus the current editable lead.
    doc=load_ustx(OUT/'lastpage_fresh.ustx');doc['tracks'][0]['volume']=float(20*np.log10(vg));track=copy.deepcopy(doc['tracks'][0]);track.update(track_name='Fresh separated backing',singer='',volume=0,voice_color_names=[]);doc['tracks'].append(track)
    doc['wave_parts']=[dict(name='Fresh MP3 backing · original recording clock',comment='',track_no=1,position=0,relative_path='lastpage_fresh_backing.wav',file_duration_ms=1000*len(v)/sr,channels=2,skip_ms=0,trim_ms=0)]
    path=d/'lastpage_fresh.ustx';save_ustx(doc,path);saved=load_ustx(path);assert saved==doc
    decisions=read(OUT/'agent_word_decisions.json');shutil.copyfile(OUT/'agent_word_decisions.json',OUT/'before_local_gain/agent_word_decisions.json')
    plans=read(OUT/'agent_function_plans.json')
    for w in decisions:
        p=plans[w['context']];w['controls']=[e for e in p['controls'] if e['word']==w['word']];dyn=[e for e in w['controls'] if e['abbr']=='dyn'];w['dyn_choice']=dict(events=dyn,unit='.1 dB') if dyn else 0
        w['nonpitch_reason']='Current actual-wave nucleus audit: finite bounded gain on three weak ni nuclei; native voicing core and other dynamics retained.'
    dump('agent_word_decisions.json',decisions)
    # Same fixed gains and clock for short comparison: own before/after only.
    focuses=[(72.1,77.9),(182.15,187.2),(209.5,214.8)]
    before=np.load(OUT/'before_local_gain/raw_vocal.npy')
    for i,(a,z) in enumerate(focuses):
        lo,hi=round(a*sr),round(z*sr);new=mix[lo:hi];old=before[lo:hi,None]*vg+b[lo:hi]*bg;gap=np.zeros((round(.6*sr),2));ab=np.concatenate([old,gap,new]);assert max(abs(ab).ravel())<1
        sf.write(d/f'nucleus_AB_{i+1}.wav',ab,sr,subtype='PCM_24')
    finalenergy=read(OUT/'actual_nucleus_energy.json')['words'];oldenergy=read(OUT/'before_local_gain/actual_nucleus_energy.json')['words'];gainstats=[]
    for k in [89,224,272]:gainstats.append(dict(word=k,actual_median30_db_gain=finalenergy[k]['rms30_db_percentiles'][2]-oldenergy[k]['rms30_db_percentiles'][2],actual_median50_db_gain=finalenergy[k]['rms50_db_percentiles'][2]-oldenergy[k]['rms50_db_percentiles'][2],peak_choice_db={89:6.5,224:3.2,272:5}[k]))
    dump('delivery_check.json',dict(samples=len(v),sample_rate=sr,duration=len(v)/sr,full_mix_peak=float(abs(mix).max()),vocal_peak=float(abs(v*vg).max()),fixed_gains=dict(vocal=vg,backing=bg),no_normalization_or_compression=True,exact_PCM24_FLAC=True,source_key_shift=0,tempo_factor=1,actual_nucleus_gain=gainstats,AB_order='own initial mix / 0.6 s silence / own final mix',fullsong_listening_pending=True,agent_perception=False,naturalness_accepted=False,files={str(p.relative_to(OUT)):sha(p) for p in d.iterdir() if p.is_file()}))
    print('DELIVERY_READY',len(v)/sr,'peak',abs(mix).max(),gainstats,flush=True)

def project_readback():
    guarded();path=OUT/'delivery/lastpage_fresh.ustx'
    bridge('inspect',['--project',str(path),'--out',str(OUT/'delivery_native_inspect.json')],'delivery_inspect')
    bridge('export-pitch',['--project',str(path),'--out',str(OUT/'delivery_native_pitch.json')],'delivery_pitch')
    bridge('export-phonemes',['--project',str(path),'--out',str(OUT/'delivery_native_phones.json')],'delivery_phones')
    raw=read(OUT/'delivery_native_pitch.json');plans=read(OUT/'agent_function_plans.json');errs=[]
    for ph,p in zip(raw['phrases'],plans):
        e=abs(np.asarray(ph['final_cents'])-target(p,np.asarray(ph['times_ms'])/1000));assert max(e)<=.501;errs.append(float(max(e)))
    a=read(OUT/'final_phones.json');b=read(OUT/'delivery_native_phones.json')
    for x,y in zip(a['parts'],b['parts']):
        assert x['notes']==y['notes']
        for q,z in zip(x['phrases'],y['phrases']):assert q['phones']==z['phones']
    dump('delivery_project_readback_check.json',dict(native_pitch_max_c=max(errs),all_current_phones_note_fields_exact=True,backing_file_exists=(OUT/'delivery/lastpage_fresh_backing.wav').exists(),roundtrip_from_yaml_exact=True))
    print('DELIVERED_PROJECT_CURRENT_NATIVE_EXACT',flush=True)

def record():
    # Record completion-bound files; do not inspect any historical project.
    delivery=read(OUT/'delivery_check.json');planes=read(OUT/'agent_function_plans.json');score=read(OUT/'chosen_score.json');pitch=read(OUT/'final_pitch_atlas_manifest.json')
    review=[]
    for folder,n in [('final_pitch_atlas',31),('control_energy_atlas',6)]:
        for i in range(n):
            path=OUT/f'{folder}/page_{i:02}.png';review.append(dict(file=str(path),sha256=sha(path),directly_read=True))
    dump('visual_review.json',dict(current_final_pages=review,source_initial_pages_read=39,corrected_source_focus_read=True,saved_pitch_scale=pitch,original_images_requested=True,tool_image_resizing_may_apply=True,live_GUI_all_song_checked=False,agent_audio_perception=False))
    skill=Path('C:/Users/Administrator/.codex/skills/singing-expression-editor');files=[p for p in skill.rglob('*') if p.is_file() and '__pycache__' not in p.parts];dump('current_skill_hashes.json',{str(p.relative_to(skill)):sha(p) for p in files})
    assert sha(SOURCE)==read(OUT/'input_binding.json')['source_sha256']
    counts=dict(words=318,sung_note_stages=332,total_notes=412,contexts=34,AP=34,SP=46,finite_gestures=sum(len(p['finite']) for p in planes),periodic_gestures=sum(len(p['periodic']) for p in planes),control_events=sum(len(p['controls']) for p in planes),pitch_windows=len(pitch['windows']))
    text=f'''# 《最后一页》从源录音重新制作 · 2026-10-07

完整版本已导出，原调、原录音时间轴，时长 {delivery['duration']:.6f} 秒。此次仅以用户给定 MP3 为歌曲输入，重新分离、转写、GAME、双 F0 和 HFA 对齐；未读取历史《最后一页》工程、音频或白烁作者工程。最新 singing-expression-editor Skill 用于条件判断和函数设计，本轮未修改 Skill。工具接口部分参考通用原生桥接源码及《花海》包装脚本的 I/O 段，未导入该曲参数。

新建谱面包含 {counts['words']} 字、{counts['sung_note_stages']} 个演唱阶段、{counts['total_notes']} 个音符和 {counts['contexts']} 个含演唱的上下文；气口 AP {counts['AP']}、SP {counts['SP']}，无 AP 单独上下文。每字均有本轮条件、函数选择、数值设计、替代方案和预期。{counts['finite_gestures']} 个有限动作、{counts['periodic_gestures']} 个发展后收回的周期动作、{counts['control_events']} 个有限发声／动态控制。低到高连接分别选用承接后推高、连续速度和短时直接到位。全曲声线候选为 Normal 75%／Classic 25%，两个模型阶段实际输入均核验。

首轮新对齐把两处“想”的低音入口分给前一字持续高音，已从当前 GAME／双 F0 定位后重跑新 HFA；首轮新 ASR 窗口又截短了两处“整／写”句尾，独立谱面补回持音，仍标为演唱解释而非已确认源时值。所有“重演／重写”的“重”明确为 chóng。字 106“没”的源音素身份／时值不确定仍保留，采用独立演唱时值，没有把自动对齐提升为真值。

实际合成完成全部 34 个新 variance（种子 11）／acoustic（种子 101）上下文；实际原生缓存、float32 控制增量、权重未变、两个阶段混合声线及重新生成输入核验。原生音高最大误差小于 0.501 音分，独立公式约 1.82e-12 音分；三个实际偏移网格检查通过。最终 31 页／{counts['pitch_windows']} 音高窗口和 6 页全部字腹实际 30／50 ms 能量、5 ms 步长及控制图已读，保存哈希在 visual_review.json。原始源图 39 页已读；两处新对齐修正另有已读焦点图。图像工具可能缩放显示，不声称整曲 GUI 逐帧检查。

实际能量检查后，三处“你”的偏弱字腹各设计最大 6.5／3.2／5.0 dB 的有限增益。采用原生 ApplyDynamics，实际波形乘法精确，AP／SP 核心增益为 1；其他字不做逐字归一化。增益后全部 34 个实际声学／方差输入与此前新合成精确相同，全部非 DYN 音符、音素、音高和发声控制精确相同。当前双 F0 技术诊断绑定增益后的实际人声，10112 个演唱核心帧可比较；它不证明自然度或声线舒适度。

交付含完整 PCM24 WAV、同 PCM FLAC、人声、伴奏、含同时间轴伴奏的可编辑 USTX，以及三组同增益局部前后比较。固定人声 1.5、伴奏 0.7，无逐句归一化、压缩或限幅，混音峰值 {delivery['full_mix_peak']:.6f}。原生重新读取交付工程后音符／音素精确、音高误差符合上述范围。

失败与限制：首轮 PITD 写成绝对 tick，改为 part 相对 tick；原生音符曲线延伸到邻音符造成重复叠加，改为只写入口连接再按实际原生基线编译 PITD。失败新草稿保留。首轮实际双 F0 报告将重叠上下文 support 当成目标所有权，造成虚高误差，已改用字的实际所属上下文；错误报告保留于 before_local_gain。一次增益辅助脚本缺 import 在任何文件复制前失败，已修正。一次自动审批服务用量故障未执行编译，用户继续后正常重试完成。

Agent 没有音频感知验证，歌词的独立语义修订、气口意图及上述源时值解释仍待试听确认；完整歌曲听感／自然度未验收，不声称未见歌曲能力已通过。

歌曲原文件 SHA256：{sha(SOURCE)}。
生产选择、模型输入、状态、波形、失败草稿、原生检查与全部交付 SHA256 均保存在 runs/lastpage_fresh_source_20261007，completion_manifest.json 绑定最终版本。
'''
    path=ROOT/'docs/lastpage-fresh-source-20261007.md';path.write_text(text,encoding='utf8')
    agents=ROOT/'AGENTS.md';backup=OUT/'AGENTS.before.md';shutil.copyfile(agents,backup)
    entry=f'''\n- 2026-10-07 completed NEW MP3-only LastPage production at user request.\n  docs/lastpage-fresh-source-20261007.md; runs/lastpage_fresh_source_20261007.\n  No historical LastPage or Baishuo project/audio inputs. Fresh MelBand/ASR/\n  unconstrained GAME/dual F0/HFA;318 own choices/332 sung stages/412notes/34contexts.\n  Source word106 unknown retained;two low xiang attribution fixes/two carried\n  releases/chong pronunciation declared,not listening-confirmed source truth.\n  All34 fresh variance11/acoustic101,Normal75/Classic25 bothstages,weights exact.\n  Independent math/native .501c/three shifted grids/current float32 inputs pass;\n  31pitch {counts['pitch_windows']}windows and6 actualenergy/control pages read.\n  Three bounded ni gains native ApplyDynamics;APSPunity/nonDYN/input equality.\n  Overlapping-support F0 checker corrected;actualdual10112 comparable each,\n  technicalonly;old new-task drafts/reports retained. Original MP3 unchanged.\n  Full245.577143s WAV/exactPCM FLAC/vocal/backing/editableUSTX/3samegainABs;\n  mixpeak {delivery['full_mix_peak']:.6f},fixed gains1.5/.7,readback exact.\n  Skill used unchanged;Agentperceptionfalse/listeningpending/naturalnessfalse.\n'''
    agents.write_text(entry+agents.read_text(encoding='utf-8-sig'),encoding='utf8')
    paths=[p for p in OUT.rglob('*') if p.is_file() and p.name!='completion_manifest.json']+[path,agents]+[ROOT/f'tools/lastpage_fresh_{x}_20261007.py' for x in ['source','design','expression','synthesis','review','finish']]
    dump('completion_manifest.json',dict(counts=counts,original_unchanged=True,AGENTS_before_sha256=sha(backup),agent_perception=False,full_song_listening_pending=True,naturalness_accepted=False,files={str(p):sha(p) for p in paths}))
    print('COMPLETION_BOUND',len(paths),counts,flush=True)

def verify_final():
    guarded();syn=read(OUT/'synthesis_check.json');plans=read(OUT/'agent_function_plans.json');rows=[]
    for i,p in enumerate(plans):
        g=np.fromfile(OUT/f'native_dynamics_ones/phrase_{i:03}.f32',dtype='<f4');t=syn['phrases'][i]['wave_start_s']+np.arange(len(g))/44100
        actual=20*np.log10(g.astype(np.float64));expected=control(p,t,'dyn')*.1;err=float(max(abs(actual-expected)));assert err<.1,(i,err)
        limit=max([0]+[e['parameters'][-1]*.1 for e in p['controls'] if e['abbr']=='dyn']);assert max(actual)<limit+1e-5
        rows.append(dict(context=i,actual_native_gain_db_error=err,designed_cap_db=limit))
    models=syn['models'];assert all(sha(k)==v for k,v in models.items())
    ins=read(OUT/'delivery_inspect.json');assert len(ins['voice_parts'])==34 and ins['wave_parts'][0]['loaded'] and ins['wave_parts'][0]['position']==0
    assert sum(p['notes'] for p in ins['voice_parts'])==412
    assert all(not p['invalidNotes'] and not p['invalidPhonemes'] for p in ins['voice_parts'])
    v=np.load(OUT/'raw_vocal.npy');wav,sr=sf.read(OUT/'delivery/lastpage_fresh_vocal.wav',dtype='float64');quant=float(max(abs(v*1.5-wav)));assert quant<2**-23+1e-12
    backing,srb=sf.read(OUT/'delivery/lastpage_fresh_backing.wav',dtype='float64');mix,srm=sf.read(OUT/'delivery/lastpage_fresh_mix.wav',dtype='float64');sep,_=sf.read(read(OUT/'separation.json')['instrumental'],dtype='float64');expected=v[:,None]*1.5+sep*.7;me=float(abs(mix-expected).max());assert me<2**-23+1e-12 and max(abs(mix).ravel())<1
    dump('final_actual_checks.json',dict(gain_rows=rows,original_model_weights_unchanged=True,delivered_vocal_pcm_max_error=quant,mix_pcm_max_error=me,exact_full_source_sample_count=len(v),all412_native_notes_no_errors=True,all34_native_contexts=True,backing_native_loaded_at_zero=True,source_readback_unknowns_retained=[106],carried_release_hypotheses=[221,269],source_unknown_not_relabelled=True,actual_F0_binding='Final native-gain float vocal before constant global gain and PCM24 quantization; delivered quantization bounded above'))
    print('FINAL_ACTUAL_CHECKS_PASS',max(r['actual_native_gain_db_error'] for r in rows),quant,me,flush=True)

def repeat_current():
    guarded();import onnxruntime as ort
    from agent2utau.expression.variance_expectation import gaussian_frame_noise,CHANNELS
    i=8;r=read(OUT/f'feeds/phrase_{i:03}.json');vr=read(OUT/f'feeds/variance_{i:03}.json');v=tensors(vr['tensors']);b=tensors(r['tensors']);nf=b['f0'].size
    op=ort.SessionOptions();op.intra_op_num_threads=op.inter_op_num_threads=1
    vs,ac,vc=[ort.InferenceSession(str(p),sess_options=op,providers=['CPUExecutionProvider'])for p in [OUT/'models/variance.onnx',OUT/'models/acoustic.onnx',r['vocoder_model']]]
    names=[q.name for q in vs.get_outputs()];v['probe_noise']=gaussian_frame_noise(11,3,24,nf);pred=dict(zip(names,vs.run(names,v)));state=np.load(OUT/f'synthesis/state_{i:03}.npz')
    for k in CHANNELS:
        assert np.array_equal(pred[k+'_pred'],state[k]);lo,hi=(-10,10) if k=='tension' else (-96,0);delta=np.asarray(r['expression_deltas'][k],np.float32)[None,:];b[k]=np.clip(pred[k+'_pred']+delta,lo,hi).astype(np.float32);assert np.array_equal(b[k],state['final_'+k])
    b['probe_noise']=gaussian_frame_noise(101,1,128,nf);mel=ac.run(['mel'],b)[0]
    if r['acoustic_mel_base']!=r['vocoder_mel_base']:mel*=np.log(10) if r['acoustic_mel_base']=='10' else 1/np.log(10)
    w=vc.run(None,dict(mel=mel,f0=np.asarray(r['vocoder_f0'],np.float32)[None,:]))[0].reshape(-1);old=np.load(OUT/f'synthesis/phrase_{i:03}.npy');assert np.array_equal(w,old)
    dump('current_fresh_repeat_check.json',dict(context=i,new_sessions=True,new_variance_predictions_exact=True,new_final_control_inputs_exact=True,new_wave_exact=True,before_native_dynamic_gain=True,current_inputs_only=True));print('NEW_CURRENT_REPEAT_EXACT',flush=True)

if __name__=='__main__':globals()[sys.argv[1]]()
