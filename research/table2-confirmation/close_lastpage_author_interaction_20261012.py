"""Bind qualitative fourth-corner feedback and freeze one own-context voice test."""
import csv
import json
from pathlib import Path
import subprocess
import sys
import yaml

from assemble_lastpage_accepted_baseline_20261011 import ROOT,ENTRIES,load,save,ref,check

PRIOR=ROOT/'runs/experiments/lastpage-author-interaction-20261012'
RUN=ROOT/'runs/research/lastpage-author-interaction-feedback-20261012'
REPORT=ROOT/'docs/reports/lastpage'
NAME='author-interaction-feedback-20261012'
OWN=ROOT/'runs/production/lastpage-accepted-baseline-20261011'
BASE=ROOT/'runs/lastpage_loudness_skill_v02_20261007'


def main():
    assert not RUN.exists() and not (REPORT/(NAME+'.json')).exists()
    sealed=load(PRIOR/'completion-manifest.json');check(sealed['files']+sealed['documents']+sealed['entries'])
    protected=load(PRIOR/'protected-before.json')+sealed['files']+sealed['documents']+[ref(PRIOR/'completion-manifest.json')]
    check(protected);RUN.mkdir(parents=True);(RUN/'logs').mkdir();save(RUN/'protected-before.json',protected)
    for n in ENTRIES:
        p=RUN/'before'/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((ROOT/n).read_bytes())
    media=load(PRIOR/'evaluation/delivery-check.json')['outputs']
    feedback=dict(verbatim='D比B好一点点，很细微，比c差很多',submissions=1,date='2026-10-12',
        response_record='RESP:LASTPAGE-AUTHOR-INTERACTION-01',audio={k:media[k] for k in ['D','B','C']},
        relations=[dict(comparison='D-B',direction='D better',magnitude_verbatim='好一点点，很细微',magnitude='very small'),
            dict(comparison='D-C',direction='D worse',magnitude_verbatim='差很多',magnitude='large')],
        perceived_axis='comparative quality in ongoing solidity task; separate solidity/articulation/level dimensions not restated',
        reply_is_not_two_independent_feedback_submissions=True,individual_word_labels_added=0,
        D_vs_own_original='not directly stated in latest reply',A_vs_C_direction='unknown; previous close statement retained',
        side_effects_and_absolute_acceptance='unknown',adoption=False,agent_heard=False,measurement_validated=False)
    check(list(feedback['audio'].values()));save(RUN/'feedback/feedback.json',feedback)
    old_sources={
        'pitch_ablation':REPORT/'author-pitch-feedback-20261011.json',
        'speaker_author_controls':REPORT/'author-voice-feedback-20261011.json',
        'manual_group_author_speaker':REPORT/'author-controls-feedback-20261012.json',
        'native_gates':PRIOR/'evaluation/native-independent-check.json',
        'fresh_gates':PRIOR/'evaluation/fresh-independent-check.json',
        'music_timing_review':ROOT/'runs/research/lastpage-author-controls-feedback-20261012/evaluation/music-timing-review.json'}
    bindings=[ref(p) for p in old_sources.values()]
    relationships=[
        dict(comparison='A/P/N/PN vs own',factor='PITD/note.pitch offsets and snap',finding='all four author variants more solid than own',
            magnitude='no inter-version ranking',source=ref(old_sources['pitch_ablation'])),
        dict(comparison='B-A',factor='speaker under authored controls',finding='B worse than A; B slightly better than own by contextual referent',
            magnitude='not numerically graded',source=ref(old_sources['speaker_author_controls'])),
        dict(comparison='C-A',factor='manual three-channel group under authored speaker',finding='C very close to A',
            magnitude='close, not identical or graded interval',source=ref(old_sources['manual_group_author_speaker'])),
        dict(comparison='D-C',factor='speaker under zero manual group',finding='D much worse than C',
            magnitude='large',source=ref(RUN/'feedback/feedback.json')),
        dict(comparison='D-B',factor='manual three-channel group under own speaker',finding='D slightly better than B',
            magnitude='very small',source=ref(RUN/'feedback/feedback.json'))]
    findings=[
        'Latest reply contains two explicitly unequal comparison magnitudes; preserve very small improvement vs B and large degradation vs C.',
        'Under zero manual group, changing only speaker composition and its predictions/output causes a substantial reported preference gap.',
        'Under own speaker, removing the three manual deltas yields a very small reported improvement; it does not restore author-speaker quality.',
        'Earlier B-A preference and current D-C gap show speaker contribution in both tested control settings. This is local, not proof of a universal dominant factor.',
        'No exact perceptual interaction magnitude or absence can be computed from ordinal close/slight/large replies; numerical RMS interaction remains a proxy.',
        'Speaker contrasts include altered output levels and all three predictions; no matched-loudness physiological or unique-cause claim.',
        'Own-context Bright40/Cute60 has not been tested: earlier own Normal75/Bright25 rejection is a different composition.',
        'Musical first tones/stages and phone clocks differ across author/own, as already reviewed; preserve them while first testing speaker contribution under own conditions.'
    ]
    save(RUN/'evaluation/factorial-review.json',dict(relationships=relationships,findings=findings,source_bindings=bindings,
        speaker_effect_includes_prediction_and_level=True,quantified_auditory_interaction='unknown',
        new_models=0,new_PCM_NPZ_reads=0,new_waveforms=0,independent_author_contexts=2))
    own_score=OWN/'delivery/lastpage_accepted_C_baseline.ustx';doc=yaml.safe_load(own_score.read_text(encoding='utf-8-sig'))
    assert len(doc['voice_parts'])==34
    own_summary=[]
    for ix in [28,29]:
        p=doc['voice_parts'][ix]
        for k,v in [('cl03',75),('cl05',25)]:assert all(y==v for y in next(c for c in p['curves'] if c['abbr']==k)['ys'])
        for k in ['cl01','cl02','cl04']:
            c=next((c for c in p['curves'] if c['abbr']==k),None);assert doc['expressions'][k]['default_value']==0 and (c is None or all(y==0 for y in c['ys']))
        own_summary.append(dict(context=ix,notes=len(p['notes']),original_mix='Normal75/Classic25',part_position=p['position']))
    author_path=REPORT/'li-kan-author-reference-20261011.json';author=load(author_path)
    focal=[]
    for case in author['cases']:
        stages={}
        for field in ['speaker_author_acoustic','speaker_author_variance']:
            weights=case[field]['weights'];assert abs(weights['Bright']-.4)<1e-6 and abs(weights['Cute']-.6)<1e-6
            stages[field]=dict(weights=weights,reconstruction_max_abs=case[field]['reconstruction_max_abs'])
        focal.append(dict(word=case['word'],char=case['char'],stages=stages))
    next_protocol=dict(id='LASTPAGE-OWN-BRIGHT-CUTE-01',status='frozen_design_not_executed',
        rationale='reverse speaker factor under own music/phone/control conditions before changing music or timing',
        baseline=ref(own_score),baseline_preview=ref(OWN/'delivery/lastpage_accepted_C_baseline_vocal.wav'),
        author_focal_speaker_evidence=ref(author_path),evidence_summary=focal,
        candidate_label='E',contexts=[28,29],words=list(range(270,285)),own_contexts=own_summary,
        target_mix_by_name={'Bright':40,'Cute':60,'Normal':0,'Whisper':0,'Classic':0},target_cl01_cl05=[40,60,0,0,0],
        distinction='one independently chosen constant named composition informed by focal evidence; not a copy of author time-varying cl curve/CLR/note/PITD/control arrays',
        score_recipe='new own accepted-C copy; replace cl01..cl05 only on selected two parts with explicit total100 constant mix, preserve all other fields and 32 other parts',
        fixed=['own notes/tuning/PITD/note.pitch/vibrato','own lyrics/phone clocks/CLR','own VOIC/TENC/BREC/SHFC','original native DYN','fixed vocal gain1.5','variance11/acoustic101'],
        allowed=['both stage speaker embeddings','three newly computed predictions/final channels','selected acoustic output'],
        gates=['actual current singer clNN-name mapping and embeddings rechecked','native phonetic/full pitch and manual-delta identities',
            'new own-A inputs/predictions/raw PCM exact historical context28/29 and repeats exact',
            'E variance and acoustic speaker exact .4Bright+.6Cute, non-speaker conditions preserved',
            'E new predictions rebuilt, no reuse of Normal75/Classic25 prediction state',
            'native DYN/fixed gain/PCM clipping and second-context overlap explicitly checked',
            'all unaffected contributions including accepted baoC retained; no production adoption'],
        protection='kan283 original local solidity label retained; E new quality/side effects pending, not presumed protected by math',
        budget={'candidate_count':1,'independent_contexts':2,'new_native_cached_contexts':4,'new_seeded_waveforms':8,
            'variants_per_context':['own_A','own_A_repeat','E','E_repeat'],'new_F0_calls':8},
        preview='own two-phrase clock209.4–218.0; E vs own A is causal speaker contrast; author reference separate descriptive comparator',
        listening='whether E improves solidity/connection under own conditions; kan and articulation/break/level effects, missing labels unknown',
        stops=['identity/current mapping/A or repeat failure','nonfinite/file clipping','no automatic proportions/dose sweep or next factor'],
        new_score_written=0,new_model_calls=0,new_waveforms=0,adoption=False,agent_heard=False,measurement_validated=False,general_rule_validated=False)
    save(RUN/'design/next-own-voice-protocol.json',next_protocol)
    supplement=dict(record_id=feedback['response_record'],append_only_feedback=True,feedback=feedback,
        prior_report=ref(REPORT/'author-interaction-20261012.json'),table1_refs=['PER:S1']+[f'PARAM:C20.0{i}' for i in range(1,6)]+['PARAM:C11.01','PARAM:C12.01','PARAM:C13.01'],
        general_rule_validated=False,measurement_validated=False,adoption=False)
    save(RUN/'evaluation/table2-supplement.json',supplement)
    report=dict(status='author_interaction_feedback_closed_reverse_voice_design_frozen',feedback=feedback,relationships=relationships,findings=findings,
        table2_supplement=supplement,next_protocol=ref(RUN/'design/next-own-voice-protocol.json'),new_native_calls=0,new_models=0,new_PCM_NPZ_reads=0,new_waveforms=0,agent_heard=False)
    save(REPORT/(NAME+'.json'),report)
    csvrows=[dict(comparison=r['comparison'],factor=r['factor'],finding=r['finding'],magnitude=r['magnitude'],source_path=r['source']['path'],source_sha256=r['source']['sha256']) for r in relationships]
    with (REPORT/(NAME+'-comparisons.csv')).open('x',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(csvrows[0]));writer.writeheader();writer.writerows(csvrows)
    md='''# 最后一页：第四角反馈与反向声线候选准备

2026-10-12。用户原话“D比B好一点点，很细微，比c差很多”，计1回复，包含两条明确不同强度的关系：D−B为很细微改善，D−C为明显较差。绑定D/B/C音频SHA，不折叠为“差不多”，不新增逐字实感/无破音/咬字/响度副作用/绝对验收标签。D与自己的原版本轮未直接比较，前序B与原版关系的“原版”仍为语境解释。A与C保留之前“很接近”的表述，不推定准确方向或完全相同。

## 四角有限结论

|比较|所改因素|用户反馈|
|---|---|---|
|B−A|作者人工控制下换自己的声线|B不如A，略好于自己的原版（语境）|
|C−A|作者声线下取消三人工增量|C很接近A|
|D−C|零人工增量下换自己的声线|D比C差很多|
|D−B|自己的声线下取消三人工增量|D略好，差别很细微|

在两句作者音乐/音素条件下，声线及其预测/输出响应在两种控制设置下都有听感影响；取消控制组没有把自己的声线恢复到作者声线听感，组控制在自己声线下只支持细微改善。因此，**当前这两句中声线差距的反馈强度更明确**。这是有限条件的相对偏好证据，不是任意歌曲通用配比或唯一生理病因。声线响应还包含电平和三预测变化，未做响度匹配；三人工通道合组取消，不能宣布每条都无效或单个通道造成差距。

“接近／细微／差很多”不是可相减的区间标尺，不能从这些原话计算准确听觉交互幅度或证明完全无交互。既有四角RMS差分之差只是代理，原报告数值和状态保留；SHFC焦点原0仍没有实际干预结论。D不采用为自己制作版修复，作者A/C也不是整曲或独立留出验收。

## 下一项：自己的条件下反向检验声线，尚未执行

先保留自己完整音高、音乐阶段、歌词、音素时钟及人工控制，选一个E=Bright40/Cute60候选，仅在自己context28/29完整两句替换声线。该配比来源依据为已绑定作者里/看焦点两阶段实际speaker重建；作者整句mix有时变及CLR余量，所以E是**明确恒定的命名声线候选**，不声称整句与作者完全等价，不搬运作者cl节点/PITD/note.pitch/时钟/发声控制数组。

当前自己两句仍Normal75/Classic25。以前Normal75/Bright25未改善与本次40Bright/60Cute不同，旧阴性保留。先在自己的条件下判断声线能否改善；若不支持或仍有差距，既有15字里8字首音与阶段差异、原生时长差异继续作为有限候选，不一次同时改音高和时长，也不认作已确认病因。

E设计冻结两句A/A_repeat/E/E_repeat共8套新variance11/acoustic101/vocoder波形与8次新双F0、4原生缓存上下文，实际均0；E工程未写。本机clNN名称/两阶段embedding须复核，新自己的A须精确重现旧28/29预测/PCM，音符/phone时钟/人工增量与DYN保持，E新预测完整重算，原32句及已接受抱C、看283原局部标签保护范围明确。参考作者音频单独交付，只作描述性对照；E−自己A才是声线因素对照。固定1.5，无归一化/压缩/BGM/扫比例或加量，听觉待评、未采用。

本轮只完成1条反馈追加、5组关系汇总与反向设计冻结，没有新原生/模型/PCM或NPZ解码/波形。表1PER:S1与C20声线、C11–13控制及表2RESP:LASTPAGE-AUTHOR-INTERACTION-01追加；全部measurement_validated=false、通用规律0、Agent未听。原歌曲/音频/作者原件/Skill、unknown与旧阴性/抱C保持，单Agent，CI仅手动。

'''
    md+=f'[比较CSV]({NAME}-comparisons.csv)、[JSON]({NAME}.json)、[审计]({NAME}-audit.json)。\n'
    (REPORT/(NAME+'.md')).write_text(md,encoding='utf-8',newline='\n')
    status='当前状态author_interaction_feedback_closed_reverse_voice_design_frozen：2026-10-12“D比B好一点点很细微，比C差很多”计1回复/2关系，绑定D/B/C，保留细微与明显差距，不增逐字/副作用/绝对接受。四角支持作者条件下声线反馈影响更明确，取消组控制在自己声线下仅细微改善，不能计算准确听觉交互/单通道或唯一病因。下一项冻结自己两句E=Bright40/Cute60恒定命名声线，保持自身音高/时钟/控制、不搬作者数组；8波形/8双F0预算实际0、工程未写。原Normal75/Classic25及旧阴性/抱C/unknown保持，本轮无新模型/音频或NPZ解码/波形，原歌曲/音频/Skill/作者原件不变，Agent未听/通用规律0，单Agent/CI仅手动。'
    for n in ENTRIES:
        p=ROOT/n;lines=p.read_text(encoding='utf-8').splitlines();ix=[i for i,l in enumerate(lines) if '当前状态author_interaction_delivered_pending_listening：' in l];assert len(ix)==1,n
        rel='docs/reports/lastpage/'+NAME+'.md'
        if '/' in n:rel=('../../' if n.startswith('research/') else '../../../')+rel
        lines[ix[0]]=('- ' if lines[ix[0]].startswith('- ') else '')+status+f' 见[第四角反馈与反向声线设计]({rel})。'
        if n=='plan.md':
            for i,l in enumerate(lines):
                if l.startswith('下一工作进入逐首更新，先《最后一页》：'):lines[i]='下一工作进入逐首更新，先《最后一页》：D相对B细微改善、相对C明显较差，第四角反馈已追加。下一项按冻结协议在自己两句试E=Bright40/Cute60，只换两阶段声线并重算预测，自身音高/音素/控制/DYN保持，8新波形预算实际0；先验证自己的A精确与E隔离，再接听感。音乐阶段/时长差异仍待验，不一次同时改、不搬运作者数组或扫比例/加量。'
        p.write_text('\n'.join(lines)+'\n',encoding='utf-8',newline='\n')
    check(protected);check(bindings);check([ref(own_score),ref(author_path)])
    with (REPORT/(NAME+'-comparisons.csv')).open(encoding='utf-8',newline='') as f:restored=list(csv.DictReader(f))
    assert restored==[{k:str(v) for k,v in row.items()} for row in csvrows]
    gate=subprocess.run([sys.executable,'tools/repository/check_repository.py','--worktree'],cwd=ROOT,capture_output=True,encoding='utf-8')
    (RUN/'logs/repository-gate.log').write_text(gate.stdout+gate.stderr,encoding='utf-8');assert gate.returncode==0,gate.stdout+gate.stderr
    audit=dict(status='passed_with_perceptual_scale_and_transfer_gaps',feedback_submissions=1,new_relations=2,reviewed_relationships=5,new_word_labels=0,
        new_models=0,new_waveforms=0,new_PCM_NPZ_reads=0,source_bindings=bindings+[ref(own_score),ref(author_path)],
        next_protocol=ref(RUN/'design/next-own-voice-protocol.json'),source=ref(Path(__file__)),CSV_JSON_exact=True,
        protected_references=len(protected),gate=gate.stdout.strip(),agent_heard=False,measurement_validated=False)
    save(RUN/'evaluation/audit.json',audit);save(REPORT/(NAME+'-audit.json'),audit)
    save(RUN/'completion-manifest.json',dict(status=report['status'],files=[ref(p) for p in sorted(RUN.rglob('*')) if p.is_file()],
        documents=[ref(p) for p in sorted(REPORT.glob(NAME+'*'))],entries=[ref(ROOT/n) for n in ENTRIES]))
    print(json.dumps(dict(status=report['status'],feedback=feedback['verbatim'],new_waveforms=0,gate=audit['gate']),ensure_ascii=False))


if __name__=='__main__':main()
