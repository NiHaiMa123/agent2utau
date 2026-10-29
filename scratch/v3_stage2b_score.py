"""阶段2b：生成 USTX 谱面。

设计（关键差异，针对前两版失败点）：
  1) 旋律骨架 = GAME 音符（实测 vs 源F0 中位 9.2c / p90 41.7c，是可靠旋律来源）
     而不是"每字一个整数音高 + 忽略 melisma"
  2) 字界 = v3 自建时钟（349 字，最短 0.20s，无碎字）
  3) 每字音高 = 该字内 GAME 音符的音高（cent 精度，用 round 到整数 tone，
     余下的 cent 小数交给后续 PITD 设计表达）
  4) AP/SP：只用真实静默（>=0.20s），不固定时长；句内不留未标注空隙
"""
import sys, json, io
import numpy as np, soundfile as sf
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')
from agent2utau.openutau.build import build_project, sec_to_tick, RESOLUTION, BPM_FIXED

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
W = json.load(io.open(NEW/'words_v3.json', encoding='utf-8'))
G = json.load(io.open(NEW/'inputs/game.json', encoding='utf-8'))
notes = G['notes']
v, sr = sf.read(str(NEW/'inputs/stems/vocals.wav'), dtype='float32')
if v.ndim > 1: v = v.mean(1)

# ---- source F0 (cent precision) ----
f0 = np.load(NEW/'inputs/fcpe.npz'); f0r = np.load(NEW/'inputs/rmvpe.npz')
ft = f0['times'].astype(float); ff = f0['f0_hz'].astype(float); fv = f0['voiced'].astype(bool)
rt = f0r['times'].astype(float); rf = f0r['f0_hz'].astype(float); rv = f0r['voiced'].astype(bool)
def cents(a): return 6900.0 + 1200.0*np.log2(np.maximum(a, 1e-6)/440.0)
C_F = np.where(fv, cents(ff), np.nan); C_R = np.where(rv, cents(rf), np.nan)
AGREE = np.isfinite(C_F) & np.isfinite(C_R) & (np.abs(C_F-C_R) <= 100)
C_SRC = np.where(AGREE, (C_F+C_R)/2, np.nan)

def seg_pitch(a, b):
    m = (ft >= a) & (ft < b) & np.isfinite(C_SRC)
    if m.sum() < 2: return None
    return float(np.median(C_SRC[m]))

# ---- energy for AP/SP detection ----
HOP = 0.01
nn = len(v)//int(HOP*sr)
DB = 20*np.log10(np.maximum(np.sqrt((v[:nn*int(HOP*sr)].reshape(nn, int(HOP*sr))**2).mean(1)), 1e-9))
TE = (np.arange(nn)+0.5)*HOP
SIL_THR = -45.0

def is_silent(a, b):
    m = (TE >= a) & (TE < b)
    return (m.sum() > 0) and (float(np.median(DB[m])) < SIL_THR)

# ---- build notes per phrase ----
MIN_NOTE = 0.075     # USTX note 最小（低于此不可唱）
MIN_SPLIT = 0.11     # 只有 >= 此长度才考虑 melisma 拆分

