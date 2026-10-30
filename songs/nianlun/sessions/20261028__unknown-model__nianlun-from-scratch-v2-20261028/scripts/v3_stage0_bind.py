"""阶段0：建立新 run，绑定复用观测。

复用（用户授权）：分离出的伴奏/人声、GAME、双F0、ASR。
其余全部重新生成。
"""
import sys, json, io, shutil, hashlib
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path(r'E:\project\agent2utau')
V2 = ROOT / 'runs/production/nianlun-from-scratch-v2-20261028'
NEW = ROOT / 'runs/production/nianlun-v3-20261029'
SRC = Path(r'E:\data\music\年轮 - 张碧晨.flac')


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for c in iter(lambda: f.read(1 << 20), b''):
            h.update(c)
    return h.hexdigest()


if NEW.exists():
    raise SystemExit(f'{NEW} already exists - refusing to overwrite')

obs = NEW / 'inputs'
obs.mkdir(parents=True)
for sub in ('stems',):
    (obs / sub).mkdir()

# copy the reusable observations verbatim
copy_list = [
    ('observation/stems/source_(vocals)_vocals_mel_band_roformer.wav', 'stems/vocals.wav'),
    ('observation/stems/source_(other)_vocals_mel_band_roformer.wav', 'stems/instrumental.wav'),
    ('observation/game.json', 'game.json'),
    ('observation/fcpe.npz', 'fcpe.npz'),
    ('observation/rmvpe.npz', 'rmvpe.npz'),
    ('observation/fcpe_provenance.json', 'fcpe_provenance.json'),
    ('observation/rmvpe_provenance.json', 'rmvpe_provenance.json'),
    ('observation/asr.json', 'asr.json'),
    ('observation/manifest.json', 'v2_observation_manifest.json'),
]
manifest = {}
for rel, dst in copy_list:
    s = V2 / rel
    d = obs / dst
    shutil.copy2(s, d)
    manifest[dst] = sha(d)
    print(f'  copied {dst}  sha={manifest[dst][:16]}...')

# verify against v2 manifest that bytes are unchanged
v2m = json.load(io.open(V2 / 'observation/manifest.json', encoding='utf-8'))
checks = {
    'stems/vocals.wav': 'stems\\source_(vocals)_vocals_mel_band_roformer.wav',
    'stems/instrumental.wav': 'stems\\source_(other)_vocals_mel_band_roformer.wav',
    'game.json': 'game.json', 'fcpe.npz': 'fcpe.npz', 'rmvpe.npz': 'rmvpe.npz',
    'asr.json': 'asr.json',
}
ok = True
for dst, v2key in checks.items():
    want = v2m['files'][v2key]
    got = manifest[dst]
    same = want == got
    ok &= same
    print(f'  verify {dst}: {"OK" if same else "MISMATCH"}')

binding = dict(
    schema_version=1,
    run_id='nianlun-v3-20261029',
    source_flac=dict(path=str(SRC), sha256=sha(SRC)),
    reused_observations=manifest,
    reuse_statement='用户授权复用：分离伴奏/人声、GAME、双F0、ASR。其余（HFA、歌词/音素身份、谱面、意图、音高函数、发声层、编译、渲染、混音、图审）全部重新生成。',
    reused_verified_byte_identical=ok,
    prior_versions=[
        dict(run='nianlun-from-scratch-20261028', verdict='rejected_by_user',
             reason='用户：差到无法给出具体建议'),
        dict(run='nianlun-from-scratch-v2-20261028', verdict='rejected_by_user',
             reason='用户：差到无法给出具体建议'),
    ],
)
(NEW / 'manifest.json').write_text(json.dumps(binding, ensure_ascii=False, indent=2), encoding='utf-8')
print(f'\nrun created: {NEW}')
print('all reused bytes verified:', ok)
