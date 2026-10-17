"""Version-bound feedback and separate current-runtime author reference research."""
import copy
import csv
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
import soundfile as sf
import yaml

from assemble_lastpage_accepted_baseline_20261011 import sha, ref, load, save, check, ENTRIES, ROOT
from agent2utau.openutau.ustx import TempoMap
from agent2utau.resources.config import load_config

RUN = ROOT / 'runs/research/lastpage-li-kan-author-reference-20261011'
BASE = ROOT / 'runs/lastpage_loudness_skill_v02_20261007'
DELIVERY = ROOT / 'runs/production/lastpage-accepted-baseline-20261011'
AUTHOR = ROOT / 'research/baishuo/projects/最后一页-有参by白烁.ustx'
REPORT = ROOT / 'docs/reports/lastpage'
NAME = 'li-kan-author-reference-20261011'
TEXT = '3：33，基本都是这种为主，就是感觉有点虚，不够实在。实在的比如3:36，的看字就很实在。我的感觉是发音不同，声库的推测不一样。但这也就需要针对这个进行调整。你看下白烁的有什么不同。并且等下给我音频时，单独给他的作为对照'


def command(args, name, executable='a2u-bridge.exe'):
    cfg = load_config()
    exe = Path(cfg['openutau_dir']) / executable
    print('Native reference:', name, flush=True)
    p = subprocess.run([str(exe), *args], cwd=exe.parent, capture_output=True,
                       encoding='utf-8', errors='replace', timeout=1200)
    (RUN / 'logs' / (name + '.log')).write_text(p.stdout + p.stderr, encoding='utf-8')
    assert p.returncode == 0, p.stdout[-2000:] + p.stderr[-1000:]
    result = json.loads(p.stdout.strip().splitlines()[-1])
    assert result.get('ok', True) is not False and not result.get('errors'), result
    save(RUN / 'native-inputs' / (name + '-result.json'), result)
    return result


