"""Publish H native DYN response, current table index and immutable delivery seal."""
import copy
import csv
import json
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET
from assemble_lastpage_accepted_baseline_20261011 import ROOT,ENTRIES,load,save,ref,check
from lastpage_own_li_dyn_20261012 import RUN,F,runtime
from agent2utau.knowledge import collect_context,validate_context

REPORT=ROOT/'docs/reports/lastpage';NAME='own-li-DYN-probe-20261012'
KNOW=ROOT/'docs/knowledge/acoustic-manifestations-20261009';INDEX='table2-DYN-delivery-index-20261012'

def csv_write(path,rows):
    with path.open('x',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def main():
    assert not (RUN/'completion-manifest.json').exists() and not (REPORT/(NAME+'.json')).exists()
    gates={k:load(RUN/f'evaluation/{k}-independent-check.json') for k in ['native','processed','delivery']}
    assert all(g['status']=='passed' for g in gates.values())
    for g in gates.values():check([g['checker']])
    runtime();plan=load(RUN/'design/protocol.json');exe=load(RUN/'processed/execution.json');pack=load(RUN/'evaluation/delivery-check.json');obs=load(RUN/'observations/results.json')
    assert exe['new_fixed_seeded_variance_calls']==exe['new_fixed_seeded_synthesis_waveforms']==0 and exe['processed_contribution_repeats']==2
    assert obs['actual_F0_calls']==2 and obs['reused_F_F0_array_bindings']==6 and len(obs['windows'])==83
    outputs=pack['outputs'];check(list(outputs.values()));words=[];phases=[]
    for w in obs['windows']:
        if w['role']=='full_vowel':
            words.append(dict(word=w['word'],char=w['char'],context=w['context'],action='DYN envelope and l preparation' if w['word']==277 else 'keep F',
                vowel_RMS_change_db=w['H_minus_F']['level_ratio_db'],FCPE_abs_cents_p50=w['H_minus_F']['F0']['FCPE']['abs_cents_p50'],
                RMVPE_abs_cents_p50=w['H_minus_F']['F0']['RMVPE']['abs_cents_p50'],auditory_force='pending' if w['word']==277 else 'no new individual label'))
        if w['role'].startswith('li_'):
            phases.append(dict(phase=w['role'],start_s=w['interval_s'][0],end_s=w['interval_s'][1],
                F_RMS_dbfs=w['variants']['F']['level']['dbfs'],H_RMS_dbfs=w['variants']['H']['level']['dbfs'],
                H_minus_F_db=w['H_minus_F']['level_ratio_db'],native_gain_median=w['variants']['H']['native_DYN_gain']['median'],
                auditory_force='unknown'))
    assert len(words)==15 and len(phases)==6;csv_write(REPORT/(NAME+'-words.csv'),words);csv_write(REPORT/(NAME+'-stages.csv'),phases)
    junit=ROOT/'runs/test-results/lastpage-own-li-dyn-20261012/junit.xml';suites=ET.parse(junit).getroot()
    tests=sum(int(s.get('tests','0')) for s in suites.iter('testsuite'));assert tests==11
    assert all(int(s.get('errors','0'))==int(s.get('failures','0'))==0 for s in suites.iter('testsuite'))
    table1=['PER:S1','EVT:L2','ACO:L1','PARAM:C10.01']
    supplement=dict(record_id='RESP:LASTPAGE-OWN-LI-DYN-LAYERS-01',status='processed_checked_pending_human_listening',comparison='H-F',
        table1_refs=table1,protocol=ref(RUN/'design/protocol.json'),knowledge_receipt=ref(RUN/'evaluation/knowledge_receipt.json'),
        intervention='only native DYN finite envelope0→−4→+1.5→0→−1.5→0dB, last40ms l preparation and i277',
        affected_context=28,control_context=29,target_word=277,independent_affected_contexts=1,review_words=list(range(270,285)),
        two_stage_speaker_and_all_model_conditions_exact_F=True,model_phonation_features_changed=False,
        new_fixed_seeded_variance_calls=0,new_fixed_seeded_synthesis_waveforms=0,native_cached_technical_contexts=2,
        native_Core_processed_contribution_repeats=2,native_gain_probe=1,sealed_F_raw_and_predictions_reused=True,
        processed_repeat_exact=True,actual_gain_span_s=gates['processed']['actual_gain_change_span_s'],
        gain_min=gates['processed']['gain_min'],gain_max=gates['processed']['gain_max'],
        digital_stage_RMS_rise_and_recovery=True,perceived_force_or_voicebank_force_changed='unknown: DYN only output gain',
        new_F0_calls=2,reused_F_F0_bindings=6,word_rows=words,phase_rows=phases,outputs=outputs,
        new_feedback_count=0,adoption=False,agent_heard=False,measurement_validated=False,general_rule_validated=False)
    save(RUN/'evaluation/table2-supplement.json',supplement)
    report=dict(status='H_DYN_delivered_pending_listening',table2_supplement=supplement,table1_refs=table1,
        execution=exe,delivery=pack,phase_rows=phases,word_rows=words,
        checks={k:ref(RUN/f'evaluation/{k}-independent-check.json') for k in gates},observations=ref(RUN/'observations/results.json'),
        native_gain_tool=ref(RUN/'native-inputs/dyn-tool-source.json'),runtime_context='prior47 resources unchanged plus4 bound existing levelprobe files; no install/source/Skill modification',
        new_native_neural_inference_count='not instrumented; native cached technical export separate from fixed-seeded reuse',
        F0_boundary='Outside-gain PCM exact even if whole-context detector estimates differ slightly; detector context response is not measured pitch intervention.',
        support_boundary='actual change starts~1.665ms earlier than design prep, ends~3.146ms before vowel end; native5tick interpolation, no hidden crop',
        contracts_passed=tests,test_report=ref(junit),agent_heard=False,adoption=False,measurement_validated=False,general_rule_validated=False)
    save(REPORT/(NAME+'.json'),report)
    table='|阶段|F RMS dBFS|H RMS dBFS|H−F dB|\n|---|---:|---:|---:|\n'
    for p in phases:table+=f"|{p['phase']}|{p['F_RMS_dbfs']:.3f}|{p['H_RMS_dbfs']:.3f}|{p['H_minus_F_db']:+.3f}|\n"
    span=gates['processed']['actual_gain_change_span_s']
    md=f'''# 最后一页：里字DYN强弱包络H

2026-10-12，状态H_DYN_delivered_pending_listening。用户“下一步”执行冻结单个H；G“不行”保留并在7ID知识receipt明确拒绝，不采用G、不增大VOIC。F仅为已获聚合改善的工作比较基底，不冒称发布歌或整曲验收。

## 本次改变与实际原生执行

自己的里277：最后40ms l准备、i入口DYN−4dB，自己主体锚点+1.5dB后回收，再下降阶段−1.5dB并恢复0；UI0/−40/−40/+15/0/−15/0，原整数5tick网格/逐段smoothstep及整数UI编译。声线Bright40/Cute60、全部音高/音乐阶段、歌词/音素/CLR完整时钟、TENC/BREC/VOIC/SHFC精确F。DYN只变输出增益，没有改变声库发声特征，也没有搬运作者曲线/能量数据。

全34part副本只改context28 dyn值、节点xs保持；原生roundtrip声明/曲线精确，phone/完整pitch/两阶段speaker/全部variance和acoustic输入、原生预测与F精确。现有levelprobe-v15程序集与原构建DLL字节相同并绑定源码，调用当前Core真实ExportDynamics/ApplyDynamics；安装/旧build不改、未部署新桥。47原资源SHA保持，4现有DYN工具文件单列绑定。

**新的固定种子variance/acoustic/vocoder合成0**：F原11/101 raw/预测/输入明确封存复用，Core实际处理H/H_repeat两份贡献精确；另ones得到逐样本gain。处理重复不是2个独立合成或条件。2句native缓存技术导出另列，未对native内部神经推理计数作未核实的0声明。独立由实际原生曲线重建振幅/5tick终点/逐样本插值，gain及raw*gain float32逐元素精确，不以Python另一条包络代替工程。增益最小{gates['processed']['gain_min']:.9f}、最大{gates['processed']['gain_max']:.9f}，不触发特殊最小静音。

实际gain≠1共{gates['processed']['changed_samples']}样本，支撑{span[0]:.9f}–{span[1]:.9f}s；原生插值比计划准备早约1.665ms、比元音末尾早约3.146ms，另一个独立PCM门禁限制在一5tick加一样本边界内。l最后约41.665ms受影响，咬字需试听；没有裁切回设计边界伪造精准支撑。其它14元音/面及第二句完整PCM保持，原音符/音素/模型条件不变。

## 阶段响应与试听边界

{table}

入口约−20.222、展开−20.025、主体−19.479，再回收−21.149/−23.703dBFS，五阶段均值呈先增加后降低；这是这次有限包络的数字电平响应，不证明每个瞬时短窗严格单调，也不证明发力/自然度或更像作者。全里RMS相对F约−1.230dB，因为入口减轻；不是整字归一化或音量补偿策略。

83窗包含原15字/辅音/两整句77窗口加里5阶段及l准备1窗。2次新H FCPE/RMVPE，6旧F数组绑定复用；共同有效帧不足3则unknown、不跨无声插值，原raw/mel/发声特征精确F。未改PCM元音仍有检测器约百分之几音分的上下文响应，不能当音高改变；检测器未校准真实发力或F0真值。原生数据/数学通过与听觉效果分开。

## 同增益PCM交付

完整245.577秒研究H由34贡献重建，只有context28有限gain-mask内样本改变；context29独立贡献和完整混合窗口/看、抱C及其它32贡献精确F，原89ms重叠保留且共享padding改变0。F整曲PCM重建/正反组装/H量化、掩码外样本与预览通过，44100Hz mono PCM24、固定1.5，峰值{pack['peak']:.6f}，无文件削波、归一化、压缩或BGM。

- [H新版两句](../../../{outputs['candidate_preview']['path']})、[F基线](../../../{outputs['original_preview']['path']})：209.4–218.0秒8.6秒，里约3.56–4.19秒，l准备约3.52秒。
- [白烁单独参考](../../../{outputs['author_reference']['path']})：沿用当前1.65c已有fresh作者A，212–220.5秒8.5秒，音乐/时钟不同，只作描述参考，H−F才是DYN对照。
- [完整研究H工程](../../../{outputs['candidate_project']['path']})、[完整研究H人声](../../../{outputs['candidate_full']['path']})：未采用为原歌。

本批{tests}项相关PCM契约与独立native/处理/83窗PCM门禁通过，知识receipt/sourceSHA明确消费G否定；新增H加入当前表2索引近10系列及表1PER:S1/EVT:L2/ACO:L1/PARAM:C10.01。下步只接H相对F是否有所需强弱/发力层次，及实感/挤尖/l咬字副作用；新反馈0、Agent未听、全部measurement_validated=false、通用规律0。不自动扫剂量/改音高/加发声通道，原歌曲/音频/Skill/作者原件/旧阴性/抱C/source_unknown106保持，单Agent、CI仅手动。

[15字CSV]({NAME}-words.csv)、[阶段CSV]({NAME}-stages.csv)、[JSON]({NAME}.json)、[审计]({NAME}-audit.json)。
'''
    (REPORT/(NAME+'.md')).write_text(md,encoding='utf-8',newline='\n')
    registry=KNOW/'active-knowledge-sources.json';config=load(registry);old_path=ROOT/config['response_indices'][0];old_index=load(old_path);idx=copy.deepcopy(old_index)
    assert len(idx['rows'])==33
    idx['rows'].append(dict(id=supplement['record_id'],kind='recent_response_series',source=ref(REPORT/(NAME+'.json')),feedback_sources=[],
        table1_refs=table1,source_record=supplement,scope='native DYN processed H delivery; new auditory feedback pending, not new seeded synthesis'))
    idx.update(recent_response_series_count=10,status='current_index_H_DYN_pending_with_G_negative_retained',prior_index=ref(old_path),generator=ref(Path(__file__)))
    save(KNOW/(INDEX+'.json'),idx)
    csvrows=[dict(id=r['id'],kind=r['kind'],source_path=r['source']['path'],source_sha256=r['source']['sha256'],feedback_paths='|'.join(p['path'] for p in r['feedback_sources']),
        table1_refs='|'.join(r['table1_refs']),scope=r['scope']) for r in idx['rows']];csv_write(KNOW/(INDEX+'.csv'),csvrows)
    imd='# 表2当前制作索引：H DYN交付\n\n旧14/2E与近10响应系列原字段和反馈保持，G否定保留、H待评。处理重复/窗口/索引行不是独立合成或样本数。\n\n|ID|原/技术记录|追加反馈|\n|---|---|---|\n'
    for r in idx['rows']:
        fb='、'.join(f"[{Path(p['path']).stem}](../../../{p['path']})" for p in r['feedback_sources']) or '见原包；H待评'
        imd+=f"|{r['id']}|[{Path(r['source']['path']).stem}](../../../{r['source']['path']})|{fb}|\n"
    imd+=f'\n[CSV]({INDEX}.csv)、[JSON]({INDEX}.json)。保留局部/阴性/unknown，不升级通用规则。\n'
    (KNOW/(INDEX+'.md')).write_text(imd,encoding='utf-8',newline='\n')
    config['response_indices']=[ref(KNOW/(INDEX+'.json'))['path']];registry.write_text(json.dumps(config,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    newpacket=collect_context(['PER:S1','EVT:L2'],['PARAM:C10.01'],[supplement['record_id']]);decisions=[dict(id=r['id'],decision='keep_unknown',reason='H new delivery, auditory feedback pending',condition_match='current own li DYN only',limitations='Digital gain change is not perceived force or general recipe') for r in newpacket['records']]
    save(RUN/'evaluation/new_H_catalogue_context.json',newpacket);save(RUN/'evaluation/new_H_catalogue_receipt.json',validate_context(newpacket,decisions))
    status=('当前状态H_DYN_delivered_pending_listening：2026-10-12用户“下一步”执行H，F声线/全部音高/时钟/声学发声输入预测精确保持，'
        '仅里及l准备DYN−4dB→主体+1.5dB再回收；原生曲线/实际Core gain/逐样本乘法/重复精确，0新固定seeded合成、2处理贡献重复/2原生技术上下文分开。'
        '7ID知识receipt保留G否定，47原资源+4DYN工具绑定保持；83窗/2新F0+6旧F数组与34贡献PCM通过，11本机契约通过。'
        '入口−20.2→主体−19.5→后段−21.1/−23.7dBFS为数字包络响应、非听觉发力已通过；实际支撑早1.665ms/尾提前3.146ms范围明确，l咬字待听。'
        'H/F/作者参考固定1.5分开交付，第二句全PCM/看及抱C/掩码外精确，近10系列入表，H待评未采用。'
        '原歌音频Skill/作者/旧阴性/unknown保持，Agent未听/通用规律0，单Agent/CI仅手动。')
    for name in ENTRIES:
        p=ROOT/name;lines=p.read_text(encoding='utf-8').splitlines();ix=[i for i,l in enumerate(lines) if '当前状态G_feedback_closed_DYN_layer_design_frozen：' in l];assert len(ix)==1,name
        rel='docs/reports/lastpage/'+NAME+'.md'
        if '/' in name:rel=('../../' if name.startswith('research/') else '../../../')+rel
        lines[ix[0]]=('- ' if lines[ix[0]].startswith('- ') else '')+status+f' 见[里DYN层次H]({rel})。'
        if name=='plan.md':
            for i,l in enumerate(lines):
                if l.startswith('下一工作进入逐首更新，先《最后一页》：'):lines[i]='下一工作进入逐首更新，先《最后一页》：DYN单因素H已按原生实际增益交付，下一步只接H相对F的强弱/发力层次及实感/挤尖/l咬字反馈。数字阶段能量先升后收，不代表听觉已通过；不自动加剂量/发声通道或改音高，近10系列与G否定已入当前知识索引，H未采用。'
        if name=='docs/knowledge/acoustic-manifestations-20261009/README.md':
            for i,l in enumerate(lines):
                if l.startswith('制作使用[当前表2索引]'):lines[i]=f'制作使用[当前表2索引]({INDEX}.md)与[显式来源目录](active-knowledge-sources.json)，知识接入见[指南](../../guides/knowledge-use-in-production.md)。近10系列包含H待听觉评价及G否定；旧索引/字段/SHA保持，不是通用规则。'
        p.write_text('\n'.join(lines)+'\n',encoding='utf-8',newline='\n')
    runtime()
    for r in old_index['rows']:assert r==next(q for q in idx['rows'] if q['id']==r['id'])
    with (KNOW/(INDEX+'.csv')).open(encoding='utf-8-sig',newline='') as f:assert list(csv.DictReader(f))==[{k:str(v) for k,v in r.items()} for r in csvrows]
    gate=subprocess.run([sys.executable,'tools/repository/check_repository.py','--worktree'],cwd=ROOT,capture_output=True,encoding='utf-8')
    (RUN/'logs/repository-gate.log').write_text(gate.stdout+gate.stderr,encoding='utf-8');assert gate.returncode==0,gate.stdout+gate.stderr
    scripts=[ref(ROOT/'research/table2-confirmation'/n) for n in ['lastpage_own_li_dyn_20261012.py','check_lastpage_own_li_dyn_20261012.py',
        'package_lastpage_own_li_dyn_20261012.py','observe_lastpage_own_li_dyn_20261012.py','check_lastpage_own_li_dyn_delivery_20261012.py',Path(__file__).name]]
    audit=dict(status='passed_with_explicit_DYN_phonation_perception_gaps',scripts=scripts,contracts_passed=tests,contract_report=ref(junit),
        protected_references=len(load(RUN/'protected-before.json')),runtime_original_resources=47,additional_DYN_tools=4,
        new_fixed_seeded_variance_calls=0,new_fixed_seeded_synthesis_waveforms=0,processed_contribution_repeats=2,gain_probe=1,
        native_cached_technical_contexts=2,new_F0_calls=2,reused_F_F0_bindings=6,actual_new_feedback=0,gate=gate.stdout.strip(),
        current_index=ref(KNOW/(INDEX+'.json')),agent_heard=False,adoption=False,measurement_validated=False,general_rule_validated=False)
    save(RUN/'evaluation/audit.json',audit);save(REPORT/(NAME+'-audit.json'),audit)
    docs=[ref(p) for p in sorted(REPORT.glob(NAME+'*'))]+[ref(p) for p in sorted(KNOW.glob(INDEX+'*'))]+[ref(registry)]
    save(RUN/'completion-manifest.json',dict(status=report['status'],files=[ref(p) for p in sorted(RUN.rglob('*')) if p.is_file()],documents=docs,entries=[ref(ROOT/n) for n in ENTRIES]))
    print(json.dumps(dict(status=report['status'],tests=tests,preview=outputs['candidate_preview'],phase_rows=phases,gate=audit['gate']),ensure_ascii=False),flush=True)

if __name__=='__main__':main()

