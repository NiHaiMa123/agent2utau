"""Acquire four current native input records in one new cache per condition."""
import subprocess
from freeze_stage_2d import ROOT, HERE, load, sha
from prepare_stage_2e_execution import save

def main():
    binding=load(HERE/'stage_2e_execution_baseline_binding.json'); run=ROOT/binding['run']
    prep=load(run/'preparation.json'); build=ROOT/prep['build']
    binary=build/'bin/a2u-table2-paths-20261011.dll'
    assert binary.exists() and not (run/'native-acquisition.json').exists()
    save(run/'native-build-bindings.json',dict(files=[dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p)) for p in (build/'bin').iterdir() if p.is_file()]))
    rows=[]
    for case in prep['conditions']:
        cid=case['condition_id']; work=run/'native-work'/cid
        for label in ['A','S']:
            ref=case[label]; assert sha(ROOT/ref['path'])==ref['sha256']
            output=run/'native'/cid/label; assert not output.exists()
            cmd=['dotnet',str(binary),'acquire','--project',str(ROOT/ref['path']),
                '--out',str(output),'--indices',str(case['phrase_index']),
                '--work',str(work),'--workspace',str(ROOT),'--install',prep['install_root']]
            print('native acquisition '+cid+' '+label,flush=True)
            result=subprocess.run(cmd,cwd=ROOT,capture_output=True,timeout=900)
            (run/'logs'/f'native-{cid}-{label}.stdout').write_bytes(result.stdout)
            (run/'logs'/f'native-{cid}-{label}.stderr').write_bytes(result.stderr)
            save(run/'logs'/f'native-{cid}-{label}.invocation.json',dict(command=cmd,returncode=result.returncode))
            if result.returncode:
                print(result.stdout.decode('utf-8-sig',errors='replace')[-2500:],flush=True)
                print(result.stderr.decode('utf-8-sig',errors='replace')[-2500:],flush=True)
                raise SystemExit('Native acquisition failed; retained without effect interpretation')
            data=__import__('json').loads(result.stdout.decode('utf-8-sig'))
            assert data['ok'] and data['technical_native_waveform_only']
            assert __import__('pathlib').Path(data['private_cache']).resolve()==(work/'Cache').resolve()
            save(output/'acquisition-layout.json',data)
            rows.append(dict(condition_id=cid,label=label,files=[dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p)) for p in output.iterdir() if p.is_file()]))
    save(run/'native-acquisition.json',dict(records=rows,new_native_record_pairs=4,
        technical_native_cache_waveforms=4,causal_seeded_waveforms=0,automatic_retry=False))

if __name__=='__main__': main()