def prepare():
    assert not RUN.exists()
    old = load(DELIVERY / 'completion-manifest.json')
    check(old['files'] + old['documents'] + old['entries'])
    assert sha(AUTHOR) == '5b064bb96262cf579b13ff7ab28e302e75d641ff4152a9b0e5c33306d7184c2b'
    RUN.mkdir(parents=True)
    (RUN / 'logs').mkdir()
    for n in ENTRIES:
        p = RUN / 'before' / n
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes((ROOT / n).read_bytes())
    protected = old['files'] + old['documents'] + load(DELIVERY / 'evaluation/protected-before.json')
    protected += [ref(AUTHOR), ref(ROOT / 'research/baishuo/manifest.json'),
                  ref(ROOT / 'research/baishuo/baishuo-projects.zip'),
                  ref(ROOT / 'research/singing-expression-examples/source-condition-resource-index.json')]
    save(RUN / 'protected-before.json', protected)
    save(RUN / 'feedback/feedback.json', dict(verbatim=TEXT, source_audio=ref(DELIVERY / 'delivery/lastpage_accepted_C_baseline_vocal.wav'),
         submissions=1, approximate_time_s=213, localized_word=277, localized_char='里',
         localization='time-based attribution; exact word not explicitly named by user',
         feeling='somewhat airy/insufficient solidity', scope='predominant whole-song impression; no per-word blanket labels',
         positive_word=283, positive_char='看', positive_time_s=216,
         positive_scope='explicitly named local solidity; other qualities unknown',
         hypothesis='user suggests phonetic conditions and voicebank prediction; causal attribution unconfirmed',
         request='Compare authorized Baishuo original project; deliver his reference separately',
         device='unknown', playback_extent='unknown', timestamp_precision='approximate', measurement_validated=False))
    a = yaml.safe_load(AUTHOR.read_text(encoding='utf-8-sig'))
    tm = TempoMap.from_doc(a)
    assert a['tracks'][0]['singer'] == 'yousaV1.56'
    part = a['voice_parts'][2]
    assert part['track_no'] == 0
    mapping = {}
    for lyric, word in [('里',277), ('看',283)]:
        ns = [i for i,n in enumerate(part['notes']) if n['lyric'] == lyric]
        assert len(ns) == 1
        i = ns[0]
        stages = [part['notes'][i]]
        j = i + 1
        while j < len(part['notes']) and part['notes'][j]['lyric'] == '+':
            stages.append(part['notes'][j]); j += 1
        mapping[str(word)] = dict(author_original_part=2, author_primary_note=i, lyric=lyric,
             preceding_lyrics=[part['notes'][k]['lyric'] for k in range(max(0,i-3),i) if part['notes'][k]['lyric']!='+'],
             following_lyrics=[part['notes'][k]['lyric'] for k in range(j,min(len(part['notes']),j+3)) if part['notes'][k]['lyric']!='+'],
             authored_stages=[dict(tone=n['tone'],start_s=tm.tick_to_ms(part['position']+n['position'])/1000,
                 end_s=tm.tick_to_ms(part['position']+n['position']+n['duration'])/1000) for n in stages])
    assert mapping['277']['author_primary_note'] == 11 and mapping['283']['author_primary_note'] == 22
    # A separate reference copy; no author nodes become inputs to Agent production.
    r = copy.deepcopy(a)
    r['voice_parts'] = [copy.deepcopy(part)]
    r['wave_parts'] = []
    r['tracks'] = [copy.deepcopy(a['tracks'][0])]
    r['tracks'][0]['singer'] = 'YousaV1.65c'
    r['tracks'][0]['volume'] = 0
    r['tracks'][0]['pan'] = -100
    r['tracks'][0]['mute'] = False
    r['tracks'][0]['solo'] = False
    assert r['voice_parts'][0] == part
    p = RUN / 'score/baishuo-main-part2-current165c.ustx'
    p.parent.mkdir(parents=True)
    p.write_text(yaml.safe_dump(r, allow_unicode=True, sort_keys=False), encoding='utf-8')
    cfg = load_config()
    ou = Path(cfg['openutau_dir'])
    runtime = [ref(ROOT / 'configs/defaults.yaml')]
    external = {}
    for f in ['OpenUtau.Core.dll','a2u-bridge.exe','a2u-bridge.dll','a2u-bridge.deps.json','prefs.json']:
        external[str(ou / f)] = sha(ou / f)
    for f in (ou / 'Singers/YousaV1.65c').rglob('*'):
        if f.is_file() and f.suffix in ['.onnx','.emb','.yaml']:
            external[str(f)] = sha(f)
    save(RUN / 'native-inputs/runtime-binding.json', external)
    plan = dict(scope='read-only author research, separate current-runtime reference; own production controls unchanged',
        original=ref(AUTHOR), reference_copy=ref(p), own_source=ref(DELIVERY / 'delivery/lastpage_accepted_C_baseline_vocal.wav'),
        reference_historical_audio=False, author_original_singer='yousaV1.56', rendering_singer='YousaV1.65c',
        original_part=2, original_track=0, excluded='harmony and muted analysis/reference tracks; backing',
        musical_notes_pitch_curves_and_controls_exact=True,
        setup_changes=['extract complete original part2', 'singer current165c', 'neutral volume0/panleft for scalar raw vocal export', 'no waves'],
        authored_track_gain_separated=a['tracks'][0]['volume'], fixed_vocal_gain_after_export=1.5,
        budget=dict(reference_part_renders=1, expected_native_phrases=3, own_new_candidates=0),
        seed='native cache/inference; no claim of fixed11/101 fresh reconstruction',
        comparison='same lyric sequence research; different model version, music stages, clocks and voice colors; not single factor',
        mapping=mapping, side_effects_and_agent_perception='unknown; Agent has not heard',
        prior_negative_experiments_preserved=True, author_curve_transfer_to_production=False,
        source_unknown_masks_unchanged=True, measurement_validated=False,
        future_delivery='author and own vocals as separate files, original timelines and label differences explicit')
    save(RUN / 'design/reference-plan.json', plan)
    print('Prepared: bound one feedback, author part2 exact, current165c reference only.', flush=True)
    command(['export-phonemes','--project',str(p),'--out',str(RUN/'native-inputs/author-phones.json')], 'phones')
    command(['inspect','--project',str(p)], 'inspect')
    command(['render','--project',str(p),'--out',str(RUN/'native-render/author-native.wav'),'--mixdown','--timeout','15'], 'render')
    command(['export-render-probe','--project',str(p),'--out',str(RUN/'native-inputs/probe'),'--indices','0,1,2'], 'probe')
    print('Native reference material ready; comparison and separate delivery still to finish.', flush=True)


