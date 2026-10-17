"""Identity-bound production review, separate from descriptive measurement.

No musical selector, repair, author-array fitting or naturalness score lives here.
The inventory is derived before reading decisions; unknown never counts as pass.
"""
from collections import Counter
import ast
import hashlib
import json
from pathlib import Path

import numpy as np

from ..openutau.ustx import TempoMap, load_ustx, sha256
from .features import Thresholds, shape_features
from .independent import extract_regions, read, static_inventory, validate_native

SCHEMA = 1
FORBIDDEN_ROLES = {'author_array', 'derived_author_parameters', 'historical_target'}
SOURCE_ROLES = {'source_observation', 'current_score', 'native_export', 'software',
                'implementation', 'inferred_rule', 'unknown'} | FORBIDDEN_ROLES


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def ref(path):
    p = Path(path).resolve()
    return dict(path=str(p), sha256=sha256(p))


def bound(spec, base):
    if not isinstance(spec, dict) or set(spec) != {'path', 'sha256'}:
        raise ValueError('Expected a path/SHA256 binding')
    p = Path(spec['path'])
    p = p.resolve() if p.is_absolute() else (Path(base) / p).resolve()
    if not p.is_file() or sha256(p) != spec['sha256']:
        raise ValueError(f'Stale or missing review input: {p}')
    return p


def write(path, value):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open('x', encoding='utf8') as f:
        json.dump(value, f, ensure_ascii=False, indent=2, allow_nan=False)


def exact(value, keys, name):
    if not isinstance(value, dict) or set(value) != set(keys):
        raise ValueError(f'Unsupported {name} schema/fields')


def interval(value):
    if len(value) != 2 or not np.isfinite(value).all() or value[1] <= value[0]:
        raise ValueError('Finite ordered support required')
    return [float(x) for x in value]


def inside(inner, outer, tol=1e-7):
    return outer[0] - tol <= inner[0] < inner[1] <= outer[1] + tol


def source_manifest(path):
    if path is None:
        return [], []
    obj = read(path)
    exact(obj, {'schema_version', 'sources'}, 'source manifest')
    if obj['schema_version'] != SCHEMA:
        raise ValueError('Unsupported source manifest version')
    rows, seen = [], set()
    for s in obj['sources']:
        exact(s, {'id', 'role', 'file', 'description'}, 'source')
        if s['id'] in seen or s['role'] not in SOURCE_ROLES or not s['description'].strip():
            raise ValueError('Duplicate/unsupported source or missing description')
        seen.add(s['id'])
        p = bound(s['file'], Path(path).parent)
        rows.append({**s, 'file': ref(p)})
    return rows, [ref(path)]


def identity(unit):
    """Conditions can change without changing the independently enumerated IDs."""
    return {k: unit[k] for k in ['id', 'part_index', 'phrase_index', 'primary_index',
                                'note_ids', 'phone_ids', 'support_s', 'symbol']}


def native_unit_notes(part, region):
    """A RenderPhone may name only its parent while sounding across extenders."""
    return [n for n in part['notes']
            if n.get('primary_index',n['note_index'])==region['primary_index']
            and n['end_ms']/1000>region['start_s']
            and n['start_ms']/1000<region['end_s']]


