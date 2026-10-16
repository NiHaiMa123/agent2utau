"""Append one rejection feedback and review existing joint conditions read-only.

No audio/NPZ decoding, native/model execution, new control design or Skill edits.
"""
import csv
import json
from pathlib import Path
import subprocess
import sys

from assemble_lastpage_accepted_baseline_20261011 import ROOT, ENTRIES, load, save, ref, check

PRIOR=ROOT/'runs/experiments/lastpage-conditioned-voicing-20261011'
RUN=ROOT/'runs/research/lastpage-conditioned-voicing-feedback-20261011'
REPORT=ROOT/'docs/reports/lastpage'
NAME='conditioned-voicing-feedback-20261011'


def main():
    assert not RUN.exists() and not (REPORT/(NAME+'.json')).exists()
    sealed=load(PRIOR/'completion-manifest.json')
    check(sealed['files']+sealed['documents']+sealed['entries'])
    protected=load(PRIOR/'protected-before.json')+sealed['files']+sealed['documents']
    check(protected)
    RUN.mkdir(parents=True)
    for name in ENTRIES:
        p=RUN/'before'/name;p.parent.mkdir(parents=True,exist_ok=True)
        p.write_bytes((ROOT/name).read_bytes())
    save(RUN/'protected-before.json',protected)
    probe=load(REPORT/'conditioned-voicing-probe-20261011.json')
    media=probe['delivery']['outputs']
    feedback=dict(original_text='还是不行',reply_count=1,
        response_record='RESP:LASTPAGE-CONDITIONED-VOIC-01',comparison='B-A',
        candidate=media['candidate_preview'],original_A=media['original_preview'],author_reference=media['author_reference'],
        result='candidate not accepted; target not met',
        scope='one aggregate reply after displayed two-phrase comparison; full carrier audition unknown',
        perceptible_difference='unknown: no explicit no-difference statement',
        solidity_detail='no more specific wording in this reply',
        break_articulation_loudness_deterioration='unknown; do not inherit prior speaker no-deterioration reply',
        labels_added_per_word=0,adoption=False,agent_heard=False)
    check([feedback[k] for k in ['candidate','original_A','author_reference']])
    save(RUN/'feedback/feedback.json',feedback)
    paths=[ROOT/'runs/lastpage_loudness_skill_v02_20261007'/n for n in ['agent_word_decisions.json','native_word_geometry.json']]
    paths.extend([REPORT/'li-kan-author-reference-20261011.json',REPORT/'voice-baseline-feedback-20261011.json',
        REPORT/'conditioned-voicing-probe-20261011.json'])
    bindings=[ref(p) for p in paths]
    decisions={r['word']:r for r in load(paths[0])}
    geometry={r['word']:r for r in load(paths[1])}
    author={r['word']:r for r in load(paths[2])['cases']}
    response={r['word']:r for r in probe['word_rows']}
    rows=[]
    for word in range(270,285):
        d,g,r=decisions[word],geometry[word],response[word]
        row=dict(word=word,char=d['char'],context=d['context'],source_unknown=d['source_unknown'],
            own_music_stages_MIDI=[a['tone']/100 for a in d['entry_actions']],
            first_entry_family=d['entry_actions'][0]['family'],
            native_phone_symbols=[p['phoneme'] for p in g['phones']],
            native_phone_tones=[p['tone'] for p in g['phones']],native_vowel_s=g['native_vowel'],
            original_manual_controls=[dict(abbreviation=c['abbr'],parameters=c['parameters']) for c in d['controls']],
            original_VOIC_choice=d['voic_choice'],rejected_candidate_additive_VOIC=r['additive_VOIC_UI'],
            A_core_voicing=r['A_voicing_core_median'],rejected_B_core_voicing=r['B_voicing_core_median'],
            rejected_B_vowel_RMS_delta_db=r['vowel_RMS_change_db'],
            prior_label='original kan283 locally solid' if word==283 else ('airy near approximate time, not a named isolated word' if word==277 else 'individual label unknown'),
            new_individual_label='unknown: aggregate candidate rejection is not 15 individual labels',
            author_stages_MIDI=[s['tone'] for s in author[word]['author']['authored_stages']] if word in author else None,
            author_native_phone_tones=[p['tone'] for p in author[word]['phones_author']] if word in author else None)
        rows.append(row)
    assert len(rows)==15 and not any(r['source_unknown'] for r in rows)
    # A similar selected entry family exists in both focal words. Symbolic
    # phone identity and an entry label cannot identify the audible cause.
    focal={r['word']:r for r in rows if r['word'] in [277,283]}
    assert focal[277]['first_entry_family']==focal[283]['first_entry_family']=='short_direct'
    assert focal[277]['own_music_stages_MIDI']==[68,66] and focal[283]['own_music_stages_MIDI']==[66,64]
    findings=[
        'Finite positive VOIC changes actual input and increases five vowel RMS proxies by0.519..1.504dB, but aggregate target remains unaccepted; not sufficient evidence of solidity improvement.',
        'Original li277 has positive VOIC support while kan283 has none; original kan is locally solid. Written larger VOIC is not a demonstrated solidity rule.',
        'Both li277 and kan283 use short_direct first entry and descending two-stage musical shapes; an entry-family name alone does not distinguish their perceived solidity.',
        'Phonemes differ li:l/i vs kan:k/an; own native primary tones68 vs66. Author same symbolic words have lower primary tones66 vs64 and three-stage shapes66/68/66 and64/66/64.',
        'Author-vs-own comparison changes speaker, duration, musical phases, controls, context and prediction noise provenance; it is descriptive, not a causal isolation or transferable author target.',
        'The latest VOIC contrast held pitch/phones/speaker/three predictions fixed. Its rejection does not test a new phoneme or pitch-condition hypothesis.',
        'New candidate scopes are only two already-seen phrases, one affected VOIC phrase; repeats and successive feedback do not create independent holdout coverage.'
    ]
    save(RUN/'evaluation/joint-condition-review.json',dict(rows=rows,source_bindings=bindings,findings=findings,
        native_identity_binding=ref(PRIOR/'evaluation/native-independent-check.json'),
        stage_interpretation='existing own independently designed music stages, not an author curve transplant',
        author_arrays_used_as_targets=False,source_unknown106_elsewhere_preserved=True,
        next='review actual entry/body/pitch and phone context against original source observations before selecting any new finite design; no parameter sweep',
        next_candidate_designed=False,new_waveforms=0,new_array_audio_decodes=0,agent_heard=False))
    csv_rows=[]
    for row in rows:
        csv_rows.append({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(list,dict)) else v for k,v in row.items()})
    with (REPORT/(NAME+'-conditions.csv')).open('x',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(csv_rows[0]));writer.writeheader();writer.writerows(csv_rows)
    supplement=dict(record_id='RESP:LASTPAGE-CONDITIONED-VOIC-01',append_only_feedback=True,
        sealed_delivery_report=ref(REPORT/'conditioned-voicing-probe-20261011.json'),
        feedback=feedback,status='rejected_for_target_unmet',adoption=False,
        scope_words=list(range(270,285)),changed_words=[271,272,274,277,278],
        independent_contexts=2,affected_contexts=1,new_word_labels=0,
        stop='close current finite VOIC route; no dose escalation, gain compensation or automatic new candidate',
        prior_bright25_not_adopted=True,original_Normal75_Classic25_and_accepted_bao_C_preserved=True,
        table1_refs=['PER:S1','PARAM:C11.01'],measurement_validated=False,general_rule_validated=False)
    save(RUN/'evaluation/table2-supplement.json',supplement)
    report=dict(status='conditioned_voicing_feedback_closed_joint_conditions_reviewed',feedback=feedback,
        table2_supplement=supplement,condition_rows=rows,findings=findings,
        new_native_exports=0,new_model_calls=0,new_waveforms=0,new_candidate_designs=0,agent_heard=False,
        original_baseline=load(PRIOR/'design/protocol.json')['baseline'],
        further_auditory_or_unique_cause_status='unknown',general_rule_validated=False,measurement_validated=False)
    check([report['original_baseline']])
    save(REPORT/(NAME+'.json'),report)
    md='''# 最后一页：有限VOIC反馈收口与组合条件复核

2026-10-11。用户原话：“还是不行”。绑定本次VOIC候选B、原A与分开交付的白烁参考SHA，计1条聚合回复。候选未达到目标，不采用；没有补造“完全没区别”、破音、响度、咬字或未退化标签，也不沿用上轮speaker的“没有退化”。整曲载体是否试听unknown，不将这一回复扩为15条独立字标签。

关闭本次五字有限VOIC路线，停止加量、增益补偿或自动第三候选。上轮Bright25也未采用；原Normal75/Classic25、原VOIC范围200和已接受抱C保留。冻结交付报告的pending是当时状态，本补充登记后续反馈，旧报告/run/工程/音频保持。

数值执行通过不能代替目标达成：VOIC这次确实改变152帧，五字元音RMS代理上升约0.52–1.50dB，但用户仍不接受。这是当前剂量/条件的不足证据，不能宣布整个VOIC无效、只差更多增量或声音已因更响而变实。

只读复核两句15字的既有音乐阶段、声母/元音、原控制与当前响应。里277已有正VOIC，而看283没有新增VOIC仍被用户指出局部实；两者第一入口都叫short_direct，并各有下行两个音乐阶段，因此单一入口函数名称或正VOIC不能作为已验证规律。发音分别为l/i与k/an，原生主音tone分别68与66；作者同字tone为66与64，另保留三阶段66→68→66及64→66→64。它们是条件差异，不证明降低主音、修改音素或照抄作者能解决当前听感。原声源双F0/GAME、实际入口/字腹及完整邻域仍须逐项核对。

作者参考与自身同时改变声线、时长、音乐阶段、控制和上下文，预测噪声来源也未做跨作者同条件隔离；作者当前native/cache与自身seed11/101不是等随机条件的因果试验。不能用作者数组反向拟合目标，不能从两句试验宣称整曲/通用规律。当前两条新路线仍是已见曲开发，技术重复不扩充留出样本量。

下一项先核对原声源与当前实际音高阶段/音素条件，再决定有依据的有限设计。本轮仅反馈与既有条件复核，新控制设计/原生导出/模型执行/数组或音频解码/新波形均0。表1PER:S1、PARAM:C11.01与表2RESP:LASTPAGE-CONDITIONED-VOIC-01绑定该否定结果；原标签、源unknown106及未知病因保持。Agent未听，单Agent、CI仅手动。

详见[15字条件台账](conditioned-voicing-feedback-20261011-conditions.csv)、[JSON](conditioned-voicing-feedback-20261011.json)、[审计](conditioned-voicing-feedback-20261011-audit.json)。
'''
    (REPORT/(NAME+'.md')).write_text(md,encoding='utf-8',newline='\n')
    status=('当前状态conditioned_voicing_feedback_closed_joint_conditions_reviewed：2026-10-11“还是不行”绑定有限VOIC候选，'
        '计1聚合回复、目标未达到、不采用；破音/咬字/响度/差别细分unknown，不继承上轮未退化、不新增逐字标签。'
        'Bright25与本次VOIC均收口，停止加量/增益补偿，原Normal75/Classic25/范围200及抱C保留。'
        '15字音乐阶段/音素/原控制和响应只读复核；里/看入口同类、主音/元音/上下文不同，作者比较多因素且噪声未隔离，病因unknown。'
        '下一项先核对原声源与当前实际音高/音素条件再决定有限设计；新设计/导出/模型/数组音频解码/波形0。'
        'Agent未听、通用规律0，原歌曲/音频/Skill保持，单Agent/CI仅手动。')
    for name in ENTRIES:
        p=ROOT/name;lines=p.read_text(encoding='utf-8').splitlines()
        ids=[i for i,line in enumerate(lines) if '当前状态conditioned_voicing_delivered_pending_listening：' in line]
        assert len(ids)==1,name
        relative='docs/reports/lastpage/'+NAME+'.md'
        if '/' in name:relative=('../../' if name.startswith('research/') else '../../../')+relative
        lines[ids[0]]=('- ' if lines[ids[0]].startswith('- ') else '')+status+f' 见[VOIC收口与条件复核]({relative})。'
        for i,line in enumerate(lines):
            if name=='plan.md' and line.startswith('下一工作进入逐首更新，先《最后一页》：'):
                lines[i]='下一工作进入逐首更新，先《最后一页》：Bright25及本次有限VOIC未获接受，当前两路线收口、不加量。下一项先核对原声源与当前实际音高入口/字腹和音素/上下文条件，再决定有限设计；不复制白烁数组、不自动追加候选，原A/抱C、旧阴性和unknown保持。'
        p.write_text('\n'.join(lines)+'\n',encoding='utf-8',newline='\n')
    check(protected);check(bindings)
    with (REPORT/(NAME+'-conditions.csv')).open(encoding='utf-8-sig',newline='') as f:
        reread=list(csv.DictReader(f))
    assert len(reread)==15
    assert all(all(c[k]==('' if v is None else str(v)) for k,v in r.items()) for c,r in zip(reread,csv_rows))
    gate=subprocess.run([sys.executable,'tools/repository/check_repository.py','--worktree'],cwd=ROOT,capture_output=True,encoding='utf-8')
    (RUN/'logs').mkdir();(RUN/'logs/repository-gate.log').write_text(gate.stdout+gate.stderr,encoding='utf-8')
    assert gate.returncode==0,gate.stdout+gate.stderr
    audit=dict(status='passed_with_cause_and_auditory_gaps',reply_count=1,individual_new_labels=0,
        rejected_response='RESP:LASTPAGE-CONDITIONED-VOIC-01',existing_conditions_reviewed=15,
        new_waveforms=0,new_model_calls=0,new_array_audio_decodes=0,
        old_artifact_refs_unchanged=len(protected),source_bindings=bindings,script=ref(Path(__file__)),gate=gate.stdout.strip(),
        sealed_pending_reports_not_rewritten=True,measurement_validated=False,agent_heard=False)
    audit['csv_json_condition_rows_exact']=15
    save(RUN/'evaluation/audit.json',audit);save(REPORT/(NAME+'-audit.json'),audit)
    save(RUN/'completion-manifest.json',dict(status=audit['status'],
        files=[ref(p) for p in sorted(RUN.rglob('*')) if p.is_file()],
        documents=[ref(p) for p in sorted(REPORT.glob(NAME+'*'))],entries=[ref(ROOT/n) for n in ENTRIES]))
    print(json.dumps(dict(status=report['status'],reply=feedback['original_text'],conditions=15,new_waveforms=0,gate=audit['gate']),ensure_ascii=False))


if __name__=='__main__':main()
