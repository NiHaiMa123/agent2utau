"""Publish bounded DYN response and current voice-feedback listening status."""
import copy,csv,json,os,subprocess,sys
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np
from review_lastpage_v03_volume_20261014 import ROOT,RUN,V03,BASE,KNOW,REPORT,ENTRIES,NAME as FEEDBACK_NAME,INDEX as FEEDBACK_INDEX,load,save,ref,sha,check
from lastpage_v04_dyn_envelope_20261014 import runtime
from agent2utau.knowledge import collect_context,validate_context

NAME='v04-native-DYN-voice-recovery-20261014'
INDEX='table2-v04-DYN-delivery-index-20261014'
ID='RESP:LASTPAGE-V03-DYN-RECOVERY-01'

def csv_write(path,rows):
    with path.open('x',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def main():
    assert not (RUN/'completion-manifest.json').exists()
    gates={k:load(RUN/f'evaluation/{k}-independent-check.json') for k in ['native','processed','delivery']}
    assert all(g['status']=='passed' for g in gates.values());check([g['checker'] for g in gates.values()])
    check(load(RUN/'protected-before.json'));runtime()
    pack=load(RUN/'evaluation/delivery-check.json');metrics=load(RUN/'observations/v04-volume-comparison.json');review=load(RUN/'observations/envelope-review.json')
    plan=load(RUN/'design/protocol.json');check(list(pack['outputs'].values()))
    junit=ROOT/'runs/test-results/lastpage-v04-dynamic-envelope-20261014/junit-complete.xml';suites=ET.parse(junit).getroot()
    count=sum(int(s.get('tests','0')) for s in suites.iter('testsuite'));assert count==164
    assert all(int(s.get('failures','0'))==int(s.get('errors','0'))==0 for s in suites.iter('testsuite'))
    rows=[dict(word=w['word'],char=w['char'],context=w['context'],source_unknown=w['source_unknown'],
        in_user_interval=w['in_feedback_interval'],A_rms_dbfs=w['old_rms_dbfs'],B_rms_dbfs=w['new_rms_dbfs'],delta_db=w['rms_delta_db'],
        A_30ms_p10=w['A_windows']['30'].get('p10_dbfs'),B_30ms_p10=w['B_windows']['30'].get('p10_dbfs'),
        A_50ms_p10=w['A_windows']['50'].get('p10_dbfs'),B_50ms_p10=w['B_windows']['50'].get('p10_dbfs'),listening='pending; no new per-word labels') for w in metrics['words']]
    csv_write(REPORT/(NAME+'-words.csv'),rows)
    targets=[r for r in rows if r['in_user_interval']]
    supplementary=dict(record_id=ID,status='native_DYN_only_delivered_pending_human_listening',date='2026-10-14',
        type='controlled_post_vocoder_amplitude_revision',table1_refs=['ACO:L1','EVT:L2','PER:S1','PARAM:C10.01'],
        user_feedback_source=ref(REPORT/(FEEDBACK_NAME+'.json')),feedback_submissions=1,feedback_intervals=3,
        protocol=ref(RUN/'design/protocol.json'),knowledge_receipt=ref(RUN/'evaluation/execution-knowledge-receipt.json'),
        intervention='Only native DYN4 independently designed phrase envelopes; no note/pitch/voice/phonation/model changes',
        changed_contexts=[11,22,23,25],new_variance_calls=0,new_acoustic_vocoder_waveforms=0,new_F0_calls=0,
        raw34_current_v03_SHA_bound_reused=True,processed_primary=34,unity_probes=34,repeated_processed=4,repeat_exact=True,
        all318_vowels_early_middle_late_and30_50ms_reviewed=True,changed_vowel_records=sum(r['delta_db']!=0 for r in rows),
        unchanged_vowel_records=sum(r['delta_db']==0 for r in rows),original_J_context28_29_PCM_exact=True,
        accepted_bao_C_raw_phonation_exact=True,bao_final_amplitude_changed=True,
        AP_SP_core_protection=ref(RUN/'evaluation/AP-SP-protection.json'),outside_native_sample_support_PCM_exact=True,
        native_sample_change_support=gates['processed']['rows'],
        maximum_requested_DYN_dB=4,per_target_word_level_changes=targets,
        fixed_vocal_gain=1.5,common_mix_margin=.9,original_backing_bytes_exact=True,BGM_relation_research=False,
        new_vocal_peak=pack['peak'],new_mix_peak=pack['mix_peak'],outputs=pack['outputs'],AB_clips=pack['AB_clips'],
        response_limit='Positive output-envelope support, not regenerated force/solidity/texture. Weak ni224 retains lower amplitude even after4dB; no uniform vowel loudness target.',
        old_H_negative='Do not repeat early -4dB weakening; old negative does not prove all DYN envelopes ineffective',
        old_G_I_negatives_retained=True,source_unknown_words=[106],new_listening_feedback=0,adoption=False,
        agent_heard=False,full_song_accepted=False,measurement_validated=False,general_rule_validated=False)
    save(REPORT/(NAME+'.json'),dict(status='v03_volume_feedback_recorded_native_DYN_v04_delivered_pending_listening',table2_supplement=supplementary,
        native_check=ref(RUN/'evaluation/native-independent-check.json'),processed_check=ref(RUN/'evaluation/processed-independent-check.json'),
        delivery_check=ref(RUN/'evaluation/delivery-independent-check.json'),
        all_word_review=ref(RUN/'observations/envelope-review.json'),all_word_comparison=ref(RUN/'observations/v04-volume-comparison.json'),
        tests=dict(passed=count,junit=ref(junit)),skill_changed=False,model_inputs_changed=False,
        checker_versions=dict(early_native=ref(RUN/'logs/native-check-before-layout-fields.json'),early_checker=ref(RUN/'logs/checker-before-layout-fields.py.txt'),
            reason='Added explicit process-layout clock fields before process execution; reran native check with final file; all active checks bind final SHA'),
        initial_test_selection_error='Requested non-existing tests/contracts/test_knowledge.py and tests/unit/test_controlled_probe.py; no tests ran. Actual full suite164 passed; no test weakening.'))
    table='|字ID/字|v03 RMS dBFS|v04 RMS dBFS|变化dB|\n|---|---:|---:|---:|\n'
    for r in targets:table+=f"|{r['word']}/{r['char']}|{r['A_rms_dbfs']:.3f}|{r['B_rms_dbfs']:.3f}|{r['delta_db']:+.3f}|\n"
    (REPORT/(NAME+'.md')).write_text(f'''# v04：人声入口与情绪副歌原生DYN承托

2026-10-14。用户指出v03的1:26–1:28突然变小、3:03–3:10副歌最有情绪处强度没顶上去且相对变小、3:16–3:19变小，并明确“就是人声小了，和bgm，混音这些没关系”。一次反馈/三个范围原话已追加，不补造窗口所有字的负标签。

## 当前诊断与选择

对全部318元音核核查原始声/最终声、早中晚、30/50ms窗口及5ms步长、当前预测与实际DYN。三个范围的DYN均为1，未被曲线主动压低；弱原始输出中存在稳定主体或持续下降。223把到224你的整字能量下降约6.73dB，224后段更低；229里/230面及234你也弱，体228/不231明显较强。“强度”与RMS不同，这些数据不证明某一预测通道是病因。不是伴奏/混音比例诊断。

保持音高、音符、音素、两阶段speaker、TENC/BREC/VOIC/SHFC与当前预测/声码器波形精确v03；只选原生DYN输出包络。ctx11在“如果这”入口承托并回到原后/的；ctx22从把推进，在弱你最多+4dB，抱保持已接受原始音色，体少加、里/面继续承载后回收；ctx23不保持，敢/让/你承托、看/见回收；ctx25第二个“如果”最多约+3dB后逐步减到原后/的。四套具体独立quintic节点见protocol与compiled-DYN，现有5tick网格整数编码，不逐帧反推RMS、不逐字归一化，不加大旧G/I发声剂量，也不重复旧H的字核先减4dB形状。

## 实际执行与有限响应

原生完整音高/phones精确v03，工程只有四个part的DYN ys变。独立节点多项式和34个原生DYN振幅数组通过。当前34份原始声SHA绑定复用；Core处理34主波形、34单位波形与4重复，逐样点DYN插值、乘法和重复全部精确。30未改上下文与所有实际改动支撑之外PCM精确；AP/SP核心8段增益为1（边缘10ms另界定），源unknown106保持。J28/29输出精确v03；抱C底层原始声/发声保持，但其最终振幅在本次情绪承托中改变，不冒称其输出PCM仍等于旧C。

{table}

全318记录有25字输出变化、293字保持；保留词内动态和正常收尾。224你低分位30ms p10从约−30.07变−26.07dBFS，仍偏低；本候选没有承诺消除所有弱发声或给全部元音同样响度。DYN只提高可听能量，不证明发力、情绪或磨砂质感已经恢复。

新完整245.577s纯人声固定1.5/PCM24，峰值{pack['peak']:.9f}。原伴奏字节、相对比例、公共0.9余量都保持，工程/混音峰值检查通过（{pack['mix_peak']:.9f}），不开展BGM关系研究。三个纯人声A→0.5s静音→B对照分别覆盖85.6–89.4、181.9–190.9、195.6–199.8；所有对照同固定增益，A直接来自v03，B来自原生DYN新v04，没有归一化。

新variance/acoustic/vocoder0、F0检测器新推理0。旧v03F0只作来源参照，不冒称新检测输出完全相等。独立全PCM重建/三组裁切/318行检查通过；本机164测试通过。初次定向测试文件名错误未执行测试，完整现行目录重跑通过；检查器早期版本与记录保留，最终原生/处理/交付检查均绑定最终源码SHA。Skill、旧工程、旧音频、作者、阴性与unknown保持，单Agent/CI手动。

表2追加一条DYN单通道有限响应，39行总索引；用户新试听0，adoption/measurement_validated/通用规律仍false。下一步只接本三组试听：“声音是否撑住、该处情绪强度与自然层次是否到位”，不自动继续抬增益或换发声剂量。
''',encoding='utf8')
    idx=copy.deepcopy(load(KNOW/(FEEDBACK_INDEX+'.json')));idx['rows'].append(dict(id=ID,kind='post_vocoder_DYN_response',source=ref(REPORT/(NAME+'.json')),source_record=supplementary,feedback_sources=[]))
    idx.update(status='v04_DYN_delivered_pending_listening',generator=ref(Path(__file__)),prior_index=ref(KNOW/(FEEDBACK_INDEX+'.json')),
        output_envelope_revision_records=1,recent_response_series_count=12)
    save(KNOW/(INDEX+'.json'),idx)
    csv_write(KNOW/(INDEX+'.csv'),[dict(id=r['id'],kind=r.get('kind','response'),source_path=r['source']['path'],source_sha256=r['source']['sha256'],measurement_validated=False) for r in idx['rows']])
    (KNOW/(INDEX+'.md')).write_text('# v04原生DYN试听索引\n\n39行，原38保持且v03反馈保留，新增一条四上下文输出包络记录。12旧近期研究系列、1整曲生产记录与1本次包络记录分列，不把318观察或三个时间范围当独立听觉接受。\n',encoding='utf8')
    registry=load(KNOW/'active-knowledge-sources.json');registry['response_indices']=[(KNOW/(INDEX+'.json')).relative_to(ROOT).as_posix()]
    (KNOW/'active-knowledge-sources.json').write_text(json.dumps(registry,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    packet=collect_context(['ACO:L1','EVT:L2','PER:S1'],['PARAM:C10.01'],[ID,'RESP:LASTPAGE-J-METHOD-WHOLE-SONG-01'])
    decisions=[dict(id=r['id'],decision='keep_unknown' if r['id']==ID else 'use',reason='Current voice feedback and isolated output amplitude response bound; new sound listening pending.',
        condition_match='v04 only4 DYN envelopes; all model conditions exactv03.',limitations='Technical amplitude response is not emotional force or texture acceptance.') for r in packet['records']]
    save(RUN/'evaluation/current-knowledge-roundtrip.json',dict(packet=packet,receipt=validate_context(packet,decisions)))
    status='当前状态v03_volume_feedback_recorded_native_DYN_v04_delivered_pending_listening：2026-10-14用户指出1:26–1:28、3:03–3:10情绪副歌、3:16–3:19人声偏小，并明确与BGM/混音关系无关。一次三范围反馈已记录；318元音核原始/最终/早中晚/30与50ms复核，目标原DYN均1。仅ctx11/22/23/25四条原生DYN正向承托，最多4dB，保持音乐/声线/预测/原始声；34主+34单位+4重复Core处理、音高phones/逐样点增益/PCM/164测试通过。25字输出变化、293字保持，J28/29PCM精确v03，抱C原始发声保持但此次输出增益改变。三组同1.5纯人声A→B及新v04整曲/工程已交付，旧伴奏/比例/公共0.9余量保持；新模型/F0推理0，Skill与旧原件/阴性/unknown保持。39索引、Agent未听，力度/自然层次待用户试听，通用规律0；单Agent/CI仅手动。'
    for name in ENTRIES:
        p=ROOT/name;lines=p.read_text(encoding='utf8').splitlines(keepends=True);count=0
        relative=Path(os.path.relpath(REPORT/(NAME+'.md'),p.parent)).as_posix()
        for i,line in enumerate(lines):
            if '当前状态whole_song_J_method_v03_rendered_checked_pending_listening：' in line:
                lines[i]=('- ' if line.startswith('- ') else '')+status+f' 见[v04人声承托记录]({relative})。\n';count+=1
            if line.startswith('下一工作进入逐首更新，先《最后一页》：'):
                lines[i]='下一工作进入逐首更新，先《最后一页》：已记录三个时段的人声小/情绪副歌强度反馈，v04仅原生DYN承托的三组同增益纯人声A/B已交付；下一步接本三组与整曲反馈，再按实际未解决的音量或发声问题决定候选，不自动增大剂量或研究BGM关系。\n'
        assert count==1,name;p.write_text(''.join(lines),encoding='utf8')
    result=subprocess.run([sys.executable,str(ROOT/'tools/repository/check_repository.py'),'--worktree'],cwd=ROOT,capture_output=True,encoding='utf8')
    (RUN/'logs/repository-gate.log').write_text(result.stdout+result.stderr,encoding='utf8');assert result.returncode==0,result.stderr
    save(RUN/'evaluation/repository-gate.json',json.loads(result.stdout))
    check(load(RUN/'protected-before.json'));runtime();check([g['checker'] for g in gates.values()])
    wf=(ROOT/'.github/workflows/ci.yml').read_text(encoding='utf8');assert 'workflow_dispatch' in wf and not any(k in wf for k in ['push:','pull_request:','schedule:'])
    documents=[REPORT/(NAME+s) for s in ['.md','.json','-words.csv']]+[REPORT/(FEEDBACK_NAME+s) for s in ['.md','.json']]+[KNOW/(INDEX+s) for s in ['.md','.json','.csv']]+[KNOW/(FEEDBACK_INDEX+s) for s in ['.md','.json']]+[KNOW/'active-knowledge-sources.json']
    implementation=[Path(__file__),ROOT/'research/table2-confirmation/review_lastpage_v03_volume_20261014.py',ROOT/'research/table2-confirmation/lastpage_v04_dyn_envelope_20261014.py',ROOT/'research/table2-confirmation/check_lastpage_v04_dyn_20261014.py',ROOT/'research/table2-confirmation/package_lastpage_v04_dyn_20261014.py']
    save(RUN/'completion-manifest.json',dict(status='technical_delivery_complete_pending_listening',files=[ref(p) for p in sorted(RUN.rglob('*')) if p.is_file()],
        documents=[ref(p) for p in documents],entries=[ref(ROOT/n) for n in ENTRIES],implementation=[ref(p) for p in implementation],published=[pack['outputs']['published']],
        tests=ref(junit),protected_count=len(load(RUN/'protected-before.json')),new_model_calls=0,new_auditory_feedback=0,agent_heard=False,measurement_validated=False,general_rule_validated=False))
    print('v04 sealed;39-row knowledge index;old SHA/Skill unchanged;new human listening pending.',flush=True)

if __name__=='__main__':main()
