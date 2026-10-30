"""更新图审记录（v14 实际审阅）并写最终报告数据。"""
import sys, json, io
import numpy as np
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')
from agent2utau.openutau.ustx import load_ustx

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
REF = Path(r'E:\project\agent2utau\research\baishuo\projects\雨爱-有参by白烁.ustx')

def pitd_summary(path,label):
    d=load_ustx(path); ys=[]
    for part in d['voice_parts']:
        pit=next((c for c in part.get('curves',[]) if c['abbr']=='pitd'),None)
        if pit: ys.extend(pit['ys'])
    y=np.array(ys,float); dy=np.abs(np.diff(y))
    return dict(label=label,n=len(y),
                p50=float(np.percentile(y,50)),p99=float(np.percentile(y,99)),
                abs200=float((np.abs(y)>200).mean()),
                dy_max=float(dy.max()), dy_med=float(np.median(dy)),
                steps_over200=int((dy>200).sum()))

summary=dict(
  baishuo=pitd_summary(REF,'白烁 雨爱'),
  v14=pitd_summary(NEW/'compiled'/'project_v14.ustx','v14 年轮'),
)

review = dict(
  schema_version=1,
  method='atlas PNG actually opened with read_image; observation recorded per image',
  records=[
    dict(version='v11', atlas='p0_f0_v0_000.png', opened=True, result='fail',
         observation='18.75s 垂直暴跌 56->50.8（约 -520c，5 个半音）；19.4s 亦有阶梯。',
         reason='极端段在 12ms 网格内瞬移成悬崖；句首下探 5 个半音音乐上不成立。',
         action='极端段改为有起有落的平滑段 + 斜率软限幅。'),
    dict(version='v12', atlas='p0_f0_v0_000.png', opened=True, result='fail',
         observation='悬崖消失，但 18.75s 仍为 V 形下陷 57->51.4（-560c），约 100ms。',
         reason='按分位数统计去拟合，导致每个字都深挖；白烁 p1=-513c 是极少数点而非句首常态。',
         action='按音乐判断收敛字头深度（普通字 22~95c，大跳最多 150c）。'),
    dict(version='v13', atlas='p0_f0_v0_000.png', opened=True, result='fail',
         observation='仍有 57->54 的 3 个半音下探；音符边界处相邻字偏移方向相反造成 |dy|≈450c 的跳变。',
         reason='每个音符的起止偏移独立设计，跨音符不连续。',
         action='把音符两端偏移强制为 0，动作只在音符内部完成。'),
    dict(version='v14', atlas='p0_f0_v0_000.png', opened=True, result='keep',
         observation='起音仅轻微下探即平滑进入 57 平台；音符之间是连续斜坡而非垂直台阶；'
                     '字腹有可见起伏；无尖角、无深 V。',
         reason='形状符合手绘线条：平滑、幅度克制、跨音符连续。',
         action='保留。'),
  ],
  coverage=dict(units_total=349, units_opened=4,
                note='4/349 实际打开（同一单元在 4 个版本上各看一次）；其余单元未审，不计覆盖'),
  limitation='349 个单元未逐个打开，本记录不构成覆盖完成；也不构成听感验收')
(NEW/'evaluation'/'visual_review_partial.json').write_text(
  json.dumps(dict(review=review, summary=summary), ensure_ascii=False, indent=2), encoding='utf-8')

print('PITD shape:')
for k in ('baishuo','v14'):
    s=summary[k]
    print(f"  {s['label']:12s} n={s['n']:6d} p50={s['p50']:+6.0f} p99={s['p99']:+6.0f} "
          f"|y|>200={s['abs200']:.2%} |dy|med={s['dy_med']:.0f} max={s['dy_max']:.0f} "
          f"steps>200={s['steps_over200']}")
print('\nwrote evaluation/visual_review_partial.json')
