"""One frozen DYN envelope with native Core gain and sealed F raw reuse."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import numpy as np
import yaml
from assemble_lastpage_accepted_baseline_20261011 import ROOT,ENTRIES,load,save,sha,ref,check
from agent2utau.resources.config import load_config
from agent2utau.openutau.ustx import TempoMap
from agent2utau.knowledge import check_plan_knowledge

PRIOR=ROOT/'runs/research/lastpage-own-li-voic-feedback-20261012'
F=ROOT/'runs/experiments/lastpage-own-control-neutral-20261012'
BASE=ROOT/'runs/lastpage_loudness_skill_v02_20261007'
CURRENT=ROOT/'runs/production/lastpage-accepted-baseline-20261011'
RUN=ROOT/'runs/experiments/lastpage-own-li-dyn-20261012'

def runtime():
    check(load(RUN/'protected-before.json'))
    for p,h in load(RUN/'native-inputs/runtime.json').items():assert sha(Path(p))==h,p
    for p,h in load(RUN/'native-inputs/dyn-tool-runtime.json').items():assert sha(Path(p))==h,p
    plan=load(RUN/'design/protocol.json');check_plan_knowledge(plan,RUN/'design/protocol.json')

def shape(t,nodes):
    if t<=nodes[0][0] or t>=nodes[-1][0]:return 0.
    for (a,x),(b,y) in zip(nodes,nodes[1:]):
        if a<=t<=b:
            u=(t-a)/(b-a);return x+(y-x)*u*u*(3-2*u)
    raise AssertionError(t)

def prepare():
    assert not RUN.exists();seal=load(PRIOR/'completion-manifest.json');check(seal['files']+seal['documents']+seal['entries'])
    original=load(PRIOR/'protected-before.json')+seal['files']+seal['documents']+[ref(PRIOR/'completion-manifest.json')]
    check(original);RUN.mkdir(parents=True);(RUN/'logs').mkdir();(RUN/'score').mkdir()
    registry='docs/knowledge/acoustic-manifestations-20261009/active-knowledge-sources.json'
    save(RUN/'protected-before.json',[r for r in original if r['path']!=registry])
    for name in ENTRIES+[registry]:
        p=RUN/'before'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((ROOT/name).read_bytes())
    plan=load(PRIOR/'design/next-li-DYN-protocol.json');assert plan['budget']['new_seeded_variance_calls']==0 and plan['budget']['new_F0_calls']==2
    check([plan[k] for k in ['baseline_score','baseline_audio','author_reference']]);(RUN/'design').mkdir(exist_ok=True)
    (RUN/'design/knowledge_context.json').write_bytes((PRIOR/'design/knowledge_context.json').read_bytes())
    doc=yaml.safe_load((ROOT/plan['baseline_score']['path']).read_text(encoding='utf-8-sig'));h=copy.deepcopy(doc);tm=TempoMap.from_doc(h)
    c=next(c for c in h['voice_parts'][28]['curves'] if c['abbr']=='dyn');assert all(y==0 for y in c['ys']) and all(x%5==0 for x in c['xs'])
    c['ys']=[int(np.rint(shape(tm.tick_to_ms(h['voice_parts'][28]['position']+x)/1000,plan['gesture']['UI_nodes_s']))) for x in c['xs']]
    assert min(c['ys'])==-40 and max(c['ys'])==15
    full=RUN/'score/lastpage_own_li_dyn_H.ustx';full.write_text(yaml.safe_dump(h,allow_unicode=True,sort_keys=False),encoding='utf-8')
    native=copy.deepcopy(h);native['voice_parts']=[native['voice_parts'][i] for i in [28,29]];native['wave_parts']=[];native['tracks']=[native['tracks'][0]]
    native['tracks'][0].update(volume=0,pan=-100,mute=False,solo=False)
    (RUN/'score/native_H.ustx').write_text(yaml.safe_dump(native,allow_unicode=True,sort_keys=False),encoding='utf-8')
    plan.update(status='frozen_before_execution',execution_authorization='2026-10-12 user 下一步',original_frozen_protocol=ref(PRIOR/'design/next-li-DYN-protocol.json'),
        candidate=ref(full),native_score=ref(RUN/'score/native_H.ustx'),raw_sources=[ref(F/f'fresh/context{ctx}/{label}/raw.npy') for ctx in [28,29] for label in ['F','F_repeat']])
    save(RUN/'design/protocol.json',plan);_,receipt=check_plan_knowledge(plan,RUN/'design/protocol.json');save(RUN/'evaluation/knowledge_receipt.json',receipt)
    save(RUN/'native-inputs/runtime.json',load(F/'native-inputs/runtime.json'))
    ou=Path(load_config()['openutau_dir']);tools=[ou/('a2u-levelprobe-v15'+s) for s in ['.exe','.dll','.deps.json','.runtimeconfig.json']]
    snapshot=ROOT/'runs/yuai_level_edge_study_v15_20261007/native_probe_build/a2u-levelprobe-v15.dll'
    assert sha(snapshot)==sha(tools[1]);save(RUN/'native-inputs/dyn-tool-runtime.json',{str(p):sha(p) for p in tools})
    save(RUN/'native-inputs/dyn-tool-source.json',dict(installed_binary=str(tools[1]),sha256=sha(tools[1]),matching_old_build=ref(snapshot),
        source=ref(ROOT/'runs/yuai_level_edge_study_v15_20261007/native_probe_source/Program.cs'),
        calls=['export-dynamics','apply-dynamics'],no_deployment_or_install_change=True))
    runtime();print('H DYN-only score and inherited7-ID knowledge receipt prepared.',flush=True)

def call(name,args,exe):
    result=RUN/f'native-inputs/{name}-result.json'
    if result.exists():return load(result)
    print(name,flush=True);p=subprocess.run([str(exe),*args],cwd=exe.parent,capture_output=True,encoding='utf-8',errors='replace',timeout=1200)
    log=RUN/f'logs/{name}.log';assert not log.exists();log.write_text(p.stdout+p.stderr,encoding='utf-8')
    assert p.returncode==0,p.stdout[-1000:]+p.stderr[-1000:]
    r=json.loads(p.stdout.strip().splitlines()[-1]);assert not r.get('errors') and r.get('ok',True);save(result,r);return r

def native():
    runtime();ou=Path(load_config()['openutau_dir']);exe=ou/'a2u-shfcprobe-20261008.exe';p=str(RUN/'score/native_H.ustx')
    commands=[('roundtrip',['roundtrip','--project',p,'--out',str(RUN/'native-inputs/H-roundtrip.ustx')]),
        ('phones',['export-phonemes','--project',p,'--out',str(RUN/'native-inputs/H-phones.json')]),
        ('pitch',['export-pitch','--project',p,'--out',str(RUN/'native-inputs/H-pitch.json')]),
        ('render',['render','--project',p,'--out',str(RUN/'native-render/H.wav'),'--mixdown','--timeout','15']),
        ('probe',['export-render-probe','--project',p,'--out',str(RUN/'native-inputs/H'),'--indices','0,1'])]
    for name,args in commands:call('H-'+name,args,exe)
    call('H-export-dynamics',['export-dynamics','--project',p,'--out',str(RUN/'native-inputs/H-dynamics.json')],ou/'a2u-levelprobe-v15.exe')
    runtime();print('H native dependencies and DYN curves exported; independent gate required.',flush=True)

def apply():
    assert load(RUN/'evaluation/native-independent-check.json')['status']=='passed' and not (RUN/'processed').exists();runtime()
    (RUN/'dynamics-inputs').mkdir();(RUN/'processed').mkdir();ou=Path(load_config()['openutau_dir'])
    f=load(F/'native-inputs/F/phrase_000.json');origin=load(BASE/'synthesis/phrase_028.json')['wave_start_s']
    clock=dict(phrase=0,position_ms=f['position_ms'],leading_ms=f['position_ms']-origin*1000)
    manifests=[]
    for label in ['H','H_repeat','gain']:
        if label=='gain':x=np.ones_like(np.load(F/'fresh/context28/F/raw.npy',allow_pickle=False))
        else:x=np.load(F/f'fresh/context28/{"F" if label=="H" else "F_repeat"}/raw.npy',allow_pickle=False)
        path=RUN/f'dynamics-inputs/{label}.f32';x.astype('<f4').tofile(path)
        mf=RUN/f'design/dynamics-{label}-manifest.json';save(mf,[dict(**clock,input_f32=str(path))]);manifests.append((label,mf))
    for label,mf in manifests:
        call('H-apply-'+label,['apply-dynamics','--project',str(RUN/'score/native_H.ustx'),'--manifest',str(mf),'--out',str(RUN/f'processed/{label}')],ou/'a2u-levelprobe-v15.exe')
    dyn=load(RUN/'native-inputs/H-dynamics.json')['phrases'][0];tm=TempoMap.from_doc(yaml.safe_load((RUN/'score/native_H.ustx').read_text(encoding='utf-8')))
    start=dyn['position']-dyn['leading'];save(RUN/'processed/layout.json',dict(**clock,samples=len(x),dynamic_curve=dyn['dynamics'],
        dynamic_start_tick=start,dynamic_end_ms=[tm.tick_to_ms(start+5*(i+1)) for i in range(len(dyn['dynamics']))],
        native_export=ref(RUN/'native-inputs/H-dynamics.json'),raw_origin_s=origin,
        clock_role='sealed F raw origin retained; ApplyDynamics receives this position/leading manifest, not a retimed waveform'))
    runtime();save(RUN/'processed/execution.json',dict(new_fixed_seeded_variance_calls=0,new_fixed_seeded_synthesis_waveforms=0,
        processed_contribution_repeats=2,gain_probe=1,sealed_F_reused=True,new_F0_calls_pending=2))
    print('Actual Core DYN applied to F raw and repeat; no fresh synthesis.',flush=True)

if __name__=='__main__':{'prepare':prepare,'native':native,'apply':apply}[sys.argv[1]]()
