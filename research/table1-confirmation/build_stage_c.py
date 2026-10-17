"""Build concrete control rows from explicit, SHA-bound source/config inputs.

No native process, inference, audio, cache search or production modifications.
Requires the frozen source snapshot; only hashes/configs are read at installation.
"""
import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
from frozen_inputs import refuse_after_formal_migration

import yaml
from stage_c_control_data import controls
from stage_c_remaining_data import extra_controls, GRAPH_TYPES, PENDING
from stage_c_local_review import review as local_review, apply_review
from stage_c_editor_review import editor_controls, preference_review, report as editor_report

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'docs/knowledge/acoustic-manifestations-20261009'

def load(p):
    return json.loads(p.read_text(encoding='utf-8'))

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def csv_value(v):
    if isinstance(v, (dict, list)):
        return json.dumps(v, ensure_ascii=False, sort_keys=True)
    return str(v)

def path_report(rows, local, graph_rows):
    def link(field):
        r = next(r for r in rows if r['field']==field)
        return f'[{r["id"]}]({r["source_url"]})'
    result = ['', '## 导出、播放与声像的实际区别', '',
        '| 入口 | 实际顺序与选择 | 本机边界 |', '|---|---|---|',
        '| UI/桥接混音导出 | voice与已加载wave → 每轨fader（Volume/Pan/Muted）→ MixFx → WaveMix → ExportAdapter → WAV16/44100/stereo | 本机IL读路径已核查；整体FX配置决定旁路，没有新输出测试 |',
        '| UI/桥接分轨导出 | voice请求 → dry slot source → ExportAdapter → ToMono(1,0) → WAV16/44100/mono | 跳过Muted；无track Volume/Pan/MixFx、无导入伴奏；renderer DYN仍在 |',
        '| UI播放 | 范围/指定track → mixdown → PlaybackMix节拍overlay → MasterAdapter → audio output | 本机FX为WrapWith静态组装；上游WrapLive不存在；live设备/OS音量未知 |', '',
        '入口依据：'+link('mixdown PCM encoding/sample_rate/channels')+'、'+link('track export PCM encoding/sample_rate/channels')+'、'+link('playback tick/endTick/trackNo')+'。主UI音频导出文件过滤为WAV，所核查路径没有可选MP3/FLAC、采样率或位深；输入支持多种格式不等于可以按同样格式导出。', '',
        '声像公式：angle=(clip(pan,-100,100)+100)/200×π/2；L=cos(angle)，R=sin(angle)。mono在slot复制到两侧后，中心每侧1/√2（约-3.0103dB），L²+R²=1。对已有stereo输入，fader是对原左右各乘此系数，不做声像交叉混合；不能宣称任意stereo总功率都恒定。见'+link('track.pan → channel gains')+'及本机LOCAL:07。', '',
        '轨道Volume低区采用分段规则：db<=-24静音；-24<db<-16先变为2db+16；否则直接db，再10^(effective_db/20)。动态fader每个交错sample最多变化0.0005，初始SetScaleToTarget直接设置。它与DYN的0.1dB存储及最低值特殊静音是不同入口。见'+link('track.volume → fader.Scale')+'、'+link('fader.Scale live smoothing')+'。', '',
        'solo/mute主要由App的JudgeMuted写派生Muted：Solo优先，随后Mute或任一其它Solo使Muted=true。桥接Load不实例化该UI；UTrack.AfterLoad只有!Solo且Mute时置Muted，因此不能把UI多轨solo效果自动推广到桥接加载上下文。已核查两种导出都读取派生Muted，不是单独每次重新求Solo。见'+link('UI mute/solo → tracks[].Muted')+'。', '',
        '本轮修正首批C46.01：MixFxApplyOnExportMixdown虽有默认true声明，已读取的上游和本机正常mixdown都固定传applyMixFx=true，没有读该偏好。它不能列为当前有效的导出FX开关；每轨Enabled/null仍决定整体旁路。无既有音频/实验输入变动。', '',
        '导入wave的skip/trim/fadein/fadeout存储为ticks，经项目timeAxis换ms再截断到sample数；不是存储ms。截取后的PCM是副本，线性淡入/淡出可重叠相乘。GetStereoSamples/GetSamples将非44100输入做Wdl重采样，ExportAdapter本身不是任意选采样率的导出控件。见'+link('wave_parts[].skip/trim')+'、'+link('wave_parts[].fadein/fadeout')+'、'+link('wave import resampling')+'。', '',
        '内部float transport与最终编码分开：ExportAdapter为44100/2 float，正常WAV最终CreateWaveFile16；分轨ToMono选左侧，不是两侧平均。上游WriteMono16Wav的cache编码又是独立路径。MasterAdapter的3ms播放边沿淡变/等待策略不进入ExportAdapter；当前播放调用没有传有限endMs，终止由playback boundary管理，不能声称导出也自动加同一淡出。', '',
        '项目自身桥接的render --mixdown选择混音入口，否则分轨（[桥接源码](../../../bridge/OuBridge/Program.cs)）；[固定增益mix](../../../src/agent2utau/audio/mix.py)显式线性增益、拒绝peak>=1并输出PCM24。封存fresh实验还需按各自实际输入/PCM绑定追踪，不能用UI WAV16替代原实验编码，也未重跑歌曲。', '',
        'Windows NAudio实现中默认设备模式为WASAPI shared，手动设备模式为WaveOutEvent；50ms延迟/两buffers属于代码常量。NAudio实现存在不证明本次live选它；设备格式、驱动/OS重采样、增强、音量及外部播放器增益均unknown，未开启监听。', '',
        '## 图节点逐类型与端口fallback', '',
        '完整数据见[节点登记](graph-node-review.json)。31种固定类型与源码常量集合逐一相等，每种类型都有具体参数/端口行；该检查不穷尽未来扩展。连接优先，未连接输入依次取同名文本参数的Invariant float解析值、端口默认。输出节点未连接时不会进入输出plan，填写value不等于驱动。数值端口无全局NaN/Infinity拒绝，不从编辑Number类的通用min/max推断运行钳位。', '',
        '| type | 角色/输出口 | 输入口fallback | 显式参数（新节点默认） |', '|---|---|---|---|']
    for r in graph_rows:
        ports = '; '.join(f'{p["name"]}={p["fallback"]}' for p in r['ports']) or '无'
        params = '; '.join(f'{p["name"]}={p["editor_default"] if p["editor_default"] is not None else "unset"}' for p in r['parameters']) or '无额外参数'
        result.append(f'| [{r["type"]}]({r["source_url"]}) | {r["role"]}/{",".join(r["outputs"]) or "无输出口"} | {ports} | {params} |')
    result += ['', 'curve/pitch按phrase 5tick网格计算；phone outputs整part按各phone自身位置，禁止依赖pitch_input。curve和phone输出最后clip到目标descriptor范围；pitch_output覆盖绝对cents目标，该读取点没有同一descriptor钳位。pitch_input的notes/pitch_bend是绝对cents，vibrato/MOD+是相对贡献；将这些相加需显式保留音符基底。', '',
        'phoneme_input在phone输出网格直接按index读，在curve/pitch网格按step/linear/单调cubic插值；端点保持、同tick末音素获胜。Smooth/Slew状态限本次grid；LFO/随机桶按项目绝对时钟避免句拆分重置。这些是数学驱动规则，不是新的声学表现维度或自然度结论。', '',
        '本机Core不存在ExpressionGraph命名空间、UMaskedCurve、项目图库/default字段及track图属性。RPIT/PITO/图节点仅登记上游机制，本机当前不采用，不通过读写USTX猜成已生效。', '',
        '## 本机静态支持矩阵', '',
        '方法token/IL偏移、DLL SHA/MVID及版本见[JSON](local-capability-review.json)。离线PEReader只读元数据/方法体，没有加载目标程序集、运行初始化、加载模型或打开音频。完整类型/成员缺失结论限绑定Core/App；方法IL存在也不保证分支当前启用。', '',
        '| 能力 | 核查状态 | 结论 |', '|---|---|---|']
    for r in local['rows']:
        result.append(f'| {r["id"]} {r["capability"]} | {r["status"]} | {r["conclusion"]} |')
    result += ['', '首批184个ID保持；已核查支持列和说明可纠正，不改变其身份。分类仍为当前路线/其它引擎/仅上游或版本差异/编辑元数据四栏，scope行数不等于有效艺术旋钮数。成员存在、已选IL路径、非默认执行和听觉效果是独立层级；当前未把任意新能力或未听输出记为通过。', '']
    return result

