"""Apply actual installed-Core DYN to the exact finite new raw waveforms."""
import json
import subprocess
from freeze_stage_2d import ROOT,HERE,load,sha
from prepare_stage_2e_execution import save

def main():
    run=ROOT/load(HERE/'stage_2e_execution_baseline_binding.json')['run']
    raw=load(run/'raw-execution.json'); assert raw['rendered_waveforms']==16 and raw['raw_exact_repetitions']
    assert not (run/'dynamics-execution.json').exists()
    prep=load(run/'preparation.json'); build=ROOT/load(run/'dynamics-preparation.json')['build']
    binary=build/'bin/a2u-table2-paths-20261011.dll'
    save(run/'dynamics-build-bindings.json',dict(files=[dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p)) for p in (build/'bin').iterdir() if p.is_file()]))
    rows=[]
    for case in prep['conditions']:
        cid=case['condition_id']; out=run/'dynamics'/cid
        assert not out.exists()
        for row in raw['raw']:
            if row['condition_id']==cid: assert sha(ROOT/row['raw']['path'])==row['raw']['sha256']
        cmd=['dotnet',str(binary),'dynamics','--project',str(ROOT/case['A']['path']),
            '--out',str(out),'--indices',str(case['phrase_index']),'--input',str(run/'raw'/cid),
            '--work',str(run/'native-work'/cid),'--workspace',str(ROOT),'--install',prep['install_root']]
        result=subprocess.run(cmd,cwd=ROOT,capture_output=True,timeout=180)
        (run/'logs'/f'dynamics-{cid}.stdout').write_bytes(result.stdout)
        (run/'logs'/f'dynamics-{cid}.stderr').write_bytes(result.stderr)
        save(run/'logs'/f'dynamics-{cid}.invocation.json',dict(command=cmd,returncode=result.returncode))
        if result.returncode: raise RuntimeError(result.stdout.decode('utf-8-sig',errors='replace')[-2000:])
        row=json.loads(result.stdout.decode('utf-8-sig')); assert row['ok'] and row['files']==8 and row['DYN_actual_core']
        save(out/'layout.json',row); rows.append(dict(condition_id=cid,layout=row,
            artifacts=[dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p)) for p in out.iterdir() if p.is_file()]))
        print('actual Core DYN '+cid+' eight waves',flush=True)
    save(run/'dynamics-execution.json',dict(conditions=rows,actual_Core_DYN_waveforms=16,delivery_audio=0))

if __name__=='__main__':main()
