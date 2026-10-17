"""Freeze independent questions before writing mappings; no audio/curve use."""
import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from frozen_inputs import refuse_after_formal_migration

import yaml
from stage_e_checklist_data import cases, WEB_SOURCES, DATE, STUDY, TENC, SHFC, ONSET, GUO, POSITIVE, BREC, PHONE

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'docs/knowledge/acoustic-manifestations-20261009'
HERE=Path(__file__).resolve().parent

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def load(path):return json.loads(path.read_text(encoding='utf-8'))

def main():
    refuse_after_formal_migration()
    ap=argparse.ArgumentParser();ap.add_argument('--run',type=Path,required=True);args=ap.parse_args()
    run=args.run.resolve();assert run.is_relative_to(ROOT/'runs/research')
    target=OUT/'coverage-checklist.json'
    assert not target.exists(), 'Already frozen; do not overwrite or revise the denominator after mapping'
    assert not (OUT/'description-coverage.json').exists(), 'Freeze must precede mapping'
    (run/'observations').mkdir(parents=True,exist_ok=True);(run/'logs').mkdir(exist_ok=True)
    manifest=load(ROOT/'research/baishuo/manifest.json')
    structures=[]
    inputs=[ROOT/p for p in [STUDY,TENC,SHFC,ONSET,GUO,POSITIVE,BREC,PHONE,
        'research/baishuo/manifest.json','docs/knowledge/acoustic-manifestations-20261009/conditional-responses.json']]
    for key,r in manifest['resources'].items():
        p=ROOT/'research/baishuo'/r['file'];assert sha(p)==r['sha256'];inputs.append(p)
        j=yaml.safe_load(p.read_text(encoding='utf-8-sig'))
        notes=[n for part in j.get('voice_parts',[]) for n in part.get('notes',[])]
        singing=[n for n in notes if n.get('lyric') not in {'AP','SP','+','-'}]
        continuations=[dict(index=i,position=n['position'],duration=n['duration'],tone=n['tone'],lyric=n['lyric'])
            for i,n in enumerate(notes) if n.get('lyric')=='+'][:2]
        de=[dict(index=i,position=n['position'],duration=n['duration'],tone=n['tone'],lyric=n['lyric'])
            for i,n in enumerate(notes) if n.get('lyric')=='de'][:3]
        gaps=[]
        # Per-part sequence only. A new part is not a gap between two notes.
        for pi,part in enumerate(j.get('voice_parts',[])):
            ns=part.get('notes',[])
            for i,(a,b) in enumerate(zip(ns,ns[1:])):
                delta=b['position']-a['position']-a['duration']
                if delta>0 and len(gaps)<3:gaps.append(dict(part=pi,index=i,gap_ticks=delta))
        structures.append(dict(project=key,path=p.relative_to(ROOT).as_posix(),sha256=sha(p),
            note_count=len(notes),voice_part_count=len(j.get('voice_parts',[])),tempos=j.get('tempos'),
            continuation_examples=continuations,repeated_de_examples=de,gap_examples=gaps,
            AP_count=sum(n.get('lyric')=='AP' for n in notes),SP_count=sum(n.get('lyric')=='SP' for n in notes),
            all_note_tone_range=[min(n['tone'] for n in notes),max(n['tone'] for n in notes)],
            lyric_note_tone_range=[min(n['tone'] for n in singing),max(n['tone'] for n in singing)],
            curve_arrays_exported_or_reused=False,auditory_label='unknown'))
    assert next(r for r in structures if r['project']=='huahai')['continuation_examples'][0]['index']==21
    assert len(next(r for r in structures if r['project']=='yuai')['repeated_de_examples'])==3
    # Preserve the plan that supplied task scope, since its progress is mutable.
    plan_copy=run/'observations/plan-at-freeze.md';assert not plan_copy.exists()
    plan_copy.write_bytes((ROOT/'plan.md').read_bytes());inputs.append(plan_copy)
    rows=cases()
    payload=dict(schema_version=1,date=DATE,stage='E',status='checklist_frozen_before_mapping',
        case_count=42,main_count=36,deferred_recheck_count=6,rows=rows,
        counts_by_origin=dict(Counter(r['origin'] for r in rows)),sources=WEB_SOURCES,
        input_bindings=[dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p)) for p in inputs],
        author_structures=structures,
        independence_scope='Question selection from user evidence, original studies, music-task requirements and author structures; no enumeration of the 31 descriptors, no B hypothetical counterexamples',
        recheck_scope='Deferred mapping process check only. Agent already saw A–D; no statistical blindness, unseen-audio holdout or generalization validation',
        sampling_limit='Purposive finite checklist, not all singing phenomena. U18 aggregates313 unknown words into1 case; 6BREC rows share1 utterance; repeated papers do not create independent experiments',
        table2_text_quality='Some existing conditional-responses.json prose is mojibake; retained unchanged. Feedback wording comes from bound readable reports, numeric identities/record IDs and stored hashes only from JSON. F must expose this gap before formal consolidation.',
        no_new_audio_or_synthesis=True,no_new_auditory_labels=True,formal_ids_migrated=False)
    text=json.dumps(payload,ensure_ascii=False,indent=2)+'\n'
    target.write_text(text,encoding='utf-8')
    checkpoint=run/'observations/coverage-checklist-frozen.json';assert not checkpoint.exists();checkpoint.write_text(text,encoding='utf-8')
    proof=dict(path=target.relative_to(ROOT).as_posix(),sha256=sha(target),checkpoint_path=checkpoint.relative_to(ROOT).as_posix(),
        checkpoint_sha256=sha(checkpoint),case_count=42,main_count=36,deferred_recheck_count=6,
        frozen_before_mapping=True,definition_baseline=dict(path=(OUT/'measurement-protocols.json').relative_to(ROOT).as_posix(),sha256=sha(OUT/'measurement-protocols.json')),
        checklist_authoring_source=dict(path=(HERE/'stage_e_checklist_data.py').relative_to(ROOT).as_posix(),sha256=sha(HERE/'stage_e_checklist_data.py')))
    (HERE/'stage_e_freeze_binding.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(status=payload['status'],cases=42,main=36,recheck=6,sha256=proof['sha256'])))

if __name__=='__main__':main()
