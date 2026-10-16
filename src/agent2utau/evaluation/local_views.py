"""Per-vowel native contour atlas and explicit, stale-sensitive review coverage."""
import importlib.util
import html
import math
from pathlib import Path

import numpy as np

from ..resources.config import REPO_ROOT
from .independent import read
from .execution_review import bound, digest, exact, independent_facts, interval, ref, validate_inventory, write


def _viewport_module():
    path=REPO_ROOT/'skills/singing-expression-editor/scripts/contour_viewports.py'
    spec=importlib.util.spec_from_file_location('review_contour_viewports',path)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    return mod


def build_local_views(project, inventory, pitch, phonemes, provenance, out,
                      window_s=2., overlap_s=.25, context_s=.22,
                      px_per_s=600., px_per_semitone=50., png=True):
    from ..openutau.ustx import TempoMap,load_ustx
    inv=validate_inventory(inventory)
    if inv['stage']!='native_bound':
        raise ValueError('Local native views require actual native vowel identities')
    if not all(np.isfinite(v) and v>0 for v in [window_s,overlap_s,context_s,px_per_s,px_per_semitone]) or overlap_s>=window_s:
        raise ValueError('Positive scales/context and overlapping ordered pages required')
    # Validate final native version before drawing anything. No ledger is read.
    independent_facts(inventory,project,pitch,phonemes,provenance)
    lines=read(pitch)['phrases'];phones=read(phonemes)['parts']
    doc=load_ustx(project);tm=TempoMap.from_doc(doc)
    notes=[]
    for pi,part in enumerate(doc['voice_parts']):
        for ni,n in enumerate(part['notes']):
            notes.append(dict(start_s=tm.tick_to_ms(part['position']+n['position'])/1000,
                              end_s=tm.tick_to_ms(part['position']+n['position']+n['duration'])/1000,
                              tone=n['tone'],label=f'p{pi}:n{ni} '+n['lyric']))
    out=Path(out);out.mkdir(parents=True,exist_ok=False);helper=_viewport_module();views=[];mapping=[];pages=[]
    if png:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        from matplotlib import font_manager
        available={f.name for f in font_manager.fontManager.ttflist}
        cjk=next((name for name in ['Microsoft YaHei','Noto Sans SC','Noto Sans CJK SC','SimHei'] if name in available),None)
        if cjk:plt.rcParams['font.sans-serif']=[cjk,'DejaVu Sans']
    for unit in inv['units']:
        a=unit['support_s'][0]-context_s;b=unit['support_s'][1]+context_s
        count=max(1,math.ceil(max(0,b-a-window_s)/(window_s-overlap_s))+1)
        unit_views=[]
        for page in range(count):
            lo=a+page*(window_s-overlap_s);hi=lo+window_s
            ts=[];ys=[];before=[];segments=[];chunks=[]
            for index,line in enumerate(lines):
                tt=np.asarray(line['times_ms'])/1000;mask=(tt>=lo)&(tt<=hi)
                if not mask.any():continue
                yy=np.asarray(line['final_cents'])[mask];bb=np.asarray(line['before_pitd_cents'])[mask]
                chunks.append((tt[mask],yy,bb));ts.extend(tt[mask].tolist());ys.extend(yy.tolist());before.extend(bb.tolist());segments.extend([index]*len(yy))
            curve=dict(id=unit['id']+' / '+unit['lyric'],times_s=ts,cents=ys,before_cents=before,segment_ids=segments,
                       notes=notes,regions=[dict(start_s=s['support_s'][0],end_s=s['support_s'][1],label=s['kind']) for s in unit['stages']])
            svg,meta=helper.viewport(curve,lo,hi,px_per_s,px_per_semitone)
            ident=unit['id'].replace(':','_')+f'_{page:03}';sp=out/(ident+'.svg');sp.write_text(svg,encoding='utf8');files=dict(svg=ref(sp))
            if png:
                # Identical physical scale, axes limits and data as the SVG;
                # larger intervals yield more pixels, never per-unit amplitude scaling.
                width,height=meta['width_px'],meta['height_px'];fig=plt.figure(figsize=(width/100,height/100),dpi=100)
                ax=fig.add_axes([72/width,38/height,(width-96)/width,(height-82)/height])
                ax.set(xlim=(lo,hi),ylim=(meta['cents_low']/100,meta['cents_high']/100),xlabel='absolute seconds',ylabel='MIDI')
                ax.grid(alpha=.25);ax.set_title(curve['id']+f' | {px_per_s:g}px/s; {px_per_semitone:g}px/semitone',fontsize=9)
                for n in notes:
                    x=max(lo,n['start_s']);z=min(hi,n['end_s'])
                    if z>x:
                        ax.fill_between([x,z],n['tone']-.10,n['tone']+.10,color='#61aae3',alpha=.30)
                        ax.text(x,n['tone']+.14,n['label'],fontsize=6,clip_on=True)
                for t,y,bb in chunks:
                    ax.plot(t,bb/100,color='.68',lw=.7);ax.plot(t,y/100,color='#145da0',lw=1)
                ax.axvspan(*unit['support_s'],alpha=.05,color='#008844')
                for s in unit['stages']:
                    ax.axvline(s['support_s'][0],color='#ae7380',lw=.6,ls='--')
                pp=out/(ident+'.png');fig.savefig(pp,dpi=100);plt.close(fig);files['png']=ref(pp)
            coverage=[max(lo,unit['support_s'][0]),min(hi,unit['support_s'][1])]
            row=dict(id=ident,unit_id=unit['id'],view_s=[lo,hi],unit_coverage_s=coverage,
                     source='bound_native_final_not_measured_audio_F0',files=files,
                     px_per_s=px_per_s,px_per_semitone=px_per_semitone,
                     includes_neighbor_context_s=context_s,input_bindings=dict(project=ref(project),pitch=ref(pitch),phonemes=ref(phonemes),inventory=ref(inventory)),
                     data_sha256=digest(curve),metadata=meta)
            views.append(row);unit_views.append(ident)
            pages.append(f'<h3 id="{ident}">{html.escape(unit["id"]+" / "+unit["lyric"])}</h3><div style="overflow:auto"><img style="max-width:none" src="{ident}.svg"></div>')
        mapping.append(dict(unit_id=unit['id'],support_s=unit['support_s'],view_ids=unit_views))
    atlas=dict(schema_version=1,bindings=dict(project=ref(project),inventory=ref(inventory),pitch=ref(pitch),phonemes=ref(phonemes),provenance=ref(provenance)),
               views=views,units=mapping,denominator=inv['denominator'],reviewed_count=0,
               image_generation_is_not_review=True,scales=dict(window_s=window_s,overlap_s=overlap_s,context_s=context_s,px_per_s=px_per_s,px_per_semitone=px_per_semitone))
    write(out/'atlas.json',atlas)
    (out/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>逐元音原生局部图册</title><p>Blue: final; gray: before-PITD. Native intended curves, not audio F0. Atlas generation does not attest actual viewing.</p>'+''.join(pages),encoding='utf8')
    return atlas


def _covers(spans,support):
    cursor=support[0]
    for a,b in sorted(spans):
        if b<=a:continue
        if a>cursor+1e-7:return False
        cursor=max(cursor,b)
    return cursor>=support[1]-1e-7


def review_coverage(inv, facts, atlas, reviews, inventory, ledger, facts_path):
    result=dict(status='unknown',denominator=inv['denominator'],completed=0,numeric_only=0,pending=inv['denominator'],
                failed=0,choice_pending=inv['denominator'],choice_evidence_semantics='Agent attestation only, not musical correctness',resolved_findings=[],units=[],
                review_method_boundary='Image access is an Agent attestation with bound view evidence, not proof of musical understanding or human hearing')
    rows={};valid_sources={s['id'] for s in inv['sources']};viewmap={v['id']:v for v in atlas['views']} if atlas else {}
    if reviews:
        obj=read(reviews)
        exact(obj,{'schema_version','inventory','facts','ledger','atlas','records'},'local review records')
        if obj['schema_version']!=1:raise ValueError('Unsupported local review version')
        for key,target in [('inventory',inventory),('facts',facts_path),('ledger',ledger)]:
            actual=bound(obj[key],Path(reviews).parent)
            if target is None or (key=='facts' and ref(actual)['sha256']!=ref(target)['sha256']) or (key!='facts' and actual!=Path(target).resolve()):
                raise ValueError('Review records target another '+key)
        atlas_path=bound(obj['atlas'],Path(reviews).parent)
        stored=read(atlas_path)
        if not atlas or stored['bindings']!=atlas['bindings']:
            raise ValueError('Stale local atlas version')
        for v in stored['views']:
            for b in v['files'].values():bound(b,atlas_path.parent)
        # New regenerated atlas may have different directory paths but exact
        # source/data/scales. Reuse requires those dependencies, not a filename.
        new={v['id']:v for v in atlas['views']}
        if set(new)!={v['id'] for v in stored['views']} or any(v['data_sha256']!=new[v['id']]['data_sha256'] or v['view_s']!=new[v['id']]['view_s'] for v in stored['views']):
            raise ValueError('View content/coverage changed after review')
        for r in obj['records']:
            exact(r,{'unit_id','view_ids','method','view_evidence','facts_sha256','observation','result','reason','evidence_ids','resolved_findings'},'per-unit review')
            if r['unit_id'] in rows:raise ValueError('Duplicate actual unit review')
            if r['result'] not in {'keep','revise','fail','unknown'} or r['method'] not in {'image_and_numeric','numeric_only'}:
                raise ValueError('Unsupported review method/result')
            if r['facts_sha256']!=digest(next((u for u in facts['units'] if u['id']==r['unit_id']),None)):
                raise ValueError('Stale unit measurements')
            if not r['observation'].strip() or not r['reason'].strip() or not set(r['evidence_ids'])<=valid_sources:
                raise ValueError('Missing contextual observation/reason or unbound evidence')
            if r['method']=='image_and_numeric':
                if not r['view_evidence']:raise ValueError('Image review needs an access/artifact evidence record')
                for e in r['view_evidence']:bound(e,Path(reviews).parent)
            rows[r['unit_id']]=r
    actual={u['id'] for u in inv['units']}
    if set(rows)-actual:raise ValueError('Review for nonexisting unit')
    for u in inv['units']:
        r=rows.get(u['id']);state='unknown';covered=False
        if r:
            if not set(r['view_ids'])<=viewmap.keys() or any(viewmap[i]['unit_id']!=u['id'] for i in r['view_ids']):
                raise ValueError('Wrong unit/view identity')
            covered=_covers([viewmap[i]['unit_coverage_s'] for i in r['view_ids']],u['support_s'])
            if r['result'] in {'fail','revise'}:state='fail';result['failed']+=1
            elif r['method']=='numeric_only':result['numeric_only']+=1
            elif covered and r['result']=='keep':state='pass';result['completed']+=1
            if r['result']=='keep' and r['evidence_ids']:
                result['choice_pending']-=1
                result['resolved_findings'].extend(r['resolved_findings'])
        result['units'].append(dict(unit_id=u['id'],status=state,view_coverage_complete=covered,
                                    method=r['method'] if r else None))
    result['pending']=result['denominator']-result['completed']-result['failed']
    result['resolved_findings']=sorted(set(result['resolved_findings']))
    result['status']='fail' if result['failed'] else 'pass' if result['completed']==result['denominator'] and result['denominator'] else 'unknown'
    return result
