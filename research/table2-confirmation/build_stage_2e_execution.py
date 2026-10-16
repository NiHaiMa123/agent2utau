"""Publish the completed finite technical batch, keeping auditory results pending."""
import csv
import io
import json
from freeze_stage_2d import ROOT,HERE,OUT,load,sha

OUTPUTS=['table2-stage-2e-execution.json','table2-stage-2e-execution.md','table2-stage-2e-execution-comparisons.csv']

def publish(path,text):
    content=text.encode('utf-8')
    if path.exists():assert path.read_bytes()==content, 'Refuse changed/reinterpreted report overwrite'
    else:path.write_bytes(content)

def build():
    b=load(HERE/'stage_2e_execution_baseline_binding.json');run=ROOT/b['run']
    gate=load(run/'technical-delivery-check.json');assert gate['eligible_for_listening']
    raw=load(run/'raw-execution.json');native=load(run/'native-current-check.json')
    pcm=load(run/'pcm-packaging.json');obs=load(run/'observations.json');summaries=[];comparison_rows=[]
    for c,n in zip(pcm['conditions'],native['conditions']):
        vowel=n['identity']['target_phone_indices'][1]
        w=next(x for x in obs['windows'] if x['condition_id']==c['condition_id'] and x['id']==f'phone-{vowel:02}')
        summaries.append(dict(condition_id=c['condition_id'],word=c['word'],native_identity=n['identity'],
            actual_Q5_sampling=n['sampling'],native_isolation=n['native_isolation'],
            original_A_fresh_PCM_exact=True,repeat_exact=True,new_clipping_frames=0,
            PCM_clock={k:c[k] for k in ['origin_s','samples','backing_start_sample','backing_grid_rounding_s']},
            requested_focus_s=c['requested_focus_s'],focus_complete=c['focus_complete'],focus_role=c['focus_role'],
            target_in_full_file_s=c['target_in_full_file_s'],vowel_window=w['interval_s'],
            vowel_comparisons=w['comparisons'],auditory_status='pending'))
        for direction,value in w['comparisons'].items():
            comparison_rows.append(dict(condition_id=c['condition_id'],word=c['word'],direction=direction,
                vowel_level_ratio_db=value['level_ratio_db'],mean_removed_mel_shape_rms=value['mean_removed_mel_shape_difference_rms'],
                FCPE_valid_frames=value['F0']['FCPE']['valid_pair_frames'],FCPE_abs_cents_p50=value['F0']['FCPE']['abs_cents_p50'],FCPE_max_abs_cents=value['F0']['FCPE']['max_abs_cents'],
                RMVPE_valid_frames=value['F0']['RMVPE']['valid_pair_frames'],RMVPE_abs_cents_p50=value['F0']['RMVPE']['abs_cents_p50'],RMVPE_max_abs_cents=value['F0']['RMVPE']['max_abs_cents'],
                auditory_status='pending',true_F0_status='unknown',measurement_validated=False))
    proofs=['preparation.json','native-build-bindings.json','native-acquisition.json','native-current-check.json',
        'execution-start.json','model-adapters.json','prepared-input-checks.json','raw-execution.json',
        'dynamics-preparation.json','dynamics-build-bindings.json','dynamics-execution.json','raw-independent-check.json',
        'pcm-packaging.json','observations-start.json','observations.json','technical-delivery-check.json']
    code=['freeze_stage_2e_execution.py','prepare_stage_2e_execution.py','NativeBatch.cs','acquire_stage_2e_native.py',
        'check_stage_2e_current_native.py','execute_stage_2e_paths.py','prepare_stage_2e_dynamics.py','apply_stage_2e_dynamics.py',
        'shfc_pcm_checks.py','check_stage_2e_raw.py','package_stage_2e_pcm.py','observe_stage_2e_paths.py',
        'check_stage_2e_delivery.py','build_stage_2e_execution.py']
    data=dict(schema_version=1,stage='2E-execution',date='2026-10-11',protocol_id='T2D-SHFC-PATHS-01',protocol_version=1,
        status='technical_execution_complete_pending_human_listening',stage_2E_complete=False,
        authorization=load(ROOT/b['manifest'])['authorization'],baseline=b,
        actual_execution=dict(new_native_record_pairs=4,technical_native_cache_waveforms=4,
            fresh_seeded_variance_calls=8,seeded_acoustic_vocoder_waveforms=16,unique_first_repeat_variants=8,
            effect_replications=0,F0_detector_inferences=16,delivery_PCM_files=72,FLOAT_diagnostic_files=16,new_feedback=0,generic_rules=0),
        gains=pcm['gains'],conditions=summaries,listener_pairs=pcm['pairs'],
        proofs=[dict(path=(run/x).relative_to(ROOT).as_posix(),sha256=sha(run/x)) for x in proofs],
        implementation=[dict(path=(HERE/x).relative_to(ROOT).as_posix(),sha256=sha(HERE/x)) for x in code],
        independent_gate=gate,measurements_scope=dict(windows=53,complete_real_phones=41,
            F0='voiced finite positive common frames; incomplete/conflicting evidence unknown; no detector truth calibration',
            level='RMS/peak and 30/50ms centered 5ms-hop proxies, not perceived loudness',
            spectral='mel and per-frame mean-removed shape proxies, not formant/register/break cause',
            measurement_validated_upgrades=False),
        history=dict(old_C_new_S_fresh_inputs_predictions_raw_PCM_exact=True,
            old_C_label_scope='C-B local usable; no transfer to new S-A comparison',
            accepted_C_preserved=True,guo_SHFC_and_BREC_dose_expansion_stopped=True,
            old_negative_and_unknown_feedback_preserved=True),
        scope=dict(single_agent=True,CI_manual_only=True,published_song_edited=False,existing_audio_edited=False,
            Skill_edited=False,model_or_install_edited=False,D_or_P_native_USTX_created=False,
            heldout_conditions=0,agent_heard=False,auditory_status='pending',stage_2F_to_2H_executed=False),
        listening=dict(index=(run/'delivery/listening.md').relative_to(ROOT).as_posix(),
            condition_pages=[(run/f'delivery/word{c["word"]}.md').relative_to(ROOT).as_posix() for c in pcm['conditions']],
            anonymous_codes='frozen v1 mapping; actual device/blinding unknown, not double blind',
            feedback_scope='可感知差别/方向与可用性/字头咬字破音/响度与邻字；无反馈维持pending'))
    body=['# 表2 2E：有限SHFC四路径实际执行\n',
        '2026-10-11。用户明确授权冻结协议后完成两条件A/S/D/P、各两次的16套实验波形。技术隔离和重复通过，现交付人工试听；2E整体仍未完成，听觉结果pending，2F–2H未执行。\n',
        '## 实际范围与技术结果\n',
        '抱225（b/ao、MIDI71、part22）与偏实只214（zh/ir、MIDI69、part21）均来自已见条件，不是留出。完整41音素及421/594帧上下文保留。−400c、145ms进入/55ms退出、5tick Q5锚点和预算不改。D/P只为研究反事实，不新增原生旋钮，也不归因单个VOIC/BREC/TENC。\n',
        '4组新原生A/S导出使用新缓存/日志/偏好副本，原安装只读；4套普通原生缓存技术波形另计，未作为16套固定种子因果样本。实际8次variance11及16次acoustic101/vocoder，CPU顺序单线程、steps20/depth0.6、两阶段Normal75/Classic25、unshifted vocoder F0与人工控制保持。三通道采用同条件本批完整新预测，不做字内旧状态拼接。\n',
        '实际抱32帧/只33帧SHFC与冻结数学采样精确，完整时钟及语言ID4通过。独立重开NPZ重建四路径、裁剪和重复；16组输入、预测、mel、raw、DYN重复精确，新特征裁剪0。两个新A与历史A输入/预测/raw PCM精确，新抱S与历史C输入/预测/raw PCM亦精确；这些关系不自动继承旧C-B听感为新S-A接受。\n',
        '原生ApplyDynamics对全部16套raw执行，实际曲线/时间轴独立重建与逐样本乘法精确。交付固定人声1.5/伴奏0.7、PCM24；FLOAT诊断另留。无归一化、压缩或事后补偿，编码读回误差不超过1 LSB，全部有限且峰值<1。原生乐句起点与伴奏44100Hz网格用ceil绑定，网格残差不足1样本，未重采样匹配。\n',
        '## 有限响应摘要\n',
        '下表只取完整目标元音窗。完整41音素、核心20%–80%、前后60ms、邻phone、整句及30/50ms中心窗均在绑定观测文件中。RMS变化不是感知响度，去均值mel变化不是共振/真假声或破音病因。\n',
        '| 条件 | 比较 | 元音电平ΔdB | 去均值mel差RMS | FCPE差p50/max(c) | RMVPE差p50/max(c) |\n|---|---|---:|---:|---:|---:|']
    for r in comparison_rows:
        body.append(f'| {r["word"]} | {r["direction"]} | {r["vowel_level_ratio_db"]:+.3f} | {r["mean_removed_mel_shape_rms"]:.3f} | {r["FCPE_abs_cents_p50"]:.2f}/{r["FCPE_max_abs_cents"]:.2f} | {r["RMVPE_abs_cents_p50"]:.2f}/{r["RMVPE_max_abs_cents"]:.2f} |')
    body += ['\nFCPE与RMVPE对8份新PCM各执行一次，共16次，源/模型SHA、输出数组及各自10ms时钟绑定；只比较共同voiced、有限且>0的帧，不跨无声插值。覆盖不足与检测器分歧保持unknown，无真实F0或自然度校准；固定vocoder输入不能说实测输出F0固定。全部表1measurement_validated仍false。\n',
        '## 试听与保留\n',
        f'本机[完整试听入口](../../../{data["listening"]["index"]})分开两条件与每个版本：8份完整上下文人声及混音、8份焦点人声及混音、两条件五组主对照的两顺序人声/混音，共72份PCM衍生文件，不是72次新成声。0.6秒空白仅隔开呈现段，不填补波形边界。先完整上下文，再固定对照；无变化重复用于确定性检查，不计独立效应重复。\n',
        '抱完整播放器中声母约1.58秒、元音约1.79–2.10秒。只完整播放器中声母约0.71秒、元音约0.85–1.17秒；只的预定焦点175.098958秒早于可用波形175.190454秒，故按协议保留整句并标焦点未完整，不补零。真实设备/是否看版本编码unknown，固定匿名码不等于双盲。\n',
        f'本机SHA审计：20份执行前快照、79生产/桥接/Skill/发布工程、67保护输入、1079旧封存路径、567当前歌曲run文件、{gate["original_sources_preserved"]}原来源与47安装资源保持。旧完成清单还带75项仓库/安装Skill引用，其中迁移前报告/脚本及历史AGENTS不属于567项run保护范围；首次宽范围路径检查失败保留，按现行独立保护/迁移边界修正，未改原清单。旧2E原生报告/审计写入口拒绝覆盖。\n',
        '初期协议字段误读phrase_index已改为实际context；本地构建权限/项目准备顺序失败、自动审批额度失败（未执行操作）均不计模型样本。新测试初轮152通过/2夹具失败：ceil(-0.441)=0以及DYN截断端点229，纠正预期后完整154通过，未改检查器或音频；原日志保留。实际8/16模型计算未发生失败或选择性重试。\n',
        '下一步只接收本批人工试听反馈、绑定实际版本/方向/设备能取得的元数据，未回答保持pending。旧抱C局部接受、果SHFC失败、BREC六条件无区别和其它unknown原样保留。技术响应不升级通用调参规律、不采用新版本、不改整曲或Skill；不自动扩为2F留出、2G整曲或2H迁移。\n',
        '输入、脚本、数组、输出与交付SHA见[结构化报告](table2-stage-2e-execution.json)，元音10组数值见[CSV](table2-stage-2e-execution-comparisons.csv)；根入口为[plan.md](../../../plan.md)及[专项计划](../../../plan-table2.md)。']
    csv_text=io.StringIO(newline=''); writer=csv.DictWriter(csv_text,fieldnames=list(comparison_rows[0]));writer.writeheader();writer.writerows(comparison_rows)
    outputs={OUTPUTS[0]:json.dumps(data,ensure_ascii=False,indent=2)+'\n',OUTPUTS[1]:'\n'.join(body)+'\n',OUTPUTS[2]:csv_text.getvalue()}
    for name,text in outputs.items():publish(OUT/name,text)
    pages=[]
    for c in pcm['conditions']:
        title='抱' if c['word']==225 else '只'
        page=[f'# {title}：四个独立完整上下文\n',
            '先听各完整人声，再按固定顺序对照；混音单独复查。播放器响度保持一致。可只回报有无区别、哪个更可用，以及字头/咬字/破音、响度或邻字变化。\n',
            f'目标声母在播放器约{c["target_in_full_file_s"][0]:.2f}秒，元音约{c["target_in_full_file_s"][1]:.2f}–{c["target_in_full_file_s"][2]:.2f}秒。'+('预定焦点早于波形起点，焦点文件保留整句，没有补零。\n' if not c['focus_complete'] else '\n')]
        for e in sorted(c['versions'],key=lambda x:x['code']):
            page += [f'## {e["code"]}\n',f'![{title} {e["code"]}]({(ROOT/e["full_vocal"]).as_posix()})\n',
                f'[独立混音]({(ROOT/e["full_mix"]).as_posix()}) · [焦点人声]({(ROOT/e["focus_vocal"]).as_posix()})\n']
        page += ['## 固定顺序对照\n','每段先第一编码，空白0.6秒，再第二编码。两个顺序均保留；可以分次听，不要求一次完成全部。\n']
        for pair in [x for x in pcm['pairs'] if x['condition_id']==c['condition_id']]:
            label=f'{pair["order"]:02} {pair["codes"][0]}→{pair["codes"][1]}'
            page += [f'- [{label} 人声]({(ROOT/pair["vocal"]).as_posix()}) · [混音]({(ROOT/pair["mix"]).as_posix()})']
        path=run/f'delivery/word{c["word"]}.md';publish(path,'\n'.join(page)+'\n');pages.append(path)
    publish(run/'delivery/listening.md','# 表2冻结批次试听\n\n16套实验波形、各版本同输入两次；8个独立版本及两顺序固定对照。技术检查已通过，听感待评价。\n\n'+
        '\n'.join(f'- [{"抱（3:04）" if i==0 else "只（2:56）"}独立试听]({path.as_posix()})' for i,path in enumerate(pages))+'\n\n人声1.5/伴奏0.7，PCM24，无归一化/压缩。先完整上下文，再按各页固定对照；可分次回报。\n')
    print(json.dumps(dict(status=data['status'],reports=OUTPUTS,listen=str(run/'delivery/listening.md'))))

if __name__=='__main__':build()
