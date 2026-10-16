"""Create diagnostic copies and a separately built, private-cache native bridge."""
import copy
import json
from pathlib import Path
import shutil
import yaml
import numpy as np
from freeze_stage_2d import ROOT, HERE, OUT, load, sha
from shfc_path_runner import load_sealed_protocol
from shfc_native_preflight import planned_curve, sample_curve, check_sample_support
from agent2utau.resources.config import load_config

def save(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8') as f:
        json.dump(data,f,ensure_ascii=False,indent=2); f.write('\n')

def main():
    b=load(HERE/'stage_2e_execution_baseline_binding.json'); run=ROOT/b['run']
    assert sha(ROOT/b['manifest'])==b['sha256']
    target=run/'preparation.json'; assert not target.exists()
    p=load_sealed_protocol(); install=Path(load_config()['openutau_dir']).resolve()
    for alias,digest in p['fixed']['runtime_expected_hashes'].items():
        assert sha(install/alias.removeprefix('external-resource/OpenUtau/'))==digest
    comparisons=load(OUT/'comparison-bindings.json'); rows=[]
    for case,record in zip(p['cases'],['RESP-002','RESP-007']):
        row=next(r for r in comparisons['rows'] if r['record_id']==record)
        ix=case['condition']['context']; cid=case['condition']['id']
        ref=next(r for r in row['native_and_fresh_artifact_bindings'] if r['path'].endswith(f'/native_A/phrase_{ix:03}.json'))
        assert sha(ROOT/ref['path'])==ref['expected_sha256']; old=load(ROOT/ref['path'])
        source=ROOT/case['baseline_project']['path']; assert sha(source)==case['baseline_project']['sha256']
        project=yaml.safe_load(source.read_text(encoding='utf-8')); curve=planned_curve(project,old,case)
        cents=sample_curve(project,old,curve); proof=check_sample_support(old,cents,case)
        a=copy.deepcopy(project); a['expressions']['shfc']['min']=-1200; a['expressions']['shfc']['max']=1200
        assert not any(y for c in a['voice_parts'][ix]['curves'] if c['abbr']=='shfc' for y in c['ys'])
        s=copy.deepcopy(a); s['voice_parts'][ix]['curves']=[c for c in s['voice_parts'][ix]['curves'] if c['abbr']!='shfc']+[curve]
        restored=copy.deepcopy(s); restored['voice_parts'][ix]['curves']=copy.deepcopy(a['voice_parts'][ix]['curves'])
        assert restored==a
        folder=run/'projects'/cid; folder.mkdir(parents=True)
        for label,data in [('A',a),('S',s)]:
            path=folder/f'{label}.ustx'; path.write_text(yaml.safe_dump(data,allow_unicode=True,sort_keys=False),encoding='utf-8')
            assert yaml.safe_load(path.read_text(encoding='utf-8'))==data
        rows.append(dict(condition_id=cid,phrase_index=ix,source=case['baseline_project'],
            A=dict(path=(folder/'A.ustx').relative_to(ROOT).as_posix(),sha256=sha(folder/'A.ustx')),
            S=dict(path=(folder/'S.ustx').relative_to(ROOT).as_posix(),sha256=sha(folder/'S.ustx')),
            historical_a=ref,curve=curve,sampling=proof))
    build=ROOT/'runs/build/table2-shfc-native-20261011'; build.mkdir()
    code=(ROOT/'bridge/OuBridge/Program.cs').read_text(encoding='utf-8')
    assert code.count('static class Program')==1 and code.count('Boot();')==1
    code=code.replace('static class Program','static partial class Program')
    code=code.replace('Boot();','ResearchBoot(opt); Boot();')
    code=code.replace('PathManager.Inst.LogFilePath','Path.Combine(work,"research-native.log")')
    code=code.replace('case "doctor":','case "acquire": result = Acquire(opt); break;\n                    case "dynamics": result = Dynamics(opt); break;\n                    case "doctor":')
    (build/'Program.cs').write_text(code,encoding='utf-8')
    imports='using System;\nusing System.Collections.Generic;\nusing System.IO;\nusing System.Linq;\nusing System.Reflection;\nusing System.Threading;\nusing OpenUtau.Core;\nusing OpenUtau.Core.Ustx;\n'
    (build/'NativeBatch.cs').write_text(imports+(HERE/'NativeBatch.cs').read_text(encoding='utf-8'),encoding='utf-8')
    shutil.copyfile(ROOT/'bridge/OuBridge/RenderProbe.cs',build/'RenderProbe.cs')
    csproj=(ROOT/'bridge/OuBridge/OuBridge.csproj').read_text(encoding='utf-8')
    (build/'NativeBatch.csproj').write_text(csproj.replace('a2u-bridge','a2u-table2-paths-20261011'),encoding='utf-8')
    source_paths=[ROOT/'bridge/OuBridge/Program.cs',ROOT/'bridge/OuBridge/RenderProbe.cs',ROOT/'bridge/OuBridge/OuBridge.csproj',HERE/'NativeBatch.cs',HERE/'prepare_stage_2e_execution.py']
    save(target,dict(protocol_id=p['id'],install_root=str(install),conditions=rows,build=build.relative_to(ROOT).as_posix(),
        source_bindings=[dict(path=x.relative_to(ROOT).as_posix(),sha256=sha(x)) for x in source_paths],
        generated_sources=[dict(path=x.relative_to(ROOT).as_posix(),sha256=sha(x)) for x in build.iterdir()],
        published_projects_edited=False,existing_audio_edited=False,new_native_exports=0,new_waveforms=0))
    print(json.dumps(dict(build=str(build),conditions=2,planned_frames=[r['sampling'] for r in rows])))

if __name__=='__main__': main()
