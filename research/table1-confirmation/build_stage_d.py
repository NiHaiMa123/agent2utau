"""Build SHA-bound protocols. No audio/model/USTX execution or inference."""
import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
from frozen_inputs import refuse_after_formal_migration

from stage_d_protocol_data import specs, SOURCE_ROWS, SOURCE_MAP, IMPLEMENTATIONS

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'docs/knowledge/acoustic-manifestations-20261009'
HERE=Path(__file__).resolve().parent


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def csv_value(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True) if isinstance(value,(list,dict)) else str(value)


def main():
    refuse_after_formal_migration()
    ap=argparse.ArgumentParser()
    ap.add_argument('--array-checks',type=Path,required=True)
    args=ap.parse_args()
    check_path=args.array_checks.resolve()
    assert check_path.is_relative_to(ROOT/'runs/research')
    check=load(check_path)
    assert check['status']=='finite_array_checks_passed' and len(check['cases'])==10
    assert check['no_audio_files_read_or_written'] and check['no_models_or_native_execution']
    bindings=load(HERE/'stage_d_source_bindings.json')['files']
    hashes={r['path']:r['sha256'] for r in bindings}
    for r in bindings:
        assert sha(ROOT/r['path'])==r['sha256'],f'Changed scoped implementation: {r["path"]}'
    for r in check['code_bindings']:
        assert r['sha256']==hashes[r['path']]
    a=load(OUT/'table1-row-review.json')
    b=load(OUT/'core-definition-review.json')
    c=load(OUT/'control-details.json')
    claims=load(OUT/'claim-evidence.json')['claims']
    assert c['status']=='reviewed_with_explicit_gaps' and c['counts']['parameters']==352
    entities={i for r in a['rows'] for i in r['proposed_ids']}
    by_legacy={r['legacy_id']:r for r in b['rows']}
    sources=[dict(id=id_,title=title,url=url,locator=locator,scope_limit=limit,
        read_status='component_method_or_scope_read_not_executed',checked_date='2026-10-09',
        measurement_validated=False) for id_,title,url,locator,limit in SOURCE_ROWS]
    source_ids={r['id'] for r in sources}|{r['id'] for r in claims}
    rows=[]
    for key,name,obj,inputs,window,method,units,mask,refusal,gap in specs():
        legacy=[r['legacy_id'] for r in a['rows'] if key in r['proposed_ids']]
        if key=='ACO:L5':legacy=['L3','L4']
        if key=='PER:P1':legacy=['P1']
        refs=SOURCE_MAP.get(key,[])
        inherited=sorted({ref for lid in legacy for ref in by_legacy[lid]['claim_refs']})
        impl=[]
        for path,anchor in IMPLEMENTATIONS.get(key,[]):
            assert path in hashes
            lines=(ROOT/path).read_text(encoding='utf-8').splitlines()
            matches=[i+1 for i,line in enumerate(lines) if anchor in line]
            assert len(matches)==1,(path,anchor)
            impl.append(dict(path=path,anchor=anchor,line=matches[0],sha256=hashes[path],
                role='existing_component_only_not_full_protocol_or_all_inputs'))
        val=[v for v in check['cases'] if key in v['candidate_entities']]
        proposed='B_open_candidate' if key not in entities else 'A_proposal_not_formally_migrated'
        row=dict(id=f'MEAS:D{len(rows)+1:02}',candidate_entity_id=key,entity_proposal_status=proposed,
            legacy_ids=legacy,name=name,observation_object=obj,input_requirements=inputs,
            stage_and_clock='listening/delivery clock with source binding' if key.startswith('PER:') else
                'metadata and conversion chain' if key.startswith('META:') else
                'output PCM clock unless explicitly tagged native/score/model; all offsets separately bound',
            window_hop_and_support=window,method_or_formula=method,units=units,
            quality_mask=mask,unknown_or_refusal=refusal,
            reference_and_uncertainty='Explicit identity/reference/version/offset required; report interval uncertainty and quality-mask coverage. No default identity mapping from source to score/native/PCM/delivery.',
            parameter_status='Protocol design proposals distinguished from frozen current code constants; no perceptual/clinical pass thresholds',
            source_refs=refs,inherited_B_component_refs=inherited,
            source_role='authored_protocol; cited components retain original read status and do not validate the whole protocol',
            implementation_refs=impl,implementation_status='selected_component_source_reviewed' if impl else
                'listening_record_protocol_only' if key.startswith('PER:') else 'method_candidate_not_implemented_here',
            technical_validation_refs=[v['id'] for v in val],
            technical_validation_scope=[v['validation_scope'] for v in val] or ['no_new_algorithm_accuracy_validation'],
            measurement_defined='protocol_defined_with_gaps',measurement_validated=False,
            real_audio_accuracy='not_validated_in_D',existing_labels_role='existing_scope_retained_no_new_labels',
            auditory_label_status='no_new_listening',remaining_gap=gap)
        assert set(refs+inherited)<=source_ids
        rows.append(row)
    assert {r['candidate_entity_id'] for r in rows}==entities|{'ACO:L5','PER:P1','CAND:MULTI_F0'}
    assert {lid for r in rows for lid in r['legacy_ids']}=={r['legacy_id'] for r in a['rows']}
    original_links=[]
    for r in a['rows']:
        original_links.append(dict(legacy_id=r['legacy_id'],protocol_refs=[v['id'] for v in rows if r['legacy_id'] in v['legacy_ids']],
                                  all_associated_methods_validated=False))
    candidates=[dict(candidate_entity_id=r['candidate_entity_id'],proposal_status=r['entity_proposal_status']) for r in rows if r['candidate_entity_id'] not in entities]
    payload=dict(schema_version=1,date='2026-10-09',stage='D',status='protocol_review_complete_with_explicit_gaps',
        original_rows_covered=31,A_entities_covered=47,B_extra_candidates=3,protocol_count=50,
        rows=rows,legacy_links=original_links,extra_candidates=candidates,
        counts_by_namespace=dict(Counter(r['candidate_entity_id'].split(':')[0] for r in rows)),
        implementation_bindings=bindings,component_source_entries=len(sources),
        numerical_verification=dict(path=check_path.relative_to(ROOT).as_posix(),sha256=sha(check_path),
            status=check['status'],cases=check['cases'],versions=check['versions']),
        all_measurement_methods_validated=False,all_real_audio_estimators_validated=False,
        no_new_audio_or_synthesis=True,no_models_or_native_execution=True,no_project_skill_or_production_change=True,
        no_new_auditory_labels=True,stages_E_F='not_executed',formal_id_migration='proposed_not_applied')
    (OUT/'measurement-protocols.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    with (OUT/'measurement-protocols.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader()
        w.writerows({k:csv_value(v) for k,v in row.items()} for row in rows)
    (OUT/'measurement-source-review.json').write_text(json.dumps(dict(schema_version=1,stage='D',sources=sources,
        role='component_methods_read_no_new_literature_claims_or_fulltext_upgrades_to_stage_B',
        supplementary_pages_read=['https://praat.org/manual/Sound__To_Harmonicity__cc____.html','https://praat.org/manual/Voice_4__Additive_noise.html']),
        ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    report=['# 表1观测协议审查：阶段D','','2026-10-09。**D为protocol_review_complete_with_explicit_gaps**：原31行/A的47候选实体全部关联协议，另列B的shimmer、感知音高、复音/拍频3项，共50条。协议定义完成不等于所有检测器实现或真实歌唱测量通过；E/F未执行，原清单/ID不迁移。', '',
        '完整字段见[CSV](measurement-protocols.csv)/[JSON](measurement-protocols.json)，方法来源见[组件来源](measurement-source-review.json)。每项包括对象、输入、阶段/时钟、窗口/hop、公式、单位、质量掩码、参照/不确定性、拒绝条件、实现/验证范围及尚缺证据。所有新窗口/门限均标候选，代码已有常量另列，不设通用好坏阈值。', '',
        '## 本轮做了什么','','- 只读核查11份生产/契约源码，另绑定1份研究数组验证器；源码SHA/行号明确。未修改生产代码、工程、Skill、安装或音频，未运行模型/原生导出。',
        '- 阅读10项官方/作者实验室组件来源（另2页交叉读）；B文献的摘要/范围级缺口原样保持，没有凭D协议填写升级成全文/已验证。',
        '- 运行10组已知数值数组检查，记录真值/实际值/版本/范围；没有生成或播放WAV，数组不是自然度正反例。88项仓库测试与保护绑定由执行审计另记。', '',
        '## 现有实现的关键边界','','| 实现 | 实际量与限制 |','|---|---|',
        '| features.shape_features | 显式输入曲线OLS与极值候选；8样本/150ms/gap40ms、3–12Hz/6c是代码候选常量。峰谷幅度不等于±depth，残差仍含周期。未连接PCM或voiced mask自动验真。 |',
        '| FCPE/RMVPE | 各自原生hop/UV语义、重采样、mono均值需绑定；双估计一致不等于独立真值。本轮不加载权重，未验证真实输出准确率。 |',
        '| onsets.frame_rms | forward窗从frame时间开始，非中心窗；尾部截短并分母改实际样本数。D新矩形中心窗协议若采用需另外实现与验证。 |',
        '| wavcheck.analyze_wav | 先LR算术均值；voiced_fraction是20ms不重叠窗RMS>-50dBFS比例。支持1/2/4字节整数解析，不支持PCM24；>=0.999只近满幅告警，非true peak/声断检测。 |',
        '| controlled_probe.spectral_response | 原生log-mel的每帧bin共同偏移去除；不是PCM/dBFS、formant校正或听觉改善。当前adapter布局限制继续保留。 |',
        '| independent.validate_native / TempoMap | 输入SHA/几何/单位与score时钟契约；native phone时钟不是HFA或实际爆破/元音声学边界。 |', '',
        '实现引用和哈希见JSON；本轮只记录限制，不把文档更名当作生产修复。', '',
        '## 复杂方法的拒绝条件','',
        '高F0时输出谐波峰、LPC pole和声道共振可能不可辨识；缺足够频率信息、参数稳定性或独立参照时只保留R5输出谱，R1/R2/R6为unknown。这是基于来源的协议限制，未建立一个自动高F0阈值。[UNSW对象区别](https://www.phys.unsw.edu.au/jw/formant.html)、[Burg参数](https://praat.org/manual/Sound__To_Formant__burg____.html)。', '',
        '周期级jitter/shimmer需要可信pulse、有效周期及配对筛选，不能用10ms F0残差或30/50ms包络替代；歌唱滑音、颤音、强非周期和脉冲不稳时拒绝解释，不迁移临床阈值。[jitter算法](https://praat.org/manual/PointProcess__Get_jitter__local____.html)、[shimmer定义](https://praat.org/manual/Voice_3__Shimmer.html)。', '',
        'HNR/CPPS只是声明条件下的周期性/噪声代理，不能等同模型VOIC/BREC或“实/假”；完整参数、稳定元音、辅音/泄漏与方法敏感性必须记录。[HNR参数](https://praat.org/manual/Sound__To_Harmonicity__ac____.html)、[CPPS参数](https://praat.org/manual/PowerCepstrogram__Get_CPPS___.html)。', '',
        'sample peak、true peak、短窗RMS、节目响度和听者响度分别保存。ITU规定的K加权/通道功率/400ms重叠门禁及true-peak重建是方法候选，本仓库未实现/验证符合性；不据LUFS或RMS替代字头反馈。[BS.1770-5 Annex1/2](https://www.itu.int/dms_pubrec/itu-r/rec/bs/R-REC-BS.1770-5-202311-I!!PDF-E.pdf)。', '',
        '## 数值检查与验证层级','','| 检查 | 绑定对象 | 实际验证范围 |','|---|---|']
    for v in check['cases']:
        report.append(f'| {v["id"]} | {", ".join(v["candidate_entities"])} | {v["validation_scope"]} |')
    report += ['', '反相相关首次用精确-1断言，得到-0.9999999999999998而拒绝；研究验证器改用声明1e-12容差，精确mono消除/功率断言保留后通过。失败/重试日志在新研究run，未修改生产算法。其它数组的通过只限列出的数学/组件，不把对应完整协议measurement_validated升级为true。', '',
        '## 逐项协议索引','','| 协议 | 候选对象 | 窗/时钟 | 单位 | 现有实现状态 |','|---|---|']
    for r in rows:
        report.append(f'| {r["id"]} {r["candidate_entity_id"]} {r["name"]} | {r["observation_object"]} | {r["window_hop_and_support"]} | {r["units"]} | {r["implementation_status"]} |')
    report += ['', '## 后续与人工试听','','下一步E先冻结独立覆盖清单及角色，再映射这些候选；已有问题/可用/无差别反馈是回归证据，未知字/未听细分标签仍unknown。听者的原话确认感知范围，不自动确认声学病因；测量也不能代替听者。新的因果对照按后续表2的冻结设计推进，本轮不追加合成。', '',
        'D确定性协议已列；高F0共振、声源分解、鼻化、次谐波/复音、真实声学边界、语言辅音、复杂响度/空间和任何真实音频检测性能仍有缺口。F前不静默迁移ID或改表2绑定。当前[计划](../../../plan.md)，检查见[执行审计](table1-execution-audit.json)。','']
    (OUT/'table1-measurement-review.md').write_text('\n'.join(report),encoding='utf-8')
    print(json.dumps(dict(stage='D',status=payload['status'],protocols=len(rows),A_entities=47,extra_candidates=3,array_checks=10)))


if __name__=='__main__':
    main()
