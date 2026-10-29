"""阶段2（v3-CLK3，最终）：HFA 字身份 + 局部字长修复 + cent 精度音高。

诊断结论（前两版失败的真正原因）：
  1. 【致命】v2 用「源残差×0.8」当字腹设计、13989 个中心节点 = 逐帧抄源 F0。
     Skill 明确禁止；且抄进了检测噪声与微抖动，丢失真正的演唱动作。
  2. 【重要】v2 音符音高量化到整数半音 (int(round(core_cents/100)))，丢失半音内的精细音高。
  3. 【重要】HFA 在密集段崩成 20ms 字长 → 碎字/吞字。
  4. 【重要】v2 发声层只有 7 种段落级取值，逐字无差异。

本阶段处理 2、3；1、4 在后续阶段。
"""
import sys, json, io
import numpy as np, soundfile as sf
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
h = json.load(io.open(NEW/'hfa_summary.json', encoding='utf-8'))
g = json.load(io.open(NEW/'inputs/game.json', encoding='utf-8'))
notes = g['notes']

MIN_SYL = 0.11        # 每字最小音乐时值（Skill: 短字需可承载元音）
MAX_GROW = 0.0        # 只从邻字借，不超出句界

def fix_durations(words, t0, t1):
    """Local repair: redistribute time so every syllable >= MIN_SYL, staying inside [t0,t1]."""
    ws = [dict(w) for w in words]
    n = len(ws)
    # 1. hard-bind phrase window
    ws[0]['start'] = t0; ws[-1]['end'] = t1
    for i in range(1, n):
        if ws[i]['start'] < ws[i-1]['end']:
            mid = (ws[i]['start'] + ws[i-1]['end'])/2
            ws[i-1]['end'] = mid; ws[i]['start'] = mid
    # 2. if even division can't give MIN_SYL to all, lower the floor for this phrase
    floor = min(MIN_SYL, (t1-t0)/max(n, 1) * 0.85)
    # 3. iterative repair
    for _ in range(80):
        changed = False
        for i, w in enumerate(ws):
            d = w['end'] - w['start']
            if d >= floor - 1e-9: continue
            need = floor - d
            for j in ([i-1] if i > 0 else []) + ([i+1] if i < n-1 else []):
                if need <= 1e-9: break
                slack = (ws[j]['end'] - ws[j]['start']) - floor
                if slack <= 1e-6: continue
                take = min(need, slack)
                if j < i:
                    w['start'] -= take; ws[j]['end'] -= take
                else:
                    w['end'] += take; ws[j]['start'] += take
                need -= take; changed = True
        if not changed: break
    # 4. re-enforce bounds & monotonicity AFTER repair (do not override phrase ends)
    for i in range(1, n):
        if ws[i]['start'] < ws[i-1]['end'] - 1e-9:
            mid = (ws[i]['start'] + ws[i-1]['end'])/2
            ws[i-1]['end'] = mid; ws[i]['start'] = mid
    ws[0]['start'] = t0; ws[-1]['end'] = t1
    # clamp to window
    for w in ws:
        w['start'] = max(w['start'], t0); w['end'] = min(w['end'], t1)
    for w in ws:
        w['start'] = round(w['start'], 4); w['end'] = round(w['end'], 4)
        w['dur'] = round(w['end']-w['start'], 4)
    return ws

# ---- 源 F0（双检测器一致，cent 精度） ----
f0 = np.load(NEW/'inputs/fcpe.npz'); f0r = np.load(NEW/'inputs/rmvpe.npz')
ft, ff, fv = f0['times'].astype(float), f0['f0_hz'].astype(float), f0['voiced'].astype(bool)
rt, rf, rv = f0r['times'].astype(float), f0r['f0_hz'].astype(float), f0r['voiced'].astype(bool)
def cents(hz): return 6900.0 + 1200.0*np.log2(np.maximum(hz, 1e-6)/440.0)
# Map rmvpe onto fcpe's grid by index (both 10ms, same length) — NOT interp of NaN.
assert len(rt) == len(ft) and np.allclose(rt, ft), (len(rt), len(ft))
c_f = np.where(fv, cents(ff), np.nan)
c_r = np.where(rv, cents(rf), np.nan)
agree = np.isfinite(c_f) & np.isfinite(c_r) & (np.abs(c_f-c_r) <= 100)
c_src = np.where(agree, (c_f+c_r)/2, np.nan)   # 双检测器均值，cent 精度
print(f'source comparable frames: {agree.mean():.1%}')

