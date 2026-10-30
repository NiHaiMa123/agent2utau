"""阶段5：原生导出（pitch/phonemes/provenance）+ inventory + knowledge context。"""
import sys, json, io
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')
from agent2utau.openutau.bridge import run_bridge
from agent2utau.openutau.ustx import load_ustx, sha256
from agent2utau.resources.config import load_config

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
cfg = load_config()
SCORE = NEW/'score'/'v3_score.ustx'
D = NEW/'design'; NAT = NEW/'native'
NAT.mkdir(exist_ok=True)

for cmd, out in [('export-pitch', NAT/'baseline_pitch.json'),
                 ('export-phonemes', NAT/'baseline_phones.json')]:
    r = run_bridge(cfg, [cmd, '--project', str(SCORE.resolve()), '--out', str(out.resolve())])
    print(f'{cmd}: ok={r.get("ok")} frames={r.get("frame_count")} phones={r.get("phone_count")}')
    if not r.get('ok'):
        print(json.dumps(r, ensure_ascii=False)[:1200]); raise SystemExit(1)

ou = Path(cfg['openutau_dir'])
doc = load_ustx(SCORE)
singer = doc['tracks'][0]['singer']
prov = dict(schema_version=1,
            project_sha256=sha256(SCORE),
            pitch_sha256=sha256(NAT/'baseline_pitch.json'),
            phonemes_sha256=sha256(NAT/'baseline_phones.json'),
            environment=dict(core_sha256=sha256(ou/'OpenUtau.Core.dll'),
                             bridge_sha256=sha256(ou/'a2u-bridge.exe'),
                             singer_config_sha256=sha256(ou/'Singers'/singer/'dsconfig.yaml'),
                             singer_id=singer))
(NAT/'baseline_provenance.json').write_text(json.dumps(prov, ensure_ascii=False, indent=2), encoding='utf-8')
print('provenance written; singer =', singer)

pitch = json.load(io.open(NAT/'baseline_pitch.json', encoding='utf-8'))
ph = json.load(io.open(NAT/'baseline_phones.json', encoding='utf-8'))
print(f"pitch phrases {len(pitch['phrases'])}, phone parts {len(ph['parts'])}")
print(f"total native phones: {sum(len(p['phones']) for part in ph['parts'] for p in part['phrases'])}")
print(f"total notes: {sum(len(part['notes']) for part in ph['parts'])}")
