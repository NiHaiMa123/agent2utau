"""Append C≈A feedback and review remaining conditions without new inference."""
import csv
import json
from pathlib import Path
import subprocess
import sys

import yaml

from assemble_lastpage_accepted_baseline_20261011 import ROOT,ENTRIES,load,save,ref,check
from agent2utau.openutau.ustx import TempoMap

PRIOR=ROOT/'runs/experiments/lastpage-author-control-neutral-20261011'
VOICE=ROOT/'runs/experiments/lastpage-author-voice-swap-20261011'
PITCH=ROOT/'runs/experiments/lastpage-author-pitch-ablation-20261011'
BASE=ROOT/'runs/lastpage_loudness_skill_v02_20261007'
RUN=ROOT/'runs/research/lastpage-author-controls-feedback-20261012'
REPORT=ROOT/'docs/reports/lastpage'
NAME='author-controls-feedback-20261012'


def main():
    assert not RUN.exists() and not (REPORT/(NAME+'.json')).exists()
    sealed=load(PRIOR/'completion-manifest.json');check(sealed['files']+sealed['documents']+sealed['entries'])
    protected=load(PRIOR/'protected-before.json')+sealed['files']+sealed['documents']+[ref(PRIOR/'completion-manifest.json')]
    check(protected);RUN.mkdir(parents=True);(RUN/'logs').mkdir();save(RUN/'protected-before.json',protected)
    for n in ENTRIES:
        p=RUN/'before'/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((ROOT/n).read_bytes())
    media=load(PRIOR/'evaluation/delivery-check.json')['outputs']
    feedback=dict(verbatim='很接近a了',submissions=1,date='2026-10-12',response_record='RESP:LASTPAGE-AUTHOR-CONTROL-NEUTRAL-01',
        candidate=media['C'],baseline=media['A'],finding='C perceived very close to author A',
        scope='one aggregate two-phrase comparison; contextual referent C from preceding labeled delivery',
        identical_or_no_difference='unknown: close is not identical',explicit_solidity_dimension='inferred from ongoing solidity comparison; not separately restated',
        exact_C_vs_own_rank='unknown: not directly stated in this reply',break_articulation_level_side_effects='unknown',
        individual_word_labels_added=0,absolute_acceptance='unknown',adoption=False,agent_heard=False,measurement_validated=False)
    check([feedback['candidate'],feedback['baseline']]);save(RUN/'feedback/feedback.json',feedback)
    inputs=[PRIOR/'score/A.ustx',PRIOR/'native-inputs/A-phones.json',BASE/'agent_word_decisions.json',
        BASE/'native_word_geometry.json',BASE/'source_observations.json',ROOT/'docs/knowledge/acoustic-manifestations-20261009/control-details.csv',
        VOICE/'score/B.ustx',VOICE/'evaluation/delivery-check.json',ROOT/'src/agent2utau/openutau/ustx.py']
    bindings=[ref(p) for p in inputs]
    doc=yaml.safe_load(inputs[0].read_text(encoding='utf-8-sig'));part=doc['voice_parts'][0];tm=TempoMap.from_doc(doc)
    notes=part['notes'];phrases=load(inputs[1])['parts'][0]['phrases'][:2]
    decisions={r['word']:r for r in load(inputs[2])};geometry={r['word']:r for r in load(inputs[3])};source={r['word']:r for r in load(inputs[4])['words']}
    primary=[]
    for ix,n in enumerate(notes[:26]):
        if n['lyric'] in ['+','AP','SP','EP']:continue
        children=[ix];j=ix+1
        while j<len(notes) and notes[j]['lyric']=='+':children.append(j);j+=1
        primary.append((ix,n,children))
    assert len(primary)==15 and [n['lyric'] for _,n,_ in primary]==[decisions[w]['char'] for w in range(270,285)]
    rows=[]
    for word,(ix,n,children) in zip(range(270,285),primary):
        d,g,s=decisions[word],geometry[word],source[word]
        hits=[(ctx,p) for ctx,ph in enumerate(phrases) for p in ph['phones'] if ix in p['owner_primary_indices']]
        assert hits and len({ctx for ctx,p in hits})==1
        ap=[p for ctx,p in hits];v=ap[-1];author_vowel=[v['start_ms']/1000,v['end_ms']/1000]
        stages=[]
        for child in children:
            nt=notes[child];lo=part['position']+nt['position'];hi=lo+nt['duration']
            stages.append(dict(note_index=child,tone=nt['tone'],tuning=nt.get('tuning',0),lyric=nt['lyric'],
                start_s=tm.tick_to_ms(lo)/1000,end_s=tm.tick_to_ms(hi)/1000,duration_ticks=nt['duration']))
        own_stages=[dict(a['condition']['music_stage']) for a in d['entry_actions']]
        assert all(a['word']==word for a in own_stages)
        tones=[a['tone']/100 for a in d['entry_actions']];assert tones==[a['tone'] for a in own_stages]
        own_vowel=g['native_vowel'];src_vowel=s['vowel']
        rows.append(dict(word=word,char=d['char'],own_context=d['context'],author_context=hits[0][0],author_primary_note=ix,
            own_music_stages=own_stages,author_music_stages=stages,own_music_tones=tones,author_music_tones=[a['tone'] for a in stages],
            first_tone_author_minus_own=stages[0]['tone']-tones[0],own_entry_family=d['entry_actions'][0]['family'],
            own_native_phone_symbols=[p['phoneme'] for p in g['phones']],author_native_phone_symbols=[p['phoneme'] for p in ap],
            own_native_phone_tones=[p['tone'] for p in g['phones']],author_native_phone_tones=[p['tone'] for p in ap],
            own_vowel_s=own_vowel,author_vowel_s=author_vowel,own_vowel_ms=(own_vowel[1]-own_vowel[0])*1000,
            author_vowel_ms=(author_vowel[1]-author_vowel[0])*1000,
            source_vowel_observed_s=[src_vowel['start'],src_vowel['end']],source_dual_F0_MIDI_stats=s['stats'],source_unknown=s['unknown'],
            matched_by='ordered 15 lyric primaries, explicit + grouping and native owner_primary_indices; repeated 你 kept separate',
            individual_auditory_label='unknown: latest reply is aggregate C-A closeness'))
    assert not any(r['source_unknown'] for r in rows)
    different=[r['word'] for r in rows if r['first_tone_author_minus_own']!=0]
    stage_different=[r['word'] for r in rows if r['own_music_tones']!=r['author_music_tones']]
    assert len(different)==8 and len(stage_different)==8
    focal={r['char']:r for r in rows if r['word'] in [277,283]}
    assert focal['里']['author_music_tones']==[66,68,66] and focal['里']['own_music_tones']==[68,66]
    assert focal['看']['author_music_tones']==[64,66,64] and focal['看']['own_music_tones']==[66,64]
    findings=[
        'C remains perceived very close to A after cancelling three manual deltas; this group is not necessary for reported closeness under these author conditions.',
        'No proof of complete equivalence, no-effect, individual-channel irrelevance, no side effects, or exact C-vs-own ranking.',
        'Speaker swap preference and group-neutral closeness were measured in separate contrasts; speaker×manual-control interaction has not been executed.',
        'Eight of 15 matched words have a lower author first note than own (seven -2 semitones, 抱 -1); they also retain additional onset-stage notes.',
        'Own li/kan each have two stages; author has three, with a lower onset then ascent/descent. Symbolic stage order is not actual F0 or a causal result.',
        'Vowel durations and absolute clocks differ and must be kept separate from pitch/phonation; source dual-F0 statistics are reused observations, not new measurements.'
    ]
    save(RUN/'evaluation/music-timing-review.json',dict(rows=rows,source_bindings=bindings,findings=findings,
        first_tone_differing_words=different,stage_sequence_differing_words=stage_different,
        new_native_calls=0,new_model_calls=0,new_PCM_NPZ_reads=0,source_unknown106_elsewhere_preserved=True))
    next_design=dict(id='LASTPAGE-AUTHOR-SPEAKER-CONTROL-INTERACTION-01',status='frozen_design_not_executed',
        rationale='complete fourth corner before attributing remainder to melody or timing',
        matrix={'A':'author speaker + author controls','B':'own Normal75/Classic25 + author controls',
            'C':'author speaker + neutral controls','D':'own Normal75/Classic25 + neutral controls'},
        existing_scores={'A':ref(PRIOR/'score/A.ustx'),'B':ref(VOICE/'score/B.ustx'),'C':ref(PRIOR/'score/C.ustx')},
        D_recipe={'base':ref(PRIOR/'score/C.ustx'),'replace_only_cl01_cl05':[0,0,75,0,25],'curve_support':'complete original part, explicit total100 mixture; phone CLR unchanged'},
        comparisons=['D-C (speaker with neutral controls)','D-B (control group with own speaker)','(D-C)-(B-A) factorial response proxy only'],
        contexts=[0,1],fixed=['notes/tuning/PITD/note.pitch/vibrato','lyrics/phone clock/CLR','DYN unity/fixed gain1.5','variance11/acoustic101'],
        gates=['D native phone/pitch/vocoder F0 match A/B/C','D variance inputs/predictions match B, except unchanged zero manual curves outside variance',
            'D manual deltas all0 match C','D two-stage speaker exact Normal75/Classic25 match B','D same input repeats exact',
            'all inherited model/PCM/source SHA checked before and after'],
        budget={'new_candidate':1,'new_native_cached_contexts':3,'new_seeded_D_waveforms':4,'D_repeats_per_context':2,
            'independent_contexts':2,'existing_A_B_C_waveforms':'explicit sealed reuse; not new executions','new_F0_calls':4},
        stop='identity/hash/unexpected-dependency/repeat/file-clipping failure; no extra factors or dosage sweep',
        audio_executed=0,model_executed=0,new_score_written=0,auditory_feedback='not_available',adoption=False,
        author_research_only=True,measurement_validated=False,general_rule_validated=False)
    save(RUN/'design/next-interaction-protocol.json',next_design)
    supplement=dict(record_id=feedback['response_record'],append_only_feedback=True,feedback=feedback,
        prior_report=ref(REPORT/'author-control-neutral-20261011.json'),table1_refs=['PER:S1','PARAM:C11.01','PARAM:C12.01','PARAM:C13.01'],
        SHFC_actual_intervention_frames=0,measurement_validated=False,general_rule_validated=False,adoption=False)
    save(RUN/'evaluation/table2-supplement.json',supplement)
    report=dict(status='author_controls_feedback_closed_music_timing_reviewed',feedback=feedback,table2_supplement=supplement,
        conditions=rows,findings=findings,next_protocol=ref(RUN/'design/next-interaction-protocol.json'),new_waveforms=0,new_model_calls=0,
        new_PCM_NPZ_reads=0,agent_heard=False,measurement_validated=False)
    save(REPORT/(NAME+'.json'),report)
    csvrows=[{k:json.dumps(v,ensure_ascii=False) if isinstance(v,(list,dict)) else v for k,v in r.items()} for r in rows]
    with (REPORT/(NAME+'-conditions.csv')).open('x',encoding='utf-8',newline='') as f:
        wr=csv.DictWriter(f,fieldnames=list(csvrows[0]));wr.writeheader();wr.writerows(csvrows)
    md=f'''# 最后一页：作者控制组反馈与剩余条件复核

2026-10-12。用户原话“很接近a了”，计1条聚合回复，绑定新研究C与作者A音频SHA。C取消了TENC/BREC/VOIC三人工增量，焦点SHFC原0且没有实际干预；用户感知C很接近A。在这两个作者上下文里，该组不是保持所报告接近听感的必要条件。**接近不等于完全相同、无影响或无副作用**，也没有直接给出C与自己原版的精确排序，不新增15条逐字标签、绝对自然度或整曲接受。新研究C不覆盖旧3:04抱C。

此前作者A/P/N/PN均比自己的实，声线替换B按语境为A>B>自己的；本次C接近A。这些是分别进行的对照，不能相加成某个因素唯一无关/负责。声线与人工控制组的交互仍未执行，尤其不能跳过交互后把剩余差距直接判为音高或时长病因。

## 15字只读条件复核

按两句有序15个歌词主音符、原生owner_primary_indices和显式+延续组匹配，两个你分开。{len(different)}字作者首音低于自己的首音，其中抱低1半音，其余7字低2半音；音乐阶段序列也有8字不同。里277：自己68→66，作者66→68→66；看283：自己66→64，作者64→66→64。音符主音、音符内音乐阶段与微曲线是不同对象，前面PITD/note.pitch中和没有改变这些notes.tone。

逐字登记双方原生音素/元音时长、音乐阶段物理秒与原声源双F0既有统计；源HFA/GAME/F0是观测，不能以作者较长/较低首音直接覆盖自己的制作或声学真值。作者声明bpm字段120但tempo表实际0tick/70BPM，resolution未写按480；用已绑定TempoMap计算音乐时钟，原生音素时钟另列，没有两边音频重定时/移调。15字source_unknown原false保持，别处word106未知仍保留。全部内容来自已绑定JSON/USTX，只读，不执行模型或解码PCM/NPZ。

## 下一项冻结设计，尚未执行

先补第四角D：以现有C副本为基，**只换为自己的Normal75/Classic25声线**，其余作者音乐/音素/零人工增量保持。D−C检验零控制下的声线，D−B检验自己声线下的控制组，A/B/C旧输入和波形明确封存复用；这比直接调主音/时长更先解决尚未排除的交互。预算两句D/D_repeat共4套新固定种子波形、3句原生缓存技术、4次新双F0，实际均0，D工程尚未写。原声线预测不能直接用于D；预期D variance条件/新预测应精确重现已绑定B，人工增量为0与C一致，两阶段speaker、音符/phones/F0时钟和资源SHA独立检查。限定一个D，不加量/扫比例/追加其他条件，尚无D反馈。

本轮只完成反馈追加、15字条件复核与冻结设计，没有新原生导出、模型执行、音频/数组解码或波形；没有新因果结论、采用或制作版变更。旧pending报告保留封存时态，原工程/音频/Skill/作者原件、旧阴性/抱C保留，表1PER:S1与C11–13、表2RESP:LASTPAGE-AUTHOR-CONTROL-NEUTRAL-01追加，measurement_validated=false、通用规律0、Agent未听，单Agent、CI仅手动。

[15字台账]({NAME}-conditions.csv)、[JSON]({NAME}.json)、[审计]({NAME}-audit.json)。
'''
    (REPORT/(NAME+'.md')).write_text(md,encoding='utf-8',newline='\n')
    status='当前状态author_controls_feedback_closed_music_timing_reviewed：2026-10-12“很接近a了”计1聚合回复，绑定取消三人工增量的作者研究C与A，接近不写成相同/无副作用/逐字接受，组控制非保持该接近听感必要条件，SHFC焦点无实际干预。15字音乐/音素/时长只读复核，8字作者首音低1–2半音且阶段序列不同，源unknown保持；不判为病因。声线与控制组交互尚未做，冻结第四角D=现C+自己Normal75/Classic25，两句4套新D波形预算、实际0，工程未写/模型与新导出0。本轮无PCM/NPZ解码/新波形，旧报告/run/歌曲/音频/Skill/作者原件保持，Agent未听/通用规律0/未采用，单Agent/CI仅手动。'
    for n in ENTRIES:
        p=ROOT/n;lines=p.read_text(encoding='utf-8').splitlines();ix=[i for i,l in enumerate(lines) if '当前状态author_control_neutral_delivered_pending_listening：' in l];assert len(ix)==1,n
        rel='docs/reports/lastpage/'+NAME+'.md'
        if '/' in n:rel=('../../' if n.startswith('research/') else '../../../')+rel
        lines[ix[0]]=('- ' if lines[ix[0]].startswith('- ') else '')+status+f' 见[控制组反馈与剩余条件]({rel})。'
        if n=='plan.md':
            for i,l in enumerate(lines):
                if l.startswith('下一工作进入逐首更新，先《最后一页》：'):lines[i]='下一工作进入逐首更新，先《最后一页》：作者研究C“很接近A”反馈已追加；15字主音/音乐阶段/音素时长差异只读整理，不宣称病因。下一项先按冻结设计补D=取消控制C+自己的声线，完成声线×人工控制第四角；预算两句4新波形及重复，实际0。执行前须核对当前模型/输入/两阶段speaker与A/B/C封存证据，不自动改音符/时长、加量或采用作者制作路线。'
        p.write_text('\n'.join(lines)+'\n',encoding='utf-8',newline='\n')
    check(protected);check(bindings)
    with (REPORT/(NAME+'-conditions.csv')).open(encoding='utf-8',newline='') as f:restored=list(csv.DictReader(f))
    assert len(restored)==15 and all(all(row[k]==('' if v is None else str(v)) for k,v in orig.items()) for row,orig in zip(restored,csvrows))
    gate=subprocess.run([sys.executable,'tools/repository/check_repository.py','--worktree'],cwd=ROOT,capture_output=True,encoding='utf-8')
    (RUN/'logs/repository-gate.log').write_text(gate.stdout+gate.stderr,encoding='utf-8');assert gate.returncode==0,gate.stdout+gate.stderr
    audit=dict(status='passed_with_explicit_closeness_and_cause_gaps',feedback_submissions=1,individual_labels=0,existing_condition_rows=15,
        differing_first_tone_words=different,new_native_calls=0,new_model_calls=0,new_waveforms=0,new_PCM_NPZ_reads=0,
        next_protocol=ref(RUN/'design/next-interaction-protocol.json'),source_bindings=bindings,source=ref(Path(__file__)),
        protected_references=len(protected),CSV_JSON_rows_exact=True,gate=gate.stdout.strip(),agent_heard=False,measurement_validated=False)
    save(RUN/'evaluation/audit.json',audit);save(REPORT/(NAME+'-audit.json'),audit)
    save(RUN/'completion-manifest.json',dict(status=report['status'],files=[ref(p) for p in sorted(RUN.rglob('*')) if p.is_file()],
        documents=[ref(p) for p in sorted(REPORT.glob(NAME+'*'))],entries=[ref(ROOT/n) for n in ENTRIES]))
    print(json.dumps(dict(status=report['status'],feedback=feedback['verbatim'],reviewed_words=15,new_waveforms=0,gate=audit['gate']),ensure_ascii=False))


if __name__=='__main__':main()
