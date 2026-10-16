"""Publish finite response records after independent gates; seal the new run."""
import csv
import json
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

import numpy as np

from assemble_lastpage_accepted_baseline_20261011 import ROOT, ENTRIES, load, save, ref, check, sha

RUN=ROOT/'runs/experiments/lastpage-conditioned-voicing-20261011'
REPORT=ROOT/'docs/reports/lastpage'
NAME='conditioned-voicing-probe-20261011'


def main():
    assert not (RUN/'completion-manifest.json').exists()
    assert not (REPORT/(NAME+'.json')).exists()
    for kind in ['native','fresh','delivery']:
        assert load(RUN/f'evaluation/{kind}-independent-check.json')['status']=='passed'
    plan=load(RUN/'design/protocol.json');execution=load(RUN/'fresh/execution.json')
    packaging=load(RUN/'evaluation/delivery-check.json');observations=load(RUN/'observations/results.json')
    check(list(packaging['outputs'].values()))
    check(load(RUN/'evaluation/fresh-independent-check.json')['sources'])
    check([load(RUN/'evaluation/fresh-independent-check.json')['checker']])
    check([plan['baseline'],plan['candidate'],plan['previous_plan']])
    tests=ROOT/'runs/test-results/lastpage-conditioned-voicing-20261011'
    assert not tests.exists();tests.mkdir(parents=True)
    env=os.environ.copy();env['PYTHONIOENCODING']='utf-8'
    (tests/'system-temp').mkdir();env['TEMP']=env['TMP']=str(tests/'system-temp')
    result=subprocess.run([sys.executable,'-m','pytest','-q',
        'tests/contracts/test_controlled_probe.py','tests/contracts/test_shfc_pcm_research.py',
        'tests/contracts/test_shfc_native_preflight.py',
        '--basetemp',str(tests/'pytest-temp'),'-o','cache_dir='+str(tests/'pytest-cache'),
        '--junitxml',str(tests/'junit.xml')],cwd=ROOT,env=env,capture_output=True,encoding='utf-8')
    (RUN/'logs/contracts.log').write_text(result.stdout+result.stderr,encoding='utf-8')
    assert result.returncode==0,result.stdout+result.stderr
    suites=ET.parse(tests/'junit.xml').getroot()
    passed=sum(int(t.get('tests','0')) for t in suites.iter('testsuite'))
    control=ROOT/'docs/knowledge/acoustic-manifestations-20261009/control-details.csv'
    atom=ROOT/'docs/knowledge/acoustic-manifestations-20261009/atomic-manifestations.csv'
    with control.open(encoding='utf-8-sig',newline='') as f:controls=list(csv.DictReader(f))
    with atom.open(encoding='utf-8-sig',newline='') as f:atoms=list(csv.DictReader(f))
    assert next(r['id'] for r in controls if r['abbreviation']=='voic')=='PARAM:C11.01'
    assert any(r['id']=='PER:S1' for r in atoms)
    rows=[]
    for action in plan['actions']:
        w=action['word']
        full=next(r for r in observations['windows'] if r['word']==w and r['role']=='full_vowel')
        core=next(r for r in observations['windows'] if r['word']==w and r['role']=='core15_85')
        ch=core['variants']
        row=dict(word=w,char=action['char'],context=action['context'],action=action['action'],additive_VOIC_UI=action['additive_UI'],
            executed='native_and_seeded_checked',A_voicing_core_median=ch['A']['final_features']['voicing']['median'],
            B_voicing_core_median=ch['B']['final_features']['voicing']['median'],
            vowel_RMS_change_db=full['B_minus_A']['level_ratio_db'],new_user_solidity_label='pending',
            new_break_articulation_loudness_labels='unknown')
        for detector in ['FCPE','RMVPE']:
            f=full['B_minus_A']['F0'][detector]
            row.update({detector+'_valid_pair_frames':f['valid_pair_frames'],detector+'_abs_cents_p50':f['abs_cents_p50'],
                detector+'_max_abs_cents':f['max_abs_cents']})
        rows.append(row)
    assert len(rows)==15 and sum(r['additive_VOIC_UI']>0 for r in rows)==5
    with (REPORT/(NAME+'-words.csv')).open('x',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    table1=dict(perception='PER:S1',control='PARAM:C11.01',sources=[ref(control),ref(atom)],
        examples='original A aggregate airy, kan283 original solid, new B pending; no individual airy labels inferred')
    table2=dict(record_id='RESP:LASTPAGE-CONDITIONED-VOIC-01',comparison='B-A',status='rendered_checked_pending_human_listening',
        protocol=ref(RUN/'design/protocol.json'),baseline=plan['baseline'],candidate=packaging['outputs']['candidate_project'],
        intervention='five finite additive VOIC envelopes on original Normal75/Classic25; project declared max200->215, doses unchanged',
        contexts=[28,29],affected_contexts=[28],selected_words=plan['selected_words'],scope_words=plan['scope_words'],
        independent_contexts=2,independent_affected_contexts=1,seeded_same_input_repeats=4,waveforms=8,
        both_stages_speaker='Normal75/Classic25',changed_final_input_channels=['voicing'],other_predictions_inputs_exact=True,
        real_native_changed_frames=152,feature_clipping=0,manual_doses={str(a['word']):a['additive_UI'] for a in plan['actions'] if a['additive_UI']},
        actual_F0_detection_calls=8,actual_output_F0_fixed='unknown: detectors have limited differences',
        new_user_feedback_count=0,adoption=False,measurement_validated=False,general_rule_validated=False,
        outputs=packaging['outputs'],word_response_rows=rows,overlap_scope=packaging['second_context'])
    save(RUN/'evaluation/table2-supplement.json',table2)
    report=dict(status='conditioned_voicing_delivered_pending_listening',table1_refs=table1,table2_supplement=table2,
        protocol=ref(RUN/'design/protocol.json'),execution=execution,delivery=packaging,word_rows=rows,
        native_check=ref(RUN/'evaluation/native-independent-check.json'),
        fresh_check=ref(RUN/'evaluation/fresh-independent-check.json'),
        PCM_observation_check=ref(RUN/'evaluation/delivery-independent-check.json'),
        finite_observations=ref(RUN/'observations/results.json'),observation_windows=len(observations['windows']),
        prior_feedback='Bright25 remains airy, no deterioration reported; not adopted',
        execution_repairs=['initial range200 compile rejected; explicit max215 preserved by native roundtrip, no dose clipping',
            'checker syntax and final logging import repaired; no changed candidate',
            'VOIC independent reconstruction uses local float32(sampleUI-100)*12/100, exact equality retained',
            'mixed context29 head padding includes preceding tail; independent29 wave and real phones remain exact; failed package retained'],
        source_unknown106_retained=True,agent_heard=False,contracts_passed=passed,
        scope='existing-song development, one changed full phrase plus one exact control phrase; full carrier contains32 other retained contexts',
        general_rule_validated=False,measurement_validated=False,
        next='receive same-gain B/A listening solidity, connection, break/articulation/loudness; no automatic extra candidate/dose')
    save(REPORT/(NAME+'.json'),report)
    selected=[r for r in rows if r['additive_VOIC_UI']]
    table='| 字/ID | 增量VOIC | 元音RMS差dB | FCPE差p50/max(c) | RMVPE差p50/max(c) |\n|---|---:|---:|---:|---:|\n'
    for r in selected:
        table+=f"| {r['char']}/{r['word']} | +{r['additive_VOIC_UI']} | {r['vowel_RMS_change_db']:+.3f} | {r['FCPE_abs_cents_p50']:.3f}/{r['FCPE_max_abs_cents']:.3f} | {r['RMVPE_abs_cents_p50']:.3f}/{r['RMVPE_max_abs_cents']:.3f} |\n"
    outputs=packaging['outputs']
    md=f'''# 最后一页：有限VOIC候选与两完整句交付

2026-10-11。状态：conditioned_voicing_delivered_pending_listening。用户“下一步”授权执行上轮准备的单候选。已否决的Bright25路线收口；本轮原Normal75/Classic25保持。

第一句“想把你抱进身体里面”中五个元音叠加有限VOIC，15字台账完整；想/抱/身/体输入保持，第二句“不敢让你看见”作为完整保持对照。补偿参考−44、比例0.5、特征增量上限3是Agent的有限设计，不是听觉阈值、逐字负标签或白烁拟合。原音高/音素/人工气声与张力/SHFC/DYN和两阶段speaker保持。自选慢线性建立、保持和退出，原5tick整数网格、元音内零边界，同元音延续不重启。

编译第一次被范围200拒绝：你272原VOIC190叠加25需要215。失败快照保留；仅新工程明确设上限215，原定五剂量未改，原生roundtrip表达声明与曲线精确保留。独立读回证明仅五元音152帧voicing改变，实际增量在五段支撑并集内，非目标辅音/AP/SP输入保持；模型特征裁剪0。精确核查原生乘12再除100的float32顺序，检查器初始算术误差、语法和输出日志修正记录保留，未放宽断言。

两完整上下文各A/A_repeat/B/B_repeat，固定variance11/acoustic101，8次新variance及8套acoustic/vocoder波形；原生缓存4套技术参考另列，不混计。原A完整预测/输入/波形与旧seeded记录精确；重复、两阶段speaker、三预测、variance输入、vocoder F0精确，fresh仅第一句最终voicing改变；第二句fresh输入/mel/raw PCM完全相同。

{table}
上述数值是有限技术响应，RMS不是感知响度或收实验收，检测F0不是已校准真值。共77窗口包含15字主体/入口/退出、可定位声母和两完整上下文，30/50ms窗、5ms步；8次双F0检测只取共同有声、有限正值帧，不跨无声插值。其它输入不变也不保证第一句其它字或声母的声学输出完全不变，邻域/副作用仍须试听。

完整245.577秒人声由32句旧贡献及2句新B贡献组装，实际仅context28贡献改变；context29 B=A。44100Hz mono PCM24、原生DYN及固定增益1.5，峰值{packaging['peak']:.6f}，无归一化/压缩/BGM。独立重建全部34贡献与PCM量化、原基线重建、正反组装、预览截取及原抱C通过。输出outside context28贡献支撑精确。

两句原生波形有89ms重叠，context29头部padding含上一句的新尾帧；整曲该padding的3764个样本变化。其变化结束214.309456秒，早于第二句首个真实AP开始214.313542秒；第二句所有真实音素至尾部、六个元音及“看”的整曲PCM精确保持。原“整段context29混合窗口精确”的组装断言被拒绝且失败WAV保留，本轮明确独立贡献与共享padding的范围，未裁切波形或另改控制。已有“看”偏实标签保持，不扩大为全句验收。

- [候选B两句](../../../{outputs['candidate_preview']['path']})：209.4–218.0秒，里约3.56秒、看约6.93秒。
- [原A两句](../../../{outputs['original_preview']['path']})。
- [白烁独立参考](../../../{outputs['author_reference']['path']})：原件不变，沿用上轮当前1.65c参考，非历史1.56录音。
- [完整B人声](../../../{outputs['candidate_full']['path']})、[完整B工程](../../../{outputs['candidate_project']['path']})：仅第一句改变，未采用、未宣称整曲修复。

反馈任务是第一句是否更实/连贯，是否出现破音、咬字/响度副作用；第二句为保持对照。Agent未听，新反馈0，未报维度unknown。试听后接受或收口，不自动加量或追加候选。表1PER:S1与PARAM:C11.01绑定本例，表2补充RESP:LASTPAGE-CONDITIONED-VOIC-01登记B−A；这是1个受影响完整上下文/5元音的开发对照，重复不增加独立条件，不是新留出或通用规律。全部measurement_validated仍false。源unknown106、抱C及原歌曲/音频/Skill/作者原件保持；单Agent、CI仅手动。

{passed}项相关契约测试通过，独立native/fresh/PCM与双F0数组检查通过。详见[15字台账]({NAME}-words.csv)、[JSON]({NAME}.json)、[审计]({NAME}-audit.json)。
'''
    (REPORT/(NAME+'.md')).write_text(md,encoding='utf-8',newline='\n')
    status=('当前状态conditioned_voicing_delivered_pending_listening：2026-10-11用户“下一步”后执行单个原声线VOIC候选，'
        '第一句五元音+10/+25/+25/+11/+12、15字台账完整；范围200越界拒绝后新工程显式215读回通过，剂量不裁剪。'
        '5tick/两阶段speaker/五段152帧隔离与8套固定种子新波形/原A/重复/三预测精确，裁剪0。'
        '第二句独立输入/PCM及所有真实音素/看保持，整曲共享头padding89ms包含前句新尾帧、范围明确；抱C及其它32句保持。'
        '77有限窗口/8次双F0与PCM组装检查通过、仅代理；同固定1.5分开交付B/A/白烁参考，候选未采用、反馈待接、Agent未听/通用规律0。'
        '原歌曲/音频/Skill不改，单Agent/CI仅手动，不自动追加或加量。')
    for name in ENTRIES:
        p=ROOT/name;lines=p.read_text(encoding='utf-8').splitlines()
        ids=[i for i,l in enumerate(lines) if '当前状态voice_baseline_feedback_closed_next_voicing_planned：' in l]
        assert len(ids)==1,name
        relative='docs/reports/lastpage/'+NAME+'.md'
        if '/' in name:relative=('../../' if name.startswith('research/') else '../../../')+relative
        lines[ids[0]]=('- ' if lines[ids[0]].startswith('- ') else '')+status+f' 见[有限VOIC候选]({relative})。'
        for i,line in enumerate(lines):
            if name=='plan.md' and line.startswith('下一工作进入逐首更新，先《最后一页》：'):
                lines[i]='下一工作进入逐首更新，先《最后一页》：单个有限VOIC候选已交付，下一步接第一句虚实/连贯及破音、咬字/响度反馈；第二句看所在真实音素PCM保持作对照。根据本候选结果接受或收口，不自动加量/追加候选；旧阴性及unknown保持，不宣布整曲或通用规律通过。'
        p.write_text('\n'.join(lines)+'\n',encoding='utf-8',newline='\n')
    check(load(RUN/'protected-before.json'))
    for path,digest in load(RUN/'native-inputs/runtime.json').items():assert sha(Path(path))==digest,path
    # Exact public CSV/JSON scalar correspondence, not an auditory test.
    with (REPORT/(NAME+'-words.csv')).open(encoding='utf-8-sig',newline='') as f:csv_rows=list(csv.DictReader(f))
    assert len(csv_rows)==len(rows)
    assert all(all((float(c[k])==v if isinstance(v,(int,float)) else c[k]==v) for k,v in r.items()) for c,r in zip(csv_rows,rows))
    gate=subprocess.run([sys.executable,'tools/repository/check_repository.py','--worktree'],cwd=ROOT,capture_output=True,encoding='utf-8')
    (RUN/'logs/repository-gate.log').write_text(gate.stdout+gate.stderr,encoding='utf-8')
    assert gate.returncode==0,gate.stdout+gate.stderr
    scripts=[ROOT/'research/table2-confirmation'/n for n in ['lastpage_conditioned_voicing_20261011.py',
        'check_lastpage_conditioned_voicing_20261011.py','check_lastpage_conditioned_voicing_delivery_20261011.py',
        'observe_lastpage_conditioned_voicing_20261011.py','finish_lastpage_conditioned_voicing_20261011.py']]
    rejected=ROOT/'runs/research/lastpage-conditioned-voicing-rejected-compile-20261011'
    audit=dict(status='passed_with_explicit_auditory_gaps',contracts_passed=passed,contract_report=ref(tests/'junit.xml'),
        protected_files=len(load(RUN/'protected-before.json')),protected_unique_paths=len({r['path'] for r in load(RUN/'protected-before.json')}),
        runtime_resources=len(load(RUN/'native-inputs/runtime.json')),scripts=[ref(p) for p in scripts],
        rejected_preparation=[ref(p) for p in sorted(rejected.rglob('*')) if p.is_file()],
        gate=gate.stdout.strip(),actual_seeded_variance_calls=8,actual_seeded_waveforms=8,
        native_cache_reference_waveforms=4,F0_calls=8,independent_changed_contexts=1,candidates=1,
        actual_new_feedback=0,agent_heard=False,adoption=False,measurement_validated=False,general_rule_validated=False,
        public_csv_json_exact=True,old_song_audio_Skill_unchanged=True,source_unknown106_retained=True)
    save(RUN/'evaluation/audit.json',audit);save(REPORT/(NAME+'-audit.json'),audit)
    save(RUN/'completion-manifest.json',dict(status=audit['status'],
        files=[ref(p) for p in sorted(RUN.rglob('*')) if p.is_file()],
        documents=[ref(p) for p in sorted(REPORT.glob(NAME+'*'))],entries=[ref(ROOT/n) for n in ENTRIES]))
    print(json.dumps(dict(status=report['status'],tests=passed,preview=outputs['candidate_preview'],gate=audit['gate']),ensure_ascii=False),flush=True)


if __name__=='__main__':main()