def word_pitch(a, b):
    """Core-segment median pitch at cent resolution (NOT quantized to semitone)."""
    win = (ft >= a) & (ft < b)
    m = win & np.isfinite(c_src)
    n_win = int(win.sum())
    if m.sum() < 3 or n_win == 0:
        return None, 0.0
    cover = float(m.sum()) / float(n_win)     # fraction of the WORD's frames that are voiced
    v = c_src[m]
    # longest continuous run
    tt = ft[m]
    runs, s = [], 0
    for j in range(1, len(tt)+1):
        if j == len(tt) or tt[j]-tt[j-1] > 0.06:
            if j-s >= 2: runs.append((s, j))
            s = j
    if not runs:
        return float(np.median(v)), cover
    a0, b0 = max(runs, key=lambda r: r[1]-r[0])
    return float(np.median(v[a0:b0])), cover

out, stats = [], dict(repaired=0, total=0, still_short=[], weak=[])
for p in h['phrases']:
    t0, t1 = p['time']
    ws = fix_durations(p['lexical'], t0, t1)
    words = []
    for k, (w, orig) in enumerate(zip(ws, p['lexical'])):
        pitch_c, cover = word_pitch(w['start'], w['end'])
        stats['total'] += 1
        if orig['dur'] < MIN_SYL: stats['repaired'] += 1
        if w['dur'] < MIN_SYL - 1e-6: stats['still_short'].append((p['pid'], w['hanzi'], w['dur']))
        if pitch_c is None or cover < 0.25: stats['weak'].append((p['pid'], w['hanzi'], round(cover,2)))
        words.append(dict(idx=k, hanzi=w['hanzi'], hfa_marks=orig.get('hfa_marks') or [q['mark'] for q in orig['phones']],
                          start=w['start'], end=w['end'], dur=w['dur'],
                          hfa_dur=orig['dur'], pitch_cents=pitch_c, voiced_cover=round(cover,3)))
    out.append(dict(pid=p['pid'], label=p['label'], hanzi=p['hanzi'], pinyin=p['pinyin'],
                    time=[t0, t1], words=words))

print(f"words total {stats['total']}, repaired (<{MIN_SYL}s at HFA): {stats['repaired']}")
print(f"still too short: {len(stats['still_short'])} {stats['still_short'][:8]}")
print(f"weak pitch coverage (<0.25): {len(stats['weak'])} {stats['weak'][:8]}")
d = np.array([w['dur'] for p in out for w in p['words']])
print(f"word dur: min {d.min():.3f} p5 {np.percentile(d,5):.3f} median {np.median(d):.3f} max {d.max():.3f}")

(NEW/'score_clock.json').write_text(json.dumps(dict(
    schema_version=1, min_syl_s=MIN_SYL,
    method='HFA syllable identity + local duration repair; pitch at cent resolution (dual-detector mean)',
    stats=dict(repaired=stats['repaired'], total=stats['total']),
    phrases=out), ensure_ascii=False, indent=1), encoding='utf-8')
print('wrote score_clock.json')
for p in out[:3]:
    print(f"\n{p['pid']} {p['hanzi']}")
    for w in p['words']:
        print(f"   {w['hanzi']} {w['start']:8.3f}-{w['end']:8.3f} ({w['dur']:.3f}) "
              f"pitch={w['pitch_cents'] and round(w['pitch_cents'],1)} cover={w['voiced_cover']}")
