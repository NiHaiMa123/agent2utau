"""Review existing conditions and source F0; freeze an independent entry-pitch probe."""
import copy
import csv
import json
from pathlib import Path
import subprocess
import sys
import numpy as np
from assemble_lastpage_accepted_baseline_20261011 import ROOT, ENTRIES, load, save, ref, sha, check
from agent2utau.knowledge import collect_context, validate_context, check_plan_knowledge

PRIOR = ROOT / 'runs/research/lastpage-own-li-TENC-feedback-20261013'
RUN = ROOT / 'runs/research/lastpage-li-condition-review-20261013'
BASE = ROOT / 'runs/lastpage_loudness_skill_v02_20261007'
F = ROOT / 'runs/experiments/lastpage-own-control-neutral-20261012'
REPORT = ROOT / 'docs/reports/lastpage'
NAME = 'li-condition-review-20261013'
KNOW = ROOT / 'docs/knowledge/acoustic-manifestations-20261009'
INDEX = 'table2-li-condition-review-index-20261013'
REGISTRY = KNOW / 'active-knowledge-sources.json'
OBS_ID = 'OBS:LASTPAGE-LI-ENTRY-REVIEW-01'


def csv_write(path, rows):
    with path.open('x', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def initial_save(path, value):
    if path.exists():
        assert load(path) == value, path
    else:
        save(path, value)


def pitch_at(p, sec):
    t = np.asarray(p['times_ms'], np.float64) / 1000
    y = np.asarray(p['final_cents'], np.float64)
    k = int(np.searchsorted(t, sec, side='right') - 1)
    assert 0 <= k < len(t) - 1
    slope = (y[k + 1] - y[k]) / (t[k + 1] - t[k])
    return float(y[k] + (sec - t[k]) * slope), float(slope)


def hermite(time, nodes):
    for (a, x, dx), (b, y, dy) in zip(nodes, nodes[1:]):
        if a <= time <= b:
            h = b - a
            u = (time - a) / h
            return (2*u**3-3*u**2+1)*x + (u**3-2*u**2+u)*h*dx + (-2*u**3+3*u**2)*y + (u**3-u**2)*h*dy
    raise ValueError(time)


def main():
    assert not (RUN / 'completion-manifest.json').exists() and not (REPORT / (NAME + '.json')).exists()
    seal = load(PRIOR / 'completion-manifest.json')
    check(seal['files'] + seal['documents'] + seal['entries'])
    original = load(PRIOR / 'protected-before.json') + seal['files'] + seal['documents'] + [ref(PRIOR / 'completion-manifest.json')]
    check(original)
    registry_ref = ref(REGISTRY)
    protected = [r for r in original if r['path'] != registry_ref['path']]
    RUN.mkdir(parents=True, exist_ok=True)
    (RUN / 'logs').mkdir(exist_ok=True)
    initial_save(RUN / 'protected-before.json', protected)
    for name in ENTRIES + [registry_ref['path']]:
        p = RUN / 'before' / name
        p.parent.mkdir(parents=True, exist_ok=True)
        if p.exists():
            assert p.read_bytes() == (ROOT / name).read_bytes(), name
        else:
            p.write_bytes((ROOT / name).read_bytes())
    initial_save(RUN / 'design/mutable-registry-before.json', dict(registry=registry_ref,
        preserved_original_bytes=ref(RUN / 'before' / registry_ref['path']), reason='Append condition review; old responses and receipts immutable'))
    config = load(REGISTRY)
    old_path = ROOT / config['response_indices'][0]
    old_index = load(old_path)
    recent = [r for r in old_index['rows'] if r['kind'] == 'recent_response_series']
    assert len(recent) == 11 and len(old_index['rows']) == 35
    response_ids = [r['id'] for r in recent]
    entities = ['PER:S1', 'EVT:L2', 'ACO:L1']
    parameters = ['PARAM:C01.01', 'PARAM:C02.02', 'PARAM:C03.01', 'PARAM:C13.01']
    first = collect_context(entities, parameters, response_ids)
    review_decisions = [dict(id=r['id'], decision='use', reason='Review exact recorded factor scope and feedback without transitive rankings or mechanism claims',
        condition_match='Existing current1.65c own and author two-phrase development conditions; no independent holdout',
        limitations='Source detectors, model inputs, digital level and perception remain separate; no new inference') for r in first['records']]
    initial_save(RUN / 'design/review-knowledge-context.json', first)
    review_plan = dict(id='LASTPAGE-LI-CONDITION-REVIEW-01', scope='read-only existing JSON/score and two sealed source F0 arrays',
        knowledge_context=dict(path='review-knowledge-context.json', sha256=ref(RUN / 'design/review-knowledge-context.json')['sha256'], decisions=review_decisions),
        new_native_calls=0, new_models=0, new_waveforms=0)
    initial_save(RUN / 'design/review-protocol.json', review_plan)
    _, receipt = check_plan_knowledge(review_plan, RUN / 'design/review-protocol.json')
    initial_save(RUN / 'evaluation/review-knowledge-receipt.json', receipt)
    source_binding = load(BASE / 'source_and_own_design_reuse.json')
    for name in ['source_observations.json', 'fcpe.npz', 'rmvpe.npz', 'native_word_geometry.json']:
        assert sha(BASE / name) == source_binding['source_files'][name]
    decision_ref = ref(BASE / 'agent_word_decisions.json')
    current_decision_hashes = {r['sha256'] for r in protected if r['path'] == decision_ref['path']}
    assert current_decision_hashes == {decision_ref['sha256']}
    save(RUN / 'evaluation/decision-version-binding.json', dict(current_final_decisions=decision_ref,
        initial_reuse_declaration=ref(BASE / 'source_and_own_design_reuse.json'),
        prior_reuse_decision_SHA=source_binding['source_files']['agent_word_decisions.json'],
        source_observation_and_F0_declaration_SHA_exact=True, current_final_decision_protection_SHA_exact=True,
        initial_checker_error='Initial assertion treated copied prior decisions as final current decisions; corrected without changing source files',
        failed_checker=ref(RUN / 'logs/review-initial-source.py.txt'), failure_note=ref(RUN / 'logs/initial-binding-failure.txt')))
    source = {r['word']: r for r in load(BASE / 'source_observations.json')['words']}
    geometry = {r['word']: r for r in load(BASE / 'native_word_geometry.json')}
    own = {r['word']: r for r in load(BASE / 'agent_word_decisions.json')}
    conditions = load(REPORT / 'author-controls-feedback-20261012.json')['conditions']
    pitches = load(F / 'native-inputs/F-pitch.json')['phrases']
    condition_rows = []
    for c in conditions:
        w = c['word']
        s, e = geometry[w]['native_vowel']
        p = pitches[c['own_context'] - 28]
        times = np.asarray(p['times_ms']) / 1000
        values = np.asarray(p['final_cents']) / 100
        mask = (times >= s) & (times < min(s + .080, e))
        game = [g for g in source[w]['game'] if g['voiced']]
        condition_rows.append(dict(word=w, char=c['char'], context=c['own_context'], own_tones=c['own_music_tones'],
            author_tones=c['author_music_tones'], source_GAME=game, F_first80ms_MIDI_median=float(np.median(values[mask])),
            native_vowel_s=[s, e], source_unknown=source[w]['unknown'], individual_new_label='none',
            interpretation='low-entry66 candidate missing from F absolute line' if w == 277 else
                'source GAME has no author64 entry; preserve existing positive reference' if w == 283 else 'context/counterexample; no intervention selected'))
    assert len(condition_rows) == 15 and all(not r['source_unknown'] for r in condition_rows)
    stats = []
    for name in ['fcpe', 'rmvpe']:
        with np.load(BASE / (name + '.npz'), allow_pickle=False) as z:
            times = z['times'].astype(np.float64)
            hz = z['f0_hz'].astype(np.float64)
            valid = z['voiced'] & np.isfinite(hz) & (hz > 0)
        assert len(times) == len(hz) == 24558 and times[0] == 0 and np.all(np.diff(times) > 0)
        s, e = source[277]['vowel']['start'], source[277]['vowel']['end']
        mask = (times >= s) & (times < e) & valid
        midi = 69 + 12 * np.log2(hz[mask] / 440)
        old_stats = source[277]['stats'][name]
        assert len(midi) == old_stats['n'] and abs(float(np.median(midi)) - old_stats['median']) < 1e-4
        for j, g in enumerate(source[277]['game']):
            mask = (times >= g['start']) & (times < g['end']) & valid
            midi = 69 + 12 * np.log2(hz[mask] / 440)
            stats.append(dict(detector=name, source_stage=j, start_s=g['start'], end_s=g['end'],
                GAME_tone=g['tone'], voiced_frames=int(mask.sum()), MIDI_median=float(np.median(midi)),
                MIDI_min=float(midi.min()), MIDI_max=float(midi.max()),
                scope='sealed source detector observation, not newly measured F0 or exact musical boundary truth'))
    assert len(stats) == 6 and all(r['voiced_frames'] >= 15 for r in stats)
    # Agent choices from source musical candidates; no author numeric arrays are read.
    s, e = geometry[277]['native_vowel']
    prep = s - .080
    hold = s + .090
    arrival = 213.140
    join = 213.200
    assert geometry[277]['phones'][0]['start_ms'] / 1000 < prep < s < hold < arrival < join < own[277]['entry_actions'][0]['body_end'] < e
    start_value, start_slope = pitch_at(pitches[0], prep)
    end_value, end_slope = pitch_at(pitches[0], join)
    nodes = [[prep, start_value, start_slope], [s, 6600., 0.], [hold, 6600., 0.], [arrival, 6800., 0.], [join, end_value, end_slope]]
    dense = [[float(t), float(hermite(t, nodes))] for t in np.linspace(prep, join, 1501)]
    values = np.asarray([r[1] for r in dense])
    assert np.isfinite(values).all() and values.min() >= 6599.999999 and values.max() <= start_value + 1e-6
    for j, sign in [(0, -1), (1, 0), (2, 1)]:
        a, b = nodes[j][0], nodes[j+1][0]
        yy = np.asarray([hermite(float(t), nodes) for t in np.linspace(a, b, 201)])
        assert np.all(np.diff(yy) <= 1e-7) if sign < 0 else np.all(np.diff(yy) >= -1e-7) if sign > 0 else np.max(np.abs(yy - 6600)) < 1e-7
    save(RUN / 'evaluation/planned-pitch-function.json', dict(nodes_s_cents_cents_per_s=nodes, dense=dense,
        status='analytic shape only; no native or sound execution', author_arrays_read=0, native_max_target_error='not yet checked'))
    meanings = [
        ('voice-baseline', 'normal75/bright25 only', 'this own candidate remained virtual; no regression reported', 'does not exclude all other speaker mixtures'),
        ('conditioned-VOIC', 'own five-word VOIC increases', 'not accepted', 'not evidence for more VOIC or universal channel inefficacy'),
        ('author-pitch', 'author PITD and relative note.pitch neutralization', 'A/P/N/PN all more solid than old own', 'notes.tone/music stages/clocks retained; absolute music trajectory not excluded'),
        ('author-voice', 'own speaker on author conditions', 'B somewhat better than old own, below A', 'voice contribution supported; no unique cause'),
        ('author-neutral', 'author grouped manual controls removed', 'C very close to A', 'no isolated TENC/BREC/VOIC verdict; C-F direct rank absent'),
        ('author-interaction', 'fourth speaker/control corner', 'D slightly above B, far below C', 'speaker/control interaction conditional; no transitive F rank'),
        ('own-E', 'bright40/cute60 on own conditions', 'more solid than author but forward/squeezed/thin/sharp', 'adverse example; cannot map to one tension cause'),
        ('own-F', 'grouped manual controls neutralized under E voice', 'better and author li staged strength requested', 'working comparator, not all adverse traits resolved or fully solid'),
        ('G', 'one VOIC stage gesture on F', 'not acceptable', 'rejection dimensions unspecified; no escalation'),
        ('H', 'DYN stage gesture on F raw', 'li insufficient solidity/strength', 'output envelope failed current target; not an all-DYN verdict'),
        ('I', 'TENC stage gesture on F', 'no meaningful perceived difference from F', 'finite dose negative; no escalation or universal verdict')]
    evidence_rows = []
    for r, meaning in zip(recent, meanings):
        fb = r['feedback_record']
        text = fb.get('verbatim', fb.get('original_text'))
        assert text
        evidence_rows.append(dict(id=r['id'], short_label=meaning[0], factor=meaning[1], verbatim=text,
            limited_reading=meaning[2], remaining_boundary=meaning[3], source=r['source'], feedback_sources=r['feedback_sources']))
    bindings = [ref(BASE / p) for p in ['source_and_own_design_reuse.json', 'source_observations.json', 'fcpe.npz', 'rmvpe.npz',
        'native_word_geometry.json', 'agent_word_decisions.json']] + [ref(F / 'native-inputs/F-pitch.json'),
        ref(F / 'score/lastpage_own_control_neutral_F.ustx'), ref(REPORT / 'author-controls-feedback-20261012.json')]
    supplement = dict(record_id=OBS_ID, kind='condition_review_not_response', response_series_added=0,
        table1_refs=entities + parameters, source_bindings=bindings, evidence_rows=evidence_rows,
        condition_rows=condition_rows, source_F0_stages=stats,
        finding='Own F omits source-supported low66 entry trajectory; author micro-pitch ablation did not test this own trajectory.',
        counterexamples='Own ti276/ni282 already show low bearing; source kan283 has66→64 without author64 onset. No all-word low-entry recipe.',
        causal_solidity_or_strength='unknown', next_candidate='J finite own entry pitch only; not yet generated',
        new_feedback_count=0, new_source_F0_array_reads=2, new_F0_detector_calls=0, new_audio_decodes=0,
        new_native_calls=0, new_models=0, new_waveforms=0, adoption=False, agent_heard=False,
        measurement_validated=False, general_rule_validated=False)
    report = dict(status='li_conditions_reviewed_entry_pitch_J_design_frozen', table2_supplement=supplement,
        decision_version_binding=ref(RUN / 'evaluation/decision-version-binding.json'),
        next_protocol_path=(RUN / 'design/next-li-entry-pitch-protocol.json').relative_to(ROOT).as_posix(),
        planned_function=ref(RUN / 'evaluation/planned-pitch-function.json'), knowledge_review_receipt=ref(RUN / 'evaluation/review-knowledge-receipt.json'))
    save(REPORT / (NAME + '.json'), report)
    csv_write(REPORT / (NAME + '-evidence.csv'), [dict(id=r['id'], factor=r['factor'], verbatim=r['verbatim'], limited_reading=r['limited_reading'], remaining_boundary=r['remaining_boundary']) for r in evidence_rows])
    csv_write(REPORT / (NAME + '-conditions.csv'), [dict(word=r['word'], char=r['char'], context=r['context'], own_tones=json.dumps(r['own_tones']),
        author_tones=json.dumps(r['author_tones']), source_GAME_tones=json.dumps([g['tone'] for g in r['source_GAME']]),
        F_first80ms_MIDI_median=r['F_first80ms_MIDI_median'], interpretation=r['interpretation']) for r in condition_rows])
    csv_write(REPORT / (NAME + '-source-stages.csv'), stats)
    phase_table = '|源阶段|GAME候选|FCPE中位MIDI|RMVPE中位MIDI|\n|---|---:|---:|---:|\n'
    for j in range(3):
        a, b = [next(r for r in stats if r['source_stage'] == j and r['detector'] == name) for name in ['fcpe', 'rmvpe']]
        phase_table += f"|{a['start_s']:.6f}–{a['end_s']:.6f}s|{a['GAME_tone']:.3f}|{a['MIDI_median']:.3f}|{b['MIDI_median']:.3f}|\n"
    md = f'''# 最后一页：已有条件复核与里字进入音高候选J

2026-10-13。用户“下一步”推进I阴性后的条件复核。本轮11响应系列按实际因素/原话/限制逐项串联，不将不同回复相加成唯一病因或精确全排序。G“不行”、H里实感/强度不足、I相对F没什么区别保持，不继续发声剂量搜索。E的实感及挤细尖副作用和F聚合改善仍并列，F只是工作基底。

## 找到的具体剩余差异

前作者P/N/PN仅取消PITD/note.pitch细节，仍保留notes.tone及音乐阶段。15字对照中，里自身写68→66，作者66→68→66。进一步回到自己的原曲资料：GAME里包含66附近约170ms、68附近约390ms、66附近约196ms三候选事件；F在i入口69.1、首80ms中位68.760，旧short_direct从上方到68，没有这个低66进入。这里的“遗漏”指已有观测候选未进入自己的最终设计，不把GAME本身冒称音乐真值或认定听感病因。

{phase_table}

两个封存原曲F0数组按GAME原始双精度时界复核，支持先低后高再低的观测方向；没有重跑检测器/解码音频。它们来源SHA与原词窗n/中位统计核对（转换浮点容差1e-4），未读取actual_fcpe/actual_rmvpe生成版数组；两检测器未在此校准成真值，时界及过渡精确位置仍是观测候选。新增6行阶段摘要是旧数组的派生复核，不是6个新样本/新实验。初始检查误将前序复用声明中的旧agent_word_decisions SHA当当前最终版，断言在报告/数组/模型执行前失败；当前最终决策按既有保护链SHA核对，原曲观测/源F0/几何仍与复用声明精确。失败源码/说明及两版引用另列保留，未修改源资料或放宽SHA。

反例同样记录：体276/你282已有低位承接，不能全字套相同入口；看283自己的GAME为66→64，没有作者额外64入口，因此保留看及完整context29。作者/自己的时钟、主音、phone tone、完整上下文仍不同，C与F未获直接精确排序，不把剩余差距直接归因于音高或时长。

## 下一项J：自己的进入音高单因素，未执行

从F完整副本只改context28里/l准备的最终绝对pitch：{prep:.9f}s按F自身边界值/切线接入，i起点{s:.9f}s到6600c，保持至{hold:.9f}s，再在213.140s到6800c，213.200s按F自身值/切线接回。五节点cubic Hermite，边界数值来自自己的F，内部低位、耗时和斜率是Agent基于原曲候选的独立选择；不读取作者曲线/局部节点，也不把原曲F0数组缩幅拟合成目标。解析下行/低位保持/上行和边界有限范围已检查，但不是原生执行/音频验收。

当前J保留notes.tone/tuning/positions/durations/note.pitch/vibrato、音素选择/完整时钟和Bright40/Cute60及TENC0/BREC0/VOIC100/SHFC0/DYN0。仅通过既有5tick PITD编码新的绝对目标，before-PITD只编码，不作为新目标。它检验的是自己缺少的低位进入**实际音高路径**，尚未隔离phone选择用的notes.tone独立作用；不写成谱面音符已修正。最后约80ms l会改变pitch，咬字/前后衔接须试听，不能宣称只在元音作用；5tick实际采样边缘须明确，不能缩掩码掩盖。

pitch改变将同时进入variance、acoustic F0及vocoder F0，必须重建三预测并接受它们作为依赖响应；不保持旧预测后声称已测试完整路径。全15字邻域/里进入到回收、双F0/PCM检查，context29看与抱C贡献保护、共享padding另列；后半里及其它输入精确保留，模型上下文仍可能影响邻字输出。预算单个J/J_repeat两套新固定11/101合成、2次新F0、2句原生缓存技术，实际0。F贡献/预测明确封存复用；遇身份/隔离/越界/削波失败停止，不换种子/加通道/扫参数。

本轮表2增加OBS条件复核行，不增加响应实验或试听计数：近11系列保持，索引35→36行。新来源/原话/限制及G/H/I阴性实际进入下一方案知识门禁。原歌音频Skill/作者原件/旧封存/抱C/source_unknown106保持，Agent未听，new_native/models/waveforms=0，measurement_validated=false、通用规律0，单Agent、CI仅手动。

[11系列证据CSV]({NAME}-evidence.csv)、[15字条件CSV]({NAME}-conditions.csv)、[原曲阶段CSV]({NAME}-source-stages.csv)、[JSON]({NAME}.json)、[审计]({NAME}-audit.json)。
'''
    (REPORT / (NAME + '.md')).write_text(md, encoding='utf-8', newline='\n')
    idx = copy.deepcopy(old_index)
    idx['rows'].append(dict(id=OBS_ID, kind='condition_review_not_response', source=ref(REPORT / (NAME + '.json')), feedback_sources=[],
        table1_refs=entities + parameters, source_record=supplement, scope='Derived condition/source observation review; J not executed, no new feedback'))
    idx.update(status='current_index_entry_condition_review_with_all_prior_feedbacks', prior_index=ref(old_path), generator=ref(Path(__file__)))
    save(KNOW / (INDEX + '.json'), idx)
    csvrows = [dict(id=r['id'], kind=r['kind'], source_path=r['source']['path'], source_sha256=r['source']['sha256'],
        feedback_paths='|'.join(p['path'] for p in r['feedback_sources']), table1_refs='|'.join(r['table1_refs']), scope=r['scope']) for r in idx['rows']]
    csv_write(KNOW / (INDEX + '.csv'), csvrows)
    imd = '# 表2当前索引：里进入条件复核\n\n36行，近11响应系列不变；新增1个OBS只读派生复核，不是新响应/反馈/留出。旧阴性、原字段及SHA保持，J尚未执行。\n\n|ID|记录类型|来源|\n|---|---|---|\n'
    for r in idx['rows']:
        imd += f"|{r['id']}|{r['kind']}|[{Path(r['source']['path']).stem}](../../../{r['source']['path']})|\n"
    imd += f'\n[CSV]({INDEX}.csv)、[JSON]({INDEX}.json)。\n'
    (KNOW / (INDEX + '.md')).write_text(imd, encoding='utf-8', newline='\n')
    config['response_indices'] = [ref(KNOW / (INDEX + '.json'))['path']]
    REGISTRY.write_text(json.dumps(config, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    packet = collect_context(entities, parameters, response_ids + [OBS_ID])
    decisions = []
    for r in packet['records']:
        ident = r['id']
        choice = 'reject' if ident in response_ids[-3:] else 'extrapolate' if ident in [OBS_ID, 'PARAM:C03.01'] else 'use'
        reason = ('G/H/I finite phonation/level candidates not accepted or no meaningful improvement; no escalation' if choice == 'reject' else
                  'Independent source-conditioned low entry; native/detector response and perceptual benefit untested' if choice == 'extrapolate' else
                  'Keep exact condition/feedback boundary; note.tone unchanged does not mean absolute pitch unchanged')
        decisions.append(dict(id=ident, decision=choice, reason=reason,
            condition_match='Current F own li277, source observations and15word audit; author evidence has different music/clock',
            limitations='No author array transfer, direct C-F rank or unique cause; source F0/GAME are observations; J is one development condition'))
    save(RUN / 'design/knowledge_context.json', packet)
    nextplan = dict(id='LASTPAGE-OWN-LI-ENTRY-PITCH-01', status='finite_design_frozen_not_executed', variant='J',
        baseline_score=ref(F / 'score/lastpage_own_control_neutral_F.ustx'), baseline_project=ref(F / 'delivery/lastpage_own_control_neutral_F.ustx'),
        baseline_audio=ref(F / 'delivery/F_two_phrases.wav'),
        author_reference=ref(ROOT / 'runs/experiments/lastpage-author-interaction-20261012/delivery/A_two_phrases.wav'),
        target_word=277, affected_context=28, control_context=29, review_words=list(range(270, 285)),
        source_bindings=bindings, condition_review=ref(REPORT / (NAME + '.json')),
        gesture=dict(channel='pitd encoding absolute pitch', support_s=[prep, join], center_nodes=nodes,
            interpolation='cubic Hermite with stated derivatives; F own pitch retained outside support',
            encoder='original integer5tick PITD grid, target-minus-native-before-PITD rounded cents',
            preparation='last80ms l pitch explicitly changes', source_note_candidate='66→68→66; existing later68→66 retained',
            notes_tone='unchanged: this does not isolate phonemizer note.tone selection',
            purposes=['allow source-supported lower entry', 'hold briefly before rising', 'arrive at own high center', 'rejoin own finite body/descending stage']),
        fixed=['notes/tone/tuning/duration/position/lyrics/note.pitch/vibrato', 'phoneme symbols/clock/CLR',
            'Bright40/Cute60 both stages', 'TENC0/BREC0/VOIC100/SHFC0/DYN0', 'other32contributions and acceptedbaoC', 'seeds11/101', 'gain1.5'],
        permitted_dependencies=['native final pitch', 'variance pitch and all three new predictions', 'acoustic F0 and new predicted final features', 'vocoder F0/mel/raw'],
        budget=dict(candidate_count=1, new_native_cached_contexts=2, new_seeded_variance_calls=2, new_seeded_synthesis_waveforms=2, new_F0_calls=2, sealed_F_context29_reuse=True),
        gates=['knowledge source/decision gate before writes', 'same original5tick grid and only context28 PITD ys change',
            'independent analytic target and actual native final pitch≤0.501c error; actual changed grid/frame support with l and sampling margins stated',
            'full phone/speaker/timing identity; variance changes only pitch before inference; manual deltas0, other fixed model inputs exact',
            'fresh variance predictions fully rebuilt; exact predicted+delta→final, actual acoustic/vocoder F0 checked, all repeats exact',
            'finite unclipped PCM24/gain1.5/34contributions, F reconstruction/context29 real phones/kan/baoC protection and sharedpadding scope',
            '15word/phone/explicit pitch phases and dual F0 observation, no naturalness or force acceptance inferred from proxies'],
        stops=['hash/isolation/native target mismatch', 'new clipping or nonfinite', 'no dose sweep, extra variant or combined controls'],
        listening=['li solidity and strength development', 'new low-entry pitch/musical acceptability', 'l articulation and ti→li connection', 'forward/squeezed/thin/sharp or break'],
        knowledge_context=dict(path='knowledge_context.json', sha256=ref(RUN / 'design/knowledge_context.json')['sha256'], decisions=decisions),
        new_score_written=0, new_models=0, new_waveforms=0, agent_heard=False, adoption=False, measurement_validated=False, general_rule_validated=False)
    save(RUN / 'design/next-li-entry-pitch-protocol.json', nextplan)
    _, receipt = check_plan_knowledge(nextplan, RUN / 'design/next-li-entry-pitch-protocol.json')
    save(RUN / 'evaluation/knowledge_receipt.json', receipt)
    assert len(packet['records']) == 19
    status = ('当前状态li_conditions_reviewed_entry_pitch_J_design_frozen：2026-10-13已复核11系列/15字条件，G/H/I阴性与E挤尖/F工作基底边界保持。'
        '作者微曲线取消未排除音乐阶段；自身里GAME及2封存源F0支持66→68→66，F入口69.1/首80ms中位68.760、未保留低66候选。'
        '6阶段摘要仅旧数组派生非新检测/真值/病因；体/你已有低承接、看源无作者64入口，拒绝全字套低入口。'
        '新增OBS复核非新响应，近11系列/36索引；19ID知识gate消费全部原反馈。下一项J仅冻结F里/l准备的独立Hermite低位进入、保留note.tone/phone时钟及发声/DYN0，'
        'pitch依赖三预测必须重建；2新seeded重复/2新F0/2原生上下文预算实际0，J工程音频未写。'
        '本轮读2源F0 NPZ、0音频解码/检测器/原生/模型/新波形，原歌音频Skill/作者/旧封存/抱C/unknown保持，Agent未听/通用规律0，单Agent/CI仅手动。')
    for name in ENTRIES:
        p = ROOT / name
        lines = p.read_text(encoding='utf-8').splitlines()
        ix = [i for i, l in enumerate(lines) if '当前状态I_feedback_closed_no_meaningful_difference：' in l]
        assert len(ix) == 1, name
        rel = 'docs/reports/lastpage/' + NAME + '.md'
        if '/' in name:
            rel = ('../../' if name.startswith('research/') else '../../../') + rel
        lines[ix[0]] = ('- ' if lines[ix[0]].startswith('- ') else '') + status + f' 见[里条件复核与进入音高J]({rel})。'
        if name == 'plan.md':
            for i, l in enumerate(lines):
                if l.startswith('下一工作进入逐首更新，先《最后一页》：'):
                    lines[i] = '下一工作进入逐首更新，先《最后一页》：11系列/15字复核后优先检验自身里遗漏的原曲低66进入候选，J仅冻结音高路径、原notes.tone/时钟/发声/DYN保持；重新预测完整pitch依赖，不加控制剂量。J未执行；看保持，非全字复制作者入口，下一步按冻结单条件渲染并接里实感/力量及音高咬字副作用试听。'
        if name == 'docs/knowledge/acoustic-manifestations-20261009/README.md':
            for i, l in enumerate(lines):
                if l.startswith('制作使用[当前表2索引]'):
                    lines[i] = f'制作使用[当前表2索引]({INDEX}.md)与[显式来源目录](active-knowledge-sources.json)，知识接入见[指南](../../guides/knowledge-use-in-production.md)。近11系列/36行含新增OBS条件复核（非新响应/反馈）；G/H/I阴性、旧字段/SHA保持。'
        p.write_text('\n'.join(lines) + '\n', encoding='utf-8', newline='\n')
    check(protected)
    check(bindings)
    for r in old_index['rows']:
        assert r == next(q for q in idx['rows'] if q['id'] == r['id'])
    for r in idx['rows']:
        check([r['source']] + r['feedback_sources'])
    with (KNOW / (INDEX + '.csv')).open(encoding='utf-8-sig', newline='') as f:
        assert list(csv.DictReader(f)) == [{k: str(v) for k, v in r.items()} for r in csvrows]
    gate = subprocess.run([sys.executable, 'tools/repository/check_repository.py', '--worktree'], cwd=ROOT, capture_output=True, encoding='utf-8')
    (RUN / 'logs/repository-gate.log').write_text(gate.stdout + gate.stderr, encoding='utf-8')
    assert gate.returncode == 0, gate.stdout + gate.stderr
    audit = dict(status='passed_with_explicit_source_pitch_cause_and_native_execution_gaps', source=ref(Path(__file__)),
        protected_references=len(protected), source_bindings=bindings, existing_response_series=11, matched_words=15,
        source_F0_arrays_read=2, derived_source_stage_rows=6, new_feedback=0, new_response_series=0,
        new_audio_decodes=0, new_F0_detector_calls=0, new_native_calls=0, new_models=0, new_waveforms=0,
        author_arrays_read=0, old_index_rows_exact=True, old_source_F0_SHA_and_word_stats_verified=True,
        knowledge_ID_count=19, next_protocol=ref(RUN / 'design/next-li-entry-pitch-protocol.json'),
        current_index=ref(KNOW / (INDEX + '.json')), current_registry=ref(REGISTRY), gate=gate.stdout.strip(),
        agent_heard=False, adoption=False, measurement_validated=False, general_rule_validated=False)
    save(RUN / 'evaluation/audit.json', audit)
    save(REPORT / (NAME + '-audit.json'), audit)
    docs = [ref(p) for p in sorted(REPORT.glob(NAME + '*'))] + [ref(p) for p in sorted(KNOW.glob(INDEX + '*'))] + [ref(REGISTRY)]
    save(RUN / 'completion-manifest.json', dict(status=report['status'], files=[ref(p) for p in sorted(RUN.rglob('*')) if p.is_file()],
                                               documents=docs, entries=[ref(ROOT / n) for n in ENTRIES]))
    print(json.dumps(dict(status=report['status'], source_stages=stats, nodes=nodes, knowledge_ID_count=19, new_waveforms=0, gate=audit['gate']), ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
