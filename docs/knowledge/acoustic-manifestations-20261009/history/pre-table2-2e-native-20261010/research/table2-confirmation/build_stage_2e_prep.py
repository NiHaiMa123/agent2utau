"""Publish preparation scope, not real synthesis or auditory results."""
import json
from freeze_stage_2d import ROOT, HERE, OUT, load, sha

OUTPUTS = ['table2-stage-2e-preparation.json', 'table2-stage-2e-preparation.md']


def main():
    binding = load(HERE / 'stage_2e_prep_baseline_binding.json')
    assert sha(ROOT / binding['manifest']) == binding['sha256']
    run = ROOT / binding['run']
    runtime = load(run / 'runtime-byte-check.json')
    assert runtime['counts'] == dict(exact=47, changed=0, missing=0)
    files = ['shfc_path_adapter.py', 'shfc_path_checks.py', 'shfc_path_runner.py', 'shfc_path_backend.py',
        'check_stage_2e_runtime.py']
    refs = [dict(path=(HERE / n).relative_to(ROOT).as_posix(), sha256=sha(HERE / n)) for n in files]
    refs.append(dict(path='tests/contracts/test_shfc_path_research.py', sha256=sha(ROOT / 'tests/contracts/test_shfc_path_research.py')))
    report = dict(stage='2E-prep', date='2026-10-10', status='research_interface_prepared_with_explicit_execution_gaps',
        stage_2E_complete=False, baseline=binding, protocol_id='T2D-SHFC-PATHS-01', protocol_version=1,
        protocol_bindings=load(HERE / 'stage_2d_protocol_binding.json'), implementation_bindings=refs,
        implemented=['sealed protocol/case gate', 'fresh predictor callback -> 2x2 same-condition tensor assembly',
            'independent minimum/maximum reconstruction and new-clipping guard',
            'native SHFC isolation reused with unchanged production code',
            'shared deterministic noise and same-input bounded repeat',
            'vocoder target separated from acoustic conditioning F0',
            'two conditions/8 variance calls/16 raw render slots; no cache prediction argument',
            'lazy CPU ONNX backend, source runtime/weight SHA and two-stage speaker guard',
            'raw in-memory render callback and repeat gate, rechecks both prepared repetitions before callbacks'],
        validation_scope=dict(contract_tests=40, synthetic_conditions=2, prepared_mock_acoustic_inputs=16,
            mock_raw_renderer_callback_budget=16, actual_current_native_inputs_or_Q5_sampling_validated=False,
            actual_ONNX_predictor_or_acoustic_or_vocoder_executed=False, real_embeddings_loaded=False,
            actual_output_PCM_or_DYN_or_gain_validated=False, real_waveforms_created=0, new_auditory_feedback=0,
            installed_resource_bytes_rehashed=47, installed_resource_bytes_identical=47),
        runtime_binding=dict(path=(run/'runtime-byte-check.json').relative_to(ROOT).as_posix(),sha256=sha(run/'runtime-byte-check.json'),
            scope='current installed bytes only; not branch execution/model response or device proof'),
        independent_checker='shfc_path_checks.py imports only numpy; never calls assembler or trusts its claimed checks',
        unknown=['actual fresh native export identity/phones/context and SHFC 5tick Q5 sampling',
            'actual current speaker tensor/embedding mixture and ONNX adapter/model execution',
            'actual fresh prediction/source provenance under complete runtime/file bindings',
            'real acoustic/vocoder repetition, DYN/fixed gain/delivery PCM and listener comparisons',
            'real F0 estimator truth, formants/break classification and perceptual outcomes',
            'holdout/cross-song/full-phrase acceptance and generic rule validity'],
        semantic_boundaries=['D/P remain research counterfactuals, never encoded as production USTX controls',
            'synthetic fixtures and mocked sessions are contract evidence, not independent audio experiments',
            'predictor-return provenance tags prove API scope, not that a caller actually executed ONNX',
            'raw renderer function has no delivery/DYN/gain encoder or auto CLI; remains separate from listening',
            'backend constructors not called on real models; no automatic retry/parameter search'],
        preservation=dict(production_skill_project_files=79, protected_inputs=67,
            old_2D_protocol_and_outputs_unchanged=True, old_2C_records_unchanged=True,
            auto_CI_enabled=False, new_generic_rules=0, measurement_validated_upgrades=0),
        next='2E native-input/Q5 identity and real backend integration checks before explicitly scoped rendering/listening')
    (OUT / OUTPUTS[0]).write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n',encoding='utf-8')
    md = '''# 表2 2E：研究接口准备

2026-10-10。状态research_interface_prepared_with_explicit_execution_gaps。**2E准备部分完成，受控渲染与人工试听尚未执行，2E整体未完成。** [机器报告](table2-stage-2e-preparation.json)与[审计](table2-stage-2e-prep-audit.json)分开记代码契约、当前文件SHA和真实执行缺口；原[冻结协议](validation-protocols/shfc-path-separation-v1.md)及2D/2C审计保持原字节。

研究接口仅支持冻结的抱225/只214、A/S/D/P四路径。新predictor回调每条件两次A/S预测，组装同一条件/同一批次的三通道最终输入；加不变人工基底，保留完整上下文响应。D-A仅直接F0路径，P-A仅预测组三通道，vocoder始终使用原目标F0。独立检查器不调用组装函数，另用minimum/maximum重建float32最终输入，检查非选张量、预测归属、裁剪及重复。预测不产生变化也合法，不能为符合假设要求非零响应。

有限批接口固定8次variance回调/16个acoustic输入槽位。后续raw render接口核查16个内存输出及同输入mel/数值数组精确重复；它在调用后端前重新检查输入，即使两次重复被同样改坏也拒绝。没有DYN/增益/交付编码或试听自动入口。惰性ONNX后端代码只在显式构造时读取模型、写新run适配器并创建CPU session；本轮没有构造真实后端或加载模型，原权重/生产包/原生桥接不改。

40项新增契约测试使用冻结名义时钟的合成张量和mock session，覆盖错误路径、vocoder F0、speaker/token/noise变化、旧批次/跨字/错误来源预测、手工基底丢失、部分通道、dtype/NaN、新裁剪、错误时钟/steps/depth、设计偏离、repeat失败、输出边界/预算及别名解析。这不是40个音频实验，也不验证当前真实native输入、Q5采样、embedding、模型响应或检测器准确度。mock“wave”只有有限数值数组，不保存音频文件。

当前47运行资源逐文件SHA全部与冻结期望一致，明确安装来自已绑定BREC原runtime登记表和现配置匹配，不从文件存在猜分支执行。最初把external-resource登记别名当成仓库实际路径的47个未找到定位项已拒绝、另存本轮run；按来源的实际安装映射修正后全部一致。原登记表SHA前后保持，没有据最初定位失败宣布资源缺失或修复安装。当前SHA一致不等于实际两阶段speaker/所有分支/声学效果通过。

更新前24份文档/源码在[快照](history/pre-table2-2e-prep-20261010/snapshot-manifest.json)保持；79份生产/桥接/Skill/发布工程及67保护输入SHA保持。旧2D验证入口已guard，原源码保存在快照，协议及其设计/构建源码SHA仍封存不改。测试临时文件在本轮独立runs/test-results，日志在新的runs/research；原run/音频不写入，自动CI仍只有手动触发。

下一步仍属于2E：实际native身份/完整音素时钟/5tick Q5采样及后端依赖核查，然后在明确的新音频范围内执行冻结的16套对照并人工试听。真实波形/PCM/DYN/1.5及.7增益、双F0、响度/破音/咬字与邻字标签仍待验证；没有反馈即pending，不以数值代理改为听觉通过。接受抱C及果SHFC/BREC阴性不变；2F留出、2G整句全曲、2H知识/Skill更新未开始。
'''
    (OUT / OUTPUTS[1]).write_text(md,encoding='utf-8')
    print(json.dumps(dict(status=report['status'],contract_tests=40,runtime_exact=47,real_waveforms=0,stage_2E_complete=False)))


if __name__ == '__main__':
    main()
