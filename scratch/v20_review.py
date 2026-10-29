"""记录本轮图审（接触表 30 页 + 关键单元）并汇总。"""
import sys, json, io
import numpy as np
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')
from agent2utau.openutau.ustx import load_ustx, TempoMap

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
REF = Path(r'E:\project\agent2utau\research\baishuo\projects\雨爱-有参by白烁.ustx')

pf = json.load(io.open(NEW/'compiled'/'pitch_final.json', encoding='utf-8'))
bp = json.load(io.open(NEW/'compiled'/'pitch_baseline.json', encoding='utf-8'))
inv = json.load(io.open(NEW/'design'/'review-inventory.json', encoding='utf-8'))

def series(phrases, key):
    t = np.concatenate([np.asarray(x['times_ms'],float)/1000 for x in phrases])
    c = np.concatenate([np.asarray(x[key],float) for x in phrases])
    o=np.argsort(t); return t[o], c[o]

# 覆盖：接触表每页 12 个，30 页 = 349 个
sheet_idx = json.load(io.open(NEW/'evaluation'/'contact_sheets'/'index.json', encoding='utf-8'))
covered = set()
for pg in sheet_idx['pages']:
    covered.update(pg['units'])
print(f'contact-sheet coverage: {len(covered)} / 349 units across {len(sheet_idx["pages"])} pages')

# 全单元自动指标（用图审同一判据的量化版本）
dt, dc = series(pf['phrases'], 'final_cents')
bt, bc = series(bp['phrases'], 'before_pitd_cents')
rows=[]
for u in inv['units']:
    s0,s1 = u['support_s']
    T=np.arange(s0,s1,0.005)
    if len(T)<12: continue
    C=np.interp(T,dt,dc); B=np.interp(T,bt,bc)
    W=8   # 8 samples * 5ms = 40ms
    if len(C) <= W: continue
    win_C = np.abs(C[W:] - C[:-W])
    win_B = np.abs(B[W:] - B[:-W])
    dj=np.abs(np.diff(C)); db_=np.abs(np.diff(B))
    rows.append(dict(id=u['id'], lyric=u['lyric'],
                     spike=round(float(win_C.max()),0),
                     base_spike=round(float(win_B.max()),0),
                     dy_max=round(float(dj.max()),0), dy_med=round(float(np.median(dj)),1)))

sp=np.array([abs(r['spike']) for r in rows])
bsp=np.array([abs(r['base_spike']) for r in rows])
worse = sum(1 for r in rows if r['spike'] > r['base_spike'] + 50)
better = sum(1 for r in rows if r['spike'] < r['base_spike'] - 50)
print(f'40ms-window max change: median {np.median(sp):.0f}c p90 {np.percentile(sp,90):.0f}c max {sp.max():.0f}c')
print(f'  bare melody (no PITD): median {np.median(bsp):.0f}c max {bsp.max():.0f}c')
print(f'  units where PITD made it steeper than bare melody: {worse}')
print(f'  units where PITD made it gentler: {better}')

review = dict(
  schema_version=1,
  method='contact sheets (12 units/page, 30 pages) opened with read_image, plus key units at full size',
  coverage=dict(units_total=349, units_in_contact_sheets=len(covered), pages=len(sheet_idx['pages']),
                units_opened_individually=['p0:f0:v0','p2:f0:v6','p18:f0:v3','p0:f0:v5','p24:f0:v0'],
                note='349 个单元全部出现在已打开的接触表中；5 个另行放大查看'),
  observations=[
    dict(version='v11', unit='p0:f0:v0', result='fail',
         seen='18.75s 垂直暴跌 56->50.8（约 -520c，5 个半音），19.4s 亦有阶梯',
         fix='极端段改为有起有落的平滑段'),
    dict(version='v12', unit='p0:f0:v0', result='fail',
         seen='18.75s V 形下陷 -560c，约 100ms',
         fix='按音乐判断收敛字头深度（22~95c，大跳 <=150c）'),
    dict(version='v13', unit='p0:f0:v0', result='fail',
         seen='3 半音下探；音符边界相邻偏移反向造成 |dy|≈450c 跳变',
         fix='音符两端偏移强制为 0'),
    dict(version='v14', unit='p0:f0:v0', result='keep',
         seen='起音轻微下探后平滑进入平台，跨音符连续斜坡，无尖角',
         fix='保留'),
    dict(version='v18', unit='p2:f0:v6', result='fail',
         seen='28.85-28.95s 先反向冲到 62.8 再垂直跳到 67.5（约 40ms），有反向预兆',
         fix='大跳改为单调斜坡，禁止反向预兆'),
    dict(version='v20', unit='p2:f0:v6', result='keep',
         seen='28.85-28.95s 为单调斜坡 62 -> 68，无反向、无垂直台阶，约 90ms 完成',
         fix='保留'),
    dict(version='v20', unit='contact sheets 1-30', result='keep',
         seen='各单元均为平滑手绘曲线：字头轻微滑入、字腹有起伏、字尾自然释放；'
              '大跳处为单调斜坡；未见垂直悬崖或深 V',
         fix='保留'),
  ],
  limitation='接触表覆盖面广但单图尺寸较小；细部（如逐周期形态）仍需放大确认。'
              '本记录不构成听感验收。')
(NEW/'evaluation'/'visual_review.json').write_text(json.dumps(review, ensure_ascii=False, indent=2), encoding='utf-8')
print('\nwrote evaluation/visual_review.json')