def build_inventory(project, out, native_pitch=None, phonemes=None, provenance=None,
                    context=None, sources=None):
    project = Path(project).resolve()
    doc = load_ustx(project)
    for part in doc.get('voice_parts', []):
        part.setdefault('track_no', 0)
    tm = TempoMap.from_doc(doc)
    native, gap = validate_native(project, doc, tm, native_pitch, phonemes, provenance)
    source_rows, source_refs = source_manifest(sources)
    bindings = dict(project=ref(project))
    if native:
        bindings.update(pitch=ref(native_pitch), phonemes=ref(phonemes), provenance=ref(provenance))
        regions, phrases = extract_regions(native)
        units = []
        for r in regions:
            if 'phone_ids' not in r:
                continue
            pi, fi = r['part_index'], r['phrase_index']
            part = native['phones']['parts'][pi]
            raw = part['phrases'][fi]
            matching = [p for p in phrases if p['part_index'] == pi and p['phrase_index'] == fi][0]
            phone_ids = set(r['phone_ids'])
            actual_phones = [p for p in matching['phones'] if p['id'] in phone_ids]
            # The actual Core exporter binds a phone's Parent, not every note
            # it spans. Enumerate the independently exported Extends chain too.
            notes = native_unit_notes(part,r)
            ni = sorted(n['note_index'] for n in notes)
            unit = dict(id=r['id'], part_index=pi, phrase_index=fi,
                        primary_index=r['primary_index'], note_ids=[f'p{pi}:n{i}' for i in ni],
                        phone_ids=r['phone_ids'], symbol=r['symbol'],
                        lyric=part['notes'][r['primary_index']]['lyric'],
                        support_s=[r['start_s'], r['end_s']],
                        musical_stages=[dict(note_id=f'p{pi}:n{n["note_index"]}', tone=n['tone'],
                                             support_s=[max(r['start_s'], n['start_ms']/1000),
                                                        min(r['end_s'], n['end_ms']/1000)])
                                        for n in notes if n['end_ms']/1000 > r['start_s']
                                        and n['start_ms']/1000 < r['end_s']],
                        native_anchors={p['id']: [p['start_s'], p['end_s']] for p in actual_phones},
                        stages=[dict(id=r['id']+':nucleus', kind='unsegmented_nucleus',
                                     support_s=[r['start_s'], r['end_s']], required=True)],
                        condition=dict(status='unknown', evidence_ids=[], observation='',
                                       interpretation='', reliability='native clock only; musical phases unassigned'))
            units.append(unit)
        # Neighbor identities/intervals are factual score observations, not gestures.
        for i, u in enumerate(units):
            u['neighbors'] = dict(previous=units[i-1]['id'] if i else None,
                                  next=units[i+1]['id'] if i+1 < len(units) else None)
    else:
        regions, _, _ = static_inventory(doc, tm, Thresholds())
        units = []
        for r in regions:
            if r['region_type'] != 'note_only' or r['continuation']:
                continue
            units.append(dict(id=r['id'], part_index=r['part_index'], phrase_index=None,
                              primary_index=r['note_index'], note_ids=[r['id']], phone_ids=[],
                              symbol='unknown', lyric=r['lyric'], support_s=[r['start_s'], r['end_s']],
                              musical_stages=[], native_anchors={}, stages=[],
                              condition=dict(status='unknown', evidence_ids=[], observation='',
                                             interpretation='', reliability='note-only; no native vowel clock'),
                              neighbors={}))
    if context:
        ctx = read(context)
        exact(ctx, {'schema_version', 'units'}, 'condition context')
        if ctx['schema_version'] != SCHEMA:
            raise ValueError('Unsupported condition context')
        mapping = {x['id']: x for x in ctx['units']}
        if len(mapping) != len(ctx['units']) or set(mapping)-{u['id'] for u in units}:
            raise ValueError('Unknown/duplicate context unit')
        known_sources = {s['id'] for s in source_rows}
        for u in units:
            if u['id'] not in mapping:
                continue
            c = mapping[u['id']]
            exact(c, {'id', 'condition', 'stages'}, 'unit condition')
            exact(c['condition'], {'status', 'evidence_ids', 'observation', 'interpretation', 'reliability'}, 'condition')
            if c['condition']['status'] not in {'observed', 'interpreted', 'unknown'}:
                raise ValueError('Unknown condition state')
            if not set(c['condition']['evidence_ids']) <= known_sources:
                raise ValueError('Condition cites unbound evidence')
            seen = set()
            for s in c['stages']:
                exact(s, {'id', 'kind', 'support_s', 'required'}, 'stage')
                if s['id'] in seen or not inside(interval(s['support_s']), u['support_s']):
                    raise ValueError('Duplicate/outside native stage')
                if s['kind'] not in {'arrival', 'body', 'release', 'transition', 'unsegmented_nucleus'}:
                    raise ValueError('Unsupported stage kind')
                if not isinstance(s['required'], bool):
                    raise ValueError('Stage required must be boolean')
                seen.add(s['id'])
            if not c['stages']:
                raise ValueError('A known vowel must retain an explicit stage or unknown stage')
            u['condition'], u['stages'] = c['condition'], c['stages']
        source_refs.append(ref(context))
    ids = [u['id'] for u in units]
    if len(set(ids)) != len(ids):
        raise ValueError('Duplicate actual unit identity')
    result = dict(schema_version=SCHEMA, stage='native_bound' if native else 'static_only',
                  bindings=bindings, dependencies=source_refs, sources=source_rows, units=units,
                  regions=regions, unknown_reason=gap, denominator=len(units),
                  identity_sha256=digest([identity(u) for u in units]),
                  native_environment=native['provenance']['environment'] if native else None,
                  musical_quality='unverified', inventory_from_decisions=False)
    write(out, result)
    return result


