"""Build a separately bound DYN helper; keep acquisition binary/source intact."""
import shutil
from freeze_stage_2d import ROOT,HERE,load,sha
from prepare_stage_2e_execution import save

def main():
    run=ROOT/load(HERE/'stage_2e_execution_baseline_binding.json')['run']
    prep=load(run/'preparation.json'); source=ROOT/prep['build']
    build=ROOT/'runs/build/table2-shfc-dynamics-20261011'; assert not build.exists()
    build.mkdir()
    for name in ['Program.cs','RenderProbe.cs','NativeBatch.csproj']:
        shutil.copyfile(source/name,build/name)
    text=(source/'NativeBatch.cs').read_text(encoding='utf-8')
    old='["samples"]=n.Value,["files"]=8,["DYN_actual_core"]=true'
    assert text.count(old)==1
    extra='["samples"]=n.Value,["files"]=8,["DYN_actual_core"]=true, ["dynamic_curve"]=ph.dynamics, ["dynamic_start_tick"]=ph.position-ph.leading, ["dynamic_end_ms"]=ph.dynamics==null ? new double[0] : Enumerable.Range(0,ph.dynamics.Length).Select(i=>ph.timeAxis.TickPosToMsPos(ph.position-ph.leading+5*(i+1))).ToArray()'
    (build/'NativeBatch.cs').write_text(text.replace(old,extra),encoding='utf-8')
    save(run/'dynamics-preparation.json',dict(build=build.relative_to(ROOT).as_posix(),
        base_sources=[dict(path=x.relative_to(ROOT).as_posix(),sha256=sha(x)) for x in source.iterdir() if x.is_file()],
        generator=dict(path=(HERE/'prepare_stage_2e_dynamics.py').relative_to(ROOT).as_posix(),sha256=sha(HERE/'prepare_stage_2e_dynamics.py')),
        generated_sources=[dict(path=x.relative_to(ROOT).as_posix(),sha256=sha(x)) for x in build.iterdir()]))

if __name__=='__main__':main()
