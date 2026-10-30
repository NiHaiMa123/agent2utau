"""阶段1e（修正）：正确解析 HFA TextGrid（按 tier 分离）。

修正点：旧正则把 words 与 phones 两个 tier 的 xmin 混在一个列表里，
导致"字时长总和 > 切片长度"的假重叠。实际两个 tier 各自连续铺满切片。
"""
import sys, json, io, re, hashlib
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
lyr = json.load(io.open(NEW/'lyrics.json', encoding='utf-8'))
rows = lyr['phrases']

VOWELS = set('a o e i u v ai ei ao ou an en ang eng ong ia ie iao iou ian in iang ing iong '
             'ua uo uai uei uan uen uang ueng van vn er'.split())
NONLEX = {'SP', 'AP', 'EP', ''}


def parse_textgrid(path):
    txt = path.read_text(encoding='utf-8')
    tiers = {}
    for m in re.finditer(
            r'item \[\d+\]:\s*\n\s*class = "(\w+)"\s*\n\s*name = "(\w+)"(.*?)(?=\n\titem \[|\Z)',
            txt, re.S):
        name, body = m.group(2), m.group(3)
        ivs = re.findall(
            r'intervals \[\d+\]:\s*\n\s*xmin = ([-\d.eE+]+)\s*\n\s*xmax = ([-\d.eE+]+)\s*\n\s*text = "([^"]*)"',
            body)
        tiers[name] = [dict(start=float(a), end=float(b), mark=t) for a, b, t in ivs]
    return tiers


summary, issues = [], []
for r in rows:
    p = NEW/'hfa'/'TextGrid'/f"{r['pid']}.TextGrid"
    if not p.is_file():
        issues.append(f"{r['pid']}: missing"); continue
    tg = parse_textgrid(p)
    off = r['slice'][0]
    words = [dict(mark=w['mark'], start=round(w['start']+off, 4), end=round(w['end']+off, 4),
                  dur=round(w['end']-w['start'], 4)) for w in tg.get('words', [])]
    phones = [dict(mark=q['mark'], start=round(q['start']+off, 4), end=round(q['end']+off, 4),
                   dur=round(q['end']-q['start'], 4)) for q in tg.get('phones', [])]
    lex = [w for w in words if w['mark'] not in NONLEX]
    if len(lex) != len(r['hanzi']):
        issues.append(f"{r['pid']}: {len(lex)} words vs {len(r['hanzi'])} hanzi ({r['hanzi']})")
    for w, ch in zip(lex, r['hanzi']):
        w['hanzi'] = ch
    # word -> its phones (phones inside word span)
    for w in lex:
        w['phones'] = [q for q in phones
                       if q['mark'] not in NONLEX
                       and q['start'] >= w['start']-1e-6 and q['end'] <= w['end']+1e-6]
        vs = [q for q in w['phones'] if q['mark'] in VOWELS and q['dur'] > 0.02]
        w['vowel'] = vs[-1] if vs else None   # main (final) vowel = nucleus
    # intrinsic checks
    if lex:
        sd = sum(w['dur'] for w in lex)
        sl = r['slice'][1]-r['slice'][0]
        if sd > sl + 1e-6:
            issues.append(f"{r['pid']}: word dur sum {sd:.2f} > slice {sl:.2f}")
        for a, b in zip(lex, lex[1:]):
            if a['end'] > b['start'] + 1e-6:
                issues.append(f"{r['pid']}: overlap {a['hanzi']}->{b['hanzi']}")
    vs_all = [q for q in phones if q['mark'] in VOWELS and q['dur'] > 0.02]
    summary.append(dict(pid=r['pid'], label=r['label'], hanzi=r['hanzi'], pinyin=r['pinyin'],
                        slice=r['slice'], time=[r['t0'], r['t1']],
                        words=words, lexical=lex, phones=phones, vowel_spans=vs_all,
                        textgrid=str(p)))

print(f'parsed {len(summary)} phrases, issues {len(issues)}')
for i in issues[:20]: print('  ', i)

tot_w = sum(len(p['lexical']) for p in summary)
tot_v = sum(len(p['vowel_spans']) for p in summary)
nowov = sum(1 for p in summary for w in p['lexical'] if w.get('vowel') is None)
tiny = [(p['pid'], w['hanzi'], w['dur']) for p in summary for w in p['lexical'] if w['dur'] < 0.08]
print(f'\ntotal lexical words {tot_w}, vowels {tot_v}, words WITHOUT nucleus: {nowov}')
print(f'words < 80ms: {len(tiny)}')
for t in tiny[:15]: print('   ', t)

(NEW/'hfa_summary.json').write_text(json.dumps(dict(phrases=summary, issues=issues),
                                               ensure_ascii=False, indent=1), encoding='utf-8')
print(f'\nwrote {NEW}/hfa_summary.json')