def validate_inventory(path):
    obj = read(path)
    if obj.get('schema_version') != SCHEMA:
        raise ValueError('Unsupported inventory version')
    for x in [*obj['bindings'].values(), *obj['dependencies'], *[s['file'] for s in obj['sources']]]:
        bound(x, Path(path).parent)
    if obj['identity_sha256'] != digest([identity(u) for u in obj['units']]):
        raise ValueError('Inventory identity digest changed')
    # Re-enumerate from bound inputs, not a caller-edited denominator.
    doc = load_ustx(bound(obj['bindings']['project'], Path(path).parent))
    if obj['stage'] == 'native_bound':
        b = obj['bindings']
        native, gap = validate_native(bound(b['project'], Path(path).parent), doc, TempoMap.from_doc(doc),
                                     bound(b['pitch'], Path(path).parent), bound(b['phonemes'], Path(path).parent),
                                     bound(b['provenance'], Path(path).parent))
        if gap:
            raise ValueError(gap)
        actual, _ = extract_regions(native)
        actual = [r for r in actual if 'phone_ids' in r]
        if len(actual) != obj['denominator'] or {r['id'] for r in actual} != {u['id'] for u in obj['units']}:
            raise ValueError('Inventory denominator/identity differs from actual input')
        by_id = {r['id']: r for r in actual}
        phone_rows={r['id']:r for r in extract_regions(native)[0] if 'phone_ids' not in r}
        for u in obj['units']:
            r = by_id[u['id']]
            expected_notes=sorted(n['note_index'] for n in native_unit_notes(native['phones']['parts'][r['part_index']],r))
            if (u['support_s'] != [r['start_s'], r['end_s']] or u['phone_ids'] != r['phone_ids']
                or any(u[k]!=r[k] for k in ['part_index','phrase_index','primary_index','symbol'])
                or u['note_ids']!=[f'p{r["part_index"]}:n{i}' for i in expected_notes]):
                raise ValueError('Inventory clock/phones changed')
            anchors={ident:[phone_rows[ident]['start_s'],phone_rows[ident]['end_s']] for ident in r['phone_ids']}
            if u['native_anchors']!=anchors:
                raise ValueError('Inventory native anchors changed')
            seen=set()
            for s in u['stages']:
                if s['id'] in seen or not inside(interval(s['support_s']),u['support_s']):
                    raise ValueError('Invalid inventory stage identity/clock')
                seen.add(s['id'])
    elif obj['stage'] != 'static_only':
        raise ValueError('Unsupported inventory stage')
    return obj


def independent_facts(inventory, project, pitch, phonemes, provenance, config=None):
    """This function has no ledger, plan, expectations or review-record argument."""
    inv = validate_inventory(inventory)
    doc = load_ustx(project)
    native, gap = validate_native(project, doc, TempoMap.from_doc(doc), pitch, phonemes, provenance)
    if not native:
        return dict(schema_version=SCHEMA, stage='static_only', reason=gap, units=[],
                    bindings=dict(project=ref(project), inventory=ref(inventory)), config={})
    regions, phrases = extract_regions(native)
    actual = {r['id']: r for r in regions if 'phone_ids' in r}
    if set(actual) != {u['id'] for u in inv['units']}:
        raise ValueError('Final actual vowel inventory differs')
    cfg = config or Thresholds()
    rows = []
    for u in inv['units']:
        r = actual[u['id']]
        if [r['start_s'], r['end_s']] != u['support_s'] or r['phone_ids'] != u['phone_ids']:
            raise ValueError('Final native vowel clock differs from forward inventory')
        pi, fi = u['part_index'], u['phrase_index']
        line = next(p for p in phrases if p['part_index'] == pi and p['phrase_index'] == fi)['raw']
        t = np.asarray(line['pitch_times_ms'])/1000
        y = np.asarray(line['final_cents'])
        p = next(p for p in native['pitch']['phrases'] if p['part_position'] == native['phones']['parts'][pi]['part_position'] and p['position'] == line['position'])
        # Preserve raw, slow linear center and residual; no phase/shape verdict.
        stages = []
        for s in u['stages']:
            a, b = s['support_s']; mask = (t >= a-1e-9) & (t <= b+1e-9)
            tt, yy = t[mask], y[mask]
            f = shape_features(tt, yy, cfg)
            slope = f.get('trend_c_per_s')
            center = np.polyval(np.polyfit(tt-tt[0], yy, 1), tt-tt[0]) if len(tt) >= 2 else yy
            stages.append(dict(id=s['id'], kind=s['kind'], support_s=s['support_s'], features=f,
                               times_s=tt.tolist(), raw_cents=yy.tolist(),
                               slow_linear_center_cents=center.tolist(), residual_cents=(yy-center).tolist(),
                               before_cents=np.asarray(p['before_pitd_cents'])[mask].tolist(),
                               PITD_cents=(y-np.asarray(p['before_pitd_cents']))[mask].tolist()))
        rows.append(dict(id=u['id'], stages=stages, phone_ids=u['phone_ids'],
                         control_values={c['abbr']: dict(xs=c.get('xs', []), ys=c.get('ys', []))
                                         for c in doc['voice_parts'][pi].get('curves', []) if c['abbr'] != 'pitd'},
                         note_pitch_and_vibrato=[dict(note_id=nid,
                                                     pitch=doc['voice_parts'][pi]['notes'][int(nid.split(':n')[1])].get('pitch'),
                                                     vibrato=doc['voice_parts'][pi]['notes'][int(nid.split(':n')[1])].get('vibrato'))
                                                for nid in u['note_ids']]))
    from dataclasses import asdict
    return dict(schema_version=SCHEMA, stage='native_bound',
                bindings=dict(project=ref(project), inventory=ref(inventory), pitch=ref(pitch),
                              phonemes=ref(phonemes), provenance=ref(provenance)),
                config=asdict(cfg), units=rows, denominator=inv['denominator'],
                expectations_read=False, nature='descriptive_only_not_musical_truth',
                rendered_frame_phase_probe='unknown', listening='unknown')