def main():
    refuse_after_formal_migration()
    ap = argparse.ArgumentParser()
    ap.add_argument('--upstream', type=Path, required=True)
    ap.add_argument('--openutau', type=Path, required=True)
    ap.add_argument('--singer', required=True)
    ap.add_argument('--additional-upstream', type=Path, required=True)
    ap.add_argument('--local-metadata', type=Path, required=True)
    ap.add_argument('--editor-upstream', type=Path, required=True)
    args = ap.parse_args()
    baseline = load(OUT / 'control-inventory-audit.json')
    rows = controls()
    assert len(rows) == 184
    additional = load(Path(__file__).parent / 'stage_c_source_bindings.json')
    assert additional['upstream_commit'] == baseline['upstream_commit']
    source_bindings = [dict(b, binding_role='original_44_rechecked') for b in baseline['upstream_files']]
    for b in source_bindings:
        p = args.upstream / b['path']
        assert p.is_file() and sha(p) == b['sha256'], f'Frozen source unavailable or changed: {b["path"]}'
    source_hashes = {b['path']: b['sha256'] for b in source_bindings}
    source_roots = {b['path']: args.upstream for b in source_bindings}
    for b in additional['files']:
        p = args.additional_upstream / b['path']
        assert p.is_file() and sha(p) == b['sha256'], f'Additional frozen source changed: {b["path"]}'
        assert b['path'] not in source_hashes
        source_bindings.append(dict(b,binding_role='additional_25_frozen_source_review'))
        source_hashes[b['path']] = b['sha256']
        source_roots[b['path']] = args.additional_upstream
    editor_sources = load(Path(__file__).parent / 'stage_c_editor_source_bindings.json')
    assert editor_sources['upstream_commit'] == baseline['upstream_commit']
    for b in editor_sources['files']:
        p = args.editor_upstream / b['path']
        assert p.is_file() and sha(p) == b['sha256'], f'Editor frozen source changed: {b["path"]}'
        if b['path'] in source_hashes:
            assert source_hashes[b['path']] == b['sha256'], f'Duplicate snapshot mismatch: {b["path"]}'
            continue
        source_bindings.append(dict(b,binding_role='editor_frozen_source_review'))
        source_hashes[b['path']] = b['sha256']
        source_roots[b['path']] = args.editor_upstream
    # Add stable IDs after each original group's last ID, never renumber 184 rows.
    sequence = Counter(r['group_id'] for r in rows)
    for r in extra_controls() + editor_controls():
        sequence[r['group_id']] += 1
        r['id'] = f'PARAM:{r["group_id"]}.{sequence[r["group_id"]]:02}'
        rows.append(r)
    # Explicit registry completeness is checked against serialized type constants,
    # not against the number of table rows alone.
    import re
    nodes_text = (args.upstream / 'OpenUtau.Core/ExpressionGraph/GraphNodeTypes.cs').read_text(encoding='utf-8')
    source_types = dict(re.findall(r'public const string (\w+) = "([^"]+)";', nodes_text))
    registry = {r[0]:r[1] for r in GRAPH_TYPES}
    source_types = {k:v for k,v in source_types.items() if k not in ['Out','Value','InputCategory','MathCategory','TimeCategory','LogicCategory','OutputCategory']}
    assert registry == source_types and len(registry)==31
    with (OUT / 'openutau-controls.csv').open(encoding='utf-8-sig', newline='') as f:
        groups = {r['id']: r for r in csv.DictReader(f)}
    project_path = ROOT / 'projects/latest/lastpage_loudness_v02.ustx'
    # YAML is read as data only; no OpenUtau/native load or inferred defaults.
    published = yaml.safe_load(project_path.read_text(encoding='utf-8-sig'))
    expressions = published['expressions']
    live = []
    config_values = {}
    singer_path = args.openutau / 'Singers' / args.singer
    for b in baseline['installed_files']:
        role = b['role']
        p = (args.openutau / role) if role == 'OpenUtau.Core.dll' else (ROOT / role) if role.startswith('projects/') else (singer_path / role)
        assert p.is_file() and sha(p) == b['sha256'], f'Local bound resource unavailable or changed: {role}'
        live.append(dict(role=role, sha256=b['sha256'], bytes=p.stat().st_size, rechecked=True))
        if p.suffix == '.yaml':
            config_values[role.replace('\\','/')] = yaml.safe_load(p.read_text(encoding='utf-8'))
    assert config_values == baseline['singer_configs'], 'Bound config parse mismatch'
    local = local_review(args.local_metadata, args.openutau)
    assert local['bindings'][0]['sha256'] == live[0]['sha256']
    apply_review(rows, local)
    for r in rows:
        assert r['source_path'] in source_hashes
        lines = (source_roots[r['source_path']] / r['source_path']).read_text(encoding='utf-8').splitlines()
        matches = [i+1 for i,line in enumerate(lines) if r['source_anchor'] in line]
        assert matches, f'Missing source anchor: {r["id"]} {r["source_path"]} :: {r["source_anchor"]}'
        r['source_line'] = matches[0]
        r['source_sha256'] = source_hashes[r['source_path']]
        r['source_url'] = 'https://github.com/openutau/OpenUtau/blob/' + baseline['upstream_commit'] + '/' + r['source_path'] + '#L' + str(matches[0])
        r['source_status'] = 'frozen_upstream_field_or_path_checked_not_local_source_equivalence'
        r['upstream_commit'] = baseline['upstream_commit']
        r['current_core_sha256'] = live[0]['sha256']
        r['group_name'] = groups[r['group_id']]['control']
        d = expressions.get(r['abbreviation'])
        r['current_published_descriptor'] = d if d is not None else 'not_explicitly_declared_in_bound_published_project'
        if r.pop('published_descriptor_requested'):
            assert d is not None, r['id']
        r['engine'] = ('current DiffSinger / YousaV1.65c; core fields may be shared'
                       if r['scope'] == 'current_route' else 'see field/source engine; not current DiffSinger'
                       if r['scope'] == 'other_engine' else 'frozen upstream; installed engine path unknown'
                       if r['scope'] == 'upstream_local_unknown' else 'editor/driver metadata')
        r['auditory_label_status'] = 'no_new_labels'
    counts = Counter(r['group_id'] for r in rows)
    assert set(counts) == set(groups)
    abbreviations = {r['abbreviation'] for r in rows if r['abbreviation']}
    assert set(baseline['upstream_default_expression_abbreviations']) <= abbreviations
    preferences = preference_review(source_roots, source_hashes, baseline['upstream_commit'], args.local_metadata, rows)
    pending = PENDING
    payload = dict(schema_version=1, date='2026-10-09', stage='C',
                   status='reviewed_with_explicit_gaps', all_controls_enumerated=False,
                   frozen_scope_review_complete=True, editor_declarations_reviewed=preferences['declaration_count'],
                   all_local_paths_confirmed=False, rows=rows,
                   counts=dict(parameters=len(rows), navigation_groups=len(counts),
                               by_scope=dict(sorted(Counter(r['scope'] for r in rows).items()))),
                   continuation=dict(original_parameters=184, added_parameters=len(rows)-184,
                                     graph_types=31, original_ids_preserved=True,
                                     fixed_source_files=len(source_bindings), local_capability_entries=len(local['rows'])),
                   group_counts=dict(sorted(counts.items())), pending=pending,
                   source_bindings=source_bindings, installed_bindings_rechecked=live,
                   published_project_sha256=sha(project_path), config_values=config_values,
                   existing_evidence_role='Prior bound native experiments remain within their recorded scope. Resource/config/project hashes rechecked; offline Core/App PE metadata and selected IL checked. No target assembly execution, inference, audio, live preferences or full model rehash.',
                   no_native_execution=True, no_new_audio_or_synthesis=True,
                   no_project_skill_or_production_change=True, no_new_auditory_labels=True)
    (OUT / 'local-capability-review.json').write_text(json.dumps(local, ensure_ascii=False, indent=2)+'\n',encoding='utf-8')
    (OUT / 'editor-preferences-review.json').write_text(json.dumps(preferences,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    with (OUT / 'editor-preferences-review.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w = csv.DictWriter(f,fieldnames=list(preferences['rows'][0]))
        w.writeheader()
        w.writerows({k:csv_value(v) for k,v in r.items()} for r in preferences['rows'])
    graph_rows = []
    for symbol,name,role,ports,outputs,params,operation in GRAPH_TYPES:
        param_refs = [r['id'] for r in rows if r['field'].startswith(f'graph.nodes[type={name}].')]
        graph_rows.append(dict(type=name,role=role,ports=[dict(name=k,fallback=v) for k,v in ports],
                               outputs=outputs,parameters=[dict(name=k,editor_default=v,unit_limits=u,meaning=m) for k,v,u,m in params],
                               operation=operation,control_refs=param_refs,local_status='absent_in_bound_core',
                               source_url=next(r['source_url'] for r in rows if r['id']==param_refs[0])))
    (OUT / 'graph-node-review.json').write_text(json.dumps(dict(schema_version=1,upstream_commit=baseline['upstream_commit'],
        types=graph_rows, type_count=31, all_frozen_registered_types_enumerated=True,
        future_plugins_enumerated=False,installed_graph_supported=False),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (OUT / 'control-details.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2)+'\n',encoding='utf-8')
    with (OUT / 'control-details.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w = csv.DictWriter(f,fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows({k:csv_value(v) for k,v in r.items()} for r in rows)
    report = ['# 表1具体控制核查：阶段C续审', '',
              f'2026-10-09。48个导航分组已有{len(rows)}条具体字段/执行项（首批184、第二批136、编辑/扩展续审{len(rows)-320}条，前320个PARAM ID保持）。**C为reviewed_with_explicit_gaps：固定范围审查完成，非默认本机执行与开放扩展仍有确认缺口；D–F未执行**。固定31节点、导出/播放/pan law、本机静态矩阵及偏好/预设/网格写入分别核查。', '',
              '完整记录：[CSV](control-details.csv)、[JSON](control-details.json)。每项包含PARAM ID、旧C分组、字段、引擎、默认/范围、单位、换算、采样/裁剪、读取锚点、作用阶段、重算、支持/未确认状态和局限。范围须区分上游默认、工程声明和模型clip，缺值不能猜成可用。', '',
              '## 本轮实际证据', '',
              f'- 原44+第二批25冻结源码SHA一致；编辑续审21份中4份重复重查一致、新增17份，共{len(source_bindings)}份唯一来源。绑定单列，不覆盖旧snapshot；每行有SHA/锚点/行号，不等于非默认执行测试。',
              '- 本机Core/四配置/发布工程六绑定重查一致；另对Core与App离线读取PE完整类型成员和选定IL，保存SHA、版本、MVID、方法token与指令位置。[本机能力矩阵](local-capability-review.json)有明确的存在/缺失/未执行边界；不加载目标DLL，不启动OpenUtau，不读live偏好/权重/音频。',
              '- 原生输入/PCM证据沿用已绑定实验，不扩大条件。本轮没有新的导出音频、推理或试听；静态公式与调用路径不证明听感。', '',
              '## 已明确的易混项', '',
              '| 项 | 本次区分 | 固定源码入口 |', '|---|---|---|']
    important = ['PARAM:C01.01','PARAM:C03.01','PARAM:C10.01','PARAM:C11.01','PARAM:C14.01','PARAM:C15.01','PARAM:C16.01',
                 'PARAM:C19.01','PARAM:C25.01','PARAM:C44.02','PARAM:C45.02','PARAM:C46.01']
    for id_ in important:
        r = next(r for r in rows if r['id'] == id_)
        report.append(f"| {r['field']} | {r['transform']}；{r['limitation']} | [读取/声明]({r['source_url']}) |")
    report += path_report(rows, local, graph_rows)
    report += editor_report(preferences, rows)
    report += ['', 'DYN是输出振幅；VOIC/BREC/TENC是预测上的模型条件增量；SHFC影响条件音区与预测，GENC输入不是实测共振峰。人工控制进入时间仍是函数/驱动的设计量，没有新增一个“自然度”或“口型”独立旋钮。字段和公式不支持统一剂量/听觉方向。', '',
               '## 分组展开及范围', '', '| 旧组 | 条目数 | 导航名称 |', '|---|---:|---|']
    for g,n in sorted(counts.items()):
        report.append(f'| {g} | {n} | {groups[g]["control"]} |')
    report += ['', '按当前路线、其它引擎、仅上游/本机未知与编辑元数据分别计数；当前路线包含禁用能力、资源契约和推理设置，**不能把该类行数当成有效艺术旋钮数**。同一分组可能含多种状态，须读逐项current_support/condition。', '',
               '## 保留的C确认缺口', '', '| 范围 | 缺口 | 需要什么 |', '|---|---|---|']
    for r in pending:
        report.append(f'| {r["group"]} | {r["issue"]} | {r["needed"]} |')
    report += ['', '原48类清单及表1/表2基线不改；不创建参数搜索/自动修复器，不改Skill/歌曲/音频。当前[计划](../../../plan.md)的下一步为D，D/E/F尚未执行。文件与保护绑定见[审计](table1-execution-audit.json)。', '']
    (OUT / 'table1-control-review.md').write_text('\n'.join(report),encoding='utf-8')
    print(json.dumps(dict(stage='C',status=payload['status'],**payload['counts']),ensure_ascii=True))

if __name__ == '__main__':
    main()
