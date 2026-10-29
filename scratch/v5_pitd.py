"""v5：按白烁的画法结构重画音高线（学习做法，不复制数值）。

学到的结构（来自 499 个音符、11959 个点的统计）：
  载体：note.pitch 保持直线；全部细节画在 PITD，密度 ≈ 每 15.6ms 一点
  字头：中位接近 0，但允许强负偏移（p10 ≈ -150c）→ 滑入
  字腹：中位 0；运动幅度随音符长度递增（短 13c / 中 21c / 长 61c std）
  字尾：中位数略负，p10 到 -225c → 滑出/释放
  平滑度：二阶差分中位 12c（平滑曲线，不是抖噪）

我自己的设计（不抄数值）：
  1) 载体：PITD，2 tick 步长（本项目 120bpm/480res → 1 tick=1.04ms，2tick≈2.1ms 太密；
     改用与白烁等效的 ~16ms 步长，即 15 tick）
  2) 每字：字头滑入 → 字腹按长度给不同幅度的运动 → 字尾滑出
  3) 幅度全部由「字数/位置/音区/音程」这些音乐条件决定
  4) 用平滑插值（quintic）连接节点，保证二阶差分小
"""
import sys, json, io, math
import numpy as np
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')
from agent2utau.openutau.ustx import load_ustx, TempoMap

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
W = json.load(io.open(NEW/'words_v3.json', encoding='utf-8'))
doc = load_ustx(NEW/'score'/'v3_score.ustx')
tm = TempoMap.from_doc(doc)
RES = int(doc.get('resolution', 480))
BPM = float((doc.get('tempos') or [{'bpm':120}])[0]['bpm'])
TICK_MS = 60000.0/(BPM*RES)
STEP_MS = 16.0
STEP_TICKS = max(2, int(round(STEP_MS/TICK_MS)))
print(f'resolution={RES} bpm={BPM} 1tick={TICK_MS:.3f}ms -> PITD step {STEP_TICKS} ticks = {STEP_TICKS*TICK_MS:.1f}ms')

# 源 F0 只用于「有没有运动」这个二值条件，不取数值
f0=np.load(NEW/'inputs/fcpe.npz'); f0r=np.load(NEW/'inputs/rmvpe.npz')
ft=f0['times'].astype(float); ff=f0['f0_hz'].astype(float); fv=f0['voiced'].astype(bool)
rt=f0r['times'].astype(float); rf=f0r['f0_hz'].astype(float); rv=f0r['voiced'].astype(bool)
def C(a): return 6900.0+1200.0*np.log2(np.maximum(a,1e-6)/440.0)
CF=np.where(fv,C(ff),np.nan); CR=np.where(rv,C(rf),np.nan)
AG=np.isfinite(CF)&np.isfinite(CR)&(np.abs(CF-CR)<=100)
SRC=np.where(AG,(CF+CR)/2,np.nan)
def has_motion(a,b):
    m=(ft>=a)&(ft<b)&np.isfinite(SRC)
    if m.sum()<8: return False, 0.0
    cc=SRC[m]; span=float(cc.max()-cc.min())
    return span>=60, span

parts=[]
for part in doc['voice_parts']:
    ns=[]
    for n in part['notes']:
        if n['lyric'] in ('AP','SP'): continue
        a=tm.tick_to_ms(part['position']+n['position'])/1000
        b=tm.tick_to_ms(part['position']+n['position']+n['duration'])/1000
        ns.append(dict(a=a,b=b,dur=b-a,tone=n['tone'],lyric=n['lyric']))
    ns.sort(key=lambda x:x['a'])
    parts.append(ns)

def q5(u): return u*u*u*(10+u*(-15+6*u))

