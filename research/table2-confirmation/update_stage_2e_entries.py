"""Update the authorized root-plan entry points, retaining historical stage text."""
from freeze_stage_2d import ROOT,OUT,HERE,load

MARK='2E有限实际执行状态technical_execution_complete_pending_human_listening'
STATUS=('2E有限实际执行状态technical_execution_complete_pending_human_listening：用户明确授权冻结批次，'
    '两条件新A/S原生4组导出及抱32帧/只33帧5tick采样通过；8次新variance、16套固定种子acoustic/vocoder波形，'
    '另4套原生缓存技术波形单列。四路径/重复/两阶段speaker/原生DYN/固定1.5与0.7/PCM24独立检查通过，'
    '两个新A及新抱S分别与历史A/C的fresh输入、预测、raw PCM精确。53窗口与16次双F0观测只作有限代理，'
    '只的焦点早于波形起点，按协议保留整句并标未完整。72份分开上下文/焦点/两顺序对照衍生PCM待人工试听，'
    '154项本机测试通过；20快照/79生产与Skill及工程/67保护输入/1079旧封存路径/567当前歌曲run/47安装SHA保持。'
    '新反馈0、通用规律0，全部measurement_validated仍false；2E整体待听觉确认，2F–2H未执行。'
    '原歌曲、既有音频和Skill不改，单Agent、CI仅手动，下一步只接本批试听反馈，不自动扩展。')

