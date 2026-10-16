"""Append G rejection, preserve conditional evidence, freeze one DYN-layer probe."""
import copy
import csv
import json
from pathlib import Path
import subprocess
import sys
import yaml
from assemble_lastpage_accepted_baseline_20261011 import ROOT,ENTRIES,load,save,ref,check
from agent2utau.knowledge import collect_context,validate_context,check_plan_knowledge

PRIOR=ROOT/'runs/experiments/lastpage-own-li-voic-stages-20261012'
F=ROOT/'runs/experiments/lastpage-own-control-neutral-20261012'
BASE=ROOT/'runs/lastpage_loudness_skill_v02_20261007'
RUN=ROOT/'runs/research/lastpage-own-li-voic-feedback-20261012'
REPORT=ROOT/'docs/reports/lastpage';NAME='own-li-voic-feedback-20261012'
KNOW=ROOT/'docs/knowledge/acoustic-manifestations-20261009';INDEX='table2-layering-feedback-index-20261012'
REGISTRY=KNOW/'active-knowledge-sources.json'

def write_csv(path,rows):
    with path.open('x',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def main():
    assert not RUN.exists() and not (REPORT/(NAME+'.json')).exists()
    seal=load(PRIOR/'completion-manifest.json');check(seal['files']+seal['documents']+seal['entries'])
    original=load(PRIOR/'protected-before.json')+seal['files']+seal['documents']+[ref(PRIOR/'completion-manifest.json')]
    check(original)
    registry_ref=ref(REGISTRY);protected=[r for r in original if r['path']!=registry_ref['path']]
    RUN.mkdir(parents=True);(RUN/'logs').mkdir();save(RUN/'protected-before.json',protected)
    for name in ENTRIES+[registry_ref['path']]:
        p=RUN/'before'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((ROOT/name).read_bytes())
    save(RUN/'design/mutable-registry-before.json',dict(reason='AGENTS knowledge catalogue maintenance only; old index/records remain immutable',registry=registry_ref,
        preserved_original_bytes=ref(RUN/'before'/registry_ref['path'])))
    media=load(PRIOR/'evaluation/delivery-check.json')['outputs']
    feedback=dict(verbatim='不行',submissions=1,date='2026-10-12',response_record='RESP:LASTPAGE-OWN-LI-VOIC-STAGES-01',
        candidate=media['candidate_preview'],baseline=media['original_preview'],author_reference=media['author_reference'],
        referent='G candidate inferred from immediately preceding labelled G/F/author delivery',
        finding='current G not acceptable for requested staged strength development; not adopted',
        precise_failure_dimension_location_magnitude='unknown: not specified in reply',
        no_difference_vs_worse_or_force_or_solidity_or_squeezing_or_break='unknown: rejection does not select these descriptions',
        new_individual_word_labels=0,dose_specific_rejection=True,all_VOIC_ineffective=False,adoption=False,agent_heard=False,measurement_validated=False)
    check([feedback[k] for k in ['candidate','baseline','author_reference']]);save(RUN/'feedback/feedback.json',feedback)
    prior_report=load(REPORT/'own-li-voic-stages-probe-20261012.json');phases=prior_report['phase_rows'];assert len(phases)==5
    source_bindings=[ref(REPORT/'own-li-voic-stages-probe-20261012.json'),ref(BASE/'native_word_geometry.json'),
        ref(BASE/'agent_word_decisions.json'),ref(F/'score/lastpage_own_control_neutral_F.ustx'),ref(F/'observations/results.json'),
        ref(KNOW/'knowledge-table.json'),ref(KNOW/'control-details.csv')]
    own=next(r for r in load(BASE/'agent_word_decisions.json') if r['word']==277)
    geometry=next(r for r in load(BASE/'native_word_geometry.json') if r['word']==277)
    s,e=geometry['native_vowel'];arrival=own['entry_actions'][0]['arrival'];peak=own['body'][0]['parameters'][1]
    body_end=own['entry_actions'][0]['body_end'];turn=own['entry_actions'][1]['onset']
    consonant=next(p for p in geometry['phones'] if p['phoneme']=='zh/l')
    prep=s-.040;assert consonant['start_ms']/1000<prep<s
    # One musical envelope, independently chosen from own stages; not author fitting.
    nodes=[[prep,0],[s,-40],[arrival,-40],[peak,15],[body_end,0],[turn,-15],[e,0]]
    doc=yaml.safe_load((F/'score/lastpage_own_control_neutral_F.ustx').read_text(encoding='utf-8-sig'))
    desc=doc['expressions']['dyn'];assert desc['default_value']==0 and desc['min']<min(v for t,v in nodes) and desc['max']>=max(v for t,v in nodes)
    review=dict(source_bindings=source_bindings,prior_G_phase_rows=phases,
        limited_finding='G input progression passed, but absolute output phase RMS remained stronger at onset and declined; relative middle increase only~0.16–0.27dB.',
        causal_boundary='This does not identify why user rejected G or prove VOIC cannot produce staged effects at other doses/conditions.',
        baseline='F remains improved working comparator, not full-song accepted production',
        layering_boundary='VOIC changes model phonation; DYN changes output gain. Neither input label proves perceived force development.',
        next_choice='DYN-only contrast based on own timing; no louder VOIC/TENC dose sweep, no simultaneous music/timing change',
        native_DYN_unit='0.1dB per UI; renderer minimum special mute is not used',native_DYN_descriptor=desc,
        own_word_geometry=geometry,new_PCM_NPZ_reads=0,new_measurements=0,new_models=0,new_waveforms=0)
    save(RUN/'evaluation/strength-review.json',review)
    supplement=dict(record_id=feedback['response_record'],append_only_feedback=True,feedback=feedback,
        prior_report=ref(REPORT/'own-li-voic-stages-probe-20261012.json'),
        table1_refs=['PER:S1','EVT:L2','ACO:L1','PARAM:C11.01'],
        measured_failure_cause='unknown',adoption=False,measurement_validated=False,general_rule_validated=False)
    save(RUN/'evaluation/table2-supplement.json',supplement)
    report=dict(status='G_feedback_closed_DYN_layer_design_frozen',feedback=feedback,table2_supplement=supplement,
        strength_review=ref(RUN/'evaluation/strength-review.json'),next_protocol_path=(RUN/'design/next-li-DYN-protocol.json').relative_to(ROOT).as_posix(),
        new_models=0,new_waveforms=0,new_PCM_NPZ_reads=0,agent_heard=False,adoption=False,measurement_validated=False,general_rule_validated=False)
    save(REPORT/(NAME+'.json'),report)
    write_csv(REPORT/(NAME+'-prior-stages.csv'),phases)
    md=f'''# 最后一页：里VOIC阶段G否定反馈与输出包络候选

2026-10-12。用户原话“不行”，计1聚合回复，按上轮G/F/作者标注绑定G。当前G不采用，保留F“更好了”作为工作比较基底，不写成F整曲验收。拒绝没有给出具体字/时点/差距或虚实、挤尖、破音、咬字等维度，不补“没区别”“更差”或逐字标签。表2RESP:LASTPAGE-OWN-LI-VOIC-STAGES-01追加此有限否定，旧pending报告和音频SHA保持，不宣布VOIC所有条件无效，不自动加大剂量。

## 已有响应复核

原G35帧VOIC输入上升后回收、三预测/其它输入与F精确，但已有5阶段输出RMS仍字头较强往后收；主体G−F约+0.157/+0.269dB、全里+0.116dB。技术响应轻微与目标未通过可以并列，不能因此确定用户拒绝原因。这里仅复用封存JSON、自己音素/音乐阶段与工程描述，没有新PCM/mel/F0/NPZ读取或复测，未复制作者包络/节点。

## 单个下一项H：F基底DYN输出强弱

保持F声线/全部音高/音乐与原生音素时钟/CLR/TENC/BREC/VOIC/SHFC及模型预测，仅安排里输出DYN。自身元音{s:.9f}–{e:.9f}s，最后40ms的l准备从{prep:.9f}s开始；DYN UI节点{nodes}，对应0、−4、−4、+1.5、0、−1.5、0dB。前导准备柔化入口，自己的到达后逐渐展开到主体锚点，再回收并在下一字前恢复基底。曲线逐段smoothstep零切线、原整数5tick网格，−40不是renderer特殊最小静音。单个有限设计，数值来自当前音乐判断与自身既有能量线索，不是作者拟合或通用剂量。

此对照检查**输出强弱包络是否改善力度层次**；DYN不改变声学模型发声特征或证明生理发力变化。保持真实声线、发声和音高才可区分两个层次，仍须试听。最后40ms l也受增益准备影响，辅音咬字是必查副作用，不能声称只改元音。边界0增益恢复与真实采样须核对，不偷用另一条手工增益交付。

H暂未执行：预算2句原生缓存技术导出，新的固定种子variance/acoustic/vocoder合成0，明确复用F绑定raw/预测输入；context28 H/H_repeat两份处理贡献/PCM重复，不计为2个独立合成，第二句独立F保持。新F0预算2，旧F数组显式复用；核对原生DYN实际布局/逐样本增益、乘法/固定1.5/PCM、全句及15字邻域与5阶段，只有context28贡献范围可改变，context29头padding重叠与真实音素分开、看/抱C保留。不归一化、不扫剂量、不改BGM/Skill/发布歌。

当前来源目录切换到新反馈索引，G旧技术字段精确复制，新增“不行”的音频绑定/否定被实际检索和决策门禁验证。下一项知识receipt会明确拒绝当前G、保留F基线，并将DYN层与感知发力分开。Agent未听，新模型/音频/数组读取0、measurement_validated=false、通用规律0，单Agent、CI仅手动。

[原阶段CSV]({NAME}-prior-stages.csv)、[JSON]({NAME}.json)、[审计]({NAME}-audit.json)。
'''
    (REPORT/(NAME+'.md')).write_text(md,encoding='utf-8',newline='\n')
    config=load(REGISTRY);assert len(config['response_indices'])==1
    old_path=ROOT/config['response_indices'][0];index=copy.deepcopy(load(old_path))
    row=next(r for r in index['rows'] if r['id']==feedback['response_record'])
    before_row=copy.deepcopy(row);assert not row['feedback_sources']
    row.update(feedback_sources=[ref(REPORT/(NAME+'.json'))],feedback_record=feedback,scope='G technical delivery retained; appended user rejection, no adoption')
    assert row['source_record']==before_row['source_record'] and row['source']==before_row['source']
    index.update(generator=ref(Path(__file__)),prior_index=ref(old_path),status='current_index_G_rejection_appended_with_explicit_gaps')
    save(KNOW/(INDEX+'.json'),index)
    csvrows=[dict(id=r['id'],kind=r['kind'],source_path=r['source']['path'],source_sha256=r['source']['sha256'],
        feedback_paths='|'.join(p['path'] for p in r['feedback_sources']),table1_refs='|'.join(r['table1_refs']),scope=r['scope']) for r in index['rows']]
    write_csv(KNOW/(INDEX+'.csv'),csvrows)
    imd='# 表2当前索引：G试听否定追加\n\n旧14/2E与近9系列原记录字段保持，G技术交付后追加“不行”，当前G不采用。packet/summary行不重复计为独立反馈或样本。\n\n|ID|技术/原记录|后续反馈|\n|---|---|---|\n'
    for r in index['rows']:
        fb='、'.join(f"[{Path(p['path']).stem}](../../../{p['path']})" for p in r['feedback_sources']) or '见原包'
        imd+=f"|{r['id']}|[{Path(r['source']['path']).stem}](../../../{r['source']['path']})|{fb}|\n"
    imd+=f'\n[CSV]({INDEX}.csv)、[JSON]({INDEX}.json)。无通用规律/测量全面验证升级，unknown和阴性保留。\n'
    (KNOW/(INDEX+'.md')).write_text(imd,encoding='utf-8',newline='\n')
    config['response_indices']=[ref(KNOW/(INDEX+'.json'))['path']]
    REGISTRY.write_text(json.dumps(config,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    packet=collect_context(['PER:S1','EVT:L2','ACO:L1'],['PARAM:C10.01','PARAM:C11.01'],
        ['RESP:LASTPAGE-OWN-LI-VOIC-STAGES-01','RESP:LASTPAGE-OWN-CONTROL-NEUTRAL-01'])
    decisions=[]
    for r in packet['records']:
        choice='reject' if r['id']==feedback['response_record'] else 'extrapolate' if r['id']=='PARAM:C10.01' else 'use'
        reason='Current G user rejection retained, no larger VOIC dose' if choice=='reject' else 'DYN-only musical level gesture, not a claim of changed model phonation' if choice=='extrapolate' else 'Keep F conditions and distinguish level/envelope from perceived strength'
        decisions.append(dict(id=r['id'],decision=choice,reason=reason,condition_match='Same current1.65c own li/two phrases; DYN-only response not yet tested',
            limitations='User rejection dimension unknown; F aggregate improvement not whole-song acceptance; no universal dose or calibrated force estimate'))
    save(RUN/'design/knowledge_context.json',packet);save(RUN/'evaluation/knowledge_receipt.json',validate_context(packet,decisions))
    Grow=next(r for r in packet['records'] if r['id']==feedback['response_record']);assert Grow['record']['feedback_record']['verbatim']=='不行'
    nextplan=dict(id='LASTPAGE-OWN-LI-DYN-LAYERS-01',status='finite_design_frozen_not_executed',baseline_score=ref(F/'delivery/lastpage_own_control_neutral_F.ustx'),
        baseline_project=ref(F/'delivery/lastpage_own_control_neutral_F.ustx'),baseline_audio=media['original_preview'],author_reference=media['author_reference'],
        variant='H',target_word=277,affected_context=28,control_context=29,review_words=list(range(270,285)),
        gesture=dict(channel='dyn',UI_baseline=0,UI_nodes_s=nodes,unit='UI*0.1dB',interpolation='piecewise cubic smoothstep, integer5tick UI quantization',
            support_s=[prep,e],included_consonant='last40ms l preparation before i',
            purposes=['soften entry','gradually develop output at own body anchor','recover for own descending stage','return neutral at next-word boundary']),
        fixed=['all notes/tuning/PITD/note.pitch/vibrato','lyrics/CLR/phone/full clock','two-stage Bright40/Cute60',
            'TENC/BREC/VOIC/SHFC and all variance/acoustic/vocoder conditions','F seeded raw11/101','common gain1.5'],
        dependencies='DYN post-synthesis only; source SHA and native inputs/predictions must match F before any raw reuse',
        budget=dict(candidate_count=1,new_native_cached_contexts=2,new_seeded_variance_calls=0,new_seeded_synthesis_waveforms=0,
            processed_contribution_repeats=2,new_F0_calls=2,sealed_F_reuse=True),
        gates=['full score changes only target dyn grid values, native roundtrip/readback and unaltered model feeds',
            'native DYN layout and actualgain independently reconstructed, raw multiply exact, repeated processed PCM exact',
            'no file clipping/nonfinite or gain normalization; fixed1.5 PCM24 and34contributions checked',
            'stage raw/processed outputs compared without asserting perceived force; l articulation and all15word neighbors reviewed',
            'context29 independent raw/real phone PCM and kan exact; possible shared head padding change scoped; acceptedbaoC retained'],
        stops=['hash/identity/DYN mismatch','nonfinite/file clipping','no dose sweep/combined factors or extrapolated adoption'],
        knowledge_context=dict(path='knowledge_context.json',sha256=ref(RUN/'design/knowledge_context.json')['sha256'],decisions=decisions),
        new_score_written=0,new_models=0,new_audio=0,adoption=False,agent_heard=False,measurement_validated=False,general_rule_validated=False)
    save(RUN/'design/next-li-DYN-protocol.json',nextplan);_,receipt=check_plan_knowledge(nextplan,RUN/'design/next-li-DYN-protocol.json')
    assert receipt==dict(load(RUN/'evaluation/knowledge_receipt.json'),packet_sha256=nextplan['knowledge_context']['sha256'])
    status=('当前状态G_feedback_closed_DYN_layer_design_frozen：2026-10-12“不行”计1聚合回复，绑定G并不采用，不补没区别/更差/挤尖/逐字标签，不宣布VOIC全无效或加量。'
        '保留F改善工作基线；原G输入有序但绝对能量仍头强后弱的JSON复核，仅代理非拒绝病因。'
        '新反馈索引/知识receipt实际包含否定，下一项冻结F基底DYN单因素H：后40ms l准备/里入口−4dB、主体+1.5dB再回收，音高/声线/发声预测保持，'
        '0新seeded合成/2处理重复/2新F0预算实际0，H工程未写；本轮无PCM/NPZ/模型/新音频，原歌音频Skill/作者/旧阴性/抱C/unknown保持，'
        'Agent未听/通用规律0，单Agent/CI仅手动。')
    for name in ENTRIES:
        p=ROOT/name;lines=p.read_text(encoding='utf-8').splitlines();ix=[i for i,l in enumerate(lines) if '当前状态knowledge_integrated_G_delivered_pending_listening：' in l];assert len(ix)==1,name
        rel='docs/reports/lastpage/'+NAME+'.md'
        if '/' in name:rel=('../../' if name.startswith('research/') else '../../../')+rel
        lines[ix[0]]=('- ' if lines[ix[0]].startswith('- ') else '')+status+f' 见[G否定与输出包络设计]({rel})。'
        if name=='plan.md':
            for i,l in enumerate(lines):
                if l.startswith('下一工作进入逐首更新，先《最后一页》：'):lines[i]='下一工作进入逐首更新，先《最后一页》：里VOIC阶段G被“不行”否定，已追加表2/当前索引并在知识决策中拒绝，不加大VOIC。下一项冻结F基底DYN输出包络H，声线/音乐音素/发声条件保持，0新seeded合成、2处理重复/2新F0预算实际0；先检查原生DYN与模型输入保持，再听层次，H未执行/未采用。'
        if name=='docs/knowledge/acoustic-manifestations-20261009/README.md':
            lines=[l.replace('table2-layering-delivery-index-20261012.md',INDEX+'.md') if l.startswith('制作使用[当前表2索引]') else l for l in lines]
        p.write_text('\n'.join(lines)+'\n',encoding='utf-8',newline='\n')
    check(protected);check(source_bindings)
    for r in index['rows']:
        check([r['source']]+r['feedback_sources'])
        if r['id']!=feedback['response_record']:
            assert r==next(q for q in load(old_path)['rows'] if q['id']==r['id'])
    with (KNOW/(INDEX+'.csv')).open(encoding='utf-8-sig',newline='') as f:assert list(csv.DictReader(f))==[{k:str(v) for k,v in r.items()} for r in csvrows]
    gate=subprocess.run([sys.executable,'tools/repository/check_repository.py','--worktree'],cwd=ROOT,capture_output=True,encoding='utf-8')
    (RUN/'logs/repository-gate.log').write_text(gate.stdout+gate.stderr,encoding='utf-8');assert gate.returncode==0,gate.stdout+gate.stderr
    audit=dict(status='passed_with_explicit_rejection_cause_and_gain_perception_gaps',source=ref(Path(__file__)),
        feedback_submissions=1,new_word_labels=0,new_models=0,new_waveforms=0,new_PCM_NPZ_reads=0,
        protected_references=len(protected),source_bindings=source_bindings,current_index=ref(KNOW/(INDEX+'.json')),
        current_registry=ref(REGISTRY),next_protocol=ref(RUN/'design/next-li-DYN-protocol.json'),
        knowledge_rejection_retrieved=True,CSV_and_prior_index_fields_exact=True,gate=gate.stdout.strip(),
        agent_heard=False,adoption=False,measurement_validated=False,general_rule_validated=False)
    save(RUN/'evaluation/audit.json',audit);save(REPORT/(NAME+'-audit.json'),audit)
    docs=[ref(p) for p in sorted(REPORT.glob(NAME+'*'))]+[ref(p) for p in sorted(KNOW.glob(INDEX+'*'))]+[ref(REGISTRY)]
    save(RUN/'completion-manifest.json',dict(status=report['status'],files=[ref(p) for p in sorted(RUN.rglob('*')) if p.is_file()],documents=docs,entries=[ref(ROOT/n) for n in ENTRIES]))
    print(json.dumps(dict(status=report['status'],feedback=feedback['verbatim'],new_waveforms=0,knowledge_negative_retrieved=True,gate=audit['gate']),ensure_ascii=False),flush=True)

if __name__=='__main__':main()
