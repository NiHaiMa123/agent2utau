"""Publish one F-E group intervention and seal, without auditory adoption."""
import csv
import json
from pathlib import Path
import subprocess
import sys
from assemble_lastpage_accepted_baseline_20261011 import ROOT,ENTRIES,load,save,ref,check
from lastpage_own_control_neutral_20261012 import RUN,E,PRIOR,runtime

REPORT=ROOT/'docs/reports/lastpage';NAME='own-control-neutral-probe-20261012'

def main():
    assert not (RUN/'completion-manifest.json').exists() and not (REPORT/(NAME+'.json')).exists()
    gates={k:load(RUN/f'evaluation/{k}-independent-check.json') for k in ['native','fresh','delivery']}
    assert all(v['status']=='passed' for v in gates.values())
    for g in gates.values():check([g['checker']])
    runtime();plan=load(RUN/'design/protocol.json');execution=load(RUN/'fresh/execution.json')
    pack=load(RUN/'evaluation/delivery-check.json');obs=load(RUN/'observations/results.json');outputs=pack['outputs']
    check(list(outputs.values()))
    assert len(execution['rows'])==execution['variance_calls']==execution['acoustic_vocoder_waveforms']==4
    assert all(not any(r['feature_clipping'].values()) for r in execution['rows'])
    assert obs['actual_F0_calls']==obs['reused_E_F0_arrays']==4 and len(obs['windows'])==77
    controls=ROOT/'docs/knowledge/acoustic-manifestations-20261009/control-details.csv';atoms=ROOT/'docs/knowledge/acoustic-manifestations-20261009/atomic-manifestations.csv'
    with controls.open(encoding='utf-8-sig',newline='') as f:cr=list(csv.DictReader(f))
    with atoms.open(encoding='utf-8-sig',newline='') as f:ar=list(csv.DictReader(f))
    for abbr,ident in [('voic','PARAM:C11.01'),('tenc','PARAM:C13.01'),('brec','PARAM:C12.01')]:
        assert next(r['id'] for r in cr if r['abbreviation']==abbr)==ident
    assert any(r['id']=='PER:S1' for r in ar)
    rows=[]
    for w in obs['windows']:
        if w['role']!='full_vowel':continue
        core=next(r for r in obs['windows'] if r['word']==w['word'] and r['role']=='core15_85')
        r=dict(word=w['word'],char=w['char'],context=w['context'],both_voice='Bright40/Cute60',
            F_manual_UI='TENC0/BREC0/VOIC100',vowel_RMS_change_db=w['F_minus_E']['level_ratio_db'],
            new_solidity_forward_squeezed_thin_sharp='pending',new_break_articulation_level_kan='unknown',measurement_validated=False)
        for label in ['E','F']:
            for ch in ['breathiness','voicing','tension']:r[f'{label}_{ch}_core_median']=core['variants'][label]['final_features'][ch]['median']
        for detector,d in w['F_minus_E']['F0'].items():
            for k in ['valid_pair_frames','abs_cents_p50','max_abs_cents']:r[detector+'_'+k]=d[k]
        rows.append(r)
    assert [r['word'] for r in rows]==list(range(270,285))
    with (REPORT/(NAME+'-words.csv')).open('x',encoding='utf-8-sig',newline='') as f:
        wr=csv.DictWriter(f,fieldnames=list(rows[0]));wr.writeheader();wr.writerows(rows)
    table1=dict(perception='PER:S1',controls=['PARAM:C11.01','PARAM:C12.01','PARAM:C13.01'],sources=[ref(controls),ref(atoms)],
        related_speaker_parameters=[f'PARAM:C20.0{i}' for i in range(1,6)],
        raw_terms=['前顶','挤','很细','很尖'],formal_mapping_of_raw_terms='unresolved; no physiology/F0/formant/loudness substitution')
    table2=dict(record_id='RESP:LASTPAGE-OWN-CONTROL-NEUTRAL-01',comparison='F-E',status='rendered_checked_pending_human_listening',
        protocol=ref(RUN/'design/protocol.json'),baseline_score=plan['baseline_score'],candidate=outputs['candidate_project'],
        intervention='neutralize three manual curves on own E contexts28/29 existing grids; SHFC unchanged0',
        fixed_voice='Bright40/Cute60',fixed_music_phone_clock_speaker_variance_inputs_predictions=True,
        changed_final_channels=['breathiness','voicing','tension'],predicted_channels_retained=True,single_channel_cause='unknown',
        words=list(range(270,285)),independent_contexts=2,new_variance_calls=4,new_seeded_waveforms=4,
        same_input_repeat_waveforms=2,native_cached_technical_contexts=2,sealed_E_raw_and_PCM_reused=True,
        new_F0_calls=4,reused_E_F0_arrays=4,feature_clipping=0,word_rows=rows,outputs=outputs,
        new_feedback_count=0,adoption=False,independent_holdout=False,agent_heard=False,measurement_validated=False,general_rule_validated=False)
    save(RUN/'evaluation/table2-supplement.json',table2)
    whole=[dict(context=r['context'],RMS_change_db=r['F_minus_E']['level_ratio_db'],F0=r['F_minus_E']['F0']) for r in obs['windows'] if r['role']=='whole_context']
    report=dict(status='own_control_neutral_delivered_pending_listening',table1_refs=table1,table2_supplement=table2,
        execution=execution,delivery=pack,word_rows=rows,whole_context_proxies=whole,
        gates={k:ref(RUN/f'evaluation/{k}-independent-check.json') for k in gates},observations=ref(RUN/'observations/results.json'),
        prior_E_feedback=ref(PRIOR/'feedback/feedback.json'),
        scope='own two complete phrases15words, group intervention; source106 and acceptedbaoC retained',
        old_E_and_author_audio_exact=True,no_parameter_sweep=True,agent_heard=False,measurement_validated=False,general_rule_validated=False,
        next='Receive F/E raw-description and solidity comparison; no automatic additional factors or adoption.')
    save(REPORT/(NAME+'.json'),report)
    table='|字/ID|F−E元音RMS差dB|FCPE差p50/max(c)|RMVPE差p50/max(c)|\n|---|---:|---:|---:|\n'
    for r in rows:table+=f"|{r['char']}/{r['word']}|{r['vowel_RMS_change_db']:+.3f}|{r['FCPE_abs_cents_p50']:.3f}/{r['FCPE_max_abs_cents']:.3f}|{r['RMVPE_abs_cents_p50']:.3f}/{r['RMVPE_max_abs_cents']:.3f}|\n"
    whole_text='；'.join(f"context{r['context']} {r['RMS_change_db']:+.3f}dB" for r in whole)
    md=f'''# 最后一页：E声线下自己的三人工控制组中和F

2026-10-12，状态own_control_neutral_delivered_pending_listening。用户“下一步”授权执行冻结F，前序E反馈“比白烁的更实，但是就有那种前顶的感觉，声音挤得很细很尖”保持原词，不采用E。此次只检查自身人工控制组在E声线下的贡献，没有预先判定TENC/VOIC/BREC单通道病因。

## 固定干预与实际执行

自己的context28/29两完整句“想把你抱进身体里面／不敢让你看见”15字270–284，E完整34part副本只中和两part的TENC0、BREC0、VOIC100，各自原整数5tick曲线xs保持，原正/负人工增量一起取消；三预测基底仍保留，不是三最终模型特征归零。SHFC焦点原0精确保留，没有实际干预。Bright40/Cute60声线及本机percent/default余量、自己notes.tone/tuning/PITD/note.pitch/vibrato、歌词/CLR/音素完整时钟与DYN保持，32其它part及旧接受抱C精确保留。

原生roundtrip读回曲线、phone/完整音高、两阶段speaker embedding、variance全部输入/原生预测逐元素精确E，三人工delta0。两句F/F_repeat共4次新variance及4套新acoustic/vocoder波形，固定variance11/acoustic101，fresh variance输入/三预测逐元素精确E，只有三最终发声输入改变；所有重复输入/预测/mel/raw PCM精确，特征裁剪0。2句原生缓存技术结果另列，E raw/input/波形封存显式复用，未新执行E或作者。两个独立上下文，不将重复或15字窗口当新增独立样本/留出。

## 观测与交付边界

77窗口覆盖两整句、15元音全段/15–85%主体/首尾60ms与可定位辅音，F新FCPE/RMVPE4次，E已有4数组按输入PCM SHA精确复用。无跨无声插值，少于3共同有效帧unknown；原vocoder F0输入精确不保证实际F0完全一致，双检测尚未任务真值校准。独立整句RMS差：{whole_text}。

{table}

第一句你272下降约4.585dB、进274约1.642dB、里277约0.836dB；这些是有限电平响应，不代表用户感知响度/虚实或前顶改善。输入归零不保证其它字波形不响应，声母/邻域和副作用仍须试听。没有补偿增益、归一化、压缩或BGM；固定呈现1.5，不能把听感差自动归于响度或某一通道。

完整245.577秒研究F人声由32旧贡献与2新F贡献按原时钟组装，44100Hz mono PCM24、原生DYN0dB/gain1，峰值{pack['peak']:.6f}。独立重建34贡献、封存E全PCM、F量化与209.4–218.0秒8.6秒预览通过；28/29支撑并集外和抱C PCM精确保持。两句原89ms重叠保持，没有波形重定时/交叉淡化；隔离上下文指标与整曲混合预览分开。F研究工程未采用为原歌曲，原“看”偏实标签保留但F的新标签unknown。

- [F新版两句](../../../{outputs['candidate_preview']['path']})。
- [E原对照](../../../{outputs['original_preview']['path']})：上轮有前顶/挤细尖，原字节保持。
- [作者单独参考](../../../{outputs['author_reference']['path']})：沿用当前1.65c固定11/101作者A，212–220.5秒8.5秒；音乐/时钟不同，只作描述对照，F−E才是人工控制组干预对照。
- [自己的原A](../../../{outputs['own_A_preview']['path']})、[完整研究F工程](../../../{outputs['candidate_project']['path']})、[完整研究F人声](../../../{outputs['candidate_full']['path']})。

下一步只接F相对E前顶/挤细尖是否减轻、实感是否保留，以及看/破音/咬字/响度反馈。新反馈0、未报维度unknown，Agent未听、未采用，measurement_validated=false、通用规律0，不自动扫配比/加量/扩展新因素。表1PER:S1与PARAM:C11.01/C12.01/C13.01及表2RESP:LASTPAGE-OWN-CONTROL-NEUTRAL-01追加，四原词保持尚未严格映射的听觉描述。原歌曲/音频/Skill/作者原件、旧阴性、接受抱C及source_unknown106保持，单Agent、CI仅手动。

[15字CSV]({NAME}-words.csv)、[JSON]({NAME}.json)、[审计]({NAME}-audit.json)。
'''
    (REPORT/(NAME+'.md')).write_text(md,encoding='utf-8',newline='\n')
    status=('当前状态own_control_neutral_delivered_pending_listening：2026-10-12用户“下一步”执行F=E声线与自身音乐/音素条件保持、TENC0/BREC0/VOIC100合组中和，'
        'SHFC原0无干预；15字270–284、三人工增量0，原生/fresh variance输入预测与两阶段speaker精确E，仅三最终通道改变。'
        '4新variance/4波形及重复精确，2原生缓存技术另列、裁剪0；77窗口/4新双F0+4旧E数组及34贡献PCM检查通过、仅代理。'
        '部分元音电平下降不视为虚实/挤尖改善，固定1.5分开F/E/作者参考交付；F待评未采用，32其它贡献/抱C/支撑外PCM保持。'
        '原歌曲/音频/Skill/作者原件/旧阴性/unknown保持，Agent未听/通用规律0，单Agent/CI仅手动。')
    for name in ENTRIES:
        p=ROOT/name;lines=p.read_text(encoding='utf-8').splitlines()
        ix=[i for i,l in enumerate(lines) if '当前状态own_bright_cute_feedback_closed_control_neutral_design_frozen：' in l];assert len(ix)==1,name
        rel='docs/reports/lastpage/'+NAME+'.md'
        if '/' in name:rel=('../../' if name.startswith('research/') else '../../../')+rel
        lines[ix[0]]=('- ' if lines[ix[0]].startswith('- ') else '')+status+f' 见[自己控制组F]({rel})。'
        if name=='plan.md':
            for i,l in enumerate(lines):
                if l.startswith('下一工作进入逐首更新，先《最后一页》：'):
                    lines[i]='下一工作进入逐首更新，先《最后一页》：自己声线E上的三人工控制中和F已交付，下一步只接F相对E前顶/挤细尖与实感保留，以及看/破音/咬字/响度反馈。候选未采用，不自动扩展比例/剂量或音高/时长因素；旧阴性/抱C/unknown保持。'
        p.write_text('\n'.join(lines)+'\n',encoding='utf-8',newline='\n')
    runtime()
    with (REPORT/(NAME+'-words.csv')).open(encoding='utf-8-sig',newline='') as f:restored=list(csv.DictReader(f))
    assert restored==[{k:str(v) for k,v in r.items()} for r in rows]
    gate=subprocess.run([sys.executable,'tools/repository/check_repository.py','--worktree'],cwd=ROOT,capture_output=True,encoding='utf-8')
    (RUN/'logs/repository-gate.log').write_text(gate.stdout+gate.stderr,encoding='utf-8');assert gate.returncode==0,gate.stdout+gate.stderr
    scripts=[ROOT/'research/table2-confirmation'/n for n in ['lastpage_own_control_neutral_20261012.py','check_lastpage_own_control_neutral_20261012.py',
        'package_lastpage_own_control_neutral_20261012.py','observe_lastpage_own_control_neutral_20261012.py',
        'check_lastpage_own_control_neutral_delivery_20261012.py',Path(__file__).name]]
    audit=dict(status='passed_with_explicit_auditory_gaps',scripts=[ref(p) for p in scripts],
        protected_references=len(load(RUN/'protected-before.json')),runtime_resources=len(load(RUN/'native-inputs/runtime.json')),
        actual_new_variance_calls=4,actual_new_waveforms=4,native_cached_contexts=2,actual_new_F0_calls=4,reused_E_F0_arrays=4,
        independent_contexts=2,CSV_JSON_exact=True,gate=gate.stdout.strip(),actual_new_feedback=0,agent_heard=False,adoption=False,
        original_song_audio_Skill_author_unchanged=True,measurement_validated=False,general_rule_validated=False)
    save(RUN/'evaluation/audit.json',audit);save(REPORT/(NAME+'-audit.json'),audit)
    save(RUN/'completion-manifest.json',dict(status=report['status'],files=[ref(p) for p in sorted(RUN.rglob('*')) if p.is_file()],
        documents=[ref(p) for p in sorted(REPORT.glob(NAME+'*'))],entries=[ref(ROOT/n) for n in ENTRIES]))
    print(json.dumps(dict(status=report['status'],whole_context_proxies=whole,gate=audit['gate'],preview=outputs['candidate_preview']),ensure_ascii=False),flush=True)

if __name__=='__main__':main()


