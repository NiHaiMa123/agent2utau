"""诊断 HFA 为何在部分句子崩掉：切片是否过短/边界是否切断了字。"""
import sys, json, io
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
h = json.load(io.open(NEW/'hfa_summary.json', encoding='utf-8'))

print('phrase | slice_len | word_span | sum_word_dur | collapsed?')
bad = []
for p in h['phrases']:
    if not p['lexical']: continue
    sl = p['slice'][1] - p['slice'][0]
    w0, w1 = p['lexical'][0]['start'], p['lexical'][-1]['end']
    ws = w1 - w0
    sd = sum(w['dur'] for w in p['lexical'])
    # collapsed if word span far less than slice, or word dur sum implausible
    flag = ''
    if ws < 0.5*sl: flag += 'SHORT_SPAN '
    if sd > sl*1.02: flag += 'OVERLAP '
    if any(w['dur'] < 0.03 for w in p['lexical']): flag += 'TINY_WORD '
    if flag:
        bad.append((p['pid'], p['hanzi'], sl, ws, sd, flag))
        print(f"  {p['pid']} {p['hanzi']:12s} slice={sl:5.2f} span={ws:5.2f} sumdur={sd:5.2f}  {flag}")

print(f'\nfailed phrases: {len(bad)} / {len(h["phrases"])}')
print('pids:', [b[0] for b in bad])
