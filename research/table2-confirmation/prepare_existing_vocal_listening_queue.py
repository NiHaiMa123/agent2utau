"""Bind the remaining already-generated vocal comparisons; never make audio."""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

from record_stage_2e_word225_feedback import ROOT, HERE, OUT, ENTRIES, EXPERIMENT, ref, save, check_refs

RUN = ROOT / 'runs/research/table2-existing-listening-queue-20261011'
NAME = 'table2-existing-listening-queue-20261011'
PREVIOUS = ROOT / 'runs/research/table2-exposure-coverage-20261011'
USER_TEXT = '那先把不需要新生成歌曲的试听循环完成了，做完后再接着一首一首更新'


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def main():
    outputs = [OUT / (NAME + suffix) for suffix in ('.json', '.md', '-audit.json')]
    assert not RUN.exists() and not any(p.exists() for p in outputs)
    previous_seal_path = PREVIOUS / 'completion-manifest.json'
    previous_seal = load(previous_seal_path)
    check_refs(previous_seal['files'] + previous_seal['documents'] + previous_seal['entries'])
    sampling_path = ROOT / 'runs/research/table2-sampling-review-20261011/sampling-review.json'
    sampling = load(sampling_path)
    check_refs(sampling['source_seals'])
    seals = [load(ROOT / row['path']) for row in sampling['source_seals']]
    immutable = [r for s in seals for r in s['files'] + s['documents']]
    immutable += previous_seal['files'] + previous_seal['documents'] + [ref(previous_seal_path)]
    exposure = load(PREVIOUS / 'exposure-coverage.json')
    sampling_seal = load(ROOT / exposure['previous_seal']['path'])
    immutable += sampling_seal['files'] + sampling_seal['documents'] + [exposure['previous_seal']]
    check_refs(immutable)
    binding = load(HERE / 'stage_2e_execution_baseline_binding.json')
    assert ref(ROOT / binding['manifest'])['sha256'] == binding['sha256']
    baseline = load(ROOT / binding['manifest'])
    protection = baseline['production_skill_project_bindings'] + baseline['protected_inputs']
    check_refs(protection)
    package_path = EXPERIMENT / 'pcm-packaging.json'
    package = load(package_path)
    condition = next(c for c in package['conditions'] if c['condition_id'] == 'current-word-214')
    assert {v['code']:v['label'] for v in condition['versions']} == {'K1':'P','K2':'S','K3':'A','K4':'D'}
    first_feedback = load(ROOT / 'runs/research/table2-word214-feedback-20261011/feedback.json')
    assert first_feedback['user_message_verbatim'] == '没区别'
    selected_orders = [1, 4, 5, 8, 9]
    expected_directions = ['S-A','A-D','P-A','D-S','S-P']
    queue = []
    for index,(order,direction) in enumerate(zip(selected_orders,expected_directions),1):
        pair = next(p for p in package['pairs'] if p['condition_id']=='current-word-214' and p['order']==order)
        assert pair['direction']==direction
        meta = next(m for m in package['files'] if m['path']==pair['vocal'])
        assert meta['channels']==1 and meta['subtype']=='PCM_24'
        reverse = next(p for p in package['pairs'] if p['condition_id']=='current-word-214' and p['order']==(order+1 if order%2 else order-1))
        queue.append(dict(id=f'Q{index:02d}',condition_id='current-word-214',source_pair_order=order,
            direction=direction,codes=pair['codes'],audio=meta,reverse_audio=ref(ROOT / reverse['vocal']),
            second_start_s=pair['second_start_s'],first_vowel_approx_s=[.85,1.17],
            second_vowel_approx_s=[pair['second_start_s']+.85,pair['second_start_s']+1.17],
            auditory_feedback_status='pending',actual_playback_or_order='unknown',
            feedback_fields=['difference_or_no_difference_or_uncertain','first_or_second_more_powerful_if_any','voice_break_articulation_or_neighbor_change_if_reported'],
            new_independent_context=False))
    assert len(queue)==5 and len({frozenset(q['direction'].split('-')) for q in queue})==5
    audio_refs=[q['audio'] for q in queue]+[q['reverse_audio'] for q in queue]
    check_refs(audio_refs)
    RUN.mkdir(parents=True)
    snapshots=[]
    for name in ENTRIES + [r['path'] for r in previous_seal['documents']]:
        p=ROOT/name; dest=RUN/'before'/name
        dest.parent.mkdir(parents=True,exist_ok=True)
        with dest.open('xb') as stream: stream.write(p.read_bytes())
        assert ref(dest)['sha256']==ref(p)['sha256']
        snapshots.append(dict(**ref(p),snapshot=dest.relative_to(ROOT).as_posix()))
    save(RUN/'before/snapshot-manifest.json',dict(files=snapshots))
    record=dict(status='existing_audio_listening_pending',date='2026-10-11',user_sequence_instruction=USER_TEXT,
        active_scope='complete the bounded existing-vocal listening cycle first, then prepare one-song-at-a-time updates',
        queue=queue,queue_pairs=5,selected_presentations=5,reverse_order_optional=True,
        source_condition_historical_feedback=ref(ROOT/'runs/research/table2-word214-feedback-20261011/feedback.json'),
        source_historical_no_difference_preserved=True,
        completed_word225_five_groups='preserve existing feedback without retest or new questions',
        historical_closed_loops=['TENC cancellation no perceived difference','same-bao aggregate no difference',
            'bao onset-C local accepted','guo SHFC rejected','six-condition BREC no difference','guo original clip partial label'],
        cancelled_scope=['remaining BGM/mix relationship listening'],
        closure_rule='record these five existing paired vocal comparisons including no difference/uncertain; consolidate current vocal-cycle evidence with explicit gaps; no escalation in dose/versions/conditions',
        unreported_fields='retain unknown, do not require exhaustive new labels, equipment details, reverse-order ratings, author comparison, all 318 words or every table entity for closure',
        ordering_after_closure='review existing songs and choose first song, baseline and music purpose; versioned generation/listening/correction/evidence feedback per song, sample relevant manifestations and protect neighbors; new song-specific scope to be concrete before execution',
        future_permission_scope='user authorizes sequencing to one-song-at-a-time updates after closure; current song/project, interventions and batch not selected; no automatic replay of sealed scripts or new rendering now',
        pending_sampling_design='earlier 24+48/384 scenario deferred, not an immediate required rendering/listening budget',
        holdout_clarification='baseline familiarity alone does not certify or disqualify every future task; audit whether relevant feedback was used to select rules and separate phrase/song groups for the intended inference',
        package=ref(package_path),previous_seal=ref(previous_seal_path),source_seals=sampling['source_seals'],
        generator=ref(Path(__file__).resolve()),new_audio_or_derivative_files=0,new_waveforms=0,new_model_calls=0,
        audio_or_array_decodes=0,new_feedback=0,loop_complete=False,stage_2E_fully_validated=False,
        measurement_validated=False,general_rule_validated=False,song_or_skill_changed=False,single_agent=True,CI_manual_only=True)
    save(outputs[0],record);save(RUN/'queue.json',record)
    report=f'''# 既有人声试听循环：剩余清单与后续顺序

2026-10-11。existing_audio_listening_pending；循环尚未完成，等待五组已有对照反馈。

用户指令：**{USER_TEXT}**。据此先收口既有试听，再逐首推进制作与证据回填；不把跨条件新批次或补齐所有表格条目作为当前先决条件。

## 已完成、取消和保留

- 抱225：四版K3偏好及五组人声主对照均有原反馈；不重复试听，不补造新细项。力量感S>D>A及S>P>A保留，D/P相对未知。
- 只214：四版“没区别”已绑定，保持本剂量/条件的限定阴性。仍缺五组成对对照分别反馈，本清单只使用原已封存人声文件，不加剂量、条件或版本。
- 旧TENC、抱同字/进入C、果SHFC与同字定位、六条件BREC等已有原反馈，按原范围归档；不为了补字段重开失败实验。
- 后续混音/BGM关系试听由用户取消；取消不等于未听音频通过。
- 未报自然度/细分电平、设备、反向顺序、方法性能、泛化等保持unknown；不以补齐它们无限延长本轮。

## 剩余五组只214人声

每个文件为第一段、0.6秒间隔、第二段，第二段约7.50秒开始。目标“只”的元音第一段约0.85–1.17秒，第二段约8.35–8.67秒。预定焦点起点早于已有波形起点，原文件按协议保留整句；不补零、不重裁。

请分别记录有无区别；如有，哪段更有力量；破音、咬字或邻字变化若听到再记录。无区别/不确定都是有效结果。可分次听，也可一次回报五组；不要求每组后重新批准下一组。

'''
    for q in queue:
        absolute=(ROOT/q['audio']['path']).as_posix()
        report+=f"### {q['id']}：{'→'.join(q['codes'])}\n\n![{q['id']} 只人声]({absolute})\n\n"
    report+='''## 收口与逐首推进

五组反馈绑定后，整理已有路径响应、反例/副作用及缺口，可将当前有限人声试听循环标为closed_with_explicit_gaps。并非表1/表2全部确认或2E完整测量通过，未听仍未知。

之后先明确第一首的基线与音乐目的，逐首采用“整曲/完整乐句生成→定位表现→有限纠错→前后版本与邻字复查→表1例证/表2条件响应回填”。本次确认的是先后顺序，尚未选择歌曲、剂量或新批次；不改旧歌曲、发布工程、Skill，不重跑封存脚本。此前72条件/384波形只是待审成本情景，暂不进入执行。

留出需按将要验证的规则与相关反馈使用历史判定；单纯听过基线并不使所有后续任务都失去验证价值，也不能把缺标签直接当干净留出。旧曝光审计保持历史角色，新任务分组另冻结。
'''
    report+=f'\n[机器清单]({NAME}.json) · [核查]({NAME}-audit.json)。\n'
    with outputs[1].open('x',encoding='utf-8',newline='\n') as stream: stream.write(report)
    current=('当前执行顺序existing_audio_listening_pending：用户指定先完成无需新生成歌曲的既有试听循环，再逐首更新。'
        '抱五组成对人声已有反馈不重听；只四版“没区别”保持，剩余五组已封存人声对照本轮集中交付待反馈。'
        '旧TENC/果SHFC/BREC及同字定位按原反馈收口，不重开失败或追加剂量；BGM/混音复核仍取消。'
        '五组反馈后整理有限证据与unknown、收口本循环，再明确第一首基线/目的/版本纠错与表1表2回填范围。'
        '新跨条件72/384草案暂不执行，不以全字段补齐或反向复听作门槛；当前新音频/波形/模型/反馈0，循环仍pending。'
        'measurement_validated仍false，通用规律0；本轮不改歌曲/既有音频/Skill，单Agent、CI仅手动。')
    for name in ENTRIES:
        path=ROOT/name;text=path.read_text(encoding='utf-8')
        old=next(line for line in text.splitlines() if '当前2F准备状态exposure_and_coverage_audited_with_sampling_gaps：' in line)
        link=Path(os.path.relpath(outputs[1],path.parent)).as_posix()
        text=text.replace(old,('- ' if old.startswith('- ') else '')+current+f' 见[既有试听剩余清单]({link})。',1)
        if name=='plan.md':
            old_next=next(line for line in text.splitlines() if line.startswith('下一工作为2F协议前置冻结：'))
            text=text.replace(old_next,'下一工作按用户顺序先收口既有人声试听：只214五组成对对照集中交付，接收有区别/无区别/不确定及自发细项，绑定原波形SHA并整理有限结论。抱与旧阴性不重复，BGM复核取消；未报字段仍unknown，不要求全表格或新留出批次先完成。循环收口后再确定第一首基线、音乐目的与版本纠错/证据回填范围，逐首推进；当前没有新生成或歌曲/Skill改动。',1)
        if name=='README.md':
            text=text.replace('当前准备2F跨条件采样/留出设计，BGM复核停止','当前先收口既有人声试听循环，再逐首更新与证据回填，BGM复核停止')
        if name=='plan-table2.md':
            text=text.replace('| 2F／P1 | 当前先准备跨条件总体、曝光审计、覆盖与乐句/歌曲分组留出，建立终点/样本量依据后按明确范围批量验证 |',
                '| 2F／P1 | 用户最新顺序：先收口既有人声试听循环，再逐首制作/纠错收集条件证据；跨条件总体/留出准备保留，另按任务冻结执行 |')
        path.write_text(text,encoding='utf-8',newline='\n')
    save(outputs[2],dict(status='checking'))
    gate=subprocess.run([sys.executable,str(ROOT/'tools/repository/check_repository.py'),'--worktree'],cwd=ROOT,
        capture_output=True,text=True,encoding='utf-8')
    (RUN/'worktree-gate.txt').write_text(gate.stdout+gate.stderr,encoding='utf-8')
    assert gate.returncode==0,gate.stdout+gate.stderr
    check_refs(immutable+protection+audio_refs)
    for r in snapshots: assert ref(ROOT/r['snapshot'])['sha256']==r['sha256']
    assert load(outputs[0])['queue']==queue
    checked=0
    for p in [ROOT/n for n in ENTRIES]+[outputs[1]]:
        for target in re.findall(r'\]\(([^\s)]+)\)',p.read_text(encoding='utf-8')):
            if '://' in target or target.startswith('#'): continue
            assert (p.parent/target.split('#')[0]).exists(),(p,target)
            checked+=1
    ci=(ROOT/'.github/workflows/ci.yml').read_text(encoding='utf-8')
    assert re.search(r'^on:\s*\n  workflow_dispatch:',ci,re.MULTILINE)
    assert not re.search(r'^  (push|pull_request|schedule):',ci,re.MULTILINE)
    audit=dict(status='passed_existing_audio_queue_feedback_pending',selected_pairs=5,source_audio_SHA_checked=len(audio_refs),
        preserved_bindings=len(immutable),protected_bindings=len(protection),snapshots=len(snapshots),markdown_links_checked=checked,
        artifacts=[ref(p) for p in outputs[:2]],entries=[ref(ROOT/n) for n in ENTRIES],worktree_gate=json.loads(gate.stdout),
        new_audio_files=0,new_waveforms=0,new_model_calls=0,new_feedback=0,loop_complete=False,generator=ref(Path(__file__).resolve()))
    outputs[2].write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    save(RUN/'audit.json',audit)
    save(RUN/'completion-manifest.json',dict(status=audit['status'],
        files=[ref(p) for p in sorted(RUN.rglob('*')) if p.is_file()],documents=[ref(p) for p in outputs],entries=audit['entries']))
    print(json.dumps(dict(status=audit['status'],queue_pairs=5,new_audio=0,new_feedback=0,worktree_gate=audit['worktree_gate']),ensure_ascii=False))


if __name__=='__main__':
    main()
