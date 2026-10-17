"""Append full-song production record, update active entry points, seal results."""
import copy,csv,json,math,os,subprocess,sys
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np
from prepare_feedback_and_skill import ROOT,RUN,KNOW,REPORT,ENTRIES,SKILL,INSTALLED,INDEX
from apply_whole_song import resources
from assemble_lastpage_accepted_baseline_20261011 import load,save,ref,sha,check
from agent2utau.knowledge import collect_context,validate_context

NAME='J-method-whole-song-v03-20261013'
FINALINDEX='table2-whole-song-v03-index-20261014'
RESPONSE='RESP:LASTPAGE-J-METHOD-WHOLE-SONG-01'

def csv_write(path,rows):
    with path.open('x',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def main():
    assert not (RUN/'completion-manifest.json').exists()
    gates={k:load(RUN/f'evaluation/{k}-independent-check.json') for k in ['native','fresh','delivery']}
    assert all(g['status']=='passed' for g in gates.values());resources();check(load(RUN/'protected-before.json'))
    pack=load(RUN/'evaluation/assembly-check.json');mix=load(RUN/'evaluation/mix-check.json');metrics=load(RUN/'observations/word-metrics.json')
    protocol=load(RUN/'design/protocol.json');exe=load(RUN/'fresh/execution.json');dec=load(RUN/'design/phrase-decisions.json')
    tests=ROOT/'runs/test-results/lastpage-skill-whole-song-20261013/junit.xml';suites=ET.parse(tests).getroot()
    testcount=sum(int(s.get('tests','0')) for s in suites.iter('testsuite'));assert testcount==164
    assert all(int(s.get('errors','0'))==int(s.get('failures','0'))==0 for s in suites.iter('testsuite'))
    scalars={name:dict(zip(['p50','p95','max'],map(float,np.percentile([w['F0'][name]['median_abs_target_error_cents'] for w in metrics['words'] if w['F0'][name]['median_abs_target_error_cents'] is not None],[50,95,100])))) for name in ['FCPE','RMVPE']}
    supplementary=dict(record_id=RESPONSE,kind='bundled_whole_song_production_revision',status='rendered_checked_pending_whole_song_listening',
        started_date='2026-10-13',completed_date='2026-10-14',acceptance_authorization=ref(REPORT/'own-J-acceptance-and-whole-song-authorization-20261013.json'),
        table1_refs=['PER:S1','EVT:L2','ACO:L1','PARAM:C03.01','PARAM:C13.01'],
        protocol=ref(RUN/'design/protocol.json'),knowledge_receipt=ref(RUN/'evaluation/knowledge_receipt.json'),
        words_reviewed=318,contexts=34,changed_contexts=sum(d['changed'] for d in dec),new_pitch_gestures=15,
        new_pitch_word_ids=[g['word'] for g in load(RUN/'design/pitch-gestures.json')],
        changed_pitch_grid_points=sum(r['changed_pitch_grid_points'] for r in gates['native']['rows']),
        native_target_max_error_cents=gates['native']['native_max_error_cents'],
        new_fixed_seeded_waveforms=37,new_variance_calls=37,repeat_contexts=[0,22,28],repeat_exact=True,
        native_cached_technical_render='one full34-context PCM16 technical mix; internal neural call counts uninstrumented',
        speaker_candidate='Bright40/Cute60 except retained accepted bao context22 Normal75/Classic25',
        manual_controls='neutral TENC/BREC/VOIC/SHFC except exact accepted bao context22; old DYN retained',
        feature_clipping_by_context=[dict(context=r['context'],counts=r['feature_clipping']) for r in gates['fresh']['rows']],
        all_feature_clipping_zero=True,old_originals_and_runs_preserved=True,source_unknown_words=[106],
        accepted_J_raw_contributions_exact=True,accepted_bao_raw_contribution_exact=True,
        overlap_limits=dict(new_J_crop_changed_samples=pack['new_J_preview_changed_samples'],
            new_J_crop_change_span_s=pack['new_J_preview_change_span_s'],
            real_word_windows_changed=[w for w in pack['accepted_real_phone_windows'] if not w['actual_phone_PCM_exact']],
            reason='Only changed adjacent context contributions; independent accepted J/bao waves held. New full mix still needs listening.'),
        original_vocal_gain=1.5,original_backing_bytes_exact=True,common_mix_margin=.9,post_margin_mix_peak=mix['mix']['peak'],
        vocal_peak=pack['peak'],duration_s=pack['duration_s'],
        new_F0_calls=2,F0_vowel_median_error_summary_cents=scalars,F0_proxy_not_pitch_naturalness_truth=True,
        response_limit='Joint production update, not single-factor causal study. J local acceptance is preserved; remaining contexts are explicit same-song extrapolations.',
        outputs=dict(vocal=pack['outputs']['full_vocal'],mix=mix['output'],project=mix['playback_project'],published_project=mix['published_playback_project']),
        original_J_reference=ref(RUN/'delivery/accepted_J_reference.wav'),
        word_metrics=ref(RUN/'observations/word-metrics.json'),
        new_listening_feedback_count=0,full_song_accepted=False,agent_heard=False,measurement_validated=False,general_rule_validated=False)
    assert all(not any(r['counts'].values()) for r in supplementary['feature_clipping_by_context'])
    shutil=__import__('shutil');shutil.copyfile(RUN/'observations/word-metrics.csv',REPORT/(NAME+'-words.csv'))
    pitchrows=[dict(word=g['word'],char=g['char'],context=g['context'],start_s=g['support_s'][0],end_s=g['support_s'][1],
        nodes=json.dumps(g['center_nodes']),purpose=g['purpose'],auditory_acceptance='pending') for g in load(RUN/'design/pitch-gestures.json')]
    csv_write(REPORT/(NAME+'-pitch.csv'),pitchrows)
    save(REPORT/(NAME+'.json'),dict(status='whole_song_v03_rendered_checked_pending_listening',table2_supplement=supplementary,
        skill_files=protocol['skill_bindings'],gates={k:ref(RUN/f'evaluation/{k}-independent-check.json') for k in gates},
        local_tests=dict(passed=testcount,junit=ref(tests)),stage_corrections=ref(RUN/'logs/validation-corrections.txt'),
        prior_own_functions_retained_not_redrawn=True,all_current_word_decisions=ref(RUN/'design/word-decisions.json')))
    table='|字ID/字|上下文|实际新函数支撑s|\n|---|---:|---|\n'
    for g in load(RUN/'design/pitch-gestures.json'):table+=f"|{g['word']}/{g['char']}|{g['context']}|{g['support_s'][0]:.6f}–{g['support_s'][1]:.6f}|\n"
    md=f'''# 最后一页：J方法整曲v03

2026-10-13接受与启动，2026-10-14完成。用户明确“我们的 J 可以了”，要求“记录下来。更新skill后运用到整曲”。已追加局部接受，更新并同步Skill方法；旧作者、歌曲工程、音频、封存run和历史反馈保持。单Agent、本机检查，CI仅手动。

## 实际整曲改版

全318字、34上下文重新审阅并保存逐字/逐句决策。31上下文改写，J的28/29及之前接受抱C的22保持原条件。候选整曲声线采用本曲J的Bright40/Cute60和人工TENC/BREC/VOIC零增量；22保留已接受Normal75/Classic25/SHFC和完整控制。其余上下文为明确同曲外推，不是31份新听觉接受。

先审短音乐阶段而非继续增加VOIC/TENC/DYN。选定15个原曲GAME/局部双F0支持且当前最终线遗漏的入口，以独立Hermite节点编译；相同字不强制同入口（两处里原曲低音不同、看283源是下行，均不套统一低头）。29从/112果/152是等短事件有检测冲突不执行；已有低承接保留，197舍的源下行作为未实施候选保留。unknown106不升级。对174抱/179冷，接入段保留自身边界切线后有短回探，明确不是全段单调保证，图形/C1不代替试听。

{table}

保留原有自身音符、note.pitch、音素、气口、其余字腹/周期和DYN；这是整曲发声改版及15处有限音高函数，**不是整曲每个点重新画线**。旧自己函数SHA及每字保留理由已绑定，作者数组未接入生产目标。不会因体略虚或低声母RMS做撤回的衔接/补声母增益修复；旧G/H/I等阴性不加码。

## 实际执行与交付

执行前20ID knowledge_context逐ID门禁通过，包含最新J接受和旧阴性。原生34句身份/时钟、两阶段实际speaker及完整音高依赖独立重建通过；948个pitch网格点变更，目标最大误差{gates['native']['native_max_error_cents']:.9f}c。所有34上下文新variance/acoustic/vocoder；固定11/101，共37套（34主+0/22/28三个重复），重复输入/预测/mel/raw精确，特征裁剪0。全曲原生技术mix另列，不补造内部模型调用次数。

Core ApplyDynamics对34新波形与34单位波形执行，原生DYN逐样点保持。完整245.577s人声PCM24/44100固定1.5，峰值{pack['peak']:.9f}；独立逆序拼接及PCM重建精确。J28/29、抱C22独立贡献精确保持，但邻27/30改变进入旧J预览头尾（25898样点变化）；抱句面230、J末字见284的部分重叠PCM也受邻句影响。原J参考另原字节交付，不把新整曲拼接预览说成原J完全相等。

原伴奏从封存delivery按SHA复制，未研究或调节BGM关系。原1.5人声＋原预缩放0.7伴奏相加峰值1.054508924，8样点越满幅，混音器拒绝写入。选择单次公共0.9（−0.915150dB），保持相对比例；混音峰值{mix['mix']['peak']:.9f}。播放工程两轨同降并补齐可加载伴奏；纯人声与原伴奏文件不改增益。默认GBK的Skill验证器失败用显式UTF-8纠正，伴奏旧发布目录不存在的定位失败保留，未放宽门禁。最终Skill验证、本机164测试和独立交付检查通过。

新整曲双F0各一次，318元音电平/误差行已公开CSV。FCPE每字中位绝对误差的p50/p95/max为{scalars['FCPE']['p50']:.3f}/{scalars['FCPE']['p95']:.3f}/{scalars['FCPE']['max']:.3f}c，RMVPE为{scalars['RMVPE']['p50']:.3f}/{scalars['RMVPE']['p95']:.3f}/{scalars['RMVPE']['max']:.3f}c；只是有限检测代理，电平不等于实感/力量/磨砂质感。Agent未听，新整曲反馈0，全部measurement_validated与通用规律仍false。

交付路径/SHA见同名JSON。下一步收本首完整试听按时码/唱字回填表2；不自动开另一首或继续参数搜索。J的局部接受不等于新整曲验收，旧体/太实/磨砂描述保留作细化线索，不补造作者A/C质感相等。
'''
    (REPORT/(NAME+'.md')).write_text(md,encoding='utf8')
    idx=copy.deepcopy(load(KNOW/(INDEX+'.json')));idx['rows'].append(dict(id=RESPONSE,
        kind='bundled_whole_song_production_revision',source=ref(REPORT/(NAME+'.json')),source_record=supplementary,
        feedback_sources=[],measurement_validated=False,general_rule_validated=False))
    idx.update(status='whole_song_v03_rendered_checked_pending_listening',date='2026-10-14',whole_song_production_records=1,
        generator=ref(Path(__file__)),prior_index=ref(KNOW/(INDEX+'.json')))
    save(KNOW/(FINALINDEX+'.json'),idx)
    rows=[dict(id=r['id'],kind=r.get('kind','response'),source_path=r['source']['path'],source_sha256=r['source']['sha256'],
        measurement_validated=False) for r in idx['rows']];csv_write(KNOW/(FINALINDEX+'.csv'),rows)
    (KNOW/(FINALINDEX+'.md')).write_text('# 整曲v03索引\n\n原37行/12近期研究系列保留，追加1条整曲组合改版记录，共38行；不是新增318份独立样本/听觉接受。见同名JSON/CSV及整曲报告。\n',encoding='utf8')
    reg=load(KNOW/'active-knowledge-sources.json');reg['response_indices']=[(KNOW/(FINALINDEX+'.json')).relative_to(ROOT).as_posix()]
    (KNOW/'active-knowledge-sources.json').write_text(json.dumps(reg,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    packet=collect_context(['PER:S1','EVT:L2','ACO:L1'],['PARAM:C03.01','PARAM:C13.01'],['RESP:LASTPAGE-OWN-LI-ENTRY-PITCH-01',RESPONSE])
    follow=[dict(id=r['id'],decision='keep_unknown' if r['id']==RESPONSE else 'use',reason='Full-song hearing pending; preserve explicit J local acceptance and actual condition record.',
        condition_match='New whole-song v03 with J/bao exceptions and updated Skill.',limitations='Retrieval is source verification, not auditory validation or general rule.') for r in packet['records']]
    save(RUN/'evaluation/current-knowledge-roundtrip.json',dict(packet=packet,receipt=validate_context(packet,follow)))
    status='当前状态whole_song_J_method_v03_rendered_checked_pending_listening：2026-10-13用户明确“我们的 J 可以了”并授权更新Skill/整曲，2026-10-14完成。已追加接受、更新同步Skill方法，318字/34上下文逐项审阅，31上下文改版、15处独立音高入口；J28/29与抱C22条件/独立波形保持，邻句重叠影响单列。34主+3重复新成声、两阶段speaker/原生DYN/双F0/318观测记录及164测试通过，特征裁剪0。245.577s新纯人声/混音和播放USTX已交付；纯人声1.5，原伴奏字节保持，混音公共0.9余量保留比例。旧工程/音频/作者/历史阴性与unknown保持，38索引新增1条组合生产记录，非通用因果规律。Agent未听，整曲待用户试听；单Agent/CI仅手动。'
    links={ENTRIES[0]:'docs/reports/lastpage/'+NAME+'.md',ENTRIES[1]:'docs/reports/lastpage/'+NAME+'.md',ENTRIES[2]:'docs/reports/lastpage/'+NAME+'.md',
        ENTRIES[3]:'docs/reports/lastpage/'+NAME+'.md',ENTRIES[4]:'../../docs/reports/lastpage/'+NAME+'.md',ENTRIES[5]:'../../../docs/reports/lastpage/'+NAME+'.md'}
    for name in ENTRIES:
        p=ROOT/name;text=p.read_text(encoding='utf8');lines=text.splitlines(keepends=True);found=0
        for i,line in enumerate(lines):
            if '当前状态transition_withdrawn_author_A_C_texture_reused_delivered_pending_listening：' in line:
                prefix='- ' if line.startswith('- ') else '';lines[i]=prefix+status+f' 见[整曲v03记录]({links[name]})。\n';found+=1
            if line.startswith('下一工作进入逐首更新，先《最后一页》：'):
                lines[i]='下一工作进入逐首更新，先《最后一页》：新v03完整人声、保留原伴奏比例的混音和播放工程已完成；下一步只接本首整曲试听反馈，按时码/唱字追加表2。原J局部接受、已撤回衔接问题与历史阴性保持，不自动扩大参数搜索或进入另一首。\n'
        assert found==1,name;p.write_text(''.join(lines),encoding='utf8')
    out=subprocess.run([sys.executable,str(ROOT/'tools/repository/check_repository.py'),'--worktree'],cwd=ROOT,capture_output=True,encoding='utf8')
    (RUN/'logs/repository-gate.log').write_text(out.stdout+out.stderr,encoding='utf8');assert out.returncode==0,out.stderr
    save(RUN/'evaluation/repository-gate.json',json.loads(out.stdout))
    check(load(RUN/'protected-before.json'));resources()
    wf=(ROOT/'.github/workflows/ci.yml').read_text(encoding='utf8');assert 'workflow_dispatch' in wf and not any(t in wf for t in ['push:','pull_request:','schedule:'])
    docs=[REPORT/(NAME+s) for s in ['.md','.json','-words.csv','-pitch.csv']]+[KNOW/(FINALINDEX+s) for s in ['.md','.json','.csv']]+[KNOW/'active-knowledge-sources.json']
    extra=[REPORT/('own-J-acceptance-and-whole-song-authorization-20261013'+s) for s in ['.md','.json']]+[KNOW/(INDEX+s) for s in ['.md','.json','.csv']]
    save(RUN/'completion-manifest.json',dict(status='complete_technical_delivery_pending_human_listening',
        files=[ref(p) for p in sorted(RUN.rglob('*')) if p.is_file()],documents=[ref(p) for p in docs+extra],
        entries=[ref(ROOT/n) for n in ENTRIES],implementation=[ref(p) for p in sorted(Path(__file__).parent.glob('*.py'))],
        skill=[ref(p) for p in [SKILL/'SKILL.md',SKILL/'references/local-acceptance-to-whole-song-phonation.md']],
        published=[mix['published_playback_project'],mix['published_backing'],pack['outputs']['published']],
        installed_skill=[dict(path=str(INSTALLED/p),sha256=sha(INSTALLED/p)) for p in ['SKILL.md','references/local-acceptance-to-whole-song-phonation.md']],
        protected_previous_files_count=len(load(RUN/'protected-before.json')),tests_passed=testcount,measurement_validated=False,
        general_rule_validated=False,new_feedback=0,agent_heard=False))
    print('Sealed full-song revision;38-row active index;all old protected SHA exact. Whole-song human listening pending.',flush=True)

if __name__=='__main__':main()