def resume_probe():
    assert (RUN / 'native-inputs/render-result.json').exists()
    assert not (RUN / 'native-inputs/probe-diagnostic-result.json').exists()
    exe = Path(load_config()['openutau_dir']) / 'a2u-shfcprobe-20261008.exe'
    runtime = {str(exe.with_suffix(ext)): sha(exe.with_suffix(ext))
               for ext in ['.exe', '.dll', '.deps.json', '.runtimeconfig.json']}
    save(RUN / 'native-inputs/probe-bridge-binding.json', runtime)
    save(RUN / 'native-inputs/probe-version-repair.json', dict(
        failure='Installed base bridge did not expose export-render-probe; author render and phones succeeded',
        action='Use existing separately installed diagnostic bridge for same project/cache without any rerender',
        old_failure_log=ref(RUN / 'logs/probe.log'), source_project_unchanged=True,
        runtime_rebuilt_or_redeployed=False))
    p = RUN / 'score/baishuo-main-part2-current165c.ustx'
    command(['export-render-probe','--project',str(p),'--out',str(RUN/'native-inputs/probe'),
             '--indices','0,1,2'], 'probe-diagnostic', executable=exe.name)


def tensor(doc, name):
    q = next(x for x in doc['tensors'] if x['name'] == name)
    return np.asarray(q['values'], dtype=np.float32).reshape(q['shape'])


def summary(x):
    return dict(min=float(np.min(x)), median=float(np.median(x)), max=float(np.max(x)))


def speaker(doc, root):
    names = ['Bright','Classic','Cute','Normal','Whisper']
    vectors = np.stack([np.fromfile(root / f'Yousa_{n}.emb', dtype='<f4') for n in names], axis=1)
    actual = tensor(doc, 'spk_embed').reshape(-1, vectors.shape[0])
    weights = np.linalg.lstsq(vectors.astype(np.float64), actual.T.astype(np.float64), rcond=None)[0].T
    error = float(np.max(np.abs(weights @ vectors.T - actual)))
    assert error < 1e-6
    return dict(weights=dict(zip(names, np.median(weights, axis=0).tolist())), reconstruction_max_abs=error,
                observed='actual tensor decomposition; not inferred from curve labels')


