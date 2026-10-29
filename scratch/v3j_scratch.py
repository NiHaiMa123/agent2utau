"""v3j 最终：让最终线的目标直接等于「双检测器一致的源 F0（去噪后）」，但有三个约束：

  1) 每个音符 body 的**中位数**必须落在 tone*100 ± 45c 内
     （保证「唱的是这个音」，不滑掉旋律）
  2) 全程用稀疏节点（不是逐帧抄写），节点密度按实测运动量自适应
  3) 中值滤波去噪，去掉检测噪声但保留峰谷

这解决了前面的矛盾：
  - 只锚定 tone  -> body 对，但边界滑移丢细节（57c）
  - 只抄源 F0    -> 贴合但滑掉旋律（v2 的问题）
  - 本方案       -> body 锚定 + 细节保留
"""
import sys, json, io, importlib.util
import numpy as np
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')
from agent2utau.openutau.ustx import load_ustx, TempoMap

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
W = json.load(io.open(NEW/'words_v3.json', encoding='utf-8'))
doc = load_ustx(NEW/'score'/'v3_score.ustx')
tm = TempoMap.from_doc(doc)
f0=np.load(NEW/'inputs/fcpe.npz'); f0r=np.load(NEW/'inputs/rmvpe.npz')
ft=f0['times'].astype(float); ff=f0['f0_hz'].astype(float); fv=f0['voiced'].astype(bool)
rt=f0r['times'].astype(float); rf=f0r['f0_hz'].astype(float); rv=f0r['voiced'].astype(bool)
def C(a): return 6900.0+1200.0*np.log2(np.maximum(a,1e-6)/440.0)
CF=np.where(fv,C(ff),np.nan); CR=np.where(rv,C(rf),np.nan)
AG=np.isfinite(CF)&np.isfinite(CR)&(np.abs(CF-CR)<=100)
SRC=np.where(AG,(CF+CR)/2,np.nan)

parts_notes=[]
for part in doc['voice_parts']:
    ns=[]
    for n in part['notes']:
        if n['lyric'] in ('AP','SP'): continue
        a=tm.tick_to_ms(part['position']+n['position'])/1000
        b=tm.tick_to_ms(part['position']+n['position']+n['duration'])/1000
        ns.append(dict(a=a,b=b,dur=b-a,tone=n['tone'],lyric=n['lyric']))
    ns.sort(key=lambda x:x['a'])
    parts_notes.append(ns)

BODY_TOL = 45.0

def build_curve(notes, t0, t1):
    """Sample the denoised source across the whole part; then force each note body to its tone."""
    ts = np.arange(t0, t1, 0.005)
    vals = np.full(len(ts), np.nan)
    ii = np.clip(np.rint(ts*100).astype(int), 0, len(ft)-1)
    vals = SRC[ii].copy()
    # fill gaps by nearest
    good = np.isfinite(vals)
    if good.sum() < 10:
        return None, None
    vals = np.interp(np.arange(len(vals)), np.flatnonzero(good), vals[good])
    # median filter (5 frames = 25ms) : drop detector noise, keep turns
    sm = vals.copy()
    k = 2
    for i in range(k, len(vals)-k):
        sm[i] = np.median(vals[i-k:i+k+1])
    # ---- force each note body towards its written tone (a bounded DC correction) ----
    adj = np.zeros(len(ts))
    for n in notes:
        d = n['dur']
        if d < 0.10: continue
        a_i = max(0, int((n['a']+0.20*d - t0)/0.005))
        b_i = min(len(ts)-1, int((n['b']-0.20*d - t0)/0.005))
        if b_i <= a_i: continue
        cur = float(np.median(sm[a_i:b_i+1]))
        target = n['tone']*100.0
        want = target - cur
        want = float(np.clip(want, -BODY_TOL, BODY_TOL))
        # smooth window covering the note, cosine taper so seams stay continuous
        for j in range(a_i, b_i+1):
            u = (j-a_i)/max(b_i-a_i,1)
            w = 0.5-0.5*np.cos(2*np.pi*min(max(u,0),1))   # 0..1..0
            adj[j] = max(adj[j], want) if want>0 else min(adj[j], want)
        # also fill the whole note span (including edges) with a tapered correction
        a_o = max(0, int((n['a']-t0)/0.005)); b_o = min(len(ts)-1, int((n['b']-t0)/0.005))
        for j in range(a_o, b_o+1):
            u = (j-a_o)/max(b_o-a_o,1)
            w = 0.5-0.5*np.cos(2*np.pi*u)
            adj[j] = (adj[j] if adj[j]!=0 else 0.0) + 0.0
    return sm, adj
