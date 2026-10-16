"""Seal current source-only delivery, public evidence and current plan entries."""
from source import ROOT,RUN,load,save,sha,ref
import numpy as np,soundfile as sf,yaml,copy,sys,shutil,json
from pathlib import Path
from design import cfg
from agent2utau.openutau.bridge import run_bridge

def finish():
    out=RUN/'delivery';audio={}
    for name in ['yuai_source_only_v01_vocal.wav','yuai_source_only_v01_mix.wav','backing.wav','backing_playback.wav']:
        p=out/name;x,sr=sf.read(p,dtype='float64',always_2d=True);assert sr==44100 and len(x)==11487168 and np.isfinite(x).all() and np.max(abs(x))<1
        audio[name]=dict(file=ref(p),sample_rate=sr,samples=len(x),channels=x.shape[1],duration_s=len(x)/sr,subtype=sf.info(p).subtype,peak=float(np.max(abs(x))),full_scale_samples=int(np.count_nonzero(abs(x)>=1)))
    assert sha(out/'backing.wav')==sha(RUN/'inputs/source_backing.wav')
    x,_=sf.read(out/'backing.wav',dtype='float64',always_2d=True);y,_=sf.read(out/'backing_playback.wav',dtype='float64',always_2d=True);assert np.array_equal(x,y)
    voice,_=sf.read(out/'yuai_source_only_v01_vocal.wav',dtype='float64');mix,_=sf.read(out/'yuai_source_only_v01_mix.wav',dtype='float64',always_2d=True)
    raw,_=sf.read(RUN/'final-stage/native-level/native_vocal.wav',dtype='float64');assert np.array_equal(voice[:len(raw)],raw*2) and not np.any(voice[len(raw):])
    common=min(1,.93/np.max(abs(x+voice[:,None])));assert np.max(abs(mix-common*(x+voice[:,None])))<=2**-23
    projects=[out/'yuai_source_only_v01.ustx',out/'yuai_source_only_v01_playback.ustx',ROOT/'projects/latest/yuai_source_only_v01.ustx',ROOT/'projects/latest/yuai_source_only_v01_playback.ustx']
    native=yaml.safe_load((RUN/'final-stage/compiled-level/project.ustx').read_text(encoding='utf8'))
    import subprocess
    exe=RUN/'native-runtime/a2u-yuai-wavecheck.exe';checks=[]
    for i,p in enumerate(projects):
        doc=yaml.safe_load(p.read_text(encoding='utf8'));assert doc['voice_parts']==native['voice_parts'];assert sum(len(z['notes']) for z in doc['voice_parts'])==440
        for w in doc['wave_parts']:assert (p.parent/w['relative_path']).resolve().is_file()
        r=subprocess.run([str(exe),'inspect','--project',str(p)],cwd=exe.parent,capture_output=True,encoding='utf8',errors='replace',timeout=90);obj=json.loads(r.stdout.strip().splitlines()[-1]);assert r.returncode==0 and obj['ok'] and all(w['loaded'] for w in obj['wave_parts'])
        save(RUN/f'evaluation/final-project-{i}-inspect.json',dict(project=ref(p),result=obj,stderr=r.stderr));checks.append(ref(p))
    plan=load(RUN/'final-stage/design/functions-level.json');from agent2utau.knowledge import check_plan_knowledge
    _,receipt=check_plan_knowledge(plan,RUN/'final-stage/design/functions-level.json');save(RUN/'evaluation/final-knowledge-gate.json',receipt)
    # Current model/implementation resources only. Hashing a declared model is
    # not a claim that every optional model/branch was executed.
    a=load(RUN/'native-input/actual-final/phrase_000.json');v=load(RUN/'native-input/actual-final/variance_000.json');resources={}
    for root in [Path(a['singer_location']),Path(a['vocoder_model']).parent,RUN/'native-runtime/Dependencies/rmvpe']:
        for p in root.rglob('*'):
            if p.is_file() and p.suffix.lower() in ['.onnx','.yaml','.json','.emb','.txt']:resources[str(p)]=sha(p)
    save(RUN/'evaluation/current-model-resource-bindings.json',dict(resources=resources,only_current_model_weights_configs=True,optional_resource_hash_not_execution_claim=True))
    dyn=load(RUN/'final-stage/evaluation/dynamics-level.json')['phrases'];phones=load(RUN/'final-stage/compiled-level/phones.json');flat=[p for part in phones['parts'] for ph in part['phrases'] for p in ph['phones']]
    for phrase,pp in zip(dyn,[ph for part in phones['parts'] for ph in part['phrases']]):
        for p in pp['phones']:
            if p['phoneme'] not in ['AP','SP']:continue
            t=np.asarray(phrase['times_ms']);m=(t>=p['start_ms']+.01)&(t<=p['end_ms']-.01);assert np.all(np.asarray(phrase['dynamics'])[m]==1)
    save(RUN/'evaluation/final-DYN-nonsinging-audit.json',dict(status='passed',native_phrases=len(dyn),AP=sum(p['phoneme']=='AP' for p in flat),SP=sum(p['phoneme']=='SP' for p in flat),AP_SP_interior_amplitude_exactly1=True,
        native_amplitude_range=[min(min(z['dynamics']) for z in dyn),max(max(z['dynamics']) for z in dyn)],whole_vowels=371,Agent_listened=False))
    manifest=dict(status='rendered_checked_pending_human_listening',finished='2026-10-15',audio=audio,source_allowlist=ref(RUN/'inputs/allowed-source-manifest.json'),
        projects=checks,source_key=True,original_clock=True,vocal_gain=2.0,backing_gain=1.0,common_mix_headroom=float(common),
        mix_formula='common*(2*native_Core_DYN_vocal+unchanged_decoded_source_backing)',pan_compensation_db=10*np.log10(2),no_per_word_normalization=True,
        intermediate_precision='Current native RenderToFiles PCM16; delivered PCM24 does not restore intermediate quantization.',
        playback_transport=ref(RUN/'evaluation/backing-transport-compatibility.json'),playback_check=ref(RUN/'evaluation/playback-path-equivalence.json'),
        current_run_raw_reused_only_for_DYN=True,author_or_historical_production_data_used=False,Agent_listened=False,naturalness_accepted=False)
    save(out/'delivery-manifest.json',manifest)
    save(RUN/'evaluation/local-checks.json',dict(relevant_pytest_passed=77,pytest_paths=['tests/unit','tests/skills','tests/contracts/test_workflow.py','tests/contracts/test_knowledge_context.py','tests/contracts/test_independent_evaluation.py'],
        repository_worktree_gate='passed',gate_author_and_ZIP_checks='Preservation byte checks only, not production inputs or author-array interpretation',audio_payloads=0,skill_links=105,single_agent=True,automatic_CI=False,skill_modified_this_task=False))
    print('SEALED',len(resources),'current resource bindings; 4 native projects loaded;',len(flat),'phones',flush=True)

if __name__=='__main__':finish()