def ledger_check(path, inventory, plan_path=None):
    obj = read(path)
    exact(obj, {'schema_version', 'inventory', 'plan', 'timing', 'decisions', 'revisions'}, 'decision ledger')
    if obj['schema_version'] != SCHEMA or obj['timing'] not in {'forward', 'retrospective'}:
        raise ValueError('Unsupported ledger version/timing')
    if bound(obj['inventory'], Path(path).parent) != Path(inventory).resolve():
        raise ValueError('Wrong ledger inventory')
    pp = bound(obj['plan'], Path(path).parent)
    if plan_path and pp != Path(plan_path).resolve():
        raise ValueError('Ledger targets another plan')
    inv = validate_inventory(inventory)
    units = {u['id']: u for u in inv['units']}
    stages = {s['id']: (u, s) for u in inv['units'] for s in u['stages']}
    counts = Counter()
    failures, flags, seen = [], [], set()
    source_ids = {s['id'] for s in inv['sources']}
    for d in obj['decisions']:
        exact(d, {'id', 'unit_ids', 'stage_ids', 'support_s', 'evidence_ids', 'observation',
                  'interpretation', 'reliability', 'purpose', 'choice', 'alternative',
                  'rejected_because', 'parameter_basis', 'execution', 'checks', 'uncertainty'}, 'decision')
        if d['id'] in seen:
            failures.append(dict(code='duplicate_decision', decision=d['id'])); continue
        seen.add(d['id'])
        if not d['unit_ids'] or not d['stage_ids'] or not set(d['unit_ids']) <= units.keys():
            failures.append(dict(code='missing_or_wrong_unit_mapping', decision=d['id'])); continue
        if not set(d['evidence_ids']) <= source_ids:
            failures.append(dict(code='unbound_decision_evidence', decision=d['id']))
        for k in ['observation', 'interpretation', 'reliability', 'purpose', 'alternative', 'rejected_because', 'parameter_basis']:
            if not isinstance(d[k], str) or not d[k].strip():
                failures.append(dict(code='missing_'+k, decision=d['id']))
        interval(d['support_s'])
        if not d['evidence_ids'] or any(units[i]['condition']['status'] == 'unknown' for i in d['unit_ids']):
            flags.append(dict(code='condition_evidence_unknown', decision=d['id']))
        if d['choice'] not in {'hold', 'center', 'finite_return', 'oscillation', 'landmarks', 'control', 'unknown', 'unsupported'}:
            failures.append(dict(code='unsupported_choice', decision=d['id']))
        if d['choice'] in {'unknown', 'unsupported'}:
            failures.append(dict(code=d['choice'], decision=d['id']))
        if not d['execution'] or not d['checks']:
            failures.append(dict(code='missing_execution_or_check', decision=d['id']))
        for sid in d['stage_ids']:
            if sid not in stages or stages[sid][0]['id'] not in d['unit_ids']:
                failures.append(dict(code='wrong_stage_identity', decision=d['id'], stage_id=sid)); continue
            if not inside(stages[sid][1]['support_s'], d['support_s']):
                failures.append(dict(code='decision_does_not_cover_stage', stage_id=sid))
            counts[sid] += 1
    for sid, (u, s) in stages.items():
        if s['required'] and counts[sid] != 1:
            failures.append(dict(code='missing_stage' if not counts[sid] else 'duplicate_stage', unit_id=u['id'], stage_id=sid))
    if obj['timing'] != 'forward':
        flags.append(dict(code='retrospective_not_forward_design'))
    if inv['stage'] != 'native_bound':
        flags.append(dict(code='static_only_no_native_vowels'))
    for revision in obj['revisions']:
        exact(revision, {'previous', 'reason', 'evidence_ids', 'unit_ids'}, 'ledger revision')
        previous=read(bound(revision['previous'],Path(path).parent))
        if not revision['reason'].strip() or not set(revision['evidence_ids'])<=source_ids or not set(revision['unit_ids'])<=units.keys():
            raise ValueError('Revision needs current evidence, reason and real units')
        old={d['id']:d for d in previous['decisions']}
        for d in obj['decisions']:
            prior=old.get(d['id'])
            if prior and (d['observation']!=prior['observation'] or d['interpretation']!=prior['interpretation']):
                flags.append(dict(code='changed_conditions_require_reassessment',decision=d['id'],
                                  execution_parameters_unchanged=d['execution']==prior['execution'],
                                  previous_ledger=revision['previous']))
    return obj, failures, flags


