"""Record one aggregate no-difference reply and close the finite vocal loop."""
import csv
import io
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from record_stage_2e_word225_feedback import ROOT, HERE, OUT, ENTRIES, ref, save, check_refs

RUN = ROOT / 'runs/research/table2-listening-cycle-closure-20261011'
PRIOR = ROOT / 'runs/research/table2-existing-listening-queue-20261011'
NAME = 'table2-listening-cycle-closure-20261011'


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def main():
    outputs = [OUT / (NAME + s) for s in ('.json','.md','-comparisons.csv','-audit.json')]
    assert not RUN.exists() and not any(p.exists() for p in outputs)
    prior_seal_path = PRIOR / 'completion-manifest.json'
    prior_seal = load(prior_seal_path)
    check_refs(prior_seal['files'] + prior_seal['documents'] + prior_seal['entries'])
    queue = load(PRIOR / 'queue.json')
    seal_refs = queue['source_seals'] + [queue['previous_seal'],ref(prior_seal_path)]
    exposure = load(ROOT / 'runs/research/table2-exposure-coverage-20261011/exposure-coverage.json')
    seal_refs += [exposure['previous_seal']]
    check_refs(seal_refs)
    seals = [load(ROOT / r['path']) for r in seal_refs]
    immutable = [r for s in seals for r in s['files'] + s['documents']]
    check_refs(immutable)
    binding = load(HERE / 'stage_2e_execution_baseline_binding.json')
    assert ref(ROOT / binding['manifest'])['sha256'] == binding['sha256']
    baseline = load(ROOT / binding['manifest'])
    protection = baseline['production_skill_project_bindings'] + baseline['protected_inputs']
    check_refs(protection)
    assert len(queue['queue']) == 5
    assert [q['source_pair_order'] for q in queue['queue']] == [1,4,5,8,9]
    assert [q['direction'] for q in queue['queue']] == ['S-A','A-D','P-A','D-S','S-P']
    presented = [q['audio'] for q in queue['queue']]
    check_refs(presented)
    original_only = ROOT / 'runs/research/table2-word214-feedback-20261011/feedback.json'
    assert load(original_only)['user_message_verbatim'] == '没区别'
    protocol_path = OUT / 'validation-protocols/shfc-path-separation-v1.json'
    protocol = load(protocol_path)
    assert protocol['id'] == 'T2D-SHFC-PATHS-01'
    atom_path = OUT / 'atomic-manifestations.csv'
    with atom_path.open(encoding='utf-8-sig',newline='') as stream:
        atoms = {r['id']:r for r in csv.DictReader(stream)}
    assert atoms['PER:S1']['name']=='支撑/实的听感' and atoms['PER:X1']['name']=='破音/失真听感'
    rows=[]
    source_names=['sa','da','pa','sd','sp']
    canonical=['S-A','D-A','P-A','S-D','S-P']
    findings=['S more powerful; A softer','D more powerful than A','P more powerful than A',
        'S more powerful than D','S more powerful than P']
    feedback_refs=[]
    for suffix,direction,finding in zip(source_names,canonical,findings):
        source = ROOT / f'runs/research/table2-word225-{suffix}-feedback-20261011/feedback.json'
        feedback=load(source);feedback_refs.append(ref(source))
        rows.append(dict(comparison_id='VOCAL-CYCLE:word225:'+direction,condition_id='current-word-225',
            canonical_direction=direction,presented_direction='see_bound_original_feedback',
            finding=finding,feedback_verbatim=feedback['user_message_verbatim'],feedback_group_id='historical:'+suffix,
            feedback_source=ref(source)['path'],feedback_source_sha256=ref(source)['sha256'],
            shared_feedback=False,break_or_artifact='original_reported_no_break_scope_preserved',
            other_specific_side_effects='unknown_unless_original_feedback',
            table1_power_relation='PER:S1 descriptive candidate; perceived power not equal physiological support',
            main_parameter='PARAM:C14.01',measurement_validated=False,general_rule_validated=False))
    for q,direction in zip(queue['queue'],canonical):
        rows.append(dict(comparison_id='VOCAL-CYCLE:word214:'+direction,condition_id='current-word-214',
            canonical_direction=direction,presented_direction=q['direction'],finding='no_perceived_difference_reported',
            feedback_verbatim='没区别',feedback_group_id='FB:word214-five-pairs-20261011',
            feedback_source=(RUN/'feedback.json').relative_to(ROOT).as_posix(),feedback_source_sha256='bound_after_record_creation',
            shared_feedback=True,break_or_artifact='unknown_no_separate_label',other_specific_side_effects='unknown_no_separate_label',
            table1_power_relation='no perceptible difference in this presentation; no normality or equivalence claim',
            main_parameter='PARAM:C14.01',measurement_validated=False,general_rule_validated=False))
    # Accepted complete C is the original A for the rejected guo intervention.
    working_project = ROOT / 'runs/lastpage_guo_register_probe_20261008/A.ustx'
    published_project = ROOT / 'projects/latest/lastpage_loudness_v02.ustx'
    onset_project = ROOT / 'runs/lastpage_shfc_onset_probe_20261008/C.ustx'
    assert ref(working_project)['sha256'] == ref(onset_project)['sha256'] == '45d2b34e8086ad5f12f4c701d91672b3cc12eadffda2ab9d9e405dfb2fb71816'
    assert ref(published_project)['sha256']=='a17d4bebdd3c5951f2b10138777a8fee8925ab5beb6bb70705342d1b6ba466af'
    guo_manifest_path = ROOT / 'runs/lastpage_guo_register_probe_20261008/completion_manifest.json'
    guo_manifest = load(guo_manifest_path)
    assert guo_manifest['files'][str(working_project)]==ref(working_project)['sha256']
    study_path = ROOT / 'runs/lastpage_cross_condition_study_20261008/study.json'
    study_manifest=load(study_path.parent/'completion_manifest.json')
    assert ref(study_path)['sha256']==study_manifest['files_sha256']['study.json']
    study=load(study_path)
    geometry_path = ROOT / 'runs/lastpage_loudness_skill_v02_20261007/native_word_geometry.json'
    assert ref(geometry_path)['sha256']==study['bindings'][str(geometry_path)]
    assert len(study['all_current_words'])==318
    first_song=dict(song='最后一页',status='baseline_identity_bound_preparation_only',
        selection_reason='current complete material and native clock inventory available, accepted bao protection and negative examples already bound',
        working_baseline_project=ref(working_project),same_accepted_C_project=ref(onset_project),published_baseline=ref(published_project),
        baseline_manifest=ref(guo_manifest_path),native_word_geometry=ref(geometry_path),metadata_inventory=ref(study_path),
        words=318,phrase_groups=34,baseline_labels='old 5 original positions/313 unknown remain as at original study; accepted C and newer comparisons separate',
        purpose='whole-song vocal articulation and continuity; collect manifestations and protect accepted/usable contexts, rather than chase one syllable or maximize power',
        protection=['accepted word225 bao C retained as baseline','word247 local usable retained within original scope',
            'word124/214 reported solid not whole-song normality','guo SHFC/BREC dose escalation stopped','source unknown preserved'],
        next_action='read current singing-expression-editor Skill and workflow; audit full-song baseline/observations/explicit function decisions and coverage; write first version purposes and controlled changes in root plan before compilation',
        evidence_collection='bind full-song/phrase/word identity, all changed inputs, pre/post versions, actual technical reconstruction, user labels and neighbors; multi-control corrections recorded as joint intervention',
        plan_entry='plan.md',new_plan_file_created=False,new_project_written=False,new_rendering_executed=False,
        no_old_script_replay=True,Skill_update_authorized=False,BGM_research=False)
    additional_refs=[ref(protocol_path),ref(atom_path),ref(working_project),ref(onset_project),ref(published_project),
        ref(guo_manifest_path),ref(study_path),ref(geometry_path)]+feedback_refs
    RUN.mkdir(parents=True)
    snapshots=[]
    for name in ENTRIES+[r['path'] for r in prior_seal['documents']]:
        path=ROOT/name;dest=RUN/'before'/name
        dest.parent.mkdir(parents=True,exist_ok=True)
        with dest.open('xb') as stream: stream.write(path.read_bytes())
        assert ref(path)['sha256']==ref(dest)['sha256']
        snapshots.append(dict(**ref(path),snapshot=dest.relative_to(ROOT).as_posix()))
    save(RUN/'before/snapshot-manifest.json',dict(files=snapshots))
    feedback=dict(schema_version=1,status='aggregate_no_difference_feedback_recorded',condition_id='current-word-214',
        user_message_verbatim='没区别',context_interpretation='one aggregate reply to the five just-presented vocal pairs; preceding instruction explicitly allowed one aggregate reply',
        presented_queue=ref(PRIOR/'queue.json'),presented_audio=presented,
        group_id='FB:word214-five-pairs-20261011',comparison_ids=[r['comparison_id'] for r in rows[5:]],
        source_pair_orders=[1,4,5,8,9],response_count=1,comparisons_linked=5,cumulative_this_batch_responses=10,
        actual_playback_each_file='unknown',individual_order_ratings='not_separately_reported',
        no_difference_scope='current condition, fixed dose/time shape and presentations only; not equivalence, exact waveform equality or engine-wide ineffectiveness',
        break_articulation_level_neighbor_naturalness='unknown_not_separately_reported',
        prior_four_version_reply_preserved=ref(original_only),user_message_timestamp='unknown',
        record_created_utc=datetime.now(timezone.utc).isoformat(),device_and_volume='unknown',
        new_waveforms=0,new_model_calls=0,agent_heard=False,measurement_validated=False,general_rule_validated=False)
    save(RUN/'feedback.json',feedback)
    for row in rows[5:]: row['feedback_source_sha256']=ref(RUN/'feedback.json')['sha256']
    record=dict(status='closed_with_explicit_gaps',date='2026-10-11',cycle_complete=True,
        original_protocol=ref(protocol_path),source_queue=ref(PRIOR/'queue.json'),source_seals=seal_refs,
        new_feedback=feedback,new_feedback_count=1,cumulative_batch_responses=10,
        compared_conditions=2,primary_vocal_groups_with_feedback=10,
        independent_contexts_not_increased=True,repeated_versions_not_counted_as_samples=True,
        word225_power_partial_order=['S>D>A','S>P>A'],word225_D_vs_P='unknown_not_added',
        word214='original_four_version_and_new_five_pair_aggregate_no_difference',
        cancelled_BGM_and_mix_listening='remaining cancelled by user; not marked passed',
        closure_scope='finite currently active existing-vocal auditory cycle; not all historical audio or all table1 entities validated',
        open_gaps=['specific unreported perceptual fields','actual order/device/session metadata','calibrated measurement performance','new heldout/cross-song evidence','whole-song acceptance'],
        table1_attachment=dict(entities=['PER:S1','PER:X1','PER:T3','PER:L1'],
            relation='local listener evidence and descriptive candidates only; power distinct from loudness, naturalness or physiology',
            definitions_and_measurement_validation_unchanged=True),
        table2_attachment=dict(comparisons=rows,source_original_14_records_unchanged=True,
            mediators_not_independently_identified=['VOIC','BREC','TENC'],new_general_rule=False),
        first_song=first_song,generator=ref(Path(__file__).resolve()),
        preparation_note='Initial read-only preflight rejected BOM-prefixed CSV header id before writing files; parser changed to utf-8-sig, original CSV bytes untouched.',
        original_stage_2E_complete=False,measurement_validated=False,general_rule_validated=False,
        new_audio_files=0,new_waveforms=0,new_model_calls=0,audio_or_array_decodes=0,
        song_or_skill_changed=False,single_agent=True,CI_manual_only=True)
    save(outputs[0],record);save(RUN/'closure.json',record)
    buffer=io.StringIO(newline='');writer=csv.DictWriter(buffer,fieldnames=list(rows[0]),lineterminator='\n')
    writer.writeheader();writer.writerows(rows)
    with outputs[2].open('x',encoding='utf-8',newline='') as stream:stream.write(buffer.getvalue())
    report='''# 既有人声试听循环收口与第一首入口

2026-10-11。closed_with_explicit_gaps：当前有限既有人声试听循环完成，测量/泛化/整曲验收缺口仍保留。

用户原话：**没区别**。紧接五组只214对照Q01–Q05及允许一次汇总回答的提示，本次作为五组汇总反馈绑定，计1条回复/5组引用，不伪造5次独立判断。实际每个文件的播放、顺序、设备及细分听感仍unknown。

## 当前结论与回填

- 抱225：保持四版K3偏好、五组局部力量感关系S>D>A及S>P>A，各自原对照的无破音反馈按来源保留；D/P相对未知，不追加对照。
- 只214：原四版“没区别”与本次五组汇总阴性并存。不加剂量、不再找差别，不推论波形相同、通道普遍无效或已经证明等价；破音/咬字/电平等未独立回报，不补为正常。
- 剩余BGM/混音由用户取消，不算通过。旧TENC、果SHFC、BREC及同字定位按原反馈归档，不重开阴性实验。
- 本批累计10条回复，10组主对照有反馈引用，但仍只有2个已见条件。现有循环收口，不宣称完整2E测量或通用规律验证通过。

新增10行版本/比较/原话/共享反馈组/来源SHA的表2补充CSV，并引用表1感知实体。力量感与PER:S1仅有描述候选关系，不能等同生理支撑或PER:L1响度。当前音频实例和听觉反馈可作局部证据；表1定义/检测器的measurement_validated不升级。原14记录、表1正式实体及旧封存报告原字节不改，新证据附加在本记录与当前索引。

## 接下来第一首：《最后一页》

优先使用现有完整材料。工作基线绑定已接受抱C的完整工程：旧果SHFC实验的A.ustx与原C.ustx SHA一致（45d2b34e…）；发布v02（a17d4beb…）另列，不将二者混为一份已发布工程。没有采用被否决的果B，也没有因只的阴性引入新SHFC。

已有318字/34乐句时钟元数据。原5位置/313 unknown是旧快照，不覆盖接受抱C、word247局部可用或本批比较反馈；比较无区别不变成绝对自然度标签。

下一步按当前Skill与workflow核查整曲观测、音素时钟、显式函数决策和实际基底，确定第一版本的音乐目的、修改与保护清单，再在新运行目录执行。以整曲发音和声线连贯性为目的，保留抱C、已有局部可用条件、果SHFC/BREC否决与unknown；逐轮保存前后版本、所有修改、邻字保护及表1例证/表2条件响应。多项共同修改如实记为联合干预，不强归因单一参数。

由根目录plan.md维护活动步骤，不另建活动计划、不重跑封存歌曲脚本。本轮仅收口及基线身份准备，新工程/音频/模型调用0，歌曲/Skill不改，单Agent、CI仅手动。之前72条件/384波形草案继续暂不执行。
'''
    report+=f'\n[反馈与收口JSON]({NAME}.json) · [表2补充比较CSV]({NAME}-comparisons.csv) · [核查]({NAME}-audit.json)。\n'
    with outputs[1].open('x',encoding='utf-8',newline='\n') as stream:stream.write(report)
    current=('当前状态closed_with_explicit_gaps：2026-10-11只214五组既有人声对照汇总回报“没区别”，'
        '计1条回复/5组绑定，原四版阴性保留；当前有限试听循环已收口。本批累计10回复/两已见条件/10组人声主对照引用，'
        '抱S>D>A及S>P>A与原无破音反馈保持，不追加对照/剂量，BGM混音取消且不标通过。'
        '新增10行表2补充证据与表1描述引用；未报细项/测量性能/泛化/整曲验收unknown，measurement_validated仍false、通用规律0。'
        '下一步逐首更新，先《最后一页》：完整工作基线为已接受抱C（旧果试验A与C SHA一致），发布v02单列，'
        '先整曲观测/时钟/显式函数与保护清单核查，再明确版本修改与证据回填；不重跑旧脚本，72/384草案暂不执行。'
        '本轮新音频/工程/模型0，原歌曲/Skill不改，单Agent、CI仅手动。')
    for name in ENTRIES:
        path=ROOT/name;text=path.read_text(encoding='utf-8')
        old=next(line for line in text.splitlines() if '当前执行顺序existing_audio_listening_pending：' in line)
        link=Path(os.path.relpath(outputs[1],path.parent)).as_posix()
        text=text.replace(old,('- ' if old.startswith('- ') else '')+current+f' 见[试听收口与第一首入口]({link})。',1)
        if name=='plan.md':
            old_next=next(line for line in text.splitlines() if line.startswith('下一工作按用户顺序先收口既有人声试听：'))
            text=text.replace(old_next,'下一工作进入逐首更新，先《最后一页》：读取当前Skill/workflow，核查含已接受抱C的完整工作基线（与旧果试验A相同）及318字/34乐句观测、原生时钟、显式函数决策和当前基底；在本计划明确第一版本音乐目的、修改/保护清单、实际重建与试听/证据回填范围，再执行新版本。已收口人声循环不重复，不采用否决果SHFC/BREC，不以力量感替代自然度或把unknown标正常；原工程/封存run保持，新版本使用新目录，不重跑旧脚本。',1)
        if name=='README.md':
            text=text.replace('当前先收口既有人声试听循环，再逐首更新与证据回填','既有人声试听循环已收口；当前先准备最后一页逐首更新与证据回填')
        if name=='plan-table2.md':
            text=text.replace('用户最新顺序：先收口既有人声试听循环，再逐首制作/纠错收集条件证据','既有人声试听循环已收口；下一步先最后一页逐首制作/纠错收集条件证据')
        path.write_text(text,encoding='utf-8',newline='\n')
    save(outputs[3],dict(status='checking'))
    result=subprocess.run([sys.executable,str(ROOT/'tools/repository/check_repository.py'),'--worktree'],cwd=ROOT,
        capture_output=True,text=True,encoding='utf-8')
    (RUN/'worktree-gate.txt').write_text(result.stdout+result.stderr,encoding='utf-8')
    assert result.returncode==0,result.stdout+result.stderr
    check_refs(immutable+protection+presented+additional_refs)
    for r in snapshots:assert ref(ROOT/r['snapshot'])['sha256']==r['sha256']
    with outputs[2].open(encoding='utf-8',newline='') as stream:parsed=list(csv.DictReader(stream))
    assert len(parsed)==10
    assert {r['feedback_group_id'] for r in parsed[5:]}=={'FB:word214-five-pairs-20261011'}
    assert all(r['feedback_verbatim']=='没区别' and r['measurement_validated']=='False' for r in parsed[5:])
    assert load(outputs[0])['new_feedback']==load(RUN/'feedback.json')
    checked=0
    for p in [ROOT/n for n in ENTRIES]+[outputs[1]]:
        for target in re.findall(r'\]\(([^\s)]+)\)',p.read_text(encoding='utf-8')):
            if '://' in target or target.startswith('#'):continue
            assert (p.parent/target.split('#')[0]).exists(),(p,target)
            checked+=1
    ci=(ROOT/'.github/workflows/ci.yml').read_text(encoding='utf-8')
    assert re.search(r'^on:\s*\n  workflow_dispatch:',ci,re.MULTILINE)
    assert not re.search(r'^  (push|pull_request|schedule):',ci,re.MULTILINE)
    audit=dict(status='passed_cycle_closed_with_explicit_gaps',new_feedback_count=1,linked_comparisons=5,
        comparison_rows=10,source_audio_SHA_checked=5,preserved_bindings=len(immutable),protected_bindings=len(protection),
        additional_source_bindings=len(additional_refs),snapshots=len(snapshots),markdown_links_checked=checked,
        artifacts=[ref(p) for p in outputs[:3]],entries=[ref(ROOT/n) for n in ENTRIES],feedback=ref(RUN/'feedback.json'),
        worktree_gate=json.loads(result.stdout),first_song_baseline_SHA_matched=True,
        new_audio=0,new_project=0,new_model_calls=0,loop_complete=True,measurement_validated=False,
        generator=ref(Path(__file__).resolve()))
    outputs[3].write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    save(RUN/'audit.json',audit)
    save(RUN/'completion-manifest.json',dict(status=audit['status'],
        files=[ref(p) for p in sorted(RUN.rglob('*')) if p.is_file()],documents=[ref(p) for p in outputs],entries=audit['entries']))
    print(json.dumps(dict(status=audit['status'],new_feedback_count=1,comparisons_linked=5,loop_complete=True,
        first_song='最后一页',new_audio=0,worktree_gate=audit['worktree_gate']),ensure_ascii=False))


if __name__=='__main__':
    main()
