"""Close F feedback, index sealed table2 packets, plan a finite own VOIC gesture."""
import csv
import json
from pathlib import Path
import subprocess
import sys
import yaml
from assemble_lastpage_accepted_baseline_20261011 import ROOT,ENTRIES,load,save,ref,check

PRIOR=ROOT/'runs/experiments/lastpage-own-control-neutral-20261012'
BASE=ROOT/'runs/lastpage_loudness_skill_v02_20261007'
RUN=ROOT/'runs/research/lastpage-own-layering-feedback-20261012'
REPORT=ROOT/'docs/reports/lastpage';NAME='own-layering-feedback-20261012'
KNOW=ROOT/'docs/knowledge/acoustic-manifestations-20261009';INDEX='table2-supplement-index-20261012'

def write_csv(path,rows):
    with path.open('x',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def main():
    assert not RUN.exists() and not (REPORT/(NAME+'.json')).exists() and not (KNOW/(INDEX+'.json')).exists()
    seal=load(PRIOR/'completion-manifest.json');check(seal['files']+seal['documents']+seal['entries'])
    protected=load(PRIOR/'protected-before.json')+seal['files']+seal['documents']+[ref(PRIOR/'completion-manifest.json')]
    check(protected);RUN.mkdir(parents=True);(RUN/'logs').mkdir();save(RUN/'protected-before.json',protected)
    for name in ENTRIES:
        p=RUN/'before'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((ROOT/name).read_bytes())
    media=load(PRIOR/'evaluation/delivery-check.json')['outputs']
    feedback=dict(verbatim='还有每轮的记录到表里了吗？以及更好了，但是比如像里字，白烁的是有发力强度区分的，渐强到减弱。就是发声的强弱安排也需要有层次',
        submissions=1,date='2026-10-12',response_record='RESP:LASTPAGE-OWN-CONTROL-NEUTRAL-01',
        candidate=media['candidate_preview'],baseline=media['original_preview'],author_reference=media['author_reference'],
        aggregate_finding='F better than E inferred from immediately preceding labelled delivery; precise dimensions/magnitude unspecified',
        candidate_accepted_or_solid_retained_or_adverse_terms_resolved='unknown: better does not specify complete acceptance or individual prior adjectives',
        user_named_focus=dict(word=277,char='里',author_heard_arrangement='发力强度区分，渐强到减弱',
            request='own phonation strength needs staged development',scope='musical/phonation intention; no measured author envelope or per-word blanket labels'),
        new_individual_word_quality_labels=0,break_articulation_level_kan='unknown',adoption=False,agent_heard=False,measurement_validated=False)
    check([feedback[k] for k in ['candidate','baseline','author_reference']]);save(RUN/'feedback/feedback.json',feedback)
    bindings=[ref(BASE/n) for n in ['native_word_geometry.json','agent_word_decisions.json']]
    bindings += [ref(PRIOR/'observations/results.json'),ref(PRIOR/'score/lastpage_own_control_neutral_F.ustx'),
        ref(KNOW/'atomic-manifestations.csv'),ref(KNOW/'control-details.csv')]
    g=next(r for r in load(BASE/'native_word_geometry.json') if r['word']==277)
    d=next(r for r in load(BASE/'agent_word_decisions.json') if r['word']==277)
    obs=load(PRIOR/'observations/results.json');li=next(r for r in obs['windows'] if r['word']==277 and r['role']=='full_vowel')
    s,e=g['native_vowel'];assert d['context']==28 and not d['source_unknown']
    doc=yaml.safe_load((PRIOR/'score/lastpage_own_control_neutral_F.ustx').read_text(encoding='utf-8-sig'))
    assert doc['expressions']['voic']['min']<=100 and doc['expressions']['voic']['max']>=106
    assert all(v==100 for c in doc['voice_parts'][28]['curves'] if c['abbr']=='voic' for v in c['ys'])
    # Own established arrival/body and +stage anchors, no author-node transfer.
    arrival=d['entry_actions'][0]['arrival'];peak=d['body'][0]['parameters'][1]
    body_end=d['entry_actions'][0]['body_end'];turn=d['entry_actions'][1]['onset']
    nodes=[[s,0],[arrival,0],[peak,6],[body_end,2],[turn,0],[e,0]]
    assert all(s<=t<=e for t,v in nodes) and all(a[0]<b[0] for a,b in zip(nodes,nodes[1:]))
    nextplan=dict(id='LASTPAGE-OWN-LI-VOIC-STAGES-01',status='finite_design_frozen_not_executed',
        baseline_score=media['candidate_project'],baseline_audio=media['candidate_preview'],author_reference=media['author_reference'],
        baseline_role='F improved working comparator only; not adopted as whole-song production',
        scope=dict(target_word=277,char='里',affected_context=28,control_context=29,review_words=list(range(270,285))),
        rationale='User requests soft establishment, gradual strength development, recovery before own descending stage; avoid uniform stronger plateaus.',
        gesture=dict(channel='voic',UI_baseline=100,additive_UI_nodes=nodes,peak_UI=106,
            interpolation='piecewise cubic smoothstep, zero tangent at each node; bounded monotone segments; integer5tick overlay',
            phases=['retain own vowel/lyrical entry to213.0622917s','gradually develop to own finite-body anchor213.224295s',
                'recover through own body_end213.4152083s','neutral before own descending stage213.5302083s; neutral exit'],
            expected='relative strength progression in this current context; actual output response and listening may disagree',
            dose_role='Agent one finite +6UI candidate, not learned threshold or author fit',
            support='native i vowel only; consonant l and outside support manual input exact F'),
        fixed=['Bright40/Cute60 and both-stage speaker','own notes/tuning/PITD/note.pitch/vibrato',
            'all lyrics/phone/CLR/full clocks','TENC/BREC/SHFC neutral F','native DYN unity/fixed1.5','variance11/acoustic101'],
        alternatives=['Uniform higher VOIC rejected because it lacks stages.',
            'TENC simultaneously increased rejected while squeezed/sharp issue remains only partially labelled.',
            'DYN-only deferred: it changes output level without establishing a model-phonation contrast; not a general rejection of DYN.',
            'Author control arrays/pitch/time nodes not transplanted; author auditory gesture is descriptive input only.'],
        budget=dict(candidate_count=1,new_variance_calls=2,new_seeded_waveforms=2,variants=['G','G_repeat'],
            new_native_cached_contexts=2,new_F0_calls=2,sealed_F_contexts_reused=2),
        gates=['new native only word277 VOIC support changes; score32other parts exact; context29 inputs and raw exact F',
            'fresh variance inputs/predictions exact F, acoustic only final voicing changes',
            'new repeats exact; VOIC legal range/clip independently checked',
            'real early/middle/late PCM/feature response checked; rising control is not proof rising perceived force',
            'context28 tail/context29 shared head explicit; all other real phones/acceptedbaoC/other contributions retained'],
        stop='identity/hash/nonfinite/clipping/repeat failure; no extra doses/factors or normalization',
        listening='G-F whether li has gradual force development then recovery; solidity and sharp/squeezed/articulation if reported',
        new_score_written=0,new_model_calls=0,new_waveforms=0,adoption=False,agent_heard=False,measurement_validated=False,general_rule_validated=False)
    save(RUN/'design/next-li-voic-stage-protocol.json',nextplan)
    review=dict(source_bindings=bindings,word_geometry=g,own_decision=d,
        F_li_existing_observation=li,F_manual_VOIC=100,F_DYN=0,
        finding='Neutral manual curves do not make actual output constant, and do not constitute a deliberately staged phonation gesture.',
        existing_output_read='JSON77-window observations reused; no new PCM/NPZ/F0 decoding or metrics',
        no_author_array_or_clock_transfer=True,new_models=0,new_waveforms=0)
    save(RUN/'evaluation/own-li-stage-review.json',review)
    supplement=dict(record_id=feedback['response_record'],append_only_feedback=True,feedback=feedback,
        prior_report=ref(REPORT/'own-control-neutral-probe-20261012.json'),
        table1_refs=['PER:S1','PARAM:C11.01','PARAM:C12.01','PARAM:C13.01'],
        layering_related_entities_candidates=['EVT:L2','ACO:L1'],layering_not_a_measured_entity_label=True,
        adoption=False,measurement_validated=False,general_rule_validated=False)
    save(RUN/'evaluation/table2-supplement.json',supplement)
    report=dict(status='own_F_feedback_closed_layering_design_frozen',feedback=feedback,table2_supplement=supplement,
        review=ref(RUN/'evaluation/own-li-stage-review.json'),next_protocol=ref(RUN/'design/next-li-voic-stage-protocol.json'),
        new_models=0,new_waveforms=0,new_PCM_NPZ_reads=0,agent_heard=False,measurement_validated=False,general_rule_validated=False)
    save(REPORT/(NAME+'.json'),report)
    phase_rows=[dict(time_s=t,additive_VOIC_UI=v,absolute_VOIC_UI=100+v,status='planned_not_executed') for t,v in nodes]
    write_csv(REPORT/(NAME+'-stages.csv'),phase_rows)
    md=f'''# 最后一页：F改善反馈、记录入口与里字强弱层次

2026-10-12。完整用户原话：{feedback['verbatim']}。计1回复，“更好了”按上轮交付语境为F相对E改善，未细分实感/前顶/挤细尖各自改善程度，也未宣称完全无破音、看不退化或整曲接受。F作为后续工作的比较基底，不采用为发布版。明确字“里”277及作者“发力强度区分，渐强到减弱”作为听觉描述和表达要求，不冒称实测作者包络或其具体控制手法。

每轮原生/fresh/PCM与试听反馈有带SHA的表2补充记录、CSV和报告；此前入口分散，旧14行主表没有被覆盖。本次增加[表2补充统一索引](../../../docs/knowledge/acoustic-manifestations-20261009/{INDEX}.md)，列旧14记录、2E反馈包与当前8响应系列，渲染/后续反馈分别引用，不把pending历史报告改写为已接受。索引是现行关联入口，原表1实体/主表数值保持；最近8系列的表1引用在新[案例CSV](../../../docs/knowledge/acoustic-manifestations-20261009/{INDEX}-table1-cases.csv)中并列，实验标签不升为普遍规律。

里自身native i元音{s:.9f}–{e:.9f}s、约{(e-s)*1000:.3f}ms，own68→66阶段、首音到达{arrival:.9f}s、主体锚点{peak:.9f}s、回收{body_end:.9f}s、后阶段{turn:.9f}s。F的VOIC100/DYN0无人工事件，但模型/音素输出已有强弱变化；“没有人工层次安排”和“声音完全恒定”不同。只读现有JSON短窗/特征和自己决策，未新测音频，未拿作者曲线/能量数组拟合。

下一项冻结单个G：在F基底只给里元音VOIC有限有序包络，原值100，{nodes}；早期保持既有入口，渐强到+6UI，回收至+2UI，自己的下降音乐阶段前恢复0。逐段smoothstep零切线、整数5tick编译，支撑内外检查；不把所有长音等分或同形复制。自身音乐节点作为锚点，作者只提供本次听觉目的。TENC/BREC/SHFC、speaker和DYN保持；+6UI是Agent一个有限设计，不是学得的通用剂量，不承诺实际发力单调。先区分模型发声变化与DYN输出包络，不同时抬张力/改音高/加增益。

预算context28 G/G_repeat两套新variance/acoustic/vocoder、2新F0、两句原生缓存技术；F原输入/音频封存复用，context29作为完整保持对照，共享头padding须明确。15字邻域记录、只1字为干预目标，重复不增加独立条件；不是通用或留出验证。检查三预测精确F、仅final VOIC改变、阶段输出代理与听觉分开。新G工程/模型/波形实际0。

本轮只追加1反馈、统一索引与阶段设计；没有新PCM/NPZ读取/模型/音频，原歌曲/音频/Skill/作者原件、旧阴性/抱C/unknown保持。Agent未听，measurement_validated=false、通用规律0，单Agent、CI仅手动。

[阶段CSV]({NAME}-stages.csv)、[JSON]({NAME}.json)、[审计]({NAME}-audit.json)。
'''
    (REPORT/(NAME+'.md')).write_text(md,encoding='utf-8',newline='\n')
    # Current supplement index: source packets and original fields stay separate.
    old=load(KNOW/'conditional-responses.json');index_rows=[]
    for kind in ['responses','observations','audits']:
        for r in old[kind]:
            index_rows.append(dict(id=r['id'],kind='base_'+kind,source=ref(KNOW/'conditional-responses.json'),
                feedback_sources=[],table1_refs=r.get('atomic_ids',[]),source_record=r,scope='sealed old14 schema3; no new labels'))
    for p in sorted(KNOW.glob('table2-stage-2e-*-feedback-20261011.json')):
        if p.name.endswith('-audit.json'):continue
        x=load(p);index_rows.append(dict(id='PACKET:'+p.stem,kind='2E_feedback_packet',source=ref(p),feedback_sources=[],
            table1_refs=['PER:S1'],source_record=x,scope='packet, may contain multiple comparisons; no extra independent sample count'))
    closure=KNOW/'table2-listening-cycle-closure-20261011.json'
    index_rows.append(dict(id='PACKET:2E-listening-closure',kind='2E_summary',source=ref(closure),feedback_sources=[],
        table1_refs=['PER:S1'],source_record=load(closure),scope='summary references earlier packets; do not count as duplicate feedback'))
    pairs=[('voice-baseline-probe-20261011','voice-baseline-feedback-20261011'),
        ('conditioned-voicing-probe-20261011','conditioned-voicing-feedback-20261011'),
        ('author-pitch-ablation-20261011','author-pitch-feedback-20261011'),
        ('author-voice-swap-20261011','author-voice-feedback-20261011'),
        ('author-control-neutral-20261011','author-controls-feedback-20261012'),
        ('author-interaction-20261012','author-interaction-feedback-20261012'),
        ('own-bright-cute-probe-20261012','own-bright-cute-feedback-20261012'),
        ('own-control-neutral-probe-20261012',NAME)]
    case_rows=[]
    for render_name,feedback_name in pairs:
        rp=REPORT/(render_name+'.json');fp=REPORT/(feedback_name+'.json');r=load(rp);f=load(fp);s=r['table2_supplement'];fb=f['feedback']
        text=fb.get('verbatim',fb.get('original_text',''));assert text
        refs=['PER:S1'];refs+=s.get('table1_refs',[]) if isinstance(s.get('table1_refs'),list) else []
        cols=r.get('table1_refs',{});refs+=cols.get('controls',[]) if isinstance(cols,dict) else []
        if isinstance(cols,dict) and isinstance(cols.get('control'),str):refs.append(cols['control'])
        refs+=f.get('parameter_refs',[]) if isinstance(f.get('parameter_refs'),list) else []
        refs=list(dict.fromkeys(refs))
        index_rows.append(dict(id=s['record_id'],kind='recent_response_series',source=ref(rp),feedback_sources=[ref(fp)],
            table1_refs=refs,source_record=s,feedback_record=fb,scope='render status and appended feedback separate; original fields exact'))
        case_rows.append(dict(response_id=s['record_id'],table1_refs='|'.join(refs),user_text=text,
            feedback_path=ref(fp)['path'],feedback_sha256=ref(fp)['sha256'],scope='aggregate unless original feedback says otherwise',
            measurement_validated=False,general_rule_validated=False))
    author=REPORT/'li-kan-author-reference-20261011.json'
    index_rows.append(dict(id='PACKET:li-kan-author-reference',kind='descriptive_reference',source=ref(author),feedback_sources=[],
        table1_refs=['PER:S1'],source_record=load(author),scope='matched descriptive case; not isolated causal contrast'))
    assert len([r for r in index_rows if r['kind'].startswith('base_')])==14
    assert len([r for r in index_rows if r['kind']=='recent_response_series'])==8
    assert len({r['id'] for r in index_rows})==len(index_rows)
    all_refs=[r['source'] for r in index_rows]+[p for r in index_rows for p in r['feedback_sources']];check(all_refs)
    index=dict(schema_version=1,date='2026-10-12',status='current_sealed_record_index_with_explicit_gaps',rows=index_rows,
        base_count=14,recent_response_series_count=8,packet_rows_not_independent_feedback_or_samples=True,
        master_conditional_responses_untouched=True,master_table1_definitions_untouched=True,
        measurement_validated=False,general_rule_validated=False,generator=ref(Path(__file__)))
    save(KNOW/(INDEX+'.json'),index)
    csv_rows=[dict(id=r['id'],kind=r['kind'],source_path=r['source']['path'],source_sha256=r['source']['sha256'],
        feedback_paths='|'.join(p['path'] for p in r['feedback_sources']),table1_refs='|'.join(r['table1_refs']),scope=r['scope']) for r in index_rows]
    write_csv(KNOW/(INDEX+'.csv'),csv_rows);write_csv(KNOW/(INDEX+'-table1-cases.csv'),case_rows)
    imd='# 表2补充统一索引与表1案例入口\n\n2026-10-12。旧14主记录保持原字节；最近8响应系列分别绑定技术交付和追加反馈，2E既有反馈包及收口另列。每条source SHA与原结构字段完整保留。索引行不是独立试听次数/新样本；summary不重复计反馈。表1定义与主表数值保持，案例只关联已有实体/参数，不升级通用规律。\n\n|记录|类别|原记录|后续反馈|\n|---|---|---|---|\n'
    for r in index_rows:
        src=ROOT/r['source']['path'];rel=Path('../../../')/src.relative_to(ROOT)
        fb='、'.join(f"[{Path(p['path']).stem}](../../../{p['path']})" for p in r['feedback_sources']) or '见原包'
        imd+=f"|{r['id']}|{r['kind']}|[{src.stem}]({rel.as_posix()})|{fb}|\n"
    imd+=f'\n[结构JSON]({INDEX}.json)、[索引CSV]({INDEX}.csv)、[表1反馈案例CSV]({INDEX}-table1-cases.csv)。全部measurement_validated=false；source unknown/旧阴性/未报维度保持。\n'
    (KNOW/(INDEX+'.md')).write_text(imd,encoding='utf-8',newline='\n')
    status=('当前状态own_F_feedback_closed_layering_design_frozen：2026-10-12“更好了”按交付语境记F相对E聚合改善，未补实感保持/挤尖全解决/绝对接受；'
        '里277明确要求发力渐强再减弱、有层次。已补统一表2索引：旧14原记录/2E反馈包/近8响应系列、表1案例引用，原主表/字段与SHA保持。'
        '自身元音/音乐阶段与现有JSON包络只读复核，下一项冻结F基底里VOIC0→+6→+2→0有限有序包络，TENC/DYN及音高/时钟/声线保持；'
        '2新波形/2新F0预算实际0，G工程未写，不复制作者数组，未采用/Agent未听/通用规律0，原歌音频Skill/作者/旧阴性/抱C/unknown保持，单Agent/CI仅手动。')
    for name in ENTRIES:
        p=ROOT/name;lines=p.read_text(encoding='utf-8').splitlines();ix=[i for i,l in enumerate(lines) if '当前状态own_control_neutral_delivered_pending_listening：' in l];assert len(ix)==1,name
        rel='docs/reports/lastpage/'+NAME+'.md'
        if '/' in name:rel=('../../' if name.startswith('research/') else '../../../')+rel
        lines[ix[0]]=('- ' if lines[ix[0]].startswith('- ') else '')+status+f' 见[F反馈与力度层次]({rel})。'
        if name=='plan.md':
            for i,l in enumerate(lines):
                if l.startswith('下一工作进入逐首更新，先《最后一页》：'):
                    lines[i]='下一工作进入逐首更新，先《最后一页》：F聚合改善反馈已追加，表2近8系列与旧14/2E反馈包统一索引及表1案例入口已补。下一项只执行冻结里277 VOIC渐强回收G（+6UI峰值、自身阶段锚点），两新波形/两新F0预算实际0；TENC/DYN/声线/音乐音素条件保持，检查整句15字邻域与第二句真实音素保持，不自动推广/加量。'
        if name=='docs/knowledge/acoustic-manifestations-20261009/README.md':
            at=next(i for i,l in enumerate(lines) if l=='## 现行目录')
            lines[at:at]=[f'新增当前关联入口：[表2补充统一索引]({INDEX}.md)、[结构JSON]({INDEX}.json)、[表1反馈案例CSV]({INDEX}-table1-cases.csv)。旧14主表保留；近8响应技术交付/追加反馈分别绑定，不推成通用规律。','']
        p.write_text('\n'.join(lines)+'\n',encoding='utf-8',newline='\n')
    check(protected);check(bindings);check(all_refs)
    # Validate JSON fields copied exactly, rather than rewriting older semantics.
    for r in index_rows:
        source=load(ROOT/r['source']['path'])
        if r['kind']=='recent_response_series':assert r['source_record']==source['table2_supplement']
        elif r['kind'].startswith('base_'):assert r['source_record']==next(q for q in source[r['kind'][5:]] if q['id']==r['id'])
        else:assert r['source_record']==source
    gate=subprocess.run([sys.executable,'tools/repository/check_repository.py','--worktree'],cwd=ROOT,capture_output=True,encoding='utf-8')
    (RUN/'logs/repository-gate.log').write_text(gate.stdout+gate.stderr,encoding='utf-8');assert gate.returncode==0,gate.stdout+gate.stderr
    audit=dict(status='passed_with_explicit_feedback_scope_and_stage_response_gaps',source=ref(Path(__file__)),
        protected_references=len(protected),source_bindings=bindings,index_rows=len(index_rows),base_records=14,recent_series=8,
        source_fields_exact=True,feedback_submissions=1,new_word_quality_labels=0,new_models=0,new_waveforms=0,new_PCM_NPZ_reads=0,
        gate=gate.stdout.strip(),agent_heard=False,adoption=False,measurement_validated=False)
    save(RUN/'evaluation/audit.json',audit);save(REPORT/(NAME+'-audit.json'),audit)
    docs=[ref(p) for p in sorted(REPORT.glob(NAME+'*'))]+[ref(p) for p in sorted(KNOW.glob(INDEX+'*'))]
    save(RUN/'completion-manifest.json',dict(status=report['status'],files=[ref(p) for p in sorted(RUN.rglob('*')) if p.is_file()],documents=docs,entries=[ref(ROOT/n) for n in ENTRIES]))
    print(json.dumps(dict(status=report['status'],index_rows=len(index_rows),base_records=14,recent_series=8,new_waveforms=0,gate=audit['gate']),ensure_ascii=False),flush=True)

if __name__=='__main__':main()
