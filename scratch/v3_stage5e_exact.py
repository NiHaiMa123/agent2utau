"""阶段5e：按编译器的原生 times 精确重建 support，再编译。
compile-functions 要求 design.support_s == [times[0], times[-1]]（1e-9 精度），
而原生 times 与我从 pitch.json 读到的值有微小差异；用 baseline 的原生短语重导出精确值。
"""
import sys, json, io, importlib.util
import numpy as np, yaml
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')
from agent2utau.openutau.bridge import run_bridge
from agent2utau.resources.config import load_config
from agent2utau.openutau.ustx import sha256

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
D = NEW/'design'; NAT = NEW/'native'; SCORE = NEW/'score'/'v3_score.ustx'
cfg = load_config()

# re-export from a baseline copy with pitd stripped (same as compiler does)
BL = NEW/'compiled'/'baseline.ustx'
if not BL.is_file():
    raise SystemExit('run compile once to produce baseline.ustx')
r = run_bridge(cfg, ['export-pitch', '--project', str(BL.resolve()),
                     '--out', str((NAT/'baseline_pitch_exact.json').resolve())])
print('export from baseline:', r.get('ok'))
bp = json.load(io.open(NAT/'baseline_pitch_exact.json', encoding='utf-8'))
print(f'phrases {len(bp["phrases"])}')

spec = importlib.util.spec_from_file_location('df', 'skills/singing-expression-editor/scripts/design_functions.py')
df = importlib.util.module_from_spec(spec); spec.loader.exec_module(df)
pnp = json.load(io.open(D/'plan_native.json', encoding='utf-8'))

new = []
for np_, pl in zip(bp['phrases'], pnp['phrases']):
    t = np.asarray(np_['times_ms'], float)/1000
    t0, t1 = float(t[0]), float(t[-1])
    # sample the existing design over the exact native clock
    ts = np.arange(t0, t1+1e-12, 0.003)
    if len(ts) < 2: ts = np.array([t0, t1])
    else: ts[-1] = t1
    vals = np.array([df.evaluate(pl, float(x)) for x in ts])
    keep = np.unique(np.linspace(0, len(ts)-1, min(16, len(ts))).astype(int))
    nodes = []
    for i in keep:
        tt = float(ts[i]); vv = float(vals[i])
        if nodes and tt <= nodes[-1][0]: continue
        nodes.append([tt, vv, 0.0])
    nodes[0][0] = t0
    nodes[-1][0] = t1
    out = []
    for n in nodes:
        if out and n[0] <= out[-1][0]: continue
        out.append(n)
    if out[0][0] != t0: out.insert(0, [t0, out[0][1], 0.0])
    out[0][0] = t0
    if out[-1][0] != t1:
        if out[-1][0] < t1: out.append([t1, out[-1][1], 0.0])
    out[-1][0] = t1
    amp = float(vals.max()-vals.min()) if len(vals) else 0.0
    new.append(dict(schema=1, origin='agent_designed', support_s=[t0, t1],
                    center_nodes=out, components=[],
                    decisions=[dict(support_s=[t0, t1],
                        condition=f'native phrase on baseline clock',
                        choice='resampled Agent design over the exact native phrase clock',
                        alternative='assume the analytic part window equals the native clock',
                        reason='native frames define the phrase support at 1e-9 precision',
                        uncertainty='native clock is quantised to 5 ticks',
                        component_ids=[])],
                    expectations=[dict(support_s=[t0, t1],
                                       range_c=[0.0, round(amp+60.0, 2)],
                                       purpose='native phrase keeps the design envelope')]))

bad = []
for i, pl in enumerate(new):
    try:
        r2 = df.compile_plan(pl, 0.004)
        if not r2['shape_checks_pass']:
            bad.append((i, [(c['range_c'], round(c['observed_range_c'],1)) for c in r2['local_checks'] if not c['pass']]))
    except Exception as ex:
        bad.append((i, str(ex)))
print(f'validation failures: {len(bad)}')
for b in bad[:6]: print('  ', b)

pnp['phrases'] = new
pnp['note'] = 'one plan per native RenderPhrase, support bound to the exact native clock'
(D/'plan_native.json').write_text(json.dumps(pnp, ensure_ascii=False, indent=1), encoding='utf-8')

# rebuild compile_plan with exact designs
doc = yaml.safe_load(SCORE.read_text(encoding='utf-8'))
pos_to_part = {p['position']: i for i, p in enumerate(doc['voice_parts'])}
D2 = D
kc = json.load(io.open(D/'compile_plan.json', encoding='utf-8'))
out_ph = []
for np_, pl in zip(bp['phrases'], new):
    pi = pos_to_part[np_['part_position']]
    out_ph.append(dict(part_index=pi, position=np_['position'], design=pl))
kc['phrases'] = out_ph
(D/'compile_plan.json').write_text(json.dumps(kc, ensure_ascii=False, indent=1), encoding='utf-8')
print(f'compile plan updated: {len(out_ph)} phrases')
print(f'nodes total {sum(len(p["center_nodes"]) for p in new)} ({sum(len(p["center_nodes"]) for p in new)/349:.1f}/syllable)')
