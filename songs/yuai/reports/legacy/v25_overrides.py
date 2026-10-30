"""查 phoneme_overrides 的正确格式与语义（用参考工程实例）。

白烁工程可能有 phoneme_overrides 的用法；也有可能是空。
同时查 OpenUtau 源码里的定义。
"""
import sys, json, io
from collections import Counter
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')
from agent2utau.openutau.ustx import load_ustx

REF = Path(r'E:\project\agent2utau\research\baishuo\projects\雨爱-有参by白烁.ustx')
for label, p in [('白烁 雨爱', REF),
                 ('雨爱 v17 发布工程', Path(r'E:\project\agent2utau\projects\latest\yuai_skill_v17.ustx'))]:
    if not p.is_file(): continue
    d = load_ustx(p)
    n_ov = 0; samples=[]
    for part in d['voice_parts']:
        for n in part['notes']:
            ov = n.get('phoneme_overrides') or []
            if ov:
                n_ov += len(ov)
                if len(samples) < 5: samples.append((n.get('lyric'), ov))
    print(f'=== {label} ===  phoneme_overrides 条目 {n_ov}')
    for s in samples:
        print(f'  {s[0]}: {s[1]}')

# 查 OpenUtau 源码里的字段定义
print('\n=== OpenUtau 源码中的 phoneme_overrides / phoneme_expressions ===')
import subprocess
ou = Path(r'E:\software\OpenUtau-win-x64_dpV2\OpenUtau-win-x64')
# 可能是反编译/Core.dll，但我们有 bridge 源码参考
for f in ['bridge/OuBridge/Program.cs']:
    p = Path(f)
    if p.is_file():
        txt = p.read_text(encoding='utf-8', errors='replace')
        for key in ('phoneme_overrides','PhonemeOverrides','phoneme_expressions'):
            if key in txt:
                idx = txt.find(key)
                print(f'  {f} 含 {key}: ...{txt[max(0,idx-120):idx+160]}...')
