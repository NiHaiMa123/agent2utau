"""Finite authored design. No inference, parameter search or empirical claims."""
import copy

PROTOCOL_ID = 'T2D-SHFC-PATHS-01'
PROTO_JSON = 'validation-protocols/shfc-path-separation-v1.json'
PROTO_MD = 'validation-protocols/shfc-path-separation-v1.md'


def design(ledger):
    cases = []
    for rid, role in [('RESP-003', 'mechanism_discrimination_known_problem'),
                      ('RESP-007', 'cross_vowel_regression_check_reported_solid')]:
        r = next(x for x in ledger['responses'] if x['id'] == rid)
        c = copy.deepcopy(r['condition'])
        start, end = c['vowel_s']
        # Preserve the exact historically accepted bao geometry, including its
        # end anchor (not a newly rounded vowel-relative reconstruction).
        anchors = ([r['intervention']['support_s'][0], r['intervention']['same_arrival_s'],
                    r['intervention']['same_release_start_s'], r['intervention']['support_s'][1]]
                   if rid == 'RESP-003' else [start - .080, start + .065, end - .067, end - .012])
        cases.append(dict(condition=c, source_record_id=rid, role=role, independent_holdout=False,
            baseline_project=copy.deepcopy(next(v for v in r['record_v3']['variants'] if v['logical_label'] == 'A')['project']),
            nominal_Q5_anchors_s=anchors,
            shifted_support_s=[anchors[0], anchors[-1]],
            listener_focus_s=[c['native_phones'][0]['start_ms']/1000 - .8, end + .8],
            peak_cents=-400, attack_ms=145, release_ms=55,
            design_reason=('重建抱C的完整路径再分离中介；原可用反馈是C-B，不能当此次S-A已通过'
                if rid == 'RESP-003' else '同为高音区且时长近似、不同元音/声母；检查偏实条件回退，不把偏实视作全面正常'),
            baseline_listening_truth='historical_partial_label; new A/S/D/P listening pending'))
    return dict(schema_version=1, id=PROTOCOL_ID, version=1, stage='2D', date='2026-10-10',
        status='frozen_design_with_execution_dependencies', execution_status='not_executed',
        task='区分有限SHFC条件的直接声学F0路径与三通道预测依赖，检查异元音偏实条件的回退',
        hypothesis='局部SHFC响应可能来自直接条件、预测依赖或二者组合；不预设唯一机制或改善方向',
        historical_evidence=['RESP-002', 'RESP-003', 'RESP-004', 'RESP-005', 'RESP-006', 'RESP-007', 'RESP-008', 'RESP-009', 'RESP-010', 'OBS-002'],
        counterexamples=['果SHFC未改善且响度下降；不恢复该路线', '六条件BREC -10均无可感知差别；不加量',
            '抱C的VOIC降低/TENC升高反驳统一VOIC升高/TENC降低', '抱C标签来自C-B；未独立试听C-A'],
        table1_refs=dict(main_parameter='PARAM:C14.01', mediated_parameters=['PARAM:C11.01', 'PARAM:C12.01', 'PARAM:C13.01'],
            driver='PARAM:C47.06', entity_ids=['ACO:P1', 'ACO:L1', 'EVT:L4', 'EVT:R3', 'EVT:S6', 'EVT:T4', 'PER:S1', 'PER:T3', 'PER:L1', 'PER:X1'],
            measurement_ids=['MEAS:D01', 'MEAS:D06', 'MEAS:D09', 'MEAS:D30', 'MEAS:D29', 'MEAS:D33', 'MEAS:D42', 'MEAS:D43', 'MEAS:D40', 'MEAS:D44']),
        cases=cases,
        variant_matrix=[
            dict(id='A', acoustic_F0='unshifted', prediction='fresh_unshifted_same_phrase', native_equivalent=True),
            dict(id='S', acoustic_F0='SHFC_shifted', prediction='fresh_SHFC_shifted_same_phrase', native_equivalent=True),
            dict(id='D', acoustic_F0='SHFC_shifted', prediction='fresh_unshifted_same_phrase', native_equivalent=False),
            dict(id='P', acoustic_F0='unshifted', prediction='fresh_SHFC_shifted_same_phrase', native_equivalent=False)],
        intervention_scope='一个主干预SHFC；2×2研究路径拆分。D/P是反事实研究输入，不是可直接编码的USTX或新艺术旋钮',
        prediction_exchange_rule='只用同一条件、同一新批次的A/S新variance预测；不读旧预测作为合成输入，不跨字复制或拟合作者数组。三通道整组交换后加该条件不变人工增量并按原生float32裁剪',
        geometry=dict(function='Q5 smoothstep: q(u)=6u^5-15u^4+10u^3; rise peak*q, exit peak*(1-q), else 0/plateau',
            grid_ticks=5, storage_units='cents, not semitones', explicit_diagnostic_range_cents=[-1200, 1200],
            value_quantization='在原工程part-local的整数5tick点按timeAxis换秒评估Q5，四舍六入五成双取整为整数cents；名义支撑外0。原生5tick/模型帧线性采样另核查，不以模板名字保证抱S与旧C输入/波形精确',
            native_sampling='按原timeAxis/5tick点编译；独立核查实采样、float32 /100与/1200顺序、峰值与支撑；不得用1tick或宽容差掩盖失败',
            fallback='若实采样峰值/支撑/非重叠失败，停止；不自动缩时长、换条件或重定剂量'),
        fixed=dict(common_context=copy.deepcopy(ledger['common_context']), acoustic_steps=20, acoustic_depth=.6,
            runtime_expected_hashes=copy.deepcopy(ledger['runtime_hash_bindings']),
            model_adapter='仅新run中的显式噪声适配器；权重initializer精确，绑定来源/适配器SHA。模型安装不改',
            score='原v02完整短语；note identity/pitch/clock/phones/languages/AP-SP/source unknown不变',
            speaker='两阶段Normal75/Classic25；绑定实际embedding并验证tensor，不只写名字',
            controls='TENC/VOIC/BREC/GENC/VELC及所有非SHFC人工控制、DYN不变；不归零基底',
            downstream='每条件完整短语，保留padding及上下文；不在目标窗外强制抹除预测/声学响应',
            presentation='原生DYN，固定vocal1.5/backing0.7；FLOAT诊断/同编码交付；无归一化/响度匹配/压缩；绑定裁切样本与增益',
            preservation='已接受抱C及完整制作方案保持；word214原v02仅诊断基底，不发布替换整曲'),
        budget=dict(conditions=2, logical_variants_per_condition=4, identical_repetitions_per_variant=2,
            variance_predictions_per_condition=4, total_variance_inferences=8,
            total_acoustic_vocoder_waveforms=16, independent_effect_replications=0,
            listener_pairs_per_condition=5, total_listener_pairs=10, parameter_sweeps=0,
            infrastructure_retry_limit_per_failed_operation=1,
            retry_policy='仅同输入初始化/IO失败重试一次；所有失败保留。技术隔离/重复不精确不得重试选好结果，禁止换seed'),
        comparisons=[dict(id=x, direction=x.replace('_', '-')) for x in ['S_A', 'D_A', 'P_A', 'S_D', 'S_P']],
        gates=[
            '2E首先实现独立研究runner与验证器；现controlled_probe只支持A/A-repeat/B，没有D/P接口，不直接调用为路径分离',
            '重新SHA核查当前runtime47项及依赖、原baseline工程、fresh模型和noise适配器；不一致停止，不升级安装',
            '先用有限合成数组/故意错误检查器验证D-A仅f0、P-A仅三最终条件、S-D仅预测组、S-P仅f0，非选条件及vocoder F0精确；这些数组不算真实检测器验证',
            'A/S使用现SHFC native隔离检查；新原生输出是桥接获取条件的缓存，不算本预算的seeded诊断波形',
            '每变体两次输入/预测/波形精确；所有weights/noise/speaker/manual/phone时钟与clip计数保存；任何非有限/新裁剪/峰值>=1停止交付',
            '独立数值/PCM窗检查通过后方交付试听；F0估计可unknown，不能拿未经验证检测器作自然度门禁'],
        observations=dict(input_layer='保存native/fresh actual input/prediction/manual/final/two F0 paths，独立归因允许变化及完整短语响应',
            PCM_windows='完整目标声母/元音、元音前后60ms、核心20%-80%、前后各一个完整phone、整句；原生→PCM→delivery时钟映射绑定，超界/交叉窗标unknown',
            level='完整窗RMS/peak；30/50ms中心矩形窗，hop5ms，半开窗样本索引ceil(t*sr)，不补零；零能量null/zero。dB比不等于感知响度',
            spectral='原生mel与去逐帧均值的谱形差；只能叫代理，不认定formant/生理寄存器/破音病因',
            F0='FCPE/RMVPE模型/时钟/SHA另绑定；有效voiced有限>0才比较，不跨无声插值；冲突/覆盖不足unknown并报有效率；不预设校准阈值或宣称输出F0固定',
            method_status='Table1相关测量仍未完整验证；2E只可提升实际验证的数值/组件范围，听觉/真值单列'),
        listening=dict(phase='2E生成新对照且技术gate通过后，必须人工试听；没有反馈只记录pending',
            schedule='先完整上下文A/S/D/P独立文件，再固定五组人声对照；混音作为同增益复查，每组两顺序各保留，编码表先固定且不按得分选顺序',
            presentation_order=['S-A', 'A-S', 'D-A', 'A-D', 'P-A', 'A-P', 'S-D', 'D-S', 'S-P', 'P-S'],
            anonymous_code_map={'word225': {'K1': 'A', 'K2': 'D', 'K3': 'S', 'K4': 'P'},
                'word214': {'K1': 'P', 'K2': 'S', 'K3': 'A', 'K4': 'D'}},
            clip_samples='各listener_focus_s半开裁切ceil(t*44100)；同condition所有版本与两顺序同长度；完整phone不足则保留整句并标focus未完整，不补0伪造边界',
            blinding='可用固定匿名编码；是否盲测/是否看标签如实记录，不冒称双盲',
            labels=['差别是否可感知/不确定/无差别', '偏假/往上顶或偏实方向及是否更可用', '字头/咬字/破音位置', '感知响度与邻字/上下文回退'],
            timestamps_device='回报时间与设备/播放器/OS设置能取得则记录，缺失unknown；不要求人工补造精确位置',
            statistics='2条件、同曲已见标签，不做显著性/群体统计；同seed重复只是复现，不能计作独立效应重复'),
        interpretation=[
            'S-A若本轮无可感知差别，保留既往C-B局部接受；本轮不支持新的S-A效果解释，停止扩大验证',
            'D-A有同向可用响应可支持此研究反事实中的直接路径作用，P-A同理预测组；不能归给单一VOIC/BREC/TENC或生理机制',
            'S可感知而D/P均未感知，只记录联合路径/剂量下的结果，不以未感知宣布分量为零或证明交互',
            '数值interaction=metric(S)-metric(D)-metric(P)+metric(A)仅用于同定义连续代理，不用于主观词/未知/检测冲突，也不代表自然度',
            'word214任一新副作用限定适用范围；2个条件均已参与设计，不能称留出/跨曲迁移或通用规律'],
        stop_rules=['不加剂量、不扫时间/元音/seed、不补第三条件、不恢复果SHFC或BREC/VOIC提案',
            '缺可靠接口/原生隔离失败/runtime差异/数值重复不精确→技术停止并记录依赖缺口，不转自动搜索',
            '新破音/响度下降/咬字或邻字回退→该条件不可用，保留失败；不加增益掩盖',
            '无区别/不确定→本协议限定阴性/unknown；不等待总会成功的候选',
            '最多本批16套seeded新波形、10组主对照；结束后收集结论，2F留出/2G整句全曲/2H Skill需另明确范围'],
        exclusions=['不修改歌曲工程/发布USTX/Skill/模型安装', '不将D/P写回制作', '不将本批通过当通用规律', '不自动启用CI'],
        result=dict(new_audio=0, new_feedback=0, generic_rule_validated=False, causal_mechanism_validated=False,
            execution_adapter_validated=False, all_measurement_methods_validated=False))