def finish():
    assert (RUN / 'native-inputs/probe-diagnostic-result.json').exists()
    assert not (RUN / 'completion-manifest.json').exists()
    assert not (REPORT / (NAME + '.json')).exists()
    check(load(RUN / 'protected-before.json'))
    for n in ENTRIES:
        assert (ROOT/n).read_bytes() == (RUN/'before'/n).read_bytes(), n
    for name in ['runtime-binding.json','probe-bridge-binding.json']:
        for p, expected in load(RUN/'native-inputs'/name).items():
            assert sha(Path(p)) == expected, p
    plan = load(RUN / 'design/reference-plan.json')
    author = yaml.safe_load(AUTHOR.read_text(encoding='utf-8-sig'))
    part = author['voice_parts'][2]
    tm = TempoMap.from_doc(author)
    phones = load(RUN / 'native-inputs/author-phones.json')['parts'][0]['phrases']
    geometry = load(BASE / 'native_word_geometry.json')
    decisions = load(BASE / 'agent_word_decisions.json')
    state_summary = load(BASE / 'all_word_current_prediction_and_final_inputs.json')
    inputs = [ref(BASE / n) for n in ['native_word_geometry.json','agent_word_decisions.json',
              'all_word_current_prediction_and_final_inputs.json','synthesis_check.json']]
    cases = []
    rows = []
    for word, ix in [(277,0),(283,1)]:
        orig = plan['mapping'][str(word)]
        primary = orig['author_primary_note']
        pp = [p for p in phones[ix]['phones'] if primary in p['owner_primary_indices']]
        own_pp = geometry[word]['phones']
        assert [p['phoneme'] for p in pp] == [p['phoneme'] for p in own_pp]
        vowel = pp[-1]
        a,b = vowel['start_ms']/1000, vowel['end_ms']/1000
        own_a,own_b = geometry[word]['native_vowel']
        f = load(RUN/f'native-inputs/probe/phrase_{ix:03}.json')
        vf = load(RUN/f'native-inputs/probe/variance_{ix:03}.json')
        assert f['native_acoustic_cache_verified'] and vf['native_variance_cache_verified']
        clock = (f['position_ms'] - f['head_frames'] * f['frame_ms'] + np.arange(len(f['vocoder_f0']))*f['frame_ms'])/1000
        mask = (clock >= a) & (clock < b)
        core = (clock >= a + .15*(b-a)) & (clock < b - .15*(b-a))
        assert mask.sum() > 20 and core.sum() > 10
        current_ix = decisions[word]['context']
        cf = load(BASE/f'feeds/phrase_{current_ix:03}.json')
        cs = load(BASE/f'synthesis/phrase_{current_ix:03}.json')
        cclock = cs['wave_start_s'] + np.arange(len(cf['vocoder_f0']))*cf['frame_ms']/1000
        cm = (cclock >= own_a) & (cclock < own_b)
        cc = (cclock >= own_a+.15*(own_b-own_a)) & (cclock < own_b-.15*(own_b-own_a))
        sp_a = speaker(f, Path(f['singer_location']))
        sp_v = speaker(vf, Path(vf['variance_speaker_root']))
        own_sp = speaker(cf, Path(cf['singer_location']))
        assert abs(sp_a['weights']['Bright']-.4)<1e-6 and abs(sp_a['weights']['Cute']-.6)<1e-6
        assert abs(sp_v['weights']['Bright']-.4)<1e-6 and abs(sp_v['weights']['Cute']-.6)<1e-6
        assert abs(own_sp['weights']['Normal']-.75)<1e-6 and abs(own_sp['weights']['Classic']-.25)<1e-6
        controls = {}
        for abbr in ['voic','brec','tenc','shfc','cl01','cl02','cl03','cl04','cl05']:
            curve = next(q for q in part['curves'] if q['abbr'] == abbr)
            samples = np.linspace(a,b,101)
            ticks = np.asarray([tm.ms_to_tick(t*1000)-part['position'] for t in samples])
            projected = (np.interp(ticks,curve['xs'],curve['ys']) if curve['xs'] else
                         np.full(len(ticks),author['expressions'][abbr]['default_value']))
            controls[abbr] = dict(**summary(projected), empty_curve_uses_declared_default=not curve['xs'])
        features = {}
        state_path = BASE/f'synthesis/state_{current_ix:03}.npz'
        with np.load(state_path,allow_pickle=False) as state:
            for name in ['breathiness','voicing','tension']:
                af = tensor(f,name).reshape(-1)
                ap = np.asarray(f['native_variance_predictions'][name],dtype=np.float32).reshape(-1)
                ad = np.asarray(f['expression_deltas'][name],dtype=np.float32).reshape(-1)
                lo,hi = (-10,10) if name=='tension' else (-96,0)
                assert np.array_equal(np.clip(ap+ad,lo,hi),af), name
                # Native diagnostic feeds contain native/cache predictions,
                # while the delivered v02 was made with fresh seed11/101.
                # The feed SHA binds the common template, not those final
                # seeded features. Read the delivered synthesis state itself.
                assert cs['inputs']['acoustic_feed'] == sha(BASE/f'feeds/phrase_{current_ix:03}.json')
                assert cs['inputs']['variance_seed'] == 11 and cs['inputs']['acoustic_seed'] == 101
                final = state['final_'+name].reshape(-1)
                delta = state['delta_'+name].reshape(-1)
                assert np.array_equal(delta,np.asarray(cf['expression_deltas'][name],dtype=np.float32))
                assert np.array_equal(np.clip(state[name].reshape(-1)+delta,lo,hi),final)
                features[name] = dict(author_prediction=summary(ap[mask]),author_final=summary(af[mask]),
                     author_delta=summary(ad[mask]), author_core_final=summary(af[core]),
                     own_prediction=summary(state[name].reshape(-1)[cm]),own_final=summary(final[cm]),
                     own_delta=summary(state['delta_'+name].reshape(-1)[cm]),own_core_final=summary(final[cc]),
                     units='native model feature; not PCM dB or physiological measure',
                     author_clipped_frames=int(np.count_nonzero((ap+ad<lo)|(ap+ad>hi))))
        inputs += [ref(state_path),ref(BASE/f'feeds/phrase_{current_ix:03}.json'),
                   ref(BASE/f'synthesis/phrase_{current_ix:03}.json')]
        case = dict(word=word,char=decisions[word]['char'],native_context=current_ix,
             user_label='reported_airy_near_time' if word==277 else 'reported_locally_solid',
             localization='approximate-time' if word==277 else 'explicit-lyric',
             matching='same lyric/neighbor phrase and phoneme sequence; not by uniform offset',
             author=orig,author_vowel_s=[a,b],own_vowel_s=[own_a,own_b],
             phones_author=pp,phones_own=own_pp,
             own_music_stages=[dict(cents=e['tone'],onset_s=e['onset'],body_end_s=e['body_end']) for e in decisions[word]['entry_actions']],
             author_written_controls=controls,own_control_events=decisions[word]['controls'],
             speaker_author_acoustic=sp_a,speaker_author_variance=sp_v,speaker_own_acoustic=own_sp,
             features=features,frames_author=int(mask.sum()),frames_own=int(cm.sum()),
             own_state_source='seed11/101 delivered state NPZ; native feed used for common clock/F0/deltas/speaker only',
             SHFC_author_input=summary(np.asarray(f['tone_shift_cents'])[mask]),
             F0_vocoder_author=summary(np.asarray(f['vocoder_f0'])[mask]),F0_vocoder_own=summary(np.asarray(cf['vocoder_f0'])[cm]),
             causal_isolation=False,historical_author_audio=False,agent_heard=False,measurement_validated=False)
        cases.append(case)
        rows.append(dict(word=word,char=case['char'],label=case['user_label'],own_vowel_start=own_a,
             own_vowel_end=own_b,author_vowel_start=a,author_vowel_end=b,
             own_voicing_predicted=features['voicing']['own_prediction']['median'],
             own_voicing_final=features['voicing']['own_final']['median'],
             author_voicing_predicted=features['voicing']['author_prediction']['median'],
             author_voicing_final=features['voicing']['author_final']['median'],
             author_written_voic=controls['voic']['median'],author_written_brec=controls['brec']['median'],
             author_speaker='Bright40/Cute60 actual both stages',own_speaker='Normal75/Classic25',
             interpretation='multiple co-varying conditions; no unique cause',measurement_validated=False))
    # Broader inventory remains developmental metadata, not blanket negative labels.
    with (REPORT/'whole-song-baseline-review-20261011-words.csv').open(encoding='utf-8',newline='') as f:
        inventory=list(csv.DictReader(f))
    grouped=[]
    for target in [inventory[277],inventory[283]]:
        ids=[int(w['word']) for w in inventory if w['vowel']==target['vowel'] and w['midi']==target['midi']]
        grouped.append(dict(vowel=target['vowel'],nominal_midi=target['midi'],words=ids,
            predicted_voicing_medians=[state_summary[i]['predicted_voicing_median'] for i in ids],
            note='same nominal vowel/tone still varies in context/pitch/duration/controls; other quality labels remain unknown'))
    save(RUN/'evaluation/comparison.json',dict(cases=cases,same_vowel_nominal_tone_inventory=grouped,input_bindings=inputs))
    raw,sr=sf.read(RUN/'native-render/author-native.wav',dtype='float64')
    assert sr==44100 and raw.ndim==2 and raw.shape[1]==2
    # Hard-left neutral fader provides mono reference without a center-pan loss.
    assert np.max(np.abs(raw[:,1])) == 0
    author_window=[212.0,220.35]
    own_window=[209.4,218.0]
    left,right=[round(t*sr) for t in author_window]
    y=raw[left:right,0]*1.5
    assert np.isfinite(y).all() and np.max(np.abs(y))<1
    out=RUN/'delivery';out.mkdir()
    author_out=out/'baishuo_current165c_reference_vocal.wav'
    sf.write(author_out,y,sr,subtype='PCM_24')
    own_pcm,own_rate=sf.read(DELIVERY/'delivery/lastpage_accepted_C_baseline_vocal.wav',dtype='int32')
    left,right=[round(t*sr) for t in own_window]
    own_out=out/'agent_acceptedC_same_lyrics_vocal.wav'
    sf.write(own_out,own_pcm[left:right],sr,subtype='PCM_24')
    reread,rate=sf.read(own_out,dtype='int32')
    assert own_rate==rate==sr and np.array_equal(reread,own_pcm[left:right])
    author_pcm,rate=sf.read(author_out,dtype='int32')
    assert rate==sr
    clipped=int(np.count_nonzero((author_pcm==2147483392)|(author_pcm==-2147483648)))
    assert clipped==0
    delivered= dict(author=ref(author_out),own=ref(own_out),author_window_s=author_window,own_window_s=own_window,
       author_word_offsets={str(c['word']):[v-author_window[0] for v in c['author_vowel_s']] for c in cases},
       own_word_offsets={str(c['word']):[v-own_window[0] for v in c['own_vowel_s']] for c in cases},
       independent_files=True,own_PCM_exact_extraction=True,reference_fixed_gain=1.5,
       author_track_gain_removed_for_reference_only=True,reference_peak=float(np.max(np.abs(y))),
       source_native_reference_subtype='PCM_16; PCM_24 packaging does not restore lost precision',
       fullscale_samples=clipped,no_normalization_or_compression=True,retiming_or_transposition=False,
       historical_author_recording=False,agent_heard=False)
    save(RUN/'evaluation/delivery-check.json',delivered)
    report=dict(status='feedback_bound_author_reference_compared_and_separately_delivered',feedback=ref(RUN/'feedback/feedback.json'),
       cases=cases,broader_inventory=grouped,deliveries=delivered,input_bindings=inputs,plan=ref(RUN/'design/reference-plan.json'),
       findings=['Current li and kan differ in prediction and final model inputs despite positive li VOIC overlay',
          'Author reference actual speaker is Bright40/Cute60 at variance and acoustic stages, unlike own Normal75/Classic25',
          'Author retains lower entry stages and within-word turns, and varying negative/positive tension; not simple larger VOIC',
          'Authored BREC+8/VOIC88(li),96(kan)/SHFC0 cannot alone establish perceived solidity',
          'Phones match at symbolic level; native durations and music stages differ; no phoneme misidentification proved'],
       input_slot_audit='Initial check caught native cached feed features vs seed11/101 delivered state mismatch; states are independently reconstructed from their own predicted base and identical native manual deltas, no tolerance relaxation',
       next_direction='Design a finite own phrase-scale phonation baseline correction conditioned on current vowel/core and prediction; protect kan283 and accepted bao225; no author curve copying or uniform global offset',
       own_new_candidate_count=0,new_human_feedback=1,general_rule_validated=False,measurement_validated=False)
    save(REPORT/(NAME+'.json'),report)
    with (REPORT/(NAME+'-comparison.csv')).open('x',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    li,kan=cases
    md=f'''# 最后一页“里/看”反馈与白烁独立对照

2026-10-11。状态：feedback_bound_author_reference_compared_and_separately_delivered。

用户原话：“{TEXT}”。绑定新整曲接受C人声SHA；计1条回复。“多数偏虚”为整曲印象，3:33暂定位word277“里”（212.957–213.585s），未经用户逐字命名；“看”word283（216.326–217.081s）是明确的局部偏实正例。不能给全部字贴偏虚标签，也不能把“看”扩成所有维度通过。

## 实际差异

| 项目 | 自身当前 | 白烁工程当前1.65c参考 |
|---|---|---|
| 里/看音素 | l→i；k→an | 符号相同；真实元音时长为{li['author_vowel_s'][1]-li['author_vowel_s'][0]:.3f}/{kan['author_vowel_s'][1]-kan['author_vowel_s'][0]:.3f}s，原生时钟不同 |
| 里音乐阶段 | 68→66 | 66→68→66 |
| 看音乐阶段 | 66→64 | 64→66→64 |
| speaker | Normal75/Classic25 | 实际两阶段Bright40/Cute60，嵌入重建误差<1e-6 |
| 手工VOIC | 里已有有限+15（UI 115）；看100零增量 | 里88；看96 |
| 手工BREC/SHFC | 两字无新增气声/条件移调 | BREC+8、SHFC0 |
| 张力 | 两字无新张力增量 | 里约−28→+9→−22；看主要负向随阶段变化 |

自身里预测VOIC中位{li['features']['voicing']['own_prediction']['median']:.3f}、最终{li['features']['voicing']['own_final']['median']:.3f}，看预测/最终{kan['features']['voicing']['own_final']['median']:.3f}。这些是模型特征单位，不是实际谐波电平/生理发声量。最终里低于看，支持检查发音/音区/上下文依赖的方向；两字不是单因素对照，不能确认唯一原因。声母/元音符号匹配，没有据此拆音素或宣布模型映射故障。

核查先拒绝了native/cache导出发声特征与seed11/101实际交付状态的混用。旧feed SHA绑定的是共同模板；本报告以实际交付state NPZ的预测/人工增量/最终输入为准，逐项精确重建，native feed只用于共同音高、时钟、speaker与增量。白烁是本次native当前参考，推理/缓存策略亦不同，保留比较边界，不放宽容差。

白烁并非统一使用更大VOIC或更少气声。声线、较低入口、字内换音及张力形状同时不同，参考声音的虚实尚待用户听。这里研究处理与反例，不把作者数组、数值节点、曲线或声线配方接入自身制作。

## 单独试听

白烁原工程为yousaV1.56，本机只有1.65b/c；没有作者历史音频。本次保留主唱原part2的42音符与全部曲线，独立换当前1.65c渲染3原生句；和声/伴奏不加入。工程原件/自身工程/旧音频/Skill保持。参考仅将轨道输出增益与声像中和后统一固定增益1.5；native PCM16再封装PCM24，精度不升级。自身片段为原整曲PCM精确截取。无转调、重定时、归一化或压缩；不是单因素因果对照。

- [自身原版本人声](../../../{delivered['own']['path']})：原209.4–218.0秒；里约3.56–4.19秒，看约6.93–7.68秒。
- [白烁工程当前1.65c参考](../../../{delivered['author']['path']})：原212.0–220.35秒；里约3.57–4.24秒，看约7.01–7.73秒。此文件是当前重渲染，非历史作者录音。

表1记录虚/实听感例证及局部范围；表2记录版本反馈、两字实际预测/增量/最终输入与当前作者参考差异，不把关联升级为响应规律。同元音/标称音区的其它条件另存清单，听感未知保持。新反馈1、自身新候选0、通用规律0，measurement_validated仍false，Agent未听。

下一轮自行设计以整句发声走向和元音主体为单位，区分基底不足与阶段动作；保留看283及已接受抱225。先明确有限补偿/控制范围与副作用检查，再完整重建受影响预测和波形。停止的TENC/BREC/果SHFC剂量探索不恢复；不以响度加大代替虚实改善。

基础桥的参考渲染成功，但诊断命令缺失；失败日志保留。用已安装独立诊断桥导出同项目/缓存实际输入，没有重渲染或覆盖安装。两阶段speaker、预测+实际增量=裁剪后输入、缓存键、符号身份、输出/保护SHA及仓库门禁核对；新参考听感待评。

[完整JSON]({NAME}.json)、[比较CSV]({NAME}-comparison.csv)、[审计]({NAME}-audit.json)。
'''
    (REPORT/(NAME+'.md')).write_text(md,encoding='utf-8',newline='\n')
    status=('当前状态feedback_bound_author_reference_compared_and_separately_delivered：2026-10-11新整曲1条反馈“多数偏虚”保留整曲范围，'
      '3:33暂定位里277、3:36看283明确局部偏实，不批量标签。里已有VOIC增量且预测/最终状态与看不同；'
      '白烁同歌词主唱part2原42音符/曲线保留，独立当前1.65c重渲染3句并分开交付参考/自身原PCM片段，作者历史1.56声音不可用。'
      '实际两阶段Bright40/Cute60及较低入口/转音/张力与自身75Normal/25Classic不同，多因素关联非病因；自身新候选0，不移植作者曲线。'
      '下步有限整句/元音主体发声设计，保护看283/接受抱225及阴性与unknown；原歌曲/Skill不改、Agent未听、通用规律0、单Agent/CI仅手动。')
    for name in ENTRIES:
        p=ROOT/name;text=p.read_text(encoding='utf-8');lines=text.splitlines()
        ix=[i for i,l in enumerate(lines) if '当前状态whole_song_baseline_audited_and_delivered_pending_listening：' in l]
        assert len(ix)==1,name
        prefix='- ' if lines[ix[0]].startswith('- ') else ''
        relative='docs/reports/lastpage/'+NAME+'.md'
        if '/' in name:relative=('../../' if name.startswith('research/') else '../../../')+relative
        lines[ix[0]]=prefix+status+f' 见[里/看与白烁对照]({relative})。'
        for i,l in enumerate(lines):
            if name=='plan.md' and l.startswith('下一工作进入逐首更新，先《最后一页》：'):
                lines[i]='下一工作进入逐首更新，先《最后一页》：里/看虚实反馈与白烁多因素差异已核查并交付分开人声。下一轮先明确整句发声走向/有限元音主体补偿，保护看283及接受抱225，独立设计原生控制，重建实际预测与新波形，再回填表1/表2；不复制作者曲线或恢复阴性加量。'
        p.write_text('\n'.join(lines)+'\n',encoding='utf-8',newline='\n')
    check(load(RUN/'protected-before.json'));check(inputs)
    for name in ['runtime-binding.json','probe-bridge-binding.json']:
        for p, expected in load(RUN/'native-inputs'/name).items():assert sha(Path(p))==expected,p
    gate=subprocess.run([sys.executable,'tools/repository/check_repository.py','--worktree'],cwd=ROOT,
         capture_output=True,encoding='utf-8')
    (RUN/'logs/repository-gate.log').write_text(gate.stdout+gate.stderr,encoding='utf-8')
    assert gate.returncode==0,gate.stdout+gate.stderr
    audit=dict(status='passed_with_explicit_causal_and_historical_audio_gaps',source_audio=ref(DELIVERY/'delivery/lastpage_accepted_C_baseline_vocal.wav'),
       inputs=inputs,protected_files=len(load(RUN/'protected-before.json')),new_feedback=1,own_model_execution=0,
       author_current_reference_part_renders=1,author_native_phrases=3,same_symbolic_phones=True,
       native_actual_speakers_both_stages=True,actual_control_arithmetic=True,old_PCM_exact_extraction=True,
       no_author_transfer_to_production=True,author_original_bytes_exact=True,original_Skill_and_song_unchanged=True,
       source_unknowns_unchanged=True,agent_heard=False,measurement_validated=False,gate=gate.stdout.strip(),
       script=ref(Path(__file__)),delivery=delivered)
    save(RUN/'evaluation/audit.json',audit);save(REPORT/(NAME+'-audit.json'),audit)
    files=[ref(p) for p in sorted(RUN.rglob('*')) if p.is_file()]
    docs=[ref(p) for p in sorted(REPORT.glob(NAME+'*'))]
    save(RUN/'completion-manifest.json',dict(status=audit['status'],files=files,documents=docs,entries=[ref(ROOT/n) for n in ENTRIES]))
    print(json.dumps(dict(status=audit['status'],case_rows=rows,deliveries=delivered,gate=audit['gate']),ensure_ascii=False),flush=True)


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'resume-probe':
        resume_probe()
    elif len(sys.argv) > 1 and sys.argv[1] == 'finish':
        finish()
    else:
        prepare()