def check_action(check, stage):
    exact(check, {'stage_id', 'kind', 'support_s', 'parameters'}, 'action check')
    a, b = interval(check['support_s'])
    if not inside([a, b], stage['support_s']):
        return dict(status='fail', reason='check_window_outside_frozen_stage')
    t = np.asarray(stage['times_s']); y = np.asarray(stage['raw_cents']); mask = (t >= a-1e-9) & (t <= b+1e-9)
    t, y = t[mask], y[mask]; p = check['parameters']; kind = check['kind']
    if len(t) < 3 or (len(t)>1 and np.max(np.diff(t)) > .04):
        return dict(status='unknown', reason='insufficient_actual_samples', samples=len(t))
    span = float(np.ptp(y))
    if kind in {'range', 'hold'}:
        exact(p, {'min_c', 'max_c'}, kind)
        if not 0 <= p['min_c'] <= p['max_c']:
            raise ValueError('Invalid range check')
        ok = p['min_c'] <= span <= p['max_c']; result = dict(raw_range_c=span)
    elif kind == 'direction':
        exact(p, {'direction', 'min_delta_c', 'max_backtrack_c'}, kind)
        if p['direction'] not in {'up', 'down'} or p['min_delta_c'] <= 0 or p['max_backtrack_c'] < 0:
            raise ValueError('Invalid directional check')
        sign = 1 if p['direction'] == 'up' else -1
        directed=sign*y
        delta = directed[-1]-directed[0]
        backtrack = float(np.max(np.maximum.accumulate(directed)-directed))
        ok = delta >= p['min_delta_c'] and backtrack <= p['max_backtrack_c']; result = dict(delta_c=float(delta), max_cumulative_backtrack_c=backtrack)
    elif kind == 'landmarks':
        exact(p, {'points', 'tolerance_c', 'time_tolerance_s'}, kind)
        pts = np.asarray(p['points'], float)
        if pts.ndim != 2 or pts.shape[1] != 2 or len(pts)<2 or not np.isfinite(pts).all() or np.any(np.diff(pts[:,0])<=0) or pts[0,0]<a-1e-9 or pts[-1,0]>b+1e-9 or p['tolerance_c']<0 or p['time_tolerance_s']<0:
            raise ValueError('Ordered finite supported landmarks required')
        errors = [];last_index=-1;ordered=True;matched=[]
        for at, target in pts:
            near = abs(t-at) <= p['time_tolerance_s']+1e-9
            errors.append(float(np.min(abs(y[near]-target))) if near.any() else None)
            candidates=np.flatnonzero(near & (abs(y-target)<=p['tolerance_c']) & (np.arange(len(t))>last_index))
            if len(candidates):last_index=int(candidates[0]);matched.append(float(t[last_index]))
            else:ordered=False;matched.append(None)
        ok = ordered and all(e is not None and e <= p['tolerance_c'] for e in errors)
        result = dict(landmark_errors_c=errors, order_preserved=ordered,matched_times_s=matched)
    elif kind == 'cycles':
        exact(p, {'min_cycles', 'prominence_c'}, kind)
        if p['min_cycles'] < 1 or p['prominence_c'] <= 0:
            raise ValueError('Positive cycle requirement needed')
        f = shape_features(t,y,Thresholds(prominence_c=p['prominence_c']))
        if f['status'] != 'evaluated':
            return dict(status='unknown', reason=f['reason'])
        ok = len(f['cycles']) >= p['min_cycles']; result = dict(cycles=len(f['cycles']))
    else:
        return dict(status='fail', reason='unsupported_check_kind')
    return dict(status='pass' if ok else 'fail', kind=kind, support_s=[a,b], **result)


def execution_mapping(entry, plan, doc):
    exact(entry, {'kind', 'part_index', 'position', 'id', 'support_s', 'parameters_sha256'}, 'execution mapping')
    kind = entry['kind']; pi = entry['part_index']
    if not isinstance(pi, int) or not 0 <= pi < len(doc['voice_parts']):
        raise ValueError('Wrong execution part')
    span = interval(entry['support_s'])
    if kind == 'control':
        rows = [c for c in doc['voice_parts'][pi].get('curves', []) if c['abbr'] == entry['id']]
        params = rows[0] if len(rows) == 1 else None
    else:
        phrases = [q for q in plan.get('phrases', []) if q['part_index'] == pi and q['position'] == entry['position']]
        if len(phrases) != 1:
            raise ValueError('Execution phrase not consumed')
        d = phrases[0]['design']
        if kind == 'center_nodes':
            if entry['id'] != 'center_nodes' or not inside(span, d['support_s']):
                raise ValueError('Invalid center mapping')
            params = d['center_nodes']
        elif kind == 'component':
            rows = [c for c in d['components'] if c['id'] == entry['id']]
            params = rows[0] if len(rows) == 1 else None
            if params and span != params['support_s']:
                raise ValueError('Component support changed')
        else:
            raise ValueError('Unsupported execution mapping; no silent substitution')
    if params is None or digest(params) != entry['parameters_sha256']:
        raise ValueError('Execution parameters not consumed/mismatched')
    return (kind, pi, entry['position'], entry['id'])


