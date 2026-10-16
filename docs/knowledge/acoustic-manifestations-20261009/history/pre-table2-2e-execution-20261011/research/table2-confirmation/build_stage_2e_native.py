"""Publish actual-input/static checks with explicit nonexecution boundaries."""
import json
from freeze_stage_2d import ROOT, HERE, OUT, load, sha

OUTPUTS=['table2-stage-2e-native-check.json','table2-stage-2e-native-check.md']


def main():
    binding=load(HERE/'stage_2e_native_baseline_binding.json')
    assert sha(ROOT/binding['manifest'])==binding['sha256']
    run=ROOT/binding['run']; proof=run/'native-static-check.json'
    result=load(proof)
    assert result['runtime_resources_rehashed']==47 and result['real_waveforms']==0
    code=['freeze_stage_2e_native.py','shfc_native_preflight.py','check_stage_2e_native.py',
        'shfc_path_adapter.py','shfc_path_runner.py','shfc_path_backend.py','build_stage_2e_native.py']
    report=dict(stage='2E-native',date='2026-10-10',status=result['status'],baseline=binding,
        stage_2E_complete=False,protocol_id='T2D-SHFC-PATHS-01',protocol_version=1,
        proof=dict(path=proof.relative_to(ROOT).as_posix(),sha256=sha(proof)),
        protocol_bindings=load(HERE/'stage_2d_protocol_binding.json')['bindings'],
        implementation_bindings=[dict(path=(HERE/n).relative_to(ROOT).as_posix(),sha256=sha(HERE/n)) for n in code]+[
            dict(path='tests/contracts/'+n,sha256=sha(ROOT/'tests/contracts'/n)) for n in
                ['test_shfc_path_research.py','test_shfc_native_preflight.py']],
        source_bindings=result['source_bindings'],
        conditions=[dict(condition_id=r['condition_id'],historical_identity=r['historical_identity'],
            sampling=r['sampling'],new_native_export_matches=False,
            historical_C_sample_exact=r.get('old_C_native_SHFC_samples_exact',None)) for r in result['rows']],
        confirmed_scope=dict(historical_A_complete_real_phones=41,historical_A_frame_counts=[421,594],
            historical_C_integer_curve_and_acoustic_and_variance_SHFC_samples_exact=True,
            actual_speaker_layout_checks=6,current_runtime_SHA=47,current_ONNX_graph_declarations=3,
            actual_record_identity_negative_controls=6,synthetic_research_contract_tests=55),
        corrected=['Boolean retake tensor binding accepted with dtype/content SHA',
            'Exact native float32 frame representation, not double period equality',
            'Model scalar steps/depth feed reshape only; no value/dtype casts',
            'Local variance interpolation double*0.01 before float32; 3 old-C samples differ from float32 cents/100'],
        correction_scope='Code representation corrections only; sealed dose/anchors/grid/support/budget unchanged; no tolerance widening',
        execution=dict(new_native_exports=0,variance_inferences=0,acoustic_vocoder_waveforms=0,
            delivered_PCM=0,new_feedback=0,generic_rules=0,measurement_validated_upgrades=False),
        remaining=['Fresh A/S export and installed sampling for both conditions (zhi S has never been exported)',
            'Current linguistic encoder/new variance, acoustic and vocoder execution; no old prediction feed',
            'Token vocabulary contents/encoder provenance and source unknown remain explicit',
            'Real seeded waveform repeat, nonfinite/clipping and dual-F0 coverage checks',
            'Native DYN, fixed gains1.5/.7, PCM encoding, phrase/focus/neighbor boundaries',
            'Human listening and feedback; no new sensory conclusion or generalization'],
        next='2E finite execution prerequisites and explicitly authorized new batch; 2F–2H not executed')
    (OUT/OUTPUTS[0]).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    lines=['# 表2阶段2E：实际输入与静态后端核查','',
        '2026-10-10。状态：historical_native_and_static_backend_checked_with_execution_gaps。**本轮只读核查已有绑定输入及当前静态依赖，2E真实实验/人工试听尚未执行。**', '',
        '[JSON](table2-stage-2e-native-check.json)逐项列出范围与SHA；[原接口准备](table2-stage-2e-preparation.md)及其审计保留当时原字节。更新前20份文档/接口/测试原字节冻结，79生产/桥接/Skill/发布工程及67保护输入保持；本轮无新原生导出、推理或音频。', '',
        '## 已核查范围','',
        '| 条件 | 绑定历史A的完整音素时钟 | 5tick设计的本机IL重建采样 | 证据边界 |',
        '|---|---|---|---|',
        '| 抱 word225 / phrase22 | 20实际音素，含padding共22段、421帧；b/ao为第8/9项 | 32帧、−400c，183.741021920–184.100931238s | 整数曲线点、acoustic cents及variance半音与旧C精确；不是本批新S导出或新推理 |',
        '| 只 word214 / phrase21 | 21实际音素，含padding共23段、594帧；zh/ir为第3/4项 | 33帧、−400c，175.968322035–176.339841331s | 仅冻结设计与本机IL的数学重建；新S实际导出未核查 |', '',
        '音素位置/时长/音高及完整padding/gap累计round-to-even重建与已绑定native acoustic durations/variance ph_dur精确，所有zh音素语言ID4。词表token语义及新linguistic encoder执行未验证；不凭音素字符串/框架通过宣布它们也通过。', '',
        '读取当前四份Normal/Classic embedding，六组历史A/C两阶段完整speaker张量与75/25混合精确；这是输入字节核查，尚无本批新模型执行。47安装资源SHA在前后均一致。三ONNX读取graph input/output声明、唯一RandomNormalLike布局及无external initializer；未创建InferenceSession。模型feed仅把steps/depth单元素改成声明的scalar形状，数值、dtype和原native张量不变。', '',
        '## 研究接口纠正与失败保留','',
        '- 实际variance含bool retake，原绑定器只接受数值dtype会误拒绝；现接受bool并保留dtype/形状/内容SHA。',
        '- 理想512/44100周期为11.609977324263038ms，native float32为11.609977722167969ms，JSON显示11.609978ms。检查其float32表示精确一致；相邻float32值仍拒绝，不增宽音乐或时间容差。',
        '- 本机Core TimeAxis::MsPosToTickPos先round-to-even为整数tick，再进行5tick模型帧插值。DsVariance的SHFC转换为double插值值*0.01后转float32；acoustic先取float32 cents再/1200。首轮用float32 cents/100重建半音导致3帧不相等，失败日志保留；按IL纠正后精确通过。剂量、锚点、5tick网格、支撑和16波形预算保持。',
        '- 55项研究契约测试含旧40项及新增15项；六个真实绑定输入的刻意身份混淆（phrase/clock/tone/start/duration/language）被拒绝。测试和静态数组均不能计为推理/试听样本。', '',
        '## 人工试听仍是下一阶段验收','',
        '旧C可用反馈来自C-B，不能当新S-A已通过。此处两个条件均为已见设计条件，不是留出。旧音频/预测不作为新批输入；新A/S必须来自同条件/同批次，D/P仅研究反事实。', '',
        '下一项是2E有限执行前置核查及明确授权的新批次：新A/S原生输入/采样、当前linguistic/variance/acoustic/vocoder、同输入重复、DYN/1.5/.7固定增益、PCM/双F0与邻字边界；通过后才交付匿名对照并由用户试听。当前“歌曲/音频/Skill不改”的范围仍保持，不自动生成16套实验波形、不自动CI、不转2F–2H。缺少反馈保持pending/unknown，measurement_validated全部仍false、通用规律0。','']
    (OUT/OUTPUTS[1]).write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps(dict(outputs=2,status=report['status'],new_audio=0)))


if __name__=='__main__':main()