segments = []
issues = []
for p in W['phrases']:
    t0, t1 = p['time']
    words = p['words']
    out_notes = []
    # leading AP if there is real silence before the phrase
    lead = max(t0-0.60, p['time'][0]-0.60)
    if t0 - lead >= 0.20 and is_silent(lead, t0-0.02):
        pv = seg_pitch(t0, min(t0+0.15, t1)) or 6000.0
        out_notes.append(dict(start=round(lead+0.10, 4), end=round(t0-0.02, 4),
                              dur=round(t0-0.02-(lead+0.10), 4),
                              tone=int(round(pv/100)), lyric='AP', kind='breath'))
    for wi, w in enumerate(words):
        a, b = w['start'], w['end']
        dur = b - a
        # GAME notes inside this word (voiced only, long enough)
        cand = [n for n in notes
                if n['voiced'] and n['dur'] >= 0.06
                and n['start'] >= a - 0.03 and n['start'] + n['dur'] <= b + 0.03]
        # split only if the word is long enough and the notes differ in pitch
        pieces = []
        if cand and dur >= MIN_SPLIT and len(cand) >= 2:
            # group candidate notes by pitch similarity (>=60c = new piece)
            groups = []
            for n in cand:
                if groups and abs(n['tone'] - groups[-1][-1]['tone']) < 0.6:
                    groups[-1].append(n)
                else:
                    groups.append([n])
            groups = [g for g in groups if sum(x['dur'] for x in g) >= MIN_NOTE]
            if len(groups) >= 2:
                # boundaries at group starts, clipped into the word
                edges = [a]
                for g in groups[1:]:
                    e = min(max(g[0]['start'], a + MIN_NOTE), b - MIN_NOTE)
                    if e > edges[-1] + MIN_NOTE: edges.append(e)
                edges.append(b)
                if len(edges) >= 3:
                    for k in range(len(edges)-1):
                        pieces.append((edges[k], edges[k+1]))
        if not pieces:
            pieces = [(a, b)]
        for k, (pa, pb) in enumerate(pieces):
            pv = seg_pitch(pa, pb)
            if pv is None: pv = w.get('pitch_cents') or 6000.0
            # keep cent remainder for later PITD design
            tone = int(round(pv/100))
            out_notes.append(dict(start=round(pa, 4), end=round(pb, 4), dur=round(pb-pa, 4),
                                  tone=tone, cent_remainder=round(pv - tone*100, 2),
                                  lyric=w['hanzi'] if k == 0 else '+',
                                  kind='sing', word_idx=wi, piece=k, n_pieces=len(pieces)))
    # gaps between notes: real silence -> AP/SP, else extend previous note
    fixed = []
    for i, n in enumerate(out_notes):
        if fixed:
            gap = n['start'] - fixed[-1]['end']
            if gap > 1e-6:
                if gap >= 0.20 and is_silent(fixed[-1]['end'], n['start']):
                    lv = seg_pitch(n['start'], min(n['start']+0.15, n['end'])) or n['tone']*100
                    kind = 'SP' if gap >= 0.55 else 'AP'
                    fixed.append(dict(start=round(fixed[-1]['end'], 4), end=round(n['start'], 4),
                                      dur=round(gap, 4), tone=int(round(lv/100)),
                                      lyric=kind, kind='rest'))
                else:
                    fixed[-1]['end'] = round(n['start'], 4)
                    fixed[-1]['dur'] = round(fixed[-1]['end']-fixed[-1]['start'], 4)
        fixed.append(n)
    # trailing AP if real silence after
    tail_end = min(t1+0.60, len(v)/sr - 0.1)
    if tail_end - t1 >= 0.20 and is_silent(t1+0.02, tail_end):
        pv = fixed[-1]['tone']*100 if fixed else 6000.0
        fixed.append(dict(start=round(t1+0.02, 4), end=round(min(t1+0.42, tail_end), 4),
                          dur=round(min(t1+0.42, tail_end)-(t1+0.02), 4),
                          tone=fixed[-1]['tone'] if fixed else 60, lyric='AP', kind='breath'))
    # sanity: monotone, positive, no overlap
    for i in range(1, len(fixed)):
        if fixed[i]['start'] < fixed[i-1]['end'] - 1e-6:
            fixed[i]['start'] = fixed[i-1]['end']
            fixed[i]['dur'] = round(fixed[i]['end']-fixed[i]['start'], 4)
    fixed = [n for n in fixed if n['dur'] >= 0.02]
    tiny = [n for n in fixed if n['kind'] == 'sing' and n['dur'] < MIN_NOTE]
    if tiny: issues.append((p['pid'], [(n['lyric'], n['dur']) for n in tiny]))
    segments.append(dict(pid=p['pid'], start_sec=fixed[0]['start'], notes=fixed, label=p['label']))

SCORE = NEW/'score'/f'v3_score.ustx'
build_project('nianlun_v3', segments, SCORE)
tot = sum(len(s['notes']) for s in segments)
n_sing = sum(1 for s in segments for n in s['notes'] if n['kind'] == 'sing')
n_breath = sum(1 for s in segments for n in s['notes'] if n['lyric'] in ('AP','SP'))
n_plus = sum(1 for s in segments for n in s['notes'] if n['lyric'] == '+')
print(f'parts {len(segments)}  notes {tot}  (sing {n_sing}, + {n_plus}, breath {n_breath})')
print(f'short-sing issues: {len(issues)}')
for i in issues[:8]: print('   ', i)

# note duration stats
ds = [n['dur'] for s in segments for n in s['notes'] if n['kind']=='sing']
print(f'\nsing note dur: min {min(ds):.3f} p5 {np.percentile(ds,5):.3f} median {np.median(ds):.3f} max {max(ds):.3f}')
print(f'  <0.075s: {sum(1 for d in ds if d<0.075)}')

(NEW/'score'/'score_meta.json').write_text(json.dumps(dict(
    schema_version=1, score=str(SCORE), parts=len(segments), notes=tot,
    sing_notes=n_sing, extender_notes=n_plus, breath_notes=n_breath,
    segments=[dict(pid=s['pid'], label=s['label'], start=s['start_sec'],
                   notes=[{k: v for k, v in n.items()} for n in s['notes']]) for s in segments],
    issues=issues), ensure_ascii=False, indent=1), encoding='utf-8')
print(f'\nwrote {SCORE}')
