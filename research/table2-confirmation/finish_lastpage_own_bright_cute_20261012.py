"""Publish finite E response proxies and seal; auditory acceptance remains pending."""
import csv
import json
from pathlib import Path
import subprocess
import sys
from assemble_lastpage_accepted_baseline_20261011 import ROOT,ENTRIES,load,save,ref,check,sha
from lastpage_own_bright_cute_20261012 import RUN,runtime

REPORT=ROOT/'docs/reports/lastpage';NAME='own-bright-cute-probe-20261012'

def main():
    assert not (RUN/'completion-manifest.json').exists() and not (REPORT/(NAME+'.json')).exists()
    gates={k:load(RUN/f'evaluation/{k}-independent-check.json') for k in ['native','fresh','delivery']}
    assert all(v['status']=='passed' for v in gates.values())
    for g in gates.values():check([g['checker']])
    runtime();plan=load(RUN/'design/protocol.json');exe=load(RUN/'fresh/execution.json')
    pack=load(RUN/'evaluation/delivery-check.json');obs=load(RUN/'observations/results.json')
    check(list(pack['outputs'].values()))
    assert exe['variance_calls']==exe['acoustic_vocoder_waveforms']==8 and len(exe['rows'])==8
    assert all(not any(r['feature_clipping'].values()) for r in exe['rows'])
    assert obs['actual_F0_calls']==8 and len(obs['windows'])==77
    controls=ROOT/'docs/knowledge/acoustic-manifestations-20261009/control-details.csv'
    atoms=ROOT/'docs/knowledge/acoustic-manifestations-20261009/atomic-manifestations.csv'
    with controls.open(encoding='utf-8-sig',newline='') as f:cr=list(csv.DictReader(f))
    with atoms.open(encoding='utf-8-sig',newline='') as f:ar=list(csv.DictReader(f))
    for i in range(1,6):assert next(r['id'] for r in cr if r['abbreviation']==f'cl0{i}')==f'PARAM:C20.0{i}'
    assert any(r['id']=='PER:S1' for r in ar)
    rows=[]
    for w in obs['windows']:
        if w['role']!='full_vowel':continue
        core=next(r for r in obs['windows'] if r['word']==w['word'] and r['role']=='core15_85')
        r=dict(word=w['word'],char=w['char'],context=w['context'],A_voice='Normal75/Classic25',E_voice='Bright40/Cute60',
            vowel_RMS_change_db=w['E_minus_A']['level_ratio_db'],E_solidity_connection='pending',
            E_break_articulation_loudness='unknown',measurement_validated=False)
        for label in ['A','E']:
            for ch in ['breathiness','voicing','tension']:r[f'{label}_{ch}_core_median']=core['variants'][label]['final_features'][ch]['median']
        for detector,d in w['E_minus_A']['F0'].items():
            for k in ['valid_pair_frames','abs_cents_p50','max_abs_cents']:r[detector+'_'+k]=d[k]
        rows.append(r)
    assert [r['word'] for r in rows]==list(range(270,285))
    with (REPORT/(NAME+'-words.csv')).open('x',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    table1=dict(perception='PER:S1',controls=[f'PARAM:C20.0{i}' for i in range(1,6)],sources=[ref(controls),ref(atoms)],
        original_labels='aggregate own airy, original kan283 solid; no15 individual airy labels inferred; E pending')
    table2=dict(record_id='RESP:LASTPAGE-OWN-BRIGHT-CUTE-01',comparison='E-own_A',status='rendered_checked_pending_human_listening',
        protocol=ref(RUN/'design/protocol.json'),contexts=[28,29],words=list(range(270,285)),
        intervention='constant named cl01..05=[40,60,0,0,0] on own two phrases; native float percent and default residual exact',
        music_phone_clock_manual_controls_DYN_held=True,both_stages_speaker_rebuilt=True,variance_predictions_recomputed=True,
        predicted_final_channels=['breathiness','voicing','tension'],fixed_vocoder_F0_input=True,actual_F0_truth='unknown',
        independent_contexts=2,same_input_repeats=4,new_variance_calls=8,new_acoustic_vocoder_waveforms=8,
        native_cached_technical_contexts=4,new_F0_calls=8,feature_clipping=0,word_rows=rows,outputs=pack['outputs'],
        new_feedback_count=0,adoption=False,independent_holdout=False,agent_heard=False,measurement_validated=False,general_rule_validated=False)
    save(RUN/'evaluation/table2-supplement.json',table2)
    whole=[dict(context=r['context'],RMS_change_db=r['E_minus_A']['level_ratio_db'],F0=r['E_minus_A']['F0']) for r in obs['windows'] if r['role']=='whole_context']
    report=dict(status='own_bright_cute_delivered_pending_listening',table1_refs=table1,table2_supplement=table2,
        execution=exe,delivery=pack,whole_context_proxies=whole,word_rows=rows,
        gates={k:ref(RUN/f'evaluation/{k}-independent-check.json') for k in gates},observations=ref(RUN/'observations/results.json'),
        repairs=['pre-model literal .4/.6 equality rejected; installed Core percent uses promoted0.01f double multiply, float cast, Sum and default-residual-before-dot; exact gate repaired, UI40/60 unchanged',
            'original frozen baseline_preview field was full carrier; current packaging explicitly makes209.4–218.0 preview, original protocol unchanged',
            'new observation copy selects execution origin by context/variant, not row index; chosen8calls unchanged'],
        E_not_exact_author_time_varying_mixture=True,author_nodes_pitch_clock_not_transferred=True,
        original_kan_label_retained_E_kan_unknown=True,source_unknown106_retained=True,
        agent_heard=False,measurement_validated=False,general_rule_validated=False,
        next='Receive E versus own A solidity/connection and kan/break/articulation/level; no automatic mixture sweep or adoption.')
    save(REPORT/(NAME+'.json'),report)
    table='|字/ID|元音RMS差dB|FCPE差p50/max(c)|RMVPE差p50/max(c)|\n|---|---:|---:|---:|\n'
    for r in rows:table+=f"|{r['char']}/{r['word']}|{r['vowel_RMS_change_db']:+.3f}|{r['FCPE_abs_cents_p50']:.3f}/{r['FCPE_max_abs_cents']:.3f}|{r['RMVPE_abs_cents_p50']:.3f}/{r['RMVPE_max_abs_cents']:.3f}|\n"
    whole_text='；'.join(f"context{r['context']} {r['RMS_change_db']:+.3f}dB" for r in whole)
    outputs=pack['outputs']
    md=f'''# 最后一页：自己的条件下反向声线E

2026-10-12。状态own_bright_cute_delivered_pending_listening。用户“下一步”授权执行冻结单候选，自己两完整句“想把你抱进身体里面／不敢让你看见”15字270–284、context28/29，Normal75/Classic25改为Bright40/Cute60恒定UI配比。其它音符tone/tuning/PITD/note.pitch/vibrato、歌词/音素/CLR完整时钟、VOIC/TENC/BREC/SHFC与DYN保持。E是参考里/看焦点证据后选择的命名声线候选，作者整句配比有时变，**不声称精确复制作者整句声线**；没有搬运作者音高/时钟/控制节点或数组。旧Normal75/Bright25阴性保持。

## 原生和重新预测

当前YousaV1.65c acoustic与variance配置均核对Bright/Cute/Normal/Whisper/Classic顺序，不能从工程通用cl01标签猜名称。完整34part副本只替换28/29的五色曲线，32其它part及已有抱C结构保持；原生roundtrip、phone/音高导出、两阶段speaker实际tensor精确重建。

最初独立预检以数学实数0.4/0.6重建时被严格等式拒绝，失败检查器和日志保留，尚未启动fresh模型。离线PE读取已绑定本机Core的PhraseSpeakerEmbedByFrame及采样lambda：先double采样乘promoted0.01f再cast float32，Sum后不足1补该帧默认speaker，再dot。UI40/60采样得0.3999999761581421/0.5999999642372131，和0.9999999403953552，余量5.960464477539063e−08加至本段phone默认Bright，最终权重0.40000003576278687/0.5999999642372131。独立421/305帧、两阶段embedding逐元素精确通过；未改UI/剂量/工程/预算或放宽容差。metadata reader在本批ignored run编译，未加载或修改安装程序集。

两句各A/A_repeat/E/E_repeat共8次新variance、8套acoustic/vocoder，固定variance11/acoustic101。原A的三预测/三最终通道/raw PCM与历史28/29精确，所有重复输入/预测/mel/raw精确；E仅speaker及其三预测后最终发声特征响应变化，人工增量保持并重算合法clip，裁剪0。vocoder F0输入保持不证明实际F0完全固定。原生缓存4套技术上下文另列，不计作fresh样本；2条件、同输入重复不增加独立样本量，非留出。

## 有限观测与组装

77窗口包括15字元音/15–85%主体/首尾60ms、可定位辅音和两完整上下文，8次新FCPE/RMVPE检测，没有跨无声插值；共同有声配对不足3帧保留unknown。完整独立句波形RMS差：{whole_text}。下表是代理，RMS不等于感知响度、实感或生理参数；F0检测尚未本任务真值校准，不能因电平提高宣布改善。

{table}

完整245.577秒研究人声由32旧贡献及2新E贡献按原时钟组装，原DYN0dB曲线与gain1逐项核对，固定1.5、44100Hz mono PCM24，峰值{pack['peak']:.6f}，无归一化/压缩/BGM。独立重建34贡献、原A全PCM、量化误差、两预览与抱C通过；28/29贡献支撑并集外PCM精确保持。两句89ms自然重叠保留，本轮两句均改变，隔离句观测与整曲混合预览范围明确，没有交叉淡化或重定时。原“看”局部偏实反馈保持，但E中看的新听感及副作用待评。

冻结旧协议baseline_preview字段实际上指整曲carrier；新交付显式裁209.4–218.0秒8.6秒，两端原PCM截取精确，未重写旧协议。单独作者参考沿用已有fresh作者A、当前1.65c、固定11/101、212–220.5秒8.5秒；与自己的音乐/时钟有差异，只作描述对照，E−自己的A才是声线干预对照，历史1.56不可用。

- [E两句](../../../{outputs['candidate_preview']['path']})、[自己的原A](../../../{outputs['original_preview']['path']})。
- [白烁单独参考A](../../../{outputs['author_reference']['path']})。
- [完整研究E工程](../../../{outputs['candidate_project']['path']})、[完整研究E人声](../../../{outputs['candidate_full']['path']})，未采用为原歌曲。

新反馈0，Agent未听，全部measurement_validated=false、通用规律0。表1PER:S1与PARAM:C20.01–05引用、表2RESP:LASTPAGE-OWN-BRIGHT-CUTE-01及15字响应CSV追加本例，没有新增逐字听觉标签。下一步只接E相对自己A是否更实/连贯、看是否受影响及破音/咬字/响度反馈，不自动扫配比/加量/采用。原歌曲/音频/Skill/作者原件、unknown106、旧阴性及接受抱C保持，单Agent，CI仅手动。

[15字CSV]({NAME}-words.csv)、[JSON]({NAME}.json)、[审计]({NAME}-audit.json)。
'''
    (REPORT/(NAME+'.md')).write_text(md,encoding='utf-8',newline='\n')
    status=('当前状态own_bright_cute_delivered_pending_listening：2026-10-12自己两句E=Bright40/Cute60恒定命名声线已执行，15字270–284，'
        '自身音高/时钟/人工控制/DYN保持、三预测重算；原A历史三预测/最终输入/rawPCM及重复精确，8新variance/8波形/4原生技术缓存另列、裁剪0。'
        '本机两阶段名称与percent/default余量IL精确重建，实数0.4/0.6预检拒绝保留，UI40/60/预算未改。'
        '77窗口/8双F0与34贡献PCM检查通过、仅代理；32其它贡献/抱C与支撑并集外PCM保持，89ms重叠明确。'
        'E/自己A/作者独立参考同固定1.5交付，E待评未采用，Agent未听/通用规律0；原歌曲/音频/Skill/作者原件保持，单Agent/CI仅手动。')
    for name in ENTRIES:
        p=ROOT/name;lines=p.read_text(encoding='utf-8').splitlines()
        ids=[i for i,l in enumerate(lines) if '当前状态author_interaction_feedback_closed_reverse_voice_design_frozen：' in l];assert len(ids)==1,name
        rel='docs/reports/lastpage/'+NAME+'.md'
        if '/' in name:rel=('../../' if name.startswith('research/') else '../../../')+rel
        lines[ids[0]]=('- ' if lines[ids[0]].startswith('- ') else '')+status+f' 见[自己声线E]({rel})。'
        if name=='plan.md':
            for i,l in enumerate(lines):
                if l.startswith('下一工作进入逐首更新，先《最后一页》：'):
                    lines[i]='下一工作进入逐首更新，先《最后一页》：自己两句单个E=Bright40/Cute60已渲染并交付，下一步接E相对自己A的虚实/连贯、看及破音/咬字/响度反馈；作者参考单列。未采用、不自动扫比例或扩展下一因素；音乐阶段/时长差异仍待验，旧阴性/抱C/unknown保持。'
        p.write_text('\n'.join(lines)+'\n',encoding='utf-8',newline='\n')
    runtime()
    with (REPORT/(NAME+'-words.csv')).open(encoding='utf-8-sig',newline='') as f:restored=list(csv.DictReader(f))
    assert restored==[{k:str(v) for k,v in r.items()} for r in rows]
    gate=subprocess.run([sys.executable,'tools/repository/check_repository.py','--worktree'],cwd=ROOT,capture_output=True,encoding='utf-8')
    (RUN/'logs/repository-gate.log').write_text(gate.stdout+gate.stderr,encoding='utf-8');assert gate.returncode==0,gate.stdout+gate.stderr
    scripts=[ROOT/'research/table2-confirmation'/n for n in ['lastpage_own_bright_cute_20261012.py','check_lastpage_own_bright_cute_20261012.py',
        'package_lastpage_own_bright_cute_20261012.py','observe_lastpage_own_bright_cute_20261012.py',
        'check_lastpage_own_bright_cute_delivery_20261012.py',Path(__file__).name]]
    audit=dict(status='passed_with_explicit_auditory_gaps',scripts=[ref(p) for p in scripts],
        native_percent_IL=ref(RUN/'evaluation/speaker-selected-IL.json'),
        rejected_preflight=[ref(p) for p in sorted((RUN/'logs/rejected-speaker-preflight').rglob('*')) if p.is_file()],
        protected_references=len(load(RUN/'protected-before.json')),runtime_resources=len(load(RUN/'native-inputs/runtime.json')),
        actual_new_variance_calls=8,actual_new_waveforms=8,native_cached_contexts=4,actual_F0_calls=8,independent_contexts=2,
        CSV_JSON_exact=True,gate=gate.stdout.strip(),new_feedback_count=0,agent_heard=False,adoption=False,
        original_song_audio_Skill_author_unchanged=True,measurement_validated=False,general_rule_validated=False)
    save(RUN/'evaluation/audit.json',audit);save(REPORT/(NAME+'-audit.json'),audit)
    save(RUN/'completion-manifest.json',dict(status=report['status'],files=[ref(p) for p in sorted(RUN.rglob('*')) if p.is_file()],
        documents=[ref(p) for p in sorted(REPORT.glob(NAME+'*'))],entries=[ref(ROOT/n) for n in ENTRIES]))
    print(json.dumps(dict(status=report['status'],whole_context_proxies=whole,gate=audit['gate'],preview=outputs['candidate_preview']),ensure_ascii=False),flush=True)

if __name__=='__main__':main()
