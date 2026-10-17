"""Explicit synthetic capability probe; never a song generator or listening test."""
import argparse
from pathlib import Path

import numpy as np
import soundfile as sf

from agent2utau.evaluation.execution_review import build_inventory, digest, read, ref, write
from agent2utau.knowledge import CATALOGUE, collect_context
from agent2utau.openutau.bridge import run_bridge
from agent2utau.openutau.build import build_project
from agent2utau.openutau.ustx import load_ustx, sha256
from agent2utau.resources.config import load_config
from agent2utau.workflow import compile_functions, design_math


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True)
    args=p.parse_args();out=args.out.resolve();out.mkdir(parents=True,exist_ok=False);cfg=load_config()
    spec=dict(kind='synthetic capability, not a song or source performance',
              intent=['slow center without periodic motion','asymmetric signed finite return','unequal landmarks and overshoot'],
              listening='unknown',parameter_origin='Explicit synthetic probe, never a production recipe')
    write(out/'spec.json',spec)
    score=build_project('Synthetic native capability', [dict(start_sec=1.,notes=[
        dict(start=1.,dur=1.2,tone=60,lyric='a'),
        dict(start=2.2,dur=1.2,tone=60,lyric='ma'),
        dict(start=3.4,dur=1.4,tone=60,lyric='la')])],out/'score.ustx')
    sf.write(out/'synthetic-source.wav',np.zeros(44100),44100)
    for cmd,name in [('export-pitch','pitch'),('export-phonemes','phones')]:
        receipt=run_bridge(cfg,[cmd,'--project',str(score),'--out',str(out/(name+'.json'))]);write(out/(name+'-receipt.json'),receipt)
        if not receipt.get('ok'):raise RuntimeError('Native synthetic export failed')
    ou=Path(cfg['openutau_dir']);singer=load_ustx(score)['tracks'][0]['singer']
    write(out/'provenance.json',dict(schema_version=1,project_sha256=sha256(score),pitch_sha256=sha256(out/'pitch.json'),phonemes_sha256=sha256(out/'phones.json'),environment=dict(core_sha256=sha256(ou/'OpenUtau.Core.dll'),bridge_sha256=sha256(ou/'a2u-bridge.exe'),singer_id=singer,singer_config_sha256=sha256(ou/'Singers'/singer/'dsconfig.yaml'))))
    write(out/'sources.json',dict(schema_version=1,sources=[dict(id='synthetic-condition',role='source_observation',file=ref(out/'spec.json'),description='Frozen synthetic test intent; no human audio truth'),dict(id='probe-code',role='implementation',file=ref(__file__),description='Actual new synthetic probe implementation')]))
    inv=build_inventory(score,out/'raw-inventory.json',out/'pitch.json',out/'phones.json',out/'provenance.json',sources=out/'sources.json')
    if len(inv['units'])!=3:raise ValueError('Probe clock changed; explicit design requires reassessment')
    context=[]
    for u,intent in zip(inv['units'],spec['intent']):
        context.append(dict(id=u['id'],condition=dict(status='observed',evidence_ids=['synthetic-condition'],observation='Synthetic current MIDI60 nucleus; native clock enumerated before plan',interpretation=intent,reliability='Constructed test, not inferred human singing'),stages=[dict(id=u['id']+':nucleus',kind='unsegmented_nucleus',support_s=u['support_s'],required=True)]))
    write(out/'context.json',dict(schema_version=1,units=context))
    inv=build_inventory(score,out/'inventory.json',out/'pitch.json',out/'phones.json',out/'provenance.json',context=out/'context.json',sources=out/'sources.json')
    native=read(out/'pitch.json')['phrases']
    if len(native)!=1:raise ValueError('Expected one native phrase; no fallback')
    a,b=inv['units'][0]['support_s'];c,d=inv['units'][1]['support_s'];e,f=inv['units'][2]['support_s']
    nodes=[[native[0]['times_ms'][0]/1000,6000,0],[a,6000,0],[a+.25,6012,0],[b-.12,6035,0],[b,6000,0],
           [c,6000,0],[d,6000,0],[e,6000,0],[e+.16,6040,0],[e+.40,6000,0],[e+.60,5982,0],[e+.90,6016,0],[f,6000,0],[native[0]['times_ms'][-1]/1000,6000,0]]
    # Adjacent stages can share a boundary; retain one identical node.
    native_span=[native[0]['times_ms'][0]/1000,native[0]['times_ms'][-1]/1000]
    unique={n[0]:n for n in nodes if native_span[0]<=n[0]<=native_span[1]}
    nodes=[unique[t] for t in sorted(unique)]
    comp=dict(id='signed-return',family='finite_return',support_s=[c+.15,c+.85],peak_s=c+.35,peak_c=-55.)
    support=[nodes[0][0],nodes[-1][0]]
    design=dict(schema=1,origin='agent_designed',support_s=support,center_nodes=nodes,components=[comp],
        decisions=[dict(support_s=support,condition='Explicit synthetic shape capability',choice='Three distinct declared gestures',alternative='One repeated sine',reason='The test asks for nonperiodic center and unequal finite movements',uncertainty='No auditory result',component_ids=[comp['id']])],
        expectations=[dict(support_s=support,range_c=[90,100],purpose='Synthetic helper composite capability, not musical truth')])
    # Definitions only: do not load old-song response packets in this probe.
    catalogue=read(CATALOGUE);catalogue['response_indices']=[];catalogue['response_packets']=[];write(out/'knowledge-scope.json',catalogue)
    packet=collect_context(['ACO:P1'],['PARAM:C01.01'],[],absence_reason='Synthetic function/native capability only; auditory response unknown',catalogue_path=out/'knowledge-scope.json');write(out/'knowledge.json',packet)
    plan=dict(schema_version=2,project=str(score),source_audio=str(out/'synthetic-source.wav'),input_hashes={str(score):sha256(score),str(out/'synthetic-source.wav'):sha256(out/'synthetic-source.wav')},scope='whole_song',phrases=[dict(part_index=0,position=native[0]['position'],design=design)],knowledge_context=dict(path=str(out/'knowledge.json'),sha256=sha256(out/'knowledge.json'),decisions=[dict(id=x['id'],decision='use',reason='Pitch identity and unit definitions only',condition_match='Synthetic native pitch',limitations='No dose or singing-quality conclusion') for x in packet['records']]))
    write(out/'plan.json',plan);helper=design_math();decisions=[]
    for index,u in enumerate(inv['units']):
        stage=u['stages'][0];span=u['support_s'];times=[t for t,_,_ in nodes if span[0]<=t<=span[1]]
        execution=[dict(kind='center_nodes',part_index=0,position=native[0]['position'],id='center_nodes',support_s=[max(span[0],support[0]),min(span[1],support[1])],parameters_sha256=digest(nodes))]
        if index==1:
            times=[comp['support_s'][0],comp['peak_s'],comp['support_s'][1]]
            execution.append(dict(kind='component',part_index=0,position=native[0]['position'],id=comp['id'],support_s=comp['support_s'],parameters_sha256=digest(comp)))
        decisions.append(dict(id='shape-'+str(index),unit_ids=[u['id']],stage_ids=[stage['id']],support_s=span,evidence_ids=['synthetic-condition'],observation=context[index]['condition']['observation'],interpretation=spec['intent'][index],reliability='Explicit constructed function',purpose='Native capability: '+spec['intent'][index],choice=['center','finite_return','landmarks'][index],alternative='Uniform oscillation',rejected_because='It would not preserve the requested '+spec['intent'][index],parameter_basis='New declared synthetic anchors '+str(index),execution=execution,checks=[dict(stage_id=stage['id'],kind='landmarks',support_s=span,parameters=dict(points=[[t,helper.evaluate(design,t)] for t in times],tolerance_c=3.,time_tolerance_s=.003))],uncertainty='Capability only; musical appropriateness and audio unverified'))
    write(out/'ledger.json',dict(schema_version=1,inventory=ref(out/'inventory.json'),plan=ref(out/'plan.json'),timing='forward',decisions=decisions,revisions=[]))
    write(out/'contract.json',dict(schema_version=1,inventory=ref(out/'inventory.json'),ledger=ref(out/'ledger.json'),reviews=None))
    result=compile_functions(out/'plan.json',out/'compiled',cfg,out/'contract.json')
    print({k:result[k] for k in ['status','native_max_error_c','execution_review']})


if __name__=='__main__':main()