def audit_sources(inv):
    findings, registered = [], {Path(s['file']['path']).resolve() for s in inv['sources']}
    for s in inv['sources']:
        if s['role'] in FORBIDDEN_ROLES:
            findings.append(dict(status='fail', code='reference_numerics_in_production', source_id=s['id']))
        elif s['role'] == 'unknown':
            findings.append(dict(status='unknown', code='source_role_unknown', source_id=s['id']))
        if s['role'] == 'implementation' and Path(s['file']['path']).suffix == '.py':
            p = Path(s['file']['path']); tree = ast.parse(p.read_text(encoding='utf-8-sig'))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                name = node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, 'id', '')
                if name not in {'load','open','read_text','read_bytes','load_ustx'}:
                    continue
                if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                    value = node.args[0].value
                    if Path(value).suffix in {'.npy','.npz','.ustx','.json'}:
                        q = Path(value);q = q.resolve() if q.is_absolute() else (p.parent/q).resolve()
                        if q not in registered:
                            findings.append(dict(status='review_required', code='unregistered_literal_read', source_id=s['id'], line=node.lineno, literal=value))
    return dict(status='fail' if any(f['status']=='fail' for f in findings) else 'review_required' if findings else 'pass' if inv['sources'] else 'unknown',
                scope='Registered files/roles, parameter bindings and literal Python read sites only',
                findings=findings, unobservable_dynamic_reads_and_Agent_exposure='unknown', absolute_originality_certified=False)


