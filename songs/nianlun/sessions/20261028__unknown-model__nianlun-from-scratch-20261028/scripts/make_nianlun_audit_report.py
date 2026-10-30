"""组装公开报告 JSON（合并审查产物，不改任何生产文件）。"""
import json
import pathlib
import sys

sys.stdout.reconfigure(encoding="utf-8")
S = pathlib.Path(r"E:\project\agent2utau\scratch")
audit = json.loads((S / "audit_nianlun_phrases.json").read_text(encoding="utf-8"))
grading = json.loads((S / "audit_nianlun_grading.json").read_text(encoding="utf-8"))
out = pathlib.Path(r"E:\project\agent2utau\docs\reports\nianlun")
out.mkdir(parents=True, exist_ok=True)

summary = audit["summary"]
phr = {p["part_index"]: p for p in audit["phrases"]}

payload = dict(
    schema_version=1,
    report_id="nianlun-phrase-audit-20261028",
    created="2026-10-28",
    run="runs/production/nianlun-from-scratch-20261028",
    scope="read-only audit of 51 phrases / 349 vowel units; no project, audio, plan or Skill change",
    method=[
        "源事实: observation/{fcpe,rmvpe}.npz 双检测器逐帧F0 + game.json 转谱 + hfa/hfa_summary.json 音素/呼吸",
        "设计事实: design/plan.json (center_nodes/components) + design/ledger.json (349 前向决策) + compiled/pitch.json (实际最终线) + compiled/project.ustx",
        "旋律身份: 音符中部60%窗口内 FCPE 与 RMVPE 中位互相一致时与设计最终线比较, 两检测器矛盾记 unknown",
        "字腹: 源元音支撑窗 F0 跨度 vs 设计最终线同窗跨度",
        "图审: 实际打开 compiled/execution-review/atlas 中 p19/p40/p45/p50 共 4 张 F0 视图",
    ],
    structural_findings=[
        dict(id="S1", level="P0", title="整首是固定配方，不是逐句设计",
             evidence="349 组件中 |peak|=52c 占 296、|peak|=32c 占 28、其余 25 个一次性; "
                      "全部 347 个 finite_return 落在 6 个时间归一化签名 (82/83/57/57/40/28 次); "
                      "68 个元音的设计字腹跨度精确等于 52.0c, 10 个等于 64.0c",
             skill_ref="整句尺度与字腹运动 / 执行复检契约(换ID换数字不解除复审)"),
        dict(id="S2", level="P0", title="字腹被压平",
             evidence=f"338 个可比元音中 {summary['n_flattened_total']} 个 (源跨度>80c) 设计跨度不足源一半; "
                      "源元音跨度中位 200-300c, 35 个元音源跨度>600c",
             skill_ref="整句尺度与字腹运动: 入口/出口数百cents会掩盖几乎平直的主体"),
        dict(id="S3", level="P0", title="旋律身份偏离原唱",
             evidence="两检测器一致口径下 331 个可比音符中 123 个与原唱偏差>100c; "
                      "整句轮廓相关 r: p19=0.15 p41=0.34 p03=0.33 p14=0.48 p07=0.51 p11=0.58",
             skill_ref="音乐身份改变须记录原目标、新目标和原因"),
        dict(id="S4", level="P0", title="时值被压碎",
             evidence="12 个唱字写成 0.019-0.097s (最短 p49『可』0.019s), 源对应字 0.40-0.68s; "
                      "时值比<0.7 的 135 个",
             skill_ref="唱字时长 / 音素时钟"),
        dict(id="S5", level="P1", title="呼吸与分句脱节",
             evidence="工程 59 个 SP/AP (其中 51 个固定 0.200s) vs HFA 观测 132 个呼吸标记; "
                      "音符间>0.4s 静默 0 处; SP 插在唱字中间 (p45『我』0.022s 后紧跟 SP 0.219s)",
             skill_ref="AP/SP 放置与呼吸预算"),
        dict(id="S6", level="P1", title="长字未展开",
             evidence="41 个>=0.45s 唱字中仅 2 个组件覆盖>=90% 时长; "
                      "全曲仅 2 个 oscillation (p33『恨』1.34s 深46c, p50『本』2.19s 深34c, 约5.5Hz)",
             skill_ref="持续字需要展开 / 局部周期"),
        dict(id="S7", level="P0", title="发声与动态控制完全缺失",
             evidence="compiled/project.ustx 中 phoneme_expressions 非空的音符 = 0, track_expressions = []; "
                      "无任何 VOIC/BREC/DYN/TENC",
             skill_ref="多通道与长音 / 实际包络与舒适度"),
        dict(id="S8", level="P0", title="复检收据不成立",
             evidence="review-execution 未传 --ledger -> inventory_coverage=fail(missing_forward_decision_ledger_or_plan), "
                      "实际 design/ledger.json 存在且含 349 条前向决策; local_visual_review 0/349; "
                      "musical_quality=unverified, listening=unknown",
             skill_ref="执行复检契约 v2"),
    ],
    phrase_findings=grading,
    totals=dict(
        phrases=51, units=349, notes=596, singing=349,
        level_counts={k: sum(1 for g in grading if g["level"] == k) for k in ("P0", "P1", "P2", "P3")},
        template_peak_52=296, template_peak_32=28, one_off_peak=25,
        flattened_units=summary["n_flattened_total"],
        bad_notes_two_detector_agree=123, unknown_notes=4,
        tiny_notes=12, breath_engine=59, breath_hfa=132,
        long_notes=41, long_notes_expanded=2,
    ),
    verification=dict(
        native_max_error_c=0.4999557576211373,
        native_contract_c=0.501,
        listening="unknown (no audio perception in this audit; user listening pending)",
        musical_quality="unverified",
        new_models=0, new_audio=0, project_modified=False, skill_modified=False,
    ),
)
p = out / "nianlun-phrase-audit-20261028.json"
p.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
print("written:", p, p.stat().st_size, "bytes")
print("level counts:", payload["totals"]["level_counts"])
