"""Record explicit J acceptance and authorize a separate whole-song revision."""
from pathlib import Path
import copy, csv, hashlib, json, sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'research/table2-confirmation'))
from assemble_lastpage_accepted_baseline_20261011 import ENTRIES,load,save,ref,sha,check

RUN=ROOT/'runs/production/lastpage-skill-whole-song-20261013'
PRIOR=ROOT/'runs/research/lastpage-texture-listening-preparation-20261013'
KNOW=ROOT/'docs/knowledge/acoustic-manifestations-20261009'
REPORT=ROOT/'docs/reports/lastpage'
J=ROOT/'runs/experiments/lastpage-own-li-entry-pitch-20261013'
SKILL=ROOT/'skills/singing-expression-editor'
INSTALLED=Path('C:/Users/Administrator/.codex/skills/singing-expression-editor')
NAME='own-J-acceptance-and-whole-song-authorization-20261013'
INDEX='table2-J-accepted-index-20261013'

def main():
    assert not RUN.exists()
    seal=load(PRIOR/'completion-manifest.json');check(seal['files']+seal['documents']+seal['entries'])
    original=load(PRIOR/'protected-before.json')+seal['files']+seal['documents']+[ref(PRIOR/'completion-manifest.json')]
    check(original)
    RUN.mkdir(parents=True)
    mutable=['docs/knowledge/acoustic-manifestations-20261009/active-knowledge-sources.json','skills/singing-expression-editor/SKILL.md']
    save(RUN/'protected-before.json',[r for r in original if r['path'] not in mutable])
    snapshots=[]
    for name in ENTRIES+mutable:
        p=RUN/'before'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((ROOT/name).read_bytes())
        snapshots.append(dict(original=ref(ROOT/name),snapshot=ref(p)))
    for source in [SKILL,INSTALLED]:
        target=RUN/'before'/('repository-skill' if source==SKILL else 'installed-skill')
        files=[]
        for p in sorted(source.rglob('*')):
            if p.is_file() and '__pycache__' not in p.parts:
                q=target/p.relative_to(source);q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(p.read_bytes())
                files.append(dict(original_path=str(p),sha256=sha(p),snapshot=ref(q)))
        snapshots.append(dict(skill_root=str(source),files=files))
    save(RUN/'before/snapshot-manifest.json',snapshots)
    outputs=load(J/'evaluation/delivery-check.json')['outputs'];check(list(outputs.values()))
    feedback=dict(date='2026-10-13',verbatim='这个可以了，记录下来。更新skill后运用到整曲',
        clarification_question='“这个可以了”具体指哪版？整曲我先按我们的 J 的实感方向作为参考，同时保留你说的局部虚、其他偏实和白烁质感要求。',
        clarification_verbatim='我们的 J 可以了',referent='J explicitly selected by user',
        accepted_media=outputs['candidate_preview'],accepted_project=outputs['candidate_project'],
        acceptance_scope='J two-phrase preview; accepted as reference for a new whole-song application',
        prior_correction=ref(REPORT/'li-texture-listening-20261013.json'),
        prior_qualitative_observations_retained=True,transition_issue='withdrawn; no connection repair',
        author_A_C_texture_comparison_verdict='unknown: this reply selects J, not an A/C ranking',
        full_song_accepted=False,individual_pitch_force_break_texture_dimensions='not separately rated',
        skill_update_authorized=True,whole_song_new_project_and_audio_authorized=True,
        old_originals_and_runs_immutable=True,single_agent=True,automatic_CI=False,agent_heard=False,
        measurement_validated=False,general_rule_validated=False)
    save(RUN/'feedback/J-acceptance.json',feedback)
    supplement=dict(record_id='RESP:LASTPAGE-OWN-LI-ENTRY-PITCH-01',append_only_feedback=True,latest_acceptance=feedback,
        local_adoption=True,whole_song_adoption=False,measurement_validated=False,general_rule_validated=False)
    save(REPORT/(NAME+'.json'),dict(status='J_local_accepted_whole_song_update_authorized',table2_supplement=supplement))
    (REPORT/(NAME+'.md')).write_text('''# J局部接受与整曲更新授权

2026-10-13，用户：“这个可以了，记录下来。更新skill后运用到整曲”。经版本澄清明确：“我们的 J 可以了”。

接受范围为已交付J两句试听（音频和工程SHA见同名JSON），作为新整曲版本的方向依据。此前体略虚、其它偏实、缺白烁磨砂填充的描述保留为细化线索；衔接问题已撤回。该接受不补造逐字、破音、渐强渐弱或作者A/C质感相等的细分结论，也不是旧整曲验收。Agent未听，通用规律和measurement_validated不升级。

本条明确授权更新Skill并应用整曲，覆盖先前当前任务“不改Skill/歌曲/音频”的范围限制。保留旧工程、音频、封存run和作者原件，另做整曲新版本；单Agent，CI仅手动。Skill只写可复用判断和核查方法，不保存本曲固定声线、时码或剂量为默认配方。
''',encoding='utf8')
    idx=copy.deepcopy(load(KNOW/'table2-texture-listening-index-20261013.json'))
    row=next(r for r in idx['rows'] if r['id']==supplement['record_id'])
    row.setdefault('feedback_sources',[]).append(ref(REPORT/(NAME+'.json')))
    row['latest_acceptance_record']=feedback
    row['effective_feedback_interpretation'].update(local_J_accepted=True,accepted_referent='explicit J',whole_song_accepted=False,
        prior_qualitative_observations='retained; no new per-axis ranking',transition_issue='withdrawn by user')
    idx.update(status='J_local_accepted_pending_new_whole_song_application',generator=ref(Path(__file__)),
        prior_index=ref(KNOW/'table2-texture-listening-index-20261013.json'))
    save(KNOW/(INDEX+'.json'),idx)
    rows=[dict(id=r['id'],kind=r.get('kind','response'),local_J_accepted=r['id']==supplement['record_id'],
        source_path=r['source']['path'],source_sha256=r['source']['sha256'],measurement_validated=False) for r in idx['rows']]
    with (KNOW/(INDEX+'.csv')).open('x',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    (KNOW/(INDEX+'.md')).write_text('# J接受反馈索引\n\n保留37行及12近期系列，追加J明确局部接受与整曲授权；旧技术、反馈原文、更正及阴性保持。逐项数据见同名JSON/CSV。整曲新试听尚未执行。\n',encoding='utf8')
    registry=load(KNOW/'active-knowledge-sources.json');registry['response_indices']=[(KNOW/(INDEX+'.json')).relative_to(ROOT).as_posix()]
    (KNOW/'active-knowledge-sources.json').write_text(json.dumps(registry,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('J acceptance appended; previous evidence snapshotted; new whole-song revision authorized.',flush=True)

if __name__=='__main__':main()