def main():
    run=ROOT/load(HERE/'stage_2e_execution_baseline_binding.json')['run']
    assert load(run/'technical-delivery-check.json')['eligible_for_listening']
    for name in ['plan.md','plan-table2.md']:
        path=ROOT/name;text=path.read_text(encoding='utf-8')
        if MARK in text:continue
        if name=='plan.md':
            text=text.replace('更新：2026-10-10。','更新：2026-10-11。',1)
            text=text.replace('2E研究接口/独立检查器准备完成，真实执行/试听尚未进行。','2E有限实际执行及技术门禁完成，现待本批人工试听。',1)
            text=text.replace('2E准备完成而真实渲染/试听尚未执行，2F及以后未执行','2E有限渲染/技术交付完成、人工试听pending，2F及以后未执行',1)
            text=text.replace('由当前Codex单个Agent执行。2026-10-10当前状态：','由当前Codex单个Agent执行。2026-10-11当前状态（A–F保持；表2实际批次见上方）：',1)
            start=text.index('下一工作仍为2E：');end=text.index('\n',start)
            text=text[:start]+'下一工作为本批2E人工试听及反馈绑定；已完成冻结16套成声与技术门禁，不自动加剂量、加入条件或进入2F–2H。'+text[end:]
        else:
            text=text.replace('执行更新2026-10-10。','执行更新2026-10-11。',1)
            text=text.replace('2E研究接口及历史native/静态接入核查完成，真实渲染/试听及2F–2H尚未执行。',
                '2E有限实际渲染及技术交付完成，人工试听pending；2F–2H未执行。',1)
            text=text.replace('下一步有限执行前置项及明确授权的新批次，不自动切换至新合成或整曲修改。',
                '用户已授权并完成冻结新批次，下一步人工试听/绑定反馈，不自动追加成声或整曲修改。',1)
            text=text.replace('实际输入/采样/模型执行与试听未完成，2F–2H未执行，新因果试听须进入明确的音频执行范围。',
                '冻结实际输入/采样/模型执行及技术交付完成，人工试听pending，2F–2H未执行；不自动追加批次。',1)
        first_section=text.index('\n## ')
        status='\n\n'+STATUS+'见[实际执行报告](docs/knowledge/acoustic-manifestations-20261009/table2-stage-2e-execution.md)、[JSON](docs/knowledge/acoustic-manifestations-20261009/table2-stage-2e-execution.json)与[审计](docs/knowledge/acoustic-manifestations-20261009/table2-stage-2e-execution-audit.json)。\n\n以下阶段明细保留各自完成时范围；当前步骤以上述2026-10-11实际批次为准。\n'
        text=text[:first_section]+status+text[first_section:]
        path.write_text(text,encoding='utf-8')
    path=ROOT/'README.md';text=path.read_text(encoding='utf-8')
    if MARK not in text:
        a=text.index('当前**表1 A–F');z=text.index('\n\n',a)
        text=text[:a]+('当前**表1 A–F固定范围整合完成；表2完成2A–2D及2E冻结16套实际渲染/技术交付，人工试听pending，确认缺口保留**。'
            +STATUS+'见[实际执行报告](docs/knowledge/acoustic-manifestations-20261009/table2-stage-2e-execution.md)与[审计](docs/knowledge/acoustic-manifestations-20261009/table2-stage-2e-execution-audit.json)。')+text[z:]
        text=text.replace('关联表2已完成2A–2D及2E接口准备，实际执行/试听待核查','关联表2已完成2A–2D及2E实际技术交付，人工试听待评价')
        text=text.replace('2E接口准备完成，实际渲染/试听及2F–2H尚未执行','2E实际渲染/技术交付完成，人工试听pending，2F–2H未执行')
        text=text.replace('当前另见2E准备，尚无新音频','当前另见2E实际执行报告，新对照待听')
        text=text.replace('本轮没有生成新音频、修改Skill或发布歌曲工程。2E只读输入核查已完成，真实对照仍需新原生输入/推理、PCM/DYN/固定增益等技术检查后交付人工试听，全部measurement_validated仍false。',
            '本批按明确授权生成冻结对照且技术检查通过，原歌曲、既有音频及Skill保持。现在接人工试听；未听/无反馈保持pending，全部measurement_validated仍false。')
        text=text.replace('| [表2专项计划]', '| [表2实际执行](docs/knowledge/acoustic-manifestations-20261009/table2-stage-2e-execution.md) | 8次variance/16套实验波形及72份固定增益分开试听文件；技术通过，听觉pending |\n| [表2专项计划]',1)
        path.write_text(text,encoding='utf-8')
    path=ROOT/'AGENTS.md';text=path.read_text(encoding='utf-8')
    if MARK not in text:
        text=text.replace('## Codex与当前计划\n','## Codex与当前计划\n\n- '+STATUS+'报告：[2E实际执行](docs/knowledge/acoustic-manifestations-20261009/table2-stage-2e-execution.md)。以下长段保留各阶段历史范围；最新边界以本条及根目录plan为准。\n',1)
        text=text.replace('2E研究接口准备完成但实际渲染/试听未执行；仍由根目录plan总入口维护，不自动进入新因果试听。',
            '2E冻结实际渲染/技术交付已完成、待人工试听；仍由根目录plan总入口维护，不自动扩大新因果实验。')
        path.write_text(text,encoding='utf-8')
    for path in [HERE/'README.md',OUT/'README.md']:
        text=path.read_text(encoding='utf-8')
        if MARK in text:continue
        links='../../docs/knowledge/acoustic-manifestations-20261009/' if path.parent==HERE else ''
        insert='\n\n'+STATUS+f'见[实际执行报告]({links}table2-stage-2e-execution.md)、[JSON]({links}table2-stage-2e-execution.json)与[审计]({links}table2-stage-2e-execution-audit.json)。\n\n以下准备/静态/早期阶段叙述保留当时状态，不覆盖新批次。\n'
        pos=text.index('\n');text=text[:pos]+insert+text[pos:]
        if path.parent==HERE:
            text=text.replace('当前入口为`build_stage_2e_native.py`与`verify_stage_2e_native.py`',
                '此前入口为`build_stage_2e_native.py`与`verify_stage_2e_native.py`，现已guard；当前报告构建/审计为`build_stage_2e_execution.py`与`verify_stage_2e_execution.py`')
            text=text.replace('现行使用2D构建/验证','现行使用2E实际批次构建/验证')
        path.write_text(text,encoding='utf-8')
    print('Root plan + associated plan + README/AGENTS/knowledge/research entries updated')

if __name__=='__main__':main()
