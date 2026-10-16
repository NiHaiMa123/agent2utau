"""Build PARAM/entity coverage and one finite design from pre2D records."""
import argparse
import csv
import io
import json
from collections import Counter

from freeze_stage_2d import ROOT, HERE, OUT, BINDING, load, sha
from stage_2d_design import design, PROTO_JSON, PROTO_MD

OUTPUTS = ['table2-validation-gaps.json', 'table2-validation-gaps.csv',
    'table2-manifestation-gaps.csv', 'table2-protocol-review.md', PROTO_JSON, PROTO_MD]
SEAL = HERE / 'stage_2d_protocol_binding.json'


def write(path, value):
    data = value.encode('utf-8')
    if path.name.startswith('shfc-path-') and SEAL.exists() and path.exists():
        assert path.read_bytes() == data, 'Frozen protocol cannot be changed in place'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def dump(path, value):
    write(path, json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def csv_write(path, rows):
    buf = io.StringIO(newline='')
    w = csv.DictWriter(buf, fieldnames=list(rows[0]))
    w.writeheader()
    for r in rows:
        w.writerow({k: json.dumps(v, ensure_ascii=False, sort_keys=True) if isinstance(v, (dict, list, bool)) else v for k, v in r.items()})
    write(path, '\ufeff' + buf.getvalue())


def task(group):
    n = int(group[1:])
    if n <= 9 or n in (21, 32):
        return '旋律身份、换音/长音与音高运动；缺新因果听觉/实际F0方法验证'
    if n in (10, 26, 42, 46):
        return '强弱组织与呈现链公平比较；数字增益不等于感知响度'
    if 11 <= n <= 20 or n in (39, 40):
        return '音区/发声条件与声线连续性；需分预测/增量/最终输入/PCM'
    if n in (22, 23, 24, 25, 27, 28, 41):
        return '字头/音素过渡、音乐落点与上下文；合法映射不等于自然时长'
    if n in (43, 44, 45):
        return '频谱/动态/空间呈现；本机非默认执行与听觉作用缺证'
    if n in (29, 30, 31, 33, 34, 35, 36, 37, 38):
        return '替代引擎/扩展的条件作用；需具体实现与资源，不泛化旗标'
    return '编辑/驱动记录；追踪实际写入的PARAM，纯UI不当声学旋钮'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--seal', action='store_true')
    args = ap.parse_args()
    binding = load(BINDING)
    assert sha(ROOT / binding['manifest']) == binding['sha256']
    snapshot = load(ROOT / binding['manifest'])
    old = {r['path']: ROOT / r['snapshot'] for r in snapshot['files']}
    for r in snapshot['files']:
        assert sha(ROOT / r['snapshot']) == r['sha256']
    for r in snapshot['design_source_bindings']:
        assert sha(ROOT / r['path']) == r['sha256']
    if SEAL.exists():
        for r in load(SEAL)['bindings']:
            assert sha(ROOT / r['path']) == r['sha256'], 'Sealed design/code changed'
    def frozen(name):
        return load(old[(OUT / name).relative_to(ROOT).as_posix()])
    ledger, catalog, knowledge = [frozen(n) for n in ['conditional-responses.json', 'control-details.json', 'knowledge-table.json']]
    records = ledger['responses'] + ledger['observations'] + ledger['audits']
    protocol = design(ledger)
    rows = []
    selected = {'PARAM:C14.01': 'main_intervention', 'PARAM:C11.01': 'mediated_group_only',
        'PARAM:C12.01': 'mediated_group_only', 'PARAM:C13.01': 'mediated_group_only', 'PARAM:C47.06': 'driver_only'}
    for p in catalog['rows']:
        linked = [r for r in records if p['id'] in r['record_v3']['table1_refs']['parameter_ids']]
        candidates = [e['id'] for e in knowledge['entities'] if 'CTRL:' + p['group_id'] in e['control_family_navigation_refs']]
        scope = p['scope']
        status = ('selected_finite_design' if p['id'] in selected else
                  'dependency_before_execution' if p['group_id'] in ['C39', 'C40', 'C41', 'C46'] and scope == 'current_route' else
                  'deferred_current_music_gap' if scope == 'current_route' else 'outside_selected_route_or_metadata')
        rows.append(dict(parameter_id=p['id'], field=p['field'], group_id=p['group_id'], scope=scope,
            actual_support=p['current_support'], condition=p['condition'], musical_use=task(p['group_id']),
            historical_response_ids=[r['id'] for r in linked if r in ledger['responses']],
            historical_observation_ids=[r['id'] for r in linked if r in ledger['observations']],
            historical_audit_ids=[r['id'] for r in linked if r in ledger['audits']],
            candidate_entity_ids=candidates, entity_relation='navigation candidates only; no detected occurrence or causal edge',
            evidence_gap='无已验证通用剂量/方向；历史记录按2C逐行范围，静态存在与实际执行/试听分开',
            priority=status, selected_role=selected.get(p['id'], ''),
            protocol_ids=[protocol['id']] if p['id'] in selected else [], generic_rule_validated=False))
    manifestation_rows = []
    for e in knowledge['entities']:
        linked = [r['id'] for r in records if e['id'] in r['record_v3']['table1_refs']['entity_ids']]
        manifestation_rows.append(dict(entity_id=e['id'], name=e['name'], formal_status='formal_record_entity',
            measurement_protocol_id=e['measurement_protocol_ref'], measurement_validated=False,
            historical_candidate_record_ids=linked, evidence_role='schema candidates, not validated measurement occurrences',
            musical_use='；'.join(dict.fromkeys(task(g.removeprefix('CTRL:')) for g in e['control_family_navigation_refs'])),
            remaining_gap=e['required_followup'], priority='selected_proxy_or_listener_task' if e['id'] in protocol['table1_refs']['entity_ids'] else 'deferred_method_or_music_gap',
            selected_protocol_ids=[protocol['id']] if e['id'] in protocol['table1_refs']['entity_ids'] else [], generic_rule_validated=False))
    manifestation_rows.append(dict(entity_id='CAND:MULTI_F0', name='复音/拍频开放候选', formal_status='open_candidate',
        measurement_protocol_id='MEAS:D50', measurement_validated=False, historical_candidate_record_ids=[],
        evidence_role='no promotion to atomic or detected multiple sources', musical_use='声源关系与复音身份',
        remaining_gap='源数、次谐波、AM与加强泛音旋律需独立区分；当前条件不采用', priority='deferred_method_or_music_gap',
        selected_protocol_ids=[], generic_rule_validated=False))
    counts = dict(parameter_rows=len(rows), navigation_groups=len({r['group_id'] for r in rows}),
        formal_entities=49, open_candidates=1, historical_records=14,
        directly_referenced_parameters=sum(bool(r['historical_response_ids'] or r['historical_observation_ids'] or r['historical_audit_ids']) for r in rows),
        intervention_referenced_parameters=sum(bool(r['historical_response_ids']) for r in rows),
        selected_main_interventions=1, selected_parameter_roles=5,
        priority_counts=dict(Counter(r['priority'] for r in rows)), frozen_protocols=1,
        planned_waveforms=16, new_waveforms=0, new_feedback=0, validated_generic_rules=0)
    dump(OUT / 'table2-validation-gaps.json', dict(stage='2D', date='2026-10-10',
        status='gap_review_and_protocol_frozen_with_explicit_gaps', baseline=binding,
        parameter_rows=rows, manifestation_rows=manifestation_rows, counts=counts,
        priority_rationale='先处理已有正/负反馈之间的机制判别，后验证迁移；当前音乐任务、实际支持、可判别证据共同排序，不按352参数逐个填正例',
        dependent_capability_gaps=['D/P研究runner和独立检查器尚未实现', '当前runtime重新绑定及实采样核查在2E执行前',
            '真实F0/共振峰/破音分类/感知响度/设备尚无完整验证，所有measurement_validated保持false'],
        finite_protocol_ref=PROTO_JSON, new_audio_or_arrays_read=False, new_engine_execution=False))
    csv_write(OUT / 'table2-validation-gaps.csv', rows)
    csv_write(OUT / 'table2-manifestation-gaps.csv', manifestation_rows)
    dump(OUT / PROTO_JSON, protocol)
    md = '# 有限协议：SHFC直接条件与预测依赖分离\n\n'
    md += f'2026-10-10，{protocol["id"]} v1。状态：设计冻结，尚未执行；研究runner/独立检查器待实现。机器执行规格以[JSON](shfc-path-separation-v1.json)为准。\n\n'
    md += '主问题是已有抱C局部响应的路径来源，以及同一固定条件在另一偏实元音中的回退。两个条件均已用于设计，不是独立留出；不重新试果SHFC或增大BREC。\n\n'
    md += '| 条件/任务 | 元音/音高 | Q5四锚点（秒） | 原标签范围 |\n|---|---|---|---|\n'
    for c in protocol['cases']:
        q = c['condition']
        md += f'| word{q["word"]}/part{q["context"]}，{c["role"]} | {q["phoneme"]}/MIDI{q["tone"]} | {", ".join(f"{v:.9f}" for v in c["nominal_Q5_anchors_s"])} | {q["label"]}；并非全维度验收 |\n'
    md += '\n固定-400c、145ms进入/55ms退出，5tick编码。原part-local整数5tick按timeAxis评估Q5，以五成双取整为整数cents；名义支撑外0，原生线性采样另核查。抱锚点保持原接受C名义值，不能仅凭同函数名字认定S与旧C精确；只的相对元音时钟同函数，峰值/实支撑需独立核查，不按结果改幅度。原v02为诊断基底，已接受抱C的制作方案保留。\n\n'
    md += '| 版本 | acoustic F0 | 新variance预测 | 原生可等价编码 |\n|---|---|---|---|\n'
    for v in protocol['variant_matrix']:
        md += f'| {v["id"]} | {v["acoustic_F0"]} | {v["prediction"]} | {v["native_equivalent"]} |\n'
    md += '\nD/P只在新研究run交换同条件、同新批次A/S的三通道预测组，再加不变人工增量；不用旧数组、其它字或作者数组。D/P不是生产原生出口，也不能分别归因某一个发声通道。\n\n'
    for key, title in [('gates', '执行前门槛'), ('interpretation', '有限解释'), ('stop_rules', '停止条件')]:
        md += f'## {title}\n\n' + '\n'.join('- ' + s for s in protocol[key]) + '\n\n'
    md += '## 数量、观测与人工试听\n\n每条件A/S/D/P均同输入两次：共8次variance推理、16套seeded acoustic/vocoder波形。原生桥接条件获取另保留技术缓存，不算新因果证据。重复只检查精确复现，不是独立效应复制；初始化/IO失败仅同输入重试一次，失败保留。\n\n'
    md += '两阶段Normal75/Classic25、variance11/acoustic101、steps20/depth0.6、44.1k/512及历史47项runtime期望固定；当前安装需2E重查。模型适配只在新run，权重不改。目标pitch/phones/时钟、原人工发声基底/DYN与1.5/.7增益固定，无响度匹配/归一化/压缩。保留整句、声母/元音核心/入口/退出、前后完整phone，核查完整预测与邻字响应。\n\n'
    md += '30/50ms中心窗RMS/peak、hop5ms、半开样本索引ceil(t*sr)，不足完整窗不补零；零能量保存null/zero。mel与去整体电平谱形只是代理。双F0必须绑定模型/时钟/有效率，冲突unknown；vocoder输入固定不保证实际输出F0固定。没有可靠formant、破音或生理寄存器真值，不能用数字代理宣布自然。\n\n'
    md += '人工试听在2E所有技术隔离/复现检查通过后：每条件固定S-A/D-A/P-A/S-D/S-P五组，共10组主对照；各对照保留双顺序及匿名编码、独立上下文文件，同增益混音复查。记录可感知差别/不确定、可用方向、字头/咬字/破音位置、主观响度/邻字回退。缺时间/设备/盲测信息记unknown；未取得反馈即pending。未做独立留出/跨曲/全曲，不改Skill。\n'
    write(OUT / PROTO_MD, md)
    report = '# 表2 2D：知识缺口与有限协议冻结\n\n2026-10-10。状态gap_review_and_protocol_frozen_with_explicit_gaps。2C记录原字节保持；本轮只做覆盖/设计，没有数组读取、模型执行、新音频或新反馈。\n\n'
    report += f'[PARAM矩阵](table2-validation-gaps.csv)/[JSON](table2-validation-gaps.json)逐项覆盖352 PARAM、48导航组；[表现矩阵](table2-manifestation-gaps.csv)覆盖49正式记录实体及1开放候选。只有{counts["directly_referenced_parameters"]}个PARAM被14旧记录的具体引用覆盖，其中{counts["intervention_referenced_parameters"]}个有干预记录引用。引用是路径/结构或原限定实验范围，不等于通用因果边、检测到表现或通过全部控制。\n\n'
    report += '优先级：先检验已有抱C局部接受与BREC阴性之间的路径解释，加入高音区异元音“只”偏实条件检查回退；主干预仅SHFC，VOIC/BREC/TENC列为预测组中介、C47.06为函数驱动。源数/粗糙/共振峰、其它引擎与未支持graph、真实设备/FX非默认分支保留缺口；音高、时钟和输出链作为当前实验固定/依赖，不把它们全部扩成新调参任务。\n\n'
    report += '[冻结协议](validation-protocols/shfc-path-separation-v1.md)/[机器规格](validation-protocols/shfc-path-separation-v1.json)：两个已见条件×A/S/D/P四路径×两次同输入，共16套计划波形；本轮实际0套。D/P是独立研究反事实、现controlled_probe无该接口，必须先实现研究runner与独立输入检查器，不能伪称本机原生控制支持。对三通道预测整组分离不支持单一气声/张力病因归因；预测中介可有整个上下文响应。\n\n'
    report += '抱原标签是C-B局部“可以”，本轮S-A尚待试听；“只”偏实并非全面正常。两个条件已用于设计，不是新留出。果SHFC停止、BREC -10六条件阴性、TENC取消无差别、抱C接受及源unknown全部保留，不加量/扫时长/挑seed，不更新Skill或制作方案。未将任何measurement_validated或generic_rule_validated升级。\n\n'
    report += '新因果音频与人工试听在2E，且先满足冻结协议的路径接口、runtime、实采样、输入隔离/重复与PCM交付门槛。没有可靠听音/反馈只记pending；数字电平/mel/F0估计不替代改善/破音判定。2F留出/2G整句全曲/2H知识或Skill变更不由本批自动完成。\n\n'
    report += '[更新前快照](history/pre-table2-2d-20261010/snapshot-manifest.json)保留23文件；[审计](table2-stage-2d-audit.json)记录独立核查与本地测试。协议与设计源码SHA在stage_2d_protocol_binding.json封存，禁止原地修改；重复构建必须字节一致，若未来修改需显式新版本。2C写入口转为历史guard，原源码在快照中。封存前独立引用检查拒绝了草稿中表现/测量ID的顺序错配；草稿和失败日志保留在本轮run，按原表1对应关系修正后才封存，未改变历史记录或执行音频。\n'
    write(OUT / 'table2-protocol-review.md', report)
    if args.seal:
        assert not SEAL.exists(), 'Existing protocol seal must not be replaced'
        paths = [OUT / PROTO_JSON, OUT / PROTO_MD, HERE / 'stage_2d_design.py', HERE / 'build_stage_2d.py']
        dump(SEAL, dict(id=protocol['id'], version=1, baseline=binding, execution_status='not_executed',
            bindings=[dict(path=p.relative_to(ROOT).as_posix(), sha256=sha(p)) for p in paths]))
    print(json.dumps(counts, ensure_ascii=False))


if __name__ == '__main__':
    main()