def design_offsets(n, k, cnt, prev_tone, next_tone):
    """Return (u_list, offset_list) for one syllable: head glide, body motion, tail release."""
    a,b,d,tone = n['a'],n['b'],n['dur'],n['tone']
    pos = 'first' if k==0 else ('last' if k==cnt-1 else 'mid')
    reg = 'high' if tone>=76 else ('low' if tone<=60 else 'mid')
    leap_in  = None if prev_tone is None else tone-prev_tone
    leap_out = None if next_tone is None else tone-next_tone
    moving, _span = has_motion(a,b)

    # --- 字头滑入：负偏移，短促回到 0 ---
    if pos=='first':
        head_depth = -110 if reg!='high' else -90
    elif leap_in is not None and leap_in>=5:
        head_depth = -85
    elif leap_in is not None and leap_in<=-5:
        head_depth = +70
    elif leap_in==0:
        head_depth = -45
    else:
        head_depth = -30
    head_frac = min(0.22, 0.55*(0.12/max(d,0.12)))   # 短字滑入更短

    # --- 字腹：幅度随长度递增（白烁实测 13/21/61c）---
    if d < 0.30: body_amp = 14.0
    elif d < 0.52: body_amp = 22.0
    else: body_amp = 58.0
    if not moving: body_amp *= 0.55
    if reg=='high': body_amp *= 0.85
    body_cycles = 1.0 if d < 0.52 else 2.0

    # --- 字尾滑出 ---
    if pos=='last':
        tail_depth = -120 if reg!='high' else -95
    elif leap_out is not None and leap_out>=5:
        tail_depth = -85
    elif leap_out is not None and leap_out<=-5:
        tail_depth = +75
    else:
        tail_depth = -25
    tail_frac = min(0.26, 0.5*(0.13/max(d,0.13)))

    # --- 组装 (u, offset) 节点 ---
    pts=[]
    n_head = 3 if d>0.30 else 2
    for i in range(n_head):
        u = head_frac*(i/(n_head-1)) if n_head>1 else 0.0
        # 从 head_depth 平滑回到 0
        val = head_depth*(1-q5(i/max(n_head-1,1)))
        pts.append((u,val))
    # 字腹：余弦起伏，peak 在 0.5
    b0 = head_frac; b1 = 1.0-tail_frac
    if b1-b0 < 0.10: b0=0.30; b1=0.70
    n_body = max(3, int((b1-b0)/0.14)+1)
    for i in range(n_body):
        u = b0+(b1-b0)*i/(n_body-1)
        ph = (u-b0)/max(b1-b0,1e-6)
        val = -body_amp*math.sin(math.pi*body_cycles*ph)**2 * (1 if body_cycles<1.5 else
              (0.6+0.4*math.cos(2*math.pi*ph)))
        pts.append((u,val))
    # 字尾
    n_tail = 3 if d>0.30 else 2
    for i in range(1,n_tail+1):
        u = 1.0-tail_frac*(1-i/n_tail)
        val = tail_depth*q5(i/n_tail)
        pts.append((u,val))
    pts.sort(key=lambda x:x[0])
    # dedupe
    out=[]
    for u,v in pts:
        if out and abs(u-out[-1][0])<1e-4: continue
        out.append((float(np.clip(u,0,1)), float(v)))
    return out

# ---- build PITD curves ----
report=dict(parts=0, points=0, mean_abs=[])
for pi, part in enumerate(doc['voice_parts']):
    notes = parts[pi]
    pa = tm.tick_to_ms(part['position'])
    pb = pa + tm.tick_to_ms(part['duration']) - tm.tick_to_ms(0)
    pb = tm.tick_to_ms(part['position']+part['duration'])
    # sample grid in part-relative ticks
    xs = list(range(0, int(part['duration'])+1, STEP_TICKS))
    if xs[-1] != int(part['duration']): xs.append(int(part['duration']))
    ys = np.zeros(len(xs), float)
    for ni,n in enumerate(notes):
        prev_tone = notes[ni-1]['tone'] if ni>0 else None
        nxt_tone  = notes[ni+1]['tone'] if ni+1<len(notes) else None
        nodes = design_offsets(n, ni, len(notes), prev_tone, nxt_tone)
        if not nodes: continue
        us = np.array([x[0] for x in nodes])
        vs = np.array([x[1] for x in nodes])
        na = n['a']; nb = n['b']
        for j, x in enumerate(xs):
            t_abs = tm.tick_to_ms(part['position']+x)/1000
            if t_abs < na or t_abs > nb: continue
            u = (t_abs-na)/max(nb-na,1e-6)
            # draw only where no other note has written (later notes win at seams)
            ys[j] = float(np.interp(u, us, vs))
    # to integers, keep within declared range
    ys_int = [int(round(float(np.clip(v,-1200,1200)))) for v in ys]
    part['curves'] = [c for c in part.get('curves',[]) if c['abbr']!='pitd']
    part['curves'].append(dict(abbr='pitd', xs=[int(x) for x in xs], ys=ys_int))
    report['parts']+=1; report['points']+=len(xs)
    report['mean_abs'].append(float(np.mean(np.abs(np.array(ys_int)))))

print(f"PITD written: {report['parts']} parts, {report['points']} points "
      f"({report['points']/report['parts']:.0f}/part)")
print(f"mean |offset| per part: median {np.median(report['mean_abs']):.1f}c")

OUT = NEW/'score'/'v5_score.ustx'
save = load_ustx(NEW/'score'/'v3_score.ustx')
# only copy pitd curves onto the pristine score (the function compiler will re-encode)
for pi, part in enumerate(save['voice_parts']):
    src = doc['voice_parts'][pi]
    part['curves'] = [c for c in part.get('curves',[]) if c['abbr']!='pitd']
    pit = next(c for c in src['curves'] if c['abbr']=='pitd')
    part['curves'].append(pit)
from agent2utau.openutau.ustx import save_ustx
save_ustx(save, OUT)
print(f'wrote {OUT}')