def review_execution(project, inventory, out, pitch=None, phonemes=None, provenance=None,
                     ledger=None, plan=None, reviews=None, make_atlas=True, config=None, atlas_path=None,
                     intent_lock=None, musical_critique=None):
    """Default production and direct-script delivery use this same contract."""
    out = Path(out).resolve();out.mkdir(parents=True, exist_ok=False)
    inv = validate_inventory(inventory)
    # Complete independent facts first, before reading any self-expectations.
    facts = independent_facts(inventory, project, pitch, phonemes, provenance, config)
    write(out/'independent-facts.json', facts)
    from .local_views import build_local_views, review_coverage
    if atlas_path:
        atlas=read(atlas_path)
        if atlas['bindings']!=facts['bindings'] or atlas['denominator']!=inv['denominator']:
            raise ValueError('Reused atlas inputs changed')
        for view in atlas['views']:
            for binding in view['files'].values():bound(binding,Path(atlas_path).parent)
    else:
        atlas = build_local_views(project, inventory, pitch, phonemes, provenance, out/'atlas') if make_atlas and facts['stage']=='native_bound' else None
    failures, flags, actions, ledger_obj = [], [], [], None
    if ledger is None or plan is None:
        failures.append(dict(code='missing_forward_decision_ledger_or_plan'))
    else:
        ledger_obj, failures, flags = ledger_check(ledger, inventory, plan)
        pp = read(plan); doc = load_ustx(project); used = set()
        if facts['stage']=='native_bound':
            from ..workflow import design_math
            helper=design_math();native_lines=read(pitch)['phrases']
            for planned in pp.get('phrases',[]):
                try:
                    d=planned['design'];helper.validate(d)
                    part=doc['voice_parts'][planned['part_index']]
                    lines=[line for line in native_lines if line['part_position']==part['position'] and line['position']==planned['position']]
                    if len(lines)!=1:raise ValueError('Missing actual phrase')
                    line=lines[0];target=np.asarray([helper.evaluate(d,t/1000) for t in line['times_ms']])
                    error=float(np.max(abs(target-np.asarray(line['final_cents']))))
                    if error>.501:
                        failures.append(dict(code='function_target_not_in_actual_native_line',part_index=planned['part_index'],position=planned['position'],max_error_c=error))
                except (ValueError,KeyError,IndexError) as ex:
                    failures.append(dict(code='unsupported_or_invalid_function_execution',reason=str(ex)))
        stages = {s['id']:s for u in facts['units'] for s in u['stages']}
        for d in ledger_obj['decisions']:
            for e in d['execution']:
                try:
                    used.add(execution_mapping(e,pp,doc))
                except ValueError as ex:
                    failures.append(dict(code='execution_mapping_failed', decision=d['id'], reason=str(ex)))
            discriminating = d['choice'] == 'hold'
            covered = set()
            for c in d['checks']:
                sid=c.get('stage_id')
                if sid not in stages or sid not in d['stage_ids']:
                    failures.append(dict(code='wrong_check_stage', decision=d['id'], stage_id=sid));continue
                result = check_action(c,stages[sid]);actions.append(dict(decision=d['id'],stage_id=sid,**result));covered.add(sid)
                if (c['kind'] in {'direction','cycles'}
                    or c['kind']=='landmarks' and np.ptp(np.asarray(c['parameters']['points'])[:,1])>2*c['parameters']['tolerance_c']
                    or c['kind']=='range' and c['parameters']['min_c']>0):
                    discriminating=True
            for sid in set(d['stage_ids'])-covered:
                failures.append(dict(code='missing_stage_check', decision=d['id'], stage_id=sid))
            if not discriminating:
                flags.append(dict(code='non_discriminating_movement_check',decision=d['id']))
        for p in pp.get('phrases',[]):
            for c in p['design']['components']:
                key=('component',p['part_index'],p['position'],c['id'])
                if key not in used:
                    failures.append(dict(code='unmapped_component',component=key))
        for result in actions:
            if result['status'] == 'fail':
                failures.append(dict(code='action_not_realized',**result))
            elif result['status'] == 'unknown':
                flags.append(dict(code='action_measurement_unknown',**result))
        # IDs and slightly different numbers must not defeat structural review.
        # Actual geometry is described separately from prose attestations below.
    coverage = review_coverage(inv, facts, atlas, reviews, inventory, ledger, out/'independent-facts.json')
    sources = audit_sources(inv)
    # A narrow body window cannot silently stand in for the entire vowel.
    # Unassigned entry/exit may be legitimate, but remain explicit unknowns.
    from .local_views import _covers
    unstaged=[u['id'] for u in inv['units'] if not _covers([s['support_s'] for s in u['stages']],u['support_s'])]
    if unstaged:
        flags.append(dict(code='native_support_without_stage',unit_ids=unstaged))
    all_bindings = dict(facts['bindings'])
    for name,path in [('ledger',ledger),('plan',plan),('reviews',reviews)]:
        if path:all_bindings[name]=ref(path)
    if atlas:all_bindings['atlas']=ref(atlas_path or out/'atlas/atlas.json')
    resolved = coverage['resolved_findings']
    unresolvable = {'condition_evidence_unknown','retrospective_not_forward_design',
                    'static_only_no_native_vowels','action_measurement_unknown','native_support_without_stage'}
    unresolved = [f for f in flags if f['code'] in unresolvable or f['code'] not in resolved]
    from .musical_review import evaluate_intent
    musical = evaluate_intent(project, inventory, pitch if facts['stage']=='native_bound' else None,
                              out/'independent-facts.json', plan, intent_lock, musical_critique)
    all_bindings.update(musical['bindings'])
    summary = dict(schema_version=SCHEMA, review_contract_version=2, bindings=all_bindings,
                   facts=ref(out/'independent-facts.json'),
                   inventory_coverage=dict(status='fail' if failures else 'pass' if inv['stage']=='native_bound' else 'unknown',denominator=inv['denominator'],failures=failures),
                   action_execution=dict(status='fail' if any(a['status']=='fail' for a in actions) else 'unknown' if not actions or any(a['status']=='unknown' for a in actions) else 'pass',checks=actions),
                   choice_review=dict(status='review_required' if unresolved or coverage['choice_pending'] else 'agent_attested',findings=flags,unresolved=unresolved,
                                      boundary='Keep/reason/evidence attest review activity, not musical correctness'),
                   musical_review=musical,
                   local_visual_review=coverage,reference_sources=sources,
                   audio=dict(status='unknown',reason='No bound rendered audio/perception supplied'),
                   transfer=dict(status='unknown',reason='No independent new-song validation supplied'),
                   listening='unknown',native_stage=facts['stage'],
                   scope='Process/implementation checks; no musical-quality or naturalness certification')
    unknown_regions=[r['id'] for r in inv['regions'] if r['region_type']=='unknown']
    summary['inventory_coverage']['region_type_counts']=dict(Counter(r['region_type'] for r in inv['regions']))
    summary['inventory_coverage']['phone_region_counts']=dict(Counter(r['region_type'] for r in inv['regions'] if 'phone_ids' not in r))
    summary['inventory_coverage']['vowel_group_count']=inv['denominator']
    summary['inventory_coverage']['unresolved_phone_regions']=unknown_regions
    if unknown_regions and not failures:summary['inventory_coverage']['status']='unknown'
    summary['technical_execution_complete'] = bool(ledger_obj and ledger_obj['timing']=='forward' and not failures and not unknown_regions and summary['action_execution']['status']=='pass' and not any(f['code'] in unresolvable for f in unresolved) and coverage['status']=='pass' and sources['status']=='pass')
    summary['workflow_review_complete'] = bool(summary['technical_execution_complete'] and musical['status']=='agent_attested' and musical['intent_execution']=='pass' and musical['discrimination']=='pass' and musical['phonation']=='listening_evidence')
    summary['production_execution_complete'] = summary['workflow_review_complete']
    summary['completion_boundary'] = 'Legacy completion field now requires the forward musical process and bound calibration evidence. Technical completion, Agent judgment and final auditory quality remain separate; no automatic musical-quality pass.'
    write(out/'review.json',summary)
    lines=['# Production execution review', '', f"Native stage: {facts['stage']}; actual unit denominator: {inv['denominator']}.",
           f"Identity/decision failures: {len(failures)}; unresolved choice findings: {len(unresolved)}.",
           f"Image review: {coverage['completed']}/{inv['denominator']}; numeric-only: {coverage['numeric_only']}; pending: {coverage['pending']}.",
           f"Technical execution complete: {summary['technical_execution_complete']}; workflow review complete: {summary['workflow_review_complete']}.",
           f"Musical intent: {musical['status']}; phonation evidence: {musical['phonation']}. Musical quality/listening/transfer are not certified.",
           '', 'See independent-facts.json, review.json and atlas/index.html. This report is generated by actual checks.']
    (out/'report.md').write_text('\n'.join(lines)+'\n',encoding='utf8')
    return summary


