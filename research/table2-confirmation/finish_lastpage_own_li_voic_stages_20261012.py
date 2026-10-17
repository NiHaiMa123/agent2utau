"""Publish G and the actual production knowledge integration; seal all new work."""
import csv
import json
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET
from assemble_lastpage_accepted_baseline_20261011 import ROOT,ENTRIES,load,save,ref,sha,check
from lastpage_own_li_voic_stages_20261012 import RUN,F,runtime
from agent2utau.knowledge import collect_context,validate_context

REPORT=ROOT/'docs/reports/lastpage';NAME='own-li-voic-stages-probe-20261012'
KNOW=ROOT/'docs/knowledge/acoustic-manifestations-20261009';INDEX='table2-layering-delivery-index-20261012'

def csv_write(path,rows):
    with path.open('x',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def main():
    assert not (RUN/'completion-manifest.json').exists() and not (REPORT/(NAME+'.json')).exists()
    gates={k:load(RUN/f'evaluation/{k}-independent-check.json') for k in ['native','fresh','delivery']}
    assert all(g['status']=='passed' for g in gates.values())
    for g in gates.values():check([g['checker']])
    runtime();plan=load(RUN/'design/protocol.json');exe=load(RUN/'fresh/execution.json');pack=load(RUN/'evaluation/delivery-check.json');obs=load(RUN/'observations/results.json')
    assert exe['variance_calls']==exe['acoustic_vocoder_waveforms']==2
    assert not any(gates['fresh']['rows'][0]['feature_clipping'].values()) and obs['actual_F0_calls']==2
    assert load(RUN/'design/knowledge_context.json')==load(RUN/'evaluation/CLI-knowledge-context.json')
    tests=ROOT/'runs/test-results/knowledge-integration-20261012';junit=tests/'full-suite.xml'
    suites=ET.parse(junit).getroot();count=sum(int(s.get('tests','0')) for s in suites.iter('testsuite'));assert count==164
    assert all(int(s.get('failures','0'))==int(s.get('errors','0'))==0 for s in suites.iter('testsuite'))
    words=[]
    for w in obs['windows']:
        if w['role']!='full_vowel':continue
        words.append(dict(word=w['word'],char=w['char'],context=w['context'],manual_action='VOIC-staged+6peak' if w['word']==277 else 'keep F',
            vowel_RMS_change_db=w['G_minus_F']['level_ratio_db'],FCPE_abs_cents_p50=w['G_minus_F']['F0']['FCPE']['abs_cents_p50'],
            RMVPE_abs_cents_p50=w['G_minus_F']['F0']['RMVPE']['abs_cents_p50'],auditory_status='pending' if w['context']==28 else 'real phones PCM retained, no new acceptance'))
    assert len(words)==15;csv_write(REPORT/(NAME+'-words.csv'),words)
    phases=[]
    for w in obs['windows']:
        if not w['role'].startswith('li_'):continue
        phases.append(dict(phase=w['role'],start_s=w['interval_s'][0],end_s=w['interval_s'][1],
            F_RMS_dbfs=w['variants']['F']['level']['dbfs'],G_RMS_dbfs=w['variants']['G']['level']['dbfs'],
            G_minus_F_db=w['G_minus_F']['level_ratio_db'],auditory_force='unknown'))
    assert len(phases)==5;csv_write(REPORT/(NAME+'-stages.csv'),phases)
    table1=['PER:S1','EVT:L2','ACO:L1','PARAM:C11.01']
    outputs=pack['outputs'];supplement=dict(record_id='RESP:LASTPAGE-OWN-LI-VOIC-STAGES-01',status='rendered_checked_pending_human_listening',
        comparison='G-F',intervention='one li277 finite VOIC development/recovery, existing5tick UI100→106→102→100',
        table1_refs=table1,protocol=ref(RUN/'design/protocol.json'),knowledge_receipt=ref(RUN/'evaluation/knowledge_receipt.json'),
        target_word=277,affected_context=28,control_context=29,independent_affected_contexts=1,review_words=list(range(270,285)),
        new_variance_calls=2,new_acoustic_vocoder_waveforms=2,native_cached_technical_contexts=2,sealed_F_reused=True,
        changed_native_VOIC_frames=gates['native']['rows'][0]['changed_voicing_frames'],max_feature_delta=gates['native']['rows'][0]['max_VOIC_model_increment'],
        variance_predictions_exact_F=True,only_final_voicing_changed=True,repeat_exact=True,feature_clipping=0,
        new_F0_calls=2,reused_F_F0_bindings=6,word_rows=words,phase_rows=phases,outputs=outputs,
        response_limit='Only mild relative middle-stage level change; absolute stage RMS still declines from stronger attack. Planned input crescendo is not proven audible force crescendo.',
        new_feedback_count=0,adoption=False,agent_heard=False,measurement_validated=False,general_rule_validated=False)
    save(RUN/'evaluation/table2-supplement.json',supplement)
    integration=dict(status='explicit_knowledge_context_and_compile_gate_implemented',
        CLI='knowledge-context',production_entry='compile-functions schema2',
        requirements=['source SHA and exact record content','one use/reject/extrapolate/unknown decision per retrieved ID','condition-match/rationale/limitations'],
        validation_limit='presence, provenance and decision coverage only; Agent still judges relevance and musical choices',
        schema1='rejected before native/filesystem output; explicit migration needed; sealed legacy inputs unchanged',
        registry_snapshot='context freezes catalogue selection; future active catalogue updates do not rewrite old receipts',
        no_automatic_recipe_selection=True,Skill_unchanged=True,tests_passed=count,test_report=ref(junit),
        CLI_context_exact_research_context=True,this_run_retrieved_ID_count=8,receipt=ref(RUN/'evaluation/knowledge_receipt.json'),
        sources=[ref(ROOT/p) for p in ['src/agent2utau/knowledge.py','src/agent2utau/workflow.py','src/agent2utau/cli.py',
            'tests/contracts/test_knowledge_context.py','tests/contracts/test_workflow.py','docs/workflow.md','docs/guides/knowledge-use-in-production.md']],
        authorized_before_snapshots=ref(RUN/'design/authorized-integration-change.json'))
    report=dict(status='knowledge_integrated_G_delivered_pending_listening',table2_supplement=supplement,knowledge_integration=integration,
        table1_refs=table1,execution=exe,delivery=pack,phase_rows=phases,word_rows=words,
        checks={k:ref(RUN/f'evaluation/{k}-independent-check.json') for k in gates},observations=ref(RUN/'observations/results.json'),
        finite_expectation='Input stage shape verified; absolute RMS did not reverse into a crescendo. Auditory force, coloration and acceptance pending.',
        repairs=['initial pytest temp parent missing:15 setup errors; original JUnit retained, proper parent and rerun15/all164 passed',
            'observer code generation quote/indent syntax failures rejected before any F0 calls; corrected generator, budget2 unchanged'],
        agent_heard=False,adoption=False,measurement_validated=False,general_rule_validated=False)
    save(REPORT/(NAME+'.json'),report)
    phase_table='|阶段|F RMS dBFS|G RMS dBFS|G−F dB|\n|---|---:|---:|---:|\n'
    for p in phases:phase_table+=f"|{p['phase']}|{p['F_RMS_dbfs']:.3f}|{p['G_RMS_dbfs']:.3f}|{p['G_minus_F_db']:+.3f}|\n"
    md=f'''# 最后一页：知识接入与里字VOIC阶段试听G

2026-10-12。用户授权“补齐，还有发声的强弱开始研究并提供试听”。保持Skill、原歌/音频、作者原件、旧封存报告/run及CI手动；本批明确允许更改生产knowledge/workflow/CLI和相关契约测试/文档，修改前原字节冻结，4个既有路径从旧全量保护声明单独登记，不重写旧SHA或冒称这些代码未变。

## 知识实际接入

新增knowledge-context读取公开表1实体/参数和表2条件记录，来源由active-knowledge-sources目录显式列出，不读作者音频/曲线或研究缓存。此轮实际取回8ID，逐条use/reject/extrapolate及当前条件、理由、限制写入计划，来源SHA/原字段/决策覆盖校验通过，CLI实际返回与本runner的包逐字段精确。compile-functions要求schema2 knowledge_context，在输出目录或原生执行前拒绝缺失、过期、伪造字段或漏决策；旧schema1须显式迁移，历史封存不改。知识只约束依据，没有自动选剂量或证明Agent音乐判断正确；无匹配响应可明确absence_reason并保持unknown。

{count}项本机测试通过，包含阻止缺/漏知识先调用原生、来源变化/伪造记录/未知ID/遗漏限制/重复决策/非法泛化拒绝及原编译/音频/Skill等测试。15项专项也通过；初始pytest父临时目录缺失的15 setup errors原JUnit保留，修正环境后重跑，无代码失败被掩盖。详见[制作接入](../../guides/knowledge-use-in-production.md)。更新当前来源目录后新计划读新记录，旧receipt冻结当时目录选择及已绑定来源，不刷新旧实验。

## 里277单因素G

以已获“更好了”的F作工作比较基底，Bright40/Cute60声线与自身音符/所有音高/原生音素/CLR完整时钟保持，只有context28里i元音VOIC有序变化：到达213.0622917s前保持100，自己的主体锚点213.224295s到106，213.4152083s回102，213.5302083s前恢复100，元音213.5854167s退出100。逐段smoothstep零切线、原整数5tick网格采样与UI取整，非作者节点/数组搬运。TENC/BREC/SHFC/DYN保持F，固定输出增益1.5；+6UI是单个有限设计，不是通用力度常数。

原生35帧只在里元音改变voicing，最大模型增量0.72000003，独立采样/进入上升与回收非增通过；其它音素人工输入保持，native与fresh variance输入/三预测、两阶段speaker和vocoder F0精确F。context28 G/G_repeat2套新variance/acoustic/vocoder波形、固定11/101，所有重复精确，fresh只final voicing改变，裁剪0。context29保持封存F贡献，没有新fresh执行；2原生缓存技术上下文另列，2次新双F0及6个旧F数组绑定复用，不增加独立条件。82窗口包括原15字/辅音/两句77窗及里的5阶段。

{phase_table}

**实际响应较轻，绝对阶段RMS仍字头较强、后面减弱，没有验证成声能量已形成渐强。** G在主体相对F只约+0.157/+0.269dB，整里约+0.116dB；VOIC输入按计划上升再回收，不足以宣称听觉发力有层次或更像作者。RMS是电平代理，不等于感知发力/响度；没有为制造目标而额外加量、改DYN/音高、归一化或压缩。新听感待接，如果无可感知变化仍保留有限阴性。

## PCM交付和边界

完整245.577秒研究G人声按34贡献重建，只有context28贡献替换，context29继续F、其它32贡献/抱C保持，DYN0dB/gain1、44100Hz mono PCM24、固定1.5，峰值{pack['peak']:.6f}，无文件削波。原F全PCM重建、G量化/预览和支撑外PCM精确；第二句真实音素与看PCM精确，原89ms共享头padding有{pack['overlap']['shared_padding_changed_samples']}样本微变，终止早于真实AP开始214.313542s，范围列明，未重定时/交叉淡化。

- [G新版两句](../../../{outputs['candidate_preview']['path']})、[F基线](../../../{outputs['original_preview']['path']})：209.4–218.0秒8.6秒，里约3.56–4.19秒。
- [白烁单独参考](../../../{outputs['author_reference']['path']})：当前1.65c已有fresh A，212–220.5秒8.5秒，只作描述比较，非同音乐/时钟的因果对照。
- [完整研究G工程](../../../{outputs['candidate_project']['path']})、[完整研究G人声](../../../{outputs['candidate_full']['path']})：未采用为原发布歌。

已补当前表2索引的新G行和表1关联，技术交付pending与后续反馈分开。下一步只接G−F里字力度发展/回收、实感/挤尖/咬字反馈，不自动扩大剂量或整曲采用。Agent未听，新反馈0，source_unknown106、旧阴性、接受抱C与未报维度保持，measurement_validated=false、通用规律0，单Agent、CI仅手动。

[15字CSV]({NAME}-words.csv)、[阶段CSV]({NAME}-stages.csv)、[JSON]({NAME}.json)、[审计]({NAME}-audit.json)。
'''
    (REPORT/(NAME+'.md')).write_text(md,encoding='utf-8',newline='\n')
    oldindex=load(KNOW/'table2-supplement-index-20261012.json')
    idx=dict(oldindex);idx['rows']=oldindex['rows']+[dict(id=supplement['record_id'],kind='recent_response_series',source=ref(REPORT/(NAME+'.json')),
        feedback_sources=[],table1_refs=table1,source_record=supplement,scope='new G technical delivery, auditory feedback pending')]
    idx.update(recent_response_series_count=9,date='2026-10-12',generator=ref(Path(__file__)),prior_index=ref(KNOW/'table2-supplement-index-20261012.json'))
    save(KNOW/(INDEX+'.json'),idx)
    csv_write(KNOW/(INDEX+'.csv'),[dict(id=r['id'],kind=r['kind'],source_path=r['source']['path'],source_sha256=r['source']['sha256'],
        feedback_paths='|'.join(p['path'] for p in r['feedback_sources']),table1_refs='|'.join(r['table1_refs']),scope=r['scope']) for r in idx['rows']])
    imd='# 表2当前制作接入索引\n\n旧14记录、2E反馈包及近9响应系列；G仍待听感。旧索引/记录字段/反馈SHA保持，新制作入口读取当前来源目录。\n\n|ID|原记录|追加反馈|\n|---|---|---|\n'
    for r in idx['rows']:
        fb='、'.join(f"[{Path(p['path']).stem}](../../../{p['path']})" for p in r['feedback_sources']) or '见原包；G待评'
        imd+=f"|{r['id']}|[{Path(r['source']['path']).stem}](../../../{r['source']['path']})|{fb}|\n"
    imd+=f'\n[CSV]({INDEX}.csv)、[JSON]({INDEX}.json)。索引行不是独立样本；通用规律及测量全面验证仍未通过。\n'
    (KNOW/(INDEX+'.md')).write_text(imd,encoding='utf-8',newline='\n')
    registry=KNOW/'active-knowledge-sources.json';before=RUN/'before/active-knowledge-sources.json';before.write_bytes(registry.read_bytes())
    config=load(registry);config['response_indices']=[ref(KNOW/(INDEX+'.json'))['path']]
    registry.write_text(json.dumps(config,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    newpacket=collect_context(['PER:S1'],['PARAM:C11.01'],[supplement['record_id']]);decisions=[dict(id=r['id'],decision='keep_unknown',reason='New G rendered; feedback pending',condition_match='current own li study',limitations='Not adopted or generalized') for r in newpacket['records']]
    save(RUN/'evaluation/new_G_catalogue_smoke.json',newpacket);save(RUN/'evaluation/new_G_catalogue_receipt.json',validate_context(newpacket,decisions))
    status=('当前状态knowledge_integrated_G_delivered_pending_listening：2026-10-12已补显式knowledge-context与compile-functions schema2门禁，来源SHA/原字段/逐条决策必检、无匹配须unknown，'
        '本轮8ID实际消费，CLI/runner包精确、164本机测试通过，Skill不改；旧schema1须迁移、原字节冻结。'
        '里277 VOIC有序100→106→102→100、35帧/最大0.72，仅final voicing改变，variance/两阶段speaker/音高时钟精确F，2新波形/重复精确、裁剪0。'
        '82窗/2新F0+6旧F绑定与34贡献PCM通过；主体相对+0.16～0.27dB，绝对能量仍字头强后弱，未证明渐强听感。'
        'G/F/作者参考固定1.5交付，G待评未采用、近9系列入当前索引；第二句真实音素/看及其它贡献/抱C保持，共享padding432样本微变范围明确。'
        '原歌音频Skill/作者/旧阴性/unknown保持，Agent未听/通用规律0，单Agent/CI仅手动。')
    for name in ENTRIES:
        p=ROOT/name;lines=p.read_text(encoding='utf-8').splitlines();ix=[i for i,l in enumerate(lines) if '当前状态own_F_feedback_closed_layering_design_frozen：' in l];assert len(ix)==1,name
        rel='docs/reports/lastpage/'+NAME+'.md'
        if '/' in name:rel=('../../' if name.startswith('research/') else '../../../')+rel
        lines[ix[0]]=('- ' if lines[ix[0]].startswith('- ') else '')+status+f' 见[知识接入与里阶段G]({rel})。'
        if name=='AGENTS.md':
            at=next(i for i,l in enumerate(lines) if l.startswith('- 本项目后续由Codex处理'))
            lines[at+1:at+1]=['- 制作/研究计划执行前必须按[知识接入](docs/guides/knowledge-use-in-production.md)生成SHA绑定knowledge_context和逐ID决策；compile-functions只接schema2，研究runner调用同一门禁。新增技术/反馈记录先追加公开报告，再更新active-knowledge-sources显式来源，旧记录/receipt不刷新；没有匹配证据须明确unknown/外推。']
        if name=='plan.md':
            for i,l in enumerate(lines):
                if l.startswith('下一工作进入逐首更新，先《最后一页》：'):lines[i]='下一工作进入逐首更新，先《最后一页》：知识接入/执行前门禁已补，里阶段G已交付，下一步只接G相对F的发力渐强回收/实感/挤尖/咬字反馈。当前实际电平响应轻微，未证明目标听感；不自动加量/改DYN或扩大因素，后续计划必须记录表1/表2来源与决策并更新显式来源索引。'
        if name=='README.md':lines[4:4]=['制作前执行[表1/表2知识接入](docs/guides/knowledge-use-in-production.md)：显式检索并记录条件/采用或拒绝理由，compile-functions schema2执行前校验；Skill保持方法层。','']
        if name=='docs/knowledge/acoustic-manifestations-20261009/README.md':
            at=next(i for i,l in enumerate(lines) if l=='## 现行目录')
            lines[at:at]=[f'制作使用[当前表2索引]({INDEX}.md)与[显式来源目录](active-knowledge-sources.json)，知识接入/门禁见[指南](../../guides/knowledge-use-in-production.md)。旧索引保留原字段；近9系列包含新G待评，不是通用规则。','']
        p.write_text('\n'.join(lines)+'\n',encoding='utf-8',newline='\n')
    runtime();check(list(outputs.values()))
    gate=subprocess.run([sys.executable,'tools/repository/check_repository.py','--worktree'],cwd=ROOT,capture_output=True,encoding='utf-8')
    (RUN/'logs/repository-gate.log').write_text(gate.stdout+gate.stderr,encoding='utf-8');assert gate.returncode==0,gate.stdout+gate.stderr
    scripts=[ref(ROOT/'research/table2-confirmation'/n) for n in ['lastpage_own_li_voic_stages_20261012.py','check_lastpage_own_li_voic_stages_20261012.py',
        'package_lastpage_own_li_voic_stages_20261012.py','observe_lastpage_own_li_voic_stages_20261012.py','check_lastpage_own_li_voic_delivery_20261012.py',Path(__file__).name]]
    audit=dict(status='passed_with_explicit_stage_response_and_auditory_gaps',scripts=scripts,production_integration=integration,
        authorized_existing_path_changes=ref(RUN/'design/authorized-integration-change.json'),protected_references=len(load(RUN/'protected-before.json')),
        runtime_resources=len(load(RUN/'native-inputs/runtime.json')),actual_new_variance_calls=2,actual_new_waveforms=2,
        native_cached_contexts=2,actual_new_F0_calls=2,reused_F_F0_bindings=6,tests_passed=count,gate=gate.stdout.strip(),
        active_index=ref(KNOW/(INDEX+'.json')),actual_new_feedback=0,agent_heard=False,adoption=False,measurement_validated=False,general_rule_validated=False)
    save(RUN/'evaluation/audit.json',audit);save(REPORT/(NAME+'-audit.json'),audit)
    docs=[ref(p) for p in sorted(REPORT.glob(NAME+'*'))]+[ref(p) for p in sorted(KNOW.glob(INDEX+'*'))]+[ref(registry),ref(ROOT/'docs/guides/knowledge-use-in-production.md')]
    save(RUN/'completion-manifest.json',dict(status=report['status'],files=[ref(p) for p in sorted(RUN.rglob('*')) if p.is_file()],documents=docs,entries=[ref(ROOT/n) for n in ENTRIES]))
    print(json.dumps(dict(status=report['status'],tests=count,preview=outputs['candidate_preview'],stage_response=phases,gate=audit['gate']),ensure_ascii=False),flush=True)

if __name__=='__main__':main()
