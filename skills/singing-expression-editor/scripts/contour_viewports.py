"""Draw native pitch packets with explicit, unchanged seconds/cents scales.

Input: {curves: [{id, times_s, cents, notes?: [{start_s,end_s,tone,label}],
                  regions?: [{start_s,end_s,label}], before_cents?: [...]}]}.
Output is an offline HTML/SVG atlas and exact viewport metadata. No audio or
expression verdict, smoothing, pitch fitting, or music decisions are made.
"""
import argparse,html,json,math
from pathlib import Path

def checked(curve):
 t=curve['times_s'];y=curve['cents']
 if len(t)!=len(y) or len(t)<2:raise ValueError('Equal nonempty time/pitch arrays required')
 if any(not math.isfinite(v) for v in t+y):raise ValueError('Nonfinite contour')
 if any(b<=a for a,b in zip(t,t[1:])):raise ValueError('Strict physical sample order required')
 if 'before_cents' in curve and len(curve['before_cents'])!=len(t):raise ValueError('Before-curve length differs')
 if any(not math.isfinite(v) for v in curve.get('before_cents',[])):raise ValueError('Nonfinite before-curve')
 return t,y

def viewport(curve,a,b,px_s,px_semitone):
 if not all(math.isfinite(v) for v in [a,b,px_s,px_semitone]) or b<=a or min(px_s,px_semitone)<=0:raise ValueError('Finite ordered viewport and positive scales required')
 t,y=checked(curve);ids=[i for i,v in enumerate(t) if a<=v<=b]
 if not ids:raise ValueError('No samples in viewport')
 lo=100*(math.floor(min(y[i] for i in ids)/100)-1);hi=100*(math.ceil(max(y[i] for i in ids)/100)+1)
 if hi-lo<400:hi=lo+400
 margin_l=72;margin_t=44;width=margin_l+(b-a)*px_s+24;height=margin_t+(hi-lo)/100*px_semitone+38
 def xy(ts,cs):return margin_l+(ts-a)*px_s,margin_t+(hi-cs)*px_semitone/100
 def esc(s):return html.escape(str(s),quote=True)
 ss=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:.3f}" height="{height:.3f}" viewBox="0 0 {width:.3f} {height:.3f}">',
  '<rect width="100%" height="100%" fill="white"/>',f'<text x="72" y="19" font-size="13">{esc(curve["id"])} | {a:.3f}–{b:.3f}s | {px_s:g}px/s; {px_semitone:g}px/semitone</text>']
 for cents in range(int(lo),int(hi)+1,100):
  _,yy=xy(a,cents);ss.append(f'<path d="M72,{yy:.4f} H{width-24:.4f}" stroke="#e2e5eb"/><text x="8" y="{yy+4:.4f}" font-size="11">{cents}</text>')
 # Quarter-second grid is display scaffolding, never a musical clock.
 tick=math.ceil(a*4)/4
 while tick<=b:
  xx,_=xy(tick,hi);ss.append(f'<path d="M{xx:.4f},44 V{height-38:.4f}" stroke="#ededed"/><text x="{xx:.4f}" y="{height-15:.4f}" font-size="10">{tick:.2f}</text>');tick+=.25
 for n in curve.get('notes',[]):
  na=max(a,n['start_s']);nb=min(b,n['end_s'])
  if nb<=na:continue
  x,yy=xy(na,n['tone']*100);w=(nb-na)*px_s
  ss.append(f'<rect x="{x:.4f}" y="{yy-7:.4f}" width="{w:.4f}" height="14" fill="#61aae3" opacity=".28"/><text x="{x+2:.4f}" y="{yy-10:.4f}" font-size="11">{esc(n.get("label",""))}</text>')
 for r in curve.get('regions',[]):
  if a<=r['start_s']<=b:
   xx,_=xy(r['start_s'],hi);ss.append(f'<path d="M{xx:.4f},44 V{height-38:.4f}" stroke="#ae7380" stroke-dasharray="3,3"/><text x="{xx+2:.4f}" y="35" font-size="10">{esc(r.get("label",""))}</text>')
 def line(values,color):
  pts=' '.join(f'{xy(t[i],values[i])[0]:.4f},{xy(t[i],values[i])[1]:.4f}' for i in ids)
  return f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="1.15"/>'
 if 'before_cents' in curve:ss.append(line(curve['before_cents'],'#aaa'))
 ss.append(line(y,'#145da0'));ss.append('</svg>')
 meta=dict(curve_id=curve['id'],start_s=a,end_s=b,sample_indices=ids,px_per_s=px_s,px_per_semitone=px_semitone,
  cents_low=lo,cents_high=hi,width_px=width,height_px=height,x_origin_px=margin_l,y_origin_px=margin_t,
  pitch_coordinates=[[t[i],y[i],*xy(t[i],y[i])] for i in ids],no_time_warp=True,no_smoothing=True,expression_accepted=False)
 return '\n'.join(ss),meta

def atlas(packet,out,window_s=2.,px_s=960.,px_semitone=30.):
 if not all(math.isfinite(v) for v in [window_s,px_s,px_semitone]) or min(window_s,px_s,px_semitone)<=0:raise ValueError('Finite positive explicit display scales required')
 out=Path(out);out.mkdir(parents=True,exist_ok=True);records=[];pages=[]
 for ci,curve in enumerate(packet['curves']):
  t,_=checked(curve);start=t[0];count=math.ceil((t[-1]-start)/window_s)
  pages.append(f'<h2 id="curve-{ci}">{html.escape(str(curve["id"]))}</h2>')
  for j in range(count):
   a=start+j*window_s;b=a+window_s;svg,meta=viewport(curve,a,b,px_s,px_semitone)
   name=f'curve_{ci:03}_view_{j:03}.svg';(out/name).write_text(svg,encoding='utf-8');meta['file']=name;records.append(meta)
   pages.append(f'<div class="viewport"><img src="{name}" style="width:{meta["width_px"]:.3f}px;height:{meta["height_px"]:.3f}px"/></div>')
 nav=' · '.join(f'<a href="#curve-{i}">{html.escape(str(c["id"]))}</a>' for i,c in enumerate(packet['curves']))
 doc='<!doctype html><html><meta charset="utf-8"><title>Physical pitch scale atlas</title><style>body{font-family:Arial,"Microsoft YaHei";margin:16px;background:#f1f3f6}.viewport{overflow-x:auto;margin:12px 0;background:white}h2{font-size:16px}img{max-width:none}a{font-size:12px}</style><h1>固定物理尺度的音高图册</h1><p>蓝线：最终线；灰线（如提供）：before-PITD。图形不缩放到页面宽度，可横向滚动。非唱载频不是实际有声F0。此图册不作表达或听感验收。</p><nav>'+nav+'</nav>'+''.join(pages)+'</html>'
 (out/'index.html').write_text(doc,encoding='utf-8');(out/'viewports.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
 return records

def main():
 p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--window-s',type=float,default=2);p.add_argument('--px-per-s',type=float,default=960);p.add_argument('--px-per-semitone',type=float,default=30);a=p.parse_args()
 packet=json.loads(a.input.read_text(encoding='utf-8-sig'));records=atlas(packet,a.out,a.window_s,a.px_per_s,a.px_per_semitone)
 print(json.dumps(dict(curves=len(packet['curves']),viewports=len(records),index=str(a.out/'index.html'),expression_accepted=False),ensure_ascii=False))
if __name__=='__main__':main()
