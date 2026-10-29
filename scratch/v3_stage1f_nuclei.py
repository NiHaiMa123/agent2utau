"""阶段1f：用实际音素清单定义元音核，重建 hfa_summary 的字级结构。

韵母（音节末位）共 30 种，来自实际 HFA 输出统计：
  a o e i u v E i0 ir er(无) ai ei ao ou an en ang eng ong
  ia ie iao iou(iu) ian in iang ing iong ua uo uai uei(ui) uan uen(un) uang ueng
  van vn er En
本数据实际出现：a e i o u v E i0 ir ai ei ao ou an en eng ong ia(无) ian iang in ing
                iu ui uan uang uo un van ve En
"""
import sys, json, io, re
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
h = json.load(io.open(NEW/'hfa_summary.json', encoding='utf-8'))

# 从实际数据统计出的韵母集合（音节末位 + 全部非声母符号）
NUCLEI = set("""a o e i u v E i0 ir er ai ei ao ou an en ang eng ong
ia ie iao iu ian in iang ing iong ua uo uai ui uan un uang ueng
van vn En""".split())
NONLEX = {'SP', 'AP', 'EP', ''}
ONSETS = set("""b p m f d t n l g k h j q x zh ch sh r z c s y w""".split())

issues = []
out = []
for p in h['phrases']:
    lex = p['lexical']
    for w in lex:
        marks = [q['mark'] for q in w['phones']]
        # nucleus = last symbol that is a known nucleus
        nuc = None
        for q in reversed(w['phones']):
            if q['mark'] in NUCLEI and q['dur'] > 0.0:
                nuc = q; break
        w['nucleus'] = nuc
        w['nucleus_mark'] = nuc['mark'] if nuc else None
        if nuc is None:
            issues.append(dict(pid=p['pid'], hanzi=w.get('hanzi'), marks=marks,
                               dur=w['dur'], kind='no_nucleus'))
        elif nuc['dur'] < 0.04:
            issues.append(dict(pid=p['pid'], hanzi=w.get('hanzi'), marks=marks,
                               dur=w['dur'], nuc_dur=nuc['dur'], kind='nucleus_too_short'))
    out.append(p)

print(f'phrases {len(out)}')
print(f'issues {len(issues)}')
from collections import Counter
print('  by kind:', dict(Counter(i['kind'] for i in issues)))
for i in issues[:25]:
    print('   ', i)

n_ok = sum(1 for p in out for w in p['lexical'] if w.get('nucleus'))
n_all = sum(len(p['lexical']) for p in out)
print(f'\nwords with a usable nucleus: {n_ok}/{n_all} ({n_ok/n_all:.1%})')

# word duration sanity
bad = [(p['pid'], w['hanzi'], w['dur']) for p in out for w in p['lexical'] if w['dur'] <= 0]
print(f'non-positive word durations: {len(bad)} {bad[:5]}')

(NEW/'hfa_summary.json').write_text(json.dumps(dict(phrases=out, issues=issues), ensure_ascii=False, indent=1),
                                    encoding='utf-8')
print('wrote hfa_summary.json')