def validate_review(project, review, cfg=None):
    path = Path(review)
    obj = read(path)
    if obj.get('schema_version') != SCHEMA:
        raise ValueError('Unsupported execution review')
    for b in [*obj['bindings'].values(),obj['facts']]:
        bound(b,path.parent)
    if bound(obj['bindings']['project'],path.parent) != Path(project).resolve():
        raise ValueError('Execution review targets another project')
    inventory=validate_inventory(bound(obj['bindings']['inventory'],path.parent))
    if cfg is not None:
        # Rendering consumes today's Core/bridge/singer installation, not only
        # the hashes written in an old export receipt.
        ou=Path(cfg.get('openutau_dir',''))
        singer=load_ustx(project)['tracks'][0]['singer']
        resources=dict(core_sha256=ou/'OpenUtau.Core.dll',bridge_sha256=ou/'a2u-bridge.exe',singer_config_sha256=ou/'Singers'/singer/'dsconfig.yaml')
        current={k:sha256(p) if p.is_file() else None for k,p in resources.items()}
        current['singer_id']=singer
        expected=inventory.get('native_environment')
        if expected is None or current!=expected:
            raise ValueError('Current native environment differs from reviewed environment')
    # Atlas manifest binds each view; a later swapped SVG/PNG invalidates review.
    if 'atlas' in obj['bindings']:
        atlas=read(bound(obj['bindings']['atlas'],path.parent))
        for v in atlas['views']:
            for b in v['files'].values():bound(b,path.parent)
    if 'intent_lock' in obj['bindings']:
        from .musical_review import validate_lock
        validate_lock(bound(obj['bindings']['intent_lock'],path.parent),
                      bound(obj['bindings']['inventory'],path.parent),bound(obj['bindings']['plan'],path.parent))
    if 'musical_critique' in obj['bindings']:
        critique_path=bound(obj['bindings']['musical_critique'],path.parent)
        critique=read(critique_path)
        for row in critique['records']+critique['structural_responses']:
            for evidence in row['evidence']:bound(evidence,critique_path.parent)
    return obj


def delivery_review(project, out, review=None, audio=None):
    """A directly written USTX cannot manufacture a completed delivery receipt."""
    obj = validate_review(project,review) if review else None
    technical=bool(obj and obj.get('technical_execution_complete',obj.get('production_execution_complete',False)))
    workflow=bool(obj and obj.get('review_contract_version')==2 and obj.get('workflow_review_complete'))
    result=dict(schema_version=SCHEMA,review_contract_version=2,project=ref(project),execution_review=ref(review) if review else None,
                execution_status='pass' if technical else 'fail',technical_execution_complete=technical,
                workflow_review_complete=workflow,musical_quality='unverified',
                missing=None if workflow else 'Musical process/calibration incomplete or legacy receipt; candidate only',
                audio=dict(status='unknown'),listening='unknown',transfer='unknown',
                candidate_delivery_allowed=True,production_execution_complete=workflow)
    if audio:
        import soundfile as sf
        x,sr=sf.read(audio,always_2d=True)
        result['audio']=dict(status='pass' if np.isfinite(x).all() and np.max(abs(x),initial=0)<1 else 'fail',file=ref(audio),sample_rate=sr,samples=len(x),peak=float(np.max(abs(x),initial=0)),
                             scope='Audio byte identity/finite/peak only; model inputs, alignment and perceived effect not certified')
    write(out,result)
    return result
