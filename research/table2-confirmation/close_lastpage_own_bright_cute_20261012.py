"""Append E auditory feedback, read bound control state, freeze one next group contrast."""
import csv
import json
from pathlib import Path
import subprocess
import sys
import yaml
from assemble_lastpage_accepted_baseline_20261011 import ROOT,ENTRIES,load,save,ref,check,sha

PRIOR=ROOT/'runs/experiments/lastpage-own-bright-cute-20261012'
RUN=ROOT/'runs/research/lastpage-own-bright-cute-feedback-20261012'
REPORT=ROOT/'docs/reports/lastpage';NAME='own-bright-cute-feedback-20261012'

def main():
    assert not RUN.exists() and not (REPORT/(NAME+'.json')).exists()
    seal=load(PRIOR/'completion-manifest.json');check(seal['files']+seal['documents']+seal['entries'])
    protected=load(PRIOR/'protected-before.json')+seal['files']+seal['documents']+[ref(PRIOR/'completion-manifest.json')]
    check(protected);RUN.mkdir(parents=True);(RUN/'logs').mkdir();save(RUN/'protected-before.json',protected)
    for name in ENTRIES:
        p=RUN/'before'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((ROOT/name).read_bytes())
    media=load(PRIOR/'evaluation/delivery-check.json')['outputs']
    feedback=dict(verbatim='比白烁的更实，但是就有那种前顶的感觉，声音挤得很细很尖',date='2026-10-12',submissions=1,
        record_id='RESP:LASTPAGE-OWN-BRIGHT-CUTE-01',candidate=media['candidate_preview'],author_reference=media['author_reference'],
        own_A_presented=media['original_preview'],referent='E inferred from immediately preceding labelled E/A/author delivery',
        explicit_comparison=dict(dimension='solidity',relation='E > separate author A'),
        candidate_descriptions=['前顶','挤','很细','很尖'],description_scope='aggregate two-phrase sample, precise words/time/intensity scale unknown',
        E_versus_own_A_direct_relation='unknown: not explicitly compared in this reply',
        perceived_loudness_pitch_break_articulation_connection_kan_labels='unknown: not stated',
        overall_preference_or_acceptance='unknown: greater solidity plus adverse descriptions is not overall acceptance',
        individual_word_labels_added=0,adoption=False,agent_heard=False,measurement_validated=False)
    check([feedback['candidate'],feedback['author_reference'],feedback['own_A_presented']]);save(RUN/'feedback/feedback.json',feedback)
    inputs=[PRIOR/'score/lastpage_own_bright_cute_E.ustx',PRIOR/'native-inputs/E/phrase_000.json',PRIOR/'native-inputs/E/phrase_001.json',
        PRIOR/'observations/results.json',PRIOR/'evaluation/fresh-independent-check.json',
        ROOT/'docs/reports/lastpage/author-controls-feedback-20261012.json',ROOT/'docs/reports/lastpage/author-interaction-feedback-20261012.json',
        ROOT/'docs/knowledge/acoustic-manifestations-20261009/atomic-manifestations.csv',
        ROOT/'docs/knowledge/acoustic-manifestations-20261009/control-details.csv']
    bindings=[ref(p) for p in inputs];doc=yaml.safe_load(inputs[0].read_text(encoding='utf-8-sig'));obs=load(inputs[3]);control=[]
    for j,ctx in enumerate([28,29]):
        native=load(inputs[j+1]);p=doc['voice_parts'][ctx]
        assert set(native['tone_shift_cents'])=={0}
        for ch,abbr in [('breathiness','brec'),('voicing','voic'),('tension','tenc')]:
            vals=native['expression_deltas'][ch];curve=next(c for c in p['curves'] if c['abbr']==abbr)
            control.append(dict(context=ctx,channel=ch,abbr=abbr,UI_min=min(curve['ys']),UI_max=max(curve['ys']),
                delta_min=min(vals),delta_max=max(vals),nonzero_native_frames=sum(v!=0 for v in vals),total_native_frames=len(vals)))
    rows=[]
    for r in obs['windows']:
        if r['role']!='core15_85':continue
        rows.append(dict(word=r['word'],char=r['char'],context=r['context'],
            A_final_feature_medians={ch:x['median'] for ch,x in r['variants']['A']['final_features'].items()},
            E_final_feature_medians={ch:x['median'] for ch,x in r['variants']['E']['final_features'].items()},
            new_individual_word_auditory_label='unknown: latest feedback aggregate only'))
    assert len(rows)==15
    review=dict(source_bindings=bindings,controls=control,word_features=rows,
        interpretation=['Own manual increments remain on E while speaker-conditioned predictions change.',
            'No single predicted feature or UI channel proves forward/squeezed/thin/sharp cause; feature units are not physiology or perceived brightness.',
            'Previous author C≈A and D slightly>B are in author music/clock conditions, not proof own E controls have no effect.',
            'E>author solidity is descriptive across different music/clocks; prior isolated E-ownA intervention remains separately bound.',
            'No new waveform/F0/mel/NPZ read; prior JSON predictions and deltas reused.'],
        new_PCM_NPZ_reads=0,new_model_calls=0,new_waveforms=0)
    save(RUN/'evaluation/control-review.json',review)
    nxt=dict(id='LASTPAGE-OWN-BRIGHT-CUTE-CONTROL-NEUTRAL-01',status='frozen_design_not_executed',
        rationale='Test retained own manual control group under E voice before changing speaker dose or musical identity.',
        baseline_score=media['candidate_project'],baseline_media=media['candidate_preview'],author_reference=media['author_reference'],
        contexts=[28,29],words=list(range(270,285)),variant='F',
        recipe=dict(base='complete E34-part copy',replace_only=['tenc','brec','voic'],UI_defaults={'tenc':0,'brec':0,'voic':100},
            scope='existing respective integer5tick grids in context28/29 only; ys neutral, xs and all other curves unchanged',
            SHFC='already0 in selected contexts; preserve, not an intervention',
            voice='Bright40/Cute60 native percent/default residual exact E',
            prediction='speaker/music conditions unchanged so fresh variance must exactly match E; manual deltas zero, legal clip recomputed'),
        fixed=['all notes/tone/tuning/PITD/note.pitch/vibrato','lyrics/phoneme symbols/CLR/full clocks',
            'both-stage speaker','SHFC and vocoder F0 input','native DYN/fixed1.5/PCM24','variance11/acoustic101'],
        comparison='F-E: three-channel manual control GROUP; not a single-channel causal claim',
        gates=['native phone/full pitch/two-stage speaker/variance inputs exact E',
            'all three manual deltas0; native/fresh predictions exact E; final features=legalclip(prediction)',
            'fresh changes restricted to three final channels; repeated inputs/predictions/mel/raw exact',
            'no nonfinite/PCM clipping; original34 assembly and28/29 overlap checked independently',
            '32 other contributions, acceptedbaoC, original A/song/audio/author originals/Skill/old sealed runs retained'],
        budget=dict(candidate_count=1,independent_contexts=2,new_native_cached_contexts=2,new_variance_calls=4,
            new_seeded_waveforms=4,variants_per_context=['F','F_repeat'],sealed_E_reuse=True,new_F0_calls=4),
        listening=['E vs F front/squeezed/thin/sharp','solidity retained or lost','kan/break/articulation/level if reported'],
        stops=['native identity/dependency/A reference/repeat failure','nonfinite/file clipping','no proportions/dose sweep or extra factor'],
        no_normalization_compression_BGM=True,new_score_written=0,new_models_executed=0,new_waveforms=0,
        adoption=False,agent_heard=False,measurement_validated=False,general_rule_validated=False)
    save(RUN/'design/next-own-control-neutral-protocol.json',nxt)
    table1=dict(perception='PER:S1',controls=[f'PARAM:C20.0{i}' for i in range(1,6)]+['PARAM:C11.01','PARAM:C12.01','PARAM:C13.01'],
        unmapped_raw_listener_descriptions=['前顶','挤','很细','很尖'],
        raw_terms_not_forced_to_formant_HNR_F0_nasality_or_spatial_entities=True)
    supplement=dict(record_id=feedback['record_id'],append_only_feedback=True,feedback=feedback,table1_refs=table1,
        prior_report=ref(REPORT/'own-bright-cute-probe-20261012.json'),adoption=False,measurement_validated=False,general_rule_validated=False)
    save(RUN/'evaluation/table2-supplement.json',supplement)
    report=dict(status='own_bright_cute_feedback_closed_control_neutral_design_frozen',feedback=feedback,table2_supplement=supplement,
        control_review=ref(RUN/'evaluation/control-review.json'),next_protocol=ref(RUN/'design/next-own-control-neutral-protocol.json'),
        new_models=0,new_waveforms=0,new_PCM_NPZ_reads=0,agent_heard=False,measurement_validated=False,general_rule_validated=False)
    save(REPORT/(NAME+'.json'),report)
    with (REPORT/(NAME+'-controls.csv')).open('x',encoding='utf-8-sig',newline='') as f:
        wr=csv.DictWriter(f,fieldnames=list(control[0]));wr.writeheader();wr.writerows(control)
    md='''# 最后一页：E实感与前顶、挤细尖反馈

2026-10-12。用户原话“比白烁的更实，但是就有那种前顶的感觉，声音挤得很细很尖”，计1回复。按上轮E/自己A/单独作者参考交付语境绑定E，明确一条实感关系E>作者参考；前顶、挤、很细、很尖作为四个原词并列保留。具体字/时点、强度标尺、与自己A的直接排序及整体偏好未报，不新增15条逐字标签、无破音/咬字正常/看退化或绝对验收。E不采用；“更实”与副作用分开记录，不能将实感单轴最大化当作目标通过。

E与自己A才是已隔离声线因素的对照；E与作者参考仍有音乐阶段/时钟/控制差异。用户本次明确比较的是作者，因此不能把这条反馈改写成E>自己A的直接新标签，也不能当通用最优配比。前顶不强映射为距离、细不等于低电平、尖不等于实际F0升高或共振测量真值；原词记录保留，表1PER:S1与表2RESP:LASTPAGE-OWN-BRIGHT-CUTE-01追加，不新造正式实体。

## 只读控制复核

E仍保留自己的三人工控制，context28原生breathiness增量−0.36～+0.72、101非零帧，voicing0～+10.8、80帧，tension−0.25～+0.90、105帧；context29分别−0.36～+1.08/56帧、0～+2.64/50帧、−0.35～+0.85/59帧。声线切换也已改变三个预测基底。这些是模型单位，不是响度/闭合商/挤压程度；不能靠增量或预测高低确认单通道病因。

已有作者C取消三人工增量后接近A、D取消后仅比B细微改善，均来自作者音乐/音素条件；不能直接推定自己条件下E取消控制也无效。已有E两句电平约+1.206/+1.024dB是代理且未响度匹配，既有数值保留，不代替本次听觉或证明电平唯一致因。15字已有JSON主体特征和6行控制范围只读绑定，本轮不读取PCM/mel/F0/NPZ、不执行模型或新生成音频。

## 下一项冻结F，尚未执行

在E完整副本只将context28/29的TENC=0、BREC=0、VOIC=100，保留各自既有整数5tick网格；SHFC焦点原0保持且不是干预。Bright40/Cute60声线、自己的音乐阶段/所有音高、原生音素完整时钟、CLR、DYN与固定1.5保持。F−E检验三人工增量合组在当前声线下的贡献，包含取消正/负增量；不能解释为单独TENC作用，也不是所有发声特征归零，模型预测仍保留。

两句F/F_repeat预算4次新variance、4套新固定11/101 acoustic/vocoder、2原生缓存技术上下文、4新双F0；E输入/波形显式封存复用。fresh variance条件/预测应逐元素精确E，三人工增量应0，其它输入精确；32其它贡献/接受抱C及28/29自然重叠范围检查。听感目标是前顶、挤细尖是否减轻，以及实感是否保留，未报维度unknown。F工程未写、执行实际0；不扫配比/加量、变音高/时长或增益补偿，尚不承诺改善。

原歌曲/音频/Skill/作者原件、旧阴性、接受抱C与unknown106保持；E原pending报告保留封存时态，本反馈追加。Agent未听、未采用、全部measurement_validated=false、通用规律0，单Agent，CI仅手动。

'''
    md+=f'[控制CSV]({NAME}-controls.csv)、[JSON]({NAME}.json)、[审计]({NAME}-audit.json)。\n'
    (REPORT/(NAME+'.md')).write_text(md,encoding='utf-8',newline='\n')
    status=('当前状态own_bright_cute_feedback_closed_control_neutral_design_frozen：2026-10-12E反馈“比白烁的更实，但前顶、挤得很细很尖”计1聚合回复，'
        '保留E>作者实感及四原词，不补自己A排序/逐字/无破音/绝对接受，E不采用。'
        '自己的三人工增量与声线预测基底只读复核，非单通道病因；下一项冻结F=E声线与自身音高/时钟保持、TENC0/BREC0/VOIC100合组中和，SHFC原0不干预。'
        '两句4新波形/4双F0预算实际0，F工程未写，本轮无PCM/NPZ读取/模型/新音频；原歌曲/音频/Skill/作者原件/旧阴性/抱C/unknown保持，'
        'Agent未听/通用规律0，单Agent/CI仅手动。')
    for name in ENTRIES:
        p=ROOT/name;lines=p.read_text(encoding='utf-8').splitlines()
        ix=[i for i,l in enumerate(lines) if '当前状态own_bright_cute_delivered_pending_listening：' in l];assert len(ix)==1,name
        rel='docs/reports/lastpage/'+NAME+'.md'
        if '/' in name:rel=('../../' if name.startswith('research/') else '../../../')+rel
        lines[ix[0]]=('- ' if lines[ix[0]].startswith('- ') else '')+status+f' 见[E反馈与控制组设计]({rel})。'
        if name=='plan.md':
            for i,l in enumerate(lines):
                if l.startswith('下一工作进入逐首更新，先《最后一页》：'):
                    lines[i]='下一工作进入逐首更新，先《最后一页》：E比作者更实但有前顶/挤细尖，已追加反馈，不采用。下一项冻结F=保留E声线与自身音乐/音素条件，只取消TENC/BREC/VOIC三人工增量，检验副作用减轻与实感保留；4新波形/4双F0预算实际0、F工程未写，不扫比例或同时改音高/时长，旧阴性/抱C/unknown保持。'
        p.write_text('\n'.join(lines)+'\n',encoding='utf-8',newline='\n')
    check(protected);check(bindings)
    with (REPORT/(NAME+'-controls.csv')).open(encoding='utf-8-sig',newline='') as f:restored=list(csv.DictReader(f))
    assert restored==[{k:str(v) for k,v in r.items()} for r in control]
    gate=subprocess.run([sys.executable,'tools/repository/check_repository.py','--worktree'],cwd=ROOT,capture_output=True,encoding='utf-8')
    (RUN/'logs/repository-gate.log').write_text(gate.stdout+gate.stderr,encoding='utf-8');assert gate.returncode==0,gate.stdout+gate.stderr
    audit=dict(status='passed_with_explicit_listener_term_and_causal_gaps',source=ref(Path(__file__)),feedback_submissions=1,
        explicit_solidity_relation_count=1,raw_adverse_descriptions=4,individual_word_labels_added=0,control_rows=6,
        new_native_calls=0,new_model_calls=0,new_waveforms=0,new_PCM_NPZ_reads=0,CSV_JSON_exact=True,
        source_bindings=bindings,next_protocol=ref(RUN/'design/next-own-control-neutral-protocol.json'),
        protected_references=len(protected),gate=gate.stdout.strip(),agent_heard=False,adoption=False,measurement_validated=False)
    save(RUN/'evaluation/audit.json',audit);save(REPORT/(NAME+'-audit.json'),audit)
    save(RUN/'completion-manifest.json',dict(status=report['status'],files=[ref(p) for p in sorted(RUN.rglob('*')) if p.is_file()],
        documents=[ref(p) for p in sorted(REPORT.glob(NAME+'*'))],entries=[ref(ROOT/n) for n in ENTRIES]))
    print(json.dumps(dict(status=report['status'],feedback=feedback['verbatim'],new_waveforms=0,gate=audit['gate']),ensure_ascii=False),flush=True)

if __name__=='__main__':main()
